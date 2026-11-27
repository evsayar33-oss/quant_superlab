"""Strict intake contract for Early Radar real-MVRV combination evidence."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
def validate(report):
    if report.get("schema")!="EAR.v18.mvrv_combinations.v1": raise ValueError("EAR_MVRV_SCHEMA")
    evidence=report.get("superlab_evidence",{})
    required={"schema":"QS.external_research_evidence.v1","producer":"early_accumulation_radar","study":"real_mvrv_combinations","producer_verdict":"RESEARCH_ONLY","quant_superlab_verdict":"NOT_EVALUATED","automatic_promotion":False}
    if any(evidence.get(k)!=v for k,v in required.items()): raise ValueError("EAR_MVRV_UNTRUSTED_EVIDENCE")
    payload=dict(report);payload.pop("superlab_evidence",None)
    canonical=json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False);digest=hashlib.sha256(canonical.encode()).hexdigest()
    if evidence.get("payload_sha256")!=digest: raise ValueError("EAR_MVRV_DIGEST_MISMATCH")
    if report.get("paper_eligible") is not False or report.get("trade_authorized") is not False: raise ValueError("EAR_MVRV_PERMISSION_ESCALATION")
    if report.get("combination_count")!=len(report.get("combination_results",[])) or report.get("combination_count")!=12: raise ValueError("EAR_MVRV_COMBINATION_COVERAGE")
    if report["split"]["discovery_end"]>=report["split"]["validation_start"]: raise ValueError("EAR_MVRV_NON_CHRONOLOGICAL")
    return {"schema":"QS.external_research_receipt.v1","producer":"early_accumulation_radar","study":"real_mvrv_combinations","asset":report["asset"],"payload_sha256":digest,"combination_count":12,"quant_superlab_verdict":"NOT_EVALUATED","official_gate":"NOT_RUN","paper_eligible":False,"trade_authorized":False}
def main():
    p=argparse.ArgumentParser();p.add_argument("report",nargs="+");p.add_argument("--out",required=True);a=p.parse_args()
    receipts=[validate(json.loads(Path(x).read_text())) for x in a.report];Path(a.out).write_text(json.dumps({"schema":"QS.ear_mvrv_receipts.v1","receipts":receipts},indent=2,sort_keys=True)+"\n");print("QS_EAR_MVRV_INTAKE_OK",len(receipts),"NOT_EVALUATED")
if __name__=="__main__":main()
