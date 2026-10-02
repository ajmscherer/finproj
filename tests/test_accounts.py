# finproj - accounts, guest caps, and the public-site gate
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "code"))

import accounts
import stripe_billing


def _now(day: int = 1, hour: int = 12) -> datetime:
    return datetime(2026, 10, day, hour, tzinfo=timezone.utc)


class DeploymentModeTest(unittest.TestCase):
    def test_local_and_private_hosts_skip_sign_in(self) -> None:
        secret = "whatever"
        for host in ("", "localhost", "127.0.0.1", "192.168.1.20", "10.1.1.1", "mac.local"):
            self.assertEqual(accounts.deployment_mode(host, secret), "local", host)

    def test_public_host_without_the_secret_is_refused(self) -> None:
        self.assertEqual(accounts.deployment_mode("143.244.154.68", ""), "refused")
        self.assertEqual(accounts.deployment_mode("143.244.154.68", "not-the-secret"), "refused")
        self.assertEqual(accounts.deployment_mode("example.com", ""), "refused")

    def test_public_host_with_the_secret_is_hosted(self) -> None:
        secret = Path(PROJECT_ROOT / ".host-secret").read_text().strip()
        self.assertTrue(accounts.host_secret_matches(secret))
        self.assertEqual(accounts.deployment_mode("143.244.154.68", secret), "hosted")

    def test_a_local_computer_stays_local_even_with_the_secret(self) -> None:
        secret = Path(PROJECT_ROOT / ".host-secret").read_text().strip()
        self.assertEqual(accounts.deployment_mode("localhost", secret), "local")
        self.assertEqual(accounts.deployment_mode("10.0.0.8", secret), "local")


class QuotaTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.ledger = accounts.Ledger(Path(self.directory.name) / "accounts.sqlite")

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_guest_allows_three_runs_per_day(self) -> None:
        self.ledger.remember_guest("guest-1", _now())
        for _ in range(3):
            usage = self.ledger.consume(
                role="guest", subject_id="guest-1", client_ip="203.0.113.8", now=_now()
            )
            self.assertTrue(usage.allowed)
        blocked = self.ledger.consume(
            role="guest", subject_id="guest-1", client_ip="203.0.113.8", now=_now()
        )
        self.assertFalse(blocked.allowed)
        self.assertEqual(blocked.used, 3)
        self.assertIn("3 guest runs", accounts.denial_message(blocked))

    def test_a_new_guest_cookie_does_not_reset_the_address_cap(self) -> None:
        self.ledger.remember_guest("guest-1", _now())
        self.ledger.remember_guest("guest-2", _now())
        for _ in range(3):
            self.ledger.consume(role="guest", subject_id="guest-1", client_ip="203.0.113.9", now=_now())
        blocked = self.ledger.consume(
            role="guest", subject_id="guest-2", client_ip="203.0.113.9", now=_now()
        )
        self.assertFalse(blocked.allowed)
        other_address = self.ledger.consume(
            role="guest", subject_id="guest-2", client_ip="203.0.113.10", now=_now()
        )
        self.assertTrue(other_address.allowed)

    def test_plan_a_allows_five_runs_per_day(self) -> None:
        account_id = self.ledger.create_account("a@example.com", "password1", _now())
        subject = str(account_id)
        for _ in range(5):
            usage = self.ledger.consume(role="A", subject_id=subject, now=_now())
            self.assertTrue(usage.allowed)
        blocked = self.ledger.consume(role="A", subject_id=subject, now=_now())
        self.assertFalse(blocked.allowed)
        self.assertEqual(accounts.remaining_label(blocked), "Plan A · 0 of 5 runs left today")
        next_day = self.ledger.consume(role="A", subject_id=subject, now=_now(day=2))
        self.assertTrue(next_day.allowed)

    def test_plan_b_allows_one_hundred_runs_per_month(self) -> None:
        account_id = self.ledger.create_account("b@example.com", "password1", _now())
        self.ledger.set_plan(account_id, "B")
        subject = str(account_id)
        for _ in range(100):
            usage = self.ledger.consume(role="B", subject_id=subject, now=_now())
            self.assertTrue(usage.allowed)
        blocked = self.ledger.consume(role="B", subject_id=subject, now=_now(day=20))
        self.assertFalse(blocked.allowed)
        self.assertIn("100 runs", accounts.denial_message(blocked))
        november = datetime(2026, 11, 1, tzinfo=timezone.utc)
        self.assertTrue(self.ledger.consume(role="B", subject_id=subject, now=november).allowed)

    def test_plan_c_is_unlimited(self) -> None:
        account_id = self.ledger.create_account("c@example.com", "password1", _now())
        self.ledger.set_plan(account_id, "C")
        subject = str(account_id)
        for _ in range(12):
            usage = self.ledger.consume(role="C", subject_id=subject, now=_now())
            self.assertTrue(usage.allowed)
            self.assertIsNone(usage.limit)
        self.assertEqual(accounts.remaining_label(usage), "Plan C · unlimited")

    def test_a_refused_run_is_not_recorded(self) -> None:
        self.ledger.remember_guest("guest-1", _now())
        for _ in range(3):
            self.ledger.consume(role="guest", subject_id="guest-1", client_ip="203.0.113.4", now=_now())
        self.ledger.consume(role="guest", subject_id="guest-1", client_ip="203.0.113.4", now=_now())
        peeked = self.ledger.usage(role="guest", subject_id="guest-1", client_ip="203.0.113.4", now=_now())
        self.assertEqual(peeked.used, 3)

    def test_two_overlapping_requests_cannot_pass_the_last_run(self) -> None:
        self.ledger.remember_guest("guest-1", _now())
        self.ledger.consume(role="guest", subject_id="guest-1", client_ip="203.0.113.5", now=_now())
        self.ledger.consume(role="guest", subject_id="guest-1", client_ip="203.0.113.5", now=_now())
        barrier = threading.Barrier(2)
        results: list[accounts.Usage] = []

        def worker() -> None:
            barrier.wait()
            results.append(
                self.ledger.consume(
                    role="guest",
                    subject_id="guest-1",
                    client_ip="203.0.113.5",
                    now=_now(),
                )
            )

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sum(1 for result in results if result.allowed), 1)

    def test_sign_in_and_duplicate_email(self) -> None:
        account_id = self.ledger.create_account("Alex@Example.com", "password1")
        self.assertEqual(self.ledger.authenticate("alex@example.com", "password1"), account_id)
        self.assertIsNone(self.ledger.authenticate("alex@example.com", "wrong-password"))
        with self.assertRaises(ValueError):
            self.ledger.create_account("alex@example.com", "password1")
        with self.assertRaises(ValueError):
            self.ledger.create_account("alex@example.com", "short")

    def test_session_round_trip(self) -> None:
        account_id = self.ledger.create_account("session@example.com", "password1")
        token = self.ledger.open_session(account_id)
        account = self.ledger.account_for_session(token)
        self.assertIsNotNone(account)
        assert account is not None
        self.assertEqual(account["plan"], "A")
        self.ledger.close_session(token)
        self.assertIsNone(self.ledger.account_for_session(token))

    def test_forwarded_client_address_uses_the_last_hop(self) -> None:
        self.assertEqual(accounts.client_ip_from("1.1.1.1, 203.0.113.8", "10.0.0.1"), "203.0.113.8")
        self.assertEqual(accounts.client_ip_from("", "203.0.113.8"), "203.0.113.8")


