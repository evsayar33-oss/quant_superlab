"""Read-only, repo-native research evidence bridge.

Every repository runs this locally, with its own GitHub Actions token. Private
data never enters quant_superlab. Outputs are hashed observations and an
isolated exploratory research artifact, NOT trade instructions or validated PnL.

No provider data, missing samples, intraday bars or historical delisted
constituents are fabricated. Repository-specific strategy engines stay source
of truth; this module never imports or patches them.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .audit import load_catalog
from .synthesis import designs

SCHEMA = "QS.mesh.native_observation.v1"
RESULT_SCHEMA = "QS.mesh.research_design_study.v1"
SHA = re.compile(r"^[0-9a-f]{40}$")
BRANCH = re.compile(r"^[A-Za-z0-9._/-]{1,110}$")
MAX_SOURCE_BYTES = 3000000
MAX_ROWS = 25000

# Primary/secondary sources have different roles. No retrospective first-seen
# observation is created from old snapshots on installation day.
NATIVE_SOURCES = {
    "quant_superlab": (
        ("registry", "@default", "decisions/registry.json", True),
        ("hypotheses", "@default", "hypotheses/registry.yaml", False)),
    "early_accumulation_radar": (
        ("crypto", "research/v13-crypto-alpha-evidence", "research_archive/v13_crypto/latest.json", True),
        ("v11", "research/v11-pattern-evidence", "research_archive/v11/latest.json", False),
        ("equity", "research/v13-alpha-evidence", "research_archive/v13/latest.json", False)),
    "eaverse": (
        ("release_panel", "@external", "eaverse_paper_panel.json", True),
        ("strategy_version", "@default", "eaverse/research.py", False)),
    "federal-incentive-radar": (
        ("h083", "data", "h083_last_attempt.json", True),
        ("forward", "data", "h083_forward_status.json", False),
        ("watch", "data", "event_watch_status.json", False),
        ("econ", "data", "economic_intelligence_status.json", False)),
    "global_capital_radar": (
        ("forecasts", "@default", "history/forecasts.json", True),
        ("selection", "@default", "history/method_selection.json", False),
        ("outcomes", "@default", "history/rotation/outcomes.json", False)),
    "h054_spot_bot": (
        ("paper_status", "@default", "state/state.json", True),
        ("paper_balances", "@default", "state/paper.json", False),
        ("local_registry", "@default", "decisions/registry.json", False)),
    "us_f1_bot": (
        ("demo", "@default", "data/state.json", True),
        ("shadow", "@default", "data/shadow/paired_state.json", False)),
    "bist_orderflow_quant": (
        ("variants", "@default", "data/variants_report.json", True),
        ("backtest", "@default", "data/backtest_report_v3.json", False),
        ("forward_signals", "@default", "data/signals_ledger.csv", False)),
    "tier1_quant_terminal": (
        ("performance", "@default", "performance_ledger.json", True),
        ("historical", "@default", "validation_reports/historical_replay_summary.json", False),
        ("state", "@default", "terminal_state.json", False)),
    "islem_onerisi_alarmi": (
        ("strategy_book", "@default", "STRATEGY_BOOK.md", True),
        ("forward", "@default", "results/forward_test_nq_spx_xau.csv", False)),
}
# These are NOT generic alpha thresholds. They are minimum evidence quantities
# for reporting descriptive research, never auto-certification of a strategy.
DEFAULT_REQUIRED = {"min_distinct_events": 30, "min_matched_controls": 60,
                    "min_independent_blocks": 8}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True,
                ensure_ascii=False, separators=(",", ":"), allow_nan=False
                ).encode("utf-8")).hexdigest()


def utc(value):
    if value is None or value == "":
        return None
    try:
        t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if t.tzinfo is None:
        return None
    return t.astimezone(timezone.utc)


def git(root, args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                          check=True, timeout=50).stdout


def fetch_branch(root, branch):
    if not BRANCH.fullmatch(branch) or branch.startswith((".", "-", "/")) or ".." in branch:
        raise ValueError("UNTRUSTED_BRANCH")
    git(root, ["fetch", "--depth=1", "origin", "refs/heads/" + branch])
    sha = git(root, ["rev-parse", "FETCH_HEAD"]).decode().strip()
    if not SHA.fullmatch(sha):
        raise ValueError("UNTRUSTED_SOURCE_COMMIT")
    return sha


def raw_source(root, ref, path, pins, release_file=None):
    if not isinstance(path, str) or path.startswith("/") or ".." in path.split("/"):
        raise ValueError("UNTRUSTED_SOURCE_PATH")
    if ref == "@external":
        if release_file is None:
            raise FileNotFoundError("EXTERNAL_SOURCE_NOT_LOADED")
        p = Path(release_file)
        if p.name != path or not p.is_file():
            raise FileNotFoundError("EXTERNAL_SOURCE_MISMATCH")
        data = p.read_bytes()
        pin = "release-" + hashlib.sha256(data).hexdigest()
    elif ref == "@default":
        data = (root / path).read_bytes()
        pin = git(root, ["rev-parse", "HEAD"]).decode().strip()
    else:
        if ref not in pins:
            pins[ref] = fetch_branch(root, ref)
        pin = pins[ref]
        data = git(root, ["show", pin + ":" + path])
    if len(data) > MAX_SOURCE_BYTES:
        raise ValueError("NATIVE_SOURCE_EXCEEDS_BOUNDED_BYTES")
    return data, pin


def json_obj(source):
    try:
        data = json.loads(source)
        return data if isinstance(data, (dict, list)) else {}
    except (ValueError, UnicodeDecodeError):
        return {}


def safe_number(value):
    if isinstance(value, bool):
        return None
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def native_summary(repo, contents):
    """Explicit repo-native semantics; the output is NOT synthesized alpha."""
    j = {k: json_obj(raw) for k, raw in contents.items()}
    m = {}
    asof = None
    if repo == "quant_superlab":
        a = j.get("registry", {}).get("hypotheses", {})
        if not isinstance(a, dict):
            a = {}
        m = {"registered_variants": len(a),
             "verdicts": dict(Counter(v.get("verdict", "UNKNOWN") for v in a.values())),
             "accepted_ids": sorted(k for k, v in a.items() if v.get("verdict") == "ACCEPT")}
        asof = j.get("registry", {}).get("updated")
    elif repo == "early_accumulation_radar":
        a = j.get("crypto", {})
        b = j.get("v11", {})
        m = {"crypto_variants": a.get("strategy_variants_tested"),
             "asof_observations": a.get("asof_observations"),
             "matured_modeled_outcomes": a.get("modeled_outcomes"),
             "pending_forward_horizons": a.get("pending_future_outcomes"),
             "frozen_crypto_trials": a.get("frozen_trials"),
             "v11_matured_cases": b.get("matured_case_control_samples")}
        asof = a.get("asof_utc")
    elif repo == "eaverse":
        panel = j.get("release_panel", {})
        m = {"panel_keys": sorted(panel)[:25] if isinstance(panel, dict) else [],
             "paper_candidate_count": len(panel.get("candidates", []))
                 if isinstance(panel, dict) and isinstance(panel.get("candidates"), list) else None,
             "release_is_forward_truth": False}
        asof = (panel.get("generated_utc") or panel.get("generated_at")
                if isinstance(panel, dict) else None)
    elif repo == "federal-incentive-radar":
        a, f, w = (j.get(k, {}) for k in ("h083", "forward", "watch"))
        m = {"h083_state": a.get("state"), "h083_session": a.get("session"),
             "h083_counts_as_forward": a.get("counts_as_forward_month"),
             "h083_forward_months": f.get("forward_months_closed"),
             "h083_paper_approved_count": f.get("approved_paper_rules"),
             "priced": w.get("priced_tickers"),
             "eligible": w.get("eligible_tickers"),
             "coverage": w.get("data_coverage_pct"),
             "alpha_validated": w.get("validated_alpha"),
             "event_alpha_hypotheses_distinct_from_h083": 5}
        asof = a.get("attempted_at_utc")
    elif repo == "global_capital_radar":
        a = j.get("forecasts", {})
        s = j.get("selection", {})
        v = j.get("outcomes", {})
        m = {"selection_count": len(s) if isinstance(s, dict) else 0,
             "outcomes_count": len(v) if isinstance(v, (list, dict)) else None,
             "forecast_shape": list(a)[:15] if isinstance(a, dict) else type(a).__name__,
             "selected_alpha_proven": False}
        asof = a.get("generated_utc") or a.get("asof_utc") if isinstance(a, dict) else None
    elif repo == "h054_spot_bot":
        a, h = j.get("paper_status", {}), j.get("local_registry", {}).get("hypotheses", {})
        m = {"paper_equity": a.get("equity"),
             "approved_reason": a.get("why"), "bar": a.get("last_bar"),
             "live_verdicts": {k: v.get("live_verdict") for k, v in h.items()},
             "paper_verdicts": {k: v.get("verdict") for k, v in h.items()}}
        asof = a.get("updated_at")
    elif repo == "us_f1_bot":
        a, b = j.get("demo", {}), j.get("shadow", {})
        s = a.get("risk_snapshot", {})
        m = {"demo_nav": s.get("nav_usd"), "initial_cash": a.get("capital_usd"),
             "strategy_revision": a.get("strategy_revision"),
             "shadow_sessions": b.get("sessions"),
             "shadow_closed_control": len(b.get("control", {}).get("closed_cycles", [])),
             "shadow_closed_candidate": len(b.get("candidate", {}).get("closed_cycles", []))}
        asof = s.get("date")  # session date, NOT timestamp evidence.
    elif repo == "bist_orderflow_quant":
        a, b = j.get("variants", {}), j.get("backtest", {})
        m = {"historical_variant_count": len(a.get("variants", [])),
             "backtest_cagr_pct": b.get("portfolio", {}).get("cagr_pct"),
             "period": b.get("period"), "historical_pit_verified": False}
        asof = a.get("generated_at")
    elif repo == "tier1_quant_terminal":
        a, b = j.get("performance", {}), j.get("historical", {})
        m = {"performance_records": len(a.get("records", [])),
             "historical_graded": b.get("summary", {}).get("records_graded"),
             "research30_forward_gate_approved": False}
        asof = a.get("meta", {}).get("last_cycle")
    elif repo == "islem_onerisi_alarmi":
        m = {"strategy_book_bytes": len(contents.get("strategy_book", b"")),
             "forward_csv_present": "forward" in contents,
             "historical_holdout_is_prospective": False}
    return m, asof


def bist_training_only(variants):
    """Historical comparison uses *first half only* to choose a challenger.

    Second half is disclosed as a RETROSPECTIVE comparison, never untouched
    independent OOS or real fills, since these variants were already explored.
    """
    rows = []
    for v in variants.get("variants", []):
        t = safe_number(v.get("cagr_h1_pct"))
        f = safe_number(v.get("cagr_h2_pct"))
        if not v.get("name") or t is None or f is None:
            continue
        rows.append({"name": v["name"], "training_first_half_pct": t,
                     "published_second_half_pct": f})
    control = next((r for r in rows if r["name"] == "base"), None)
    if not control or len(rows) < 2:
        return {"status": "INSUFFICIENT_HISTORICAL_VARIANT_PANEL",
                "eligible_variants": len(rows)}
    # No search on holdout.
    selected = max((r for r in rows if r["name"] != "base"),
                   key=lambda r: (r["training_first_half_pct"], r["name"]))
    return {"status": "EXPLORATORY_ONLY_HISTORICAL_PIT_UNVERIFIED",
            "selection_rule": "highest_first_half_cagr_excluding_base",
            "selected": selected, "control": control,
            "second_half_excess_pct_points": round(
                 selected["published_second_half_pct"] -
                 control["published_second_half_pct"], 4),
            "candidate_count_including_control": len(rows),
            "validated_alpha": False, "ready_for_paper": False}


def f1_shadow_study(demo, shadow):
    """Require distinct sessions, matured positions and true paired evidence."""
    sessions = shadow.get("sessions", 0)
    try:
        sessions = int(sessions)
    except (TypeError, ValueError):
        sessions = 0
    c = shadow.get("control", {})
    t = shadow.get("candidate", {})
    cc, tc = len(c.get("closed_cycles", [])), len(t.get("closed_cycles", []))
    return {"status": ("WAITING_FOR_90_INDEPENDENT_SESSIONS_AND_CLOSED_TRADES"
                       if sessions < 90 or not cc or not tc
                       else "PAIRED_SHADOW_MATURED_NEEDS_OOS_COST_STRESS_REVIEW"),
            "sessions": sessions, "control_closed_cycles": cc,
            "candidate_closed_cycles": tc,
            "independent_alpha_verified": False, "production_promotion": False}


def ict_holdout(study_text):
    """Audit the PRESELECTED six rules, not hunt positive rows in the holdout."""
    counts = {"selected": 0, "selected_positive_holdout": 0,
              "selected_negative_holdout": 0, "unparsed": 0}
    for line in study_text.splitlines():
        if not line.startswith("|") or line.startswith("|---"):
            continue
        fields = [x.strip() for x in line.strip("|").split("|")]
        if len(fields) < 10 or fields[0] not in ("NQ", "SPX", "XAU", "XAG", "BTC", "ETH"):
            continue
        value = safe_number(fields[9])
        if value is None:
            counts["unparsed"] += 1
        else:
            counts["selected"] += 1
            if value > 0:
                counts["selected_positive_holdout"] += 1
            else:
                counts["selected_negative_holdout"] += 1
    return {**counts, "status": "HISTORICAL_PRESELECTED_HOLDOUT_NOT_FUTURE_PAPER",
            "selection_from_holdout_permitted": False, "validated_alpha": False}


def native_study(repo, contents):
    j = {k: json_obj(raw) for k, raw in contents.items()}
    if repo == "bist_orderflow_quant":
        return bist_training_only(j.get("variants", {}))
    if repo == "us_f1_bot":
        return f1_shadow_study(j.get("demo", {}), j.get("shadow", {}))
    if repo == "islem_onerisi_alarmi":
        return ict_holdout(contents.get("strategy_book", b"").decode("utf-8", "replace"))
    if repo == "global_capital_radar":
        selected = j.get("selection", {})
        return {"status": "WAITING_FOR_INDEPENDENT_FORWARD_METHOD_SAMPLES"
                if not selected else "METHOD_OUTCOMES_REQUIRE_CAUSAL_RECHECK",
                "selected_methods": len(selected) if isinstance(selected, dict) else None,
                "validated_alpha": False}
    if repo == "early_accumulation_radar":
        s = j.get("crypto", {})
        return {"status": ("WAITING_FOR_REAL_4H_OUTCOMES" if s.get("modeled_outcomes") == 0
                           else "OUTCOMES_PRESENT_NOT_AUTOMATIC_ALPHA"),
                "v13_modeled_outcomes": s.get("modeled_outcomes"),
                "pending_horizons": s.get("pending_future_outcomes"), "validated_alpha": False}
    if repo == "federal-incentive-radar":
        a, s = j.get("h083", {}), j.get("forward", {})
        return {"status": "H083_RESEARCH_NOT_TWO_COMPLETED_FORWARD_MONTHS"
                if not s.get("forward_months_closed") else "H083_FORWARD_AUDIT_REQUIRED",
                "h083_counts_as_forward_month": a.get("counts_as_forward_month"),
                "h083_months": s.get("forward_months_closed"),
                "separate_causal_event_alpha_hypotheses": 5,
                "validated_alpha": False}
    if repo == "h054_spot_bot":
        a = j.get("local_registry", {}).get("hypotheses", {})
        return {"status": "INDEPENDENT_PAPER_OBSERVATION_ONLY",
                "paper_rules": sorted(k for k, v in a.items()
                                      if v.get("verdict") == "PAPER_ACCEPT"),
                "live_authorized": False}
    if repo == "eaverse":
        return {"status": "RELEASE_PAPER_SOURCE_REQUIRES_NATIVE_RESEARCH_GATES",
                "auto_promoted_from_cross_repo": False}
    if repo == "quant_superlab":
        return {"status": "OFFICIAL_ACCEPT_VERDICTS_DISTINCT_FROM_NEW_HYPOTHESES",
                "proposed_candidate_accepted": False}
    if repo == "tier1_quant_terminal":
        return {"status": "HISTORICAL_REPLAY_DISTINCT_FROM_30D_PROSPECTIVE",
                "forward_strategy_validated": False}
    raise ValueError("UNKNOWN_REPO_NATIVE_STUDY")


def snapshot(root, repo, release_file=None):
    if repo not in NATIVE_SOURCES:
        raise ValueError("UNRECOGNIZED_SOURCE_REPOSITORY")
    root = Path(root)
    contents, pins, errors, file_meta = {}, {}, {}, {}
    for alias, ref, path, required in NATIVE_SOURCES[repo]:
        try:
            data, commit = raw_source(root, ref, path, pins, release_file)
            contents[alias] = data
            file_meta[alias] = {"sha256": hashlib.sha256(data).hexdigest(),
                                "commit": commit, "bytes": len(data),
                                "reference": ref, "path": path}
        except (subprocess.CalledProcessError, OSError, ValueError,
                TimeoutError) as exc:
            errors[alias] = {"type": type(exc).__name__, "required": required}
    primary = NATIVE_SOURCES[repo][0][0]
    if primary not in contents:
        # No first-seen evidence if the critical native source is unavailable.
        status = "MISSING_REQUIRED_PRIMARY_EVIDENCE"
    else:
        status = "OBSERVED_UNPROMOTED"
    summary, source_asof = native_summary(repo, contents)
    stamp = utc(source_asof)
    return {
        "schema": SCHEMA, "repo": "evsayar33-oss/" + repo,
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "native_observation_utc": stamp.isoformat() if stamp else None,
        "native_observation_raw": str(source_asof) if source_asof is not None else None,
        "source_data_digest": digest({k: v["sha256"] for k, v in file_meta.items()}),
        "inputs": file_meta, "input_errors": errors, "data_status": status,
        "asof_source_not_reconstructed_from_current_prices": True,
        "native_metrics": summary, "research": native_study(repo, contents),
        "cross_repo_strategy_promoted": False, "paper_approved_by_mesh": False,
        "live_trade_authorized_by_mesh": False,
    }


def read_chain(path):
    path = Path(path)
    if not path.is_file():
        return []
    out, old_hash, last = [], "GENESIS", None
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        proof = dict(row)
        proof.pop("sha256", None)
        if (proof.get("prev_sha256") != old_hash or
            row.get("sha256") != digest(proof)):
            raise ValueError("MESH_SHA_CHAIN_TAMPERED")
        stamp = utc(row.get("captured_utc"))
        if stamp is None or (last is not None and stamp <= last):
            raise ValueError("MESH_NON_MONOTONIC_CAPTURE_CLOCK")
        out.append(row)
        last = stamp
        old_hash = row["sha256"]
    return out


def append_snapshot(path, snap):
    if snap.get("schema") != SCHEMA:
        raise ValueError("UNTRUSTED_NATIVE_SNAPSHOT")
    old = read_chain(path)
    if snap.get("data_status") != "OBSERVED_UNPROMOTED":
        return {"status": "NO_APPEND_PRIMARY_SOURCE_UNAVAILABLE",
                "recorded_snapshots": len(old)}
    if old and old[-1]["source_data_digest"] == snap["source_data_digest"]:
        return {"status": "UNCHANGED_NATIVE_DATA_NO_SYNTHETIC_NEW_OBSERVATION",
                "recorded_snapshots": len(old)}
    prev_asof = None
    for prior in reversed(old):
        if prior.get("native_observation_utc"):
            prev_asof = utc(prior["native_observation_utc"])
            break
    current_asof = utc(snap.get("native_observation_utc"))
    if prev_asof and current_asof and current_asof < prev_asof:
        raise ValueError("SOURCE_ASOF_REWIND_BLOCKED")
    snap = dict(snap)
    # Historical corrections can be recorded but never counted as new events.
    snap["source_revision_same_observation"] = bool(
        prev_asof and current_asof and prev_asof == current_asof)
    previous_capture = utc(old[-1]["captured_utc"]) if old else None
    if previous_capture and utc(snap["captured_utc"]) <= previous_capture:
        raise ValueError("STALE_NEW_CAPTURE_CLOCK")
    snap["prev_sha256"] = old[-1]["sha256"] if old else "GENESIS"
    snap["sha256"] = digest(snap)
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("a", encoding="utf-8") as f:
        f.write(json.dumps(snap, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False) + "\n")
    return {"status": "APPENDED_SOURCE_OBSERVATION_OR_REVISION",
            "recorded_snapshots": len(old) + 1, "new_sha256": snap["sha256"],
            "same_observation_revision": snap["source_revision_same_observation"]}


def run(repo, root, out, ledger, release_file=None):
    p = next((p for p in load_catalog()["projects"] if p["name"] == repo), None)
    if p is None:
        raise ValueError("REPO_NOT_IN_SOURCE_SPECIFIC_CATALOG")
    s = snapshot(root, repo, release_file)
    before = read_chain(ledger) if ledger else []
    result = append_snapshot(ledger, s) if ledger else {
        "status": "DRY_RUN_NO_APPEND", "recorded_snapshots": len(before)}
    after = read_chain(ledger) if ledger else before
    last_native_asof = utc(s.get("native_observation_utc"))
    valid_original_observations = sum(
        x.get("source_revision_same_observation") is False and
        x.get("native_observation_utc") is not None for x in after)
    candidate_set = designs(p)
    experiments = [{
        "id": x["id"], "features": x["signal_information_groups"],
        "status": "DESIGN_ONLY_NOT_PREREGISTERED_OR_SIMULATED",
        "market_scope": p["domain"],
        "outcome_not_invented": True,
        "required": DEFAULT_REQUIRED,
        "source_observed_snapshots": valid_original_observations,
        "true_future_trades_tested": 0,
        "paper_approved": False,
        "live_approved": False,
    } for x in candidate_set]
    report = {
        "schema": RESULT_SCHEMA, "source_repository": s["repo"],
        "data_status": s["data_status"], "native_observation_utc": s["native_observation_utc"],
        "source_data_digest": s["source_data_digest"],
        "native_source_coverage": len(s["inputs"]),
        "native_source_errors": s["input_errors"],
        "source_native_metrics": s["native_metrics"],
        "native_research_analysis": s["research"],
        "research_ideas": len(experiments),
        "first_seen_observation_count": valid_original_observations,
        "append_state": result,
        "execution_policy": ("research-only; no external repo's strategy imported; "
                             "all real entries/fills, OOS and promotion are forbidden "
                             "until source-native gates independently pass"),
        "current_hypotheses_not_a_paper_or_live_acceptance": True,
        "cross_repo_auto_promotion": False,
    }
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "source_audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "design_queue.json").write_text(
        json.dumps({"schema": "QS.mesh.design_queue.v1", "source": s["repo"],
                    "designs": experiments}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md = ["# " + repo + " — repo-native data-first research",
          "", "Data state: **" + s["data_status"] + "**.",
          "Existing genuinely observed snapshots: **" +
              str(valid_original_observations) + "**.",
          "New frozen research ideas: **0** (design-only candidates: " + str(len(experiments)) + ").",
          "Native study: **" + str(s["research"].get("status", "NO_STUDY")) + "**.",
          "No validated new alpha, independent PAPER_ACCEPT or LIVE_ACCEPT issued.",
          "No source data are published to quant_superlab.",
          "", "Collection: **" + result["status"] + "**."]
    if s["input_errors"]:
        md += ["", "Missing sources: " + ", ".join(
            k + "=" + x["type"] for k, x in sorted(s["input_errors"].items()))]
    (out / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return report


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--repo", required=True)
    a.add_argument("--root", default=".")
    a.add_argument("--out", default="out/native_mesh")
    a.add_argument("--ledger")
    a.add_argument("--release-panel")
    args = a.parse_args()
    report = run(args.repo, args.root, args.out, args.ledger, args.release_panel)
    print("MESH", args.repo, report["data_status"],
          report["native_research_analysis"]["status"],
          report["append_state"]["status"],
          "ideas", report["research_ideas"])


if __name__ == "__main__":
    main()
