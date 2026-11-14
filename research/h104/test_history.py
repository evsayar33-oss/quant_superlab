import unittest
from datetime import datetime,timezone
from history import HOUR,canonical,gate_history,manifest
class HistoryTests(unittest.TestCase):
    def b(self,t,p=100):return {"ts":t,"open":p,"high":p+1,"low":p-1,"close":p}
    def test_dedup_and_gap(self):
        rows,gaps=canonical([self.b(0),self.b(0),self.b(2*HOUR)])
        self.assertEqual(len(rows),2)
        self.assertEqual(gaps[0]["missing_bars"],1)
    def test_conflicting_overlap_rejected(self):
        with self.assertRaisesRegex(ValueError,"CONFLICTING_OVERLAP"):
            canonical([self.b(0),self.b(0,101)])
    def test_out_of_window_rejected(self):
        now=datetime.fromtimestamp(48*3600,tz=timezone.utc)
        def fake(url):return [{"t":0,"o":"100","h":"101","l":"99","c":"100"}]
        with self.assertRaisesRegex(ValueError,"GATE_OUT_OF_WINDOW"):
            gate_history("BTC",1,get=fake,now=now,page_size=2,max_pages=1)
    def test_pagination_and_manifest(self):
        now=datetime.fromtimestamp(48*3600,tz=timezone.utc)
        calls=[]
        def fake(url):
            from urllib.parse import urlparse,parse_qs
            q=parse_qs(urlparse(url).query);lo=int(q["from"][0]);hi=int(q["to"][0]);calls.append((lo,hi))
            return [{"t":t,"o":"100","h":"101","l":"99","c":"100"}
                    for t in range(lo,hi+1,3600)]
        p=gate_history("BTC",1,get=fake,now=now,page_size=10,max_pages=3)
        self.assertEqual(len(p["bars"]),24)
        self.assertTrue(p["complete_window"])
        self.assertEqual(p["pages"],3)
        self.assertEqual(manifest(p)["gap_count"],0)
        self.assertEqual(calls[0][0],24*3600)
    def test_incomplete_page_budget(self):
        now=datetime.fromtimestamp(48*3600,tz=timezone.utc)
        def fake(url):
            from urllib.parse import urlparse,parse_qs
            q=parse_qs(urlparse(url).query);lo=int(q["from"][0]);hi=int(q["to"][0])
            return [{"t":t,"o":"100","h":"101","l":"99","c":"100"} for t in range(lo,hi+1,3600)]
        p=gate_history("ETH",1,get=fake,now=now,page_size=10,max_pages=1)
        self.assertFalse(p["complete_window"])
if __name__=="__main__":unittest.main()
