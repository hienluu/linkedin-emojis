"""Take a LinkedIn post and put well-chosen emoji in the right places.

Two backends, same input/output contract:

  compose_rules(text)  - deterministic, local, ~5ms, no API key
  compose_llm(text)    - any OpenAI-compatible LLM; better judgement about
                         tone and emphasis. Configured via config.py.

Placement follows the conventions that actually read well on LinkedIn:
  * the hook line gets one emoji, leading
  * list items get one each, replacing the "-"/"•" marker
  * the call-to-action gets a pointer (👇 / 📩)
  * body prose is left alone — mid-paragraph emoji read as clutter
  * hashtag lines are never touched
  * nothing is ever placed mid-sentence, and no emoji repeats

Both backends only ever *insert* characters. The user's words are never altered;
`verify_untouched` enforces that, including for the LLM path.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from concepts import CONCEPTS
from search import get_index, norm_char, tokenize

BULLET_RE = re.compile(r"^(\s*)([-*•▪·–—]|\d+[.)])\s+(.*)$")
HASHTAG_RE = re.compile(r"^\s*#\w")
EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002190-\U000021FF"
    "\U00002B00-\U00002BFF\U0001F1E6-\U0001F1FF️‍⃣]+"
)
CTA_WORDS = {
    "comment", "comments", "link", "dm", "message", "follow", "subscribe", "repost",
    "share", "thoughts", "curious", "agree", "disagree", "tell", "reply", "join",
    "register", "sign", "apply", "read", "watch", "listen", "download",
}

DENSITY = {"light": 3, "balanced": 6, "heavy": 10}

# Emoji that are safe to auto-place. Restricting to the curated lexicon is what
# keeps output professional — an unrestricted index will happily answer "a slice
# of the market" with 🍕.
POOL = {norm_char(ch) for c in CONCEPTS.values() for ch in c["emoji"]}


@dataclass
class Line:
    raw: str
    kind: str = "body"           # hook | bullet | cta | hashtag | blank | body
    indent: str = ""
    marker: str = ""
    content: str = ""
    emoji: str | None = None
    why: str = ""
    candidates: list = field(default_factory=list)


MARKERS = "-*•▪·–—"


def strip_emoji(text):
    """Normalised text for tamper checking: emoji, list-marker characters and all
    whitespace removed.

    Markers are dropped everywhere rather than only at line start. Replacing "- "
    with an emoji is a legitimate placement, and reflowing a line changes whether a
    given dash *is* at line start — comparing positionally gives false alarms. A
    dash inside "zero-downtime" disappears from both sides equally, so reworded
    text is still caught."""
    out = EMOJI_RE.sub("", text)
    out = out.translate({ord(c): None for c in MARKERS})
    return re.sub(r"\s+", "", out)


def has_emoji(text):
    return bool(EMOJI_RE.search(text.strip()))


def segment(text):
    """Split a post into classified lines."""
    lines = [Line(raw=r) for r in text.replace("\r\n", "\n").split("\n")]
    seen_hook = False
    for ln in lines:
        s = ln.raw.strip()
        if not s:
            ln.kind = "blank"
            continue
        if HASHTAG_RE.match(ln.raw) and all(
            w.startswith("#") for w in s.split() if w
        ):
            ln.kind = "hashtag"
            continue
        m = BULLET_RE.match(ln.raw)
        if m:
            ln.kind = "bullet"
            ln.indent, ln.marker, ln.content = m.group(1), m.group(2), m.group(3)
            continue
        ln.content = s
        words = set(tokenize(s))
        if not seen_hook:
            ln.kind = "hook"
            seen_hook = True
        elif (s.endswith("?") and len(words) <= 14) or (words & CTA_WORDS and len(words) <= 14):
            ln.kind = "cta"
        else:
            ln.kind = "body"
    return lines


# Lines about loss, illness or hardship must never be decorated. Getting this
# wrong ("🎉 I got laid off in March") is far worse than placing nothing at all,
# so a match here vetoes the line outright.
SOMBER = {
    "laid", "layoff", "layoffs", "fired", "redundant", "redundancy", "unemployed",
    "died", "death", "passed", "funeral", "grief", "grieving", "loss", "lost",
    "cancer", "illness", "sick", "hospital", "diagnosis", "surgery", "injury",
    "divorce", "burnout", "burnt", "depression", "depressed", "anxiety", "shame",
    "struggling", "struggled", "failed", "failure", "mistake", "sorry", "apology",
    "tragedy", "crisis", "war", "disaster", "harassment", "discrimination", "toxic",
}
SOMBER_PHRASES = ("laid off", "let go", "passed away", "stepping away", "stepping down",
                  "difficult news", "hard news", "sad news", "my last day")

# Emoji that would jar anywhere in a serious post — outright party.
# Deliberately narrow: "laid off, then found a new role" is one of the most common
# LinkedIn arcs, and 🚀 on the good-news line is right. Only 🎉-tier is suppressed
# post-wide; the per-line somber check already protects the painful lines.
CELEBRATORY = {norm_char(c) for c in "🎉🥳🎊🎈🍾🥂💯🤩😍👏🔥"}

# Function words that carry no emoji signal but do match emoji names
# ("not" -> ⛔ no entry, "up" -> ⬆️). Filtered out before scoring.
STOP = {
    "a", "an", "the", "and", "or", "but", "if", "so", "as", "at", "by", "for", "from",
    "in", "into", "of", "on", "to", "with", "we", "i", "you", "he", "she", "they",
    "it", "our", "your", "my", "their", "this", "that", "these", "those", "is", "are",
    "was", "were", "be", "been", "am", "do", "does", "did", "have", "has", "had",
    "no", "not", "just", "like", "can", "will", "would", "should", "could", "than",
    "then", "there", "here", "what", "when", "who", "how", "why", "all", "any", "some",
    "more", "most", "very", "too", "only", "also", "about", "over", "out", "up", "down",
}


def _is_somber(text):
    low = text.lower()
    if any(p in low for p in SOMBER_PHRASES):
        return True
    return bool(set(tokenize(text)) & SOMBER)


def _signal_text(text):
    """Drop function words so they can't drive emoji choice."""
    kept = [t for t in tokenize(text) if t not in STOP]
    return " ".join(kept) if kept else text


