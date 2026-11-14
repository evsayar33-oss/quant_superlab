"""Post-hoc, explicitly exploratory annual-block chance check for H056.

H056 is locally accepted in xsec RESULT but NOT in central decision registry,
and the H056+H054 combined portfolio failed the frozen windows gate.
Five complete calendar years cannot establish a persistent trading edge.
"""
from __future__ import annotations
import json
from math import comb
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"results"/"h087"


def exact_binomial_one_sided(k,n):
    """Pr(Binomial(n,.5)>=k), a *very weak* yearly sign-null test."""
    return float(sum(comb(n,i) for i in range(k,n+1)) / 2**n)


def analyze():
    x=json.loads((ROOT/"decisions"/"xsec"/"result.json").read_text())
    z=x["strategies"]["H056"]
    years=[str(y) for y in range(2021,2026)] # ignore the partial 2026 year
    ans={}
    for label in ["base","cost_2x","delist_stress"]:
        vals=np.array([z[label]["yearly"][y] for y in years],float)
        n=len(vals);npos=int((vals>0).sum())
        if np.any(vals<=-1) or not np.isfinite(vals).all():
            raise ValueError("Invalid stored yearly funding return")
        wealth=float(np.prod(1+vals)-1)
        best=int(np.argmax(vals))
        exbest=float(np.prod(1+np.delete(vals,best))-1)
        ans[label]={
            "complete_years":years,
            "yearly_returns":vals.tolist(),
            "positive_years":npos,
            "n_years":n,
            "one_sided_exact_sign_p":exact_binomial_one_sided(npos,n),
            "wealth_2021_thru_2025":wealth,
            "wealth_without_best_year":exbest,
            "best_year":years[best],
            "worst_year_return":float(vals.min()),
            "published_sharpe":z[label].get("sharpe"),
            "published_max_drawdown":z[label].get("max_dd"),
        }
    reg=json.loads((ROOT/"decisions"/"registry.json").read_text())
    cross=z["combo"]
    obj={
        "name":"H056 funding carry",
        "status":"POSTHOC_EXPLORATORY_NO_PROSPECTIVE_VALIDATION",
        "source":"decisions/xsec/result.json",
        "local_xsec_accepted":bool(z["accepted"]),
        "all_local_xsec_checks_passed":bool(all(z["checks"].values())),
        "central_registry_H056_verdict":reg["hypotheses"].get("H056",{}).get("verdict"),
        "H054_mix_accepted":bool(cross.get("accepted")),
        "bot_comparison_three_windows":cross.get("windows"),
        "corr_with_BTC":z.get("corr_btc"),
        "corr_with_H054_bot":z.get("corr_bot"),
        "year_block_sensitivity":ans,
        "new_strategy_authorization":False,
        "interpretation":"One/few placebo annual blocks and local gating on already-reused source cannot certify alpha. 5 complete years; 2026 partial omitted.",
        "unmodelled_live_risks":[
            "Funding snapshots may differ across Binance Vision historical archive and executable Bitget perpetuals",
            "Delisted contract fills, margin, liquidations, hedging capital and funding timing are not independently broker-replayed",
            "Cross-sectional weekly top-volume ranking may use survivorship-biased contract metadata",
            "H056 positive local xsec verdict is not the central decision registry ACCEPT; combined bot failed",
            "Exact calendar-year sign test assumes independent fair-symmetric years; too few blocks for strong inference",
        ],
    }
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"H087_H056_POSTHOC.json").write_text(json.dumps(obj,indent=2))
    print(json.dumps({
        "local_accept":obj["local_xsec_accepted"],
        "central_registry_H056_verdict":obj["central_registry_H056_verdict"],
        "mix_accept":obj["H054_mix_accepted"],
        "year_sign_p":{k:v["one_sided_exact_sign_p"] for k,v in ans.items()},
        "best_year_drop":{k:v["wealth_without_best_year"] for k,v in ans.items()}
    },indent=2))
    return obj


if __name__=="__main__":
    analyze()
