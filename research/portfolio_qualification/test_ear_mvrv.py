import hashlib,json,unittest
from research.portfolio_qualification.ear_mvrv import validate
def sample():
 r={"schema":"EAR.v18.mvrv_combinations.v1","asset":"btc","split":{"discovery_end":"2023-01-01","validation_start":"2023-01-02"},"combination_count":12,"combination_results":[{"rule":str(i)} for i in range(12)],"paper_eligible":False,"trade_authorized":False};canonical=json.dumps(r,sort_keys=True,separators=(",",":"),allow_nan=False);r["superlab_evidence"]={"schema":"QS.external_research_evidence.v1","producer":"early_accumulation_radar","study":"real_mvrv_combinations","payload_sha256":hashlib.sha256(canonical.encode()).hexdigest(),"producer_verdict":"RESEARCH_ONLY","quant_superlab_verdict":"NOT_EVALUATED","automatic_promotion":False};return r
class EarMvrvIntakeTests(unittest.TestCase):
 def test_valid_contract_stays_not_evaluated(self): self.assertEqual(validate(sample())["official_gate"],"NOT_RUN")
 def test_tamper_and_permission_escalation_fail(self):
  r=sample();r["asset"]="eth"
  with self.assertRaisesRegex(ValueError,"DIGEST"):validate(r)
  r=sample();r["paper_eligible"]=True;canonical=json.dumps({k:v for k,v in r.items() if k!="superlab_evidence"},sort_keys=True,separators=(",",":"),allow_nan=False);r["superlab_evidence"]["payload_sha256"]=hashlib.sha256(canonical.encode()).hexdigest()
  with self.assertRaisesRegex(ValueError,"PERMISSION"):validate(r)
