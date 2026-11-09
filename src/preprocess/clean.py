"""Text cleaning steps for job descriptions."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

# ---------------------------------------------------------------- normalisation

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-",
                         "—": "-", "•": "\n", " ": " ", "​": ""})
_URL = re.compile(r"https?://\S+|www\.\S+")
_SPACES = re.compile(r"[ \t\f\v]+")
_BLANKS = re.compile(r"\n\s*\n+")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").translate(_QUOTES)
    text = _URL.sub(" ", text)
    text = _SPACES.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return _BLANKS.sub("\n", text).strip()


# ---------------------------------------------------------------- sentences & boilerplate

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"(])|\n+")


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text) if s and s.strip()]


def _key(sentence: str) -> str:
    return re.sub(r"\W+", " ", sentence.lower()).strip()


def frequent_sentences(docs: list[str], min_share: float = 0.03, min_count: int = 5) -> set[str]:
    """Sentences that recur across many postings of the same company (templated text)."""
    counts: Counter[str] = Counter()
    for d in docs:
        counts.update({_key(s) for s in sentences(d) if len(s) > 25})
    threshold = max(min_count, int(min_share * len(docs)))
    return {k for k, c in counts.items() if c >= threshold}


_LEGAL_CUE = re.compile(
    r"equal (?:employment )?opportunit|discriminat|accommodation|salary|compensation|benefits|equity|"
    r"applications? (?:for|will)|privacy|visa|background check|employer|diverse|e-verify|recruiters?",
    re.I,
)


_REQUIREMENT_LIKE = re.compile(
    r"\b(?:degree|bachelor|master|ph\.?d|years?|experience|proficien\w*|knowledge|skills?|familiar\w*|"
    r"ability|understanding|expertise|fluen\w*)\b",
    re.I,
)


def drop_boilerplate(text: str, frequent: set[str], company: str, strict: bool) -> str:
    """Remove templated sentences.

    strict=True (intro/about sections): drop any frequent sentence.
    strict=False (role sections): drop a frequent sentence if it mentions the company or a
    legal/pay cue, or doesn't read like a requirement. Common *requirements* such as
    "Bachelor's degree or equivalent practical experience." survive.
    """
    keep = []
    for s in sentences(text):
        if _key(s) in frequent and (
            strict
            or company.lower() in s.lower()
            or _LEGAL_CUE.search(s)
            or not _REQUIREMENT_LIKE.search(s)
        ):
            continue
        keep.append(s)
    return "\n".join(keep)


# ---------------------------------------------------------------- salary

_NUM = r"(\d{2,3}(?:,\d{3})+(?:\.\d+)?|\d{2,3}(?:\.\d+)?\s?[kK])"
_SALARY = re.compile(
    r"\$\s?" + _NUM + r"\s*(?:USD)?\s*(?:-|to)\s*\$?\s?" + _NUM
    + r"|" + _NUM + r"\s*USD\s*(?:-|to)\s*" + _NUM + r"\s*USD",
)


def _to_number(s: str) -> float:
    s = s.replace(",", "").strip()
    return float(s[:-1]) * 1000 if s[-1] in "kK" else float(s)


def extract_salary(*texts: str) -> tuple[float | None, float | None]:
    """Min and max annual USD figures across all ranges found (multi-location postings list several)."""
    lows, highs = [], []
    for t in texts:
        for m in _SALARY.finditer(normalize(t or "")):  # normalise en dashes etc.
            a, b = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
            lo, hi = _to_number(a), _to_number(b)
            if 20_000 <= lo <= hi <= 2_000_000:
                lows.append(lo)
                highs.append(hi)
    return (min(lows), max(highs)) if lows else (None, None)


# ---------------------------------------------------------------- tokens (spaCy)

PROTECTED = ["C++", "C#", "F#", ".NET", "Node.js", "Next.js", "Vue.js", "CI/CD", "A/B", "R&D", "ML/AI", "AI/ML"]
KEEP_SINGLE = {"c", "r"}


def load_nlp():
    import spacy

    nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
    for term in PROTECTED:
        nlp.tokenizer.add_special_case(term, [{"ORTH": term}])
    return nlp


_FOREIGN_FUNCTION_WORDS = {
    # French / Spanish / Italian / German / Portuguese function words that are not English words
    "les", "des", "une", "pour", "avec", "dans", "nous", "vous", "est", "sont", "du", "aux", "sur",
    "los", "las", "con", "para", "una", "del", "por", "como", "nuestro", "su", "es",
    "il", "di", "che", "per", "della", "sono", "gli", "nel",
    "der", "die", "und", "mit", "für", "ist", "wir", "sie", "das", "ein", "eine", "auf",
    "não", "uma", "com", "os", "da", "em",
}
_CJK = re.compile(r"[぀-ヿ㐀-鿿가-힯]")


def language_label(text: str, english_stop_share: float, foreign_share: float) -> str:
    """'en', 'mixed' (English plus another language, e.g. bilingual EU postings) or 'other'."""
    cjk = len(_CJK.findall(text)) / max(len(text), 1)
    foreign = foreign_share > 0.04 or cjk > 0.05
    if english_stop_share < 0.1 and (foreign or cjk > 0.2):
        return "other"
    return "mixed" if foreign else "en"


def doc_tokens(doc) -> tuple[str, float, float]:
    """Lower-cased lemmas without stop words, punctuation or numbers; plus English stop-word share
    and foreign function-word share (both over alphabetic tokens)."""
    out, alpha, stops, foreign = [], 0, 0, 0
    for t in doc:
        if t.is_alpha:
            alpha += 1
            stops += t.is_stop
            foreign += t.lower_ in _FOREIGN_FUNCTION_WORDS
        if t.is_stop or t.is_punct or t.is_space or t.like_num or t.like_url:
            continue
        lemma = t.text if t.text in PROTECTED else t.lemma_.lower()
        lemma = lemma.lower().strip("-'\"")
        if len(lemma) < 2 and lemma not in KEEP_SINGLE:
            continue
        if not any(ch.isalpha() for ch in lemma):
            continue
        out.append(lemma)
    return " ".join(out), (stops / alpha if alpha else 0.0), (foreign / alpha if alpha else 0.0)