# A call-to-action reads best with a pointer, not a topical emoji.
CTA_POOL = {norm_char(c): i for i, c in enumerate(CONCEPTS["attention"]["emoji"])}
HOOK_POOL = {norm_char(c) for c in "🚀🔥💡🎉📣✨🎯👀🧠⚡"}


def _rank_for_line(text, used, kind="body"):
    """Best curated emoji for a line, as (emoji, score, why)."""
    ix = get_index()
    scores, why = {}, {}
    signal = _signal_text(text)

    # 1. Curated concepts are the primary signal — they encode intent, not depiction.
    #    Matched on the raw line, where multi-word aliases ("open to work") live.
    for key, confidence in ix._concept_matches(text, allow_fuzzy=False).items():
        emojis = CONCEPTS[key]["emoji"]
        for rank, ch in enumerate(emojis):
            n = norm_char(ch)
            s = 100.0 * confidence * (1.0 - rank / (len(emojis) + 2))
            if s > scores.get(n, 0):
                scores[n], why[n] = s, key
        # remember the display form (with variation selector) for output
        for ch in emojis:
            why.setdefault(norm_char(ch) + "#disp", ch)

    # 2. Literal search, but only emoji in the curated pool, and with fuzzy
    #    matching off — a typo guess is fine in a search box, but here it silently
    #    stamps the wrong emoji onto someone's post ("zero-downtime" -> ⏰).
    hits, _ = ix.search(signal, limit=25, fuzzy=False)
    for rank, r in enumerate(hits):
        n = norm_char(r["char"])
        if n not in POOL:
            continue
        s = 34.0 * (1.0 - rank / 30.0)
        if s > scores.get(n, 0):
            scores[n], why[n] = s, r["name"]
        why.setdefault(n + "#disp", r["char"])

    # 3. Bias by line role.
    for n in list(scores):
        if kind == "cta" and n in CTA_POOL:
            scores[n] = scores[n] * 1.5 + 40.0 * (1.0 - CTA_POOL[n] / 12.0)
        elif kind == "hook" and n in HOOK_POOL:
            scores[n] *= 1.25

    ranked = [
        (why.get(n + "#disp", n), s, why[n])
        for n, s in sorted(scores.items(), key=lambda kv: -kv[1])
        if n not in used
    ]
    return ranked


