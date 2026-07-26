from __future__ import annotations

import re
from typing import Any, List

from backend.models import HallucinationWarning

_COMMON_WORDS: frozenset[str] = frozenset([
    "the", "and", "or", "for", "with", "from", "to", "in", "on", "at",
    "by", "a", "an", "is", "of", "le", "la", "les", "des", "pour",
    "avec", "dans", "et", "ou", "en", "sur", "au", "aux"
])

_TECH_PATTERN = re.compile(r'[\.0-9]|[a-z][A-Z]')

def check_hallucinations(tailored_output: Any, resume: Any) -> List[HallucinationWarning]:
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
                w_clean = re.sub(r'[^\w\.]', '', w)
                if not w_clean:
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
