"""Abuse and cost controls for the paid LLM endpoint.

Rules mode is free and stays open to everyone. Only `mode=llm` passes through here.

Three layers, weakest to strongest guarantee:

  1. Origin check + signed single-use token — raises the bar for casual scripts.
     A determined caller can replay the handshake; this is friction, not proof.
     Nothing sent by a browser can prove it came from a browser.
  2. Per-IP rate limit — bounds what one abuser gets through.
  3. Global budget — bounds the bill no matter who is calling or how. This is the
     only layer that is arithmetic rather than best-effort, so it is the one that
     actually protects you.

Over the limit, LLM mode degrades to rules mode instead of erroring: the app keeps
working, it just stops spending money.

All limits are per-container. Cloud Run and Modal may run several, so the real
ceiling is (limit x max instances) — set max-instances accordingly, and keep a
quota cap on the provider key as the outer backstop.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import threading
import time
from collections import deque
from dataclasses import dataclass, field

# --- limits (all overridable by env) -----------------------------------------
def _int_env(name, default):
    try:
        return max(0, int(os.environ.get(name, "").strip() or default))
    except ValueError:
        return default


def limits():
    return {
        "per_ip_per_min": _int_env("LLM_MAX_PER_IP_MIN", 5),
        "per_ip_per_day": _int_env("LLM_MAX_PER_IP_DAY", 50),
        "global_per_hour": _int_env("LLM_MAX_PER_HOUR", 60),
        "global_per_day": _int_env("LLM_MAX_PER_DAY", 300),
        "token_ttl": _int_env("LLM_TOKEN_TTL", 300),
        "require_origin": os.environ.get("LLM_REQUIRE_ORIGIN", "1").strip() != "0",
    }


# Signing key for issued tokens. A per-process random default is fine: tokens are
# short-lived, and a restart simply invalidates outstanding ones.
SECRET = os.environ.get("GUARD_SECRET") or secrets.token_hex(32)

MAX_TRACKED_IPS = 10_000
MAX_NONCES = 50_000


class Denied(Exception):
    """Rejected. `retry_after` is seconds, when meaningful."""

    def __init__(self, reason, code=429, retry_after=None):
        super().__init__(reason)
        self.reason = reason
        self.code = code
        self.retry_after = retry_after


@dataclass
class _Window:
    """Fixed window counter."""
    span: float
    start: float = 0.0
    count: int = 0

    def hit(self, now, limit):
        if now - self.start >= self.span:
            self.start, self.count = now, 0
        if self.count >= limit:
            return False, self.span - (now - self.start)
        self.count += 1
        return True, 0.0

    def peek(self, now):
        return 0 if now - self.start >= self.span else self.count


@dataclass
class _State:
    lock: threading.Lock = field(default_factory=threading.Lock)
    hour: _Window = field(default_factory=lambda: _Window(3600))
    day: _Window = field(default_factory=lambda: _Window(86400))
    ip_recent: dict = field(default_factory=dict)    # ip -> deque[timestamp]
    ip_day: dict = field(default_factory=dict)       # ip -> _Window
    nonces: dict = field(default_factory=dict)       # nonce -> expiry
    served: int = 0
    denied: int = 0


_S = _State()


def reset_for_tests():
    global _S
    _S = _State()


# --- client identity ----------------------------------------------------------
def client_ip(request) -> str:
    """Cloud Run and Modal both put the caller first in X-Forwarded-For."""
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return getattr(getattr(request, "client", None), "host", "") or "unknown"


def _sig(nonce: str, exp: int, ip: str) -> str:
    msg = f"{nonce}:{exp}:{ip}".encode()
    return hmac.new(SECRET.encode(), msg, hashlib.sha256).hexdigest()[:32]


# --- tokens -------------------------------------------------------------------
def issue_token(request) -> dict:
    """Mint a short-lived, single-use token bound to the caller's IP."""
    cfg = limits()
    now = int(time.time())
    exp = now + cfg["token_ttl"]
    nonce = secrets.token_urlsafe(12)
    ip = client_ip(request)
    with _S.lock:
        if len(_S.nonces) > MAX_NONCES:          # prune expired, then hard-cap
            for k, v in list(_S.nonces.items()):
                if v < now:
                    _S.nonces.pop(k, None)
            while len(_S.nonces) > MAX_NONCES:
                _S.nonces.pop(next(iter(_S.nonces)), None)
        _S.nonces[nonce] = exp
    return {"token": f"{nonce}.{exp}.{_sig(nonce, exp, ip)}", "expires_in": cfg["token_ttl"]}


