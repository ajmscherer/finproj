# finproj - sign-in, plans, and terms for the public site
# Copyright (C) 2025-2026 Alex Scherer

"""Screens and the run gate for the hosted site.

A local computer never calls the database. The public site does, and only
when the process holds the host secret.
"""

from __future__ import annotations

import os
import secrets
from urllib.parse import urlparse

import streamlit as st

import accounts
import stripe_billing
from browser_token import sync_browser_token

_SUBJECT_KEY = "_hosted_subject"
_USAGE_KEY = "_hosted_usage"
_TOKEN_KEY = "_browser_token"
_NOTICE_KEY = "_billing_notice"
_DENIED_KEY = "usage_denied"


def current_mode() -> str:
    """``local``, ``hosted``, or ``refused`` for this browser request."""
    return accounts.deployment_mode(_request_host(), os.environ.get("FINPROJ_HOST_SECRET", ""))


def consume_for_run() -> bool:
    """Count a hosted run. Local runs are always allowed and are not recorded."""
    if current_mode() != "hosted":
        return True
    subject = st.session_state.get(_SUBJECT_KEY)
    if not subject:
        st.session_state[_DENIED_KEY] = "Sign in is still loading. Try the run again."
        return False
    usage = accounts.Ledger(accounts.default_database_path()).consume(
        role=subject["role"],
        subject_id=subject["subject_id"],
        client_ip=subject.get("client_ip", ""),
    )
    st.session_state[_USAGE_KEY] = _usage_dict(usage)
    if not usage.allowed:
        st.session_state[_DENIED_KEY] = accounts.denial_message(usage)
        return False
    st.session_state.pop(_DENIED_KEY, None)
    return True


def hosted_block_message() -> str:
    """Why Run is unavailable, or an empty string when it is available."""
    if current_mode() != "hosted":
        return ""
    usage = _usage_from_state()
    if usage is not None and not usage.allowed:
        return accounts.denial_message(usage)
    return st.session_state.get(_DENIED_KEY, "")


def prepare_hosted_session() -> None:
    """Load the guest or account and refresh the quota line."""
    if current_mode() != "hosted":
        return
    token = _current_token()
    sync_browser_token(token)
    ip = _client_ip()
    ledger = accounts.Ledger(accounts.default_database_path())
    account = ledger.account_for_session(token)
    if account is not None:
        account = _refresh_subscription(ledger, account)
        _apply_checkout(ledger, account)
        account = ledger.account_by_id(int(account["id"])) or account
        role = str(account["plan"])
        subject_id = str(account["id"])
        email = str(account["email"])
    else:
        ledger.remember_guest(token)
        role = "guest"
        subject_id = token
        email = ""
    usage = ledger.usage(role=role, subject_id=subject_id, client_ip=ip)
    st.session_state[_SUBJECT_KEY] = {
        "role": role,
        "subject_id": subject_id,
        "client_ip": ip,
        "email": email,
    }
    st.session_state[_USAGE_KEY] = _usage_dict(usage)


def header_links() -> str:
    """Markdown for the terms link, plus sign-in on the hosted site."""
    terms = "[Terms and conditions](?page=terms)"
    if current_mode() != "hosted":
        return terms
    usage = _usage_from_state()
    label = accounts.remaining_label(usage) if usage is not None else "Guest"
    subject = st.session_state.get(_SUBJECT_KEY) or {}
    account_word = "Account" if subject.get("email") else "Sign in"
    return f"{label} · [{account_word}](?page=account) · {terms}"


def render_terms() -> None:
    st.header("Terms and conditions")
    st.markdown(
        "Use of this website is for personal use only. "
        "A copy on your own computer is an unlimited guest. "
        "Login and the plans are not part of that copy."
    )
    st.markdown(
        "Only A Scherer may deploy finproj on a remote server or charge for its use. "
        f"Anyone else who wants to do that [contacts A Scherer]({accounts.COMMERCIAL_CONTACT_URL})."
    )
    st.markdown(
        "On the website, a guest has 3 runs a day. "
        "Plan A is free and has 5 runs a day. "
        "Plan B is \\$5 per month and has 100 runs a month. "
        "Plan C is \\$10 per month and has no cap. "
        "A run is one click of Run simulation or Refresh simulation. "
        "The day and the month reset at 00:00 UTC."
    )
    if st.button("Back", key="terms_back"):
        _clear_page()


def render_refused() -> None:
    st.header("finproj")
    st.markdown(
        "This copy runs on your own computer. "
        "Serving it to other people is reserved to A Scherer."
    )
    st.markdown(f"[Contact A Scherer]({accounts.COMMERCIAL_CONTACT_URL})")
    st.markdown("[Terms and conditions](?page=terms)")


