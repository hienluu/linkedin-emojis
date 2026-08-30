"""Curated LinkedIn/professional concept lexicon.

Unicode CLDR keywords describe what an emoji *depicts* ("rocket: space, launch"),
not what a LinkedIn writer would *search for* ("shipped", "hiring", "burnout",
"Q3 results"). This file bridges that gap.

Each concept has:
  aliases  - phrases a user might type
  emoji    - hand-picked emoji, best first (order is used as a ranking signal)
  related  - other concept keys, used to power the "you might also like" row
"""

CONCEPTS = {
    # ---- hiring & careers -------------------------------------------------
    "hiring": {
        "aliases": ["hiring", "we are hiring", "were hiring", "now hiring", "recruiting",
                    "recruitment", "job opening", "open role", "open position", "vacancy",
                    "job post", "apply now", "join us", "join our team", "talent"],
        "emoji": ["📢", "🚀", "💼", "🙌", "🎯", "👔", "📩", "🔎", "🤝", "✨", "🧑‍💻", "📌"],
        "related": ["career", "team", "announcement", "opportunity"],
    },
    "career": {
        "aliases": ["career", "new job", "new role", "new chapter", "career change",
                    "promotion", "promoted", "next step", "onboarding", "first day",
                    "resignation", "quit", "laid off", "layoff", "job search", "resume", "cv",
                    "open to work", "open for work", "looking for work", "seeking opportunities",
                    "available for hire", "back on the market"],
        "emoji": ["🎉", "💼", "🚀", "🌱", "🙌", "📈", "🎓", "👔", "✨", "🔑", "🧭", "📝"],
        "related": ["hiring", "milestone", "growth", "gratitude"],
    },
    "opportunity": {
        "aliases": ["opportunity", "opportunities", "chance", "opening", "door", "prospect"],
        "emoji": ["🚪", "🔑", "🌟", "🚀", "🎯", "✨", "🪜", "🧭"],
        "related": ["career", "hiring", "growth"],
    },
    "interview": {
        "aliases": ["interview", "interviewing", "candidate", "screening", "hiring manager"],
        "emoji": ["🎙️", "🤝", "💼", "📋", "🗣️", "👔", "☕", "📝"],
        "related": ["hiring", "career", "conversation"],
    },

    # ---- growth & results -------------------------------------------------
    "growth": {
        "aliases": ["growth", "growing", "scale", "scaling", "increase", "rising", "up and to the right",
                    "revenue growth", "arr", "mrr", "traction", "compound", "momentum"],
        "emoji": ["📈", "🚀", "🌱", "📊", "⬆️", "💹", "🔝", "🌳", "🏔️", "⚡"],
        "related": ["metrics", "success", "milestone", "strategy"],
    },
    "metrics": {
        "aliases": ["metrics", "data", "analytics", "numbers", "kpi", "okr", "dashboard",
                    "report", "results", "stats", "statistics", "measure", "benchmark", "quarterly"],
        "emoji": ["📊", "📈", "📉", "🔢", "🧮", "📋", "🎯", "🔍", "💹", "🗂️"],
        "related": ["growth", "insight", "strategy", "finance"],
    },
    "decline": {
        "aliases": ["decline", "decrease", "drop", "down", "loss", "churn", "downturn",
                    "recession", "shrinking", "falling"],
        "emoji": ["📉", "⬇️", "🔻", "😬", "🥶", "🧊", "⚠️"],
        "related": ["metrics", "challenge", "risk"],
    },
    "success": {
        "aliases": ["success", "win", "winning", "achievement", "accomplished", "nailed it",
                    "crushed it", "record", "best ever", "champion", "victory", "goal reached"],
        "emoji": ["🏆", "🥇", "🎉", "🙌", "🎯", "💪", "⭐", "🔥", "✅", "👏", "🚀"],
        "related": ["celebration", "milestone", "growth", "gratitude"],
    },
    "milestone": {
        "aliases": ["milestone", "anniversary", "work anniversary", "years", "one year",
                    "landmark", "chapter", "first", "1000 customers", "10k followers", "birthday"],
        "emoji": ["🎉", "🎊", "🏁", "🥳", "📅", "🎂", "🏆", "✨", "🚩", "🗓️"],
        "related": ["celebration", "success", "gratitude", "career"],
    },
    "celebration": {
        "aliases": ["celebrate", "celebration", "congrats", "congratulations", "cheers",
                    "party", "well done", "kudos", "shoutout", "proud", "excited", "hooray"],
        "emoji": ["🎉", "🥳", "🎊", "👏", "🙌", "🥂", "🍾", "🎈", "🏆", "✨", "💫", "😍"],
        "related": ["success", "milestone", "gratitude", "team"],
    },

    # ---- product & launches ----------------------------------------------
    "launch": {
        "aliases": ["launch", "launching", "shipped", "shipping", "release", "released",
                    "go live", "live now", "announcing", "introducing", "new product",
                    "beta", "ga", "general availability", "day one", "v1", "out now"],
        "emoji": ["🚀", "🎉", "📣", "✨", "🆕", "🔥", "🎊", "🏁", "🛠️", "📦", "🎁", "⚡"],
        "related": ["announcement", "product", "startup", "celebration"],
    },
    "announcement": {
        "aliases": ["announcement", "announce", "news", "big news", "update", "heads up",
                    "attention", "important", "psa", "sharing", "excited to share", "thrilled to share"],
        "emoji": ["📣", "📢", "🎉", "🚨", "📰", "✨", "🔔", "👉", "📌", "🆕", "‼️"],
        "related": ["launch", "milestone", "media"],
    },
    "product": {
        "aliases": ["product", "feature", "roadmap", "release notes", "product management",
                    "pm", "user experience", "ux", "design", "prototype", "mvp", "backlog"],
        "emoji": ["📦", "🛠️", "🎨", "🧩", "🗺️", "📐", "🖌️", "📱", "💡", "🔧", "📋"],
        "related": ["launch", "engineering", "strategy", "innovation"],
    },
    "startup": {
        "aliases": ["startup", "founder", "founding", "entrepreneur", "entrepreneurship",
                    "bootstrapped", "seed", "series a", "funding", "raised", "vc", "venture capital",
                    "pitch", "unicorn", "yc", "0 to 1"],
        "emoji": ["🚀", "💡", "🦄", "💰", "📈", "🔥", "🧑‍🚀", "🌱", "⚡", "🎯", "🏗️"],
        "related": ["launch", "finance", "innovation", "hustle"],
    },

    # ---- tech -------------------------------------------------------------
    "engineering": {
        "aliases": ["engineering", "engineer", "developer", "dev", "coding", "code", "software",
                    "programming", "build", "building", "deploy", "devops", "infrastructure",
                    "backend", "frontend", "open source", "github", "commit", "refactor"],
        "emoji": ["💻", "🧑‍💻", "⚙️", "🛠️", "🔧", "🐛", "🚀", "📦", "🖥️", "⌨️", "🧱", "🔩"],
        "related": ["product", "ai", "innovation", "debugging"],
    },
    "debugging": {
        "aliases": ["bug", "debug", "debugging", "fix", "fixed", "broken", "outage", "incident",
                    "postmortem", "error", "crash", "hotfix", "on call"],
        "emoji": ["🐛", "🔧", "🚨", "🔥", "🩹", "🔍", "⚠️", "🧯", "💥", "🛠️"],
        "related": ["engineering", "challenge", "learning"],
    },
    "ai": {
        "aliases": ["ai", "artificial intelligence", "machine learning", "ml", "llm", "genai",
                    "generative ai", "model", "neural", "chatbot", "automation", "agent",
                    "data science", "algorithm", "robot"],
        "emoji": ["🤖", "🧠", "✨", "⚡", "🔮", "🧬", "💡", "🕸️", "🖥️", "📊", "🦾"],
        "related": ["engineering", "innovation", "future", "insight"],
    },
    "security": {
        "aliases": ["security", "cybersecurity", "privacy", "encryption", "secure", "breach",
                    "hack", "vulnerability", "compliance", "auth", "password", "protect"],
        "emoji": ["🔒", "🛡️", "🔐", "🔑", "🚨", "🕵️", "⚠️", "🧱", "👁️", "🔓"],
        "related": ["engineering", "risk", "trust"],
    },
    "innovation": {
        "aliases": ["innovation", "innovative", "idea", "ideas", "creativity", "creative",
                    "invention", "breakthrough", "disrupt", "brainstorm", "think different",
                    "lightbulb", "eureka"],
        "emoji": ["💡", "✨", "🧠", "🔬", "🚀", "🎨", "🔮", "⚗️", "🌟", "🧩", "🪄"],
        "related": ["ai", "product", "future", "strategy"],
    },
    "future": {
        "aliases": ["future", "tomorrow", "next decade", "trends", "prediction", "forecast",
                    "vision", "whats next", "2030", "ahead"],
        "emoji": ["🔮", "🚀", "🌅", "🛸", "🧭", "👀", "📡", "🌌", "⏭️", "🌠"],
        "related": ["innovation", "strategy", "ai"],
    },

    # ---- people & culture -------------------------------------------------
    "team": {
        "aliases": ["team", "teamwork", "collaboration", "collaborate", "together", "colleagues",
                    "coworkers", "squad", "crew", "partnership", "partner", "ally", "we"],
        "emoji": ["🤝", "🙌", "👥", "🧑‍🤝‍🧑", "💪", "🫂", "❤️", "🧩", "⚽", "🚣", "🐝"],
        "related": ["leadership", "culture", "celebration", "community"],
    },
    "leadership": {
        "aliases": ["leadership", "leader", "leading", "manager", "management", "ceo", "executive",
                    "boss", "mentor", "mentorship", "coaching", "coach", "direction", "vision"],
        "emoji": ["🧭", "🌟", "🗺️", "🎯", "👑", "🚩", "🦁", "🗣️", "🤝", "🔦", "⛵"],
        "related": ["team", "strategy", "culture", "growth"],
    },
    "culture": {
        "aliases": ["culture", "values", "workplace", "employee experience", "belonging",
                    "psychological safety", "diversity", "inclusion", "dei", "equity", "respect",
                    "pride", "lgbtq", "allyship", "accessibility"],
        "emoji": ["🌈", "🤝", "❤️", "🌍", "🫶", "🏳️‍🌈", "🧩", "🏡", "🌱", "🕊️", "👐", "♿"],
        "related": ["team", "leadership", "wellbeing", "community"],
    },
    "community": {
        "aliases": ["community", "network", "networking", "connections", "meetup", "audience",
                    "followers", "members", "tribe", "circle"],
        "emoji": ["🌐", "👥", "🤝", "🫂", "🌍", "💬", "🔗", "🏘️", "🎪", "🧑‍🤝‍🧑"],
        "related": ["team", "event", "culture", "conversation"],
    },
    "gratitude": {
        "aliases": ["thank you", "thanks", "grateful", "gratitude", "appreciate", "appreciation",
                    "shoutout", "thankful", "honored", "humbled", "blessed"],
        "emoji": ["🙏", "❤️", "🙌", "🫶", "✨", "😊", "💐", "🥰", "👏", "🤗"],
        "related": ["celebration", "team", "kindness"],
    },
    "kindness": {
        "aliases": ["kindness", "kind", "empathy", "compassion", "support", "care", "help",
                    "generous", "pay it forward", "human"],
        "emoji": ["🫶", "❤️", "🤗", "🙏", "🌻", "🤝", "💗", "🕊️", "☀️"],
        "related": ["gratitude", "culture", "wellbeing"],
    },
    "wellbeing": {
        "aliases": ["wellbeing", "well being", "mental health", "burnout", "balance",
                    "work life balance", "rest", "self care", "boundaries", "stress",
                    "vacation", "pto", "time off", "unplug", "recharge",
                    "imposter syndrome", "impostor syndrome", "self doubt", "anxiety",
                    "overwhelmed", "exhausted", "tired"],
        "emoji": ["🧘", "🌿", "☕", "🌅", "😌", "🛌", "🏖️", "🕯️", "🫖", "🌸", "🔋"],
        "related": ["culture", "kindness", "remote"],
    },
    "remote": {
        "aliases": ["remote", "remote work", "wfh", "work from home", "hybrid", "distributed",
                    "zoom", "video call", "async", "office", "return to office", "rto", "commute"],
        "emoji": ["🏡", "💻", "🎧", "📹", "☕", "🌍", "🖥️", "🗓️", "🪑", "✈️"],
        "related": ["wellbeing", "team", "productivity"],
    },

    # ---- work practice ----------------------------------------------------
    "productivity": {
        "aliases": ["productivity", "efficient", "efficiency", "focus", "deep work", "getting things done",
                    "gtd", "workflow", "process", "organized", "checklist", "todo", "done", "shipping fast"],
        "emoji": ["✅", "⚡", "🎯", "📋", "⏱️", "🗓️", "🧠", "🔁", "☑️", "📌", "🚀"],
        "related": ["strategy", "time", "engineering"],
    },
    "time": {
        "aliases": ["time", "deadline", "schedule", "calendar", "urgent", "asap", "clock",
                    "timeline", "on time", "late", "waiting", "soon", "countdown"],
        "emoji": ["⏰", "⏳", "🗓️", "⌛", "🕐", "⏱️", "📅", "🚦", "🔜", "⌚"],
        "related": ["productivity", "planning"],
    },
    "planning": {
        "aliases": ["planning", "plan", "roadmap", "strategy session", "prep", "preparation",
                    "blueprint", "outline", "agenda", "next steps", "quarter", "q1", "q2", "q3", "q4"],
        "emoji": ["🗺️", "📋", "🧭", "📐", "🗓️", "🧩", "📌", "✏️", "🏗️", "🎯"],
        "related": ["strategy", "productivity", "time"],
    },
    "strategy": {
        "aliases": ["strategy", "strategic", "positioning", "competitive", "moat", "playbook",
                    "chess", "decision", "tradeoff", "prioritize", "bet", "north star"],
        "emoji": ["♟️", "🧭", "🎯", "🗺️", "🧠", "⚖️", "🔭", "🪜", "🧩", "🎲"],
        "related": ["leadership", "planning", "growth", "insight"],
    },
    "insight": {
        "aliases": ["insight", "lesson", "lessons learned", "takeaway", "key takeaway", "realized",
                    "aha", "perspective", "observation", "reflection", "food for thought", "hot take"],
        "emoji": ["💡", "🔍", "🧠", "👀", "🪞", "📖", "🔦", "🧵", "☝️", "✨"],
        "related": ["learning", "innovation", "strategy"],
    },
    "learning": {
        "aliases": ["learning", "learn", "education", "course", "training", "certification",
                    "certified", "study", "student", "book", "reading", "skill", "upskill",
                    "graduated", "degree", "workshop", "curious"],
        "emoji": ["📚", "🎓", "🧠", "📖", "✏️", "🔬", "🌱", "💡", "🧑‍🏫", "📝", "🤓"],
        "related": ["insight", "career", "growth"],
    },
    "conversation": {
        "aliases": ["conversation", "discussion", "comment", "comments", "thoughts", "opinion",
                    "feedback", "question", "ask me anything", "ama", "poll", "your take",
                    "let me know", "reply", "dm", "message"],
        "emoji": ["💬", "🗣️", "💭", "❓", "👇", "📩", "🤔", "🙋", "📝", "🔁"],
        "related": ["community", "insight", "interview"],
    },
    "challenge": {
        "aliases": ["challenge", "hard", "difficult", "struggle", "obstacle", "setback", "failure",
                    "failed", "mistake", "tough", "uphill", "grind", "roadblock", "problem"],
        "emoji": ["⛰️", "🧗", "💪", "🥊", "🌊", "🚧", "🔥", "🪨", "😤", "🛤️"],
        "related": ["resilience", "learning", "hustle"],
    },
    "resilience": {
        "aliases": ["resilience", "resilient", "perseverance", "persistence", "grit", "comeback",
                    "bounce back", "keep going", "never give up", "endurance", "rebuild"],
        "emoji": ["💪", "🧗", "🌱", "🔁", "🦾", "🏋️", "🐢", "🌅", "⚓", "🪴"],
        "related": ["challenge", "growth", "motivation"],
    },
    "motivation": {
        "aliases": ["motivation", "motivated", "inspire", "inspiration", "monday", "mindset",
                    "energy", "drive", "passion", "lets go", "you got this", "believe"],
        "emoji": ["🔥", "🚀", "💪", "⚡", "🌟", "☀️", "🎯", "🙌", "💥", "🏃"],
        "related": ["hustle", "resilience", "success"],
    },
    "hustle": {
        "aliases": ["hustle", "hard work", "grind", "side project", "late night", "coffee",
                    "busy", "sprint", "crunch", "putting in the work"],
        "emoji": ["☕", "🔥", "💻", "🌙", "⚡", "🏃", "💪", "🛠️", "📈", "🥱"],
        "related": ["motivation", "productivity", "startup"],
    },

    # ---- business ---------------------------------------------------------
    "finance": {
        "aliases": ["finance", "money", "revenue", "profit", "budget", "cost", "pricing", "price",
                    "investment", "investor", "roi", "cash", "salary", "compensation", "equity",
                    "valuation", "economics", "billing"],
        "emoji": ["💰", "💵", "📊", "💳", "🏦", "📈", "🪙", "💎", "⚖️", "🧾", "💸"],
        "related": ["metrics", "startup", "strategy"],
    },
    "sales": {
        "aliases": ["sales", "selling", "deal", "closed won", "pipeline", "quota", "prospecting",
                    "customer", "client", "crm", "outreach", "cold email", "negotiation"],
        "emoji": ["🤝", "📞", "💰", "🎯", "📈", "🏆", "✍️", "📩", "🔔", "🥂"],
        "related": ["marketing", "finance", "growth"],
    },
    "marketing": {
        "aliases": ["marketing", "brand", "branding", "campaign", "content", "seo", "social media",
                    "advertising", "ads", "storytelling", "positioning", "copywriting", "newsletter"],
        "emoji": ["📣", "🎯", "✨", "📝", "🎨", "📱", "🔊", "🧲", "📊", "🌐"],
        "related": ["sales", "media", "announcement"],
    },
    "media": {
        "aliases": ["media", "podcast", "webinar", "video", "youtube", "blog", "article", "press",
                    "interview feature", "publication", "newsletter", "livestream", "recording"],
        "emoji": ["🎙️", "📹", "📰", "🎧", "📺", "🎬", "🔴", "📻", "✍️", "📸"],
        "related": ["marketing", "announcement", "event"],
    },
    "event": {
        "aliases": ["event", "conference", "summit", "keynote", "speaking", "speaker", "panel",
                    "talk", "workshop", "booth", "meetup", "hackathon", "roadshow", "expo"],
        "emoji": ["🎤", "🎟️", "📅", "🗣️", "🎪", "🌍", "👥", "📸", "🏟️", "✈️"],
        "related": ["community", "media", "travel"],
    },
    "travel": {
        "aliases": ["travel", "flight", "flying", "trip", "airport", "hotel", "abroad",
                    "on the road", "visiting", "landed", "destination"],
        "emoji": ["✈️", "🌍", "🧳", "🗺️", "🏨", "🚕", "📍", "🛫", "🚄", "🏝️"],
        "related": ["event", "remote"],
    },
    "risk": {
        "aliases": ["risk", "warning", "caution", "danger", "careful", "red flag", "threat",
                    "uncertainty", "beware", "alert"],
        "emoji": ["⚠️", "🚩", "🚨", "🛑", "⛔", "🎲", "🧊", "👀", "🔥", "🪤"],
        "related": ["security", "decline", "challenge"],
    },
    "trust": {
        "aliases": ["trust", "integrity", "honest", "honesty", "transparency", "transparent",
                    "authentic", "credibility", "reliable", "promise"],
        "emoji": ["🤝", "🫂", "🛡️", "✅", "🔒", "❤️", "🪞", "⚖️", "🕊️"],
        "related": ["culture", "leadership", "security"],
    },
    "sustainability": {
        "aliases": ["sustainability", "sustainable", "climate", "green", "environment", "esg",
                    "carbon", "renewable", "planet", "eco", "recycle"],
        "emoji": ["🌱", "🌍", "♻️", "🌳", "☀️", "💧", "🍃", "🔋", "🌊", "🐝"],
        "related": ["future", "culture"],
    },
    "health": {
        "aliases": ["health", "healthcare", "medical", "doctor", "nurse", "hospital", "patient",
                    "medicine", "fitness", "exercise", "wellness", "gym", "running"],
        "emoji": ["🩺", "❤️", "🏥", "💊", "🏃", "🧘", "🥗", "💪", "🧑‍⚕️", "🫀"],
        "related": ["wellbeing", "science"],
    },
    "science": {
        "aliases": ["science", "research", "study", "experiment", "lab", "hypothesis", "paper",
                    "biology", "chemistry", "physics", "space", "discovery"],
        "emoji": ["🔬", "🧪", "🧬", "🔭", "🧫", "📄", "🚀", "⚛️", "🌌", "🧑‍🔬"],
        "related": ["learning", "innovation", "ai"],
    },

    # ---- formatting helpers ----------------------------------------------
    "bullet": {
        "aliases": ["bullet", "bullets", "bullet point", "list", "divider", "separator",
                    "arrow", "pointer", "checkbox", "tick", "check"],
        "emoji": ["✅", "▪️", "🔹", "▶️", "➡️", "👉", "✔️", "🔸", "◾", "⭐", "1️⃣", "✳️"],
        "related": ["productivity", "announcement"],
    },
    "attention": {
        "aliases": ["attention", "look here", "read this", "point down", "swipe", "scroll",
                    "click", "link in comments", "below", "important note"],
        "emoji": ["👇", "👀", "📌", "🚨", "⬇️", "☝️", "🔗", "❗", "📍", "👉"],
        "related": ["announcement", "conversation", "bullet"],
    },
}


def build_lookup():
    """Return (alias -> concept_key) and (emoji -> [(concept_key, rank)])."""
    alias_to_concept = {}
    emoji_to_concepts = {}
    for key, c in CONCEPTS.items():
        for alias in [key] + c["aliases"]:
            alias_to_concept[alias.lower()] = key
        for rank, ch in enumerate(c["emoji"]):
            emoji_to_concepts.setdefault(ch, []).append((key, rank))
    return alias_to_concept, emoji_to_concepts
