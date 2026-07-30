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
from backend.utils.constants import (
    HALLUCINATION_COMMON_WORDS as _COMMON_WORDS,
)
from backend.utils.constants import (
    HALLUCINATION_SHORT_TECH_NAMES as _SHORT_TECH_NAMES,
)

_TECH_PATTERN = re.compile(r"[\.0-9]|[a-z][A-Z]")
_MIN_METRIC_DIGITS = 2


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


def _build_known_terms(resume: Any) -> set[str]:
    """Collect lowercased terms present in the original resume skills and bullets."""
    known_terms: set[str] = set()
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
            for w in str(bullet).lower().split():
                known_terms.add(w)
    return known_terms


def _get_rewritten_bullets(tailored_output: Any) -> list[Any]:
    """Return rewritten experience bullets when present as a list."""
    rw_bulls = getattr(tailored_output, "rewritten_experience_bullets", [])
    return rw_bulls if isinstance(rw_bulls, list) else []


def _clean_word(word: str) -> str | None:
    """Strip punctuation and keep alphanumeric/dot tokens only."""
    stripped = word.strip(".,;:!?()[]")
    if not stripped:
        return None
    cleaned = re.sub(r"[^\w\.]", "", stripped)
    return cleaned or None


def _is_metric_token(word_clean: str) -> bool:
    """Return True when the token looks like a number or percentage."""
    stripped = word_clean.replace(".", "").replace(",", "").replace("%", "")
    return stripped.isdigit() or "%" in word_clean


def _check_fabricated_metrics(
    word_clean: str,
    resume: Any,
    context_sentence: str,
) -> HallucinationWarning | None:
    """Check if a numeric/percentage claim exists in the original CV."""
    stripped = word_clean.replace(".", "").replace(",", "").replace("%", "")
    metric_found = _metric_exists_in_resume(word_clean, resume)
    if not metric_found and ("%" in word_clean or len(stripped) >= _MIN_METRIC_DIGITS):
        return HallucinationWarning(
            term=word_clean,
            context_sentence=context_sentence,
            severity="HIGH",
        )
    return None


def _check_short_tech_names(
    word_clean: str,
    known_terms: set[str],
    context_sentence: str,
) -> HallucinationWarning | None:
    """Check short tech names (Go, R, C#) against known terms."""
    if len(word_clean) > 2:
        return None
    w_low = word_clean.lower()
    if w_low in _SHORT_TECH_NAMES and w_low not in known_terms:
        return HallucinationWarning(
            term=word_clean,
            context_sentence=context_sentence,
            severity="HIGH",
        )
    return None


def _check_tech_terms(
    word_clean: str,
    known_terms: set[str],
    context_sentence: str,
    position: int,
) -> HallucinationWarning | None:
    """Check if a capitalized or tech-patterned word is hallucinated."""
    w_low = word_clean.lower()
    if w_low in known_terms or w_low in _COMMON_WORDS:
        return None

    is_tech = bool(_TECH_PATTERN.search(word_clean))
    is_cap = word_clean[0].isupper() if word_clean else False

    severity = "LOW"
    if is_tech:
        severity = "HIGH"
    elif is_cap and position > 0:
        severity = "MEDIUM"

    if severity in ("HIGH", "MEDIUM"):
        return HallucinationWarning(
            term=word_clean,
            context_sentence=context_sentence,
            severity=severity,
        )
    return None


def check_hallucinations(tailored_output: Any, resume: Any) -> list[HallucinationWarning]:
    """Scan rewritten bullets for fabricated metrics and unknown tech terms."""
    known_terms = _build_known_terms(resume)
    warnings: list[HallucinationWarning] = []

    for bullet in _get_rewritten_bullets(tailored_output):
        rewritten_text = getattr(bullet, "rewritten", "")
        if not isinstance(rewritten_text, str):
            continue

        for i, word in enumerate(rewritten_text.split()):
            word_clean = _clean_word(word)
            if not word_clean:
                continue

            # Preserve original short-circuit order: metrics → short names → tech terms
            if _is_metric_token(word_clean):
                warning = _check_fabricated_metrics(word_clean, resume, rewritten_text)
                if warning:
                    warnings.append(warning)
                continue

            if len(word_clean) <= 2:
                warning = _check_short_tech_names(word_clean, known_terms, rewritten_text)
                if warning:
                    warnings.append(warning)
                continue

            warning = _check_tech_terms(word_clean, known_terms, rewritten_text, i)
            if warning:
                warnings.append(warning)

    return warnings
