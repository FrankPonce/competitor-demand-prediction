"""Shared helpers for all collectors: polite HTTP, robots.txt checks, text cleanup, schema."""

from __future__ import annotations

import html
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

import requests

USER_AGENT = (
    "cadetx-job-postings-research/0.1 "
    "(non-commercial academic project; github.com/FrankPonce/competitor-demand-prediction)"
)

# Output schema: required CadetX fields first, then recommended/provenance fields.
FIELDS = [
    "job_id",
    "company_name",
    "job_title",
    "job_description",
    "posting_date",
    "location",
    "job_url",
    "employment_type",
    "department",
    "remote_type",
    "salary_range",
    "updated_at",
    "scraped_date",
    "source_name",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


class PoliteSession:
    """requests.Session wrapper: identifying User-Agent, fixed delay between calls, retries."""

    def __init__(self, delay_seconds: float = 2.5, timeout: float = 30.0):
        self.delay = delay_seconds
        self.timeout = timeout
        self._last = 0.0
        self.s = requests.Session()
        self.s.headers["User-Agent"] = USER_AGENT
        self.request_count = 0

    def get(self, url: str, **kwargs) -> requests.Response:
        for attempt in range(3):
            wait = self.delay - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            self.request_count += 1
            resp = self.s.get(url, timeout=self.timeout, **kwargs)
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(self.delay * (attempt + 2) * 2)
                continue
            resp.raise_for_status()
            if "charset" not in resp.headers.get("Content-Type", "").lower():
                resp.encoding = "utf-8"  # requests otherwise falls back to latin-1 (mojibake)
            return resp
        resp.raise_for_status()
        return resp


# ---------------------------------------------------------------- robots.txt


class Robots:
    """Minimal robots.txt matcher for the `User-agent: *` group.

    Supports `*` wildcards and `$` anchors with longest-match precedence (RFC 9309),
    which the stdlib urllib.robotparser does not handle.
    """

    def __init__(self, text: str):
        self.rules: list[tuple[bool, str]] = []  # (allow, pattern)
        agents: list[str] = []
        in_rules = False
        for raw in text.splitlines():
            line = raw.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            key, val = (p.strip() for p in line.split(":", 1))
            key = key.lower()
            if key == "user-agent":
                if in_rules:
                    agents, in_rules = [], False
                agents.append(val)
            elif key in ("allow", "disallow"):
                in_rules = True
                if "*" in agents and val:
                    self.rules.append((key == "allow", val))

    @staticmethod
    def _to_regex(pattern: str) -> re.Pattern:
        anchored = pattern.endswith("$")
        body = re.escape(pattern.rstrip("$")).replace(r"\*", ".*")
        return re.compile("^" + body + ("$" if anchored else ""))

    def allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        path = parts.path + ("?" + parts.query if parts.query else "")
        best_len, best_allow = -1, True
        for allow, pattern in self.rules:
            if self._to_regex(pattern).match(path):
                plen = len(pattern)
                if plen > best_len or (plen == best_len and allow):
                    best_len, best_allow = plen, allow
        return best_allow

    @classmethod
    def fetch(cls, session: PoliteSession, robots_url: str) -> "Robots":
        return cls(session.get(robots_url).text)


class DisallowedURL(RuntimeError):
    pass


def assert_allowed(robots: Robots, url: str) -> None:
    if not robots.allowed(url):
        raise DisallowedURL(f"robots.txt disallows {url}")


# ---------------------------------------------------------------- text

_TAG = re.compile(r"<[^>]+>")
_BLOCK = re.compile(r"</?(p|div|br|li|ul|ol|h[1-6]|tr)[^>]*>", re.I)
_WS = re.compile(r"[ \t\r\f\v]+")
_NL = re.compile(r"\n\s*\n+")


def html_to_text(s: str | None) -> str:
    if not s:
        return ""
    s = html.unescape(s)  # Greenhouse double-escapes its HTML
    s = _BLOCK.sub("\n", s)
    s = _TAG.sub("", s)
    s = html.unescape(s)
    s = _WS.sub(" ", s)
    s = _NL.sub("\n\n", s)
    return s.strip()


EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?<!\d)(?:\+?\d[\d ()-]{8,}\d)(?!\d)")


def scrub_contacts(text: str) -> str:
    """Remove emails and phone numbers: posting content only, no personal contact data."""
    text = EMAIL.sub("[email removed]", text)
    return PHONE.sub("[phone removed]", text)


def remote_type_from(text: str) -> str:
    t = (text or "").lower()
    if "hybrid" in t:
        return "hybrid"
    if "remote" in t:
        return "remote"
    if "on-site" in t or "onsite" in t or "in office" in t:
        return "onsite"
    return ""
