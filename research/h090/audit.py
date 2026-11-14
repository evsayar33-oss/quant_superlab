"""H090 honest repository coverage audit: missing work stays visibly missing.

Source existence and selected code markers are automatically checked. Semantic
correctness, strategy testing and alpha are NOT inferred from file presence.
No production registry or decisions are written.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = Path(__file__).with_name("catalog.json")
RECIPES = Path(__file__).with_name("recipes.json")
ALLOWED_STATUS = frozenset({"existing_partial", "missing", "foundation_only",
                            "implemented_verified"})
ALLOWED_STATE = frozenset({"UNTESTED", "NOT_TESTABLE", "DISCOVERY_ONLY",
                           "OOS_PASSED", "OOS_FAILED", "FORWARD_PENDING",
                           "FORWARD_VERIFIED"})


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_path(value: str) -> Path:
    p = Path(value)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("invalid repo path")
    result = (ROOT / p).resolve()
    if not result.is_relative_to(ROOT.resolve()):
        raise ValueError("path escapes repo")
    return result


def load_catalog(path: Path = CATALOG) -> dict:
    c = json.loads(path.read_text())
    if c.get("schema") != "H090.catalog.v1" or not c.get("research_only") or c.get("production_authorized"):
        raise ValueError("H090 research-only catalog contract invalid")
    if not c.get("research_protocol") or not isinstance(c.get("research_requirements"), list):
        raise ValueError("missing research protocol or requirement inventory")
    for group, key in (("families", "id"), ("capabilities", "id"),
                       ("research_requirements", "id")):
        entries = c.get(group)
        if not isinstance(entries, list) or not entries:
            raise ValueError("empty or absent "+group)
        ids = [x[key] for x in entries]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate "+group+" IDs")
    if not set(c.get("timeframes",[])) or not set(c.get("event_types",[])):
        raise ValueError("empty scope axes")
    return c


def audit(catalog: dict | None = None) -> dict:
    c = catalog or load_catalog()
    from engine import EVENT_KINDS, TIMEFRAMES, load_recipes
    if not set(c["event_types"]).issubset(EVENT_KIN):
        raise ValueError("unrecognized events in research catalog")
    if not set(c["timeframes"]).issubset(TIMEFRAMES):
        raise ValueError("unrecognized timeframes")
    recipes = load_recipes()
    registered_family = {f["id"] for f in c["families"]}
    ids = {x["id"] for x in c["capabilities"]}
    file_checks = []
    for x in c["capabilities"]:
        status=x.get("status")
        if status not in ALLOWED_STATUS:
            raise ValueError("invalid capability status: "+x["id"])
        if not x.get("gap"):
            raise ValueError("capability requires explicit limitations")
        path=x.get("source")
        if status=="missing" and path:
            raise ValueError("missing capability must not claim source implementation")
        exists=bool(path) and safe_path(path).is_file()
        evidence=x.get("evidence")
        text=safe_path(path).read_text() if exists else ""
        marker_found=bool(evidence) and evidence in text
        if status!="missing" and not (exists and marker_found):
            raise ValueError("asserted evidence missing: "+x["id"])
        file_checks.append({"capability":x["id"],"source":path,"exists":exists,
                            "marker_found":marker_found,
                            "source_sha256":sha256_file(safe_path(path)) if exists else None,
                            "status":status})
    rows=[]
    for req in c["research_requirements"]:
        if req.get("state") not in ALLOWED_STATE:
            raise ValueError("invalid requirement state: "+req["id"])
        if req.get("family") not in registered_family:
            raise ValueError("unregistered strategy family: "+req["id"])
        if not req.get("goal") or not req.get("capabilities"):
            raise ValueError("untraceable requirement "+req["id"])
        if not set(req["capabilities"]).issubset(ids):
            raise ValueError("unknown capability in "+req["id"])
        if req["state"] in ("OOS_PASSED","FORWARD_VERIFIED") and not req.get("evidence_sha256"):
            raise ValueError("successful research cannot lack immutable evidence: "+req["id"])
        rows.append({"id":req["id"],"family":req["family"],
                     "state":req["state"],"goal":req["goal"],
                     "capabilities":req["capabilities"],
                     "evidence_sha256":req.get("evidence_sha256")})
    covered_families={r["family"] for r in rows}
    unscoped=sorted(registered_family-covered_families)
    missing_caps=sorted(x["id"] for x in c["capabilities"] if x["status"]!="implemented_verified")
    not_verified=sorted(x["id"] for x in rows if x["state"]!="FORWARD_VERIFIED")
    counts=dict(sorted(Counter(r["state"] for r in rows).items()))
    report={
        "schema":"H090.audit.v1",
        "kind":"COVERAGE_AUDIT_NOT_HISTORICAL_BACKTEST_NOT_ALPHA",
        "research_only":True,
        "catalog_sha256":sha256_file(CATALOG),
        "recipe_sha256":sha256_file(RECIPES),
        "strategy_families_total":len(registered_family),
        "unscoped_strategy_families":unscoped,
        "research_requirements_total":len(rows),
        "requirement_states":counts,
        "unverified_requirements":not_verified,
        "unverified_capabilities":missing_caps,
        "capability_source_checks":file_checks,
        "research_requirements":rows,
        "recipe_contracts": [{"id":r["id"],"kind":r["kind"],
                              "steps":[x["kind"] for x in r["sequence"]],
                              "live_authorized":False} for r in recipes],
        "research_complete":not unscoped and not not_verified and not missing_caps,
        "paper_prospective_replay_complete":False,
        "real_fills_verified":False,
        "portfolio_alpha_verified":False,
        "source_existence_does_not_prove_semantics":True
    }
    return report


def render_markdown(report: dict) -> str:
    lines=["# H090 — Research Coverage Audit", "",
           "**NOT A BACKTEST, NOT A PERFORMANCE RESULT, NOT LIVE-AUTHORIZED.**", "",
           f"Catalog sha256: \`{report['catalog_sha256']}\`", "",
           f"Requirements: {report['research_requirements_total']}; "
           f"unverified: {len(report['unverified_requirements'])}; "
           f"capability gaps: {len(report['unverified_capabilities'])}.", "",
           f"Unscoped families: {', '.join(report['unscoped_strategy_families']) or 'none'}.", "",
           "| Required experiment | Family | State | Missing proof |",
           "|---|---|---|---|"]
    for r in report["research_requirements"]:
        lines.append(f"| {r['id']} | {r['family']} | {r['state']} | "
                     f"{'YES' if not r['evidence_sha256'] else 'Evidence recorded; check quality'} |")
    lines.extend(["","## Capabilities needing research / implementation", ""])
    for c in report["capability_source_checks"]:
        if c["status"]!="implemented_verified":
            lines.append(f"- \`{c['capability']}\`: {c['status']}; "
                         f"source={'present' if c['exists'] else 'absent'}; "
                         f"marker={'present' if c['marker_found'] else 'absent'}")
    lines.extend(["","The audit checks metadata and code markers; it does **not** certify actual "
                   "event detectors, backtests, causality, costs, statistical significance or trade execution."])
    return "\n".join(lines)+"\n"


def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",default="results/h090_audit")
    ap.add_argument("--require-complete",action="store_true",
                    help="fail if any research gap remains (expected failure for initial H090)")
    args=ap.parse_args(argv)
    report=audit()
    out=safe_path(args.output_dir)
    out.mkdir(parents=True,exist_ok=True)
    (out/"coverage.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    (out/"coverage.md").write_text(render_markdown(report))
    print(json.dumps({"research_complete":report["research_complete"],
                      "requirements":report["research_requirements_total"],
                      "unverified":len(report["unverified_requirements"]),
                      "unscoped_families":report["unscoped_strategy_families"],
                      "output":str(out.relative_to(ROOT))},sort_keys=True))
    if args.require_complete and not report["research_complete"]:
        raise SystemExit("H090_NOT_COMPLETE: all listed gaps must be verified independently")


if __name__=="__main__":
    main()
