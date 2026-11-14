"""H087: read-only complete tracked-file inventory, source-and-evidence audit.

This audits all tracked file names and the numerical result family registers;
it does NOT pretend to re-run 100m ICT searches or treat stale decisions as alpha.
"""
from __future__ import annotations
import collections
import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
EVIDENCE=ROOT/"decisions"
ICT=ROOT/"ict"/"results"
OUT=ROOT/"results"/"h087"
OUT.mkdir(parents=True,exist_ok=True)
TODAY=datetime.now(timezone.utc)
SEED=87091


def read(path: str):
    p=ROOT/path
    if not p.exists():
        raise FileNotFoundError(f"Registered evidence missing: {path}")
    return json.loads(p.read_text())


def finite_number(x):
    return isinstance(x,(float,int)) and math.isfinite(x)


def inventory():
    paths=subprocess.check_output(["git","ls-files","-z"],cwd=ROOT).decode().strip("\0").split("\0")
    files=[p for p in paths if p]
    categories=collections.Counter(p.split("/")[0] for p in files)
    return {
        "tracked_files":len(files),
        "root_category_counts":dict(sorted(categories.items())),
        "files":sorted(files),
        "source_classes":{
            "strategy_engine":"lab/; config/; hypotheses/",
            "results":"decisions/; ict/results/; research/h08*",
            "execution":"bots/core3_bot/; lab/client.py; lab/live.py",
            "presentation":"terminal/; dashboard/",
            "testing":"tests/; ict/tests/; research/*/test_*.py",
            "automation":".github/workflows/",
        },
        "scope_note":"Every tracked path enumerated; only evidence-bearing and risk-bearing families are parsed, not exhaustive line-by-line software verification",
    }