def render_account_page() -> None:
    st.header("Account")
    notice = st.session_state.pop(_NOTICE_KEY, "")
    if notice:
        st.info(notice)
    subject = st.session_state.get(_SUBJECT_KEY) or {}
    if subject.get("email"):
        _render_signed_in(subject)
    else:
        _render_signed_out()
    st.markdown("[Terms and conditions](?page=terms)")
    if st.button("Back", key="account_back"):
        _clear_page()


def _render_signed_out() -> None:
    st.caption(
        "To reset a password, contact A Scherer: "
        f"[open a GitHub issue]({accounts.COMMERCIAL_CONTACT_URL})."
    )
    choice = st.radio(
        "Account action",
        ["Sign in", "Create account"],
        horizontal=True,
        label_visibility="collapsed",
        key="account_action",
    )
    if choice == "Sign in":
        _render_sign_in()
    else:
        _render_create_account()


def _render_sign_in() -> None:
    with st.form("sign_in_form"):
        email = st.text_input("Email", key="sign_in_email")
        password = st.text_input("Password", type="password", key="sign_in_password")
        submitted = st.form_submit_button("Sign in")
    if not submitted:
        return
    ledger = accounts.Ledger(accounts.default_database_path())
    account_id = ledger.authenticate(email, password)
    if account_id is None:
        st.error("That email and password do not match an account.")
        return
    _start_session(ledger, account_id)
    st.rerun()


def _render_create_account() -> None:
    with st.form("create_account_form"):
        email = st.text_input("Email", key="create_email")
        password = st.text_input("Password", type="password", key="create_password")
        plan = st.radio(
            "Plan",
            ["A", "B", "C"],
            format_func=_plan_label,
            key="create_plan",
        )
        submitted = st.form_submit_button("Create account")
    if not submitted:
        return
    ledger = accounts.Ledger(accounts.default_database_path())
    try:
        account_id = ledger.create_account(email, password)
    except ValueError as exc:
        st.error(str(exc))
        return
    _start_session(ledger, account_id)
    if plan in {"B", "C"}:
        st.session_state["_pending_checkout_plan"] = plan
    st.rerun()


def _render_signed_in(subject: dict) -> None:
    st.write(subject.get("email", ""))
    usage = _usage_from_state()
    if usage is not None:
        st.caption(accounts.remaining_label(usage))
    pending = st.session_state.get("_pending_checkout_plan")
    if pending in {"B", "C"}:
        if stripe_billing.configured():
            _offer_checkout(
                accounts.Ledger(accounts.default_database_path()),
                int(subject["subject_id"]),
                str(pending),
            )
        else:
            st.info("Billing is not turned on yet. The account is on Plan A.")
            st.session_state.pop("_pending_checkout_plan", None)
    account = accounts.Ledger(accounts.default_database_path()).account_by_id(int(subject["subject_id"]))
    if account is None:
        return
    plan = st.radio(
        "Plan",
        ["A", "B", "C"],
        index=["A", "B", "C"].index(str(account["plan"])),
        format_func=_plan_label,
        key="chosen_plan",
    )
    if st.button("Use this plan", key="use_plan"):
        _change_plan(account, plan)
    if account.get("stripe_customer_id") and stripe_billing.configured():
        if st.button("Manage billing", key="manage_billing"):
            _open_portal(str(account["stripe_customer_id"]))
    if st.button("Sign out", key="sign_out"):
        _sign_out(str(st.session_state.get(_TOKEN_KEY, "")))


def _change_plan(account: dict, plan: str) -> None:
    ledger = accounts.Ledger(accounts.default_database_path())
    if plan == account["plan"]:
        st.info(f"This account is already on Plan {plan}.")
        return
    if plan == "A":
        subscription = account.get("stripe_subscription_id") or ""
        if subscription and stripe_billing.configured():
            try:
                stripe_billing.cancel_subscription(subscription)
            except stripe_billing.StripeError as exc:
                st.error(str(exc))
                return
        ledger.set_plan(int(account["id"]), "A", stripe_subscription_id="")
        st.success("This account is on Plan A.")
        st.rerun()
        return
    if not stripe_billing.configured():
        st.info("Billing is not turned on yet.")
        return
    _offer_checkout(ledger, int(account["id"]), plan)


def _offer_checkout(ledger: accounts.Ledger, account_id: int, plan: str) -> None:
    account = ledger.account_by_id(account_id)
    if account is None:
        return
    base = _public_base()
    if not base:
        st.error("The site address is not available, so checkout cannot start.")
        return
    try:
        session = stripe_billing.create_checkout_session(
            account_id=account_id,
            email=str(account["email"]),
            plan=plan,
            success_url=base + "/?page=account&checkout=success&session_id={CHECKOUT_SESSION_ID}",
            cancel_url=base + "/?page=account&checkout=cancel",
        )
    except stripe_billing.StripeError as exc:
        st.error(str(exc))
        return
    st.link_button("Continue to payment", session["url"])


