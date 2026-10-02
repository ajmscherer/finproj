# finproj - Stripe subscriptions for Plan B and Plan C
# Copyright (C) 2025-2026 Alex Scherer

"""Stripe Checkout and the customer portal, using the standard library.

The secret key and the two price ids stay in the server environment. They are
not part of this repository. When they are absent, paid checkout is not turned on.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

API = "https://api.stripe.com"


class StripeError(RuntimeError):
    """Stripe refused the call or the response was not usable."""


def configured(env: os._Environ[str] | dict[str, str] | None = None) -> bool:
    source = os.environ if env is None else env
    return bool(
        source.get("FINPROJ_STRIPE_SECRET_KEY")
        and source.get("FINPROJ_STRIPE_PRICE_B")
        and source.get("FINPROJ_STRIPE_PRICE_C")
    )


def price_id(plan: str, env: dict[str, str] | None = None) -> str:
    source = os.environ if env is None else env
    key = {"B": "FINPROJ_STRIPE_PRICE_B", "C": "FINPROJ_STRIPE_PRICE_C"}.get(plan, "")
    return source.get(key, "") if key else ""


def subscription_status_is_active(status: str) -> bool:
    return status in {"active", "trialing"}


def plan_from_checkout(payload: dict[str, Any]) -> tuple[str, str, str] | None:
    """Plan, customer id, and subscription id when Checkout has been paid."""
    paid = payload.get("status") == "complete" or payload.get("payment_status") == "paid"
    if not paid:
        return None
    plan = str((payload.get("metadata") or {}).get("plan") or "")
    if plan not in {"B", "C"}:
        return None
    subscription = payload.get("subscription") or ""
    customer = payload.get("customer") or ""
    if isinstance(subscription, dict):
        subscription = subscription.get("id") or ""
    if isinstance(customer, dict):
        customer = customer.get("id") or ""
    if not subscription:
        return None
    return plan, str(customer), str(subscription)


def create_checkout_session(
    *,
    account_id: int,
    email: str,
    plan: str,
    success_url: str,
    cancel_url: str,
    secret: str | None = None,
    opener: Callable[..., Any] | None = None,
) -> dict[str, str]:
    secret_key = secret if secret is not None else os.environ.get("FINPROJ_STRIPE_SECRET_KEY", "")
    price = price_id(plan)
    if not secret_key or not price:
        raise StripeError("Billing is not turned on yet.")
    payload = _request(
        "POST",
        "/v1/checkout/sessions",
        {
            "mode": "subscription",
            "customer_email": email,
            "client_reference_id": str(account_id),
            "success_url": success_url,
            "cancel_url": cancel_url,
            "line_items[0][price]": price,
            "line_items[0][quantity]": "1",
            "metadata[plan]": plan,
            "subscription_data[metadata][plan]": plan,
        },
        secret_key,
        opener,
    )
    session_id = str(payload.get("id") or "")
    url = str(payload.get("url") or "")
    if not session_id or not url:
        raise StripeError("Stripe did not return a checkout page.")
    return {"id": session_id, "url": url}


def retrieve_checkout_session(
    session_id: str,
    *,
    secret: str | None = None,
    opener: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    secret_key = secret if secret is not None else os.environ.get("FINPROJ_STRIPE_SECRET_KEY", "")
    if not secret_key:
        raise StripeError("Billing is not turned on yet.")
    return _request("GET", f"/v1/checkout/sessions/{session_id}", None, secret_key, opener)


def subscription_is_active(
    subscription_id: str,
    *,
    secret: str | None = None,
    opener: Callable[..., Any] | None = None,
) -> bool:
    secret_key = secret if secret is not None else os.environ.get("FINPROJ_STRIPE_SECRET_KEY", "")
    if not secret_key or not subscription_id:
        return False
    payload = _request("GET", f"/v1/subscriptions/{subscription_id}", None, secret_key, opener)
    return subscription_status_is_active(str(payload.get("status") or ""))


def create_portal_session(
    *,
    customer_id: str,
    return_url: str,
    secret: str | None = None,
    opener: Callable[..., Any] | None = None,
) -> str:
    secret_key = secret if secret is not None else os.environ.get("FINPROJ_STRIPE_SECRET_KEY", "")
    if not secret_key or not customer_id:
        raise StripeError("Billing is not turned on yet.")
    payload = _request(
        "POST",
        "/v1/billing_portal/sessions",
        {"customer": customer_id, "return_url": return_url},
        secret_key,
        opener,
    )
    url = str(payload.get("url") or "")
    if not url:
        raise StripeError("Stripe did not return a billing page.")
    return url


def cancel_subscription(
    subscription_id: str,
    *,
    secret: str | None = None,
    opener: Callable[..., Any] | None = None,
) -> None:
    secret_key = secret if secret is not None else os.environ.get("FINPROJ_STRIPE_SECRET_KEY", "")
    if not subscription_id or not secret_key:
        return
    _request("DELETE", f"/v1/subscriptions/{subscription_id}", None, secret_key, opener)


def _request(
    method: str,
    path: str,
    data: dict[str, str] | None,
    secret: str,
    opener: Callable[..., Any] | None,
) -> dict[str, Any]:
    url = API + path
    body = None
    if data is not None and method != "GET":
        body = urllib.parse.urlencode(data).encode()
    elif data:
        url = url + "?" + urllib.parse.urlencode(data)
    request = urllib.request.Request(url, data=body, method=method)
    request.add_header("Authorization", "Bearer " + secret)
    if body is not None:
        request.add_header("Content-Type", "application/x-www-form-urlencoded")
    open_url = opener or urllib.request.urlopen
    try:
        with open_url(request, timeout=30) as response:
            status = getattr(response, "status", 200)
            raw = response.read().decode()
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read().decode()
    payload = json.loads(raw) if raw else {}
    if status >= 400:
        message = ""
        if isinstance(payload, dict):
            message = str((payload.get("error") or {}).get("message") or "")
        raise StripeError(message or "Stripe rejected the request.")
    if not isinstance(payload, dict):
        raise StripeError("Stripe returned an unexpected response.")
    return payload