# --------------------------------------------------------------------- rules
def compose_rules(text, density="balanced"):
    budget = DENSITY.get(density, 6)
    lines = segment(text)
    used = set()
    # Whatever the author already wrote, normalised, for a containment test that
    # also catches emoji inside a run like "🚀🎉".
    already = norm_char(text)

    # A post that is *mostly* about something hard gets a lighter touch and no
    # celebratory emoji anywhere, even on its upbeat lines.
    somber_lines = sum(1 for l in lines if l.kind != "blank" and _is_somber(l.raw))
    content_lines = max(1, sum(1 for l in lines if l.kind != "blank"))
    post_is_somber = somber_lines / content_lines >= 0.25
    if post_is_somber:
        budget = min(budget, 2)

    # Lines that may receive an emoji, in priority order: bullets read best with
    # them, then the hook, then the CTA.
    order = (
        [l for l in lines if l.kind == "bullet"]
        + [l for l in lines if l.kind == "hook"]
        + [l for l in lines if l.kind == "cta"]
    )

    # Deliberately high: a bullet with no emoji looks fine, a bullet with the
    # wrong emoji looks careless. Silence beats a bad guess.
    MIN_SCORE = 32.0
    for ln in order:
        if len(used) >= budget:
            break
        source = ln.content or ln.raw.strip()
        if not source or has_emoji(source):
            continue  # respect emoji the author already placed
        if _is_somber(source):
            ln.why = "skipped: sensitive subject"
            continue
        ranked = _rank_for_line(source, used, kind=ln.kind)
        # `used` only tracks what we placed. An emoji the author already used
        # elsewhere would otherwise be placed again — the skipped line never
        # registered it.
        ranked = [r for r in ranked if norm_char(r[0]) not in already]
        if post_is_somber:
            ranked = [r for r in ranked if norm_char(r[0]) not in CELEBRATORY]
        ln.candidates = [{"char": c, "why": w} for c, _, w in ranked[:5]]
        if ranked and ranked[0][1] >= MIN_SCORE:
            ln.emoji, _, ln.why = ranked[0]
            used.add(norm_char(ln.emoji))

    out = _render(lines, mode="rules", density=density)
    if post_is_somber:
        out["note"] = "Sensitive subject detected — emoji kept minimal and celebratory ones suppressed."
    return out


def _render(lines, mode, density):
    out, placements = [], []
    for i, ln in enumerate(lines):
        if not ln.emoji:
            out.append(ln.raw)
            continue
        if ln.kind == "bullet":
            new = f"{ln.indent}{ln.emoji} {ln.content}"
        else:
            new = f"{ln.emoji} {ln.raw.strip()}"
        out.append(new)
        placements.append(
            {"line": i, "kind": ln.kind, "emoji": ln.emoji,
             "why": ln.why, "text": (ln.content or ln.raw.strip())[:80],
             "alternatives": [c["char"] for c in ln.candidates[1:5]]}
        )
    return {
        "mode": mode,
        "density": density,
        "text": "\n".join(out),
        "placements": placements,
        "count": len(placements),
    }


