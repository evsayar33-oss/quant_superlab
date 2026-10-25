"""Where could H063-H065 be traded with an API? Checks free public market lists (no keys, no orders).

  python -m lab.venues   -> decisions/watch/venues.json + venues.md

Searched: Bitget USDT-M futures, Binance USDT-M futures, Hyperliquid (native + builder dexes).
A venue that cannot be reached from GitHub Actions (geo block, error) is reported as unreachable.
"""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "decisions" / "watch"

# asset of the paper watch -> name patterns that would mean the same underlying on a crypto venue
ASSETS = {
    "GC=F": ("gold", r"^(XAU|GOLD|PAXG|XAUT)"), "SI=F": ("silver", r"^(XAG|SILVER)"),
    "HG=F": ("copper", r"^(XCU|COPPER|HG)"), "PL=F": ("platinum", r"^(XPT|PLATINUM)"),
    "PA=F": ("palladium", r"^(XPD|PALLADIUM)"),
    "ES=F": ("S&P 500", r"^(SPX|SP500|US500|SPY|ES)"), "NQ=F": ("Nasdaq 100", r"^(NDX|NAS100|NASDAQ|US100|QQQ|NQ|XYZ100)"),
    "YM=F": ("Dow Jones", r"^(DJI|US30|DOW|YM)"), "RTY=F": ("Russell 2000", r"^(RUT|US2000|IWM|RTY)"),
    "NKD=F": ("Nikkei 225", r"^(NIKKEI|JP225|NKY|N225)"),
}


def _get(url: str, body: dict | None = None, timeout: int = 30):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "quant_lab", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def bitget() -> list[str]:
    d = _get("https://api.bitget.com/api/v2/mix/market/contracts?productType=USDT-FUTURES")
    return [x["symbol"] for x in d.get("data", []) if x.get("symbolStatus", "normal") == "normal"]


def binance() -> list[str]:
    d = _get("https://fapi.binance.com/fapi/v1/exchangeInfo")
    return [x["symbol"] for x in d.get("symbols", []) if x.get("status") == "TRADING"]


def hyperliquid() -> list[str]:
    out = [f"{u['name']}" for u in _get("https://api.hyperliquid.xyz/info", {"type": "meta"}).get("universe", [])]
    dexs = _get("https://api.hyperliquid.xyz/info", {"type": "perpDexs"}) or []
    for dx in dexs:
        if not dx or not dx.get("name"):
            continue
        try:
            m = _get("https://api.hyperliquid.xyz/info", {"type": "meta", "dex": dx["name"]})
            out += [u["name"] if ":" in u["name"] else f"{dx['name']}:{u['name']}" for u in m.get("universe", [])]
        except Exception:  # noqa: BLE001
            continue
    return out


def check() -> dict:
    res = {"date": date.today().isoformat(), "venues": {}, "assets": {}}
    lists = {}
    for name, fn in (("bitget", bitget), ("binance", binance), ("hyperliquid", hyperliquid)):
        try:
            lists[name] = fn()
            res["venues"][name] = {"reachable": True, "n_markets": len(lists[name])}
        except Exception as e:  # noqa: BLE001
            res["venues"][name] = {"reachable": False, "error": str(e)[:200]}
    for t, (label, pat) in ASSETS.items():
        rx = re.compile(pat, re.I)
        hit = {}
        for v, syms in lists.items():
            m = [s for s in syms if rx.search(s.split(":")[-1])]
            if m:
                hit[v] = m[:6]
        res["assets"][t] = {"name": label, "markets": hit}
    return res


def markdown(o: dict) -> str:
    L = ["# İşlem yeri kontrolü (H063–H065)", "", f"Tarih: {o['date']}. Sadece herkese açık market listeleri okundu; anahtar yok, emir yok.", "",
         "| Borsa | Erişim | Market sayısı |", "|---|---|---|"]
    for v, x in o["venues"].items():
        L.append(f"| {v} | {'evet' if x['reachable'] else 'HAYIR: ' + x.get('error', '')[:80]} | {x.get('n_markets', '—')} |")
    L += ["", "| Paper varlığı | Dayanak | Bulunan marketler |", "|---|---|---|"]
    for t, x in o["assets"].items():
        m = "; ".join(f"{v}: {', '.join(s)}" for v, s in x["markets"].items()) or "**bulunamadı**"
        L.append(f"| {t} | {x['name']} | {m} |")
    L += ["", "Not: isim eşleşmesi otomatik yapıldı. Canlıya geçmeden önce her marketin dayanağı, kontrat büyüklüğü, "
          "işlem saatleri, funding ve Türkiye'den erişim tek tek doğrulanmalı. Bulunamayan varlık (ör. bakır) canlıda işlenemez; "
          "o varlık paper sonucundan çıkarılıp tekrar hesaplanmalı."]
    return "\n".join(L) + "\n"


def main():
    o = check()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "venues.json").write_text(json.dumps(o, indent=1))
    md = markdown(o)
    (OUT / "venues.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
