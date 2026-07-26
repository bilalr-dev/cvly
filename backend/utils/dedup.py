from __future__ import annotations

import re
import hashlib
from typing import List

from backend.models.job import RawJobPosting

_COMPANY_SUFFIX_RE = re.compile(r'\b(sas|sarl|sa|ltd|inc|gmbh|s\.a\.|s\.a\.r\.l\.)(?=\s|$)', re.IGNORECASE)
_TITLE_PREFIX_RE = re.compile(r'\b(senior|junior|lead|staff|principal)\b', re.IGNORECASE)

def normalize_company(name: str) -> str:
    name = name.lower()
    name = _COMPANY_SUFFIX_RE.sub('', name)
    return " ".join(name.split())

def normalize_title(title: str) -> str:
    title = title.lower()
    title = _TITLE_PREFIX_RE.sub('', title)
    return " ".join(title.split())

def _extract_city(location: str) -> str:
    if not location:
        return ""
    return location.split(',')[0].strip().lower()

def generate_posting_id(title: str, company: str, location: str) -> str:
    raw = f"{title}{company}{location}".encode()
    return hashlib.sha256(raw).hexdigest()

def deduplicate_postings(postings: List[RawJobPosting]) -> List[RawJobPosting]:
    if not postings:
        return []

    seen: dict[tuple[str, str, str], RawJobPosting] = {}
    for p in postings:
        city = _extract_city(getattr(p, "location", ""))
        key = (normalize_company(p.company), normalize_title(p.title), city)

        if key in seen:
            existing = seen[key]
            len_existing = len(existing.description_text) if getattr(existing, "description_text", None) else 0
            len_new = len(p.description_text) if getattr(p, "description_text", None) else 0
            if len_new > len_existing:
                seen[key] = p
        else:
            seen[key] = p

    return list(seen.values())