def _open_portal(customer_id: str) -> None:
    base = _public_base() or ""
    try:
        url = stripe_billing.create_portal_session(
            customer_id=customer_id,
            return_url=(base + "/?page=account") if base else "https://143.244.154.68/?page=account",
        )
    except stripe_billing.StripeError as exc:
        st.error(str(exc))
        return
    st.link_button("Open billing", url)


def _start_session(ledger: accounts.Ledger, account_id: int) -> None:
    previous = st.session_state.get(_TOKEN_KEY, "")
    if previous:
        ledger.close_session(previous)
    token = ledger.open_session(account_id)
    st.session_state[_TOKEN_KEY] = token


def _sign_out(token: str) -> None:
    ledger = accounts.Ledger(accounts.default_database_path())
    ledger.close_session(token)
    st.session_state[_TOKEN_KEY] = secrets.token_urlsafe(32)
    st.rerun()


def _apply_checkout(ledger: accounts.Ledger, account: dict) -> None:
    if st.query_params.get("checkout") != "success":
        return
    session_id = str(st.query_params.get("session_id") or "")
    if not session_id:
        return
    try:
        payload = stripe_billing.retrieve_checkout_session(session_id)
    except stripe_billing.StripeError as exc:
        st.session_state[_NOTICE_KEY] = str(exc)
        return
    parsed = stripe_billing.plan_from_checkout(payload)
    if parsed is None:
        return
    plan, customer, subscription = parsed
    reference = str(payload.get("client_reference_id") or "")
    if reference and reference != str(account["id"]):
        return
    ledger.set_plan(int(account["id"]), plan, customer, subscription)
    st.session_state[_NOTICE_KEY] = f"Plan {plan} is active."
    for key in ("checkout", "session_id"):
        if key in st.query_params:
            del st.query_params[key]


def _refresh_subscription(ledger: accounts.Ledger, account: dict) -> dict:
    subscription = account.get("stripe_subscription_id") or ""
    if not subscription or not stripe_billing.configured():
        return account
    if account.get("plan") not in {"B", "C"}:
        return account
    try:
        active = stripe_billing.subscription_is_active(subscription)
    except stripe_billing.StripeError:
        return account
    if active:
        return account
    ledger.set_plan(int(account["id"]), "A", stripe_subscription_id="")
    refreshed = ledger.account_by_id(int(account["id"]))
    return refreshed or account


def _current_token() -> str:
    token = str(st.session_state.get(_TOKEN_KEY) or "")
    if token:
        return token
    try:
        token = str(st.context.cookies.get("finproj_id", "") or "")
    except Exception:
        token = ""
    if not token:
        token = secrets.token_urlsafe(32)
    st.session_state[_TOKEN_KEY] = token
    return token


def _client_ip() -> str:
    forwarded = ""
    remote = ""
    try:
        headers = st.context.headers
        if headers:
            forwarded = str(headers.get("X-Forwarded-For") or headers.get("x-forwarded-for") or "")
    except Exception:
        forwarded = ""
    try:
        remote = str(st.context.ip_address or "")
    except Exception:
        remote = ""
    return accounts.client_ip_from(forwarded, remote)


def _request_host() -> str:
    try:
        url = getattr(st.context, "url", "") or ""
        host = urlparse(url).hostname or ""
        if host:
            return host
    except Exception:
        pass
    try:
        headers = getattr(st.context, "headers", None)
        if headers:
            return str(headers.get("Host") or headers.get("host") or "")
    except Exception:
        pass
    return ""


def _public_base() -> str:
    try:
        url = getattr(st.context, "url", "") or ""
    except Exception:
        return ""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def _clear_page() -> None:
    if "page" in st.query_params:
        del st.query_params["page"]
    st.rerun()


def _plan_label(plan: str) -> str:
    labels = {
        "A": "Plan A — free, 5 runs a day",
        "B": "Plan B — \\$5 per month, 100 runs a month",
        "C": "Plan C — \\$10 per month, unlimited",
    }
    return labels.get(plan, plan)


def _usage_dict(usage: accounts.Usage) -> dict:
    return {
        "allowed": usage.allowed,
        "role": usage.role,
        "used": usage.used,
        "limit": usage.limit,
        "period": usage.period,
    }


def _usage_from_state() -> accounts.Usage | None:
    raw = st.session_state.get(_USAGE_KEY)
    if not isinstance(raw, dict) or "role" not in raw:
        return None
    limit = raw.get("limit")
    return accounts.Usage(
        allowed=bool(raw.get("allowed")),
        role=str(raw.get("role")),
        used=int(raw.get("used") or 0),
        limit=None if limit is None else int(limit),
        period=str(raw.get("period") or "day"),
    )