class StripeParseTest(unittest.TestCase):
    def test_paid_checkout_selects_the_plan(self) -> None:
        parsed = stripe_billing.plan_from_checkout(
            {
                "status": "complete",
                "metadata": {"plan": "B"},
                "customer": "cus_1",
                "subscription": "sub_1",
            }
        )
        self.assertEqual(parsed, ("B", "cus_1", "sub_1"))
        self.assertIsNone(stripe_billing.plan_from_checkout({"status": "open", "metadata": {"plan": "B"}}))

    def test_checkout_request_uses_the_plan_price(self) -> None:
        captured = {}

        class Response:
            status = 200

            def read(self) -> bytes:
                return json.dumps({"id": "cs_1", "url": "https://checkout.stripe.test/pay"}).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args) -> bool:
                return False

        def opener(request, timeout=30):
            captured["url"] = request.full_url
            captured["body"] = request.data.decode()
            captured["auth"] = request.get_header("Authorization")
            return Response()

        with patch.dict(os.environ, {"FINPROJ_STRIPE_PRICE_C": "price_c"}, clear=False):
            session = stripe_billing.create_checkout_session(
                account_id=7,
                email="a@example.com",
                plan="C",
                success_url="https://143.244.154.68/?session_id={CHECKOUT_SESSION_ID}",
                cancel_url="https://143.244.154.68/",
                secret="sk_test",
                opener=opener,
            )
        self.assertEqual(session["id"], "cs_1")
        self.assertIn("metadata%5Bplan%5D=C", captured["body"])
        self.assertEqual(captured["auth"], "Bearer sk_test")
        self.assertFalse(stripe_billing.configured({}))
        self.assertTrue(
            stripe_billing.configured(
                {
                    "FINPROJ_STRIPE_SECRET_KEY": "sk",
                    "FINPROJ_STRIPE_PRICE_B": "price_b",
                    "FINPROJ_STRIPE_PRICE_C": "price_c",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
