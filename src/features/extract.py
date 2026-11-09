"""Feature extractors: skills (taxonomy matching), role family, seniority, experience, education."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .taxonomy import TAXONOMY

# ---------------------------------------------------------------- skills


@dataclass(frozen=True)
class Skill:
    name: str
    category: str
    tech: bool
    patterns: tuple[re.Pattern, ...]


def _compile(alias: str) -> re.Pattern:
    if alias.startswith("csre:"):
        return re.compile(alias[5:])
    if alias.startswith("re:"):
        return re.compile(alias[3:], re.I)
    flags = 0 if alias.startswith("cs:") else re.I
    phrase = alias[3:] if alias.startswith("cs:") else alias
    body = re.escape(phrase).replace(r"\ ", r"[\s-]+")  # "fine tuning" ~ "fine-tuning"
    if phrase[-1].isalpha():
        body += r"(?:s|es)?"
    return re.compile(r"(?<![\w+#.-])" + body + r"(?![\w+#]|-[a-z])", flags)


SKILLS: list[Skill] = [
    Skill(name, cat, spec["tech"], tuple(_compile(a) for a in aliases))
    for cat, spec in TAXONOMY.items()
    for name, aliases in spec["skills"].items()
]

SECTION_COLS = {
    "requirements": "section_requirements",
    "preferred": "section_preferred",
    "responsibilities": "section_responsibilities",
    "context": ("section_intro", "section_about"),
}


def match_skills(sections: dict[str, str]) -> dict[str, set[str]]:
    """Return {skill name: set of sections it appears in}."""
    found: dict[str, set[str]] = {}
    for sec, text in sections.items():
        if not text:
            continue
        for sk in SKILLS:
            if any(p.search(text) for p in sk.patterns):
                found.setdefault(sk.name, set()).add(sec)
    return found


def snippets(text: str, skill_name: str, width: int = 60) -> list[str]:
    sk = next(s for s in SKILLS if s.name == skill_name)
    out = []
    for p in sk.patterns:
        for m in p.finditer(text):
            out.append(text[max(0, m.start() - width): m.end() + width].replace("\n", " "))
    return out


# ---------------------------------------------------------------- role family (title-first rules, ordered)

ROLE_RULES: list[tuple[str, str]] = [
    ("Data Center & Facilities", r"data ?cent(?:er|re)|electrical|mechanical|commissioning|facilit|construction|critical environment|energy|power (?:systems|infrastructure)|site (?:lead|selection)|real estate|land development|due diligence lead"),
    ("Hardware & Silicon", r"asic|\brtl\b|verification|silicon|\bchip|hardware|firmware|physical design|analog|\bsoc\b|fpga|signal integrity|board design|thermal|packaging|\bdft\b|layout|circuit|gpu architect|systems? architect"),
    ("Research", r"research (?:scientist|engineer|lead|manager|program)|researcher|(?<!data )scientist|member of technical staff|\bmts\b|interpretability|alignment"),
    ("ML / AI Engineering", r"machine learning|\bml\b|\bai engineer|applied ai engineer|deep learning|\bllm|inference|pre-?training|post-?training|training (?:infrastructure|platform|systems|runtime)|model (?:serving|training|performance|efficiency|behavior)|\bnlp\b|computer vision|perception|ai (?:infrastructure|platform|systems)"),
    ("Safety, Policy & Trust", r"safety|safeguards|policy|trust|integrity|responsible|risk analyst|threat (?:intel|investig)|abuse|fraud|child safety|elections|human data|model behavior"),
    ("Sales & Go-to-Market", r"account (?:executive|director|manager)|\bsales\b|business development|\bbdr\b|\bsdr\b|customer success|solutions? (?:architect|engineer|consultant)|forward deployed|partner(?:ship)?s?\b|alliances|go[- ]to[- ]market|\bgtm\b|deal desk|customer engineer|technical account|startups? (?:lead|manager)|channel|enterprise (?:lead|growth)|deployment lead|delivery lead|enablement|technical (?:training|instructor)|instructor|applied ai\b(?! engineer)"),
    ("Security & Privacy", r"security|privacy|\bciso\b|detection|offensive|red team|cryptograph|identity"),
    ("Data & Analytics", r"data (?:scientist|science|engineer|analyst|platform|infrastructure)|analytics|\banalyst\b(?!.*(?:financial|finance|legal|policy|threat))|business intelligence|quantitative"),
    ("Infrastructure & SRE", r"infrastructure|site reliability|\bsre\b|devops|platform engineer|network|\bcloud\b|systems engineer|storage|\bhpc\b|kernel|compute|reliability|capacity|production engineer|\bit\b|it (?:support|engineer|operations)|systems administrator"),
    ("Program Management", r"program manager|project manager|\btpm\b|program lead|chief of staff|operations program"),
    ("Product & Design", r"product (?:manager|lead|management|designer|design|owner)|\bdesign(?:er)?\b|\bux\b|\bui\b|user research|creative|brand designer|content designer"),
    ("Marketing & Communications", r"marketing|communications|\bcomms\b|\bpr\b|brand|content|events?\b|social media|editorial|writer|developer relations|devrel|community|growth"),
    ("Finance, Legal & People", r"financ|accounting|accountant|\btax|treasury|controller|audit|\bfp&a\b|legal|counsel|attorney|lawyer|paralegal|compliance|procurement|sourcing|recruit|talent|people|\bhr\b|human resources|compensation|benefits|payroll|workplace|executive (?:assistant|business partner)|office|operations|strategy|bizops|revenue (?:accounting|operations)|billing|government affairs|public policy|economist"),
    ("Software Engineering", r"software|engineer|developer|frontend|front-end|backend|back-end|full[- ]stack|mobile|\bios\b|android|programmer|architect"),
]
_ROLE_RE = [(fam, re.compile(p, re.I)) for fam, p in ROLE_RULES]


def role_family(title: str, department: str = "") -> str:
    for fam, rx in _ROLE_RE:
        if rx.search(title or ""):
            return fam
    for fam, rx in _ROLE_RE:  # fall back to the department label
        if department and rx.search(department):
            return fam
    return "Other"


# ---------------------------------------------------------------- seniority

_IC_MANAGER = re.compile(
    r"\b(?:product|program|project|account|partner(?:ship)?s?|marketing|community|customer success|success|"
    r"operations|category|channel|territory|brand|content|technical program|solutions|relationship|"
    r"business development|sales development|events?|offer|vendor|release|campaign|support)\s+manager", re.I)
_TITLE_LEVELS = [
    ("Intern", re.compile(r"\bintern(?:ship)?\b|\bco-?op\b|\bstudent\b|\bapprentice", re.I)),
    ("Director+", re.compile(r"\bdirector\b|\bhead of\b|\bvp\b|vice president|\bchief\b|\bc[tfo]o\b|\bgeneral manager\b", re.I)),
    ("Manager", re.compile(r"\bmanager\b|\bmanaging\b", re.I)),
    ("Principal", re.compile(r"\bprincipal\b|\bstaff\b|\bdistinguished\b|\bfellow\b", re.I)),
    ("Lead", re.compile(r"\blead\b|\btech lead\b", re.I)),
    ("Senior", re.compile(r"\bsenior\b|\bsr\.?\b|\bIV\b", re.I)),
    ("Mid", re.compile(r"\bIII\b")),
    ("Junior", re.compile(r"\bjunior\b|\bjr\.?\b|new grad|\bgraduate\b|entry[- ]level|\bII\b|\bI\b(?=,|$)|\bassociate\b(?! (?:general counsel|director|partner))", re.I)),
]

_YEARS = re.compile(
    r"(\d{1,2})\s*\+?\s*(?:(?:-|to)\s*\d{1,2}\s*\+?\s*)?(?:years?|yrs?)\b(?:\s+of)?(?:[^.\n]{0,60})?",
    re.I,
)


def min_years_experience(requirements: str, fallback: str) -> float | None:
    """Smallest 'N years' figure that refers to experience (requirements first, else whole text)."""
    for text in (requirements, fallback):
        vals = []
        for m in _YEARS.finditer(text or ""):
            ctx = m.group(0).lower()
            if "experience" in ctx or "industry" in ctx or "working" in ctx or "track record" in ctx:
                v = int(m.group(1))
                if 0 < v <= 30:
                    vals.append(v)
        if vals:
            return float(min(vals))
    return None


def seniority(title: str, years: float | None) -> tuple[str, bool]:
    """(seniority_level, is_people_manager). Title cues first, then years of experience."""
    t = title or ""
    is_mgr = False
    for level, rx in _TITLE_LEVELS:
        if rx.search(t):
            if level == "Manager":
                if _IC_MANAGER.search(t):
                    continue  # product/program/account managers are individual contributors
                is_mgr = True
            if level == "Director+":
                is_mgr = True
            return level, is_mgr
    if years is None:
        return "Unspecified", False
    if years <= 2:
        return "Junior", False
    if years <= 5:
        return "Mid", False
    if years <= 9:
        return "Senior", False
    return "Principal", False


# ---------------------------------------------------------------- education

_DEGREES = [
    ("PhD", re.compile(r"\bph\.?\s?d\b|doctorate|doctoral", re.I)),
    ("Master's", re.compile(r"\bmaster'?s\b|\bm\.?s\.?\b(?= (?:in|degree|or))|\bmba\b|\bm\.?eng\b", re.I)),
    ("Bachelor's", re.compile(r"\bbachelor'?s?\b|\bb\.?s\.?\b(?= (?:in|degree|or))|\bb\.?a\.?\b(?= (?:in|degree))|undergraduate degree|\bbs/ms\b|\bbs,", re.I)),
]
_EQUIV = re.compile(r"equivalent (?:practical |work |industry )?experience|or equivalent", re.I)
_LAW = re.compile(r"\bj\.?d\.?\b|juris doctor|law degree|bar admission", re.I)


def education(requirements: str, preferred: str, all_text: str) -> dict:
    req = requirements or ""
    mentioned = {d for d, rx in _DEGREES if rx.search(all_text or "")}
    in_req = [d for d, rx in _DEGREES if rx.search(req)]
    return {
        "min_degree": in_req[-1] if in_req else "",  # lowest degree named in requirements
        "mentions_phd": "PhD" in mentioned,
        "phd_in_requirements": "PhD" in in_req,
        "degree_equivalent_ok": bool(_EQUIV.search(req or all_text or "")),
        "law_degree": bool(_LAW.search(all_text or "")),
    }
