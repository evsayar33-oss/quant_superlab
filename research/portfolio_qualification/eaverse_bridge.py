"""Read-only cross-repository economic evidence reproduction and central passport.

Uses source-SHA-pinned Eaverse *historical derived weekly return paths*, not
an artifact's success status. Independently recalculates 8-block CSCV PBO.
All external outcomes remain research-only: central lab.validate() cannot run
without authorized PIT market panels and executable candidate strategies.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from statistics import NormalDist
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from . import gate

SCHEMA = "QS.independent.v7_empirical_bridge.v1"
SYMBOLS = ("BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT",
           "BNBUSDT","ADAUSDT","LINKUSDT","AVAXUSDT")
SOURCE_REPO = "evsayar33-oss/eaverse"
SOURCE_BRANCH = "research/eaverse-v7-{symbol}-evidence"
SOURCE_LEDGERS = {
    "study": "observations/extended_flow/studies.jsonl",
    "statistics": "observations/extended_flow/statistical_trials.jsonl",
}
SHA40 = re.compile(r"^[a-f0-9]{40}$")
MAX_BYTES = 2_000_000


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False,
                                     separators=(",", ":")).encode()).hexdigest()


def _fetch(url, token=None):
    headers = {"User-Agent":"quant-superlab-readonly-reproduction/1"}
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = "Bearer " + token
    with urlopen(Request(url, headers=headers), timeout=20) as source:
        data = source.read(MAX_BYTES+1)
    if len(data) > MAX_BYTES:
        raise ValueError("EAVERSE_RESEARCH_LEDGER_OVERSIZED")
    return data.decode("utf-8")


def _read_chain(raw):
    previous="GENESIS"
    records=[]
    for line in raw.splitlines():
        if not line.strip():
            continue
        obj=json.loads(line)
        if not isinstance(obj,dict):
            raise ValueError("SOURCE_RECORD_NOT_DICT")
        unsigned={k:v for k,v in obj.items() if k!="sha256"}
        if obj.get("prev_sha256")!=previous or obj.get("sha256")!=digest(unsigned):
            raise ValueError("SOURCE_EVIDENCE_CHAIN_TAMPER")
        previous=obj["sha256"]
        records.append(obj)
    if not records:
        raise ValueError("EMPTY_SOURCE_EVIDENCE_CHAIN")
    return records


def _sharpe(values):
    # Same ranking as numpy sample Sharpe; constant series are -infinity.
    n=len(values)
    if n<2:
        return float("-inf")
    avg=sum(values)/n
    variance=sum((x-avg)**2 for x in values)/(n-1)
    return avg/math.sqrt(variance) if variance>1e-24 else float("-inf")


def reproduce_pbo(panel, blocks=8):
    """Independent plain-Python CSCV calculation on all unselected variants."""
    if len(panel)<blocks*8 or blocks%2 or blocks<4:
        return None
    n=len(panel)
    k=len(panel[0])
    if k<2 or any(len(row)!=k for row in panel):
        raise ValueError("ALIGNED_PANEL_SHAPE_MISMATCH")
    eligible=[col for col in range(k) if max(row[col] for row in panel)!=min(
        row[col] for row in panel)]
    if len(eligible)<2:
        return None
    sizes=[(n//blocks)+(1 if i<n%blocks else 0) for i in range(blocks)]
    chunks=[]
    start=0
    for width in sizes:
        chunks.append(list(range(start,start+width)))
        start+=width
    below=0
    partitions=0
    for selected_blocks in itertools.combinations(range(blocks),blocks//2):
        tr=[i for j in selected_blocks for i in chunks[j]]
        te=[i for j in range(blocks) if j not in selected_blocks for i in chunks[j]]
        train=[_sharpe([panel[i][col] for i in tr]) for col in eligible]
        winner=max(range(len(eligible)),key=lambda j:train[j])
        test=[_sharpe([panel[i][col] for i in te]) for col in eligible]
        rank=(sum(x<test[winner] for x in test)+
              0.5*sum(x==test[winner] for x in test))/len(test)
        below+=rank<.5
        partitions+=1
    return {"pbo":round(below/partitions,6),"partitions":partitions,
            "nonflat_variants":len(eligible)}


def _validate(panel, stats, study):
    if stats.get("schema")!="eaverse.v7.aligned_empirical_trials.v1":
        raise ValueError("UNREGISTERED_SOURCE_STATISTICAL_SCHEMA")
    if stats.get("symbol") not in SYMBOLS or stats.get("source_venue")!="BINANCE_SPOT":
        raise ValueError("UNREGISTERED_ASSET_OR_VENUE")
    for key in ("paper_eligible","live_allowed","untouched_holdout_read",
                "independent_prospective_validated"):
        if stats.get(key) is not False:
            raise ValueError("UNAUTHORIZED_HISTORICAL_TO_FORWARD_PROMOTION")
    if (stats.get("source_digest")!=study.get("source_digest") or
        stats.get("source_policy_sha256")!=study.get("policy_sha256") or
        stats.get("source_hypotheses_sha256")!=study.get("study_digest")):
        raise ValueError("SOURCE_HASH_OR_METHOD_VERSION_MISMATCH")
    if study.get("paper_eligible") is not False or study.get("forward_validated") is not False:
        raise ValueError("UPSTREAM_FALSE_FORWARD_AUTHORIZATION")
    if digest(study.get("full_hypothesis_studies"))!=study.get("study_digest"):
        raise ValueError("UPSTREAM_TRIALS_NOT_REPRODUCIBLE")
    if (stats.get("registered_total_trial_family_per_asset")!=64 or
        stats.get("registered_long_trial_count")!=32 or
        stats.get("cross_asset_long_trial_family")!=256):
        raise ValueError("INCOMPLETE_FAMILYWISE_SEARCH_COUNT")
    container=stats.get("weekly_panel")
    if not isinstance(container,dict):
        raise ValueError("MISSING_ALIGNED_RETURN_MATRIX")
    if container.get("sha256")!=digest({k:v for k,v in container.items()
                                       if k!="sha256"}):
        raise ValueError("WEEKLY_RETURN_MATRIX_SHA_MISMATCH")
    dates=container.get("dates_utc_week_end")
    keys=container.get("variant_ids")
    values=container.get("net_return_paths")
    if not isinstance(dates,list) or not isinstance(keys,list) or not isinstance(values,list):
        raise ValueError("WEEKLY_PANEL_FIELDS_INVALID")
    if len(keys)!=32 or len(set(keys))!=32 or len(values)!=len(dates):
        raise ValueError("MISSING_UNSELECTED_VARIANTS_OR_WEEKS")
    expected_ids={x["id"] for x in study["full_hypothesis_studies"]
                  if x.get("spec",{}).get("direction")==1}
    if set(keys)!=expected_ids:
        raise ValueError("UNREGISTERED_HYPOTHESIS_IN_PANEL")
    try:
        stamps=[datetime.fromisoformat(x) for x in dates]
    except (TypeError,ValueError) as e:
        raise ValueError("INVALID_WEEKLY_OBSERVATION_CLOCK") from e
    if any(x.tzinfo is None for x in stamps) or any(
        stamps[i]>=stamps[i+1] for i in range(len(stamps)-1)):
        raise ValueError("NONCHRONOLOGICAL_OR_NONUTC_OBSERVATIONS")
    if len(values)<64 or any(len(row)!=32 for row in values):
        raise ValueError("INSUFFICIENT_UNSELECTED_ALIGNED_PANEL")
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or
           not math.isfinite(x) or x<=-1 for row in values for x in row):
        raise ValueError("NONFINITE_OR_IMPOSSIBLE_MODEL_RETURN")
    if (int(stats.get("weekly_discovery_rows",0))+
        int(stats.get("weekly_validation_rows",0)))!=len(values):
        raise ValueError("FOLD_ROW_COUNTS_INVALID")
    chosen=stats.get("selected_discovery_variant_id")
    if chosen not in keys:
        raise ValueError("MISSING_DISCOVERY_SELECTED_VARIANT")
    train_count=stats["weekly_discovery_rows"]
    if train_count<32 or len(values)-train_count<16:
        raise ValueError("INSUFFICIENT_INDEPENDENT_RESEARCH_SPLITS")
    # Confirm source-selected variant truly maximized discovery-only score.
    scores=[_sharpe([row[col] for row in values[:train_count]])
            for col in range(32)]
    if keys[max(range(32),key=lambda j:scores[j])]!=chosen:
        raise ValueError("LOOKAHEAD_OR_WRONG_DISCOVERY_SELECTION")
    reproduced=reproduce_pbo(values)
    source_pbo=stats.get("pbo",{})
    if source_pbo.get("pbo") is not None:
        if reproduced is None or abs(reproduced["pbo"]-source_pbo["pbo"])>1e-6:
            raise ValueError("PBO_REPLICATION_MISMATCH")
        if reproduced["partitions"]!=source_pbo.get("partitions"):
            raise ValueError("CSCV_FOLD_COUNT_MISMATCH")
    elif reproduced is not None:
        raise ValueError("SOURCE_SKIPPED_MEASURABLE_CSCV")
    dsr=stats.get("dsr",{})
    d=dsr.get("dsr")
    if d is not None and (isinstance(d,bool) or not isinstance(d,(int,float)) or
                          not 0<=d<=1):
        raise ValueError("DSR_REPORT_INVALID")
    return reproduced


def _review_prerequisites(stats, study):
    # Existing central checklist; all unavailable independent facts stay FALSE.
    # No plausible proof of issuer PIT, independent prospective outcomes, or
    # broker-native execution can be inferred from a derived historical matrix.
    checks={
        "asof_only": False,
        "quality_verified": False,
        "universe_bias_accounted": False,
        "registered_before_outcomes": False,
        "matched_controls_verified": False,
        "independent_oos_verified": False,
        "cost_stress_verified": True,
        "realistic_fill_assumptions_verified": False,
        "multi_testing_adjusted": bool(stats.get("pbo",{}).get("pbo") is not None and
                                       stats.get("dsr",{}).get("dsr") is not None),
        "regime_robustness_verified": False,
        "prospective_outcomes_matured": False,
    }
    passport={
        **checks,
        "hypothesis_id":stats.get("selected_discovery_variant_id"),
        "source_repository":SOURCE_REPO,
        "methodology_sha256":stats.get("source_policy_sha256"),
        "source_evidence_sha256":stats.get("source_digest"),
        "benchmark":"CASH_ZERO_EXPOSURE_NOT_RISK_MATCHED",
        "strategy_definition":"V7_LONG_FIXED_HORIZON_EVENT_HYPOTHESIS",
        "registered_utc":None,
        "train_end_utc":None,
        "oos_start_utc":None,
        "oos_end_utc":None,
        "latest_outcome_at_utc":None,
        "distinct_time_blocks":stats.get("weekly_validation_rows",0),
        "completed_trades_or_events":max(stats.get("candidate_events_validation",[0])),
        "read_only_research":True,
    }
    verdict=gate.review(passport)
    if verdict["status"]=="READY_FOR_INDEPENDENT_PAPER_REVIEW":
        raise ValueError("UNEXPECTED_AUTOMATIC_PAPER_QUALIFICATION")
    return verdict


def audit_one(symbol, stats_ledger, study_ledger, ref_sha):
    if symbol not in SYMBOLS or not SHA40.fullmatch(ref_sha):
        raise ValueError("UNTRUSTED_V7_SOURCE_BRANCH_OR_COMMIT")
    stats=_read_chain(stats_ledger)[-1]
    study=_read_chain(study_ledger)[-1]
    if stats.get("symbol")!=symbol or study.get("asset")!=symbol:
        raise ValueError("MISMATCHED_SOURCE_SYMBOL")
    reproduced=_validate(stats.get("weekly_panel"),stats,study)
    review=_review_prerequisites(stats,study)
    return {
        "symbol":symbol, "source_repository":SOURCE_REPO,
        "source_commit_sha":ref_sha,
        "source_digest":stats["source_digest"],
        "source_policy_sha256":stats["source_policy_sha256"],
        "panel_sha256":stats["weekly_panel"]["sha256"],
        "read_only":True,"central_passport_evaluated":True,
        "central_lab_backtest_invoked":False,
        "central_lab_accept":False,"paper_approved":False,"live_allowed":False,
        "status":"INDEPENDENTLY_REPRODUCED_HISTORICAL_CSCV_ONLY_NO_ACCEPT",
        "reproduced_pbo":reproduced,
        "source_approx_dsr":stats["dsr"].get("dsr"),
        "dsr_independent_replication_complete":False,
        "central_gate_status":review["status"],
        "central_gate_blockers":review["blockers"],
        "risk_note":"Independent OOS, delist-aware issuer PIT, venue-native fills and prospective evidence not proven",
    }


def collect(symbol, fetch=_fetch, token=None):
    branch=SOURCE_BRANCH.format(symbol=symbol.lower())
    api="https://api.github.com/repos/"+SOURCE_REPO+"/git/ref/heads/"+branch
    ref=json.loads(fetch(api,token))["object"]["sha"]
    if not SHA40.fullmatch(ref):
        raise ValueError("UNTRUSTED_SOURCE_BRANCH_HEAD")
    bodies={}
    for label,path in SOURCE_LEDGERS.items():
        url="https://raw.githubusercontent.com/"+SOURCE_REPO+"/"+ref+"/"+path
        bodies[label]=fetch(url,None)
    return audit_one(symbol,bodies["statistics"],bodies["study"],ref)


def run(fetch=_fetch, token=None):
    results=[]
    for symbol in SYMBOLS:
        try:
            results.append(collect(symbol,fetch,token))
        except (HTTPError,URLError,TimeoutError,OSError,ValueError,KeyError,
                TypeError,json.JSONDecodeError) as err:
            results.append({"symbol":symbol, "status":"SOURCE_NOT_REPRODUCED",
                            "blocker":type(err).__name__+
                                (":"+str(err)[:80] if isinstance(err,ValueError) else ""),
                            "central_lab_accept":False,
                            "paper_approved":False,"live_allowed":False})
    return {
        "schema":SCHEMA,
        "source_repository":SOURCE_REPO,
        "assets_checked":len(results),
        "reproduced":sum(x["status"].startswith("INDEPENDENTLY_REPRODUCED")
                         for x in results),
        "results":results,
        "source_data_promoted_to_trading":False,
        "official_central_validation_gate_unchanged":True,
        "central_lab_accepted_by_bridge":0,
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,
                        default=Path("out/portfolio_qualification/eaverse_bridge.json"))
    args=parser.parse_args()
    result=run(token=os.environ.get("GH_TOKEN"))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("EAVERSE_INDEPENDENT_RESEARCH_BRIDGE",result["reproduced"],
          "of",result["assets_checked"],"source variants reproduced",
          "NO_LAB_ACCEPT")


if __name__=="__main__":
    main()
