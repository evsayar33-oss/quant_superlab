"""Stateful 30-day forward paper observer; no broker credentials or order placement."""
from __future__ import annotations
import argparse,json,os,sys
from datetime import datetime,timezone
from pathlib import Path
from engine import SCHEMA,VENUES,seed,snapshot,tick,summary
def run(mode,state_path,out,now_ms=None):
 if now_ms is None:now_ms=int(datetime.now(timezone.utc).timestamp()*1000)
 if mode=="start":
  if state_path.exists():raise ValueError("ALREADY_STARTED_NO_RESET")
  state=seed(now_ms)
 elif mode=="tick":
  if not state_path.exists():
   print("NO_ACTIVE_STUDY; scheduled tick skipped");return None
  state=json.loads(state_path.read_text())
 else:raise ValueError("INVALID_MODE")
 if state["schema"]!=SCHEMA:raise ValueError("STATE_SCHEMA")
 if state["finalized"]:
  print("FINALIZED; no further updates");return state
 if state["last_tick_ms"] is not None and now_ms<=state["last_tick_ms"]:
  raise ValueError("REPLAY_OR_NON_MONOTONIC")
 quotes={}
 try:
  for venue in VENUES:quotes[venue]=snapshot(venue,now_ms)
  tick(state,now_ms,quotes)
 except Exception as exc:
  # Preserve prospective outage evidence, no synthetic prices or partial ticks.
  state["outages"].append({"ts":now_ms,"error_type":type(exc).__name__,
    "error":str(exc)[:180],"venues_completed":list(quotes)})
  print("FAIL_CLOSED_OUTAGE:",type(exc).__name__,str(exc),file=sys.stderr)
 state_path.parent.mkdir(parents=True,exist_ok=True)
 state_path.write_text(json.dumps(state,indent=2,sort_keys=True)+"\n")
 out.mkdir(parents=True,exist_ok=True)
 (out/"summary.json").write_text(json.dumps(summary(state),indent=2,sort_keys=True)+"\n")
 (out/"latest_state.json").write_text(json.dumps(state,indent=2,sort_keys=True)+"\n")
 print(json.dumps({"started_ms":state["started_ms"],"ticks":len(state["ticks"]),
   "outages":len(state["outages"]),"trades":len(state["trades"]),
   "positions":len(state["positions"]),"finalized":state["finalized"]}))
 return state
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--mode",choices=("start","tick"),required=True)
 p.add_argument("--state",default="results/h111/state.json")
 p.add_argument("--out",default="results/h111/report")
 a=p.parse_args();run(a.mode,Path(a.state),Path(a.out))
