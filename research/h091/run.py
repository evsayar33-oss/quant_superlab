"""H091-H094 real-source read-only discovery runner.

Writes an Actions *artifact*, not main decisions or bot inputs. Never assert
profitability from one venue, tiny sample or already-researched historical bars.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path
from datetime import datetime,timezone

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
sys.path.insert(0,str(ROOT/"research"/"h091"))
sys.path.insert(0,str(ROOT/"research"/"h094"))
from market import fetch_okx,save_snapshot
from baseline import research
from gates import classify,coverage


def run(symbols:list[str],out:Path,pages:int=12)->dict:
    out.mkdir(parents=True,exist_ok=True)
    records=[];gates=[];errors={};source_manifest=[]
    for symbol in symbols:
        try:
            raw=fetch_okx(symbol,pages=pages)
            path=save_snapshot(raw,out/"market")
            source_manifest.append(path)
            result=research(raw["bars"],symbol)
            result["independent_price_source_count"]=raw["independent_price_source_count"]
            result["input_sha256"]=path["sha256"]
            result["input_gaps"]=len(raw["gaps"])
            result["market_retrieved_at_utc"]=raw["retrieved_at_utc"]
            result["data_earliest_utc"]=raw["earliest_utc"]
            result["data_latest_utc"]=raw["latest_utc"]
            result["price_reference_type"]="OKX_USDT_SWAP_BAR_PROXY_NOT_FILL"
            verdict=classify(result)
            records.append(result);gates.append(verdict)
            (out/(symbol+"_exploratory.json")).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
            (out/(symbol+"_evidence_gate.json")).write_text(json.dumps(verdict,indent=2,sort_keys=True)+"\n")
        except Exception as e:
            errors[symbol]={"error_type":type(e).__name__,"detail":str(e)[:400],
                            "status":"NOT_TESTABLE_REAL_PROVIDER_OR_DATA_ERROR"}
    report=coverage(records,gates)
    report["retrieved_at_utc"]=datetime.now(timezone.utc).isoformat()
    report["sources"]=source_manifest
    report["errors"]=errors
    report["requested_symbols"]=symbols
    report["real_input_verified"]=len(records)>0
    report["research_complete"]=False
    report["real_strategy_proof_complete"]=False
    (out/"program.json").write_text(json.dumps(report,indent=2,sort_keys=True,default=list)+"\n")
    summary=["# H091–H094 — Independent Research Evidence", "",
             "**Exploratory only: NO live orders, NO ACCEPT, NO new proven alpha.**","",
             f"Real public OKX snapshots: {len(records)}/{len(symbols)} assets.",
             f"Test variants (not independent trials): {report['trials']}.",
             "Historical 70/30 cut is descriptive; these dates are NOT untouched holdout.",
             "Costs modeled: 10 bps round-trip assumed, actual spread/funding/slippage unverified.",
             "Concurrent signals are NOT portfolio-NAV-tested.",
             "Source quality: one venue; independent validation required.",""]
    for v,g in zip(records,gates):
        summary.append(f"## {v['symbol']}")
        summary.append(f"Period: {v['data_earliest_utc']} — {v['data_latest_utc']}.")
        summary.append(f"Variants: {v['trial_count']}; >=30 hold sample: {v['trials_with_30_hold_entries']}.")
        summary.append(f"Gate: {g['verdict']}; missing {', '.join(g['reasons'])}.")
    if errors:
        summary.extend(["","## Source or input failures",""])
        for k,v in errors.items():summary.append(f"- {k}: {v['error_type']} — {v['detail']}")
    (out/"SUMMARY.md").write_text("\n".join(summary)+"\n")
    return report


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--symbols",nargs="+",choices=["BTC","ETH"],default=["BTC","ETH"])
    ap.add_argument("--pages",type=int,default=12)
    ap.add_argument("--out",default="results/h091_h094")
    args=ap.parse_args()
    result=run(args.symbols,ROOT/args.out,args.pages)
    print(json.dumps({"symbols":result["symbols"],"errors":result["errors"],
                      "trials":result["trials"],"research_complete":False,
                      "production_registry_modified":False},sort_keys=True))
    if result["errors"] or not result["real_input_verified"]:
        raise SystemExit("INCOMPLETE_RESEARCH_SOURCE: report preserved, no invented result")


if __name__=="__main__":main()
