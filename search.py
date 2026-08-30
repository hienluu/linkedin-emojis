"""Emoji search + recommendation engine.

Pure stdlib on purpose: the whole index is ~1900 emoji, so an inverted index with
weighted fields beats an embedding model here on latency, cold-start and cost.

Ranking signals, strongest to weakest:
  1. curated concept match  (query "hiring" -> the emoji a recruiter actually wants)
  2. exact emoji name match
  3. name token match / prefix
  4. CLDR keyword match / prefix
  5. subgroup, then group
  6. fuzzy token match (typo tolerance), scored at a discount
Emoji matching *every* query token are boosted over partial matches.
"""

import difflib
import json
import math
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from concepts import CONCEPTS, build_lookup

DATA = Path(__file__).parent / "data" / "emojis.json"

# Variation selector: article text and user input are inconsistent about it, so
# every char is matched on its stripped form.
VS16 = "️"

W_CONCEPT = 60.0
W_NAME_EXACT = 100.0
W_NAME_TOKEN = 30.0
W_NAME_PREFIX = 14.0
W_KEYWORD_EXACT = 22.0
W_KEYWORD_TOKEN = 16.0
W_KEYWORD_PREFIX = 7.0
W_SUBGROUP = 5.0
W_GROUP = 3.0
FUZZY_DISCOUNT = 0.45
FUZZY_CUTOFF = 0.78

# Emoji that carry well in a professional feed. Used only as a tie-breaker so
# that e.g. "star" surfaces ⭐ before 🌠.
COMMON = list("🎉🔥🚀💡✅❤️👏🙌🤝📈📊🎯💪✨⭐🙏👍💯📣📌🧠💻🌱🏆🎓💼📝🔍⚡🌍☕🧵👀🤔😊🥳")


def norm_char(ch):
    return ch.replace(VS16, "")


def tokenize(text):
    text = unicodedata.normalize("NFKD", text.lower())
    return [t for t in re.split(r"[^a-z0-9À-ɏ]+", text) if t]


