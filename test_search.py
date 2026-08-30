"""Ranking regression tests.  Run: python test_search.py  (or: pytest -q)"""

from search import get_index, norm_char

ix = get_index()


def top(q, n=10):
    return [norm_char(r["char"]) for r in ix.search(q, limit=n)[0]]


def related(q, n=12):
    r = ix.query(q, limit=30, rec_limit=n)
    return [norm_char(x["char"]) for x in r["related"]]


# (query, emoji that must appear in the top N)
EXPECT_TOP = [
    ("hiring", "📢", 5), ("hiring", "💼", 5),
    ("we are hiring", "🙌", 8),
    ("celebrate", "🎉", 2), ("congrats", "🥳", 5),
    ("launch", "🚀", 2), ("shipped", "🚀", 3),
    ("growth", "📈", 2), ("q3 results", "📊", 5),
    ("burnout", "🧘", 3), ("imposter syndrome", "🧘", 5),
    ("thank you", "🙏", 2), ("gratitude", "🙏", 3),
    ("open to work", "💼", 5),
    ("team", "🤝", 2), ("leadership", "🧭", 3),
    ("ai", "🤖", 2), ("machine learning", "🤖", 3),
    ("money", "💰", 2), ("data", "📊", 2),
    ("link in comments", "👇", 3),
    ("pride", "🌈", 3),
    # literal lookups must still work
    ("rocket", "🚀", 1), ("laptop", "💻", 1), ("pizza", "🍕", 1),
    ("star", "⭐", 2), ("japan flag", "🇯🇵", 1),
    ("flag", "🏁", 5),          # generic "flag" must not be buried by countries
    # typo tolerance
    ("grwoth", "📈", 3), ("recruting", "💼", 6), ("thnak you", "🙏", 3),
]

# things that must NOT rank highly
EXPECT_ABSENT = [
    ("flag", "🇨🇳", 3),         # country flags demoted for a generic query
]


def main():
    fails = []
    for q, want, n in EXPECT_TOP:
        got = top(q, n)
        if norm_char(want) not in got:
            fails.append(f"  {q!r}: expected {want} in top {n}, got {' '.join(got)}")
    for q, unwanted, n in EXPECT_ABSENT:
        got = top(q, n)
        if norm_char(unwanted) in got:
            fails.append(f"  {q!r}: {unwanted} should not be in top {n}, got {' '.join(got)}")

    # recommendations must be non-empty, and must not just echo the results
    for q in ["hiring", "celebrate", "burnout", "ai", "🚀"]:
        rel = related(q)
        if not rel:
            fails.append(f"  {q!r}: no recommendations returned")
        overlap = set(rel) & set(top(q, 30))
        if overlap:
            fails.append(f"  {q!r}: recommendations duplicate results: {overlap}")

    # empty / junk queries degrade gracefully
    assert ix.query("")["count"] == 0
    assert ix.query("asdfghjkl")["count"] == 0
    assert ix.query("🚀")["results"][0]["char"] == "🚀"
    assert not ix.unknown_concept_chars, ix.unknown_concept_chars

    total = len(EXPECT_TOP) + len(EXPECT_ABSENT) + 5
    if fails:
        print(f"FAIL  {len(fails)}/{total} checks\n" + "\n".join(fails))
        raise SystemExit(1)
    print(f"ok    {total} ranking checks passed  ({len(ix.records)} emoji indexed)")


def test_ranking():
    main()


