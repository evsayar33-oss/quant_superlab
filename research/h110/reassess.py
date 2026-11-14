"""Reprice all H109 ledgers; explicitly distinguish executable and hypothetical fills."""
from __future__ import annotations
import argparse,csv,hashlib,json,math
from pathlib import Path
from statistics import mean
SCHEMA="h110.cost_reassessment.v1"
# Fee rates in bps per fill; only taker+taker corresponds to H109 next-open/stop-first proxy.
# Maker cases are counterfactual, not executable with H109 fill assumptions.
PROFILES={
 "taker_base":{"entry_fee":5.0,"exit_fee":5.0,"slippage_roundtrip":2.0,"executable_proxy":True},
 "taker_mid":{"entry_fee":5.0,"exit_fee":5.0,"slippage_roundtrip":6.0,"executable_proxy":True},
 "taker_stress":{"entry_fee":5.0,"exit_fee":5.0,"slippage_roundtrip":10.0,"executable_proxy":True},
 "maker_maker_optimistic":{"entry_fee":2.0,"exit_fee":2.0,"slippage_roundtrip":0.0,"executable_proxy":False},
 "maker_taker_optimistic":{"entry_fee":2.0,"exit_fee":5.0,"slippage_roundtrip":0.0,"executable_proxy":False},
}
def read(path,sha):
 raw=path.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=sha:raise ValueError("SHA256_MISMATCH:"+str(path))
 return json.loads(raw)
def mean_net(trades,bps):
 if not trades:return None
 values=[]
 for t in trades:
  g=float(t["gross_r"]);entry=float(t["entry"]);risk=float(t["risk"])
  if not all(math.isfinite(x) for x in (g,entry,risk)) or entry<=0 or risk<=0:raise ValueError("INVALID_TRADE")
  if not math.isclose(float(t["net_r"]["20"]),g-20/10000*entry/risk,rel_tol=0,abs_tol=1e-8):
   raise ValueError("ORIGINAL_COST_MISMATCH")
  values.append(g-bps/10000*entry/risk)
 return mean(values)
def score(trades,profile,tail_start,train_end):
 bps=profile["entry_fee"]+profile["exit_fee"]+profile["slippage_roundtrip"]
 tail=[t for t in trades if t["entry_ms"]>=tail_start]
 validation=[t for t in trades if t["entry_ms"]>=train_end and t["exit_ms"]<tail_start]
 return {"n":len(trades),"tail_n":len(tail),"validation_n":len(validation),
  "net_mean_r":mean_net(trades,bps),"validation_mean_r":mean_net(validation,bps),
  "tail_mean_r":mean_net(tail,bps),"cost_bps":bps}
def decide(pair):
 if not pair["sample_ok"]:return "INSUFFICIENT_SAMPLE"
 if not pair["base_both_positive"]:return "REJECT_TAKER_BASE"
 if not pair["mid_both_positive"]:return "REJECT_TAKER_MID"
 if not pair["tail_both_positive"]:return "REJECT_HISTORICAL_TAIL"
 if not pair["validation_both_positive"]:return "REJECT_VALIDATION"
 if not pair["stress_both_positive"]:return "SENSITIVITY_WATCH_ONLY"
 return "RESEARCH_WATCHLIST_ONLY"
