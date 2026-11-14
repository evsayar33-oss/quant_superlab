import hashlib,json,tempfile,unittest
from pathlib import Path
from audit import read_checked,summarize,audit
class Tests(unittest.TestCase):
    def test_sha(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.json";p.write_text("[]")
            self.assertEqual(read_checked(p,hashlib.sha256(b"[]").hexdigest()),[])
            with self.assertRaisesRegex(ValueError,"SHA256_MISMATCH"):read_checked(p,"bad")
    def test_bootstrap_reproducible(self):
        trades=[{"net_r":{"20":x}} for x in (-1,0,1,2)]
        self.assertEqual(summarize(trades),summarize(trades))
        self.assertEqual(summarize(trades)["n"],4)
    def test_empty(self):
        self.assertIsNone(summarize([])["mean_r"])
    def test_schema_guard(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/"summary.json").write_text('{"schema":"wrong"}')
            with self.assertRaisesRegex(ValueError,"WRONG_SCHEMA"):audit(p,p/"out.json")
if __name__=="__main__":unittest.main()
