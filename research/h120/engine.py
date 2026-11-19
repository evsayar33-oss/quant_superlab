"""H120 — isolated Tier-1 evidence intelligence lane inside quant_superlab.

Sources ONLY Tier-1 independent audit and sealed study decisions.
No Early Radar import. No modification to either project's model, state,
hypothesis registry, ACCEPT gate, PAPER experiment or trading decisions.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UPSTREAM = "evsayar33-oss/tier1_quant_terminal"
SCHEMA = "QS.h120.tier1_intelligence.v1"
AUDIT = "audit/30d-evidence"
STUDIES = "audit/study-decisions"
SENTIMENT = "audit/sentiment-superlab"
ASSETS = ("SPX", "NQ", "XAU", "XAG", "BTC", "ETH")
HORIZONS = ("4", "24")
SHA40 = re.compile(r"^[0-9a-f]{40}$")
STUDY_FILES = (
    "research_decisions/tier1_v2_forward-final.json",
    "research_decisions/research30_crypto_flow-final.json",
)
SENTIMENT_FILE = "sentiment_study_decisions/tier1_sentiment_superlab-final.json"
MIN_INDEPENDENT = 100
MIN_ALLOWED = 30
STALE_HOURS = 24
NOTIFY_KINDS = {
    "SEALED_STUDY_DECISION", "PROSPECTIVE_REPLICATION_LEAD",
    "SOURCE_AUDIT_STALE",
}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def utc(value):
    d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("H120_NAIVE_UTC_TIMESTAMP")
    return d.astimezone(timezone.utc)


def now_utc():
    return datetime.now(timezone.utc)


def read_ledger(path):
    p = Path(path)
    if not p.exists():
        return []
    prev, last = "GENESIS", -1
    rows = []
    for raw in p.read_text(encoding="utf-8").splitlines():
        row = json.loads(raw)
        record = {k: v for k, v in row.items() if k != "sha256"}
        if (record.get("prev_sha256") != prev
                or fingerprint(record) != row.get("sha256")
                or not isinstance(row.get("seq"), int)
                or row["seq"] <= last
                or row.get("schema") != SCHEMA):
            raise ValueError("H120_HASH_CHAIN_INVALID")
        prev, last = row["sha256"], row["seq"]
        rows.append(row)
    return rows


def append_ledger(path, events):
    previous = read_ledger(path)
    known = {x["id"] for x in previous}
    fresh = [dict(x) for x in events if x["id"] not in known]
    if not fresh:
        return previous
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    prev = previous[-1]["sha256"] if previous else "GENESIS"
    seq = previous[-1]["seq"] if previous else 0
    with p.open("a", encoding="utf-8") as out:
        for x in fresh:
            seq += 1
            x.update({"schema": SCHEMA, "seq": seq, "prev_sha256": prev})
            x["sha256"] = fingerprint(x)
            out.write(canonical(x) + "\n")
            previous.append(x)
            prev = x["sha256"]
    return previous


def http_text(url):
    headers = {"User-Agent": "quant-superlab-h120-readonly",
               "Accept": "application/vnd.github+json"}
    if url.startswith("https://api.github.com/"):
        token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        if token:
            headers["Authorization"] = "Bearer " + token
            headers["X-GitHub-Api-Version"] = "2022-11-28"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read().decode("utf-8")


def remote_ref(branch, fetch=http_text, optional=False):
    url = "https://api.github.com/repos/" + UPSTREAM + "/git/ref/heads/" + branch
    try:
        data = json.loads(fetch(url))
    except urllib.error.HTTPError as err:
        if optional and err.code == 404:
            return None
        raise
    sha = data["object"]["sha"]
    if not SHA40.fullmatch(sha):
        raise ValueError("H120_INVALID_UPSTREAM_SHA")
    return sha


def check_ancestry(branch, before, after, fetch=http_text):
    if not before or before == after:
        return
    if not SHA40.fullmatch(before):
        raise ValueError("H120_INVALID_PRIOR_SOURCE_SHA")
    url = ("https://api.github.com/repos/" + UPSTREAM + "/compare/"
           + before + "..." + after)
    result = json.loads(fetch(url))
    if (result.get("status") != "ahead"
            or result.get("behind_by") != 0
            or result.get("ahead_by", 0) <= 0):
        raise ValueError("H120_SOURCE_BRANCH_REWRITTEN_OR_ROLLED_BACK")


def source_raw(branch_sha, path, fetch=http_text, optional=False):
    url = ("https://raw.githubusercontent.com/" + UPSTREAM +
           "/" + branch_sha + "/" + path)
    try:
        return fetch(url)
    except urllib.error.HTTPError as err:
        if optional and err.code == 404:
            return None
        raise


def fetch_evidence(old_sha, fetch=http_text):
    """Fetch pinned only from Tier-1; no H119/Early endpoints."""
    sha = remote_ref(AUDIT, fetch)
    check_ancestry(AUDIT, old_sha.get(AUDIT), sha, fetch)
    summary_raw = source_raw(sha, "independent_audit/summary.json", fetch)
    ledger_raw = source_raw(sha, "independent_audit/ledger.json", fetch)
    report = {
        "summary": json.loads(summary_raw),
        "ledger": json.loads(ledger_raw),
        "decision_docs": [],
        "source_commits": {AUDIT: sha},
        "source_hashes": {
            "summary": hashlib.sha256(summary_raw.encode()).hexdigest(),
            "ledger": hashlib.sha256(ledger_raw.encode()).hexdigest(),
        },
    }
    for branch, paths in ((STUDIES, STUDY_FILES),
                          (SENTIMENT, (SENTIMENT_FILE,))):
        commit = remote_ref(branch, fetch, optional=True)
        if commit is None:
            if old_sha.get(branch):
                raise ValueError("H120_SEALED_STUDY_BRANCH_DISAPPEARED")
            continue
        check_ancestry(branch, old_sha.get(branch), commit, fetch)
        report["source_commits"][branch] = commit
        for path in paths:
            contents = source_raw(commit, path, fetch, optional=True)
            if contents is None:
                continue
            report["decision_docs"].append({
                "path": path, "branch": branch, "commit": commit,
                "sha256": hashlib.sha256(contents.encode()).hexdigest(),
                "data": json.loads(contents),
            })
    return report


def finite_number(x, lo=None, hi=None):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ValueError("H120_INVALID_NUMERIC_METRIC")
    if lo is not None and x < lo:
        raise ValueError("H120_METRIC_BELOW_ALLOWED_RANGE")
    if hi is not None and x > hi:
        raise ValueError("H120_METRIC_ABOVE_ALLOWED_RANGE")
    return x


def validate_source(evidence, when):
    summary, ledger = evidence["summary"], evidence["ledger"]
    if str(ledger.get("schema")) != "1.0":
        raise ValueError("H120_AUDIT_SCHEMA_CHANGED")
    st, en = utc(summary["start_utc"]), utc(summary["end_utc"])
    asof = utc(summary["as_of_utc"])
    observed = utc(ledger["last_audit_utc"])
    if not st < en or asof > when or observed > when:
        raise ValueError("H120_INVALID_PROSPECTIVE_WINDOW")
    if abs((asof - observed).total_seconds()) > 3600:
        raise ValueError("H120_SUMMARY_LEDGER_OUT_OF_SYNC")
    if not isinstance(ledger.get("calls"), list) or not isinstance(ledger.get("snapshots"), list):
        raise ValueError("H120_AUDIT_CALLS_OR_PRICE_SNAPSHOTS_MISSING")
    for h in HORIZONS:
        m = summary["horizons"][h]
        for key in ("model_hit", "always_long_hit",
                    "multiple_testing_adjusted_p_bonferroni_12"):
            finite_number(m[key], 0, 1)
        finite_number(m["independent_by_asset_n"], 0)
        for key in ("missing_labels", "pending_labels"):
            finite_number(m[key], 0)
        if m["independent_by_asset_n"] > len(ledger["calls"]):
            raise ValueError("H120_AUDIT_N_EXCEEDS_OBSERVED_CALLS")
        if m.get("independent_assets_assumption_verified") not in (True, False):
            raise ValueError("H120_CROSS_ASSET_INDEPENDENCE_UNKNOWN")
        for cost in ("0", "40"):
            if cost not in m["hypothetical_cost_scenarios_bps"]:
                raise ValueError("H120_REQUIRED_COST_STRESS_MISSING")
            finite_number(m["hypothetical_cost_scenarios_bps"][cost]["hypothetical_mean_bps"])
    n_allowed = finite_number(summary["entry_allowed"], 0)
    if n_allowed > len(ledger["calls"]):
        raise ValueError("H120_TRADEABLE_ENTRIES_EXCEED_OBSERVED_CALLS")
    for c in ledger["calls"]:
        if c.get("asset") not in ASSETS:
            raise ValueError("H120_UNKNOWN_ASSET_IN_AUDIT")
        if utc(c["observed_utc"]) > when:
            raise ValueError("H120_FUTURE_OBSERVATION")
        if utc(c["publication_utc"]) > utc(c["observed_utc"]):
            raise ValueError("H120_PUBLICATION_AFTER_FIRST_SEEN")
        # The source auditor emits only *observed* horizon records.
        # Pending/stale/unpriceable rows can have one or zero horizons:
        # absence means MISSING, NEVER an invented grade or a hard crash.
        horizon_data = c.get("horizons")
        if not isinstance(horizon_data, dict):
            raise ValueError("H120_INVALID_FORECAST_HORIZONS")
        for h, details in horizon_data.items():
            if h not in HORIZONS or not isinstance(details, dict):
                raise ValueError("H120_UNEXPECTED_FORECAST_HORIZON")
        if c.get("entry_allowed") not in (True, False):
            raise ValueError("H120_MISSING_ENTRY_PERMISSION")
    return observed


def grade_summary(summary):
    """Preregistered two-horizon *diagnostic* rule; never a trade ACCEPT."""
    result = {}
    for horizon in HORIZONS:
        x = summary["horizons"][horizon]
        independent = x["independent_by_asset_n"]
        edge = round(x["model_hit"] - x["always_long_hit"], 4)
        stress = x["hypothetical_cost_scenarios_bps"]["40"]["hypothetical_mean_bps"]
        # Multi-symbol 12-test corrected p alone cannot prove independence.
        qualified = (
            independent >= MIN_INDEPENDENT
            and summary["entry_allowed"] >= MIN_ALLOWED
            and x["independent_assets_assumption_verified"] is True
            and x["multiple_testing_adjusted_p_bonferroni_12"] <= .05
            and edge > .05 and stress > 0
            and x["missing_labels"] <= independent
            and x["verdict"] != "INSUFFICIENT"
        )
        result[horizon] = {
            "horizon_hours": int(horizon), "observations": independent,
            "model_hit": x["model_hit"],
            "always_long_hit": x["always_long_hit"],
            "directional_uplift": edge,
            "bonferroni_12_p": x["multiple_testing_adjusted_p_bonferroni_12"],
            "assumed_40bps_mean_bps": stress,
            "independent_asset_assumption_verified":
                x["independent_assets_assumption_verified"],
            "grade": ("REPLICATION_LEAD_REQUIRES_NATIVE_LAB_TEST"
                      if qualified else "NOT_ENOUGH_INDEPENDENT_EVIDENCE"),
            "source_verdict": x["verdict"],
            "official_lab_gate": "NOT_RUN",
            "realized_executable_pnl": None,
        }
    return result


def descriptive_asset_review(ledger):
    """Hypothesis ranking only, NOT selection/gate data: overlaps unadjusted."""
    rows = []
    for asset in ASSETS:
        for horizon in HORIZONS:
            calls = []
            for c in ledger["calls"]:
                if c["asset"] != asset:
                    continue
                h = c["horizons"].get(horizon, {})
                if h.get("status") != "GRADED":
                    continue
                gross, reference = h.get("gross_return"), h.get("baseline_long_return")
                if any(not isinstance(z, (int, float)) or not math.isfinite(z)
                       for z in (gross, reference)):
                    continue
                calls.append((gross, reference))
            if not calls:
                continue
            n = len(calls)
            rows.append({
                "asset": asset, "horizon_hours": int(horizon),
                "graded_raw_rows_not_independent": n,
                "model_direction_hit": round(sum(x > 0 for x, _ in calls) / n, 4),
                "always_long_hit": round(sum(y > 0 for _, y in calls) / n, 4),
                "data_label": "OVERLAPPING_AND_PROXY_NOT_TRADEABLE",
                "selection_allowed": False,
            })
    return sorted(rows, key=lambda r:(ASSETS.index(r["asset"]), r["horizon_hours"]))


def validate_decision(d):
    item = d["data"]
    if (item.get("schema") != 1
            or item.get("auto_applied") != "RESEARCH_STATUS_ONLY"
            or item.get("live_orders") is not False
            or item.get("production_logic_modified") is not False
            or item.get("stage") != "FINAL"
            or item.get("study_id") not in (
                "tier1_v2_forward", "research30_crypto_flow",
                "tier1_sentiment_superlab")):
        raise ValueError("H120_UNTRUSTED_STUDY_DECISION")
    if item["study_id"] == "tier1_sentiment_superlab" and d["branch"] != SENTIMENT:
        raise ValueError("H120_STUDY_BRANCH_MISMATCH")
    if item["study_id"] != "tier1_sentiment_superlab" and d["branch"] != STUDIES:
        raise ValueError("H120_STUDY_BRANCH_MISMATCH")
    if not isinstance(item.get("assessment", {}).get("decision"), str):
        raise ValueError("H120_UNTRUSTED_STUDY_ASSESSMENT")
    return item


def event(kind, identity, details, stamp):
    return {
        "kind": kind, "id": fingerprint([SCHEMA, kind, identity]),
        "observed_utc": stamp, "source_repo": UPSTREAM,
        "scope": "TIER1_ONLY_NO_EARLY_RADAR",
        "evidence": details,
        "quant_superlab_verdict": "NOT_EVALUATED",
        "live_orders_allowed": False,
        "terminal_logic_modified": False,
    }


def evaluate(evidence, previous, now):
    observed = validate_source(evidence, now)
    if observed < utc(evidence["summary"]["start_utc"]):
        raise ValueError("H120_AUDIT_PRECEDES_STUDY")
    if len(evidence["ledger"]["calls"]) < int(previous.get("calls_seen", 0)):
        raise ValueError("H120_AUDIT_OBSERVATIONS_DISAPPEARED")
    grades = grade_summary(evidence["summary"])
    candidates = []
    for horizon, grade in grades.items():
        if grade["grade"] == "REPLICATION_LEAD_REQUIRES_NATIVE_LAB_TEST":
            # One event per independent horizon AND study identity, not per poll.
            candidates.append(event(
                "PROSPECTIVE_REPLICATION_LEAD",
                "tier1_30d:" + horizon,
                {"horizon": horizon, "metrics": grade,
                 "source_commit": evidence["source_commits"][AUDIT],
                 "approved_strategy": False},
                now.isoformat()))
    for d in evidence["decision_docs"]:
        item = validate_decision(d)
        if utc(item["as_of_utc"]) > now:
            raise ValueError("H120_FUTURE_STUDY_DECISION")
        candidates.append(event(
            "SEALED_STUDY_DECISION",
            item["study_id"] + ":" + d["sha256"],
            {"study_id": item["study_id"], "decision": item["assessment"]["decision"],
             "stage": "FINAL", "source_commit": d["commit"],
             "source_file_hash": d["sha256"],
             "approved_strategy": False,
             "reasons": str(item["assessment"].get("reason", ""))[:320]},
            now.isoformat()))
    gap_h = (now - observed).total_seconds() / 3600
    if gap_h >= STALE_HOURS:
        candidates.append(event(
            "SOURCE_AUDIT_STALE",
            evidence["source_commits"][AUDIT] + ":" + observed.isoformat(),
            {"last_audit_utc": observed.isoformat(),
             "hours_without_audit": round(gap_h, 1),
             "source_commit": evidence["source_commits"][AUDIT],
             "approved_strategy": False},
            now.isoformat()))
    report = {
        "schema": SCHEMA,
        "asof_utc": now.isoformat(),
        "tier1_audit_utc": observed.isoformat(),
        "audit_age_hours": round(gap_h, 2),
        "source": UPSTREAM, "source_commits": evidence["source_commits"],
        "source_hashes": evidence["source_hashes"],
        "observed_calls": len(evidence["ledger"]["calls"]),
        "observed_snapshots": len(evidence["ledger"]["snapshots"]),
        "entry_allowed": evidence["summary"]["entry_allowed"],
        "grades": grades,
        "descriptive_asset_diagnostics": descriptive_asset_review(evidence["ledger"]),
        "final_study_decisions": [
            {"study": validate_decision(d)["study_id"],
             "decision": d["data"]["assessment"]["decision"],
             "sha256": d["sha256"]} for d in evidence["decision_docs"]],
        "replication_leads_not_accepts": sum(
            g["grade"] == "REPLICATION_LEAD_REQUIRES_NATIVE_LAB_TEST"
            for g in grades.values()),
        "production_logic": "UNCHANGED",
        "research_only": True,
        "official_gate": "NOT_RUN",
        "limitations": [
            "Only tier1_quant_terminal independent audit and sealed decisions are read",
            "Model directional scores do not imply permitted/executed trades",
            "Source quotes are delayed proxies, not executable entries or fills",
            "Per-asset raw grades overlap and are descriptive, not independent alpha",
            "30-day observations lack 3-year OOS, independent PIT and brokerage NAV",
            "No automatic hypothesis/registry update, paper reset or live model changes",
        ],
    }
    return report, candidates


def run(state_path, fetch=http_text, current=None):
    now = current or now_utc()
    root = Path(state_path)
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "manifest.json"
    old_manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    if old_manifest and old_manifest.get("schema") != SCHEMA:
        raise ValueError("H120_UNRECOGNIZED_STATE_SCHEMA")
    # Refuse corrupt or partially deleted records.
    existing = read_ledger(root / "events.jsonl")
    read_ledger(root / "receipts.jsonl")
    if old_manifest and not (root / "events.jsonl").exists():
        raise ValueError("H120_PREVIOUS_EVIDENCE_MISSING")
    evidence = fetch_evidence(old_manifest.get("source_commits", {}), fetch)
    report, candidates = evaluate(evidence, old_manifest, now)
    events = append_ledger(root / "events.jsonl", candidates)
    # An empty but present journal is a valid evidence baseline. Without
    # this marker, a quiet first run would look like lost history on poll 2.
    (root / "events.jsonl").touch(exist_ok=True)
    receipts_path = root / "receipts.jsonl"
    receipts_path.touch(exist_ok=True)
    receipts = read_ledger(receipts_path)
    notified = {r["event_id"] for r in receipts}
    pending = sum(e["kind"] in NOTIFY_KINDS and e["id"] not in notified for e in events)
    report.update({
        "total_events": len(events),
        "new_events": len(events) - len(existing),
        "pending_notifications": pending,
        "state_branch": "research/h120-tier1-evidence",
    })
    manifest = {
        "schema": SCHEMA, "source_commits": evidence["source_commits"],
        "calls_seen": len(evidence["ledger"]["calls"]),
        "last_poll_utc": now.isoformat(),
        "last_audit_utc": report["tier1_audit_utc"],
        "no_production_changes": True,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8")
    (root / "latest.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True)
    a = parser.parse_args()
    report = run(a.state)
    print("H120_TIER1_ONLY source audit", report["tier1_audit_utc"])
    print("H120_GRADES", canonical(report["grades"]))
    print("H120_NEW_EVENTS", report["new_events"],
          "H120_PENDING_ALERTS", report["pending_notifications"])
    summary_file = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a", encoding="utf-8") as out:
            out.write("# H120 Tier-1 independent intelligence (research-only)\n\n")
            out.write("Audit observed: " + report["tier1_audit_utc"] + " UTC\n\n")
            out.write("No production model, state, acceptance gate or PAPER changed.\n\n")
            out.write("| Horizon | N | Model | Always long | Adjusted p | Verdict |\n")
            out.write("|---|---:|---:|---:|---:|---|\n")
            for h, g in report["grades"].items():
                out.write(f"| {h}h | {g['observations']} | {g['model_hit']} "
                          f"| {g['always_long_hit']} | {g['bonferroni_12_p']} "
                          f"| {g['grade']} |\n")


if __name__ == "__main__":
    main()
