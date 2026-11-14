"""H102: fixed-scope economic diagnostics; no parameter search or alpha approval."""
import argparse, hashlib, json, math, statistics
from collections import defaultdict
from pathlib import Path

def analyze(source, out):
    source=Path(source); out=Path(out)
    summary_path=source/"summary.json"
    if not summary_path.is_file(): raise ValueError("H102_H101_SUMMARY_MISSING")
    summary=json.loads(summary_path.read_text())
    if summary.get("alpha_accepted") is not False or summary.get("real_execution_cost_verified") is not False:
        raise ValueError("H102_UNEXPECTED_SOURCE_STATUS")
    manifests=summary.get("sources",{})
    groups=defaultdict(list)
    hashes={}
    for path in sorted((source/"trade_ledgers").glob("*.json")):
        key=path.stem
        if key not in summary.get("venue_results",{}): raise ValueError("H102_UNKNOWN_LEDGER")
        raw=path.read_bytes()
        digest=hashlib.sha256(raw).hexdigest()
        expected=summary["venue_results"][key].get("ledger_sha256")
        if expected!=digest: raise ValueError("H102_LEDGER_HASH_MISMATCH:"+key)
        hashes[key]=digest
        trades=json.loads(raw)
        for t in trades:
            if not isinstance(t,dict): raise ValueError("H102_BAD_TRADE")
            risk=float(t["risk_price"]); entry=float(t["entry_price"])
            if not (math.isfinite(risk) and math.isfinite(entry) and risk>0 and entry>0):
                raise ValueError("H102_INVALID_RISK")
            cost20=float(t["net_r_20bps"]); cost40=float(t["net_r_40bps"]); cost80=float(t["net_r_80bps"])
            if not all(math.isfinite(v) for v in (cost20,cost40,cost80)):
                raise ValueError("H102_NONFINITE_R")
            unit=entry/risk/10000
            gross=cost20+20*unit
            if abs((gross-40*unit)-cost40)>1e-7 or abs((gross-80*unit)-cost80)>1e-7:
                raise ValueError("H102_COST_INCONSISTENCY")
            symbol,tf,venue=key.split("_")
            groups[(symbol,tf,venue,t["config"])].append({
                "gross_r":gross,"cost20_r":cost20,"cost40_r":cost40,"cost80_r":cost80,
                "cost_per_bp_r":unit,"duration_minutes":(int(t["exit_ms"])-int(t["entry_ms"]))/60000,
                "entry_ms":int(t["entry_ms"]),"tail":bool(t["historical_tail"]),
                "exit_cause":t.get("stop_first_exit_cause","UNKNOWN")})
    rows=[]
    for (symbol,tf,venue,config),trades in sorted(groups.items()):
        n=len(trades)
        def avg(k,items=trades): return statistics.fmean(x[k] for x in items) if items else None
        gross=avg("gross_r"); perbp=avg("cost_per_bp_r")
        # Maximum assumed round-trip cost that leaves mean R at zero; negative => no positive-cost break-even.
        break_even=gross/perbp if perbp>0 else None
        tail=[x for x in trades if x["tail"]]
        causes={c:sum(t["exit_cause"]==c for t in trades) for c in sorted({t["exit_cause"] for t in trades})}
        rows.append({"symbol":symbol,"timeframe":tf,"venue":venue,"config":config,"n":n,
          "gross_mean_r":gross,"net_mean_r_20bps":avg("cost20_r"),
          "net_mean_r_40bps":avg("cost40_r"),"net_mean_r_80bps":avg("cost80_r"),
          "cost_drag_20bps_r":gross-avg("cost20_r"),
          "break_even_roundtrip_bps":break_even,
          "median_duration_minutes":statistics.median(t["duration_minutes"] for t in trades),
          "exit_causes":causes,"tail_n":len(tail),
          "tail_net_mean_r_20bps":avg("cost20_r",tail),
          "eligible_n30":n>=30,"tail_eligible_n30":len(tail)>=30,
          "descriptive_only":True})
    families=defaultdict(list)
    for r in rows:
        if r["n"]>=30:
            families[r["config"].split(":")[0]].append(r)
    family_report=[]
    for family,items in sorted(families.items()):
        family_report.append({"family":family,"eligible_venue_cells":len(items),
            "gross_positive_cells":sum(r["gross_mean_r"]>0 for r in items),
            "net20_positive_cells":sum(r["net_mean_r_20bps"]>0 for r in items),
            "net80_positive_cells":sum(r["net_mean_r_80bps"]>0 for r in items),
            "median_break_even_bps":statistics.median(r["break_even_roundtrip_bps"] for r in items)})
    report={"schema":"h102.economic_diagnostics.v1","status":"RESEARCH_ONLY",
      "source_summary_sha256":hashlib.sha256(summary_path.read_bytes()).hexdigest(),
      "source_ledger_sha256":hashes,"source_manifest_count":len(manifests),
      "source_errors":summary.get("venue_errors",{}),
      "analyzed_venue_config_cells":len(rows),"eligible_n30_cells":sum(r["eligible_n30"] for r in rows),
      "gross_positive_eligible_cells":sum(r["eligible_n30"] and r["gross_mean_r"]>0 for r in rows),
      "net20_positive_eligible_cells":sum(r["eligible_n30"] and r["net_mean_r_20bps"]>0 for r in rows),
      "family_diagnostics":family_report,"cells":rows,
      "candidate_families_for_future_preregistration":[
        {"family":"medium_term_trend_following","hypothesis":"lower_turnover","status":"UNTESTED"},
        {"family":"volatility_expansion_breakout","hypothesis":"larger_move_per_trade","status":"UNTESTED"},
        {"family":"cross_asset_relative_strength","hypothesis":"different_signal_source","status":"UNTESTED"}],
      "alpha_accepted":False,"prospective_oos_verified":False,
      "real_execution_cost_verified":False,"multiple_testing_adjusted":False,
      "research_complete":False,
      "limitations":["Overlapping trades and venues are statistically dependent",
       "Historical-tail data is reused and not prospective OOS",
       "Assumed cost scenarios are not measured fills, funding or impact",
       "New families are preregistration ideas, not backtested strategies"]}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",default="results/h101")
    p.add_argument("--out",default="results/h102/diagnostics.json")
    a=p.parse_args()
    result=analyze(a.source,a.out)
    print(json.dumps({k:result[k] for k in ("analyzed_venue_config_cells","eligible_n30_cells","gross_positive_eligible_cells","net20_positive_eligible_cells","alpha_accepted")},sort_keys=True))
