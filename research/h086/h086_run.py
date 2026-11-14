"""H086: independent Dartmouth Fama-French + Cboe VIX causal historical tests.

The preregistration file was committed before the data were downloaded.
No live orders, ACCEPT verdicts or production code changes.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONF = ROOT / "research" / "h086" / "PREREGISTRATION.yaml"
SEED = 86014


def acquire(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "quant-superlab-H086-research/1.0"})
    with urllib.request.urlopen(req, timeout=75) as reply:
        content = reply.read()
    if len(content) < 10000:
        raise ValueError(f"Source unexpectedly small: {url}")
    return content


def parse_ff_daily(payload: bytes) -> pd.DataFrame:
    """Only YYYYMMDD daily block; percent units to fractions. No monthly/annual rows."""
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        files = [x for x in z.namelist() if x.lower().endswith(".csv")]
        if len(files) != 1:
            raise ValueError(f"Expected one French CSV; got {files}")
        raw = z.read(files[0]).decode("latin-1")
    lines = raw.splitlines()
    header = next((i for i, x in enumerate(lines)
                   if re.search(r"\bMkt-RF\s*,\s*SMB\s*,\s*HML\s*,\s*RF\b", x)), None)
    if header is None:
        raise ValueError("French daily factor header not found")
    records = []
    for line in lines[header + 1:]:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 5 or not re.fullmatch(r"\d{8}", parts[0]):
            if records:
                break
            continue
        records.append([parts[0], float(parts[1]) / 100., float(parts[4]) / 100.])
    if len(records) < 6000:
        raise ValueError(f"French daily history too short: {len(records)}")
    frame = pd.DataFrame(records, columns=["date", "mkt_excess", "rf"])
    frame["date"] = pd.to_datetime(frame.date, format="%Y%m%d", errors="raise")
    return frame.set_index("date").sort_index()


def parse_cboe_vix(payload: bytes) -> pd.Series:
    frame = pd.read_csv(io.BytesIO(payload))
    frame.columns = frame.columns.str.strip().str.upper()
    if not {"DATE", "CLOSE"}.issubset(frame):
        raise ValueError(f"Cboe VIX header changed: {list(frame.columns)}")
    dates = pd.to_datetime(frame["DATE"], errors="coerce")
    values = pd.to_numeric(frame["CLOSE"], errors="coerce")
    vix = pd.Series(values.to_numpy(), index=pd.DatetimeIndex(dates), name="vix")
    vix = vix.loc[vix.index.notna()].sort_index()
    if len(vix) < 6000 or (vix.dropna() <= 0).any():
        raise ValueError("VIX source invalid or too short")
    if vix.index.duplicated().any():
        raise ValueError("VIX duplicate dates")
    return vix


def join_sources(ff: pd.DataFrame, vix: pd.Series, c: dict) -> tuple[pd.DataFrame, dict]:
    start = pd.Timestamp(c["data"]["start"])
    end = pd.Timestamp(c["data"]["end"])
    frame = ff.loc[start:end].copy()
    if frame.index.duplicated().any() or not frame.index.is_monotonic_increasing:
        raise ValueError("French date integrity invalid")
    if frame.index.max() < end - pd.Timedelta(days=30):
        raise ValueError(f"French provider stale at {frame.index.max()}")
    if vix.loc[:end].index.max() < end - pd.Timedelta(days=30):
        raise ValueError(f"Cboe provider stale at {vix.index.max()}")
    observed = vix.reindex(frame.index)
    missing_fraction = float(observed.isna().mean())
    if missing_fraction > c["data"]["maximum_vix_missing_fraction"]:
        raise ValueError(f"VIX missing fraction {missing_fraction:.3%} exceeds frozen limit")
    frame["vix"] = observed.ffill(limit=int(c["data"]["forward_fill_trading_days"]))
    if frame.isna().any().any() or not np.isfinite(frame.to_numpy(float)).all():
        raise ValueError("Joined factor/VIX panel has missing or invalid returns")
    if len(frame) < int(c["data"]["min_overlap"]):
        raise ValueError("Independent-source matched history too short")
    if ((frame["mkt_excess"] + frame["rf"]) <= -1).any():
        raise ValueError("Invalid market total returns")
    metadata = {
        "dates": [str(frame.index.min().date()), str(frame.index.max().date())],
        "aligned_trading_days": len(frame),
        "vix_missing_fraction_before_1day_fill": missing_fraction,
        "vix_one_day_forward_fills": int(observed.isna().sum()),
        "latest_market": str(ff.index.max().date()),
        "latest_vix": str(vix.index.max().date()),
    }
    return frame, metadata


def signal_weights(panel: pd.DataFrame) -> dict[str, pd.Series]:
    """Target weight for session t ONLY from completed sessions through t-1."""
    v = panel.vix
    total = panel.mkt_excess + panel.rf
    spike = (v.pct_change(5, fill_method=None) >= .25) & (total <= -.01)
    hold = spike.shift(1, fill_value=False).rolling(5, min_periods=1).max().astype(bool)
    a = pd.Series(np.where(hold, 0.0, 1.0), index=panel.index)
    b = pd.Series(np.where(v.shift(1) >= 25, .5, 1.), index=panel.index)
    annvol = total.rolling(21, min_periods=21).std().shift(1) * np.sqrt(252)
    target = (.12 / annvol.where(annvol > 0)).clip(lower=.3, upper=1.)
    c = target.fillna(1.)
    hist_median = v.rolling(252, min_periods=252).median().shift(1)
    d = pd.Series(np.where((v.shift(1) > hist_median) & hist_median.notna(),
                           .5, 1.), index=panel.index)
    momentum_negative = np.log1p(total).rolling(63, min_periods=63).sum().shift(1) < 0
    e = pd.Series(np.where((v.shift(1) >= 25) & momentum_negative, .25, 1.), index=panel.index)
    return {"H086A": a, "H086B": b, "H086C": c, "H086D": d, "H086E": e}


def daily_book(panel: pd.DataFrame, weights: pd.Series, bps_oneway: int) -> pd.DataFrame:
    if not panel.index.equals(weights.index):
        raise ValueError("Weights/calendar misaligned")
    if weights.isna().any() or (weights < 0).any() or (weights > 1).any():
        raise ValueError("Invalid or leveraged weights")
    turnover = weights.diff().abs().fillna(weights.iloc[0])
    cost = turnover * (bps_oneway / 10000.)
    # T-bill RF on uninvested cash, market premium on the invested share.
    ret = panel.rf + weights * panel.mkt_excess - cost
    if (ret <= -1).any():
        raise ValueError("Bankrupt or impossible daily portfolio return")
    return pd.DataFrame({"ret": ret, "rf": panel.rf, "weight": weights,
                         "turnover": turnover, "cost": cost}, index=panel.index)


def summarize(frame: pd.DataFrame) -> dict:
    if len(frame) < 100:
        raise ValueError("Too few dates in evaluation split")
    r = frame["ret"].to_numpy(float)
    nav = np.cumprod(1 + r)
    years = len(r) / 252.
    sh = np.std(r, ddof=1)
    dd = (nav / np.maximum.accumulate(np.r_[1., nav])[1:]) - 1
    return {
        "sessions": len(r), "years": float(years),
        "total_return": float(nav[-1] - 1),
        "cagr": float(nav[-1] ** (1 / years) - 1),
        "sharpe": float(r.mean() / sh * math.sqrt(252)) if sh > 0 else None,
        "max_drawdown": float(dd.min()),
        "mean_market_weight": float(frame.weight.mean()),
        "turnover_sum": float(frame.turnover.sum()),
        "cost_sum": float(frame.cost.sum()),
    }


def evaluate_period(candidate: pd.DataFrame, baseline: pd.DataFrame,
                    first: str, last: str) -> dict:
    d = candidate.loc[first:last]
    b = baseline.loc[first:last]
    if not d.index.equals(b.index):
        raise ValueError("Benchmark date mismatch")
    x, y = summarize(d), summarize(b)
    return {"candidate": x, "benchmark": y,
            "active_cagr": x["cagr"] - y["cagr"],
            "active_total_gap": x["total_return"] - y["total_return"],
            "dd_not_worse": x["max_drawdown"] >= y["max_drawdown"]}


def monthly_active(candidate: pd.DataFrame, benchmark: pd.DataFrame) -> pd.Series:
    d = candidate.ret.resample("ME").apply(lambda x: float((1 + x).prod() - 1))
    b = benchmark.ret.resample("ME").apply(lambda x: float((1 + x).prod() - 1))
    return d.sub(b).dropna()


def bootstrap_p(monthly_active_return: pd.Series, n: int = 2000,
                block: int = 3, seed: int = SEED) -> dict:
    """Paired monthly excess return, stationary circular blocks, one-sided p(mean <= 0)."""
    x = monthly_active_return.to_numpy(float)
    if len(x) < 60 or not np.isfinite(x).all():
        return {"p": None, "months": len(x), "reason": "insufficient_finite_months"}
    rng = np.random.default_rng(seed)
    means = np.empty(n)
    T = len(x)
    for j in range(n):
        ix = np.empty(T, dtype=int)
        ix[0] = rng.integers(0, T)
        for i in range(1, T):
            ix[i] = rng.integers(0, T) if rng.random() < 1. / block else (ix[i-1] + 1) % T
        means[j] = float(x[ix].mean())
    return {"p": float((1 + (means <= 0).sum()) / (n + 1)),
            "mean_monthly_active": float(x.mean()),
            "mean_ci95": [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))],
            "months": len(x), "reps": n, "block_mean": block}


def holm_adjust(pmap: dict[str, float | None]) -> dict[str, float | None]:
    ok = sorted((p, k) for k, p in pmap.items() if p is not None)
    adj: dict[str, float | None] = {k: None for k in pmap}
    running = 0.
    m = len(pmap)  # all five frozen candidates count even if one p is missing
    for i, (p, k) in enumerate(ok):
        running = max(running, (m-i)*p)
        adj[k] = min(1., running)
    return adj


def _dates(c: dict, period: str) -> tuple[str, str]:
    return tuple(c["splits"][period])


def run(c: dict, output: Path):
    paths = [c["source_a"]["url"], c["source_b"]["url"]]
    payloads = [acquire(url) for url in paths]
    hashes = {name: hashlib.sha256(b).hexdigest() for name, b in
              zip(["french_factors_zip", "cboe_vix_csv"], payloads)}
    ff, vix = parse_ff_daily(payloads[0]), parse_cboe_vix(payloads[1])
    panel, meta = join_sources(ff, vix, c)
    weights = signal_weights(panel)
    if set(weights) != set(c["hypotheses"]):
        raise ValueError("Hypothesis registry doesn't match frozen registrations")

    periods = list(c["splits"])
    costs = c["execution"]["fee_bps_oneway"]
    baselines = {fee: daily_book(panel, pd.Series(1., index=panel.index), fee) for fee in costs}
    ledger = []
    by_candidate = {}
    for name, w in weights.items():
        cdata = {"hypothesis": name, "rules": c["hypotheses"][name]}
        for fee in costs:
            perf = daily_book(panel, w, fee)
            if fee == costs[0]:
                out = perf.assign(benchmark=baselines[fee].ret, hypothesis=name)
                ledger.append(out)
            cdata[f"cost_{fee}bps"] = {
                p: evaluate_period(perf, baselines[fee], *_dates(c, p))
                for p in periods
            }
            test_start, test_end = _dates(c, "untouched_holdout_one_shot")
            if fee == costs[0]:
                series = monthly_active(perf.loc[test_start:test_end],
                                        baselines[fee].loc[test_start:test_end])
                cdata["inference"] = bootstrap_p(series,
                    n=int(c["selection_and_release"]["bootstrap_replicates"]),
                    block=int(c["selection_and_release"]["bootstrap_mean_block_months"]))
                cdata["month_dates"] = [str(series.index.min().date()), str(series.index.max().date())]
                cdata["holdout_subperiods"] = {
                    "2019_2022": evaluate_period(perf, baselines[fee], "2019-01-01", "2022-12-31"),
                    "2023_2026": evaluate_period(perf, baselines[fee], "2023-01-01", "2026-08-31"),
                }
        by_candidate[name] = cdata
    pmap = {k: v["inference"]["p"] for k, v in by_candidate.items()}
    adjusted = holm_adjust(pmap)
    for k, v in by_candidate.items():
        validation = v[f"cost_{costs[0]}bps"]["validation"]
        held = v[f"cost_{costs[0]}bps"]["untouched_holdout_one_shot"]
        stressed = v[f"cost_{costs[1]}bps"]["untouched_holdout_one_shot"]
        sub = v["holdout_subperiods"]
        gates = {
            "validation_excess_ge_1pct": validation["active_cagr"] >= .01,
            "validation_maxdd_not_worse": validation["dd_not_worse"],
            "holdout_excess_ge_1pct": held["active_cagr"] >= .01,
            "holdout_maxdd_not_worse": held["dd_not_worse"],
            "holdout_2019_2022_excess_positive": sub["2019_2022"]["active_cagr"] > 0,
            "holdout_2023_2026_excess_positive": sub["2023_2026"]["active_cagr"] > 0,
            "holdout_2x_cost_excess_positive": stressed["active_cagr"] > 0,
            "holdout_market_exposure_ge_50pct": held["candidate"]["mean_market_weight"] >= .5,
            "familywise_holm_p_le_005": adjusted[k] is not None and adjusted[k] <= .05,
            "holdout_min_6years": held["candidate"]["years"] >= 6,
            "validation_min_7years": validation["candidate"]["years"] >= 7,
        }
        v["holm_adjusted_p"] = adjusted[k]
        v["gates"] = gates
        v["research_verdict"] = "HISTORICAL_PASS_NOT_LIVE" if all(gates.values()) else "FAIL_PREDECLARED_GATE"
        v["new_accept"] = False  # historical research can never modify the live registry

    output.mkdir(parents=True, exist_ok=True)
    daily = pd.concat(ledger).reset_index().rename(columns={"index": "date"})
    daily.to_csv(output / "H086_DAILY_RETURNS.csv", index=False)
    gate_rows = []
    for k, v in by_candidate.items():
        hold = v[f"cost_{costs[0]}bps"]["untouched_holdout_one_shot"]
        val = v[f"cost_{costs[0]}bps"]["validation"]
        row = {"hypothesis": k, "holdout_cagr": hold["candidate"]["cagr"],
               "holdout_benchmark_cagr": hold["benchmark"]["cagr"],
               "holdout_active_cagr": hold["active_cagr"],
               "holdout_maxdd": hold["candidate"]["max_drawdown"],
               "holdout_benchmark_maxdd": hold["benchmark"]["max_drawdown"],
               "validation_active_cagr": val["active_cagr"],
               "cost_2x_holdout_active_cagr": v[f"cost_{costs[1]}bps"]["untouched_holdout_one_shot"]["active_cagr"],
               "holm_adjusted_p": v["holm_adjusted_p"],
               "passed_count": sum(v["gates"].values()),
               "total_gates": len(v["gates"]),
               "research_verdict": v["research_verdict"],
               **{"gate_" + g: bool(z) for g, z in v["gates"].items()}}
        gate_rows.append(row)
    pd.DataFrame(gate_rows).to_csv(output / "H086_GATES.csv", index=False)
    summary = {
        "study": c["study_id"], "freeze_commit_provenance": "PREREGISTRATION.yaml committed before source acquisition",
        "source_urls": paths, "source_sha256": hashes,
        "pre_registered_candidates": len(by_candidate), "data": meta,
        "performance_proxy": "Fama French CRSP value-weight market; not directly investable",
        "date_splits": c["splits"], "cost_bps_per_oneway_turnover": costs,
        "hypotheses": by_candidate,
        "new_live_accepts": 0, "no_optimization_after_holdout": True,
        "caveat": "Independent external providers, NOT prospective forward observation or vintage-PIT source",
    }
    (output / "H086_COMPLETE_RESULTS.json").write_text(json.dumps(summary, indent=2, default=str))
    md = [
        "# H086 — Independent Dartmouth+Cboe hypothesis freeze and test",
        "", "**Historical independent sources; not future/prospective data. No trading authorization.**", "",
        f"- Source SHA-256: {hashes}", f"- Aligned daily sessions: {len(panel)}; last date: {meta['dates'][1]}.",
        f"- Pre-registered models: {len(by_candidate)}; costs: {costs}bp per 1-way turnover.",
        "", "| Model | Validation active CAGR | Held-out model CAGR | Held-out benchmark CAGR | Active CAGR | 2x cost active CAGR | Holm p | Verdict |",
        "|---|---:|---:|---:|---:|---:|---:|---|"
    ]
    for v in gate_rows:
        md.append(f"| {v['hypothesis']} | {v['validation_active_cagr']:+.2%} | "
                  f"{v['holdout_cagr']:+.2%} | {v['holdout_benchmark_cagr']:+.2%} | "
                  f"{v['holdout_active_cagr']:+.2%} | {v['cost_2x_holdout_active_cagr']:+.2%} | "
                  f"{v['holm_adjusted_p']:.4f} | {v['research_verdict']} |")
    md += [
        "", "All eleven frozen gates are reported individually in H086_GATES.csv.",
        "A failure cannot be repaired by retrospectively modifying model thresholds.",
        "2026-08-31 was frozen as final data date before fetching either independent dataset.",
        "Cboe/French current historical archives can be revised; not point-in-time vintage series.",
        "Daily market-factor proxy does not reproduce broker execution, ETF tracking, liquidity or exact financing.",
    ]
    (output / "H086_FINAL_REPORT.md").write_text("\n".join(md) + "\n")
    print(json.dumps({
        "study": "H086", "freeze_file": "research/h086/PREREGISTRATION.yaml",
        "raw_source_sha256": hashes, "data_end": meta["dates"][1],
        "trading_sessions": len(panel),
        "gates": gate_rows,
        "new_live_accepts": 0,
    }, indent=2))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=Path("results/h086"))
    ap.add_argument("--config", type=Path, default=CONF)
    a = ap.parse_args()
    c = yaml.safe_load(a.config.read_text())
    run(c, a.output)
