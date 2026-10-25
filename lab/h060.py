"""H060: scaled H056 alone and mixed with the bot (config/h060.yaml). Needs network.  python -m lab.h060"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from lab import xsec

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    c = yaml.safe_load((ROOT / "config" / "h060.yaml").read_text())
    xc = yaml.safe_load((ROOT / "config" / "xsec.yaml").read_text())
    D = xsec.load(xc)
    s = xc["strategies"]["H056"]
    h = xsec.book(D, xc, s["signal"], s["lookback"], s["long"])["r"] * (c["vol_target"] / xc["portfolio"]["vol_target"])
    bot = xsec.bot_returns(D)
    idx = bot.index.intersection(h.index)
    bot, h = bot.reindex(idx), h.reindex(idx)
    out = {"data_end": str(idx[-1].date()), "bot": {"full": xsec.stats(bot)}, "rows": {}}
    out["bot"]["windows"] = {k: xsec.stats(bot[bot.index > k]) for k in c["cutoffs"]}
    for name, w in c["variants"].items():
        r = w["bot"] * bot + w["h056"] * h
        full = xsec.stats(r)
        win = {k: xsec.stats(r[r.index > k]) for k in c["cutoffs"]}
        chk = {"beat_bot_full": full["final_1000"] > out["bot"]["full"]["final_1000"],
               "beat_bot_windows": all(win[k]["final_1000"] > out["bot"]["windows"][k]["final_1000"] for k in c["cutoffs"]),
               "max_dd": full["max_dd"] >= c["accept"]["max_dd"]}
        out["rows"][name] = {"full": full, "windows": win, "checks": chk, "accepted": all(chk.values())}
    d = ROOT / "decisions" / "h060"
    d.mkdir(parents=True, exist_ok=True)
    (d / "result.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out, indent=1, default=str)[:3000])


if __name__ == "__main__":
    main()
