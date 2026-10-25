"""Free, point-in-time fundamental data.

BIST : Is Yatirim public MaliTablo endpoint (same source as bist_orderflow_quant).
       Turkish income-statement items are year-to-date; TTM is rebuilt as
       TTM(y,q) = YTD(y,q) + FY(y-1) - YTD(y-1,q). Availability = period end + 75 days
       (quarter) / 100 days (annual), so the backtest never sees a report before it is public.
US   : SEC EDGAR XBRL "companyfacts" API (free, full history since ~2009).
       Availability = the real filing date ("filed"). The FIRST filed value for a period is
       used, so later restatements cannot leak into the past.
       Set env SEC_USER_AGENT="name email" (SEC asks for a contact in the User-Agent).

Output: dict[field] -> wide daily frame (dates x tickers), forward-filled from availability.
Fields: net_income, revenue, op_profit, gross_profit, cfo, equity, total_assets, fin_debt,
        cur_assets, cur_liab, shares
"""
from __future__ import annotations

import json
import os
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

CACHE = Path(__file__).resolve().parent.parent / "data" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)
UA = os.environ.get("SEC_USER_AGENT", "quant_lab research bot (github actions)")

# ============================================================== BIST (Is Yatirim)
ISY_URL = "https://www.isyatirim.com.tr/_layouts/15/IsYatirim.Website/Common/Data.aspx/MaliTablo"
ISY_GROUPS = ["XI_29", "UFRS"]
LAG_Q, LAG_A = 75, 100
PATTERNS = {
    "net_income": {"exact": ["donem net kari veya zarari", "net donem kari veya zarari", "net donem kari/zarari",
                             "donem kari (zarari)", "net profit after taxes", "net profit", "net income"],
                   "contains": ["net donem kar", "donem net kar", "net profit"]},
    "equity": {"exact": ["ozkaynaklar", "toplam ozkaynaklar", "ana ortakliga ait ozkaynaklar",
                         "shareholders equity", "total equity"], "contains": ["ozkaynaklar", "equity"]},
    "revenue": {"exact": ["satis gelirleri", "hasilat", "net satislar", "net sales", "revenue", "sales"],
                "contains": ["satis gelir", "hasilat", "net sales"]},
    "op_profit": {"exact": ["faaliyet kari veya zarari", "esas faaliyet kari veya zarari", "faaliyet kari",
                            "operating profit", "operating income"], "contains": ["faaliyet kar", "operating profit"]},
    "gross_profit": {"exact": ["brut kar (zarar)", "brut kar veya zarar", "ticari faaliyetlerden brut kar (zarar)",
                               "gross profit"], "contains": ["brut kar", "gross profit"]},
    "total_assets": {"exact": ["toplam varliklar", "varliklar toplami", "total assets"],
                     "contains": ["toplam varlik", "total assets"]},
    "cur_assets": {"exact": ["donen varliklar", "current assets"], "contains": ["donen varlik"]},
    "cur_liab": {"exact": ["kisa vadeli yukumlulukler", "short term liabilities", "current liabilities"],
                 "contains": ["kisa vadeli yukumluluk"]},
    "paid_in": {"exact": ["odenmis sermaye", "paid-in capital", "paid in capital", "sermaye"],
                "contains": ["odenmis sermaye", "paid-in capital"]},
}
DEBT_EXACT = ["finansal borclar", "financial liabilities", "financial loans", "borrowings"]
FLOWS = ["net_income", "revenue", "op_profit", "gross_profit"]


def _norm(s) -> str:
    s = str(s or "").strip().lower().replace("ı", "i").replace("İ", "i")
    s = unicodedata.normalize("NFKD", s)
    return " ".join("".join(ch for ch in s if not unicodedata.combining(ch)).split())


def _num(v):
    try:
        x = float(str(v).replace(",", "")) if isinstance(v, str) else float(v)
        return x if np.isfinite(x) else np.nan
    except Exception:  # noqa: BLE001
        return np.nan


def _isy_extract(rows, k):
    descs = [(_norm(r.get("itemDescTr")), _norm(r.get("itemDescEng")), r) for r in rows]
    out = {}
    for concept, pat in PATTERNS.items():
        val = np.nan
        for mode in ("exact", "contains"):
            for pt in pat[mode]:
                for tr, en, r in descs:
                    hit = (tr == pt or en == pt) if mode == "exact" else (pt in tr or pt in en)
                    if hit and np.isfinite(_num(r.get(f"value{k}"))):
                        val = _num(r.get(f"value{k}"))
                        break
                if np.isfinite(val):
                    break
            if np.isfinite(val):
                break
        out[concept] = val
    debt = [_num(r.get(f"value{k}")) for tr, en, r in descs if tr in DEBT_EXACT or en in DEBT_EXACT]
    debt = [d for d in debt if np.isfinite(d)]
    out["fin_debt"] = float(np.sum(debt)) if debt else np.nan
    return out


