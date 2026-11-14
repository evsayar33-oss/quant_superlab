"""Synthetic regression: integrity, causality, stop precedence and whole workflow."""
import hashlib,json,math,tempfile,unittest
from pathlib import Path
from campaign_core import HOUR,aggregate,validate,indicators,signal,simulate,btc_regime,evaluate
from campaign_stats import metrics,time_splits,weekly_bootstrap,bh,pair_decision
from campaign_run import run,load

def sample(n=240,base=100):
    result=[]
    for i in range(n):
        p=base+i*.018+3*math.sin(i/15)
        result.append({"ts":i*HOUR,"open":p,"high":p+1,
                       "low":p-1,"close":p+.2})
    return result

class CampaignTests(unittest.TestCase):
    def test_bad_ohlc_rejected(self):
        b=sample();b[1]["high"]=b[1]["low"]
        with self.assertRaisesRegex(ValueError,"BAD_OHLC"):validate(b)
    def test_duplicate_timestamp_rejected(self):
        b=sample();b[10]["ts"]=b[9]["ts"]
        with self.assertRaisesRegex(ValueError,"BAD_TIMESTAMP"):validate(b)
    def test_strict_four_hour(self):
        b=sample()
        self.assertEqual(len(aggregate(b)),60)
        b.pop(2);self.assertEqual(len(aggregate(b)),59)
    def test_no_future_lookahead(self):
        b=sample(300);d=indicators(b,HOUR)
        current=[signal("trend_cross","long",b,i,d[i]) for i in range(74,140)]
        for r in b[140:]:r["close"]=r["open"]+.5
        e=indicators(b,HOUR)
        self.assertEqual(current,[signal("trend_cross","long",b,i,e[i]) for i in range(74,140)])
    def test_gap_invalidates_signal(self):
        b=sample(300);b[150]["ts"]+=HOUR//2
        d=indicators(b,HOUR)
        self.assertIsNone(d[150])
        self.assertIsNotNone(d[240])
    def test_stop_first(self):
        b=sample(230)
        b[100]["high"]=b[100]["open"]+8
        b[100]["low"]=b[100]["open"]-8
        t=simulate(b,100,"long",1,HOUR)
        self.assertEqual(t["cause"],"STOP")
        self.assertAlmostEqual(t["gross_r"],-1)
    def test_censor_incomplete_horizon(self):
        self.assertIsNone(simulate(sample(200),190,"long",1,HOUR))
    def test_chronological_purge(self):
        t={"entry_ms":100*HOUR,"exit_ms":110*HOUR,"gross_r":1,
           "net_r":{str(x):1 for x in (0,10,20,40,80,120)},"cause":"TIME"}
        x=time_splits([t],105*HOUR,120*HOUR)
        self.assertEqual(x["purged_cross_boundary"],1)
    def test_bootstrap_determinism(self):
        t=[{"entry_ms":w*7*24*HOUR,"net_r":{"40":.1 if w%2 else -.1}} for w in range(10)]
        self.assertEqual(weekly_bootstrap(t,100),weekly_bootstrap(t,100))
    def test_bh(self):
        q=bh([("a",.01),("b",.025),("c",.5),("missing",None)])
        self.assertAlmostEqual(q["a"],.03)
        self.assertIsNone(q["missing"])
    def test_controls_excluded(self):
        self.assertEqual(pair_decision({"control":True}),"CONTROL_EXCLUDED")
    def test_empty_returns_none(self):
        self.assertIsNone(metrics([])["net_mean_r"]["40"])
    def test_end_to_end_synthetic_no_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/"h104";(source/"bars").mkdir(parents=True)
            sources={}
            for symbol in ("BTC","ETH"):
                for venue in ("okx","gate"):
                    key=f"{symbol}_{venue}";bars=sample(95*24,base=200 if symbol=="BTC" else 100)
                    if venue=="gate":
                        for row in bars:
                            for f in ("open","high","low","close"):row[f]*=1.0001
                    data=json.dumps(bars).encode()
                    (source/"bars"/f"{key}.json").write_bytes(data)
                    sources[key]={"bars_sha256":hashlib.sha256(data).hexdigest(),"gap_count":0}
            (source/"summary.json").write_text(json.dumps({"schema":"h104.long_history.v1","sources":sources}))
            out=root/"campaign";r=run(source,out)
            self.assertEqual(r["venue_level_trials"],144)
            self.assertEqual(r["paired_candidates"],72)
            self.assertFalse(r["alpha_accepted"])
            self.assertTrue((out/"matrix.csv").exists())
            self.assertTrue((out/"committee.md").exists())
            self.assertEqual(len(json.loads((out/"trials.json").read_text())),144)
            sources["BTC_gate"]["bars_sha256"]="invalid"
            (source/"summary.json").write_text(json.dumps({"schema":"h104.long_history.v1","sources":sources}))
            with self.assertRaisesRegex(ValueError,"H104_SHA256_MISMATCH"):load(source)

if __name__=="__main__":unittest.main()