class EmojiIndex:
    def __init__(self, path=DATA):
        self.records = json.loads(Path(path).read_text(encoding="utf-8"))
        self.alias_to_concept, emoji_to_concepts = build_lookup()
        self._alias_list = list(self.alias_to_concept)

        self.by_norm = {}
        for i, r in enumerate(self.records):
            r["id"] = i
            r["concepts"] = []
            self.by_norm.setdefault(norm_char(r["char"]), i)

        # Attach curated concepts, and report any curated char that isn't a real
        # emoji so the lexicon can't silently rot.
        self.unknown_concept_chars = []
        for ch, pairs in emoji_to_concepts.items():
            idx = self.by_norm.get(norm_char(ch))
            if idx is None:
                self.unknown_concept_chars.append(ch)
                continue
            for key, rank in pairs:
                self.records[idx]["concepts"].append({"key": key, "rank": rank})

        self._build_postings()
        self._common = {norm_char(c) for c in COMMON}

    # ------------------------------------------------------------------ index
    def _build_postings(self):
        self.postings = defaultdict(dict)  # token -> {emoji_id: weight}
        self.name_exact = {}               # full name -> emoji_id
        self.keyword_sets = []             # emoji_id -> set of keywords
        self.by_subgroup = defaultdict(list)

        def add(token, idx, weight):
            p = self.postings[token]
            if p.get(idx, 0) < weight:
                p[idx] = weight

        for r in self.records:
            idx = r["id"]
            name = r["name"].lower()
            self.name_exact.setdefault(name, idx)

            for t in tokenize(name):
                add(t, idx, W_NAME_TOKEN)
                for n in range(3, len(t)):
                    add(t[:n], idx, W_NAME_PREFIX)

            kws = set()
            for kw in r["keywords"]:
                kws.add(kw)
                add(kw, idx, W_KEYWORD_EXACT)
                for t in tokenize(kw):
                    add(t, idx, W_KEYWORD_TOKEN)
                    for n in range(3, len(t)):
                        add(t[:n], idx, W_KEYWORD_PREFIX)
            self.keyword_sets.append(kws)

            for t in tokenize(r["subgroup"]):
                add(t, idx, W_SUBGROUP)
            for t in tokenize(r["group"]):
                add(t, idx, W_GROUP)

            self.by_subgroup[r["subgroup"]].append(idx)

        self.vocab = list(self.postings.keys())

        # Inverse document frequency: a token like "you" or "face" hits hundreds of
        # emoji and says little about intent; "burnout" or "abacus" says a lot.
        n = len(self.records)
        self.idf = {}
        for token, posting in self.postings.items():
            df = len(posting)
            self.idf[token] = min(1.5, max(0.12, math.log(n / (1 + df)) / math.log(n / 2)))

    # ----------------------------------------------------------------- search
    def _concept_matches(self, query, allow_fuzzy=True):
        """Longest-first n-gram match of the query against curated aliases."""
        tokens = tokenize(query)
        hits = {}
        n = len(tokens)
        for size in range(min(n, 5), 0, -1):
            for start in range(n - size + 1):
                phrase = " ".join(tokens[start:start + size])
                key = self.alias_to_concept.get(phrase)
                if key:
                    # Longer phrase match = more specific = higher confidence.
                    hits[key] = max(hits.get(key, 0), size / max(n, 1))

        if hits or not allow_fuzzy:
            return hits
        # Nothing matched exactly — a typo shouldn't cost the user the curated
        # layer, which is where most of the useful ranking lives.
        for phrase in (" ".join(tokens), *tokens):
            for cand in difflib.get_close_matches(phrase, self._alias_list, n=2, cutoff=FUZZY_CUTOFF):
                key = self.alias_to_concept[cand]
                score = len(tokenize(cand)) / max(n, 1) * FUZZY_DISCOUNT
                hits[key] = max(hits.get(key, 0), score)
            if hits:
                break
        return hits

    def search(self, query, limit=60, fuzzy=True):
        query = (query or "").strip()
        if not query:
            return [], {}

        # An emoji pasted straight into the box means "find me things like this".
        direct = self.by_norm.get(norm_char(query))
        if direct is not None:
            return [self._render(direct, W_NAME_EXACT)], {}

        scores = defaultdict(float)
        matched_tokens = defaultdict(set)
        tokens = tokenize(query)

        # Only guess at concepts fuzzily when a token is genuinely unknown to the
        # index; otherwise "pride" would get dragged to "price" -> finance.
        has_typo = fuzzy and any(t not in self.postings for t in tokens)
        concept_hits = self._concept_matches(query, allow_fuzzy=has_typo)
        for key, confidence in concept_hits.items():
            emojis = CONCEPTS[key]["emoji"]
            for rank, ch in enumerate(emojis):
                idx = self.by_norm.get(norm_char(ch))
                if idx is None:
                    continue
                decay = 1.0 - (rank / (len(emojis) + 2))
                scores[idx] += W_CONCEPT * confidence * decay
                matched_tokens[idx].update(tokens)

        exact = self.name_exact.get(" ".join(tokens))
        if exact is not None:
            scores[exact] += W_NAME_EXACT
            matched_tokens[exact].update(tokens)

        for t in tokens:
            posting = self.postings.get(t)
            if posting:
                idf = self.idf.get(t, 1.0)
                for idx, w in posting.items():
                    scores[idx] += w * idf
                    matched_tokens[idx].add(t)
                continue
            if not fuzzy:
                continue
            # Unknown token: typo-tolerant fallback.
            for cand in difflib.get_close_matches(t, self.vocab, n=3, cutoff=FUZZY_CUTOFF):
                idf = self.idf.get(cand, 1.0)
                for idx, w in self.postings[cand].items():
                    scores[idx] += w * idf * FUZZY_DISCOUNT
                    matched_tokens[idx].add(t)

        if not scores:
            return [], concept_hits

        # Reward emoji that match the whole query, not just one word of it.
        n_tokens = max(len(tokens), 1)
        ranked = []
        for idx, base in scores.items():
            coverage = len(matched_tokens[idx]) / n_tokens
            score = base * (0.35 + 0.65 * coverage) ** 2 * (2.0 if coverage == 1 else 1.0)
            rec = self.records[idx]
            if norm_char(rec["char"]) in self._common:
                score *= 1.08
            score *= 1.0 + max(0.0, (3.0 - rec["version"])) * 0.01
            # There are 260+ country flags, all named "flag: <country>". Without this
            # a generic "flag" query buries 🏁 and 🚩 under a wall of countries.
            if rec["subgroup"] == "country flag" and matched_tokens[idx] <= {"flag", "flags"}:
                score *= 0.5
            ranked.append((score, idx))

        ranked.sort(key=lambda si: (-si[0], len(self.records[si[1]]["name"])))
        return [self._render(i, s) for s, i in ranked[:limit]], concept_hits

    # -------------------------------------------------------- recommendations
    def recommend(self, query, results, concept_hits, limit=12):
        """'You might also like' — related concepts + keyword/subgroup neighbours."""
        seen = {r["id"] for r in results[:40]}
        scores = defaultdict(float)

        # 1. Concepts adjacent to the ones the query hit.
        for key, confidence in concept_hits.items():
            for rel in CONCEPTS[key]["related"]:
                rel_emoji = CONCEPTS.get(rel, {}).get("emoji", [])
                for rank, ch in enumerate(rel_emoji):
                    idx = self.by_norm.get(norm_char(ch))
                    if idx is not None and idx not in seen:
                        scores[idx] += 30.0 * confidence * (1.0 - rank / (len(rel_emoji) + 2))

        # 2. Neighbours of the strongest results, by shared CLDR keywords and by
        #    sharing a Unicode subgroup (a decent "same kind of thing" signal).
        for rank, r in enumerate(results[:6]):
            weight = 1.0 - rank / 8.0
            src_kws = self.keyword_sets[r["id"]]
            for idx in self.by_subgroup[r["subgroup"]]:
                if idx not in seen:
                    scores[idx] += 4.0 * weight
            if src_kws:
                for kw in src_kws:
                    for idx in self.postings.get(kw, {}):
                        if idx in seen or idx == r["id"]:
                            continue
                        overlap = len(src_kws & self.keyword_sets[idx])
                        if overlap >= 2:
                            scores[idx] += 5.0 * weight * overlap / len(src_kws)

        # 3. Concepts the top results themselves belong to (query may have been
        #    literal, e.g. "rocket", but the user is probably writing about launches).
        for rank, r in enumerate(results[:5]):
            for c in self.records[r["id"]]["concepts"]:
                for crank, ch in enumerate(CONCEPTS[c["key"]]["emoji"]):
                    idx = self.by_norm.get(norm_char(ch))
                    if idx is not None and idx not in seen:
                        scores[idx] += 12.0 * (1.0 - rank / 6.0) * (1.0 - crank / 14.0)

        for idx in list(scores):
            if norm_char(self.records[idx]["char"]) in self._common:
                scores[idx] *= 1.2

        ranked = sorted(scores.items(), key=lambda kv: -kv[1])[:limit]
        return [self._render(i, s) for i, s in ranked]

    # ----------------------------------------------------------------- output
    def _render(self, idx, score):
        r = self.records[idx]
        return {
            "id": idx,
            "char": r["char"],
            "name": r["name"],
            "keywords": r["keywords"][:8],
            "group": r["group"],
            "subgroup": r["subgroup"],
            "tones": r.get("tones"),
            "concepts": [c["key"] for c in r["concepts"]],
            "score": round(score, 2),
        }

    def query(self, q, limit=60, rec_limit=12):
        results, concept_hits = self.search(q, limit=limit)
        return {
            "query": q,
            "count": len(results),
            "concepts": sorted(concept_hits, key=lambda k: -concept_hits[k]),
            "results": results,
            "related": self.recommend(q, results, concept_hits, limit=rec_limit),
        }

    def groups(self):
        out = defaultdict(int)
        for r in self.records:
            out[r["group"]] += 1
        return dict(out)

    def browse(self, group, limit=500):
        return [self._render(r["id"], 0) for r in self.records if r["group"] == group][:limit]


_index = None


def get_index():
    global _index
    if _index is None:
        _index = EmojiIndex()
    return _index