def _isy_fetch(code: str, years: list[int]) -> pd.DataFrame:
    import requests

    recs, group = [], None
    for y in sorted(years, reverse=True):
        params = {"companyCode": code, "exchange": "TRY"}
        for i, pr in enumerate([12, 9, 6, 3], start=1):
            params[f"year{i}"], params[f"period{i}"] = y, pr
        rows = []
        for g in ([group] if group else ISY_GROUPS):
            try:
                r = requests.get(ISY_URL, params={**params, "financialGroup": g},
                                 headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
                r.raise_for_status()
                rows = r.json().get("value", []) or []
            except Exception:  # noqa: BLE001
                rows = []
            if rows and any(np.isfinite(_num(x.get("value1"))) for x in rows):
                group = g
                break
        for i, pr in enumerate([12, 9, 6, 3], start=1):
            v = _isy_extract(rows, i) if rows else {}
            if v and any(np.isfinite(x) for x in v.values()):
                recs.append({"code": code, "year": y, "period": pr, **v})
        time.sleep(0.1)
    return pd.DataFrame(recs)


def _isy_pit(raw: pd.DataFrame) -> pd.DataFrame:
    """Long table: ticker, field, value, avail_date (TTM flows)."""
    out = []
    for code, g in raw.groupby("code"):
        g = g.drop_duplicates(["year", "period"], keep="last").set_index(["year", "period"]).sort_index()
        for (y, pr), r in g.iterrows():
            end = pd.Timestamp(f"{y}-{pr:02d}-01") + pd.offsets.MonthEnd(0)
            avail = end + pd.Timedelta(days=LAG_A if pr == 12 else LAG_Q)
            vals = {}
            for f in FLOWS:
                cur = r[f]
                if pr == 12:
                    vals[f] = cur
                else:
                    vals[f] = cur + g[f].get((y - 1, 12), np.nan) - g[f].get((y - 1, pr), np.nan)
            for f in ("equity", "fin_debt", "total_assets", "cur_assets", "cur_liab"):
                vals[f] = r[f]
            vals["shares"] = r["paid_in"]  # nominal 1 TL per share -> paid-in capital = share count
            for f, v in vals.items():
                if np.isfinite(v):
                    out.append((f"{code}.IS", f, float(v), avail, end))
    return pd.DataFrame(out, columns=["ticker", "field", "value", "avail", "period_end"])


def bist_long(tickers: list[str], start_year: int = 2008) -> pd.DataFrame:
    cache = CACHE / "fund_bist_raw.csv"
    raw = pd.read_csv(cache) if cache.exists() else pd.DataFrame(columns=["code", "year", "period"])
    this = pd.Timestamp.now().year
    codes = [t.replace(".IS", "") for t in tickers if t.endswith(".IS") and not t.startswith("XU")]
    jobs = {}
    for c in codes:
        have = raw[raw["code"] == c]
        jobs[c] = list(range(start_year - 1, this + 1)) if have.empty else list(range(this - 1, this + 1))
    with ThreadPoolExecutor(6) as ex:
        parts = list(ex.map(lambda kv: _isy_fetch(*kv), jobs.items()))
    parts = [p for p in parts if not p.empty]
    if parts:
        raw = pd.concat([raw, *parts], ignore_index=True).drop_duplicates(["code", "year", "period"], keep="last")
        raw.to_csv(cache, index=False)
    return _isy_pit(raw[raw["code"].isin(codes)]) if not raw.empty else pd.DataFrame()


# ============================================================== US (SEC EDGAR)
SEC_MAP = {
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"],
    "op_profit": ["OperatingIncomeLoss"],
    "gross_profit": ["GrossProfit"],
    "cfo": ["NetCashProvidedByUsedInOperatingActivities"],
    "equity": ["StockholdersEquity"],
    "total_assets": ["Assets"],
    "fin_debt": ["LongTermDebt", "LongTermDebtNoncurrent"],
    "cur_assets": ["AssetsCurrent"],
    "cur_liab": ["LiabilitiesCurrent"],
}
FLOW_US = {"net_income", "revenue", "op_profit", "gross_profit", "cfo"}


def _sec_get(url: str):
    import requests
    r = requests.get(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"}, timeout=30)
    r.raise_for_status()
    time.sleep(0.12)  # SEC fair-access: < 10 requests / second
    return r.json()


def _cik_map() -> dict:
    p = CACHE / "sec_tickers.json"
    if p.exists() and time.time() - p.stat().st_mtime < 30 * 86400:
        return json.loads(p.read_text())
    j = _sec_get("https://www.sec.gov/files/company_tickers.json")
    m = {v["ticker"].upper(): int(v["cik_str"]) for v in j.values()}
    p.write_text(json.dumps(m))
    return m


def _sec_facts(ticker: str, cik: int) -> pd.DataFrame:
    p = CACHE / f"sec_{ticker}.json"
    if p.exists() and time.time() - p.stat().st_mtime < 7 * 86400:
        j = json.loads(p.read_text())
    else:
        j = _sec_get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json")
        p.write_text(json.dumps(j))
    gaap = j.get("facts", {}).get("us-gaap", {})
    rows = []
    for field, concepts in SEC_MAP.items():
        got = []
        for cpt in concepts:
            for u in gaap.get(cpt, {}).get("units", {}).get("USD", []):
                if field in FLOW_US:
                    if u.get("form") not in ("10-K", "10-K/A") or u.get("fp") != "FY" or not u.get("start"):
                        continue
                    dur = (pd.Timestamp(u["end"]) - pd.Timestamp(u["start"])).days
                    if not 340 <= dur <= 380:
                        continue
                elif u.get("form") not in ("10-K", "10-Q", "10-K/A", "10-Q/A"):
                    continue
                got.append((u["end"], u["filed"], u["val"]))
            if got:
                break
        if not got:
            continue
        df = pd.DataFrame(got, columns=["end", "filed", "val"]).sort_values("filed")
        df = df.drop_duplicates("end", keep="first")  # first-reported value only (no restatement leak)
        for _, r in df.iterrows():
            rows.append((ticker, field, float(r["val"]), pd.Timestamp(r["filed"]), pd.Timestamp(r["end"])))
    dei = j.get("facts", {}).get("dei", {}).get("EntityCommonStockSharesOutstanding", {}).get("units", {})
    for u in dei.get("shares", []):
        rows.append((ticker, "shares", float(u["val"]), pd.Timestamp(u["filed"]), pd.Timestamp(u["end"])))
    return pd.DataFrame(rows, columns=["ticker", "field", "value", "avail", "period_end"])


def us_long(tickers: list[str]) -> pd.DataFrame:
    try:
        m = _cik_map()
    except Exception as e:  # noqa: BLE001
        print(f"[fund] SEC ticker map failed: {e}")
        return pd.DataFrame()
    parts = []
    for t in tickers:
        cik = m.get(t.upper().replace("-", "."), m.get(t.upper()))
        if not cik:
            continue
        try:
            parts.append(_sec_facts(t, cik))
        except Exception as e:  # noqa: BLE001
            print(f"[fund] SEC {t}: {e}")
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


# ============================================================== panel builder
def to_panels(long: pd.DataFrame, index: pd.DatetimeIndex, tickers: list[str]) -> dict[str, pd.DataFrame]:
    """Wide daily frames: value known on each date (forward-filled from availability)."""
    out = {}
    if long is None or long.empty:
        return out
    for f, g in long.groupby("field"):
        g = g.sort_values(["avail", "period_end"]).drop_duplicates(["ticker", "avail"], keep="last")
        w = g.pivot(index="avail", columns="ticker", values="value")
        w = w.reindex(w.index.union(index)).sort_index().ffill(limit=500).reindex(index)
        out[f] = w.reindex(columns=tickers)
    # previous-year values for growth / change factors (same field, 1 year earlier, still point-in-time)
    for f in ("revenue", "net_income", "total_assets", "gross_profit", "cfo", "cur_assets", "cur_liab",
              "fin_debt", "shares", "equity"):
        if f in out:
            out[f + "_1y"] = out[f].shift(252)
    return out


def load(tickers: list[str], index: pd.DatetimeIndex, market: str) -> dict[str, pd.DataFrame]:
    try:
        if market == "bist":
            long = bist_long(tickers, start_year=max(index[0].year - 1, 2005))
        elif market in ("us", "multi"):
            long = us_long([t for t in tickers if "." not in t or t.endswith("-B")])
        else:
            return {}
    except Exception as e:  # noqa: BLE001 - fundamentals are optional; price research continues
        print(f"[fund] load failed: {e}")
        return {}
    p = to_panels(long, index, tickers)
    cov = {k: round(float(v.notna().mean().mean()), 2) for k, v in p.items() if not k.endswith("_1y")}
    print(f"[fund] coverage {cov}")
    return p
