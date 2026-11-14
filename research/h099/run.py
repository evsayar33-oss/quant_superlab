"""H099 cross-venue independent strategy trade proxies, read-only."""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"research"/"h096"))
from market import fetch as okx_fetch
from engine import FAMILIES,aggregate
sys.path.insert(0,str(ROOT/"research"/"h098"))
from venues import fetch as venue_fetch,VENUES,ProviderError
from replicate import signals,pair,bootstrap_ci

def emit(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(obj,sort_keys=True,separators=(",",":"))+"\n").encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()

def evaluate(bars,parents,symbol,tf):
    from engine import simulate,exclusive
    sig=signals(bars,parents,symbol,tf)
    out={}
    for fam in FAMILIES:
        for side in ("long","short"):
            for cohort in ("all","htf_aligned"):
                subset=[s for s in sig if s["signal"]["kind"]==fam and s["side"]==side
                        and (cohort=="all" or s["aligned"])]
                # fixed, predeclared 1R and 20 bps; no post-hoc selection
                trades=exclusive([t for s in subset
                                  if (t:=simulate(bars,s,"1R",20.,tf)) is not None])
                out[f"{fam}:{side}:{cohort}"]=trades
    return out

def run(out,pages=8):
    out.mkdir(parents=True,exist_ok=True)
    report={"schema":"H099.independent_trade_proxy.v1","status":"RESEARCH_ONLY",
            "results":{},"errors":{},"sources":{},"alpha_accepted":False,
            "h089_modified":False,"production_modified":False,
            "real_execution_verified":False,"fresh_prospective_verified":False,
            "multiple_testing_corrected":False}
    comparisons=0
    for symbol in ("BTC","ETH"):
        primary={}
        for tf in ("15m","1H","4H"):
            if tf=="4H":continue
            try:
                r=okx_fetch(symbol,tf,pages=pages)
                primary[tf]=r["bars"]
                report["sources"][f"{symbol}_OKX_{tf}"]=emit(out/"sources"/f"{symbol}_OKX_{tf}.json",r)
            except Exception as e:
                report["errors"][f"{symbol}_OKX_{tf}"]=str(e)[:160]
        if "1H" in primary:primary["4H"]=aggregate(primary["1H"],"4H")
        if not all(k in primary for k in ("15m","1H","4H")):continue
        for tf,parent_tf in (("15m","1H"),("1H","4H")):
            try:reference=evaluate(primary[tf],primary[parent_tf],symbol,tf)
            except Exception as e:
                report["errors"][f"{symbol}_{tf}_reference"]=str(e)[:160]
                continue
            for venue in VENUES:
                key=f"{symbol}_{tf}_{venue}"
                try:
                    child=venue_fetch(venue,symbol,tf)
                    if tf=="15m":
                        parent=venue_fetch(venue,symbol,"1H")
                        pb=parent["bars"]
                    else:
                        hour=venue_fetch(venue,symbol,"1H")
                        pb=aggregate(hour["bars"],"4H")
                    if len(pb)<30:raise ValueError("INSUFFICIENT_PARENT_BARS")
                    report["sources"][key]=emit(out/"sources"/f"{key}.json",child)
                    other=evaluate(child["bars"],pb,symbol,tf)
                    result={}
                    for name,a in reference.items():
                        b=other[name]
                        p=pair(a,b)
                        idx={(x["entry_ms"],x["family"],x["side"]):x for x in b}
                        matched=[idx[(x["entry_ms"],x["family"],x["side"])]["net_r"]
                                 for x in a if (x["entry_ms"],x["family"],x["side"]) in idx]
                        p["secondary_bootstrap"]=bootstrap_ci(matched)
                        result[name]=p
                    report["results"][key]={"status":"DESCRIPTIVE_TRADE_PROXY_COMPARISON",
                                            "configs":len(result),
                                            "matched_trades_total":sum(x["matched_n"] for x in result.values()),
                                            "independent_venue":venue,
                                            "source_sha256":report["sources"][key],
                                            "configurations":result,
                                            "alpha_accepted":False}
                    comparisons+=1
                except Exception as e:
                    report["results"][key]={"status":"NOT_VERIFIED_PROVIDER_OR_DATA",
                                            "error_type":type(e).__name__,
                                            "error_category":getattr(e,"category","OTHER"),
                                            "detail":str(e)[:180]}
    report["independent_trade_comparison_sets"]=comparisons
    report["research_gate"]="DESCRIPTIVE_ONLY" if comparisons else "DEGRADED_NO_INDEPENDENT_TRADE_COMPARISONS"
    emit(out/"summary.json",report)
    if report["errors"] or not comparisons:raise SystemExit("H099_INSUFFICIENT_PRIMARY_OR_INDEPENDENT_DATA")
    print(json.dumps({"comparison_sets":comparisons,
                      "matched_trades":sum(v.get("matched_trades_total",0) for v in report["results"].values()),
                      "research_gate":report["research_gate"],"alpha_accepted":False,
                      "errors":report["errors"]},sort_keys=True))
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--pages",type=int,default=8)
    p.add_argument("--out",default="results/h099")
    a=p.parse_args()
    run(ROOT/a.out,a.pages)
