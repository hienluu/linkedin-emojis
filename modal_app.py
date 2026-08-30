"""Modal deployment.

    modal serve modal_app.py     # live-reloading dev URL
    modal deploy modal_app.py    # persistent URL

The index is built once per container at import time (~1900 emoji, well under a
second) and reused across requests, so scaledown_window keeps warm containers
around rather than rebuilding on every hit.
"""

import modal

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("fastapi[standard]==0.115.*", "openai>=1.60")
    .add_local_python_source(
        "app", "search", "concepts", "compose", "config", "guard", "feedback")
    # data/raw holds the ~1.5MB of Unicode source files; only emojis.json is needed at runtime.
    .add_local_dir("data", remote_path="/root/data", ignore=["raw/**", "raw"])
    .add_local_dir("static", remote_path="/root/static")
)

app = modal.App("linkedin-emoji-search", image=image)

# Credentials for the optional LLM placement mode. Any OpenAI-compatible provider
# works — set LLM_API_KEY plus LLM_BASE_URL and LLM_MODEL, or just a recognised
# provider key (OPENAI_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, ...) and the defaults
# in compose.py fill in the rest.
#   modal secret create llm-api-key LLM_API_KEY=... LLM_BASE_URL=... LLM_MODEL=...
# The existing gemini-api-key secret keeps working unchanged.
# Without any secret the app still runs; the LLM button is disabled and
# /api/compose?mode=llm returns 503.
secrets = [modal.Secret.from_name("gemini-api-key")]


@app.function(
    min_containers=0,
    scaledown_window=300,
    # guard.py's limits are per container, so this also bounds the LLM budget:
    # worst case is (per-container limit x containers).
    max_containers=2,
    secrets=secrets,
    timeout=120,
)
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def web():
    from app import api

    return api
