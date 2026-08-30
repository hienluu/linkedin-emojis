# Emoji for LinkedIn posts

Two tools for writing LinkedIn posts, in one page with no build step:

1. **Search 1,898 emoji by meaning.** Type what your post is *about* — `hiring`,
   `burnout`, `Q3 results`, `link in comments` — not what the emoji looks like.
2. **Add emoji to a whole post.** Paste your draft, get it back with emoji placed
   where they belong. Rule-based (instant, free) or an LLM (better judgement).

It exists because the emoji lists floating around LinkedIn are long pages you can
only scroll and copy from — there is no way to search them, and no help deciding
which emoji suits "we just closed our Series A".

---

## Contents

- [Using the app](#using-the-app)
- [Run it locally](#run-it-locally)
- [Deploy your own](#deploy-your-own)
- [API](#api)
- [How it works](#how-it-works)
- [Tests](#tests)
- [Project layout](#project-layout)

---

## Using the app

### Search emoji

Type a meaning. Results are ranked for what a post author actually wants, and a
**You might also like** row suggests related emoji you didn't think to ask for.

```
hiring       ->  🚀 📢 💼 🙌 🎯 👔 📩 🔎 🤝 ✨     also: 🎉 📈 🌱 💪 📣 🌟
burnout      ->  🧘 🌿 ☕ 🌅 😌 🛌 🏖️ 🕯️ 🫖 🌸     also: ❤️ 🤝 🏡 🌍
q3 results   ->  📋 📊 🗺️ 📈 📉 🧭 🎯 🔢 📐 🗓️     also: 🧠 🚀 💹 💡
```

| Action | How |
|---|---|
| Copy an emoji | Click it |
| Collect several, copy as a set | Click several → **Copy all** in the bottom tray |
| Pick a skin tone | Hover an emoji that has variants, choose from the strip |
| Find similar to one you have | Paste the emoji itself into the search box |
| Keyboard | `/` focus search · `Enter` copy top hit · `Esc` clear |

Typos are fine (`grwoth`, `recruting`, `thnak you` all work). Recently copied emoji
persist in your browser via `localStorage`.

### Add emoji to a post

Open the **Add emoji to a post** tab, paste your draft, pick a mode and density,
press **Add emoji** (`Cmd`/`Ctrl` + `Enter`; `Cmd`/`Ctrl` + `Backspace` clears).

```
We shipped v2 today.                         🚀 We shipped v2 today.

Six months ago the roadmap was a    ->       Six months ago the roadmap was a
napkin sketch.                               napkin sketch.

- Latency down 60%                           📉 Latency down 60%
- Revenue up 40%                             💰 Revenue up 40%

Full writeup in the comments.                👇 Full writeup in the comments.

#engineering                                 #engineering
```

Placement follows the conventions that read well on LinkedIn: the hook line gets
one, list items get one each (replacing the `-` marker), the call-to-action gets a
pointer, ordinary body prose is left alone, and hashtag-only lines are never
touched. Nothing lands mid-sentence, no emoji repeats, and emoji you placed
yourself are left as they are.

| Mode | Speed | Cost | Character |
|---|---|---|---|
| **Rule-based** (default) | ~5 ms engine, ~0.3 s round trip | free | Deterministic and never surprising. Follows fixed conventions; can't read irony or judge which point matters most. |
| **LLM** | ~1.5–3 s | fractions of a cent | Any OpenAI-compatible provider. Better at picking the line that deserves emphasis. Needs an API key. |

**Density** — `light` (max 3 emoji), `balanced` (6), `heavy` (10).

**Clear**, **Copy post** and **Add emoji** live in a sticky toolbar that stays
pinned to the top of the page, so they remain one click away no matter how long the
post is. Clear is undoable — the confirmation toast restores your text if clicked.
Each panel scrolls internally rather than stretching the page.

Every placement is listed underneath with a one-line reason and up to four
alternatives; click one to swap it in.

### Two guarantees

**Rule-based mode cannot change your words** — it only ever inserts characters.
That is structural, not a promise.

**LLM mode is asked not to, and then checked.** `verify_untouched()` strips emoji,
list markers and whitespace from input and output and compares what remains, so it
tolerates a `-` being replaced by an emoji but catches any reworded, added, deleted
or altered text, including a changed number.

Models do occasionally reword — roughly 8% of calls in early usage here. When that
happens the response carries `changes`, a word-level diff, and the UI names the edit
rather than vaguely warning that something moved:

> The model changed your wording, not just emoji: "shipped" → "launched";
> "60%" → "80%". Switch to rule-based to keep your original exactly.

The banner offers a one-click **Use rule-based instead**, which re-runs locally on
your original text — free and instant. Naming the change matters because the reader
is scanning emoji placement, not proofreading text they already believe they wrote;
a swapped word or number is exactly what the eye skips.

**Sensitive posts are not decorated.** `🎉 I got laid off in March` is the failure
this guards against — and it is a real one; it is what the first version produced.
Lines about layoffs, illness, grief, burnout or failure get no emoji, in **both**
modes: for the LLM the rule is enforced in code after the response, not merely
requested in the prompt. A post that is mostly about something painful also
suppresses party emoji (🎉 🥳 🎊 …) throughout — while still allowing 🚀 on a
genuine good-news line, since "laid off, then found a new role" is one of the most
common arcs on the platform.

---

## Run it locally

Requires [uv](https://docs.astral.sh/uv/).

```bash
git clone <this repo> && cd linkedin-emojis
uv venv --python 3.12                 # matches the Modal runtime
uv pip install -r requirements.txt
uv run uvicorn app:api --reload       # http://127.0.0.1:8000
```

The dataset (`data/emojis.json`) is committed, so there is no build step. LLM mode
is disabled unless a provider is configured — see below.

### Configuring the LLM provider

Any **OpenAI-compatible** endpoint works. Three variables, and nothing else:

| Variable | |
|---|---|
| `LLM_API_KEY` | the key — omit only for a keyless local server |
| `LLM_BASE_URL` | the endpoint — omit for OpenAI itself |
| `LLM_MODEL` | the model — **required** whenever either other is set |

There are no per-provider environment variables and no precedence rules: the app
reads these three and nothing else. Point them at whichever provider you have.

| Provider | `LLM_BASE_URL` | a good `LLM_MODEL` |
|---|---|---|
| OpenAI | *(leave empty)* | `gpt-4o-mini` |
| Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-3.5-flash-lite` |
| Groq | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` |
| Together | `https://api.together.xyz/v1` | `meta-llama/Llama-3.3-70B-Instruct-Turbo` |
| OpenRouter | `https://openrouter.ai/api/v1` | `google/gemini-2.5-flash-lite` |
| DeepSeek | `https://api.deepseek.com` | `deepseek-chat` |
| Fireworks | `https://api.fireworks.ai/inference/v1` | `accounts/fireworks/models/llama-v3p3-70b-instruct` |
| Ollama (local) | `http://localhost:11434/v1` | `llama3.2` — no key needed |

For local development, copy the template and fill in the three:

```bash
cp .env.example .env
uv run config.py          # check what the app actually resolved
```

`config.py` prints the resolved endpoint, model and a masked key, then warns about
the mistakes people actually make — a key with no model, a `base_url` pointing at
`/chat/completions` instead of the API root, a missing `http://`, or a local server
that isn't running. It exits non-zero when unconfigured, so it works in a setup
script. The same warnings appear in the server's startup log and `GET /api/health`.

```
  status         : configured
  provider       : groq
  model          : llama-3.3-70b-versatile
  base_url       : https://api.groq.com/openai/v1
  key            : gsk-ab…mnop
  timeout        : 60.0s   retries: 2   temperature: 0.4
```

Or export directly instead of using a file:

```bash
export LLM_API_KEY=gsk-... \
       LLM_BASE_URL=https://api.groq.com/openai/v1 \
       LLM_MODEL=llama-3.3-70b-versatile
```

Optional tuning: `LLM_TIMEOUT` (60s), `LLM_MAX_RETRIES` (2), `LLM_TEMPERATURE`
(0.4), and `ENV_FILE` to load a different .env path.

The app requests JSON-object output and falls back to a plain call plus tolerant
parsing (code fences, surrounding prose) if a provider doesn't support that flag —
so an endpoint not listed above still works. `GET /api/health` reports the resolved
provider, model and base URL; it never returns the key.

### Protecting the paid endpoint

Rules mode is free and stays open. `mode=llm` costs money, so on a public
deployment it passes through `guard.py` first — three layers, weakest to
strongest guarantee:

1. **Origin check + signed single-use token.** The page fetches a short-lived
   HMAC token bound to the caller's IP; `/api/compose` requires an unused one and
   a matching `Origin`. This stops casual scripts and cross-site abuse.
2. **Per-IP rate limit** — default 5/min and 50/day.
3. **Global budget** — default 60/hour and 300/day.

Over any limit the API returns 429 and **the UI silently falls back to rules
mode**, so the app keeps working; it just stops spending.

Be clear about what layer 1 is worth: **nothing a browser sends can prove it came
from a browser.** A determined caller can replay the token handshake. Layers 1 and
2 are friction; layer 3 is the one that actually caps your bill, because it is
arithmetic rather than detection. Size it to a number you would be happy to pay.

| Variable | Default | |
|---|---|---|
| `LLM_MAX_PER_HOUR` | 60 | global hourly cap |
| `LLM_MAX_PER_DAY` | 300 | global daily cap |
| `LLM_MAX_PER_IP_MIN` | 5 | per-IP burst |
| `LLM_MAX_PER_IP_DAY` | 50 | per-IP daily |
| `LLM_TOKEN_TTL` | 300 | token lifetime, seconds |
| `LLM_REQUIRE_ORIGIN` | 1 | set `0` to allow direct API calls |
| `ALLOWED_ORIGINS` | *(same-origin)* | comma-separated extra origins |
| `GUARD_SECRET` | random per process | token signing key |

**Limits are per container.** Cloud Run and Modal may run several, so the real
ceiling is roughly `limit x max instances`. Both deployments cap instances at **2**
(`--max-instances 2`, `max_containers=2`), so the worst case is 2x the numbers
above — about 120 LLM calls/hour and 600/day. Exact global limits would need
shared state (Firestore/Redis); this is deliberately in-memory and approximate.
Lower the instance cap or the per-container limits to tighten it further.

**Set a quota cap on the provider key too.** The app can only protect calls that
go through the app. A spend limit or rate quota on the key itself (Google AI
Studio / Cloud Console) is the backstop if anything here is bypassed or
misconfigured. Do that regardless of what the app does.

`GET /api/health` reports current usage (`llm_calls_this_hour`, `denied`, …) for
monitoring.

**`.env` is for local development only.** Deployments get these from a Modal secret
or GCP Secret Manager — never from a file. Three properties enforce that:

- It is excluded from git, the Docker build context and the Cloud Build upload, so
  it cannot reach an image or a build log.
- It is loaded with `override=False`, so a real environment variable always wins.
  A stray `.env` can never shadow a production secret.
- Only `.env.example` — which holds no secrets — is committed.

A test asserts all three, because this is the kind of thing that breaks silently.

---

## Deploy your own

The app is a plain FastAPI ASGI service, so it runs anywhere. Two deployments are
configured; they share all application code and differ only in packaging.

| | Modal | Cloud Run |
|---|---|---|
| Deploy command | `uv run modal deploy modal_app.py` | `./deploy_gcp.sh` |
| Config file | `modal_app.py` | `Dockerfile` + `deploy_gcp.sh` |
| Build | image built by Modal | Cloud Build (no local Docker needed) |
| Secret store | Modal secret | Secret Manager |
| Scale to zero | `min_containers=0` | `--min-instances 0` |

Both re-deploy in place: run the same command again to ship changes.

### Modal

**First time only**

```bash
uv pip install modal
uv run modal setup                      # opens a browser to authenticate
```

**Deploy**

```bash
uv run modal deploy modal_app.py        # persistent URL
uv run modal serve  modal_app.py        # temporary dev URL, live reload
```

**Enable LLM mode** — create the secret first; the deploy expects the name
referenced in `modal_app.py` to exist:

```bash
modal secret create gemini-api-key --force \
    LLM_API_KEY=sk-... \
    LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/ \
    LLM_MODEL=gemini-3.5-flash-lite

uv run modal deploy modal_app.py        # redeploy to pick it up
```

`--force` overwrites an existing secret. The secret simply becomes the container's
environment, so it must contain the same three variables the app reads — a secret
holding a provider-specific key such as `OPENAI_API_KEY` is ignored. Rename the
secret in `modal_app.py` if you prefer a clearer name.

**Useful**

```bash
uv run modal app list                                  # deployments and running tasks
uv run modal app logs linkedin-emoji-search            # stream logs
uv run modal app stop <app-id> -y                      # -y required non-interactively
```

### Google Cloud Run

**First time only**

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud config set run/region us-west1

gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com

chmod +x deploy_gcp.sh
```

Billing must be enabled on the project.

**Deploy**

```bash
./deploy_gcp.sh
```

Builds remotely with Cloud Build, so no local Docker is needed. Defaults come from
your gcloud config; override any of them per-run:

```bash
PROJECT=my-project REGION=us-central1 SERVICE=emoji ./deploy_gcp.sh
```

**Enable LLM mode** — the script mounts the secret automatically if it exists, and
deploys rules-only if it doesn't:

```bash
printf %s "sk-your-key" | gcloud secrets create llm-api-key --data-file=-

LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/ \
LLM_MODEL=gemini-3.5-flash-lite ./deploy_gcp.sh
```

The secret is mounted as `LLM_API_KEY`; `LLM_BASE_URL` and `LLM_MODEL` are ordinary
env vars since they aren't sensitive. **`LLM_MODEL` is required** — without it the
revision deploys but LLM mode stays disabled.

The runtime service account needs `roles/secretmanager.secretAccessor` on the
secret. gcloud does *not* grant this for you: without it the revision fails to
start with `Permission denied on secret`. `deploy_gcp.sh` now grants it
automatically, scoped to that one secret, or do it by hand:

```bash
gcloud secrets add-iam-policy-binding llm-api-key \
  --member="serviceAccount:$(gcloud projects describe $(gcloud config get-value project) \
             --format='value(projectNumber)')-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

**Useful**

```bash
gcloud run services list --region us-west1
gcloud run services describe linkedin-emoji-search --region us-west1 --format='value(status.url)'
# logs — via Cloud Logging, so no `beta` component needed
gcloud logging read \
  'resource.type=cloud_run_revision AND resource.labels.service_name=linkedin-emoji-search' \
  --limit 20 --format='value(timestamp,textPayload)'
gcloud run services delete linkedin-emoji-search --region us-west1
```

`.gcloudignore` matters more than it looks: this project is not a git repo, so
gcloud will **not** fall back to `.gitignore`, and without that file the entire
`.venv/` would be uploaded on every deploy.

**Notes**

- Both endpoints are **public** — anyone with the URL can use them, and LLM mode spends
  your key. To restrict them: `requires_proxy_auth=True` on Modal, or drop
  `--allow-unauthenticated` from `deploy_gcp.sh` on Cloud Run.
- No GPU, no model weights, no database. The index is a ~450 KB JSON file loaded at
  container start, so idle cost is zero on both and cold start is a few seconds.
- Both deployments cap at 2 instances, which also bounds the LLM spend (see above).
- Just after a deploy, a warm container can briefly serve the *previous* version.
  If a change seems missing, wait ~20 s before digging in — and stop polling, since
  each request resets Modal's scaledown timer and keeps the old container alive.

---

## Feedback and usage signals

A thumbs up/down widget with one optional text box appears after someone copies
something — once per browser, plus a **Send feedback** link in the footer.
Alongside it the app records two implicit signals that are usually more actionable
than opinions:

- **`zero_results`** — searches that matched nothing. Every one is a phrase missing
  from `concepts.py`, so this doubles as a worklist.
- **`compose`** — mode, density, input length, emoji placed, whether the sensitivity
  guard fired.

Everything is emitted as single-line JSON on stdout. Cloud Run parses that into
queryable `jsonPayload` fields; Modal keeps it as log text. No database.

```bash
# what people searched for and didn't find
gcloud logging read \
  'jsonPayload.component="feedback" AND jsonPayload.event="zero_results"' \
  --limit 50 --format='value(jsonPayload.query)' | sort | uniq -c | sort -rn

# what people said
gcloud logging read \
  'jsonPayload.component="feedback" AND jsonPayload.event="feedback"' \
  --limit 50 --format='value(jsonPayload.rating,jsonPayload.comment)'

# rules vs LLM usage
gcloud logging read 'jsonPayload.event="compose"' \
  --limit 200 --format='value(jsonPayload.mode)' | sort | uniq -c
```

### What is never logged

**Post content is never recorded — only derived facts about it.** People paste real
drafts, including things they would not want stored; the layoff post in the test
suite is exactly that case. A test asserts the post text cannot reach the log.

Search queries are recorded *only* when they returned nothing, truncated to 120
characters. Successful searches, post text and API keys are never logged. There is
no cookie, no third-party analytics and no cross-site identifier — feedback is
rate-limited by IP (5/hour) but the IP itself is not stored.

Set `FEEDBACK_LOGGING=0` to disable all of it. Cloud Logging's default retention is
30 days; for history beyond that, route a sink to BigQuery or swap `emit()` for a
Firestore write.


## API

| Endpoint | Notes |
|---|---|
| `GET /api/search?q=&limit=&related=` | Main search. Pass an emoji as `q` to find similar ones. |
| `POST /api/compose` | `{text, mode: "rules"\|"llm", density: "light"\|"balanced"\|"heavy"}` → post with emoji, per-placement reasons, and `verified` |
| `GET /api/groups` | Category names and counts |
| `GET /api/browse?group=Objects` | Everything in one category |
| `GET /api/token` | Short-lived single-use token required by `mode=llm` |
| `POST /api/feedback` | Thumbs rating plus optional comment; rate-limited per IP |
| `GET /api/health` | Index size, LLM config, and current usage counters |
| `GET /api/docs` | OpenAPI |

```bash
curl -X POST https://hienluu--linkedin-emoji-search-web.modal.run/api/compose \
  -H 'Content-Type: application/json' \
  -d '{"text":"We shipped v2 today.\n\n- Latency down 60%","mode":"rules"}'
```

---

## How it works

### Where the emoji come from

The two LinkedIn articles that prompted this are copy-paste dumps of the standard
Unicode set, so rather than scrape them the dataset is built from the sources they
derive from:

- [`emoji-test.txt`](https://unicode.org/Public/emoji/15.1/emoji-test.txt) — the
  canonical emoji list plus the group/subgroup taxonomy
- CLDR [`annotations`](https://github.com/unicode-org/cldr/tree/main/common/annotations)
  and [`annotationsDerived`](https://github.com/unicode-org/cldr/tree/main/common/annotationsDerived)
  — human-readable names and search keywords

That is a strict superset of both articles: a 344-emoji sample drawn from every
category of both pages — including ZWJ sequences like 👩‍❤️‍💋‍👩 and variation-selector
oddities like ⭐️ vs ⭐ — matches at 344/344.

Result: **1,898 base emoji**, each with CLDR keywords, plus **315** carrying
skin-tone variants (offered as a hover picker rather than 2,000 extra rows of noise).

```bash
uv run build_dataset.py    # re-download sources, rewrite data/emojis.json
```

### Search

CLDR keywords describe what an emoji *depicts* ("rocket: space, launch"), not what a
post author *searches for*. Nothing in Unicode connects "hiring" to 📢. So
`concepts.py` adds a curated professional layer: **52 concepts, 662 aliases**, each
mapping phrases to hand-ordered emoji and to neighbouring concepts.

Ranking, strongest signal first: curated concept → exact name → name token/prefix →
CLDR keyword → subgroup → group. On top of that:

- **IDF weighting**, so `you` or `face` (hundreds of hits) counts far less than `burnout`
- **coverage boost** for emoji matching *every* query token
- **typo tolerance**, with fuzzy matching against the curated layer firing only when a
  token is genuinely unknown — otherwise `pride` gets dragged to `price`
- **country-flag demotion**, so a generic `flag` query returns 🏁 🚩 🏳️ rather than 260 countries

Recommendations combine adjacent concepts, CLDR keyword overlap and shared Unicode
subgroup, excluding anything already shown. Typical query: **~4 ms**, no network calls.

### Composing

`compose.py` segments the post into `hook` / `bullet` / `cta` / `hashtag` / `body`
lines, then scores each eligible line against the concept lexicon and places the best
match above a deliberately high threshold — a bullet with no emoji looks fine, a
bullet with the wrong one looks careless.

Auto-placement only ever draws from the 257 emoji in the curated lexicon. An
unrestricted index will happily answer "a slice of the market" with 🍕. Fuzzy
matching is also off here: a typo guess is fine in a search box and harmful when it
stamps the wrong emoji into someone's post.

---

## Tests

```bash
uv run test_search.py
```

37 ranking checks plus a compose suite, pinning the behaviour that is easy to
regress: that `hiring` returns recruiting emoji rather than a literal match, that
typos still resolve, that recommendations never echo the results, that hashtag lines
and existing emoji are untouched, that density holds, that the tamper check catches
real edits while tolerating legitimate placement, and that a layoff post comes back
bare.

---

## Project layout

```
build_dataset.py   Unicode/CLDR -> data/emojis.json   (run occasionally)
concepts.py        curated LinkedIn vocabulary        (edit this to tune results)
config.py          env-driven LLM config + `uv run config.py` diagnostics
guard.py           rate limits, budget cap and request tokens for LLM mode
feedback.py        usage signals + feedback intake, as structured logs
search.py          inverted index, ranking, recommendations
compose.py         post segmentation + placement, rules and LLM backends
app.py             FastAPI: API + serves the UI
static/index.html  the entire front end, no build step
modal_app.py       Modal deployment
Dockerfile         Cloud Run image
deploy_gcp.sh      Cloud Run deploy (Cloud Build, no local Docker)
.gcloudignore      what gcloud uploads — required, this is not a git repo
test_search.py     ranking + compose regression tests
data/emojis.json   the committed index
```

**Tuning tip:** most result quality lives in `concepts.py`. Adding an alias or
reordering a concept's emoji list changes both search ranking and post placement
immediately — no reindexing, no redeploy of the dataset.

Known rough edge: the rule-based composer still picks 💰 for "scaled past a million
users" (matching *million*) and 🗺️ for "three engineers, one quarter". LLM mode
handles those better; adding aliases narrows the gap.
