"""Bounded, non-executable research-hypothesis inventory.

Emits protocol IDs, not trading strategies, winners, backtests, or newly
accepted PAPER experiments. Existing repo strategy logic remains authoritative.
"""
from __future__ import annotations
import argparse
import hashlib
import itertools
import json
from pathlib import Path
from .audit import load_catalog


def designs(project):
    groups = project["families"]
    if not groups or len(groups) != len(set(groups)) or len(groups) > 12:
        raise ValueError("INVALID_REPO_FEATURE_FAMILIES")
    # Deliberately bound combinatorial mining: baseline + singles + distinct pairs.
    variants = [()] + [(x,) for x in groups] + list(itertools.combinations(groups, 2))
    if len(variants) > 79:
        raise ValueError("UNBOUNDED_HYPOTHESIS_SEARCH")
    proposals = []
    for family in variants:
        spec = {"repository": "evsayar33-oss/" + project["name"],
                "domain": project["domain"],
                "signal_information_groups": list(family),
                "objective": project["scope"],
                "status": "DESIGN_ONLY_NO_COMPUTED_BACKTEST",
                "asof_features_only": True,
                "pre_registered": False,
                "price_after_event_not_used_as_feature": True,
                "validation": "NOT_RUN",
                "paper_approved": False,
                "live_approved": False}
        spec["id"] = hashlib.sha256(
            json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:20]
        proposals.append(spec)
    return proposals


def plan(catalog=None):
    catalog = catalog or load_catalog()
    return {"schema": "QS.portfolio_qualification.designs.v1",
            "purpose": "RESEARCH_DESIGN_QUEUE_NOT_AN_EXECUTABLE_STRATEGY",
            "projects": {p["name"]: designs(p) for p in catalog["projects"]},
            "declaration": ("All combinations are BOUNDED high-level information dimensions, "
                "not tested numerical thresholds or independent alpha evidence; each "
                "idea needs project-specific data, preregistration, OOS and costed "
                "forward verification before any PAPER eligibility."),
            "auto_promote": False}


def main():
    arg = argparse.ArgumentParser()
    arg.add_argument("--out", default="out/portfolio_qualification")
    args = arg.parse_args()
    x = plan()
    path = Path(args.out)
    path.mkdir(parents=True, exist_ok=True)
    (path / "candidate_designs.json").write_text(
        json.dumps(x, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("DESIGN_ONLY", sum(len(a) for a in x["projects"].values()), "hypotheses")


if __name__ == "__main__":
    main()
