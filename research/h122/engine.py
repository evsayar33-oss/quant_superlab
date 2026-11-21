"""H122: Federal Incentive Radar evidence and prospective cohort integrity.

Two independent tracks:
  * H083 two monthly style-rotation PAPER families (not news-event alpha).
  * five frozen 20-session news/event causal hypotheses (not H083 fills).

Nothing in this module can make trades, claim executable fills, promote
quant_superlab ACCEPT, or change Radar data, research protocols or models.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from research import bridge_guard as b

SCHEMA = "QS.h122.federal_evidence.v1"
SOURCE = "evsayar33-oss/federal-incentive-radar"
BRANCH = "data"
H083_RULES = {"monthly_low_beta", "monthly_vol_squeeze"}
EVENT_HYPOTHESES = (
    "FEDERAL_DIRECT_20D", "POLICY_REGULATORY_20D",
    "FEDERAL_PRESTRENGTH_20D", "FEDERAL_SECTOR_LEAD_20D",
    "DIRECT_PRIVATE_RECIPIENT_20D",
)
REQUIRED = (
    "h083_last_attempt.json", "event_watch_status.json",
    "economic_intelligence_status.json",
)
OPTIONAL = ("h083_forward_status.json",)
WORKFLOWS = ("h083_forward.yml", "alpha_discovery.yml")


def finite_number(x, minimum=None, maximum=None):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ValueError("H122_INVALID_SOURCE_NUMBER")
    if minimum is not None and x < minimum:
        raise ValueError("H122_NEGATIVE_SOURCE_NUMBER")
    if maximum is not None and x > maximum:
        raise ValueError("H122_SOURCE_METRIC_TOO_HIGH")
    return x


def collect(fetch=b.request):
    # Federal Radar data branch is an operational snapshot that CAN be
    # replaced; record the source SHA and per-file hashes at each poll.
    # Do NOT apply an append-only GitHub ancestry assertion to this branch.
    sha = b.get_sha(SOURCE, BRANCH, fetch)
    payloads, hashes = {}, {}
    for path in REQUIRED + OPTIONAL:
        try:
            content, check = b.pinned(SOURCE, sha, path, fetch)
        except urllib.error.HTTPError as err:
            if path in OPTIONAL and err.code == 404:
                payloads[path] = None
                continue
            raise
        payloads[path] = json.loads(content)
        hashes[path] = check
    workflows = {}
    for wf in WORKFLOWS:
        url = (f"https://api.github.com/repos/{SOURCE}/actions/workflows/"
               f"{wf}/runs?per_page=1")
        try:
            values = json.loads(fetch(url))
            runs = values.get("workflow_runs", [])
            if runs:
                run = runs[0]
                workflows[wf] = {
                    "id": run.get("id"), "event": run.get("event"),
                    "status": run.get("status"), "conclusion": run.get("conclusion"),
                    "created_at": run.get("created_at"),
                    "head_sha": run.get("head_sha"),
                }
            else:
                workflows[wf] = {"status": "NO_RUN_AVAILABLE"}
        except urllib.error.HTTPError:
            # API access or optional metadata can fail without contaminating
            # official source evidence or pretending a successful workflow.
            workflows[wf] = {"status": "RUN_METADATA_UNAVAILABLE"}
    return sha, payloads, hashes, workflows


def validate(sha, data, now):
    attempt = data["h083_last_attempt.json"]
    watch = data["event_watch_status.json"]
    econ = data["economic_intelligence_status.json"]
    forward = data.get("h083_forward_status.json")
    if attempt.get("state") not in ("SKIPPED", "FAILED", "COMPLETED_RESEARCH"):
        raise ValueError("H122_UNRECOGNIZED_H083_ATTEMPT_STATE")
    if not isinstance(attempt.get("attempt_id"), str) or not attempt["attempt_id"]:
        raise ValueError("H122_MISSING_ATTEMPT_ID")
    when = b.utc(attempt["attempted_at_utc"])
    if when > now:
        raise ValueError("H122_ATTEMPT_FROM_FUTURE")
    # COMPLETED_RESEARCH means the after-close observer ran, not that a
    # monthly cohort matured. The source explicitly publishes False when
    # there are zero completed forward months; this is valid evidence.
    if attempt["state"] == "SKIPPED" and attempt.get("counts_as_forward_month") is not False:
        raise ValueError("H122_SKIPPED_CANNOT_COUNT_AS_FORWARD")
    if (watch.get("watch_only") is not True
            or watch.get("validated_alpha") is not False
            or watch.get("decision") != "WATCH_ONLY_NO_TRADE"):
        raise ValueError("H122_WATCH_IS_MISREPRESENTED_AS_APPROVED_ALPHA")
    # Source data outage is a real observable research state, not alpha.
    # Preserve the outage and emit a coverage alert rather than terminating
    # before our independent evidence and notification receipts are written.
    if watch.get("ok") not in (True, False):
        raise ValueError("H122_WATCH_REPORT_STATUS_UNKNOWN")
    if watch["ok"] is False:
        if (watch.get("data_coverage_ok") is not False
                or watch.get("candidates") != 0
                or not isinstance(watch.get("reason"), str)
                or not watch["reason"].strip()):
            raise ValueError("H122_UNSAFE_WATCH_OUTAGE_REPORT")
    watch_time = b.utc(watch["generated_at_utc"])
    if watch_time > now:
        raise ValueError("H122_WATCH_GENERATED_IN_FUTURE")
    finite_number(watch["data_coverage_pct"], 0, 1)
    for key in ("eligible_tickers", "priced_tickers", "candidates",
                "liquid_tickers", "excluded_tickers",
                "source_first_seen_forward_only"):
        finite_number(watch[key], 0)
    if (watch["priced_tickers"] > watch["eligible_tickers"]
            or watch["liquid_tickers"] > watch["priced_tickers"]):
        raise ValueError("H122_COVERAGE_COUNTS_INCONSISTENT")
    if not set(watch.get("by_rule", {})).issubset(H083_RULES):
        raise ValueError("H122_UNKNOWN_H083_STYLE_RULE")
    if watch["candidates"] != sum(watch["by_rule"].values()):
        raise ValueError("H122_STYLE_CANDIDATES_NOT_RECONCILED")
    if econ.get("research_only") is not True:
        raise ValueError("H122_ECON_INTELLIGENCE_IS_NOT_RESEARCH_ONLY")
    if b.utc(econ["generated_at_utc"]) > now:
        raise ValueError("H122_FUTURE_ECONOMIC_RESEARCH")
    for key in ("new_relationships", "total_relationships",
                "pending_primary_verification"):
        finite_number(econ[key], 0)
    if forward:
        if forward.get("ok") is not True or forward.get("broker_ordering") is not False or forward.get("information_only") is not True:
            raise ValueError("H122_UNSAFE_FORWARD_STATUS")
        if set(forward.get("monitor_rules", [])) != H083_RULES:
            raise ValueError("H122_WRONG_FORWARD_STYLES")
        if forward.get("research_approved_styles") != 0:
            raise ValueError("H122_HISTORICAL_ALPHA_MISLABELED_AS_APPROVED")
        if b.utc(forward["generated_utc"]) > now:
            raise ValueError("H122_FORWARD_STATUS_IN_FUTURE")
        finite_number(forward["forward_months_closed"], 0)
        finite_number(forward["cohorts_frozen_this_run"], 0)
        if not set(forward.get("approved_paper_rules", [])).issubset(H083_RULES):
            raise ValueError("H122_UNKNOWN_APPROVED_PAPER_STYLE")
    return attempt, watch, econ, forward


def notice(kind, identity, message, now):
    return {
        "lane": "H122", "kind": kind,
        "id": b.hashobj([SCHEMA, kind, identity]),
        "source_repo": SOURCE, "observed_at_utc": now.isoformat(),
        "message": message, "official_lab_status": "NOT_RUN",
        "broker_trade_authorized": False,
    }


def evaluate(sha, data, hashes, workflows, previous, now):
    attempt, watch, econ, forward = validate(sha, data, now)
    last_attempt = {
        "state": attempt["state"],
        "reason": attempt.get("reason"),
        "session": attempt.get("session"),
        "attempt_id": attempt["attempt_id"],
        "attempted_at_utc": attempt["attempted_at_utc"],
        "counts_as_forward_month": attempt.get("counts_as_forward_month"),
    }
    current_forward = None if not forward else {
        "generated_utc": forward["generated_utc"],
        "last_complete_nyse_session": forward["last_complete_nyse_session"],
        "cohorts_frozen_this_run": forward["cohorts_frozen_this_run"],
        "forward_months_closed": forward["forward_months_closed"],
        "approved_paper_rules": list(forward["approved_paper_rules"]),
        "data_coverage_ok": forward["data_coverage_ok"],
    }
    skip_streak = previous.get("h083_skipped_session_streak", 0)
    events = []
    old_attempt = previous.get("h083_attempt", {})
    new_attempt = attempt["attempt_id"] != old_attempt.get("attempt_id")
    if new_attempt and attempt["state"] == "COMPLETED_RESEARCH":
        skip_streak = 0
    elif new_attempt and attempt["state"] == "SKIPPED":
        if last_attempt.get("session") != old_attempt.get("session"):
            skip_streak += 1
    elif new_attempt and attempt["state"] == "FAILED":
        skip_streak = 0
    if previous:
        old_watch = previous["watch"]
        old_forward = previous.get("forward")
        if forward is None and old_forward is not None:
            raise ValueError("H122_PUBLISHED_H083_FORWARD_RESULT_DISAPPEARED")
        if forward is not None and old_forward and forward["forward_months_closed"] < old_forward["forward_months_closed"]:
            raise ValueError("H122_CLOSED_FORWARD_MONTHS_DISAPPEARED")
        if old_attempt and b.utc(attempt["attempted_at_utc"]) < b.utc(old_attempt["attempted_at_utc"]):
            # Mutable data branch may be replaced, but silently reverting
            # the last recorded attempt is still not a valid new result.
            raise ValueError("H122_H083_ATTEMPT_ROLLED_BACK")
        if new_attempt and attempt["state"] == "FAILED":
            events.append(notice("H083_RUN_FAILED", last_attempt["attempt_id"],
                f"Federal Radar H083 kaynak calismasi FAILED: {attempt.get('reason', 'UNKNOWN')}. "
                "Basarili islem ayina sayilmaz; geriye veri doldurulmaz.", now))
        if skip_streak >= 3 and previous.get("h083_skipped_session_streak", 0) < 3:
            events.append(notice("H083_REPEATED_SKIPPED_SESSIONS", last_attempt.get("session"),
                f"H083 >=3 farkli seans boyunca SKIPPED raporlandi. Son neden: "
                f"{attempt.get('reason')}. GitHub yesil olmasi  ileri test kaniti degildir.", now))
        if old_watch["data_coverage_ok"] and not watch["data_coverage_ok"]:
            events.append(notice("H083_COVERAGE_LOST", watch["feature_asof"],
                f"Radar fiyat/veri kapsama yeterliligi kaybedildi: %{100*watch['data_coverage_pct']:.1f}. "
                "Yeni adaylarin PAPER onayi degil, kaynak riski bildirimi.", now))
        if current_forward and old_forward:
            if current_forward["forward_months_closed"] > old_forward["forward_months_closed"]:
                events.append(notice("NEW_MATURED_H083_MONTH", str(current_forward["forward_months_closed"]),
                    f"H083 yeni tamamlanmis PAPER ay kaydi: {old_forward['forward_months_closed']} -> "
                    f"{current_forward['forward_months_closed']}. SPY ustunlugu veya net alpha henuz kanitlanmadi.", now))
            if set(current_forward["approved_paper_rules"]) - set(old_forward["approved_paper_rules"]):
                events.append(notice("SOURCE_DECLARED_FORWARD_VALIDATED_PAPER",
                    b.hashobj(current_forward["approved_paper_rules"]),
                    "Radar H083 kaynak sistemi FORWARD_VALIDATED_PAPER etiketi bildirdi. "
                    "Bu yalnızca kaynak kararıdır; bağımsız QS analizi ve gercek broker fill kaniti "
                    "olmadan ACCEPT veya otomatik emir izni degildir.", now))
        if forward is not None and old_forward is None:
            events.append(notice("FIRST_PUBLISHED_H083_FORWARD_REPORT",
                forward["generated_utc"],
                "Radar ilk dogrulanabilir H083 ileri arastirma raporunu yayimladi. "
                "Sonuc PAPER ve info-only; QS ACCEPT degildir.", now))
        if econ["pending_primary_verification"] >= 10 and previous["econ"].get("pending_primary_verification", 0) < 10:
            events.append(notice("PRIMARY_RELATIONSHIP_REVIEW_BACKLOG",
                str(econ["pending_primary_verification"]),
                f"Radar {econ['pending_primary_verification']} birincil kaynak dogrulamasi "
                "bekleyen ekonomik iliski gosteriyor; haberler kanitli anlasma degildir.", now))
    report = {
        "source_repo": SOURCE, "data_branch": BRANCH, "source_commit_sha": sha,
        "source_hashes": hashes, "asof_utc": now.isoformat(),
        "h083": {
            "research_tracks": sorted(H083_RULES),
            "last_attempt": last_attempt,
            "skipped_session_streak_since_h122_start": skip_streak,
            "published_forward_report": current_forward,
            "forward_results_status": (
                "PUBLISHED_SOURCE_ONLY_NOT_SUPERLAB_APPROVED" if forward
                else "NO_PUBLISHED_H083_FORWARD_JSON"),
            "green_workflow_is_not_forward_result": True,
        },
        "event_watch": {
            "feature_asof": watch["feature_asof"],
            "data_coverage_pct": watch["data_coverage_pct"],
            "data_coverage_ok": watch["data_coverage_ok"],
            "source_report_ok": watch["ok"],
            "source_failure_reason": watch.get("reason") if watch["ok"] is False else None,
            "eligible_tickers": watch["eligible_tickers"],
            "priced_tickers": watch["priced_tickers"],
            "liquid_tickers": watch["liquid_tickers"],
            "watch_candidates": watch["candidates"],
            "candidate_counts_by_rule": watch["by_rule"],
            "source_first_seen_forward_only": watch["source_first_seen_forward_only"],
            "source_decision": "WATCH_ONLY_NO_TRADE",
        },
        "economic_relationships": {
            "recorded": econ["total_relationships"],
            "pending_primary_verification": econ["pending_primary_verification"],
            "research_only": True,
        },
        "five_event_hypotheses": {
            "fixed_names": EVENT_HYPOTHESES,
            "source_workflow": workflows.get("alpha_discovery.yml"),
            "published_forward_20_session_net_scores": "NOT_AVAILABLE_AS_READABLE_SOURCE",
            "matured_positions": None,
            "SPY_relative_alpha": "NOT_EVALUATED",
            "never_use_h083_rotation_as_event_alpha": True,
        },
        "workflow_metadata": workflows,
        "two_strategy_families_never_combined": True,
        "original_lab_gate": "NOT_RUN",
        "no_official_alpha_approval": True,
        "executable_broker_pnl": None,
        "data_branch_sha_may_be_replaced": True,
        "known_limitations": [
            "Green H083 Actions run may safely skip on after-close NYSE time guard",
            "H083 monthly rotations are not event-specific causal price effects",
            "Five 20-session event hypotheses publish artifacts not parsed as verified returns here",
            "Data branch is mutable/replaced: source commit and SHA checks enable snapshot provenance, not permanent upstream immutability",
            "Yahoo adjusted daily bars and post-close proxies are not actual Midas fills",
            "No automatic research or trade approvals from source watch candidates",
        ],
    }
    manifest = {
        "last_source_commit": sha, "h083_attempt": last_attempt,
        "h083_skipped_session_streak": skip_streak,
        "watch": {
            "data_coverage_ok": watch["data_coverage_ok"],
            "data_coverage_pct": watch["data_coverage_pct"],
            "feature_asof": watch["feature_asof"],
        },
        "forward": current_forward,
        "econ": {"pending_primary_verification": econ["pending_primary_verification"]},
        "seen_utc": now.isoformat(),
    }
    return report, manifest, events


def run(state, fetch=b.request, now=None):
    now = now or datetime.now(timezone.utc)
    old = b.read_manifest(state, SCHEMA)
    sha, data, hashes, workflows = collect(fetch)
    report, manifest, events = evaluate(sha, data, hashes, workflows, old, now)
    result = b.record(state, SCHEMA, manifest, report, events)
    print("H122_FEDERAL", b.canonical({
        "last_attempt": result["h083"]["last_attempt"]["state"],
        "last_reason": result["h083"]["last_attempt"]["reason"],
        "watch_candidates": result["event_watch"]["watch_candidates"],
        "published_forward": bool(result["h083"]["published_forward_report"]),
        "alerts": result["alerts_pending"], "events_new": result["events_new"],
    }))
    return result


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--state", required=True)
    args = a.parse_args()
    result = run(args.state)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.getenv("GITHUB_STEP_SUMMARY"), "a") as f:
            f.write("# H122 Federal Radar intelligence / research-only\n\n")
            f.write("H083 last result: " + result["h083"]["last_attempt"]["state"] +
                    " — " + str(result["h083"]["last_attempt"]["reason"]) + "\n\n")
            f.write("Watch-only candidates: " + str(result["event_watch"]["watch_candidates"]) + "\n\n")
            f.write("Forward result: " + result["h083"]["forward_results_status"] + "\n\n")
            f.write("SPY-relative event alpha is NOT EVALUATED from unreadable artifacts.\n\n")


if __name__ == "__main__":
    main()
