"""Build the emoji dataset from authoritative Unicode sources.

Sources (downloaded once into data/raw/):
  - unicode.org emoji-test.txt   -> the canonical emoji list, group/subgroup taxonomy
  - CLDR common/annotations/en.xml -> search keywords + short names
  - CLDR common/annotationsDerived/en.xml -> names for ZWJ / modifier sequences

Output: data/emojis.json

Run:  python build_dataset.py
"""

import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "emojis.json"

SOURCES = {
    "emoji-test.txt": "https://unicode.org/Public/emoji/15.1/emoji-test.txt",
    "annotations.xml": "https://raw.githubusercontent.com/unicode-org/cldr/main/common/annotations/en.xml",
    "annotationsDerived.xml": "https://raw.githubusercontent.com/unicode-org/cldr/main/common/annotationsDerived/en.xml",
}

SKIN_TONES = {
    "\U0001F3FB": "light",
    "\U0001F3FC": "medium-light",
    "\U0001F3FD": "medium",
    "\U0001F3FE": "medium-dark",
    "\U0001F3FF": "dark",
}

# Emoji whose glyphs render as text-style (or not at all) in many places, or that
# are noise in a LinkedIn-post context.
SKIP_GROUPS = {"Component"}


def download():
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        dest = RAW / name
        if dest.exists():
            continue
        print(f"downloading {name} ...")
        with urllib.request.urlopen(url) as r:
            dest.write_bytes(r.read())


def parse_annotations(path):
    """Return {emoji: {"keywords": [...], "name": str}}."""
    out = {}
    root = ET.parse(path).getroot()
    for ann in root.iter("annotation"):
        cp = ann.get("cp")
        text = (ann.text or "").strip()
        entry = out.setdefault(cp, {"keywords": [], "name": None})
        if ann.get("type") == "tts":
            entry["name"] = text
        else:
            entry["keywords"] = [k.strip() for k in text.split("|") if k.strip()]
    return out


LINE_RE = re.compile(
    r"^(?P<codes>[0-9A-F ]+?)\s*;\s*(?P<status>[\w-]+)\s*#\s*(?P<emoji>\S+)\s+E(?P<version>[\d.]+)\s+(?P<name>.+)$"
)


def parse_emoji_test(path):
    """Yield dicts for every fully-qualified emoji, tagged with group/subgroup."""
    group = subgroup = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# group:"):
            group = line.split(":", 1)[1].strip()
            continue
        if line.startswith("# subgroup:"):
            subgroup = line.split(":", 1)[1].strip()
            continue
        if not line or line.startswith("#"):
            continue
        m = LINE_RE.match(line)
        if not m or m.group("status") != "fully-qualified":
            continue
        if group in SKIP_GROUPS:
            continue
        yield {
            "char": m.group("emoji"),
            "unicode_name": m.group("name"),
            "group": group,
            "subgroup": subgroup,
            "version": float(m.group("version")),
            "codepoints": m.group("codes").split(),
        }


def build():
    download()
    base_ann = parse_annotations(RAW / "annotations.xml")
    derived_ann = parse_annotations(RAW / "annotationsDerived.xml")

    def lookup(char):
        """CLDR keys sometimes omit the U+FE0F variation selector; try both."""
        for table in (base_ann, derived_ann):
            for key in (char, char.replace("️", "")):
                if key in table:
                    return table[key]
        return {"keywords": [], "name": None}

    records = []
    tone_variants = {}  # base char -> {tone: char}

    for e in parse_emoji_test(RAW / "emoji-test.txt"):
        char = e["char"]
        tones_in = [t for t in SKIN_TONES if t in char]
        if tones_in:
            # Register as a variant of its tone-less base rather than its own entry.
            base = char
            for t in tones_in:
                base = base.replace(t, "")
            tone_variants.setdefault(base, {})[SKIN_TONES[tones_in[0]]] = char
            continue

        ann = lookup(char)
        name = ann["name"] or e["unicode_name"]
        keywords = sorted({k.lower() for k in ann["keywords"]})
        records.append(
            {
                "char": char,
                "name": name,
                "keywords": keywords,
                "group": e["group"],
                "subgroup": e["subgroup"].replace("-", " "),
                "version": e["version"],
            }
        )

    # Attach skin tone variants. The tone-less base of a ZWJ sequence may itself be
    # non-RGI (e.g. some profession sequences), so only attach where a base exists.
    by_char = {r["char"]: r for r in records}
    attached = 0
    for base, variants in tone_variants.items():
        rec = by_char.get(base) or by_char.get(base + "️") or by_char.get(base.replace("️", ""))
        if rec:
            rec["tones"] = {k: variants[k] for k in SKIN_TONES.values() if k in variants}
            attached += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")

    groups = {}
    for r in records:
        groups[r["group"]] = groups.get(r["group"], 0) + 1
    print(f"wrote {len(records)} emoji to {OUT.relative_to(ROOT)}")
    print(f"  skin-tone variant sets attached: {attached}")
    for g, n in sorted(groups.items(), key=lambda kv: -kv[1]):
        print(f"  {n:>5}  {g}")
    missing = [r["char"] for r in records if not r["keywords"]]
    print(f"  entries with no CLDR keywords: {len(missing)}")


if __name__ == "__main__":
    build()
