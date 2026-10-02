# finproj - accounts, guest quotas, and the public-site gate
# Copyright (C) 2025-2026 Alex Scherer

"""Who may run a simulation, and how many runs they have left.

This module does not import Streamlit. A copy running on a local computer
never has to open the database. Login and the plan caps apply only when the
browser reached the app through a public address and the process holds the
host secret.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import os
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

# SHA-256 of the host secret. The secret itself is not in the repository.
HOST_SECRET_SHA256 = "fe305424563374511a84f89f189c874bd4a260e2fce06cb8a75b81b2f3023174"

GUEST_DAILY = 3
PLAN_A_DAILY = 5
PLAN_B_MONTHLY = 100

COMMERCIAL_CONTACT_URL = "https://github.com/ajmscherer/finproj/issues/new"

PLANS = ("A", "B", "C")


@dataclass(frozen=True)
class Usage:
    """A peek or a consume result for one subject."""

    allowed: bool
    role: str
    used: int
    limit: int | None
    period: str


def is_local_host(host: str) -> bool:
    """True for loopback, private LAN, and .local names."""
    host = (host or "").strip().lower().rstrip(".")
    if host.startswith("[") and "]" in host:
        host = host[1 : host.index("]")]
    elif host.count(":") == 1 and not _looks_like_ipv6(host):
        host = host.split(":", 1)[0]
    if not host:
        return True
    if host in {"localhost", "127.0.0.1", "::1", "0.0.0.0", "0:0:0:0:0:0:0:1"}:
        return True
    if host.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return bool(ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_unspecified)


def _looks_like_ipv6(host: str) -> bool:
    return host.count(":") > 1


def host_secret_matches(secret: str) -> bool:
    """True when secret is the host secret stored outside the repository."""
    if not secret:
        return False
    digest = hashlib.sha256(secret.encode()).hexdigest()
    return hmac.compare_digest(digest, HOST_SECRET_SHA256)


def deployment_mode(host: str, host_secret: str) -> str:
    """How this request should behave.

    ``local`` is an unlimited guest with no sign-in. ``hosted`` is the public
    site. ``refused`` is a public address that does not hold the host secret.
    """
    if is_local_host(host):
        return "local"
    if host_secret_matches(host_secret):
        return "hosted"
    return "refused"


def default_database_path() -> Path:
    root = os.environ.get("FINPROJ_DATA_DIR", "").strip()
    if not root:
        root = "/home/finproj/finproj-data"
    return Path(root) / "accounts.sqlite"


def client_ip_from(forwarded: str, remote: str) -> str:
    """Client address for the guest cap.

    A proxy appends the address it actually saw. The last hop is that address.
    """
    parts = [part.strip() for part in (forwarded or "").split(",") if part.strip()]
    if parts:
        return parts[-1]
    return (remote or "").strip()


def remaining_label(usage: Usage) -> str:
    if usage.role == "guest":
        left = max(0, GUEST_DAILY - usage.used)
        return f"Guest · {left} of {GUEST_DAILY} runs left today"
    if usage.role == "A":
        left = max(0, PLAN_A_DAILY - usage.used)
        return f"Plan A · {left} of {PLAN_A_DAILY} runs left today"
    if usage.role == "B":
        left = max(0, PLAN_B_MONTHLY - usage.used)
        return f"Plan B · {left} of {PLAN_B_MONTHLY} runs left this month"
    return "Plan C · unlimited"


def denial_message(usage: Usage) -> str:
    if usage.role == "guest":
        return (
            "You have used today's 3 guest runs. "
            "Create a free account for 5 runs a day, or look at Plan B and Plan C."
        )
    if usage.role == "A":
        return (
            "You have used today's 5 runs. "
            "Plan B is \\$5 per month for 100 runs, and Plan C is \\$10 per month with no cap."
        )
    if usage.role == "B":
        return "You have used this month's 100 runs. Plan C is \\$10 per month with no cap."
    return ""


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    n, r, p = 2**14, 8, 1
    derived = hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p, dklen=32)
    return f"scrypt${n}${r}${p}${salt.hex()}${derived.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_hex, derived_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        salt = bytes.fromhex(salt_hex)
        derived = hashlib.scrypt(
            password.encode(),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=32,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(derived.hex(), derived_hex)


def _normalize_email(email: str) -> str:
    text = (email or "").strip().lower()
    if "@" not in text or text.startswith("@") or text.endswith("@"):
        raise ValueError("Enter an email address.")
    domain = text.split("@", 1)[1]
    if "." not in domain or domain.startswith(".") or domain.endswith("."):
        raise ValueError("Enter an email address.")
    return text


def _check_password(password: str) -> None:
    if len(password or "") < 8:
        raise ValueError("Use at least 8 characters for the password.")


def _as_utc(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _period_bounds(now: datetime, period: str) -> tuple[str, str]:
    moment = _as_utc(now)
    if period == "day":
        start = moment.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    else:
        start = moment.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
    return start.isoformat(), end.isoformat()


class Ledger:
    """SQLite store for accounts, sessions, guests, and counted runs."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        self._migrate(conn)
        return conn

    def _migrate(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                plan TEXT NOT NULL DEFAULT 'A',
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                account_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES accounts(id)
            );
            CREATE TABLE IF NOT EXISTS guests (
                token TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY,
                subject_type TEXT NOT NULL,
                subject_id TEXT NOT NULL,
                client_ip TEXT,
                started_at TEXT NOT NULL
            );
            """
        )

    def create_account(self, email: str, password: str, now: datetime | None = None) -> int:
        email = _normalize_email(email)
        _check_password(password)
        moment = _as_utc(now).isoformat()
        conn = self._connect()
        try:
            cursor = conn.execute(
                """
                INSERT INTO accounts (email, password_hash, plan, created_at)
                VALUES (?, ?, 'A', ?)
                """,
                (email, hash_password(password), moment),
            )
            conn.commit()
            return int(cursor.lastrowid)
        except sqlite3.IntegrityError as exc:
            raise ValueError("An account with that email already exists.") from exc
        finally:
            conn.close()

    def authenticate(self, email: str, password: str) -> int | None:
        try:
            email = _normalize_email(email)
        except ValueError:
            return None
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT id, password_hash FROM accounts WHERE email = ?",
                (email,),
            ).fetchone()
        finally:
            conn.close()
        if row is None or not verify_password(password, row["password_hash"]):
            return None
        return int(row["id"])

    def open_session(self, account_id: int, now: datetime | None = None) -> str:
        token = secrets.token_urlsafe(32)
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO sessions (token, account_id, created_at) VALUES (?, ?, ?)",
                (token, account_id, _as_utc(now).isoformat()),
            )
            conn.commit()
        finally:
            conn.close()
        return token

    def close_session(self, token: str) -> None:
        if not token:
            return
        conn = self._connect()
        try:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
        finally:
            conn.close()

    def account_for_session(self, token: str) -> dict | None:
        if not token:
            return None
        conn = self._connect()
        try:
            row = conn.execute(
                """
                SELECT accounts.*
                FROM sessions
                JOIN accounts ON accounts.id = sessions.account_id
                WHERE sessions.token = ?
                """,
                (token,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return dict(row)

    def account_by_id(self, account_id: int) -> dict | None:
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        finally:
            conn.close()
        return dict(row) if row is not None else None

    def set_plan(
        self,
        account_id: int,
        plan: str,
        stripe_customer_id: str | None = None,
        stripe_subscription_id: str | None = None,
    ) -> None:
        if plan not in PLANS:
            raise ValueError("Choose Plan A, Plan B, or Plan C.")
        conn = self._connect()
        try:
            current = conn.execute(
                "SELECT stripe_customer_id, stripe_subscription_id FROM accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
            if current is None:
                raise ValueError("That account does not exist.")
            customer = stripe_customer_id if stripe_customer_id is not None else current["stripe_customer_id"]
            subscription = (
                stripe_subscription_id
                if stripe_subscription_id is not None
                else current["stripe_subscription_id"]
            )
            if plan == "A":
                subscription = None
            conn.execute(
                """
                UPDATE accounts
                SET plan = ?, stripe_customer_id = ?, stripe_subscription_id = ?
                WHERE id = ?
                """,
                (plan, customer, subscription, account_id),
            )
            conn.commit()
        finally:
            conn.close()

    def remember_guest(self, token: str, now: datetime | None = None) -> None:
        if not token:
            raise ValueError("A guest needs a token.")
        conn = self._connect()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO guests (token, created_at) VALUES (?, ?)",
                (token, _as_utc(now).isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    def usage(
        self,
        *,
        role: str,
        subject_id: str,
        client_ip: str = "",
        now: datetime | None = None,
    ) -> Usage:
        conn = self._connect()
        try:
            return self._measure(conn, role, subject_id, client_ip, _as_utc(now))
        finally:
            conn.close()

    def consume(
        self,
        *,
        role: str,
        subject_id: str,
        client_ip: str = "",
        now: datetime | None = None,
    ) -> Usage:
        """Count one run when the cap allows it.

        The check and the insert share one immediate transaction, so two
        overlapping requests cannot both pass the last remaining run.
        """
        moment = _as_utc(now)
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            current = self._measure(conn, role, subject_id, client_ip, moment)
            if not current.allowed:
                conn.execute("COMMIT")
                return current
            subject_type = "guest" if role == "guest" else "account"
            conn.execute(
                """
                INSERT INTO runs (subject_type, subject_id, client_ip, started_at)
                VALUES (?, ?, ?, ?)
                """,
                (subject_type, subject_id, client_ip or None, moment.isoformat()),
            )
            conn.execute("COMMIT")
            # The run that reaches the cap was accepted. The next one is refused.
            if current.limit is None:
                return current
            return Usage(
                True,
                current.role,
                current.used + 1,
                current.limit,
                current.period,
            )
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def _measure(
        self,
        conn: sqlite3.Connection,
        role: str,
        subject_id: str,
        client_ip: str,
        now: datetime,
    ) -> Usage:
        if role == "C":
            return Usage(True, "C", 0, None, "month")
        if role == "guest":
            start, end = _period_bounds(now, "day")
            token_used = self._count(conn, "guest", subject_id, start, end)
            used = token_used
            if client_ip:
                ip_used = self._count_ip(conn, client_ip, start, end)
                used = max(token_used, ip_used)
            return Usage(used < GUEST_DAILY, "guest", used, GUEST_DAILY, "day")
        if role == "A":
            start, end = _period_bounds(now, "day")
            used = self._count(conn, "account", subject_id, start, end)
            return Usage(used < PLAN_A_DAILY, "A", used, PLAN_A_DAILY, "day")
        if role == "B":
            start, end = _period_bounds(now, "month")
            used = self._count(conn, "account", subject_id, start, end)
            return Usage(used < PLAN_B_MONTHLY, "B", used, PLAN_B_MONTHLY, "month")
        raise ValueError(f"Unknown role {role}")

    def _count(
        self,
        conn: sqlite3.Connection,
        subject_type: str,
        subject_id: str,
        start: str,
        end: str,
    ) -> int:
        row = conn.execute(
            """
            SELECT COUNT(*) AS n FROM runs
            WHERE subject_type = ? AND subject_id = ? AND started_at >= ? AND started_at < ?
            """,
            (subject_type, subject_id, start, end),
        ).fetchone()
        return int(row["n"])

    def _count_ip(self, conn: sqlite3.Connection, client_ip: str, start: str, end: str) -> int:
        row = conn.execute(
            """
            SELECT COUNT(*) AS n FROM runs
            WHERE subject_type = 'guest' AND client_ip = ? AND started_at >= ? AND started_at < ?
            """,
            (client_ip, start, end),
        ).fetchone()
        return int(row["n"])
