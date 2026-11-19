"""Direct one-shot H119 Telegram connectivity verification; NOT an alpha signal.

Does not open Issues, change H119 registers, or fake a new profitable strategy.
Runs only on explicit workflow dispatch or protected main workflow bootstrap.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def send_test(token: str | None, chat: str | None, *, post=None) -> str:
    if not token or not chat:
        raise RuntimeError(
            "H119_TELEGRAM_MISSING_SECRETS: configure TELEGRAM_TOKEN and CHAT_ID "
            "in quant_superlab Actions repository secrets")
    message = (
        "✅ quant_superlab H119 — Telegram bağlantısı doğrulama testi\n\n"
        "Bu mesaj bir bağlantı testidir. Kârlı strateji, yeni ACCEPT kararı "
        "veya işlem sinyali değildir.\n\n"
        "Gerçek yeni araştırma adayları ve ileri test sonuçları oluştuğunda "
        "H119 otomatik bilgilendirme yapacaktır."
    )
    endpoint = "https://api.telegram.org/bot" + token + "/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat, "text": message,
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    request = urllib.request.Request(
        endpoint, method="POST", data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    handler = post or urllib.request.urlopen
    try:
        with handler(request, timeout=20) as response:
            if response.status != 200:
                raise RuntimeError("H119_TELEGRAM_HTTP_NON_200")
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        # Never print the request URL; it contains a secret bot token.
        if error.code in (401, 404):
            raise RuntimeError("H119_TELEGRAM_BOT_TOKEN_INVALID_OR_NOT_FOUND") from None
        if error.code == 403:
            raise RuntimeError(
                "H119_TELEGRAM_BOT_BLOCKED_OR_CANNOT_MESSAGE_CHAT") from None
        if error.code == 400:
            raise RuntimeError(
                "H119_TELEGRAM_BAD_CHAT_ID_OR_BOT_NOT_STARTED: open the bot "
                "in Telegram, press Start, verify CHAT_ID") from None
        if error.code == 429:
            raise RuntimeError("H119_TELEGRAM_RATE_LIMITED") from None
        raise RuntimeError("H119_TELEGRAM_HTTP_ERROR_" + str(error.code)) from None
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(
            "H119_TELEGRAM_CONNECTION_TIMEOUT_OR_NETWORK_FAILURE") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise RuntimeError("H119_TELEGRAM_MALFORMED_RESPONSE") from None
    if payload.get("ok") is not True:
        raise RuntimeError("H119_TELEGRAM_NOT_ACKNOWLEDGED")
    result = payload.get("result") or {}
    if not isinstance(result.get("message_id"), int):
        raise RuntimeError("H119_TELEGRAM_MISSING_DELIVERY_MESSAGE_ID")
    return "H119_TELEGRAM_ACKNOWLEDGED: Telegram API accepted test message"


def main():
    token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")
    try:
        print(send_test(token, chat))
    except RuntimeError as exc:
        print("::error title=H119 Telegram connectivity test failed::" + str(exc),
              file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
