"""Fail-closed read-only cross-repository evidence audit.

A WATCH, completed cron run, demo trade or descriptive backtest is not
a profitable strategy, an independently validated forward test or LIVE_ACCEPT.
No source file, trading bot, experimental clock or decision registry is edited.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

SCHEMA = "QS.portfolio_qualification.audit.v1"
ROOT = Path(__file__).resolve().parent
MAX_BYTES = 1800000
SHA = re.compile(r"^[0-9a-f]{40}$")


def load_catalog(path=ROOT / "catalog.json"):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema") != "QS.portfolio_qualification.catalog.v1":
        raise ValueError("INVALID_PORTFOLIO_CATALOG")
    names = [p["name"] for p in data["projects"]]
    if len(names) != len(set(names)) or any(not p.get("scope") for p in data["projects"]):
        raise ValueError("INVALID_OR_DUPLICATE_PROJECT")
    return data


def get_text(url, token=None):
    headers = {"User-Agent": "qs-research-readonly/1",
               "Accept": "application/vnd.github+json"}
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = "Bearer " + token
    with urlopen(Request(url, headers=headers), timeout=18) as stream:
        blob = stream.read(MAX_BYTES + 1)
    if len(blob) > MAX_BYTES:
        raise ValueError("SOURCE_OVERSIZE")
    return blob.decode("utf-8")


def collect(project, fetch=get_text, token=None):
    """Pin source files to actual Git commit; never infer an absent dataset."""
    name = project["name"]
    repo = "evsayar33-oss/" + name
    pins, evidence, errors = {}, {}, {}
    # The central repo is public. Never copy private repository content into
    # its Actions artifacts, even if permissions change in the future.
    if project.get("source_visibility") == "private":
        return {"repo": repo, "ref_pins": {}, "evidence": {},
                "errors": {name: "PRIVATE_SOURCE_NOT_COLLECTED_IN_PUBLIC_CI"
                           for name in project["feeds"]},
                "observed_sources": [],
                "missing_sources": sorted(project["feeds"])}
    for alias, (ref, path) in project["feeds"].items():
        try:
            if (not ref or path.startswith("/") or ".." in path.split("/")
                    or not path or not all(x.isascii() for x in (ref, path))):
                raise ValueError("UNSAFE_SOURCE_PATH")
            if ref not in pins:
                u = "https://api.github.com/repos/" + repo + "/git/ref/heads/" + quote(ref, safe="/")
                raw_ref = json.loads(fetch(u, token))
                sha = raw_ref["object"]["sha"]
                if not SHA.fullmatch(sha):
                    raise ValueError("UNTRUSTED_SOURCE_SHA")
                pins[ref] = sha
            url = "https://raw.githubusercontent.com/" + repo + "/" + pins[ref] + "/" + quote(path, safe="/")
            raw = fetch(url, None)
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("UNEXPECTED_REPORT_SCHEMA")
            evidence[alias] = payload
        except (KeyError, TypeError, ValueError, RuntimeError, HTTPError, URLError, TimeoutError,
                json.JSONDecodeError, UnicodeError) as exc:
            errors[alias] = type(exc).__name__
    return {"repo": repo, "ref_pins": pins, "evidence": evidence,
            "errors": errors, "observed_sources": sorted(evidence),
            "missing_sources": sorted(set(project["feeds"]) - set(evidence))}


def _number(d, key):
    value = d.get(key)
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def interpret(project, fetched):
    """Classify observed evidence only. This method cannot authorize PAPER/LIVE."""
    profile = project["profile"]
    e = fetched.get("evidence", {})
    warnings = list(project.get("missing", []))
    out = {"repo": fetched["repo"], "domain": project["domain"],
           "scope": project["scope"], "profile": profile,
           "status": "UNKNOWN_SOURCE_EVIDENCE", "metrics": {}, "limitations": warnings,
           "source_commit_pins": fetched.get("ref_pins", {}),
           "source_errors": fetched.get("errors", {}),
           "source_present": fetched.get("observed_sources", []),
           "research_only": True, "new_paper_approval": False,
           "new_live_approval": False, "trade_authorized": False}
    m = out["metrics"]
    if profile == "lab" and isinstance(e.get("registry", {}).get("hypotheses"), dict):
        h = e["registry"]["hypotheses"]
        counts = dict(Counter(x.get("verdict", "UNKNOWN") for x in h.values()))
        m.update(registry_count=len(h), verdict_counts=counts,
                 accepted_ids=sorted(k for k, v in h.items() if v.get("verdict") == "ACCEPT"),
                 registry_updated=e["registry"].get("updated"))
        out["status"] = "REGISTERED_LAB_VERDICTS_NO_CROSS_REPO_PROMOTION"
    elif profile == "early" and "crypto" in e and "association" in e:
        c, a = e["crypto"], e["association"]
        m.update(crypto_variants=c.get("strategy_variants_tested"),
                 asof_observations=c.get("asof_observations"),
                 modeled_outcomes=c.get("modeled_outcomes"),
                 crypto_pending_future=c.get("pending_future_outcomes"),
                 frozen_trials=c.get("frozen_trials"),
                 association_matured=a.get("matured_case_control_samples"),
                 association_frozen=a.get("frozen_hypotheses_total"))
        out["status"] = ("RESEARCH_NO_MATURED_OUTCOMES"
                         if c.get("modeled_outcomes") == 0 and
                         a.get("matured_case_control_samples") == 0
                         else "RESEARCH_ONLY_OUTCOMES_REQUIRE_INDEPENDENT_GATE")
        if "equity" in e:
            out["metrics"]["equity_segments"] = {
                name: {"frozen": x.get("frozen_total"),
                       "matured": x.get("v12_matured_outcomes")}
                for name, x in e["equity"].get("markets", {}).items()}
    elif profile == "federal" and all(z in e for z in ("h083", "forward", "watch")):
        a, f, w = e["h083"], e["forward"], e["watch"]
        completed = _number(f, "forward_months_closed")
        months = completed if completed is not None else None
        m.update(h083_state=a.get("state"), last_nyse_session=a.get("session"),
                 counts_as_forward_month=a.get("counts_as_forward_month"),
                 months_completed=months, approved_paper_rules=f.get("approved_paper_rules"),
                 price_coverage=w.get("data_coverage_pct"), validated_alpha=w.get("validated_alpha"))
        # Research completion/legitimate SKIPPED is NEVER forward completion.
        out["status"] = ("H083_PAPER_ROTATION_UNVERIFIED_SEPARATE_FROM_EVENT_ALPHA"
                         if not completed or a.get("counts_as_forward_month") is not True
                         else "H083_FORWARD_EVIDENCE_PRESENT_REQUIRES_REVIEW")
        out["limitations"].append("Five independent 20-session event-alpha hypotheses are not H083 months")
    elif profile == "capital" and "selection" in e:
        selection = e["selection"]
        m["registered_method_selected"] = bool(selection)
        m["forward_validation_summary"] = e.get("validation", {}).get("selection")
        out["status"] = ("OBSERVATION_NO_SELECTED_PROVEN_METHOD"
                         if not selection else "METHOD_RECORD_PRESENT_REQUIRES_FORWARD_REVIEW")
    elif profile == "h054" and "registry" in e:
        h = e["registry"].get("hypotheses", {})
        m["local_hypotheses"] = {k: {"paper": v.get("verdict"), "live": v.get("live_verdict")}
                                 for k, v in h.items()}
        m["sim_status"] = e.get("status", {}).get("why")
        out["status"] = "LOCAL_PAPER_APPROVAL_LIVE_DENIED" if (h and
            all(x.get("live_verdict") == "DENY" for x in h.values())) else "PAPER_STATE_REQUIRES_REVIEW"
    elif profile == "usf1" and "demo" in e:
        demo = e["demo"]
        capital = _number(demo, "capital_usd")
        nav = _number(demo.get("risk_snapshot", {}), "nav_usd")
        m.update(demo_initial_cash=capital, latest_demo_nav=nav,
                 demo_nav_vs_initial_pct=round(100 * (nav / capital - 1), 2)
                 if capital and capital > 0 and nav is not None else None,
                 strategy_revision=demo.get("strategy_revision"),
                 shadow_sessions=e.get("paired", {}).get("sessions"))
        out["status"] = "DEMO_RUNNING_NOT_INDEPENDENT_ALPHA_PROOF"
    elif profile == "bist" and "backtest" in e:
        b = e["backtest"]
        m.update(backtest_generated_at=b.get("generated_at"),
                 backtest_cagr_pct=b.get("portfolio", {}).get("cagr_pct"),
                 historical_period=b.get("period"),
                 variant_count=len(e.get("variants", {}).get("variants", []))
                 if "variants" in e else None)
        out["status"] = "HISTORICAL_BACKTEST_PIT_NOT_VERIFIED"
    elif profile == "tier1" and "historical" in e:
        s = e["historical"].get("summary", {})
        m.update(historical_graded=s.get("records_graded"),
                 historical_end=e["historical"].get("end"))
        out["status"] = "HISTORICAL_REPLAY_FORWARD_GATE_UNKNOWN"
    elif profile in ("eaverse", "ict"):
        out["status"] = "NON_MAIN_EVIDENCE_REQUIRES_SEPARATE_AUDIT"
    return out


def run(catalog=None, fetch=get_text, token=None):
    catalog = catalog or load_catalog()
    reports = []
    for p in catalog["projects"]:
        reports.append(interpret(p, collect(p, fetch=fetch, token=token)))
    return {"schema": SCHEMA,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "audit_scope": "READ_ONLY_RESEARCH_NON_PROMOTING",
            "projects_audited": len(reports),
            "source_errors_count": sum(len(x["source_errors"]) for x in reports),
            "project_reports": reports,
            "production_files_modified": False, "live_strategy_promoted": False,
            "paper_strategy_promoted": False}


def render_md(data):
    lines = ["# Portfolio qualification / evidence status",
             "", "Read-only. Status is evidence classification, not a finding of profitability.",
             "No current strategy, PAPER process, notification or production gate is modified.",
             "", "| Repository | Evidence status | Input gaps |", "|---|---|---:|"]
    for x in data["project_reports"]:
        lines.append("| " + " | ".join([
            x["repo"].split("/", 1)[1], x["status"], str(len(x["source_errors"]))
        ]) + " |")
    lines += ["", "## Critical distinctions",
        "- WATCH / green cron / sampled quote != independent OOS, PAPER_ACCEPT or LIVE_ACCEPT.",
        "- H083 research completion and NYSE SKIPPED are not completed forward months.",
        "- H083 PAPER rotation and the five 20-session causal event-alpha hypotheses remain separate.",
        "- Existing official registry ACCEPT records are reported; they are not granted to other repos.",
        "- Historical survivor-universe backtests and current-symbol rankings cannot prove PIT alpha.",
        "- Missing or inaccessible sources remain UNKNOWN, not failures or synthetic success.",
        "", "## No changes to running systems", "",
        "Research-only audit; no automatic promotion, trade order or Telegram report."]
    return "\n".join(lines) + "\n"


def main():
    arg = argparse.ArgumentParser()
    arg.add_argument("--out", default="out/portfolio_qualification")
    args = arg.parse_args()
    result = run(token=os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN"))
    path = Path(args.out)
    path.mkdir(parents=True, exist_ok=True)
    (path / "audit.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                                     encoding="utf-8")
    (path / "audit.md").write_text(render_md(result), encoding="utf-8")
    print("PORTFOLIO_QUALIFICATION", result["projects_audited"],
          "projects;", result["source_errors_count"], "unavailable files")
    for project in result["project_reports"]:
        for key, kind in sorted(project["source_errors"].items()):
            print("SOURCE_UNAVAILABLE", project["repo"], key, kind)


if __name__ == "__main__":
    main()
