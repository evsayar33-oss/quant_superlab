import copy
import unittest
from research.portfolio_qualification.ear_adaptive import validate, digest

DAY=86_400_000
RULE={"market":"CRYPTO","direction":"UP","terms":[["x",True]],"operator":"all"}

def row(i,case,flag,kind="FIRST_SEEN"):
    day=(10+i//30)*DAY
    ret=15 if case else 0
    bars=[{"start":day+2+j*900000,"end":day+2+(j+1)*900000,
           "open":100,"high":100+(ret if j==15 else 0),"low":100,"close":100+(ret if j==15 else 0),"volume":20} for j in range(16)]
    return {"id":str(i),"market":"CRYPTO","symbol":str(i%37),"kind":kind,
            "anchor":day,"seen":day+1,"features":{"x":flag},"liquidity":"M",
            "outcome":{"status":"COMPLETE_MARK_ONLY","entry":day+2,"end":bars[-1]["end"],
              "entry_open":100,"exit_close":100+ret,"gross_pct":ret,"up_pct":ret,
              "down_pct":0,"label":"UP" if case else "NONE","bars_sha":digest(bars),"bars":bars}}

class TestEarAdaptive(unittest.TestCase):
    def test_recomputed_and_no_accept(self):
        rows=[row(d*30+i,i<3,i<3) for d in range(15) for i in range(30)]
        result=validate(RULE,rows,stage="DISCOVERY",n_trials=1)
        self.assertEqual(result["tp"],45)
        self.assertEqual(result["fp"],0)
        self.assertEqual(result["verdict"],"SCREEN_PASSED")
        self.assertFalse(result["paper_approved"])
        self.assertEqual(result["official_gate"],"NOT_RUN")
    def test_wrong_label_and_return_rejected(self):
        r=row(1,True,True)
        r["outcome"]["gross_pct"]=20
        with self.assertRaisesRegex(ValueError,"RETURN_MISMATCH"):
            validate(RULE,[r],stage="DISCOVERY",n_trials=1)
        r=row(1,True,True);r["outcome"]["label"]="NONE"
        with self.assertRaisesRegex(ValueError,"EVENT_LABEL_MISMATCH"):
            validate(RULE,[r],stage="DISCOVERY",n_trials=1)
    def test_holdout_leak_and_missing_coverage(self):
        r=row(1,True,True,"HISTORICAL_DISCOVERY")
        lock={"rule":RULE,"start":0,"end":100*DAY}
        with self.assertRaisesRegex(ValueError,"HOLDOUT_LEAK"):
            validate(RULE,[r],stage="FORWARD",n_trials=1,lock=lock)
        r=row(1,True,None)
        self.assertEqual(validate(RULE,[r],stage="DISCOVERY",n_trials=1)["valid"],0)
    def test_duplicate_rejected(self):
        r=row(1,True,True)
        with self.assertRaisesRegex(ValueError,"DUPLICATE"):
            validate(RULE,[r,r],stage="DISCOVERY",n_trials=1)
if __name__=="__main__":unittest.main()
