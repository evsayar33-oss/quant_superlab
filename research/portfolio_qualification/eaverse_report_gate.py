"""Common independent Eaverse report passport and cohort arithmetic. No approval."""
import argparse
import json
import math
from pathlib import Path
from . import gate, eaverse_bridge, eaverse_coverage

SCHEMA="QS.eaverse.report_gate.v3"
REPORTS={
 "eaverse.early_flow_hourly.v1":"results",
 "eaverse.extended_flow.v7.1":"results",
 "eaverse.pit_replay_result.v1":"discoveries",
 "eaverse.causal_discovery_queue.v8":"designs",
 "eaverse.pit_integrity_audit.v9":"results",
 "eaverse.equity_source_assurance.v1":"sources",
 "eaverse.cross_venue_reference.v1":"sources",
 "eaverse.v7.aligned_empirical_trials.v1":None,
}
digest=eaverse_coverage.digest

def review_report(report, *, label=None):
    schema=report.get("schema")
    key=REPORTS.get(schema)
    registered=schema in REPORTS
    records=report.get(key,[]) if key else []
    if isinstance(records,dict):
        records=[{"source_name":k,"record":v} for k,v in records.items()]
    if not isinstance(records,list):
        raise ValueError("BAD_REPORT_RECORDS")
    if not records:
        records=[{"report_only":True,"label":label or schema}]
    source=digest(report)
    policy=report.get("policy") or {"schema":schema,"report_type":label}
    receipts=[]
    for row in records:
        if not isinstance(row,dict):
            raise ValueError("BAD_REPORT_ROW")
        for flag in ("paper_eligible","live_allowed","live_authorized","trade_authorized","paper_approved"):
            if row.get(flag) is True or report.get(flag) is True:
                raise ValueError("UNAUTHORIZED_PROMOTION_IN_SOURCE_REPORT")
        passport={"source_repository":eaverse_coverage.REPO,
                  "hypothesis_id":str(row.get("id") or digest(row)),
                  "strategy_definition":json.dumps(row.get("spec",row),sort_keys=True),
                  "methodology_sha256":digest(policy),"source_evidence_sha256":source,
                  "benchmark":"not independently verified","read_only_research":True}
        receipts.append({"id":passport["hypothesis_id"],"gate":gate.review(passport)})
    return {"schema":SCHEMA,"source_schema":schema,"source_sha256":source,
            "registered_schema":registered,"classification":"KNOWN_SCHEMA_BLOCKED" if registered else "UNMAPPED_REPORT_BLOCKED",
            "records":receipts,"central_lab_accept":False,"paper_approved":False,"live_allowed":False}

def review_cohort(cohort):
    panel=cohort["panel"]
    if panel["sha256"]!=digest({k:v for k,v in panel.items() if k!="sha256"}):
        raise ValueError("COHORT_HASH_MISMATCH")
    dates,ids,values,train=panel["dates"],panel["ids"],panel["returns"],panel["train_weeks"]
    if len(dates)!=len(values) or dates!=sorted(set(dates)) or len(ids)!=len(set(ids)) or len(ids)<2:
        raise ValueError("COHORT_ALIGNMENT")
    if not 0<train<len(dates) or any(len(row)!=len(ids) or any(not math.isfinite(x) or x < -1 for x in row) for row in values):
        raise ValueError("COHORT_PATH")
    selected=max(range(len(ids)),key=lambda i:eaverse_bridge._sharpe([row[i] for row in values[:train]]))
    if ids[selected]!=cohort["selected_id"]:
        raise ValueError("COHORT_SELECTION_MISMATCH")
    pbo=eaverse_bridge.reproduce_pbo(values)
    dsr=eaverse_bridge.reproduce_dsr(values,selected,train,cohort["trial_count"])
    if (None if pbo is None else pbo["pbo"])!=cohort["pbo"]:
        raise ValueError("COHORT_PBO_MISMATCH")
    if dsr!=cohort["dsr"]:
        raise ValueError("COHORT_DSR_MISMATCH")
    passport={"source_repository":eaverse_coverage.REPO,"hypothesis_id":cohort["selected_id"],
              "strategy_definition":json.dumps(cohort["selected_spec"],sort_keys=True),
              "methodology_sha256":cohort["methodology_sha256"],"source_evidence_sha256":panel["sha256"],
              "benchmark":"cash only; not independently matched","read_only_research":True}
    return {"pbo":pbo,"dsr":dsr,"gate":gate.review(passport),"independent_arithmetic":True,
            "central_lab_accept":False,"paper_approved":False,"live_allowed":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    if a.input.stat().st_size>32*1024*1024:
        raise ValueError("REPORT_LIMIT")
    result=review_report(json.loads(a.input.read_text()),label=a.input.name)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,sort_keys=True,allow_nan=False))
    print(result["classification"],len(result["records"]))

if __name__=="__main__":
    main()