def audit():
    inv=inventory()
    registry=read("decisions/registry.json")
    hypotheses=registry["hypotheses"]
    counts=dict(collections.Counter(x.get("verdict","UNKNOWN") for x in hypotheses.values()))
    approvals=[]
    for key,rec in hypotheses.items():
        if rec.get("verdict")=="ACCEPT":
            age=None
            try:
                dt=datetime.fromisoformat(rec["validated_at"])
                age=(TODAY-dt).total_seconds()/86400
            except (ValueError,TypeError,KeyError):
                pass
            approvals.append({"id":key,"age_days":age,"validated_at":rec.get("validated_at"),
                              "data_end":rec.get("data_end"),
                              "stale_over_10days":age is None or age>10 or age<0})
    mega=read("decisions/mega/result.json")
    m_tm=read("decisions/mega/timemachine.json")
    m_base=read("decisions/mega/baseline.json")
    asset=read("decisions/assetbook/result.json")
    synthesis=read("decisions/synthesis/result.json")
    ml=read("decisions/mlbook/result.json")
    vol=read("decisions/volrange/result.json")
    xsec=read("decisions/xsec/result.json")
    cppi=read("decisions/cppi/result.json")
    core_d=read("decisions/core/1d.json")
    core_h=read("decisions/core/4h.json")
    forward=read("decisions/synthesis/forward.json")
    live=read("decisions/live_status.json")
    watch=read("decisions/watch/state.json")
    ictr=[]
    for ticker in ["NQ","SPX","XAU","XAG","BTC","ETH"]:
        source=ICT/f"{ticker}_placebo.csv"
        if source.exists():
            x=pd.read_csv(source)
            expected={"series","oos_exp","oos_trades"}
            if expected-set(x):
                raise ValueError(f"ICT placebo schema corrupt: {source}")
            records=x.to_dict("records")
            real=x[x.series=="real"]
            if len(real)!=1:
                raise ValueError(f"ICT has no unique real series for {ticker}")
            r=real.iloc[0]
            p=x[x.series!="real"]
            ictr.append({"asset":ticker,"real_oos_exp":float(r.oos_exp),
                         "real_trades":int(r.oos_trades),"placebo_rows":len(p),
                         "real_exceeds_all_placebos":bool(len(p)>0 and (r.oos_exp>p.oos_exp).all()),
                         "placebo_best_oos_exp":float(p.oos_exp.max()) if len(p) else None})
    cross=pd.read_csv(ICT/"cross_asset.csv")
    if cross.duplicated(["combo","entry","stop","rr","mgmt"]).any():
        dup=int(cross.duplicated(["combo","entry","stop","rr","mgmt"]).sum())
    else:dup=0
    # Positive cross-asset expectancy is a ranking lead, not a familywise pass.
    positive=int((pd.to_numeric(cross.pooled_oos_exp,errors="coerce")>0).sum())
    fw=pd.read_csv(ICT/"forward_test_nq_spx_xau.csv")
    arena={}
    for key in ["4h","4h_long","4h_short","1d","1d_long","1d_short"]:
        root=f"decisions/arena/{key}"
        r=read(root+"/roster.json")
        s=read(root+"/switcher.json")
        gate=read(root+"/switcher_gate.json")
        dt=None
        try:
            dt=datetime.fromisoformat(s["updated_at"])
        except (KeyError,TypeError,ValueError):
            pass
        n=r.get("members",[])
        arena[key]={
            "roster_count":len(n),
            "active":sum(m.get("status")=="active" for m in n),
            "control":sum(m.get("status")=="control" for m in n),
            "retired":sum(m.get("status")=="retired" for m in n),
            "switcher_updated_at":s.get("updated_at"),
            "switcher_age_days":(TODAY-dt).total_seconds()/86400 if dt else None,
            "switcher_usable":s.get("usable"),
            "backtest_gate_pass":gate.get("backtest_pass"),
        }
    # Historical results do not necessarily have daily-trade underlying series.
    sources={
        "H062":{"path":"decisions/mega/result.json","trials":mega["n_trials_total"],
                "d4_candidates":mega.get("d4_candidates",0),
                "finalists":len(mega.get("finalists",[])),
                "winners":len(mega.get("winners",[])),
                "time_machine_survivors":m_tm.get("n_survivors"),
                "random_entry_baseline_passers":m_base.get("n_pass"),
                "historical_baseline_independent_of_DSR":True},
        "H073":{"path":"decisions/assetbook/result.json","trials":asset["n_trials"],
                "jobs":len(asset.get("jobs",[])),
                "every_job_no_final_accept":all(not any(c.get("pick") for c in j.get("cuts",{}).values())
                                                for j in asset.get("jobs",[]))},
        "H072":{"path":"decisions/synthesis/result.json","trials":synthesis["n_trials"],
                "block_a_final":synthesis.get("block_a",{}).get("n_pass"),
                "block_b_final":synthesis.get("block_b",{}).get("n_pass")},
        "H076":{"path":"decisions/mlbook/result.json","trials":ml.get("n_trials"),"result_keys":list(ml)},
        "H077":{"path":"decisions/volrange/result.json","trials":vol.get("n_trials"),"result_keys":list(vol)},
        "xsec":{"path":"decisions/xsec/result.json","trials":xsec.get("n_trials"),
                "approved":{k:bool(v.get("accepted")) for k,v in xsec.get("strategies",{}).items()}},
        "CPPI":{"path":"decisions/cppi/result.json","date":cppi.get("data_end"),"books":list(cppi.get("rows",{}))},
        "core":{"date_1d":core_d.get("data_end"),"date_4h":core_h.get("data_end"),
                "trials_1d":core_d.get("n_trials"),"trials_4h":core_h.get("n_trials")},
    }
    return {
        "study":"H087", "asof_utc":TODAY.isoformat(),
        "file_manifest_count":inv["tracked_files"],
        "family_results":sources,
        "decision_registry":{"source_updated":registry.get("updated"),"hypotheses_count":len(hypotheses),
                             "verdict_counts":counts,"accepts":approvals},
        "live_status":live,
        "paper_watch":{"date":watch.get("date"),"start":watch.get("start"),
                       "ids":list(watch.get("ideas",{})),
                       "has_first_seen_committed":(EVIDENCE/"watch"/"observations.csv").exists()},
        "arena":arena,
        "synthesis_forward":forward,
        "ict":{"cross_asset_rows":len(cross),"duplicate_spec_keys":dup,
               "positive_cross_asset_rows_not_independent_alpha":positive,
               "forward_replays":fw.to_dict("records"),
               "asset_placebo":ictr},
        "non_comparable": [
            "H062/H073/ICT counts overlap correlated parameter/market search, do not sum as independent tests",
            "H072 CRSP monthly/daily proxy is not identical to executable SPY",
            "H083/H084/H085 portfolios reuse the same US securities history",
            "Arena backtest/protection metrics are not first-observed forward portfolio returns",
            "H076/ICT signals with report-only summarized outputs cannot be reconstructed as time-aligned daily trades",
            "H074 Bitget contract proxies differ from cash equity / continuous futures",
            "USD macro observations are not a pre-registered directly tradable FX return series",
        ],
    }