def run(source,out):
 manifest=json.loads((source/"manifest.json").read_text())
 s=json.loads((source/"summary.json").read_text())
 if s.get("schema")!="h109.one_shot_campaign.v1" or manifest.get("schema")!=s["schema"]:
  raise ValueError("INVALID_H109_SCHEMA")
 if hashlib.sha256((source/"manifest.json").read_bytes()).hexdigest()!=s["manifest_sha256"]:
  raise ValueError("MANIFEST_HASH_MISMATCH")
 trials=read(source/"trials.json",hashlib.sha256((source/"trials.json").read_bytes()).hexdigest())
 if len(trials)!=144 or len(s["paired"])!=72:raise ValueError("INCOMPLETE_TRIAL_MATRIX")
 output={}
 for row in trials:
  tf=row["timeframe"];bounds=manifest["time_windows"][tf]
  trades=read(source/"ledgers"/(row["id"]+".json"),row["ledger_sha256"])
  if len(trades)!=row["full"]["n"]:raise ValueError("COUNT_MISMATCH")
  full={name:score(trades,p,bounds["historical_tail_start_ms"],bounds["train_end_ms"])
        for name,p in PROFILES.items()}
  output[row["id"]]={"id":row["id"],"pair_id":row["pair_id"],"control":row["control"],
    "venue":row["venue"],"profiles":full,"gross_mean_r":row["full"]["gross_mean_r"]}
 pairs=[]
 for old in s["paired"]:
  key=old["id"]
  if old["control"]:
   pairs.append({"id":key,"decision":"CONTROL_EXCLUDED"});continue
  v={venue:output[venue+"_"+key]["profiles"] for venue in ("okx","gate")}
  sample=all(v[venue]["taker_base"]["n"]>=30 and v[venue]["taker_base"]["tail_n"]>=10 for venue in v)
  def both(profile,field="net_mean_r"):
   return all(v[venue][profile][field] is not None and v[venue][profile][field]>0 for venue in v)
  entry={"id":key,"sample_ok":sample,
   "base_both_positive":both("taker_base"),"mid_both_positive":both("taker_mid"),
   "stress_both_positive":both("taker_stress"),
   "tail_both_positive":both("taker_mid","tail_mean_r"),
   "validation_both_positive":both("taker_mid","validation_mean_r"),
   "maker_maker_both_positive":both("maker_maker_optimistic"),
   "venues":{venue:{name:v[venue][name] for name in PROFILES} for venue in v}}
  entry["decision"]=decide(entry);pairs.append(entry)
 from collections import Counter
 counts=dict(Counter(x["decision"] for x in pairs))
 report={"schema":SCHEMA,"source_schema":s["schema"],"source_manifest_sha256":s["manifest_sha256"],
  "profiles":PROFILES,"trial_count":len(output),"paired_count":len(pairs),
  "decision_counts":counts,"pairs":pairs,
  "alpha_accepted":False,"prospective_oos_verified":False,"execution_verified":False,
  "funding_verified":False,"realized_spread_verified":False,"research_only":True,
  "notes":["OKX standard 2bps maker/5bps taker per fill are published reference rates, not user-account verified",
   "Gate rates must be confirmed for specific BTC/ETH perpetual, tier and date; assumed 2/5 bps here",
   "2/6/10 bps roundtrip slippage is sensitivity assumption, not measured spread or L2 execution",
   "H109 next-open entry and stop-first exit imply taker-style execution; maker cases cannot be promoted",
   "Funding, realized spreads, impact and adverse selection are unavailable and not silently assumed zero",
   "Repricing uses the same H109 selected historical trials; it is not independent OOS",
   "No automatic strategy promotion; positive mean alone does not establish robust alpha"]}
 out.mkdir(parents=True,exist_ok=True)
 (out/"summary.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
 (out/"trials.json").write_text(json.dumps(list(output.values()),indent=2,sort_keys=True)+"\n")
 with (out/"matrix.csv").open("w",newline="") as f:
  w=csv.writer(f);w.writerow(["pair_id","decision","sample_ok","taker_base_both_positive",
   "taker_mid_both_positive","taker_stress_both_positive","historical_tail_both_positive",
   "validation_both_positive","maker_hypothetical_both_positive"])
  for x in pairs:w.writerow([x["id"],x["decision"],x.get("sample_ok"),
   x.get("base_both_positive"),x.get("mid_both_positive"),x.get("stress_both_positive"),
   x.get("tail_both_positive"),x.get("validation_both_positive"),x.get("maker_maker_both_positive")])
 (out/"committee.md").write_text("# H110 — Execution-cost reassessment\n\n"
  +"The H109 144 trial ledgers were repriced with explicit assumed fee and slippage profiles. "
  +"Maker-only scenarios are hypothetical; no live fills, funding, or verified spread history.\n\n"
  +"## Decisions\n"+ "".join(f"- {k}: {v}\n" for k,v in sorted(counts.items()))
  +"\n**No alpha accepted.** Candidates marked WATCHLIST require independent future paper trading and measured execution.\n")
 print(json.dumps({"trial_count":len(output),"paired_count":len(pairs),"decisions":counts}))
 return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--source",default="results/h109/campaign")
 p.add_argument("--out",default="results/h110");a=p.parse_args();run(Path(a.source),Path(a.out))
