"""Transport, tamper-evident journals and notification receipts for isolated lanes.

This module contains no strategy logic, no shared hypothesis state and
cannot approve a strategy or access brokers. Every lane owns its own branch.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SHA = re.compile(r"^[a-f0-9]{40}$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def canonical(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def hashobj(data):
    return hashlib.sha256(canonical(data).encode()).hexdigest()


def utc(value):
    val = str(value).strip().replace("Z", "+00:00")
    t = datetime.fromisoformat(val)
    if t.tzinfo is None:
        raise ValueError("NAIVE_TIME_REJECTED")
    return t.astimezone(timezone.utc)


def request(url):
    headers = {"User-Agent": "quant-superlab-isolated-paper-research/1"}
    if url.startswith("https://api.github.com/"):
        headers["Accept"] = "application/vnd.github+json"
        token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        if token:
            headers["Authorization"] = "Bearer " + token
            headers["X-GitHub-Api-Version"] = "2022-11-28"
    with urllib.request.urlopen(
            urllib.request.Request(url, headers=headers), timeout=25) as resp:
        return resp.read().decode("utf-8")


def get_sha(repo, branch, get=request):
    if not REPO.fullmatch(repo):
        raise ValueError("INVALID_SOURCE_REPO")
    value = json.loads(get(
        f"https://api.github.com/repos/{repo}/git/ref/heads/{branch}"))
    sha = value["object"]["sha"]
    if not SHA.fullmatch(sha):
        raise ValueError("INVALID_SOURCE_SHA")
    return sha


def ensure_fast_forward(repo, before, after, get=request):
    if not before or before == after:
        return
    if not SHA.fullmatch(before) or not SHA.fullmatch(after):
        raise ValueError("INVALID_SHA_CONTINUITY")
    result = json.loads(get(
        f"https://api.github.com/repos/{repo}/compare/{before}...{after}"))
    if result.get("status") != "ahead" or result.get("behind_by") != 0:
        raise ValueError("SOURCE_HISTORY_REWRITTEN_OR_ROLLED_BACK")


def pinned(repo, sha, path, get=request):
    if not REPO.fullmatch(repo) or not SHA.fullmatch(sha):
        raise ValueError("UNPINNED_SOURCE_REJECTED")
    if path.startswith("/") or ".." in path.split("/"):
        raise ValueError("UNSAFE_SOURCE_PATH")
    value = get(f"https://raw.githubusercontent.com/{repo}/{sha}/{path}")
    return value, hashlib.sha256(value.encode("utf-8")).hexdigest()


def journal(path, schema):
    file = Path(path)
    if not file.exists():
        return []
    previous, seq, rows = "GENESIS", 0, []
    for line in file.read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        record = {k: v for k, v in d.items() if k != "sha256"}
        if (d.get("schema") != schema
                or d.get("seq") != seq + 1
                or d.get("prev_sha256") != previous
                or d.get("sha256") != hashobj(record)):
            raise ValueError("TAMPERED_OR_MISSING_JOURNAL_RECORD")
        previous, seq = d["sha256"], d["seq"]
        rows.append(d)
    return rows


def append(path, schema, additions):
    path = Path(path)
    existing = journal(path, schema)
    ids = {x["id"] for x in existing}
    previous = existing[-1]["sha256"] if existing else "GENESIS"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for item in additions:
            if item["id"] in ids:
                continue
            x = dict(item)
            x.update({"schema": schema, "seq": len(existing) + 1,
                      "prev_sha256": previous})
            x["sha256"] = hashobj(x)
            f.write(canonical(x) + "\n")
            existing.append(x)
            ids.add(x["id"])
            previous = x["sha256"]
    return existing


def read_manifest(root, schema):
    root = Path(root)
    manifest = root / "manifest.json"
    current = json.loads(manifest.read_text()) if manifest.exists() else {}
    if current and current.get("schema") != schema:
        raise ValueError("UNKNOWN_EXISTING_MANIFEST_SCHEMA")
    if current and any(not (root / name).exists()
                       for name in ("events.jsonl", "receipts.jsonl", "latest.json")):
        raise ValueError("PREVIOUS_RESEARCH_EVIDENCE_LOST")
    journal(root / "events.jsonl", schema)
    journal(root / "receipts.jsonl", schema)
    return current


def record(root, schema, manifest, report, new_events):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    events = append(root / "events.jsonl", schema, new_events)
    (root / "receipts.jsonl").touch(exist_ok=True)
    receipts = journal(root / "receipts.jsonl", schema)
    received = {x["event_id"] for x in receipts}
    report.update({
        "schema": schema,
        "events_total": len(events),
        "events_new": sum(e["id"] in {x["id"] for x in new_events}
                          for e in events),
        "alerts_pending": sum(e["id"] not in received for e in events),
        "research_only": True,
        "official_lab_accept": "NOT_RUN",
        "live_trading_enabled": False,
    })
    manifest["schema"] = schema
    (root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    (root / "latest.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return report


def send_telegram(message, token, chat):
    if not token or not chat:
        return False
    body = urllib.parse.urlencode({"chat_id": chat, "text": message}).encode()
    req = urllib.request.Request(
        "https://api.telegram.org/bot" + token + "/sendMessage",
        data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
            return (r.status == 200 and data.get("ok") is True
                    and isinstance((data.get("result") or {}).get("message_id"), int))
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


def issue_fallback(message, group, token, repository):
    if not token or not REPO.fullmatch(repository):
        return False
    owner = repository.split("/")[0]
    signature = hashobj(sorted(e["id"] for e in group))[:14]
    title = "[Quant Intelligence] " + group[0]["lane"] + " " + signature
    base = "https://api.github.com/repos/" + repository + "/issues"
    headers = {"Accept": "application/vnd.github+json",
               "Authorization": "Bearer " + token,
               "User-Agent": "quant-superlab-independent-lanes"}
    def call(url, payload=None):
        if payload is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, headers=headers,
                data=json.dumps(payload).encode() if payload is not None else None,
                method="POST" if payload is not None else "GET")
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    # Duplicate-safe across retries when issue creation succeeded but
    # receipt publication did not. Never put bot secrets in issue content.
    for page in (1, 2):
        entries = call(base + f"?state=all&per_page=100&page={page}")
        if any(x.get("title") == title for x in entries):
            return True
        if len(entries) < 100:
            break
    result = call(base, {"title": title,
                         "body": "@" + owner + "\n\n" + message,
                         "assignees": [owner]})
    return bool(result.get("number"))


def notify(root, schema, sender=send_telegram, issue=issue_fallback):
    root = Path(root)
    read_manifest(root, schema)
    records = journal(root / "events.jsonl", schema)
    receipts = journal(root / "receipts.jsonl", schema)
    delivered = {x["event_id"] for x in receipts}
    pending = [e for e in records if e["id"] not in delivered]
    if not pending:
        print("INDEPENDENT_LANE_NO_NEW_MILESTONES")
        return {"delivered": 0, "pending": 0}
    group = pending[:5]
    message = (
        "quant_superlab " + group[0]["lane"] + " | arastirma / risk bildirimi\n\n"
        + "\n\n".join(e["message"] for e in group)
        + "\n\nBu bir PAPER / arastirma denetimidir. "
          "LIVE islem izni veya Superlab ACCEPT degildir."
    )[:3950]
    token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")
    ok = sender(message, token, chat) if token and chat else False
    method = "TELEGRAM" if ok else "NONE"
    if not ok:
        try:
            ok = issue(message, group, os.getenv("GITHUB_TOKEN", ""),
                       os.getenv("GITHUB_REPOSITORY", ""))
        except (urllib.error.URLError, ValueError, RuntimeError):
            ok = False
        method = "GITHUB_ASSIGNED_ISSUE" if ok else "NONE"
    if not ok:
        raise RuntimeError("RESEARCH_MILESTONES_UNDELIVERED_RETRY_REQUIRED")
    now = datetime.now(timezone.utc).isoformat()
    additions = [{
        "id": hashobj(["receipt", e["id"]]), "kind": "ACK",
        "event_id": e["id"], "method": method, "sent_at_utc": now,
    } for e in group]
    receipts = append(root / "receipts.jsonl", schema, additions)
    report_path = root / "latest.json"
    report = json.loads(report_path.read_text())
    if report.get("schema") != schema:
        raise ValueError("NOTIFY_LATEST_SCHEMA_MISMATCH")
    received = {r["event_id"] for r in receipts}
    report["alerts_pending"] = sum(e["id"] not in received for e in records)
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    print(f"INDEPENDENT_LANE_DELIVERY_OK method={method} count={len(group)}")
    return {"delivered": len(group), "pending": len(pending) - len(group)}


def notify_main(schema):
    import argparse
    a = argparse.ArgumentParser()
    a.add_argument("--state", required=True)
    args = a.parse_args()
    notify(args.state, schema)