def stationary_ci(x: np.ndarray, reps:int=2000, block:int=30, seed:int=SEED):
    x=np.asarray(x,float)
    n=len(x)
    if n<60 or not np.isfinite(x).all():
        return {"n":n,"p_positive_mean":None,"ci":None}
    rng=np.random.default_rng(seed)
    centered=x-x.mean()
    observed=float(x.mean())
    samples=np.empty(reps)
    for j in range(reps):
        ix=np.empty(n,dtype=int);ix[0]=rng.integers(n)
        for t in range(1,n):
            ix[t]=rng.integers(n) if rng.random()<1/block else (ix[t-1]+1)%n
        samples[j]=x[ix].mean()
    # Null centered distribution: probability mean >= observed, positive-edge one-sided.
    p=(1+(samples-observed>=observed).sum())/(reps+1)
    return {"n":n,"p_positive_mean":float(p),
            "ci":[float(np.quantile(samples,.025)),float(np.quantile(samples,.975))],
            "mean_per_bar":observed,"positive_mean_supported":bool(p<=.05)}


def live_stress():
    series={}
    for k in ["H052","H054"]:
        f=EVIDENCE/"live"/f"{k}.csv"
        df=pd.read_csv(f)
        if set(df)!= {"ts","live_return"}:
            raise ValueError(f"Unexpected prospective schema for {k}")
        df.ts=pd.to_datetime(df.ts,errors="raise")
        if df.ts.duplicated().any() or not df.ts.is_monotonic_increasing:
            raise ValueError(f"Duplicate or noncausal timestamp order {k}")
        vals=df.live_return.to_numpy(float)
        if len(vals)<60 or not np.isfinite(vals).all() or (vals<=-1).any():
            raise ValueError(f"Insufficient live series: {k}")
        mean=float(vals.mean())
        wealth=float(np.prod(1.+vals)-1.)
        neglog=np.sort(vals)[-5:]
        trimmed=float(np.prod(1.+np.delete(vals,np.argsort(vals)[-5:]))-1)
        st=stationary_ci(vals,seed=SEED+(1 if k=="H054" else 0))
        series[k]={
            "start":str(df.ts.iloc[0]),"end":str(df.ts.iloc[-1]),"bars":len(vals),
            "cum_return":wealth,"mean_bar":mean,"zero_return_pct":float((vals==0).mean()),
            "positive_bar_pct":float((vals>0).mean()),
            "return_excluding_five_best_bars":trimmed,
            "best_five_bar_returns":neglog.tolist(),"block_bootstrap":st,
        }
    a=pd.read_csv(EVIDENCE/"live"/"H052.csv").set_index("ts").live_return
    b=pd.read_csv(EVIDENCE/"live"/"H054.csv").set_index("ts").live_return
    pair=pd.concat([a,b],axis=1,keys=["H052","H054"]).dropna()
    corr=float(pair.corr().iloc[0,1])
    d=(pair.H054-pair.H052).to_numpy()
    return {"models":series,"correlation":corr,"correlation_warning":
            "H052 and H054 are strongly related models, not independent return bets",
            "paired_delta_H054_minus_H052":stationary_ci(d,seed=SEED+8),
            "no_reconstructed_paper_nav_passed_off_as_forward":True}


def run():
    inv=inventory();aud=audit();live=live_stress()
    (OUT/"H087_REPO_INVENTORY.json").write_text(json.dumps(inv,indent=2))
    (OUT/"H087_AUDIT.json").write_text(json.dumps(aud,indent=2,default=str))
    (OUT/"H087_LIVE_STRESS.json").write_text(json.dumps(live,indent=2))
    print(json.dumps({
        "file_count":inv["tracked_files"],
        "verdict_counts":aud["decision_registry"]["verdict_counts"],
        "family_trials":{k:v.get("trials") for k,v in aud["family_results"].items()},
        "live":{k:v["cum_return"] for k,v in live["models"].items()},
        "live_correlation":live["correlation"],
        "ict_real_placebo":aud["ict"]["asset_placebo"],
        "arena_usable":{k:v["switcher_usable"] for k,v in aud["arena"].items()},
    },indent=2,default=str))


if __name__=="__main__":
    run()