# ---------------------------------------------------------------- composer
def test_compose():
    from compose import compose_rules, verify_untouched, segment

    launch = ("We shipped v2 today.\n\n"
              "- Latency down 60%\n- Zero-downtime migration\n\n"
              "Full writeup in the comments.\n\n#engineering")
    r = compose_rules(launch)
    assert verify_untouched(launch, r["text"]), "rules path altered the author's words"
    assert r["count"] >= 2
    assert "#engineering" in r["text"].split("\n")[-1], "hashtag line was touched"
    assert r["text"].split("\n")[-1].strip().startswith("#")

    # a somber post must not be decorated
    somber = ("I got laid off in March.\n\n"
              "Burnout is real and so is shame.\n\nThank you to everyone who helped.")
    s = compose_rules(somber)
    assert s["count"] == 0, f"placed emoji on a layoff post: {s['text']}"
    assert "note" in s

    # existing emoji are respected, never doubled
    already = "🚀 We shipped v2 today.\n\n- Latency down 60%"
    a = compose_rules(already)
    assert a["text"].count("🚀") == 1

    # density is honoured
    many = "\n".join(f"- point about growth and hiring number {i}" for i in range(12))
    assert compose_rules(many, density="light")["count"] <= 3
    assert compose_rules(many, density="heavy")["count"] <= 10

    # no emoji is ever repeated
    chars = [p["emoji"] for p in compose_rules(many, density="heavy")["placements"]]
    assert len(chars) == len(set(chars)), f"repeated emoji: {chars}"

    # segmentation basics
    kinds = [l.kind for l in segment("Hook line\n\n- a bullet\n\nThoughts?\n\n#tag")]
    assert kinds[0] == "hook" and "bullet" in kinds and "cta" in kinds and "hashtag" in kinds

    # empty input degrades gracefully
    assert compose_rules("")["count"] == 0

    # The tamper check must tolerate legitimate placement (markers replaced, text
    # reflowed) while still catching any change to the author's actual words.
    o = "We shipped v2 today.\n\n- Latency down 60%\n\nFull writeup in the comments."
    allowed = [
        "🚀 We shipped v2 today.\n\n📈 Latency down 60%\n\n👇 Full writeup in the comments.",
        "🚀 We shipped v2 today.\n\n📈 - Latency down 60%\n\n👇 Full writeup in the comments.",
        "🚀 We shipped v2 today. 📈 Latency down 60% 👇 Full writeup in the comments.",
    ]
    forbidden = [
        "🚀 We launched v2 today.\n\n📈 Latency down 60%\n\n👇 Full writeup in the comments.",
        "🚀 We shipped v2 today, finally.\n\n📈 Latency down 60%\n\n👇 Full writeup in the comments.",
        "🚀 We shipped v2.\n\n📈 Latency down 60%\n\n👇 Full writeup in the comments.",
        "🚀 We shipped v2 today.\n\n📈 Latency down 80%\n\n👇 Full writeup in the comments.",
    ]
    for c in allowed:
        assert verify_untouched(o, c), f"false alarm on legitimate placement: {c!r}"
    for c in forbidden:
        assert not verify_untouched(o, c), f"missed a real edit: {c!r}"

    # The LLM path is guarded in code, not just by prompt: emoji on painful lines
    # are stripped, party emoji are stripped post-wide, but a genuinely good-news
    # line in a hard post keeps its 🚀.
    from compose import enforce_sensitivity

    llm_out = ("📉 I got laid off in March.\n\nBurnout is real.\n\n"
               "🚀 Today I start a new role.\n\n🎉 Thank you to everyone.")
    cleaned, removed = enforce_sensitivity(llm_out, post_is_somber=True)
    assert "📉" not in cleaned and "🎉" not in cleaned, cleaned
    assert "🚀 Today I start a new role." in cleaned, cleaned
    assert set(removed) == {"📉", "🎉"}, removed

    # and it must not touch an ordinary upbeat post
    good = "🚀 We shipped v2 today.\n\n📈 Latency down 60%\n\n👇 Read more."
    assert enforce_sensitivity(good, post_is_somber=False) == (good, [])

    print("ok    compose checks passed")


def test_llm_config():
    """Provider resolution and JSON parsing — no network calls."""
    import os

    import compose as c
    import config

    keys = ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "LLM_TIMEOUT",
            "LLM_MAX_RETRIES", "LLM_TEMPERATURE"] + config.LEGACY_KEYS
    saved = {k: os.environ.pop(k, None) for k in keys}
    try:
        assert c.llm_config() is None, "should report unconfigured with no env"

        # LLM_MODEL is required — a key alone is not enough
        os.environ["LLM_API_KEY"] = "sk-test-key-1234567890"
        assert c.llm_config() is None, "must require LLM_MODEL"
        assert any("LLM_MODEL is not set" in n for n in config.diagnose())

        os.environ["LLM_MODEL"] = "gpt-4o-mini"
        cfg = c.llm_config()
        assert cfg.provider == "openai", cfg.provider   # no base_url -> OpenAI
        assert cfg.base_url is None
        assert cfg.model == "gpt-4o-mini"
        assert cfg.api_key == "sk-test-key-1234567890"
        assert "api_key" not in cfg.describe(), "describe() must never leak the key"
        assert "…" in cfg.masked_key and "1234567890" not in cfg.masked_key

        # base_url drives only the display label
        os.environ["LLM_BASE_URL"] = "https://api.groq.com/openai/v1"
        assert c.llm_config().provider == "groq"
        os.environ["LLM_BASE_URL"] = "https://example.invalid/v1"
        assert c.llm_config().provider == "example.invalid"

        # keyless local server works
        del os.environ["LLM_API_KEY"]
        os.environ["LLM_BASE_URL"] = "http://localhost:11434/v1"
        os.environ["LLM_MODEL"] = "llama3.2"
        cfg = c.llm_config()
        assert cfg is not None and cfg.provider == "ollama"
        assert cfg.api_key == "not-needed"
        assert "keyless" in cfg.masked_key

        # tunables come from the environment
        os.environ["LLM_TIMEOUT"] = "12.5"
        os.environ["LLM_MAX_RETRIES"] = "5"
        os.environ["LLM_TEMPERATURE"] = "0"
        cfg = c.llm_config()
        assert (cfg.timeout, cfg.max_retries, cfg.temperature) == (12.5, 5, 0.0)
        os.environ["LLM_TIMEOUT"] = "not-a-number"      # bad values fall back
        assert c.llm_config().timeout == 60.0

        # provider-specific keys are no longer read, and say so
        for k in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"):
            os.environ.pop(k, None)
        os.environ["OPENAI_API_KEY"] = "sk-old-style"
        assert c.llm_config() is None, "legacy provider keys must not configure the app"
        assert any("no longer reads" in n for n in config.diagnose())
    finally:
        for k in keys:
            os.environ.pop(k, None)
            if saved[k] is not None:
                os.environ[k] = saved[k]

    # tolerant JSON parsing across provider quirks
    assert c._parse_json('{"text":"a","placements":[]}')["text"] == "a"
    assert c._parse_json('```json\n{"text":"a"}\n```')["text"] == "a"
    assert c._parse_json('Sure!\n{"text":"a"}\nHope that helps.')["text"] == "a"
    try:
        c._parse_json("no json here")
        raise AssertionError("should have raised on non-JSON")
    except ValueError:
        pass
    print("ok    llm provider config checks passed")


