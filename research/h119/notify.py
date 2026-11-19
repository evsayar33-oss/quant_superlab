"""H119 low-noise milestone notifications with durable delivery receipts.

Primary: existing TELEGRAM_TOKEN + CHAT_ID. If not configured/unavailable,
GitHub Issues fallback (requires GITHUB_TOKEN issues:write). No secrets logged.
Deliver first, then append a SHA receipt; unsuccessful delivery remains pending.
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
from research.h119.engine import NOTIFY_EVENT_TYPES, SCHEMA, append_chain, event_id, read_chain

MAX_PER_BATCH = 8


def line(x):
    kind = x["kind"]
    if kind == "NOTIFICATION_READY":
        return ("H119 otomatik kesif ve kanit izleme aktif. "
                "Bu bir kanal testidir; karli strateji bulundugu anlamina gelmez.")
    if kind == "NEW_LAB_ACCEPT":
        d = x.get("evidence", {})
        return (f"YENI LAB ACCEPT: {x['hypothesis']}, {d.get('strategy','')} "
                f"(DSR={d.get('dsr','?')}; forward PnL ayrica incelenmeli)")
    if kind == "LAB_ACCEPT_REVOKED":
        return f"ONEMLI: {x['hypothesis']} artik resmi ACCEPT listesinde degil."
    market, rule, side, horizon = (x.get(k, "") for k in
                                   ("market", "rule", "side", "horizon"))
    d = x.get("evidence", {})
    desc = f"{market} {side} {rule} / {horizon}"
    if kind == "COSTED_RESEARCH_CANDIDATE":
        return (f"NET-POZITIF ARASTIRMA ADAYI: {desc}; "
                f"model net ort. %{d.get('net_mean_pct','?')}, "
                f"stres %{d.get('cost_stress_pct','?')}; "
                "quant_superlab ACCEPT DEGIL.")
    if kind == "FUTURE_TRIAL_FROZEN":
        return f"ILERI TESTE ALINDI: {desc}; kurallar donduruldu; kar kaniti degil."
    if kind == "POSITIVE_FORWARD_RESEARCH":
        return (f"ILERI TESTTE POZITIF ARASTIRMA SONUCU: {desc}; "
                f"model net %{d.get('net_mean_pct','?')}; "
                "gercek emir/fill ve tam lab onayi dogrulanmadi.")
    raise ValueError("UNKNOWN_ALERT_KIND")


def message(events):
    if not events:
        return None
    if any(x.get("kind") not in NOTIFY_EVENT_TYPES
           or x.get("schema") != SCHEMA for x in events):
        raise ValueError("INVALID_ALERT_EVENT")
    lines = ["quant_superlab H119 | onemli strateji olaylari"]
    lines += [line(x) for x in events]
    lines += [
        "Arastirma ve model PnL sonucudur. "
        "Sadece resmi karar kapisi ACCEPT verebilir; bu mesaj emir onayi degildir.",
        "Kaynak: https://github.com/evsayar33-oss/quant_superlab/actions/workflows/h119.yml",
    ]
    return "\n\n".join(lines)[:3900]


def request_json(url, data=None, token=None):
    headers = {"User-Agent": "quant-superlab-h119",
               "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if data is not None:
        data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        url, data=data, headers=headers,
        method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=18) as resp:
        if resp.status not in (200, 201):
            raise RuntimeError("UNEXPECTED_NOTIFICATION_HTTP_STATUS")
        return json.loads(resp.read().decode("utf-8"))


def send_telegram(text, token, chat):
    if not token or not chat:
        return False
    body = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    req = urllib.request.Request(
        "https://api.telegram.org/bot" + token + "/sendMessage",
        data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=18) as resp:
            return resp.status == 200 and json.load(resp).get("ok") is True
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


def fallback_issue(text, events, token, repo):
    if not token or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        return False, None
    signature = event_id("H119_ISSUE_BATCH", *sorted(x["id"] for x in events))[:14]
    base = "https://api.github.com/repos/" + repo + "/issues"
    title = "[H119 ALPHA] " + signature + " - significant research update"
    # Retry-safe fallback: on receipt-commit loss, find an existing issue.
    for page in (1, 2, 3):
        existing = request_json(base + "?state=all&per_page=100&page=" + str(page),
                                token=token)
        if any(i.get("title") == title for i in existing):
            return True, "existing_issue"
        if len(existing) < 100:
            break
    details = (
        "**Autonomous research milestone; NOT an order instruction.**\n\n"
        + text + "\n\n"
        + "Event IDs (receipt deduplication):\n"
        + "\n".join("- " + x["id"] for x in events)
        + "\n\nTelegram credentials may be missing or Telegram may have "
          "been unreachable; check Actions secrets TELEGRAM_TOKEN, CHAT_ID."
    )
    response = request_json(base, {"title": title, "body": details}, token)
    return bool(response.get("number")), str(response.get("number"))


def notify(state_dir, token=None, chat=None, github_token=None, repo=None,
           transport=None, issue_transport=None, when=None):
    state = Path(state_dir)
    events = read_chain(state / "events.jsonl")
    receipts = read_chain(state / "receipts.jsonl")
    notified = {x["event_id"] for x in receipts}
    pending = [x for x in events
               if x["kind"] in NOTIFY_EVENT_TYPES and x["id"] not in notified]
    if not pending:
        return {"status": "NO_NEW_MILESTONES", "delivered": 0, "pending": 0}
    batch = pending[:MAX_PER_BATCH]
    txt = message(batch)
    token = token if token is not None else (
        os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN"))
    chat = chat if chat is not None else (
        os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID"))
    gh = github_token if github_token is not None else os.getenv("GITHUB_TOKEN")
    name = repo if repo is not None else os.getenv("GITHUB_REPOSITORY", "")
    sender = transport or send_telegram
    issue_sender = issue_transport or fallback_issue
    ok = sender(txt, token, chat) if token and chat else False
    method = "TELEGRAM" if ok else ""
    receipt_ref = "Telegram delivery confirmed" if ok else ""
    if not ok:
        try:
            fallback_ok, reference = issue_sender(txt, batch, gh, name)
            if fallback_ok:
                method = "GITHUB_ISSUE_FALLBACK"
                receipt_ref = reference
                ok = True
        except (urllib.error.URLError, ValueError, RuntimeError) as exc:
            print("H119_GITHUB_FALLBACK_UNAVAILABLE", type(exc).__name__)
    if not ok:
        raise RuntimeError(
            "H119_MILESTONE_UNDELIVERED: set TELEGRAM_TOKEN+CHAT_ID "
            "or enable GITHUB_TOKEN issues write; events remain queued")
    timestamp = when or datetime.now(timezone.utc)
    records = [{
        "schema": SCHEMA, "kind": "notification_receipt",
        "id": event_id("receipt", x["id"]), "event_id": x["id"],
        "method": method, "reference": receipt_ref,
        "delivered_utc": timestamp.isoformat(),
    } for x in batch]
    append_chain(state / "receipts.jsonl", records,
                 int(timestamp.timestamp() * 1000))
    return {
        "status": "MILESTONES_DELIVERED", "method": method,
        "delivered": len(batch), "pending": len(pending) - len(batch),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True)
    a = parser.parse_args()
    result = notify(a.state)
    print(json.dumps(result, sort_keys=True))
    if result["pending"]:
        print("::warning::H119 notification batch limit hit; remaining events "
              "will be delivered in next scheduled workflow")


if __name__ == "__main__":
    main()
