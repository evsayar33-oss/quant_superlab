"""Independent free-history source atlas and guarded integration priority report.

Static source *documentation* is not evidence an API responds, that a historical
universe is survivorship-free, or that a factor is profitable. No downloads,
credentials, orders or production changes occur in this script.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MARKETS = {"BIST", "US", "CRYPTO"}
SCHEMA = "QS.free_history_atlas.v1"
ALLOWED = {"eaverse","quant_superlab","early_accumulation_radar",
           "bist_orderflow_quant","us_f1_bot","h054_spot_bot",
           "global_capital_radar","tier1_quant_terminal",
           "federal-incentive-radar","islem_onerisi_alarmi"}


def load_catalog(path=ROOT / "free_history_catalog.json"):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise ValueError("UNKNOWN_HISTORICAL_ATLAS_SCHEMA")
    seen = set()
    for source in data.get("sources", []):
        sid = source["id"]
        if sid in seen or not sid.replace("_","").isalnum():
            raise ValueError("DUPLICATE_OR_INVALID_SOURCE_ID")
        seen.add(sid)
        if source["market"] not in MARKETS:
            raise ValueError("INVALID_SOURCE_MARKET")
        if not source.get("documentation_url","").startswith("https://"):
            raise ValueError("NO_VERIFIED_SOURCE_DOCUMENTATION")
        if not source.get("signals") or not source.get("historical_scope"):
            raise ValueError("UNBOUNDED_SOURCE_DESCRIPTION")
        if not source.get("first_available_clock"):
            raise ValueError("MISSING_PUBLICATION_CLOCK_REVIEW")
        if not set(source.get("targets",[])).issubset(ALLOWED):
            raise ValueError("UNKNOWN_SOURCE_REPO")
        if (source.get("production_approved") is not False
                or source.get("alpha_validated") is not False
                or source.get("historical_pit_ready") is not False
                or source.get("automatic_download_enabled") is not False):
            raise ValueError("DISCOVERY_CATALOG_CANNOT_PROMOTE_OR_SCRAPE")
    if len(seen)<25:
        raise ValueError("TOO_FEW_DISTINCT_SOURCES_FOR_SCOPE")
    return data


def assess(catalog=None):
    c = catalog or load_catalog()
    categories = {"official_archive":[], "conditional_free":[],
                  "community_rebuilt":[], "paid_or_sample_only":[]}
    by_repo = {name:[] for name in ALLOWED}
    for x in c["sources"]:
        access=x["access_model"]
        if access in ("OFFICIAL_FREE_NO_KEY","OFFICIAL_FREE_DOWNLOAD",
                      "OFFICIAL_FREE_ARCHIVE","OFFICIAL_PUBLIC_API"):
            key="official_archive"
        elif ("LICENSED" in access or "PAID" in access or
              "SAMPLE" in access):
            key="paid_or_sample_only"
        elif ("COMMUNITY" in access or
              x["evidence_class"].startswith("COMMUNITY")):
            key="community_rebuilt"
        else:
            key="conditional_free"
        categories[key].append(x["id"])
        for p in x["targets"]:
            by_repo[p].append(x["id"])
    return {
        "schema":"QS.source_atlas.assessment.v1",
        "source_count":len(c["sources"]),
        "market_counts":dict(Counter(x["market"] for x in c["sources"])),
        "access_categories":categories,
        "repository_sources":{k:sorted(v) for k,v in sorted(by_repo.items())},
        "verified_source_downloads":0,
        "verified_pit_backtests":0,
        "automatically_promoted_alpha":0,
        "interpretation":("The atlas lists documented candidates only. "
           "Each historical endpoint needs a separately logged source-version, "
           "terms, archival timestamps and reproducible sample before use.")
    }


def markdown(catalog=None):
    c=catalog or load_catalog()
    lines=["# Ücretsiz tarihsel veri atlası — araştırma envanteri",
           "",
           "**Bu listedeki kaynakların hepsi teknik olarak erişilmiş ya da "
           "backtest için onaylanmış değildir.** Belgelenen arşivleri ve "
           "sınırlamaları görünür kılan araştırma envanteridir.",
           "",
           "Ücretsiz API ile ücretsiz kullanım hakkı, eski tarihli ham veri, "
           "geçmişte o anda bilinebilen veri ve geçmişten günümüze ücretsiz "
           "sürekli erişim birbirinden farklıdır.",
           ""]
    for market in ("BIST","US","CRYPTO"):
        lines += ["## "+market,"",
                  "| Kaynak | Eksik sinyal ailesi | Geriye dönük kapsam | Erişim | Kısıt |",
                  "|---|---|---|---|---|"]
        for s in c["sources"]:
            if s["market"]!=market:
                continue
            def clean(v):
                return str(v).replace("|","/").replace("\n"," ").strip()
            lines.append("| ["
                +s["id"]+"]("+s["documentation_url"]+") | "
                +clean(", ".join(s["signals"]))+" | "
                +clean(s["historical_scope"])+" | "
                +clean(s["access_model"])+" | "
                +clean(s["limitations"])+" |")
        lines.append("")
    lines += ["## Zaman doğruluğu ve research gate",
              "",
              "1. Kaynak olay tarihi, **orijinal kamusal yayımlanma zamanı**, "
              "arşivin değişiklik zamanı, sistemin gerçek indirme zamanı ve "
              "strateji sinyal zamanı ayrı tutulur.",
              "2. Sonradan güncellenen FINRA/FRED/KAP/SEC/BIST/kripto arşivleri "
              "eski bir stratejiye bugünkü bilgi geri taşınmış gibi yüklenmez.",
              "3. Historical membership ayrı, delisted fiyat/fill ayrı, "
              "split/dividend doğru versiyonlu olmalıdır.",
              "4. Teknik açıdan bedava görünen bir servis, veri tekrar "
              "yayınlama veya otomatik veri toplama yetkisi vermeyebilir.",
              "5. Keşif metodolojisi ve parametre aralığı outcome görülmeden "
              "kilitlenir; çoklu test, PIT, fill ve gerçek ileri örnek yoksa "
              "PAPER veya LIVE terfisi reddedilir.",
              "",
              "Her kaynağın deneysel entegrasyonu ancak kaynak davranışı, "
              "tarihsel doğruluk ve kullanım koşulları test edildikten sonra "
              "ayrı araştırma PR'ı ile yapılmalıdır."]
    return "\n".join(lines)+"\n"


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out", default="out/free_history_atlas")
    args=p.parse_args()
    c=load_catalog()
    z=assess(c)
    d=Path(args.out)
    d.mkdir(parents=True,exist_ok=True)
    (d/"source_review.json").write_text(
        json.dumps(z,indent=2,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8")
    (d/"source_atlas.md").write_text(markdown(c),encoding="utf-8")
    print("ATLAS_DOCS_REVIEWED",z["source_count"],z["market_counts"],
          "END_TO_END_SOURCE_DOWNLOADS",z["verified_source_downloads"])


if __name__=="__main__":
    main()
