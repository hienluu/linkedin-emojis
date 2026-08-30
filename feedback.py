"""Usage signals and user feedback, emitted as structured log lines.

Written as single-line JSON on stdout, which Cloud Run parses into queryable
`jsonPayload` fields (Modal keeps them as plain log lines). No database, nothing
new to run, and it works identically on both deployments.

    gcloud logging read \
      'jsonPayload.component="feedback" AND jsonPayload.event="zero_results"' \
      --limit 50 --format='value(jsonPayload.query)'

PRIVACY — the rule that matters here:

  Post content is NEVER logged. People paste real drafts, including things like
  a layoff announcement. Only derived facts are recorded: length, mode, how many
  emoji were placed, whether the sensitivity guard fired.

  Search queries are logged only when they returned nothing, because that case is
  the actionable one — every zero-result query is a phrase missing from
  concepts.py. They are truncated and stripped of newlines.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from collections import deque

MAX_QUERY = 120
MAX_COMMENT = 1000
FEEDBACK_PER_IP_PER_HOUR = 5

_lock = threading.Lock()
_ip_feedback: dict[str, deque] = {}

ENABLED = os.environ.get("FEEDBACK_LOGGING", "1").strip() != "0"


def emit(event: str, **fields):
    """One structured line. Never raises — telemetry must not break a request."""
    if not ENABLED:
        return
    try:
        record = {
            "severity": "INFO",
            "component": "feedback",
            "event": event,
            "ts": int(time.time()),
            **fields,
        }
        sys.stdout.write(json.dumps(record, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    except Exception:
        pass


def _clean(text: str | None, limit: int) -> str:
    if not text:
        return ""
    return " ".join(str(text).split())[:limit]


# --- implicit signals ---------------------------------------------------------
def log_zero_results(query: str):
    """A search that found nothing — the most actionable signal this app produces."""
    q = _clean(query, MAX_QUERY)
    if q:
        emit("zero_results", query=q)


def log_compose(result: dict, mode: str, density: str, chars: int):
    """Derived stats only. `result["text"]` is deliberately not touched."""
    emit(
        "compose",
        mode=mode,
        density=density,
        input_chars=chars,
        emoji_placed=result.get("count", 0),
        # did the sensitivity guard fire, or did the LLM alter the wording?
        sensitive=bool(result.get("note")),
        verified=result.get("verified"),
        provider=result.get("provider"),
    )


# --- explicit feedback --------------------------------------------------------
def accept_feedback(ip: str, rating: str, comment: str, context: str) -> dict:
    """Validate, rate-limit and record one piece of user feedback."""
    if rating not in ("up", "down", ""):
        return {"ok": False, "error": "rating must be 'up' or 'down'"}
    comment = _clean(comment, MAX_COMMENT)
    if not rating and not comment:
        return {"ok": False, "error": "nothing to submit"}

    now = time.time()
    with _lock:
        hits = _ip_feedback.setdefault(ip, deque())
        while hits and now - hits[0] > 3600:
            hits.popleft()
        if len(hits) >= FEEDBACK_PER_IP_PER_HOUR:
            return {"ok": False, "error": "Thanks — you've already sent several. "
                                          "Try again later."}
        hits.append(now)

    emit("feedback", rating=rating or None, comment=comment or None,
         context=_clean(context, 40) or None)
    return {"ok": True}


def reset_for_tests():
    with _lock:
        _ip_feedback.clear()
