"""Pure-offline archive integrity contracts; live probes run separately."""
from __future__ import annotations
import csv
import hashlib
import io
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from research.source_discovery.probe import parse_binance,parse_bist


def binance_zip():
    buffer=io.StringIO()
    w=csv.writer(buffer)
    first=datetime(2021,1,1,tzinfo=timezone.utc)
    for h in range(24):
        t=int((first+timedelta(hours=h)).timestamp()*1000)
        w.writerow([t,"100","105","99","102","1",
                    t+3600000-1,"100000","50","0.3","50000","0"])
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w") as z:
        z.writestr("BTCUSDT-1h-2021-01-01.csv",buffer.getvalue())
    return out.getvalue()


def bist_csv():
    out=io.StringIO()
    w=csv.writer(out)
    w.writerow(["year","snapshot_date","ticker","name","index","delisted_in_year"])
    for d in range(110):
        date=f"{2000+d//4:04d}-{(d%4)*3+1:02d}-01"
        for ticker in range(202):
            idx="XU030" if ticker<30 else (
                "XU050" if ticker<50 else ("XU100" if ticker<100 else ""))
            w.writerow([2000+d//4,date,
                        f"TK{(d*202+ticker)%700:04d}","dummy",idx,"False"])
    return out.getvalue().encode()


class HistoricalProbeTests(unittest.TestCase):
    def test_zip_checksum_and_hourly_taker_columns(self):
        data=binance_zip()
        checksum=(hashlib.sha256(data).hexdigest()+"   file.zip\n").encode()
        z=parse_binance(data,checksum)
        self.assertEqual(z["observations"],24)
        self.assertTrue(z["has_taker_buy_quote_volume"])
        self.assertFalse(z["validated_alpha"])

    def test_archive_mismatch_and_corrupt_ohlc_rejected(self):
        data=binance_zip()
        with self.assertRaisesRegex(ValueError,"CHECKSUM"):
            parse_binance(data,b"f"*64)
        self.assertNotEqual(hashlib.sha256(data).hexdigest(),"0"*64)

    def test_bist_quarter_tiers_and_delisted_prices_never_inferred(self):
        z=parse_bist(bist_csv())
        self.assertEqual(z["historical_review_dates"],110)
        self.assertEqual(z["complete_30_20_50_tier_snapshots"],110)
        self.assertFalse(z["contains_delisted_member_prices"])
        self.assertFalse(z["official_vintage_crosscheck_completed"])

    def test_bist_bad_ticker_fails_instead_of_silent_drop(self):
        x=bist_csv().replace(b"TK0000",b"UNKNOWN_SYMBOL_VALUE_OVER_THE_24_CHAR_LIMIT",1)
        with self.assertRaisesRegex(ValueError,"BAD_TICKER"):
            parse_bist(x)


if __name__=="__main__":
    unittest.main()
