"""H120 Tier-1-only research notifications, independent from H119/Early Radar.

Telegram first; assigned GitHub issue fallback. SHA-linked receipts are written
only after a delivery is confirmed and are stored on H120's independent branch.
No periodic "no alpha" notifications, no bot orders, no fake ACCEPT claims.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from research.h120.engine import (
    NOTIFY_KINDS, SCHEMA, append_ledger, fingerprint, read_ledger,
)

BATCH_SIZE = 6


def render(item):
    kind, x = item["kind"], item["evidence"]
    if kind == "SEALED_STUDY_DECISION":
        return (
            "Tier-1 kesinlesen arastirma karari\n"
            + x["study_id"] + ": " + x["decision"] + "\n"
            + ("Neden: " + x.get("reasons", "") + "\n" if x.get("reasons") else "")
            + "Bu resmi quant_superlab ACCEPT ya da islem izni DEGIL."
        )
    if kind == "PROSPECTIVE_REPLICATION_LEAD":
        m = x["metrics"]
        return (
            f"Tier-1 bagimsiz ileri gozlem adayi {x['horizon']}s\n"
            f"n={m['observations']}, model={m['model_hit']}, "
            f"always-long={m['always_long_hit']}, "
            f"Bonferroni p={m['bonferroni_12_p']}\n"
            "Ek native Superlab backtest, maliyet ve PIT denetimi gerekir; "
            "ACCEPT DEGIL."
        )
    if kind == "SOURCE_AUDIT_STALE":
        return (
            "Tier-1 bagimsiz audit KESINTI UYARISI\n"
            f"Son audit: {x['last_audit_utc']} / "
            f"kesinti yaklasik {x['hours_without_audit']} saat\n"
            "Yalnizca audit kaynaginin gecikmesi tespit edildi; "
            "uretimin durdugu varsayilmiyor."
        )
    raise ValueError("H120_UNKNOWN_NOTICE_KIND")


def make_message(batch):
    if not batch or any(e.get("kind") not in NOTIFY_KINDS
                        or e.get("schema") != SCHEMA for e in batch):
        raise ValueError("H120_UNTRUSTED_NOTIFICATION_BATCH")
    return (
        "quant_superlab H120 | Tier-1 bagimsiz arastirma\n\n"
        + "\n\n".join(render(x) for x in batch)
        + "\n\nEarly Radar H119'dan bagimsizdir. "
          "Yalnizca research-only bildirim; canli islem emri degildir.\n"
          "https://github.com/evsayar33-oss/quant_superlab/actions/workflows/h120.yml"
    )[:3990]


def telegram_send(message, token, chat):
    if not token or not chat:
        return False
    data = urllib.parse.urlencode({"chat_id": chat, "text": message}).encode()
    req = urllib.request.Request(
        "https://api.telegram.org/bot" + token + "/sendMessage",
        data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.load(response)
            return bool(response.status == 200 and data.get("ok") is True
                        and isinstance((data.get("result") or {}).get("message_id"), int))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError):
        return False


def github_request(url, token, body=None):
    headers = {"User-Agent": "quant-superlab-h120",
               "Accept": "application/vnd.github+json",
               "Authorization": "Bearer " + token}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        url, data=json.dumps(body).encode() if body is not None else None,
        method="POST" if body is not None else "GET", headers=headers)
    with urllib.request.urlopen(req, timeout=20) as response:
        if response.status not in (200, 201):
            raise RuntimeError("H120_GITHUB_ISSUE_HTTP_ERROR")
        return json.load(response)


def issue_fallback(message, batch, token, repository):
    if not token or not re.fullmatch(r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+", repository):
        return False, None
    owner = repository.split("/")[0]
    signature = fingerprint(sorted(e["id"] for e in batch))[:14]
    title = "[H120 TIER1] " + signature + " - evidence milestone"
    base = "https://api.github.com/repos/" + repository + "/issues"
    for page in range(1, 4):
        found = github_request(
            base + f"?state=all&per_page=100&page={page}", token)
        if any(issue.get("title") == title for issue in found):
            return True, "existing_issue"
        if len(found) < 100:
            break
    body = (
        "@" + owner + " **Tier-1 research milestone; not an order.**\n\n"
        + message + "\n\n"
        + "Evidence IDs:\n"
        + "\n".join("- " + e["id"] for e in batch)
        + "\n\nIf Telegram failed, verify TELEGRAM_TOKEN and CHAT_ID."
    )
    created = github_request(base, token, {
        "title": title, "body": body, "assignees": [owner],
    })
    return bool(created.get("number")), str(created.get("number"))


def notify(state, sender=None, fallback=None, token=None, chat=None,
           github_token=None, repository=None, now=None):
    root = Path(state)
    events, receipts = (
        read_ledger(root / "events.jsonl"),
        read_ledger(root / "receipts.jsonl"))
    sent = {r["event_id"] for r in receipts}
    pending = [
        e for e in events
        if e["kind"] in NOTIFY_KINDS and e["id"] not in sent
    ]
    if not pending:
        return {"status": "NO_NEW_MILESTONE", "delivered": 0, "pending": 0}
    batch, message = pending[:BATCH_SIZE], None
    message = make_message(batch)
    token = token if token is not None else (
        os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN"))
    chat = chat if chat is not None else (
        os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID"))
    github_token = github_token if github_token is not None else os.getenv("GITHUB_TOKEN")
    repository = repository if repository is not None else os.getenv("GITHUB_REPOSITORY", "")
    send = sender or telegram_send
    fallback_fn = fallback or issue_fallback
    ok = send(message, token, chat) if token and chat else False
    method, reference = ("TELEGRAM", "message_id_acknowledged") if ok else ("", "")
    if not ok:
        try:
            ok, reference = fallback_fn(message, batch, github_token, repository)
            if ok:
                method = "ASSIGNED_GITHUB_ISSUE"
        except (urllib.error.URLError, ValueError, RuntimeError) as exc:
            # No authorization headers or Telegram tokens in output.
            print("H120_ISSUE_FALLBACK_UNAVAILABLE", type(exc).__name__)
    if not ok:
        raise RuntimeError("H120_MILESTONE_UNDELIVERED_PRESERVED_FOR_RETRY")
    now = now or datetime.now(timezone.utc)
    confirmed = [{
        "id": fingerprint(["receipt", e["id"]]),
        "kind": "NOTIFICATION_RECEIPT", "event_id": e["id"],
        "method": method, "reference": reference, "delivered_utc": now.isoformat(),
    } for e in batch]
    receipts = append_ledger(root / "receipts.jsonl", confirmed)
    latest = root / "latest.json"
    if latest.exists():
        report = json.loads(latest.read_text(encoding="utf-8"))
        if report.get("schema") != SCHEMA:
            raise ValueError("H120_LATEST_SCHEMA_MISMATCH")
        delivered = {x["event_id"] for x in receipts}
        report["pending_notifications"] = sum(
            x["kind"] in NOTIFY_KINDS and x["id"] not in delivered
            for x in events)
        report["last_notification_delivery"] = {
            "utc": now.isoformat(), "method": method, "count": len(batch),
        }
        latest.write_text(json.dumps(report, indent=2, ensure_ascii=False,
                                     sort_keys=True) + "\n", encoding="utf-8")
    return {"status": "DELIVERED", "method": method,
            "delivered": len(batch), "pending": len(pending) - len(batch)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True)
    args = parser.parse_args()
    result = notify(args.state)
    print("H120_ALERT", json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
