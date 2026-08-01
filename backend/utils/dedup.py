"""Job posting deduplication utilities."""
from __future__ import annotations

import hashlib
import re

from backend.models.job import RawJobPosting
from backend.utils.constants import TRUNCATED_DESCRIPTION_MAX_CHARS


def is_truncated(text: str) -> bool:
    """Return True if the description appears to be a truncated excerpt."""
    if not text:
        return True
    stripped = text.rstrip()
    return (
        stripped.endswith("…")
        or stripped.endswith("...")
        or len(text) < TRUNCATED_DESCRIPTION_MAX_CHARS
    )


_COMPANY_SUFFIX_RE = re.compile(r"\b(sas|sarl|sa|ltd|inc|gmbh|s\.a\.|s\.a\.r\.l\.)(?=\s|$)", re.IGNORECASE)
_TITLE_PREFIX_RE = re.compile(r"\b(senior|junior|lead|staff|principal)\b", re.IGNORECASE)

def normalize_company(name: str) -> str:
    name = name.lower()
    name = _COMPANY_SUFFIX_RE.sub("", name)
    return " ".join(name.split())

def normalize_title(title: str) -> str:
    title = title.lower()
    title = _TITLE_PREFIX_RE.sub("", title)
    return " ".join(title.split())

def _extract_city(location: str) -> str:
    if not location:
        return ""
    return location.split(",")[0].strip().lower()

def generate_posting_id(title: str, company: str, location: str) -> str:
    raw = f"{title}{company}{location}".encode()
    return hashlib.sha256(raw).hexdigest()

def _posting_key(p: RawJobPosting) -> tuple:
    """Return the deduplication key for a posting."""
    city = _extract_city(getattr(p, "location", ""))
    norm_company = normalize_company(p.company)
    norm_title = normalize_title(p.title)
    # Fall back to URL/ID when metadata is absent to avoid over-merging.
    if not norm_company.strip() and not city.strip():
        return (p.url or p.id,)
    return (norm_company, norm_title, city)


def _description_len(p: RawJobPosting) -> int:
    """Return the byte length of the posting description, or 0 if absent."""
    text = getattr(p, "description_text", None)
    return len(text) if text else 0


def deduplicate_postings(postings: list[RawJobPosting]) -> list[RawJobPosting]:
    if not postings:
        return []

    seen: dict[tuple, RawJobPosting] = {}
    for p in postings:
        key = _posting_key(p)
        existing = seen.get(key)
        if existing is None or _description_len(p) > _description_len(existing):
            seen[key] = p

    return list(seen.values())
