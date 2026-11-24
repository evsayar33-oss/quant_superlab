"""Generic Eaverse research passport and independent return-path arithmetic.
This is NOT the central lab.validation backtest or an ACCEPT.
"""
import argparse
import gzip
import hashlib
import json
import math
import os
import re
import sqlite3
import tempfile
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen

from . import gate

REPO = "evsayar33-oss/eaverse"
SCHEMA = "QS.eaverse.research_receipt.v2"
LIMIT = 768 * 1024 * 1024
NAME = re.compile(r"state-(\d{20})-([0-9a-f]{64})\.sqlite\.gz")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def audit_record(row, kind="technical"):
    raw = dict(row)
    spec = json.loads(raw["spec"]) if kind == "technical" else json.loads(raw["summary"]).get("design")
    outcome = json.loads(raw["discovered"] if kind == "technical" else raw["summary"])
    policy = json.loads(raw["policy"]) if kind == "technical" else {"event_version": raw["version"]}
    valid = json.loads(raw.get("validated") or "{}") if kind == "technical" else outcome.get("recent", {})
    evidence = outcome.get("return_evidence")
    reproduced = False
    if evidence is not None:
        if evidence.get("sha256") != digest({k: v for k, v in evidence.items() if k != "sha256"}):
            raise ValueError("RETURN_PATH_HASH_MISMATCH")
        for name, metrics in (("discovery", outcome["metrics"]), ("validation", valid["metrics"])):
            path = evidence[name]
            if not path or any(not math.isfinite(x) or x < -1 for x in path):
                raise ValueError("BAD_RETURN_PATH")
            net = math.prod(1 + x for x in path) - 1
            if not math.isclose(net, metrics["net"], rel_tol=1e-8, abs_tol=1e-8):
                raise ValueError("RETURN_PATH_NET_MISMATCH")
        reproduced = True
    passport = {"source_repository": REPO, "hypothesis_id": raw["id"],
                "strategy_definition": json.dumps(spec, sort_keys=True),
                "methodology_sha256": digest(policy),
                "source_evidence_sha256": raw.get("snapshot"),
                "benchmark": "not independently verified", "read_only_research": True}
    result = gate.review(passport)
    return {"schema": SCHEMA, "kind": kind, "asset": raw["asset"], "id": raw["id"],
            "version": raw["version"], "source_record_sha256": digest({k:v for k,v in raw.items() if k != "rowid"}),
            "path_net_reproduced": reproduced, "gate": result,
            "central_lab_accept": False, "paper_approved": False, "live_allowed": False}


def inspect_db(path):
    counts, errors = Counter(), []
    with sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        for kind, sql in (("technical", "SELECT * FROM attempts WHERE policy<>''"),
                          ("event", "SELECT * FROM event_trials WHERE calendar<>''")):
            for row in db.execute(sql):
                try:
                    receipt = audit_record(row, kind)
                    counts[kind + "_reviewed"] += 1
                    counts["paths_reproduced"] += int(receipt["path_net_reproduced"])
                    counts["blocked"] += int(bool(receipt["gate"]["blockers"]))
                except (ValueError, TypeError, KeyError, OverflowError) as exc:
                    counts["invalid"] += 1
                    if len(errors) < 50:
                        errors.append({"id": row["id"], "error": str(exc)})
        counts["archived_not_replayed"] = db.execute("SELECT count(*) FROM attempts WHERE policy=''").fetchone()[0] + db.execute("SELECT count(*) FROM event_trials WHERE calendar=''").fetchone()[0]
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='foundry_cohorts'").fetchone():
            from . import eaverse_report_gate
            for row in db.execute("SELECT evidence,forward,status FROM foundry_cohorts"):
                cohort=json.loads(row[0])
                try:
                    receipt=eaverse_report_gate.review_cohort(cohort)
                    counts["cohorts_reproduced"]+=1
                    counts["cohort_pbo_available"]+=int(receipt["pbo"] is not None)
                    counts["cohort_dsr_available"]+=int(receipt["dsr"] is not None)
                    forward=json.loads(row[1])
                    if row[2]=="forward_matured_research_only":
                        result=forward["result"]
                        if result["sha256"]!=digest({k:v for k,v in result.items() if k!="sha256"}) or result["bars"]!=90:
                            raise ValueError("FORWARD_RECEIPT_MISMATCH")
                        if not math.isclose(math.prod(1+x for x in result["returns"])-1,result["metrics"]["net"],abs_tol=1e-8,rel_tol=1e-8):
                            raise ValueError("FORWARD_RETURN_MISMATCH")
                        counts["forward_path_arithmetic_reproduced"]+=1
                except (ValueError,TypeError,KeyError,OverflowError) as exc:
                    counts["invalid"]+=1
                    if len(errors)<50:
                        errors.append({"id":cohort.get("selected_id"),"error":str(exc)})
    return {"schema": SCHEMA, "counts": dict(counts), "errors": errors,
            "central_lab_accept": False, "paper_approved": False, "live_allowed": False}


def fetch_checkpoint(out):
    url = f"https://api.github.com/repos/{REPO}/releases/tags/research-state-v1"
    headers = {"User-Agent": "quant-superlab-coverage-audit", "Accept": "application/vnd.github+json"}
    if os.getenv("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        release = json.load(response)
    assets = sorted((x for x in release["assets"] if NAME.fullmatch(x["name"]) and x.get("state") == "uploaded"), key=lambda x:x["name"])
    if not assets:
        raise ValueError("NO_SOURCE_CHECKPOINT")
    asset = assets[-1]
    expected = NAME.fullmatch(asset["name"]).group(2)
    h = hashlib.sha256()
    archive = out.with_suffix(".gz")
    with urlopen(Request(f"https://github.com/{REPO}/releases/download/research-state-v1/{asset['name']}", headers={"User-Agent": "quant-superlab"}), timeout=60) as response, archive.open("wb") as f:
        while chunk := response.read(1024*1024):
            if f.tell() + len(chunk) > LIMIT:
                raise ValueError("SOURCE_COMPRESSED_LIMIT")
            h.update(chunk)
            f.write(chunk)
    if h.hexdigest() != expected:
        raise ValueError("SOURCE_CHECKPOINT_HASH_MISMATCH")
    with gzip.open(archive, "rb") as stream, out.open("wb") as f:
        while chunk := stream.read(1024*1024):
            if f.tell() + len(chunk) > LIMIT:
                raise ValueError("SOURCE_EXPANDED_LIMIT")
            f.write(chunk)
    return expected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "source.sqlite"
        sha = fetch_checkpoint(path)
        report = inspect_db(path)
    report["source_checkpoint_sha256"] = sha
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps(report["counts"]))
    if report["counts"].get("invalid"):
        raise SystemExit("INVALID_EAVERSE_EVIDENCE")


if __name__ == "__main__":
    main()
