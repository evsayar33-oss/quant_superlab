"""H088 forward decision snapshot: first seen only; no historic PnL fabrication."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
from evidence import ROOT,append_chain,canonical,stamp,utcnow

WATCH=ROOT/"decisions"/"watch"/"state.json"
OUT=ROOT/"decisions"/"evidence"/"watch_decisions.jsonl"


def capture(now=None,path=WATCH):
    now=now or utcnow()
    f=Path(path)
    if not f.exists():
        return {"schema":"H088.watch.v1","collected_at_utc":stamp(now),
                "kind":"MISSING_WATCH_STATE_NOT_FORWARD_PNL",
                "source_path":"decisions/watch/state.json","source_exists":False,
                "decisions":[]}
    content=f.read_bytes()
    state=json.loads(content)
    if not isinstance(state.get("ideas"),dict):
        raise ValueError("invalid watch schema")
    decisions=[]
    for hid,r in sorted(state["ideas"].items()):
        if not isinstance(r.get("held"),dict) or not r.get("bar"):
            raise ValueError("watch decision missing held or bar")
        bar=str(r["bar"])
        dt=datetime.fromisoformat(bar).replace(tzinfo=timezone.utc)
        if dt>now:raise ValueError("future bar date")
        decisions.append({"id":hid,"source_bar_date":bar,
                          "positions":r["held"],"leverage_pick":r.get("leverage_pick"),
                          "age_days_at_capture":(now-dt).total_seconds()/86400,
                          "stale_gt_3_days":(now-dt).total_seconds()>3*86400})
    return {"schema":"H088.watch.v1","collected_at_utc":stamp(now),
            "kind":"FIRST_SEEN_DECISION_SNAPSHOT_NOT_FORWARD_PNL",
            "source_path":"decisions/watch/state.json","source_exists":True,
            "source_sha256":hashlib.sha256(content).hexdigest(),
            "source_run_date":state.get("date"),"decisions":decisions,
            "all_fresh":bool(decisions) and not any(d["stale_gt_3_days"] for d in decisions)}


def main():
    r=capture()
    digest=append_chain(r,OUT)
    print(canonical({"digest":digest,"source_exists":r["source_exists"],
                     "all_fresh":r.get("all_fresh",False),"decisions":len(r["decisions"])}))
    if not r.get("all_fresh"):
        raise SystemExit("STALE_OR_MISSING_WATCH_DECISION: snapshot retained, not called forward evidence")


if __name__=="__main__":main()
