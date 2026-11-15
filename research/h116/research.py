"""H116: fixed, auditable 4h spot strategy comparison against H054-MOM2.

Public historical Binance OHLC only; research, never live orders.
Signals use completed close t; fills use next open t+1, with turnover costs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from lab import assetdata

SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT")
SMA = (100, 150, 200)
PPY = 365.25 * 6
STEP = pd.Timedelta(hours=4)
START = "2020-01-01"
TEST_START = pd.Timestamp("2021-01-01")
SPLITS = {
    "discovery_2021_22": ("2021-01-01", "2023-01-01"),
    "validation_2023_24": ("2023-01-01", "2025-01-01"),
    "reused_tail_2025_26": ("2025-01-01", "2100-01-01"),
}
# One-way *traded notional* fee+slippage. Not actual account fills.
COST_BPS = (15, 30, 45)
NAMES = (
    "h054_legacy", "h054_mom2", "h054_mom3",
    "four_asset_mom2", "four_asset_mom2_vt50",
    "top1_90d", "top2_90d", "top2_90d_vt50",
    "top2_180d", "top2_btc_regime",
    "trend_ensemble", "breakout_55_20", "top2_drawdown_guard",
)
BASELINE = "h054_mom2"


def validate_source(frame: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Do not quietly forward-fill missing OHLC or tolerate future candles."""
    if not {"Open", "High", "Low", "Close", "Volume"}.issubset(frame.columns):
        raise ValueError(f"{symbol}:MISSING_OHLCV")
    z = frame[["Open", "High", "Low", "Close", "Volume"]].copy()
    z.index = pd.DatetimeIndex(z.index)
    if z.index.tz is not None:
        z.index = z.index.tz_convert("UTC").tz_localize(None)
    if z.index.has_duplicates or not z.index.is_monotonic_increasing:
        raise ValueError(f"{symbol}:BAD_INDEX")
    z = z.loc[z.index + STEP <= pd.Timestamp.now(tz="UTC").tz_localize(None)]
    if z.empty or (z[["Open", "High", "Low", "Close"]] <= 0).any().any():
        raise ValueError(f"{symbol}:NONPOSITIVE_PRICE_OR_EMPTY")
    if not np.isfinite(z.to_numpy(dtype=float)).all():
        raise ValueError(f"{symbol}:NONFINITE_BAR")
    if ((z["Low"] > z[["Open", "Close"]].min(axis=1)) |
            (z["High"] < z[["Open", "Close"]].max(axis=1))).any():
        raise ValueError(f"{symbol}:BAD_OHLC")
    return z