def test_dotenv():
    """A .env is a local convenience and must never shadow a real env var —
    otherwise a stray file could silently redirect a deployment's API calls."""
    import os
    import pathlib

    import compose as c

    # Use a temp file rather than the repo's .env, so this always runs and never
    # touches a developer's real configuration.
    import tempfile

    saved = os.environ.pop("LLM_MODEL", None)
    with tempfile.TemporaryDirectory() as d:
        env = pathlib.Path(d) / ".env"
        env.write_text("LLM_MODEL=from-dotenv\nLLM_API_KEY=k\n", encoding="utf-8")
        try:
            c._load_dotenv(env)
            assert os.environ.get("LLM_MODEL") == "from-dotenv", "did not load .env"

            # now a real environment variable must win
            os.environ["LLM_MODEL"] = "from-real-env"
            c._load_dotenv(env)
            assert os.environ["LLM_MODEL"] == "from-real-env", ".env overrode the real env"

            # a missing file is not an error
            assert c._load_dotenv(pathlib.Path(d) / "nope.env") is False
        finally:
            os.environ.pop("LLM_MODEL", None)
            os.environ.pop("LLM_API_KEY", None)
            if saved is not None:
                os.environ["LLM_MODEL"] = saved

    # and it must be excluded everywhere that ships code
    root = pathlib.Path(c.__file__).parent
    for name in (".gitignore", ".dockerignore", ".gcloudignore"):
        body = (root / name).read_text(encoding="utf-8")
        assert ".env" in body, f"{name} does not exclude .env"

    # config diagnostics must catch the mistakes they exist for
    import config

    tracked = ["LLM_API_KEY", "LLM_MODEL", "LLM_BASE_URL"] + config.LEGACY_KEYS
    saved_env = {k: os.environ.pop(k, None) for k in tracked}
    try:
        assert any("No LLM provider" in n for n in config.diagnose())

        os.environ["LLM_MODEL"] = "some-model"           # model but no key
        assert any("LLM_API_KEY is not" in n for n in config.diagnose())
        del os.environ["LLM_MODEL"]

        os.environ["LLM_API_KEY"] = "k"                  # key but no model
        assert any("LLM_MODEL is not set" in n for n in config.diagnose())

        os.environ["LLM_MODEL"] = "m"
        os.environ["LLM_BASE_URL"] = "http://x/v1/chat/completions"
        assert any("API root" in n for n in config.diagnose()), "missed /chat/completions"

        os.environ["LLM_BASE_URL"] = "localhost:11434/v1"    # missing scheme
        assert any("http://" in n for n in config.diagnose())

        os.environ["LLM_BASE_URL"] = "http://localhost:11434/v1"
        assert any("local endpoint" in n for n in config.diagnose())
    finally:
        for k, v in saved_env.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v

    print("ok    dotenv + config diagnostics passed")


def test_packaging():
    """Every local module the app imports must be listed in BOTH deploy configs.

    Adding config.py broke this silently: the code ran locally and in tests, and
    would only have failed with ImportError inside a deployed container.
    """
    import ast
    import pathlib

    root = pathlib.Path(__file__).parent
    local = {p.stem for p in root.glob("*.py")} - {"test_search", "modal_app", "build_dataset"}

    # modules reachable from app.py
    needed, seen = set(), set()
    queue = ["app"]
    while queue:
        mod = queue.pop()
        if mod in seen or mod not in local:
            continue
        seen.add(mod)
        needed.add(mod)
        tree = ast.parse((root / f"{mod}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                queue += [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                queue.append(node.module.split(".")[0])

    modal_src = (root / "modal_app.py").read_text(encoding="utf-8")
    docker_src = (root / "Dockerfile").read_text(encoding="utf-8")
    for mod in sorted(needed):
        assert f'"{mod}"' in modal_src, f"modal_app.py does not ship {mod}.py"
        assert f"{mod}.py" in docker_src, f"Dockerfile does not COPY {mod}.py"
    print(f"ok    packaging checks passed ({', '.join(sorted(needed))})")


if __name__ == "__main__":
    main()
    test_compose()
    test_llm_config()
    test_dotenv()
    test_packaging()