def _check_token(token: str, ip: str):
    if not token:
        raise Denied("Missing request token. Reload the page and try again.", 403)
    try:
        nonce, exp_s, sig = token.split(".")
        exp = int(exp_s)
    except (ValueError, AttributeError):
        raise Denied("Malformed request token.", 403) from None
    if not hmac.compare_digest(sig, _sig(nonce, exp, ip)):
        # Also fires when the caller's IP differs from the one the token was issued to.
        raise Denied("Invalid request token.", 403)
    now = time.time()
    if exp < now:
        raise Denied("Request token expired. Reload the page.", 403)
    with _S.lock:
        if _S.nonces.pop(nonce, None) is None:
            raise Denied("Request token already used. Reload the page.", 403)


# --- origin -------------------------------------------------------------------
def _check_origin(request):
    """Browsers always send Origin on POST. Its absence means a non-browser client."""
    cfg = limits()
    if not cfg["require_origin"]:
        return
    origin = request.headers.get("origin")
    if not origin:
        raise Denied(
            "LLM mode is only available from the web app. "
            "Set LLM_REQUIRE_ORIGIN=0 to allow direct API calls on your own deployment.",
            403,
        )
    allowed = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
    host = request.headers.get("host", "")
    same_site = host and origin.split("//")[-1] == host
    if allowed:
        if origin not in allowed and not same_site:
            raise Denied(f"Origin {origin} is not allowed.", 403)
    elif not same_site:
        raise Denied(f"Origin {origin} does not match this host.", 403)


# --- the gate -----------------------------------------------------------------
def check_llm_request(request, token: str | None):
    """Raise Denied if this paid request should not proceed."""
    cfg = limits()
    ip = client_ip(request)
    now = time.time()

    _check_origin(request)
    _check_token(token, ip)

    with _S.lock:
        # per-IP: sliding minute
        recent = _S.ip_recent.get(ip)
        if recent is None:
            if len(_S.ip_recent) >= MAX_TRACKED_IPS:
                _S.ip_recent.pop(next(iter(_S.ip_recent)), None)
                _S.ip_day.pop(next(iter(_S.ip_day)), None)
            recent = _S.ip_recent[ip] = deque()
        while recent and now - recent[0] > 60:
            recent.popleft()
        if len(recent) >= cfg["per_ip_per_min"]:
            _S.denied += 1
            raise Denied("You are going a bit fast — try again in a moment.",
                         429, retry_after=int(60 - (now - recent[0])) + 1)

        # per-IP: day
        day = _S.ip_day.get(ip)
        if day is None:
            day = _S.ip_day[ip] = _Window(86400)
        ok, wait = day.hit(now, cfg["per_ip_per_day"])
        if not ok:
            _S.denied += 1
            raise Denied("Daily limit for LLM placement reached for your network. "
                         "Rule-based mode still works.", 429, retry_after=int(wait))

        # global budget — the layer that actually caps the bill
        ok, wait = _S.hour.hit(now, cfg["global_per_hour"])
        if not ok:
            _S.denied += 1
            raise Denied("The app has hit its hourly LLM budget. "
                         "Rule-based mode still works.", 429, retry_after=int(wait))
        ok, wait = _S.day.hit(now, cfg["global_per_day"])
        if not ok:
            _S.hour.count -= 1                      # don't consume the hour slot too
            _S.denied += 1
            raise Denied("The app has hit its daily LLM budget. "
                         "Rule-based mode still works.", 429, retry_after=int(wait))

        recent.append(now)
        _S.served += 1


def refund():
    """Give back a budget slot when the upstream call failed and cost nothing."""
    with _S.lock:
        _S.hour.count = max(0, _S.hour.count - 1)
        _S.day.count = max(0, _S.day.count - 1)
        _S.served = max(0, _S.served - 1)


def status() -> dict:
    """Non-sensitive usage counters, safe to expose for monitoring."""
    cfg = limits()
    now = time.time()
    with _S.lock:
        return {
            "llm_calls_this_hour": _S.hour.peek(now),
            "llm_calls_today": _S.day.peek(now),
            "hourly_limit": cfg["global_per_hour"],
            "daily_limit": cfg["global_per_day"],
            "per_ip_per_min": cfg["per_ip_per_min"],
            "per_ip_per_day": cfg["per_ip_per_day"],
            "served": _S.served,
            "denied": _S.denied,
            "tracked_ips": len(_S.ip_recent),
        }
