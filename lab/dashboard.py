"""Static dashboard for GitHub Pages: dashboard/index.html + data_<tf>.json per timeframe + tfs.json (built by every arena run).

The page is deployed with actions/deploy-pages (an artifact, not a commit), so the repository does not grow.
Settings -> Pages -> Source: "GitHub Actions" (one time).
"""
from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _clean(x):
    if isinstance(x, float):
        return None if (math.isnan(x) or math.isinf(x)) else x
    if isinstance(x, dict):
        return {str(k): _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    return x


def build(out: dict, cfg: dict, site: str | Path = "site") -> Path:
    from lab import arena
    site = Path(site)
    site.mkdir(parents=True, exist_ok=True)
    gate = arena._read(arena.GATE, {})
    summ = arena._read(arena.SUMMARY, {})
    data = {
        "updated_at": out["switcher"]["updated_at"], "data_end": out["data_end"],
        "universe": cfg.get("universe"), "timeframe": cfg.get("timeframe"),
        "windows": cfg.get("report_windows_years", [3, 5, 0]), "account": cfg.get("account", {}),
        "switcher": out["switcher"], "gate": gate, "screen": summ,
        "spark_switch_fwd": out.get("spark_switch_fwd", []), "spark_ew_fwd": out.get("spark_ew_fwd", []),
        "members": out["members"], "books": out.get("books", []),
    }
    tf = cfg.get("key", cfg.get("timeframe", "4h"))
    (site / f"data_{tf}.json").write_text(json.dumps(_clean(data), ensure_ascii=False, default=str, separators=(",", ":")))
    return site / f"data_{tf}.json"


def write_index(site: str | Path, timeframes: list[str]) -> None:
    site = Path(site)
    site.mkdir(parents=True, exist_ok=True)
    (site / "tfs.json").write_text(json.dumps(timeframes))
    shutil.copy(ROOT / "dashboard" / "index.html", site / "index.html")
    (site / ".nojekyll").write_text("")
