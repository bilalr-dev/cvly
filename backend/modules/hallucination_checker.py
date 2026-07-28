"""
Hallucination checker module for detecting fabricated content in tailored output.

Detection layers:
1. Tech terms: Flags any technical term (capitalized or alphanumeric) not present in the original CV.
2. Fabricated metrics: Flags numbers and percentages that were added during rewriting but don't exist originally.
3. Short tech names: Explicitly flags known short abbreviations (e.g., 'Go', 'R', 'C#') if fabricated.
"""
from __future__ import annotations

import re
from typing import Any

from backend.models import HallucinationWarning

_COMMON_WORDS: frozenset[str] = frozenset([
    "the", "and", "or", "for", "with", "from", "to", "in", "on", "at",
    "by", "a", "an", "is", "of", "le", "la", "les", "des", "pour",
    "avec", "dans", "et", "ou", "en", "sur", "au", "aux"
])

_SHORT_TECH_NAMES = frozenset(["go", "r", "c", "c#", "c++", "ai", "ml", "qa", "ux", "ui", "ci", "cd", "js", "ts"])

_TECH_PATTERN = re.compile(r'[\.0-9]|[a-z][A-Z]')

def _metric_exists_in_resume(metric: str, resume: Any) -> bool:
    """Check if a numeric metric appears in any original resume bullet or metric list."""
    for exp in getattr(resume, "experience", []):
        for bullet in getattr(exp, "bullets", []):
            if metric in str(bullet):
                return True
        for m in getattr(exp, "metrics", []):
            if metric in str(m):
                return True
    return False

def check_hallucinations(tailored_output: Any, resume: Any) -> list[HallucinationWarning]:
    known_terms = set()
    skills = getattr(resume, "skills", None)
    if skills:
        for t in getattr(skills, "technical", []):
            known_terms.add(str(t).lower())
        for t in getattr(skills, "tools", []):
            known_terms.add(str(t).lower())
        for t in getattr(skills, "certifications", []):
            known_terms.add(str(t).lower())

    for exp in getattr(resume, "experience", []):
        for bullet in getattr(exp, "bullets", []):
            words = str(bullet).lower().split()
            for w in words:
                known_terms.add(w)

    warnings = []
    rw_bulls = getattr(tailored_output, "rewritten_experience_bullets", [])

    if isinstance(rw_bulls, list):
        for b in rw_bulls:
            rewritten_text = getattr(b, "rewritten", "")
            if not isinstance(rewritten_text, str):
                continue

            words = rewritten_text.split()
            for i, w in enumerate(words):
                w = w.strip(".,;:!?()[]")
                if not w:
                    continue
                w_clean = re.sub(r'[^\w\.]', '', w)
                if not w_clean:
                    continue

                # Check for fabricated metrics — numbers/percentages not in original CV
                stripped = w_clean.replace(".", "").replace(",", "").replace("%", "")
                if stripped.isdigit() or "%" in w_clean:
                    # Search for this metric in original resume bullets
                    metric_found = _metric_exists_in_resume(w_clean, resume)
                    if not metric_found and ("%" in w_clean or len(stripped) >= 2):
                        warnings.append(
                            HallucinationWarning(
                                term=w_clean,
                                context_sentence=rewritten_text,
                                severity="HIGH"
                            )
                        )
                    continue

                # Short terms: check against known short tech names
                if len(w_clean) <= 2:
                    w_low = w_clean.lower()
                    if w_low in _SHORT_TECH_NAMES and w_low not in known_terms:
                        warnings.append(
                            HallucinationWarning(
                                term=w_clean,
                                context_sentence=rewritten_text,
                                severity="HIGH"
                            )
                        )
                    continue

                w_low = w_clean.lower()
                is_tech = bool(_TECH_PATTERN.search(w_clean))
                is_cap = w_clean[0].isupper() if w_clean else False

                if w_low not in known_terms:
                    if w_low in _COMMON_WORDS:
                        continue

                    severity = "LOW"
                    if is_tech:
                        severity = "HIGH"
                    elif is_cap and i > 0:
                        severity = "MEDIUM"

                    if severity in ["HIGH", "MEDIUM"]:
                        warnings.append(
                            HallucinationWarning(
                                term=w_clean,
                                context_sentence=rewritten_text,
                                severity=severity
                            )
                        )

    return warnings