# ----------------------------------------------------------------------- llm
SYSTEM = """You place emoji into LinkedIn posts.

Rules, in order of importance:
1. NEVER change the author's words. Do not add, delete, reword, reorder, or \
re-punctuate anything. You may ONLY insert emoji characters and the single space \
that follows one.
2. Place an emoji at the START of a line. If the line begins with a "-" or "•" list \
marker, DELETE that marker and put the emoji in its place — never leave both, and \
never output "🚀 - text". Never place an emoji mid-sentence.
3. Good targets: the opening hook, each item in a list, and a closing \
call-to-action. Leave ordinary body paragraphs alone.
4. Never touch a line that is only hashtags, and never touch a line that already \
has an emoji.
5. Use at most {budget} emoji in total. Fewer is better than forced. Never repeat one.
6. Keep it professional. Prefer restrained, widely-understood emoji \
(🚀 📈 🎯 💡 🤝 🙌 ✅ 👇 📊 🔥) over obscure or cutesy ones. No skin tones.
7. NEVER decorate a line about hardship — a layoff, illness, grief, failure, \
burnout or an apology. Leave those lines completely bare. A post that is mostly \
about something painful should get very few emoji, or none at all. Putting 🎉 or 📉 \
on "I got laid off" is the worst thing you can do here.

Return the complete post with emoji inserted, and a short reason for each choice."""

def _parse_json(content):
    """Parse a model's JSON reply, tolerating code fences and surrounding prose —
    providers without json_object mode wrap output in ```json blocks."""
    import json

    s = content.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        start, end = s.find("{"), s.rfind("}")
        if start == -1 or end <= start:
            raise ValueError(f"model did not return JSON: {content[:200]!r}")
        return json.loads(s[start:end + 1])


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {"type": "string", "description": "the full post with emoji inserted"},
        "placements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "emoji": {"type": "string"},
                    "why": {"type": "string", "description": "under 8 words"},
                },
                "required": ["emoji", "why"],
            },
        },
    },
    "required": ["text", "placements"],
}

# Provider resolution lives in config.py so it can be inspected standalone
# (`uv run config.py`) without importing the placement engine.
from config import llm_available, llm_config, load_dotenv as _load_dotenv  # noqa: E402

_load_dotenv()


def _llm_placements(composed, model_reasons):
    """Describe what the model actually did, by reading its output.

    Derived from the composed text rather than the model's self-reported list,
    which gives three things that list cannot:
      * line numbers, so a swap edits the right line instead of the first match
      * alternatives, computed by the same ranking the rules path uses, so both
        modes offer the same swap chips
      * accuracy — it reflects the text, not what the model claims it did
    """
    reasons = {}
    for p in model_reasons or []:
        ch = p.get("emoji")
        if ch:
            reasons.setdefault(norm_char(ch), (p.get("why") or "").strip())

    placed = {}
    for i, line in enumerate(composed.split("\n")):
        m = LEADING_EMOJI_RE.match(line)
        if m and line[m.end():].strip():
            placed[i] = (m.group(2), line[m.end():])

    used = {norm_char(ch) for ch, _ in placed.values()}
    out = []
    for i, (ch, rest) in placed.items():
        ranked = _rank_for_line(rest, used)      # `used` keeps alternatives unique
        out.append({
            "line": i,
            "kind": "llm",
            "emoji": ch,
            "why": reasons.get(norm_char(ch), ""),
            "text": rest.strip()[:80],
            "alternatives": [c for c, _, _ in ranked[:4]],
        })
    return out


def _explain_api_error(exc, cfg):
    """Turn an SDK exception into something a developer can act on.

    The raw errors ("Error code: 401") don't say which of the eight possible env
    vars supplied the bad key, or which endpoint was called.
    """
    status = getattr(exc, "status_code", None)
    where = f"{cfg.provider} · {cfg.model} · {cfg.base_url or 'api.openai.com'}"
    if status == 401 or "api_key" in str(exc).lower() or "unauthorized" in str(exc).lower():
        return (f"Authentication failed for {where}. LLM_API_KEY is {cfg.masked_key} — "
                "check it, then run `uv run config.py`.")
    if status == 404:
        return (f"Model {cfg.model!r} not found at {cfg.base_url or 'api.openai.com'}. "
                "Set LLM_MODEL to a model this provider serves.")
    if status == 429:
        return f"Rate limited or out of quota on {cfg.provider}. Try again shortly."
    if isinstance(exc, (ConnectionError, TimeoutError)) or "connect" in str(exc).lower():
        hint = (" Is the local server running?" if cfg.base_url
                and ("localhost" in cfg.base_url or "127.0.0.1" in cfg.base_url) else "")
        return f"Could not reach {cfg.base_url or 'api.openai.com'}.{hint}"
    return f"{type(exc).__name__} calling {where}: {exc}"


