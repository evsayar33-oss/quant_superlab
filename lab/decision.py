"""Decision registry: the single source of truth the trading bots read.

Each validation writes decisions/parts/<id>.json (parallel jobs never collide).
merge() builds decisions/registry.json:
{
  "updated": "...",
  "hypotheses": {"H001": {"verdict": "ACCEPT", "targets": {...}, "params": {...}, ...}},
  "systems":   {"bist_orderflow_quant": {"approved": ["H001", ...],
                                         "allocation": {"H001": 0.6, "H013": 0.4},
                                         "method": "hrp"}}
}
Live tracking (lab/live.py) can demote an ACCEPT to DEGRADED; bots act only on ACCEPT.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DEC = ROOT / "decisions"
PARTS = DEC / "parts"
REG = DEC / "registry.json"
HISTORY = DEC / "history.csv"
LIVE_STATUS = DEC / "live_status.json"


def load() -> dict:
    if REG.exists():
        return json.loads(REG.read_text())
    return {"updated": None, "hypotheses": {}, "systems": {}}


def record(hid: str, meta: dict, report: dict, targets: dict, oos_csv: str | None = None) -> dict:
    prev = load()["hypotheses"].get(hid, {}).get("verdict")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    entry = {
        "verdict": report["verdict"],
        "previous_verdict": prev,
        "reasons": report["reasons"],
        "strategy": meta.get("strategy") or meta.get("rule"),
        "kind": report["kind"],
        "universe": meta["universe"],
        "timeframe": report.get("timeframe", "1d"),
        "for_system": meta.get("for_system"),
        "spec": {k: v for k, v in meta.items() if k not in ("note",)},
        "variant": report["final_variant"],
        "params": report["final_params"],
        "targets": targets if report["verdict"] == "ACCEPT" else {},
        "targets_observe_only": targets,
        "gate_sharpe": report.get("gate_sharpe"),
        "pbo": report["pbo"],
        "reality_check_p": report.get("reality_check_p"),
        "dsr": report["dsr"],
        "n_trials": report["n_trials"],
        "oos": report["oos"],
        "trade_stats": report["trade_stats"],
        "regimes": report["regimes"],
        "robustness": report.get("robustness"),
        "protection_rules_passed": [k for k, v in ((report.get("protection") or {}).get("tests") or {}).items()
                                    if v.get("pass")],
        "recommended_overlay": (report.get("studies") or {}).get("overlays", {}).get("best_by_calmar"),
        "kelly_fraction": (report.get("trade_stats") or {}).get("kelly_fraction"),
        "oos_csv": oos_csv,
        "validated_at": now,
        "accepted_at": now if report["verdict"] == "ACCEPT" and prev != "ACCEPT" else None,
        "data_end": report["data_end"],
    }
    PARTS.mkdir(parents=True, exist_ok=True)
    old = PARTS / f"{hid}.json"
    if old.exists() and entry["accepted_at"] is None and report["verdict"] == "ACCEPT":
        entry["accepted_at"] = json.loads(old.read_text()).get("accepted_at") or now
    old.write_text(json.dumps(entry, indent=2, ensure_ascii=False, default=str))
    new = not HISTORY.exists()
    with HISTORY.open("a") as f:
        if new:
            f.write("validated_at,id,strategy,universe,timeframe,verdict,gate_sharpe,dsr,pbo,oos_cagr,oos_maxdd\n")
        o = report["oos"]
        f.write(f"{now},{hid},{entry['strategy']},{meta['universe']},{entry['timeframe']},{entry['verdict']},"
                f"{entry['gate_sharpe']},{report['dsr']},{report['pbo']},{o.get('cagr')},{o.get('max_dd')}\n")
    return entry


def _hrp(R: pd.DataFrame) -> pd.Series:
    """Hierarchical Risk Parity (Lopez de Prado 2016), small-sample friendly."""
    from scipy.cluster.hierarchy import leaves_list, linkage
    from scipy.spatial.distance import squareform
    cov, corr = R.cov(), R.corr().fillna(0)
    if R.shape[1] == 1:
        return pd.Series(1.0, index=R.columns)
    dist = np.sqrt(np.clip((1 - corr) / 2, 0, 1))
    order = list(R.columns[leaves_list(linkage(squareform(dist.values, checks=False), "single"))])
    w = pd.Series(1.0, index=order)
    clusters = [order]
    while clusters:
        nxt = []
        for cl in clusters:
            if len(cl) < 2:
                continue
            a, b = cl[: len(cl) // 2], cl[len(cl) // 2:]

            def var(c):
                cv = cov.loc[c, c].values
                iv = 1 / np.diag(cv)
                iv /= iv.sum()
                return float(iv @ cv @ iv)
            va, vb = var(a), var(b)
            alpha = 1 - va / (va + vb)
            w[a] *= alpha; w[b] *= 1 - alpha
            nxt += [a, b]
        clusters = nxt
    return w / w.sum()


def merge() -> dict:
    hyps = {}
    for f in sorted(PARTS.glob("*.json")):
        hyps[f.stem] = json.loads(f.read_text())
    live = json.loads(LIVE_STATUS.read_text()) if LIVE_STATUS.exists() else {}
    for hid, st in live.items():
        if hid in hyps and hyps[hid]["verdict"] == "ACCEPT" and st.get("degraded"):
            hyps[hid]["verdict"] = "DEGRADED"
            hyps[hid]["reasons"] = hyps[hid]["reasons"] + [f"live tracking: {st.get('why')}"]
            hyps[hid]["targets"] = {}
        if hid in hyps:
            hyps[hid]["live"] = st
    systems: dict = {}
    for hid, h in hyps.items():
        if h["verdict"] == "ACCEPT" and h.get("for_system"):
            systems.setdefault(h["for_system"], []).append(hid)
    sys_out = {}
    for sysname, ids in systems.items():
        rets = {}
        for hid in ids:
            p = hyps[hid].get("oos_csv")
            if p and (ROOT / p).exists():
                rets[hid] = pd.read_csv(ROOT / p, index_col=0, parse_dates=True).iloc[:, 0]
        method, alloc = "equal", {hid: round(1 / len(ids), 4) for hid in ids}
        if len(rets) == len(ids) and len(ids) > 1:
            R = pd.DataFrame(rets).dropna(how="all").fillna(0.0)
            if len(R) > 60:
                alloc = {k: round(float(v), 4) for k, v in _hrp(R).items()}
                method = "hrp"
                corr = R.corr().round(2).to_dict()
            else:
                corr = None
        else:
            corr = None
        sys_out[sysname] = {"approved": ids, "allocation": alloc, "method": method, "correlation": corr}
    reg = {"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "hypotheses": hyps, "systems": sys_out}
    REG.write_text(json.dumps(reg, indent=2, ensure_ascii=False, default=str))
    return reg