def load_prices(start: str = START) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Load immutable complete Binance spot candles with SHA256 provenance."""
    raw = {}
    for symbol in SYMBOLS:
        data = assetdata.binance_vision(symbol, "4h", start=start)
        if data.empty:
            raise RuntimeError(f"NO_SOURCE:{symbol}")
        raw[symbol] = validate_source(data.loc[data.index >= pd.Timestamp(start)], symbol)
    common_start = max(frame.index[0] for frame in raw.values())
    common_end = min(frame.index[-1] for frame in raw.values())
    if common_end - common_start < pd.Timedelta(days=1500):
        raise RuntimeError("LESS_THAN_1500_DAYS_COMMON_SOURCE")
    span = pd.date_range(common_start, common_end, freq="4h")
    metadata = {}
    for symbol, frame in raw.items():
        frame = frame.loc[common_start:common_end]
        if not frame.index.equals(span):
            absent = len(span.difference(frame.index))
            raise ValueError(f"{symbol}:GAP_OR_MISALIGNED_BARS:{absent}")
        raw[symbol] = frame
        digest = hashlib.sha256(pd.util.hash_pandas_object(frame, index=True).values.tobytes()).hexdigest()
        metadata[symbol] = {"first": str(frame.index[0]), "last": str(frame.index[-1]),
                            "bars": len(frame), "sha256_ohlcv": digest}
    opens = pd.DataFrame({s: raw[s]["Open"] for s in SYMBOLS}, index=span)
    closes = pd.DataFrame({s: raw[s]["Close"] for s in SYMBOLS}, index=span)
    return opens, closes, metadata


def banded(raw: pd.DataFrame, band: float = 0.10) -> pd.DataFrame:
    """The exact original H054 idea: suppress churn unless abs(delta) > band."""
    values = raw.fillna(0).clip(0, 1).to_numpy(dtype=float)
    out = np.zeros_like(values)
    active = np.zeros(values.shape[1])
    for i, proposed in enumerate(values):
        change = (np.abs(proposed - active) > band) | ((proposed == 0) & (active != 0))
        active = np.where(change, proposed, active)
        out[i] = active
    return pd.DataFrame(out, index=raw.index, columns=raw.columns)


def make_weights(closes: pd.DataFrame) -> dict[str, pd.DataFrame]:
    if not set(SYMBOLS).issubset(closes.columns):
        raise ValueError("MISSING_MARKET")
    if closes.isna().any().any() or (closes <= 0).any().any():
        raise ValueError("PRICE_GAPS")
    returns = closes.pct_change(fill_method=None)
    vol = returns.rolling(180, min_periods=90).std() * math.sqrt(PPY)
    score90 = closes.pct_change(90 * 6, fill_method=None)
    score180 = closes.pct_change(180 * 6, fill_method=None)
    above = {d: closes > closes.rolling(d * 6, min_periods=d * 6).mean()
             for d in SMA}
    votes = sum((closes > closes.shift(h * 6)).astype(int) for h in (30, 90, 180))
    valid = (vol > 1e-8) & above[200]
    holdings = {}

    def target(vote: int, vt: float = 0.40, universe=SYMBOLS):
        eligible = valid & (votes >= vote)
        w = ((vt / vol).clip(upper=1.0)).where(eligible, 0).fillna(0)
        mask = [s for s in universe]
        result = pd.DataFrame(0., index=closes.index, columns=SYMBOLS)
        result[mask] = w[mask] / len(mask)
        return banded(result)

    pair = SYMBOLS[:2]
    holdings["h054_legacy"] = target(1, universe=pair)
    holdings["h054_mom2"] = target(2, universe=pair)
    holdings["h054_mom3"] = target(3, universe=pair)
    holdings["four_asset_mom2"] = target(2)
    holdings["four_asset_mom2_vt50"] = target(2, vt=0.50)

    def rotation(name, score, k=2, vt=0.40, regime=None):
        eligible = valid & (votes >= 2) & score.notna()
        scores = score.where(eligible)
        ranks = scores.rank(axis=1, ascending=False, method="first")
        chosen = ranks <= k
        w = (vt / vol).clip(upper=1).where(chosen, 0).fillna(0) / k
        if regime is not None:
            w = w.where(regime, 0.)
        holdings[name] = banded(w)

    rotation("top1_90d", score90, k=1)
    rotation("top2_90d", score90)
    rotation("top2_90d_vt50", score90, vt=0.50)
    rotation("top2_180d", score180)
    btc_risk = above[200]["BTCUSDT"] & (score90["BTCUSDT"] > 0)
    rotation("top2_btc_regime", score90, regime=btc_risk)

    ensemble = ((above[100].astype(int) + above[150].astype(int) +
                 above[200].astype(int)) >= 2) & (votes >= 2)
    en = (0.40 / vol).clip(upper=1).where(ensemble, 0).fillna(0) / 4
    holdings["trend_ensemble"] = banded(en)

    # Breakout is stateful: completed-close break above *previous* 55-day high,
    # remain exposed until close breaks *previous* 20-day low.
    high55 = closes.rolling(55 * 6, min_periods=55 * 6).max().shift(1)
    low20 = closes.rolling(20 * 6, min_periods=20 * 6).min().shift(1)
    breakout = pd.DataFrame(0., index=closes.index, columns=SYMBOLS)
    for sym in SYMBOLS:
        active = False
        for i in range(len(closes)):
            if active and (closes[sym].iloc[i] < low20[sym].iloc[i] or
                           not bool(above[200][sym].iloc[i])):
                active = False
            elif (not active and bool(above[200][sym].iloc[i]) and
                  closes[sym].iloc[i] > high55[sym].iloc[i]):
                active = True
            if active:
                breakout.iat[i, breakout.columns.get_loc(sym)] = 1.
    holdings["breakout_55_20"] = banded(
        (0.40 / vol).clip(upper=1).where(breakout > 0, 0).fillna(0) / 4)

    # Risk circuit based only on *past* BTC closes, not on future drawdown.
    btc_drawdown = closes["BTCUSDT"] / closes["BTCUSDT"].rolling(30 * 6).max() - 1
    risk_on = (btc_drawdown > -0.18) & btc_risk
    rotation("top2_drawdown_guard", score90, regime=risk_on)

    if tuple(holdings) != NAMES:
        raise AssertionError("PREREGISTERED_CANDIDATE_SET_CHANGED")
    for name, w in holdings.items():
        if w.isna().any().any() or (w < -1e-9).any().any() or (w.sum(axis=1) > 1.000001).any():
            raise ValueError(f"{name}:INVALID_LONG_CASH_ALLOCATION")
    return holdings


def simulate(opens: pd.DataFrame, weights: pd.DataFrame, side_bps: int) -> pd.DataFrame:
    if side_bps < 0:
        raise ValueError("INVALID_COST")
    if not opens.index.equals(weights.index) or not opens.columns.equals(weights.columns):
        raise ValueError("UNALIGNED_EXECUTION_INPUTS")
    # W(close t-1) trades at next open t; PnL from open t to open t+1.
    current = weights.shift(1).iloc[1:-1].copy()
    o2o = (opens.shift(-1) / opens - 1).iloc[1:-1]
    turnover = current.diff().abs()
    turnover.iloc[0] = current.iloc[0].abs()
    traded = turnover.sum(axis=1)
    gross = (current * o2o).sum(axis=1)
    net = gross - traded * (side_bps / 10000)
    # Closing the account incurs a final liquidation fee.
    net.iloc[-1] -= current.iloc[-1].abs().sum() * (side_bps / 10000)
    if not np.isfinite(net.to_numpy()).all() or (net <= -1).any():
        raise ValueError("INVALID_NET_RETURNS")
    return pd.DataFrame({"net": net, "gross": gross, "turnover": traded,
                         "exposure": current.sum(axis=1)}, index=current.index).loc[TEST_START:]


def stats(ledger: pd.DataFrame) -> dict:
    if ledger.empty:
        return {"bars": 0, "return_pct": None}
    r = ledger["net"].to_numpy(float)
    nav = np.cumprod(1 + r)
    peaks = np.maximum.accumulate(np.concatenate(([1.], nav)))[1:]
    dd = nav / peaks - 1
    sd = float(np.std(r, ddof=1))
    return {"bars": len(r), "return_pct": round(float((nav[-1] - 1) * 100), 3),
            "max_dd_pct": round(float(np.min(dd) * 100), 3),
            "sharpe": round(float(np.mean(r) / sd * math.sqrt(PPY)), 3) if sd > 1e-12 else None,
            "turnover": round(float(ledger["turnover"].sum()), 3),
            "active_bars": int((ledger["exposure"] > 1e-9).sum())}


def paired_monthly_ci(candidate: pd.DataFrame, base: pd.DataFrame, seed: int = 116) -> list[float] | None:
    """Descriptive monthly paired excess bootstraps; NOT prospective alpha proof."""
    aligned = candidate["net"].to_frame("x").join(base["net"].rename("b"), how="inner")
    if len(aligned) < 360:
        return None
    monthly = aligned.groupby(aligned.index.to_period("M")).apply(
        lambda z: float((1 + z["x"]).prod() - (1 + z["b"]).prod())).to_numpy(float)
    if len(monthly) < 12:
        return None
    rng = np.random.default_rng(seed)
    samples = rng.choice(monthly, size=(2000, len(monthly)), replace=True).mean(axis=1)
    return [round(float(x * 100), 4) for x in np.percentile(samples, [2.5, 97.5])]


def analyze(opens: pd.DataFrame, closes: pd.DataFrame, meta: dict) -> tuple[dict, list[dict], dict]:
    candidates = make_weights(closes)
    ledgers = {}
    rows = []
    for name in NAMES:
        for cost in COST_BPS:
            ledger = simulate(opens, candidates[name], cost)
            ledgers[(name, cost)] = ledger
            slices = {period: stats(ledger.loc[a:pd.Timestamp(b) - STEP])
                      for period, (a, b) in SPLITS.items()}
            rows.append({"name": name, "cost_bps_per_side": cost,
                         "full": stats(ledger), "splits": slices})
    match = {(x["name"], x["cost_bps_per_side"]): x for x in rows}
    base = match[(BASELINE, 15)]
    winners = []
    for name in NAMES:
        if name in ("h054_legacy", BASELINE):
            continue
        x = match[(name, 15)]
        high = match[(name, 30)]
        b30 = match[(BASELINE, 30)]
        dd = x["full"]["max_dd_pct"]
        better = (x["full"]["return_pct"] > base["full"]["return_pct"]
                  and high["full"]["return_pct"] > b30["full"]["return_pct"]
                  and x["splits"]["validation_2023_24"]["return_pct"] >
                  base["splits"]["validation_2023_24"]["return_pct"]
                  and x["splits"]["reused_tail_2025_26"]["return_pct"] >
                  base["splits"]["reused_tail_2025_26"]["return_pct"]
                  and dd >= base["full"]["max_dd_pct"] - 5)
        if better:
            winners.append(name)
        x["paired_monthly_excess_ci95_pct"] = paired_monthly_ci(
            ledgers[(name, 15)], ledgers[(BASELINE, 15)])
    winners.sort(key=lambda name: match[(name, 15)]["full"]["return_pct"], reverse=True)
    summary = {
        "schema": "h116.spot_profit_discovery.v1",
        "research_only": True,
        "alpha_accepted": False,
        "production_bot_modified": False,
        "source": "Binance Vision public spot archived 4h OHLCV",
        "history": meta,
        "fixed_candidates": list(NAMES),
        "model_count": len(NAMES),
        "scenario_count": len(rows),
        "baseline": BASELINE,
        "baseline_15bps": base,
        "qualified_historical_candidates": winners,
        "target_total_return_pct": 200.,
        "hit_200pct_base_cost": [
            n for n in NAMES if match[(n, 15)]["full"]["return_pct"] >= 200
        ],
        "holding": "long/cash only, total exposure <= 1, no leverage",
        "evaluation": "as-of completed 4h close t-1 -> next 4h open t; open-to-next-open NAV",
        "costs_bps_per_traded_side": list(COST_BPS),
        "windows": SPLITS,
        "statistical_limitations": [
            "Reused exposed historical 2025-2026 tail, NOT untouched OOS",
            "Single venue; cross-venue execution/fill parity UNVERIFIED",
            "No funding hedge or verified borrow/funding premium",
            "No maker fill probability, spreads, impact or taxes",
            "Spot assets selected from currently surviving listed symbols",
            "Monthly bootstrap descriptive, no multiple-test alpha approval",
        ],
    }
    return summary, rows, ledgers


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="results/h116")
    args = p.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    opens, closes, provenance = load_prices()
    summary, rows, ledgers = analyze(opens, closes, provenance)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False))
    (out / "matrix.json").write_text(json.dumps(rows, indent=2, allow_nan=False))
    pd.DataFrame([
        {"name": r["name"], "cost_bps": r["cost_bps_per_side"],
         "period": period, **metrics}
        for r in rows for period, metrics in
        [("full", r["full"]), *list(r["splits"].items())]
    ]).to_csv(out / "matrix.csv", index=False)
    for name in NAMES:
        ledgers[(name, 15)].to_csv(out / f"nav_{name}_15bps.csv")
    lines = [
        "# H116 — 4h Spot strategy discovery (NOT live-trading approval)",
        f"Historical cost-stressed configurations: {len(rows)}",
        f"Qualifying historical improvements vs MOM2: {', '.join(summary['qualified_historical_candidates']) or 'NONE'}",
        f"Hit +200% nominal historical threshold: {', '.join(summary['hit_200pct_base_cost']) or 'NONE'}",
        "All return claims are historical, single-venue and explicitly NOT untouched OOS.",
    ]
    (out / "committee.md").write_text("\n\n".join(lines) + "\n")
    print(json.dumps({key: summary[key] for key in ("model_count", "scenario_count",
         "qualified_historical_candidates", "hit_200pct_base_cost")}, indent=2))


if __name__ == "__main__":
    main()