def compose_llm(text, density="balanced", model=None):
    """LLM-backed placement via any OpenAI-compatible endpoint."""
    import json

    from openai import OpenAI

    cfg = llm_config()
    if not cfg:
        raise RuntimeError(
            "No LLM provider configured. Copy .env.example to .env and set one "
            "option, then run `uv run config.py` to check it."
        )

    budget = DENSITY.get(density, 6)
    client = OpenAI(
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        timeout=cfg.timeout,
        max_retries=cfg.max_retries,
    )
    messages = [
        {"role": "system", "content": SYSTEM.format(budget=budget)},
        {"role": "user", "content":
            "Add emoji to this LinkedIn post. Reply with JSON matching this schema:\n"
            f"{json.dumps(RESPONSE_SCHEMA)}\n\n<post>\n{text}\n</post>"},
    ]
    kwargs = dict(model=model or cfg.model, messages=messages, temperature=cfg.temperature)

    # json_object mode is widely but not universally supported; fall back to a
    # plain call and parse, so an unknown provider still works.
    try:
        try:
            resp = client.chat.completions.create(
                response_format={"type": "json_object"}, **kwargs
            )
        except Exception:
            resp = client.chat.completions.create(**kwargs)
    except Exception as e:
        raise RuntimeError(_explain_api_error(e, cfg)) from e

    data = _parse_json(resp.choices[0].message.content or "")

    lines = [l for l in text.split("\n") if l.strip()]
    post_is_somber = sum(1 for l in lines if _is_somber(l)) / max(1, len(lines)) >= 0.25
    composed, removed = enforce_sensitivity(data["text"], post_is_somber)

    result = {
        "mode": "llm",
        "model": model or cfg.model,
        "provider": cfg.provider,
        "density": density,
        "text": composed,
        "placements": _llm_placements(composed, data.get("placements")),
    }
    if removed:
        result["note"] = (
            f"Removed {' '.join(removed)} from lines about a sensitive subject."
        )
    result["count"] = len(EMOJI_RE.findall(result["text"])) - len(EMOJI_RE.findall(text))
    result["verified"] = verify_untouched(text, result["text"])
    if not result["verified"]:
        result["warning"] = (
            "The model altered the post's wording, not just its emoji. "
            "Showing its output anyway — compare before posting."
        )
    return result


LEADING_EMOJI_RE = re.compile(rf"^(\s*)({EMOJI_RE.pattern})\s*")


def enforce_sensitivity(text, post_is_somber):
    """Strip emoji the model placed on sensitive lines.

    The system prompt asks for this, but a prompt is a request, not a guarantee —
    and `📉 I got laid off in March` is the one output that must never reach a
    user's clipboard. So it is enforced in code as well.
    """
    out, removed = [], []
    for line in text.split("\n"):
        m = LEADING_EMOJI_RE.match(line)
        if not m:
            out.append(line)
            continue
        emoji, rest = m.group(2), line[m.end():]
        drop = _is_somber(rest) or (post_is_somber and norm_char(emoji) in CELEBRATORY)
        if drop:
            removed.append(emoji)
            out.append(m.group(1) + rest)
        else:
            out.append(line)
    return "\n".join(out), removed


def verify_untouched(original, composed):
    """True if `composed` differs from `original` only by inserted emoji/whitespace."""
    return strip_emoji(original) == strip_emoji(composed)


def compose(text, mode="rules", density="balanced", model=None):
    text = (text or "").strip("\n")
    if not text.strip():
        return {"mode": mode, "text": "", "placements": [], "count": 0}
    if mode == "llm":
        return compose_llm(text, density=density, model=model)
    return compose_rules(text, density=density)


def llm_available():
    return llm_config() is not None
