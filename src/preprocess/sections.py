"""Split a job description into canonical sections using each company's heading styles.

Headings were catalogued from the corpus on 2026-11-09 (see docs/sprints/sprint-03-nlp-preprocessing.md).
They work both on line-structured text (Anthropic, OpenAI, Google) and on flattened text
where headings appear inline after a sentence, e.g. "... deployment. What you'll be doing: ..."
(NVIDIA's JSON-LD descriptions).

Canonical sections:
    intro             text before the first recognised heading (usually team/role pitch)
    about             "About the role / team / job"
    responsibilities  what the person will do
    requirements      minimum / required qualifications
    preferred         nice-to-haves
    boilerplate       company description, logistics, pay, benefits, legal (dropped from clean text)
"""

from __future__ import annotations

import re

# (regex for the heading text, canonical section). Apostrophes are normalised to ' beforehand.
_HEADINGS: list[tuple[str, str]] = [
    # --- responsibilities
    (r"(?:key |core |primary )?responsibilities", "responsibilities"),
    (r"in this role,? you(?:'ll| will)(?: get to)?", "responsibilities"),
    (r"what you(?:'ll| will) (?:be )?do(?:ing)?", "responsibilities"),
    (r"you(?:'ll| will) be responsible for", "responsibilities"),
    (r"representative projects", "responsibilities"),
    (r"the role", "responsibilities"),
    (r"what success looks like", "responsibilities"),
    # --- requirements
    (r"(?:minimum |basic |required )?qualifications", "requirements"),
    (r"requirements", "requirements"),
    (r"what we need to see", "requirements"),
    (r"you(?:'ll| will| might| may)? (?:thrive|be a (?:good|great|strong) fit)(?: in this role)? if you(?: have)?(?: experience (?:with|in))?",
     "requirements"),
    (r"we(?:'re| are) (?:seeking|looking for) someone with(?: experience including)?", "requirements"),
    (r"your background might look something like", "requirements"),
    (r"who you are", "requirements"),
    # --- preferred
    (r"preferred (?:qualifications|skills|experience)", "preferred"),
    (r"strong candidates may (?:also )?have(?: experience (?:with|in))?", "preferred"),
    (r"strong candidates may also", "preferred"),
    (r"nice[ -]to[ -]haves?", "preferred"),
    (r"ways to stand out from the crowd", "preferred"),
    (r"bonus points(?: if you have)?", "preferred"),
    (r"candidates need not have", "preferred"),
    # --- about the role/team (kept)
    (r"about the (?:role|team|job|position|opportunity)", "about"),
    (r"what makes this role unique", "about"),
    # --- boilerplate (dropped)
    (r"about (?:anthropic|openai|nvidia|google|us|the company)", "boilerplate"),
    (r"logistics", "boilerplate"),
    (r"(?:annual |base )?salary(?: range)?", "boilerplate"),
    (r"compensation(?:,? (?:and|&) benefits)?", "boilerplate"),
    (r"benefits", "boilerplate"),
    (r"what we offer", "boilerplate"),
    (r"workplace (?:&|and) location", "boilerplate"),
    (r"visa sponsorship", "boilerplate"),
    (r"deadline to apply", "boilerplate"),
    (r"location-based hybrid policy", "boilerplate"),
    (r"role specific location policy", "boilerplate"),
    (r"guidance on candidates' ai usage", "boilerplate"),
    (r"minimum education", "boilerplate"),
    (r"required field of study", "boilerplate"),
    (r"minimum years of experience", "boilerplate"),
    (r"how we're different", "boilerplate"),
    (r"equal (?:employment )?opportunity", "boilerplate"),
    (r"the expected base salary ranges? for this position (?:is|are)", "boilerplate"),
    (r"your base salary will be determined[^:\n]{0,80}", "boilerplate"),
]

# Longest patterns first so "you may be a good fit if you have" beats "... if you".
_HEADINGS.sort(key=lambda h: len(h[0]), reverse=True)
_SECTION_OF = {}
_alts = []
for i, (pat, sec) in enumerate(_HEADINGS):
    _alts.append(f"(?P<h{i}>{pat})")
    _SECTION_OF[f"h{i}"] = sec

# Inline mode: multi-word headings may also follow any whitespace if they end with ':'
# (NVIDIA bullets often lack a full stop: "...GPUs) What we need to see: ...").
_inline_alts = []
for i, (pat, sec) in enumerate(_HEADINGS):
    if " " in pat and len(pat) > 12:
        _inline_alts.append(f"(?P<i{i}>{pat})")
        _SECTION_OF[f"i{i}"] = sec

# A heading must start a line or follow a sentence end, and be followed by ':' or a line break.
HEADING_RE = re.compile(
    r"(?:(?:^|(?<=[.!?] )|(?<=[.!?]\n)|(?<=\n))[ \t]*(?:" + "|".join(_alts) + r")[ \t]*(?::|\n|$))"
    r"|(?:(?<=\s)(?:" + "|".join(_inline_alts) + r"):)",
    re.IGNORECASE | re.MULTILINE,
)

SECTIONS = ["intro", "about", "responsibilities", "requirements", "preferred", "boilerplate"]


def split_sections(text: str) -> dict[str, str]:
    out = {s: [] for s in SECTIONS}
    pos, current = 0, "intro"
    for m in HEADING_RE.finditer(text):
        chunk = text[pos:m.start()].strip()
        if chunk:
            out[current].append(chunk)
        current = _SECTION_OF[m.lastgroup]
        pos = m.end()
    tail = text[pos:].strip()
    if tail:
        out[current].append(tail)
    return {s: "\n".join(v).strip() for s, v in out.items()}
