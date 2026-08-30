"""FastAPI app: emoji search API + the single-page UI.

Run locally:  uvicorn app:api --reload  (or: python app.py)
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import compose as composer
import config
import feedback
import guard
from search import get_index

ROOT = Path(__file__).parent
STATIC = ROOT / "static"


@asynccontextmanager
async def lifespan(app):
    ix = get_index()  # build the inverted index once, not on first request
    # Say out loud what was resolved, so a developer starting this on their own
    # machine can see immediately whether their .env was picked up.
    log = logging.getLogger("uvicorn.error")
    log.info("indexed %d emoji, %d concept aliases", len(ix.records), len(ix.alias_to_concept))
    log.info(config.summary())
    for note in config.diagnose():
        log.warning("config: %s", note)
    yield


api = FastAPI(
    title="LinkedIn Emoji Search", docs_url="/api/docs", redoc_url=None, lifespan=lifespan
)


@api.get("/api/search")
def search(
    q: str = Query("", description="free text, or paste an emoji to find similar ones"),
    limit: int = Query(60, ge=1, le=300),
    related: int = Query(12, ge=0, le=40),
):
    result = get_index().query(q, limit=limit, rec_limit=related)
    # A search that found nothing is a phrase missing from concepts.py.
    if q.strip() and result["count"] == 0:
        feedback.log_zero_results(q)
    return result


@api.get("/api/groups")
def groups():
    ix = get_index()
    return {"groups": ix.groups(), "total": len(ix.records)}


@api.get("/api/browse")
def browse(group: str, limit: int = Query(500, ge=1, le=2000)):
    return {"group": group, "results": get_index().browse(group, limit=limit)}


@api.get("/api/token")
def issue_token(request: Request):
    """Short-lived single-use token required by LLM mode. See guard.py."""
    return guard.issue_token(request)


@api.post("/api/compose")
def compose_post(
    request: Request,
    text: str = Body(..., embed=True, max_length=20000),
    mode: str = Body("rules", embed=True),
    density: str = Body("balanced", embed=True),
    token: str = Body("", embed=True),
):
    """Return the post with emoji inserted. mode: 'rules' (local, free) or 'llm'."""
    if mode not in ("rules", "llm"):
        raise HTTPException(400, "mode must be 'rules' or 'llm'")

    if mode == "llm":
        if not composer.llm_available():
            raise HTTPException(
                503,
                "LLM mode is not configured on this deployment. Set LLM_API_KEY "
                "(plus LLM_BASE_URL and LLM_MODEL for a non-OpenAI provider).",
            )
        # Only paid requests are gated; rules mode stays open.
        try:
            guard.check_llm_request(request, token)
        except guard.Denied as d:
            headers = {"Retry-After": str(d.retry_after)} if d.retry_after else None
            logging.getLogger("uvicorn.error").info(
                "llm denied (%s): %s", guard.client_ip(request), d.reason)
            raise HTTPException(d.code, d.reason, headers=headers) from None

    try:
        result = composer.compose(text, mode=mode, density=density)
        # Derived stats only — the post itself is never logged.
        feedback.log_compose(result, mode=mode, density=density, chars=len(text))
        return result
    except RuntimeError as e:
        # compose._explain_api_error already produced an actionable message.
        if mode == "llm":
            guard.refund()   # the call failed, so it cost nothing
        logging.getLogger("uvicorn.error").warning("compose failed: %s", e)
        raise HTTPException(502, str(e)) from e
    except Exception as e:  # a bad upstream call shouldn't 500 with a stack trace
        if mode == "llm":
            guard.refund()
        logging.getLogger("uvicorn.error").exception("compose failed")
        raise HTTPException(502, f"{type(e).__name__}: {e}") from e


@api.post("/api/feedback")
def submit_feedback(
    request: Request,
    rating: str = Body("", embed=True),
    comment: str = Body("", embed=True, max_length=2000),
    context: str = Body("", embed=True),
):
    """Thumbs up/down plus an optional note. Rate-limited per IP."""
    out = feedback.accept_feedback(guard.client_ip(request), rating, comment, context)
    if not out["ok"]:
        raise HTTPException(429 if "already sent" in out["error"] else 400, out["error"])
    return out


@api.get("/api/health")
def health():
    ix = get_index()
    cfg = config.llm_config()
    d = cfg.describe() if cfg else {}
    return {
        "ok": True,
        "emoji": len(ix.records),
        "concepts": len(ix.alias_to_concept),
        "llm": bool(cfg),
        # describe() deliberately never includes the api key.
        "llm_model": d.get("model"),
        "llm_provider": d.get("provider"),
        "llm_base_url": d.get("base_url"),
        "notes": config.diagnose(),
        "usage": guard.status(),
    }


@api.get("/")
def index():
    return FileResponse(STATIC / "index.html")


if STATIC.exists():
    api.mount("/static", StaticFiles(directory=STATIC), name="static")


@api.exception_handler(404)
def not_found(request, exc):
    return JSONResponse({"error": "not found"}, status_code=404)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(api, host="127.0.0.1", port=8000)
