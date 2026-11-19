"""H119 autonomous *research* bridge. No trading or lab ACCEPT mutation.

Ingest immutable, commit-pinned SHA-verified evidence from early_accumulation_radar.
Re-check economic sample gates, pre-register research proposals, and only queue
substantive milestones. Original quant_superlab validation.GATE remains authoritative.
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

UPSTREAM = "evsayar33-oss/early_accumulation_radar"
SCHEMA = "QS.h119.autonomous_alpha.v1"
BRANCHES = {
    "equity": "research/v13-alpha-evidence",
    "crypto": "research/v13-crypto-alpha-evidence",
    "patterns": "research/v12-equity-pattern-evidence",
}
FILES = {
    "equity": (
        "research_archive/v13/latest.json",
        "research_archive/v13/BIST/frozen.jsonl",
        "research_archive/v13/BIST/decisions.jsonl",
        "research_archive/v13/US/frozen.jsonl",
        "research_archive/v13/US/decisions.jsonl",
    ),
    "crypto": (
        "research_archive/v13_crypto/latest.json",
        "research_archive/v13_crypto/frozen.jsonl",
        "research_archive/v13_crypto/decisions.jsonl",
    ),
    "patterns": (
        "research_archive/v12/BIST/latest.json",
        "research_archive/v12/BIST/frozen.jsonl",
        "research_archive/v12/BIST/decisions.jsonl",
        "research_archive/v12/US/latest.json",
        "research_archive/v12/US/frozen.jsonl",
        "research_archive/v12/US/decisions.jsonl",
    ),
}
ELIGIBLE_EVENT_TYPES = {
    "COSTED_RESEARCH_CANDIDATE", "FUTURE_TRIAL_FROZEN",
    "POSITIVE_FORWARD_RESEARCH", "NEW_LAB_ACCEPT",
    "LAB_ACCEPT_REVOKED", "NOTIFICATION_READY",
}
NOTIFY_EVENT_TYPES = ELIGIBLE_EVENT_TYPES
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
RULE_RE = re.compile(r"^[a-z0-9_ +\-]{1,120}$")
MARKETS = ("BIST", "US", "CRYPTO_PERPETUAL")
SIDES = ("LONG", "SHORT")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def event_id(*parts):
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()


def now_utc():
    return datetime.now(timezone.utc)


def parse_date(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("NAIVE_SOURCE_TIME")
    return result.astimezone(timezone.utc)


def read_chain(path):
    path = Path(path)
    if not path.exists():
        return []
    prev = "GENESIS"
    last = -1
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        record = {k: v for k, v in item.items() if k != "sha256"}
        tick = record.get("scan_utc_ms")
        if (record.get("prev_sha256") != prev
                or item.get("sha256") != digest(record)
                or not isinstance(tick, int) or tick <= last):
            raise ValueError("H119_LEDGER_TAMPERED_OR_REORDERED")
        result.append(item)
        prev, last = item["sha256"], tick
    return result


def append_chain(path, entries, base_ms):
    existing = read_chain(path)
    seen = {x["id"] for x in existing}
    new = [x for x in entries if x["id"] not in seen]
    if not new:
        return existing
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    last = existing[-1]["scan_utc_ms"] if existing else 0
    prev = existing[-1]["sha256"] if existing else "GENESIS"
    with Path(path).open("a", encoding="utf-8") as stream:
        for i, item in enumerate(new):
            row = dict(item)
            row["scan_utc_ms"] = max(last + 1, base_ms + i)
            row["prev_sha256"] = prev
            row["sha256"] = digest(row)
            stream.write(canonical(row) + "\n")
            existing.append(row)
            prev, last = row["sha256"], row["scan_utc_ms"]
    return existing


def http_text(url):
    headers = {
        "User-Agent": "quant-superlab-h119-read-only/1",
        "Accept": "application/vnd.github+json" if "api.github.com" in url
                  else "text/plain",
    }
    # Public unauthenticated GitHub REST calls have a small shared runner
    # quota. Use the ephemeral Actions token for API calls only. Never print
    # the token, URL authorization parameters or request headers.
    if url.startswith("https://api.github.com/"):
        token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        if token:
            headers["Authorization"] = "Bearer " + token
            headers["X-GitHub-Api-Version"] = "2022-11-28"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=22) as res:
        return res.read().decode("utf-8")


def fetch_sources(previous_commits, fetch=http_text):
    """Pin every input to a Git commit SHA, refusing source history rollback."""
    result = {}
    commits = {}
    for key, branch in BRANCHES.items():
        ref = json.loads(fetch(
            "https://api.github.com/repos/" + UPSTREAM +
            "/git/ref/heads/" + branch))
        sha = ref["object"]["sha"]
        if not SHA_RE.fullmatch(sha):
            raise ValueError("INVALID_UPSTREAM_COMMIT")
        old = previous_commits.get(key)
        if old and old != sha:
            if not SHA_RE.fullmatch(old):
                raise ValueError("INVALID_STORED_UPSTREAM_COMMIT")
            compare = json.loads(fetch(
                "https://api.github.com/repos/" + UPSTREAM +
                "/compare/" + old + "..." + sha))
            if (compare.get("status") != "ahead"
                    or compare.get("behind_by") != 0
                    or compare.get("ahead_by", 0) <= 0):
                raise ValueError("UPSTREAM_EVIDENCE_REWRITE_OR_REWIND")
        files = {}
        for path in FILES[key]:
            url = ("https://raw.githubusercontent.com/" + UPSTREAM +
                   "/" + sha + "/" + path)
            data = fetch(url)
            files[path] = data
        result[key] = files
        commits[key] = sha
    return result, commits


def verify_upstream_ledger(text):
    prev, last = "GENESIS", 0
    output = []
    for line in text.splitlines():
        row = json.loads(line)
        record = {k: v for k, v in row.items() if k != "sha256"}
        timestamp = row.get("scan_utc_ms")
        if (record.get("prev_sha256") != prev
                or row.get("sha256") != digest(record)
                or not isinstance(timestamp, int) or timestamp <= last):
            raise ValueError("UPSTREAM_SHA_CHAIN_OR_CLOCK_INVALID")
        prev, last = row["sha256"], timestamp
        output.append(row)
    return output


def validate_rule(rule, market, side, horizon):
    if (market not in MARKETS or side not in SIDES
            or not isinstance(rule, str) or not RULE_RE.fullmatch(rule)
            or not isinstance(horizon, int) or horizon <= 0 or horizon > 365):
        raise ValueError("UNTRUSTED_HYPOTHESIS_FIELDS")


def positive_equity(x):
    """Independently check the V13 research gate, not a lab ACCEPT."""
    def num(k):
        v = x.get(k)
        return v if isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v) else None

    return (
        x.get("passes_fixed_research_gates") is True
        and num("hypothetical_closed_trades") is not None and num("hypothetical_closed_trades") >= 30
        and num("matched_control_events") is not None and num("matched_control_events") >= 60
        and num("distinct_symbols") is not None and num("distinct_symbols") >= 8
        and num("signal_days") is not None and num("signal_days") >= 12
        and num("net_mean_pct") is not None and num("net_mean_pct") > 0.35
        and num("stressed_net_mean_pct") is not None and num("stressed_net_mean_pct") > 0
        and num("excess_vs_matched_control_pct") is not None and num("excess_vs_matched_control_pct") > 0.35
        and num("closed_profit_factor") is not None and num("closed_profit_factor") >= 1.25
        and num("stressed_ten_day_block_lower_bound_pct") is not None
        and num("stressed_ten_day_block_lower_bound_pct") > 0
    )


def positive_crypto(x):
    def num(k):
        v = x.get(k)
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else None
    return (
        x.get("fixed_costed_research_gates_pass") is True
        and num("hypothetical_mark_trades") is not None and num("hypothetical_mark_trades") >= 35
        and num("controls") is not None and num("controls") >= 100
        and num("distinct_symbols") is not None and num("distinct_symbols") >= 12
        and num("distinct_days") is not None and num("distinct_days") >= 6
        and num("mean_model_net_pct") is not None and num("mean_model_net_pct") >= 0.20
        and num("stressed_mean_net_pct") is not None and num("stressed_mean_net_pct") > 0
        and num("excess_over_matched_controls_pct") is not None
        and num("excess_over_matched_controls_pct") >= 0.20
        and num("profit_factor") is not None and num("profit_factor") >= 1.3
        and num("multiplicity_screen_lower_pct") is not None
        and num("multiplicity_screen_lower_pct") > 0
    )


def event(kind, market, rule, side, horizon, origin_id, payload, version, source_sha):
    validate_rule(rule, market, side, horizon)
    if kind not in ELIGIBLE_EVENT_TYPES:
        raise ValueError("UNKNOWN_H119_KIND")
    return {
        "schema": SCHEMA, "kind": kind,
        "id": event_id(kind, market, side, rule, horizon, origin_id),
        "market": market, "rule": rule, "side": side,
        "horizon": horizon, "source_event_id": str(origin_id),
        "source_methodology_sha256": version,
        "source_commit_sha": source_sha,
        "source_repository": UPSTREAM,
        "evidence": payload,
        "lab_validation": "NOT_RUN",
        "lab_verdict": "NOT_EVALUATED",
        "real_money_trade_authorized": False,
        "full_pit_verified": False,
        "verified_actual_fills": False,
    }


def analyze(sources, commits, registry, now=None):
    """Evidence-based proposals; never writes official hypothesis registry."""
    now = now or now_utc()
    events = []
    summary = {}
    # V12 flags are descriptive, NEVER costed alpha claims.
    v12 = {}
    for market in ("BIST", "US"):
        prefix = "research_archive/v12/" + market + "/"
        report = json.loads(sources["patterns"][prefix + "latest.json"])
        if (report.get("schema") != "EAR.v12_equity_discovery.v1"
                or report.get("market") != market
                or report.get("limitations", {}).get("trade_authorized") is not False):
            raise ValueError("UNTRUSTED_V12_MARKET_REPORT")
        if parse_date(report["asof_utc"]) > now:
            raise ValueError("FUTURE_DATED_V12_REPORT")
        v12[market] = report
        for name in ("frozen", "decisions"):
            verify_upstream_ledger(sources["patterns"][prefix + name + ".jsonl"])
    # Equity 64 x 2, stage independent of V12 anomaly scores.
    equity_prefix = "research_archive/v13/"
    eq = json.loads(sources["equity"][equity_prefix + "latest.json"])
    if (eq.get("schema") != "EAR.v13_costed_profitability_discovery.v1"
            or eq.get("trade_authorized") is not False
            or eq.get("paper_approved") is not False
            or eq.get("profitable_strategy_proven") is not False
            or parse_date(eq["asof_utc"]) > now):
        raise ValueError("UNTRUSTED_EQUITY_COSTED_REPORT")
    for market in ("BIST", "US"):
        segment = eq["markets"][market]
        stats = segment["all_trial_statistics"]
        if (len(stats) != segment["rule_horizon_trials"]
                or len(stats) < 64):
            raise ValueError("MISSING_EQUITY_SEARCH_TRIALS")
        positive = 0
        by_rule = {}
        for x in stats:
            rule, horizon = x["rule"], x["horizon_sessions"]
            validate_rule(rule, market, "LONG", horizon)
            key = (rule, horizon)
            if key in by_rule:
                raise ValueError("DUPLICATE_EQUITY_VARIANT")
            by_rule[key] = x
            if positive_equity(x):
                positive += 1
                events.append(event(
                    "COSTED_RESEARCH_CANDIDATE", market, rule, "LONG", horizon,
                    eq["methodology_sha256"] + ":" + rule + ":" + str(horizon),
                    {"net_mean_pct": x["net_mean_pct"],
                     "cost_stress_pct": x["stressed_net_mean_pct"],
                     "matched_excess_pct": x["excess_vs_matched_control_pct"],
                     "n": x["hypothetical_closed_trades"],
                     "profit_factor": x["closed_profit_factor"],
                     "status": "EXPLORATORY_RESEARCH_NOT_ACCEPT"},
                    eq["methodology_sha256"], commits["equity"]))
        frozen = verify_upstream_ledger(sources["equity"][
            equity_prefix + market + "/frozen.jsonl"])
        decisions = verify_upstream_ledger(sources["equity"][
            equity_prefix + market + "/decisions.jsonl"])
        if (len(frozen) != segment["frozen_total"]
                or len(decisions) != segment["completed_forward_decisions_total"]):
            raise ValueError("EQUITY_SOURCE_REPORT_ARCHIVE_MISMATCH")
        frozen_ids = set()
        for x in frozen:
            rule, horizon = x["rule"], x["horizon_sessions"]
            validate_rule(rule, market, "LONG", horizon)
            if x.get("market") != market or not positive_equity(x["selection_evidence"]):
                raise ValueError("UNQUALIFIED_EQUITY_FROZEN_PATTERN")
            frozen_ids.add(x["id"])
            events.append(event(
                "FUTURE_TRIAL_FROZEN", market, rule, "LONG", horizon,
                x["id"], {"trial_start_utc": x["trial_start_utc"],
                          "trial_end_utc": x["trial_end_utc"],
                          "status": "FUTURE_VALIDATION_PENDING"},
                x["methodology_sha256"], commits["equity"]))
        for x in decisions:
            if x["hypothesis_id"] not in frozen_ids or x["market"] != market:
                raise ValueError("EQUITY_DECISION_WITHOUT_FROZEN_TRIAL")
            if x["status"] == "POSITIVE_NET_FORWARD_RESEARCH_ONLY":
                h = x["future_costed_metrics"]
                if not positive_equity(h):
                    raise ValueError("SOURCE_FORWARD_POSITIVE_GATE_INCONSISTENT")
                events.append(event(
                    "POSITIVE_FORWARD_RESEARCH", market,
                    x["rule"], "LONG", x["horizon_sessions"],
                    x["id"], {"status": x["status"],
                              "net_mean_pct": h["net_mean_pct"],
                              "n": h["hypothetical_closed_trades"],
                              "cost_stress_pct": h["stressed_net_mean_pct"],
                              "profit_factor": h["closed_profit_factor"]},
                    x["methodology_sha256"], commits["equity"]))
        summary[market] = {
            "source_reported_variants": len(stats),
            "costed_research_candidates": positive,
            "forward_trials_frozen": len(frozen),
            "future_test_decisions": len(decisions),
            "matured_first_seen_horizon_counts": segment["v12_matured_outcomes"],
            "v12_pre_move_observations": v12[market]["asof_observations_total"],
        }

    # Crypto 92 variants, independently priced future perpetual marks.
    crypto_prefix = "research_archive/v13_crypto/"
    cr = json.loads(sources["crypto"][crypto_prefix + "latest.json"])
    if (cr.get("schema") != "EAR.v13_crypto_costed_research.v1"
            or cr.get("limitations", {}).get("trade_authorized") is not False
            or parse_date(cr["asof_utc"]) > now
            or len(cr["all_rule_horizon_results"]) != cr["strategy_variants_tested"]
            or cr["strategy_variants_tested"] < 92):
        raise ValueError("UNTRUSTED_CRYPTO_COSTED_REPORT")
    positive = 0
    keys = set()
    for x in cr["all_rule_horizon_results"]:
        rule, side, horizon = x["rule"], x["direction"], x["horizon_minutes"]
        validate_rule(rule, "CRYPTO_PERPETUAL", side, horizon)
        if (rule, side, horizon) in keys:
            raise ValueError("DUPLICATE_CRYPTO_VARIANT")
        keys.add((rule, side, horizon))
        if positive_crypto(x):
            positive += 1
            events.append(event(
                "COSTED_RESEARCH_CANDIDATE", "CRYPTO_PERPETUAL", rule,
                side, horizon, cr["methodology_sha256"] +
                ":" + rule + ":" + side + ":" + str(horizon),
                {"net_mean_pct": x["mean_model_net_pct"],
                 "cost_stress_pct": x["stressed_mean_net_pct"],
                 "matched_excess_pct": x["excess_over_matched_controls_pct"],
                 "n": x["hypothetical_mark_trades"],
                 "profit_factor": x["profit_factor"],
                 "status": "MODELLED_NOT_EXECUTABLE_PNL"},
                cr["methodology_sha256"], commits["crypto"]))
    frozen = verify_upstream_ledger(
        sources["crypto"][crypto_prefix + "frozen.jsonl"])
    decisions = verify_upstream_ledger(
        sources["crypto"][crypto_prefix + "decisions.jsonl"])
    if (len(frozen) != cr["frozen_trials"]
            or len(decisions) != cr["completed_forward_trials"]):
        raise ValueError("CRYPTO_SOURCE_REPORT_ARCHIVE_MISMATCH")
    frozen_ids = set()
    for x in frozen:
        validate_rule(x["rule"], "CRYPTO_PERPETUAL",
                      x["direction"], x["horizon_minutes"])
        if not positive_crypto(x["training_evidence"]):
            raise ValueError("UNQUALIFIED_CRYPTO_FROZEN_TRIAL")
        frozen_ids.add(x["id"])
        events.append(event(
            "FUTURE_TRIAL_FROZEN", "CRYPTO_PERPETUAL", x["rule"],
            x["direction"], x["horizon_minutes"], x["id"],
            {"trial_start_utc": x["trial_start_utc"],
             "trial_end_utc": x["trial_end_utc"],
             "status": "FUTURE_VALIDATION_PENDING"},
            x["methodology_sha256"], commits["crypto"]))
    for x in decisions:
        if x["hypothesis_id"] not in frozen_ids:
            raise ValueError("CRYPTO_DECISION_WITHOUT_FROZEN_TRIAL")
        if x["status"] == "POSITIVE_STRESSED_SNAPSHOT_MARK_ASSOCIATION":
            h = x["future_report"]
            if not positive_crypto(h):
                raise ValueError("CRYPTO_FORWARD_GATE_INCONSISTENT")
            events.append(event(
                "POSITIVE_FORWARD_RESEARCH", "CRYPTO_PERPETUAL",
                x["rule"], x["direction"], x["horizon_minutes"],
                x["id"], {"status": x["status"],
                          "net_mean_pct": h["mean_model_net_pct"],
                          "n": h["hypothetical_mark_trades"],
                          "profit_factor": h["profit_factor"]},
                x["methodology_sha256"], commits["crypto"]))
    summary["CRYPTO_PERPETUAL"] = {
        "source_status": cr.get("source_status"),
        "source_age_minutes": cr.get("source_age_minutes"),
        "source_reported_variants": cr["strategy_variants_tested"],
        "costed_research_candidates": positive,
        "asof_first_seen_observations": cr["asof_observations"],
        "forward_trials_frozen": len(frozen),
        "future_test_decisions": len(decisions),
    }

    if not isinstance(registry.get("hypotheses"), dict):
        raise ValueError("INVALID_LAB_REGISTRY")
    accepted = {}
    for label, spec in registry["hypotheses"].items():
        if spec.get("verdict") == "ACCEPT":
            accepted[label] = {
                "accepted_at": spec.get("accepted_at"),
                "strategy": spec.get("strategy", ""),
                "oos_cagr": (spec.get("oos") or {}).get("cagr"),
                "dsr": spec.get("dsr"),
                "live_degraded": bool((spec.get("live") or {}).get("degraded")),
            }
    return events, summary, accepted


def run(state_root, registry_path, fetch=http_text, when=None):
    now = when or now_utc()
    root = Path(state_root)
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "manifest.json"
    had_prior = manifest_path.exists()
    previous = json.loads(manifest_path.read_text(encoding="utf-8")) if had_prior else {
        "schema": SCHEMA, "source_commits": {}, "accepted": {}
    }
    if previous.get("schema") != SCHEMA:
        raise ValueError("H119_STATE_SCHEMA_MISMATCH")
    # Always verify prior immutable records before using a manifest.
    old_events = read_chain(root / "events.jsonl")
    read_chain(root / "receipts.jsonl")
    if had_prior and (not (root / "events.jsonl").exists()
                      or not (root / "receipts.jsonl").exists()):
        raise ValueError("H119_EVIDENCE_LEDGER_LOST")
    sources, commits = fetch_sources(previous.get("source_commits", {}), fetch)
    registry = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    proposals, summary, accepted = analyze(sources, commits, registry, now)
    added = []
    existing = {x["id"] for x in old_events}
    for p in proposals:
        if p["id"] not in existing:
            added.append(p)
    prior_acc = previous.get("accepted", {})
    if had_prior:
        for label, data in sorted(accepted.items()):
            if label not in prior_acc:
                added.append({
                    "schema": SCHEMA, "kind": "NEW_LAB_ACCEPT",
                    "id": event_id("NEW_LAB_ACCEPT", label, data.get("accepted_at")),
                    "hypothesis": label, "market": "QUANT_SUPERLAB",
                    "evidence": data, "lab_verdict": "ACCEPT",
                    "real_money_trade_authorized": False,
                })
        for label in sorted(set(prior_acc) - set(accepted)):
            added.append({
                "schema": SCHEMA, "kind": "LAB_ACCEPT_REVOKED",
                "id": event_id("LAB_ACCEPT_REVOKED", label),
                "hypothesis": label, "market": "QUANT_SUPERLAB",
                "evidence": {"prior": prior_acc[label]},
                "lab_verdict": "NO_LONGER_ACCEPT",
                "real_money_trade_authorized": False,
            })
    else:
        # One bootstrap message verifies whether Telegram is actually working;
        # importing old ACCEPT and upstream research does not spam history.
        added.append({
            "schema": SCHEMA, "kind": "NOTIFICATION_READY",
            "id": event_id("NOTIFICATION_READY", SCHEMA),
            "market": "QUANT_SUPERLAB",
            "evidence": {"channel": "TELEGRAM_FIRST_GITHUB_ISSUE_FALLBACK"},
            "lab_verdict": "NOT_EVALUATED",
            "real_money_trade_authorized": False,
        })
    events = append_chain(root / "events.jsonl", added,
                          int(now.timestamp() * 1000))
    # Ensure receipt path exists from inception even without delivered alerts.
    (root / "receipts.jsonl").touch(exist_ok=True)
    manifest = {
        "schema": SCHEMA, "updated_utc": now.isoformat(),
        "source_commits": commits, "accepted": accepted,
        "research_only": True, "writes_lab_registry": False,
        "source_count": len(BRANCHES),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    report = {
        "schema": SCHEMA, "asof_utc": now.isoformat(),
        "markets": summary,
        "source_commits": commits,
        "new_hypotheses_or_milestones": sum(
            x["kind"] in ("COSTED_RESEARCH_CANDIDATE",
                          "FUTURE_TRIAL_FROZEN", "POSITIVE_FORWARD_RESEARCH")
            for x in added),
        "new_lab_accepts": sum(x["kind"] == "NEW_LAB_ACCEPT" for x in added),
        "total_evidence_events": len(events),
        "notifications_waiting_delivery": sum(
            x["kind"] in NOTIFY_EVENT_TYPES for x in events
        ) - len(read_chain(root / "receipts.jsonl")),
        "status": "RESEARCH_ONLY_NO_NEW_OFFICIAL_LAB_APPROVAL",
        "limitations": [
            "H119 never changes hypotheses/registry.yaml or decisions/registry.json",
            "upstream event patterns are not a deployable backtest until native data/DSR/PBO/Reality Check pass",
            "upstream quote marks and source costs are not real exchange fills",
            "historical PIT membership, liquidity and all contract costs are unverified",
            "registered proposal is NOT quant_superlab ACCEPT",
        ],
    }
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True)
    parser.add_argument("--registry", default="decisions/registry.json")
    parser.add_argument("--out", default="results/h119/report")
    a = parser.parse_args()
    report = run(a.state, a.registry)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8")
    lines = [
        "# H119 — Autonomous Alpha Discovery Bridge",
        "",
        "Read-only, pinned-commit import: " + UPSTREAM,
        "New research hypotheses/milestones: " + str(report["new_hypotheses_or_milestones"]),
        "New official lab ACCEPT verdicts: " + str(report["new_lab_accepts"]),
        "Separate chained research events total: " + str(report["total_evidence_events"]),
        "",
    ]
    for market, detail in report["markets"].items():
        lines += ["## " + market,
                  "Cost-screen research candidates: " + str(detail["costed_research_candidates"]),
                  "Variant count checked: " + str(detail["source_reported_variants"]),
                  "Future trials frozen: " + str(detail["forward_trials_frozen"]),
                  "Forward trial decisions: " + str(detail["future_test_decisions"]), ""]
    lines += [
        "Research-only. Nothing imported automatically passes the existing",
        "quant_superlab DSR/PBO/Reality Check, time-machine or official ACCEPT gate.",
    ]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("H119", report["status"], "new",
          report["new_hypotheses_or_milestones"],
          "accepts", report["new_lab_accepts"])


if __name__ == "__main__":
    main()
