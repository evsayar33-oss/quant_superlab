"""No actual network calls during CI; real Telegram send occurs only after merge."""
import io
import json
import unittest
import urllib.error
from research.h119.telegram_smoke import send_test


class Reply:
    status = 200

    def __init__(self, obj):
        self.obj = obj

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.obj).encode()


class TestDirectTelegramSmoke(unittest.TestCase):
    def test_success_only_with_real_message_id_ack(self):
        calls = []

        def fake(request, timeout):
            calls.append((request.get_full_url(), request.data))
            return Reply({"ok": True, "result": {"message_id": 123}})

        status = send_test("secret", "12345", post=fake)
        self.assertIn("ACKNOWLEDGED", status)
        self.assertEqual(len(calls), 1)
        self.assertIn(b"12345", calls[0][1])
        self.assertIn(b"baglant", calls[0][1].lower())

    def test_missing_secret_fails(self):
        with self.assertRaisesRegex(RuntimeError, "MISSING_SECRETS"):
            send_test("", "123", post=lambda *a, **k: None)

    def test_success_without_message_id_is_not_success(self):
        with self.assertRaisesRegex(RuntimeError, "MISSING_DELIVERY_MESSAGE_ID"):
            send_test("token", "123", post=lambda *a, **k: Reply({"ok": True, "result": {}}))

    def test_rejected_bot_start_chat_id_is_explicit_without_leaking_token(self):
        def fail(request, timeout):
            raise urllib.error.HTTPError(request.full_url, 400, "Bad Request", {}, io.BytesIO())
        with self.assertRaisesRegex(RuntimeError, "BOT_NOT_STARTED") as context:
            send_test("private-test-bot-token", "234", post=fail)
        self.assertNotIn("private-test-bot-token", str(context.exception))

    def test_blocked_chat_fails(self):
        def fail(request, timeout):
            raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, io.BytesIO())
        with self.assertRaisesRegex(RuntimeError, "BOT_BLOCKED"):
            send_test("secret", "234", post=fail)


if __name__ == "__main__":
    unittest.main()
