"""Environment-driven configuration for the optional LLM placement mode.

Everything the app needs to talk to an LLM comes from environment variables, so a
developer can run this on their own laptop against whatever provider they have a
key for — or against a local model with no key at all.

Check what the app resolved without starting the server:

    uv run config.py

Three variables configure everything:

    LLM_API_KEY    the key (omit only for a keyless local server)
    LLM_BASE_URL   the endpoint (omit for OpenAI itself)
    LLM_MODEL      the model

Real environment variables always beat values in a local .env file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).parent
ENV_FILE = Path(os.environ.get("ENV_FILE", ROOT / ".env"))


# Endpoints for common providers. These are documentation, not configuration —
# nothing here is read automatically; you paste one into LLM_BASE_URL.
KNOWN_ENDPOINTS = {
    "openai": ("https://api.openai.com/v1", "gpt-4o-mini"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", "gemini-3.5-flash-lite"),
    "groq": ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
    "together": ("https://api.together.xyz/v1", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
    "openrouter": ("https://openrouter.ai/api/v1", "google/gemini-2.5-flash-lite"),
    "deepseek": ("https://api.deepseek.com", "deepseek-chat"),
    "fireworks": ("https://api.fireworks.ai/inference/v1",
                  "accounts/fireworks/models/llama-v3p3-70b-instruct"),
    "ollama": ("http://localhost:11434/v1", "llama3.2"),
}


def _provider_label(base_url: str | None) -> str:
    """A display label inferred from the host. Cosmetic only — never affects behaviour."""
    if not base_url:
        return "openai"
    host = base_url.split("//", 1)[-1].split("/", 1)[0].lower()
    for name, (url, _) in KNOWN_ENDPOINTS.items():
        if url.split("//", 1)[-1].split("/", 1)[0].lower() == host:
            return name
    return host or "custom"


@dataclass(frozen=True)
class LLMConfig:
    provider: str          # inferred from base_url, for display only
    api_key: str
    base_url: str | None
    model: str
    timeout: float = 60.0
    max_retries: int = 2
    temperature: float = 0.4

    @property
    def masked_key(self) -> str:
        k = self.api_key
        if k == "not-needed":
            return "(none — keyless endpoint)"
        return f"{k[:6]}…{k[-4:]}" if len(k) > 12 else "…"

    def describe(self) -> dict:
        """Safe to expose over HTTP: never includes the key."""
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
        }


# --------------------------------------------------------------------- .env
def load_dotenv(path: Path | None = None) -> bool:
    """Load a local .env for development. Returns True if a file was read.

    `override=False` is the important part: a real environment variable always
    wins, so a stray .env can never shadow a deployed secret.
    """
    path = Path(path or ENV_FILE)
    if not path.exists():
        return False
    try:
        from dotenv import load_dotenv as _load
        _load(path, override=False)
    except ImportError:  # works without the optional dependency
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))
    return True


def _float(name, default):
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int(name, default):
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# ------------------------------------------------------------------- config
def llm_config() -> LLMConfig | None:
    """Resolve the LLM settings from the environment, or None if unconfigured.

    Exactly three variables decide everything, with no precedence rules and no
    per-provider special cases:

        LLM_API_KEY    the key (omit only for a keyless local server)
        LLM_BASE_URL   the endpoint (omit for OpenAI itself)
        LLM_MODEL      the model

    LLM_MODEL is required whenever anything else is set — guessing a default per
    provider is what made the old version confusing.
    """
    key = (os.environ.get("LLM_API_KEY") or "").strip()
    base_url = (os.environ.get("LLM_BASE_URL") or "").strip() or None
    model = (os.environ.get("LLM_MODEL") or "").strip() or None

    if not key and not base_url:
        return None          # nothing configured at all
    if not model:
        return None          # incomplete; diagnose() explains what is missing

    return LLMConfig(
        provider=_provider_label(base_url),
        # A local server (Ollama, vLLM) needs no key, but the SDK requires a string.
        api_key=key or "not-needed",
        base_url=base_url,
        model=model,
        timeout=_float("LLM_TIMEOUT", 60.0),
        max_retries=_int("LLM_MAX_RETRIES", 2),
        temperature=_float("LLM_TEMPERATURE", 0.4),
    )


def llm_available() -> bool:
    return llm_config() is not None


# Keys from the old provider-specific scheme. Still recognised *only* to tell a
# developer why their previously-working setup went quiet.
LEGACY_KEYS = [
    "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY",
    "TOGETHER_API_KEY", "OPENROUTER_API_KEY", "DEEPSEEK_API_KEY", "FIREWORKS_API_KEY",
]


def diagnose() -> list[str]:
    """Human-readable warnings for the mistakes people actually make."""
    notes = []
    key = (os.environ.get("LLM_API_KEY") or "").strip()
    base_url = (os.environ.get("LLM_BASE_URL") or "").strip()
    model = (os.environ.get("LLM_MODEL") or "").strip()
    cfg = llm_config()

    if cfg is None:
        if (key or base_url) and not model:
            notes.append("LLM_MODEL is not set — it is required. See .env.example.")
        elif model and not (key or base_url):
            notes.append(
                "LLM_MODEL is set but LLM_API_KEY is not — set it, or set "
                "LLM_BASE_URL for a keyless local server.")
        else:
            notes.append(
                "No LLM provider configured. Copy .env.example to .env and set "
                "LLM_API_KEY, LLM_BASE_URL and LLM_MODEL. Emoji search and "
                "rule-based composing still work without it.")

        stale = [k for k in LEGACY_KEYS if os.environ.get(k)]
        if stale:
            notes.append(
                f"Found {', '.join(stale)}, which this app no longer reads. "
                "Configuration is now LLM_API_KEY / LLM_BASE_URL / LLM_MODEL only.")
        return notes

    if base_url and not base_url.startswith(("http://", "https://")):
        notes.append(f"LLM_BASE_URL does not start with http:// or https:// — got {base_url!r}")
    if base_url and base_url.rstrip("/").endswith("/chat/completions"):
        notes.append(
            "LLM_BASE_URL should be the API root (…/v1), not the /chat/completions path.")
    if base_url and ("localhost" in base_url or "127.0.0.1" in base_url):
        notes.append(
            f"Using a local endpoint — make sure that server is running at {base_url}")
    return notes


def summary() -> str:
    """One line for the startup log."""
    cfg = llm_config()
    if cfg is None:
        return "LLM mode: disabled (no provider configured) — rules mode still works"
    return (f"LLM mode: {cfg.provider} · {cfg.model} · "
            f"{cfg.base_url or 'https://api.openai.com/v1'}")


# ---------------------------------------------------------------------- CLI
def _report():
    print("LinkedIn emoji app — LLM configuration\n")
    loaded = load_dotenv()
    print(f"  .env file      : {ENV_FILE}")
    print(f"                   {'loaded' if loaded else 'not present (using real environment only)'}")
    cfg = llm_config()
    print()
    if cfg is None:
        print("  status         : NOT CONFIGURED")
        print("                   emoji search and rule-based composing work fine;")
        print("                   only the LLM placement mode is unavailable.")
    else:
        print("  status         : configured")
        print(f"  provider       : {cfg.provider}")
        print(f"  model          : {cfg.model}")
        print(f"  base_url       : {cfg.base_url or 'https://api.openai.com/v1 (SDK default)'}")
        print(f"  key            : {cfg.masked_key}")
        print(f"  timeout        : {cfg.timeout}s   retries: {cfg.max_retries}   "
              f"temperature: {cfg.temperature}")

    notes = diagnose()
    if notes:
        print("\n  notes:")
        for n in notes:
            print(f"    - {n}")

    print("\n  tunables (all optional): LLM_TIMEOUT, LLM_MAX_RETRIES, LLM_TEMPERATURE")
    print("  endpoints for common providers are listed in .env.example")
    return 0 if cfg else 1


if __name__ == "__main__":
    raise SystemExit(_report())
