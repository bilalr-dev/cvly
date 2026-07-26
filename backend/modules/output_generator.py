from __future__ import annotations

import re
from datetime import datetime, timezone, date  # noqa: F401
from typing import Any

_ACADEMIC_KEYWORDS: frozenset[str] = frozenset([
    "professor", "researcher", "postdoc", "faculty",
    "chercheur", "enseignant-chercheur", "maître de conférences"
])

_SECTION_HEADINGS = {
    "fr": {
        "skills": "Compétences",
        "experience": "Expérience professionnelle",
        "education": "Formation",
        "projects": "Projets académiques",
        "associations": "Associations",
    },
    "en": {
        "skills": "Skills",
        "experience": "Professional Experience",
        "education": "Education",
        "projects": "Academic Projects",
        "associations": "Associations",
    },
}

_FILENAME_SANITIZE_PATTERN = re.compile(r'[^\w]')

def is_one_page_exception(resume: Any, jd: Any) -> bool:
    total_y = 0
    is_senior = False

    exps = getattr(resume, "experience", [])
    if isinstance(exps, list) and len(exps) > 0:
        first_title = str(getattr(exps[0], "title", "")).lower()
        if "senior" in first_title or "lead" in first_title:
            is_senior = True

        for exp in exps:
            s = str(getattr(exp, "start_date", ""))
            e = str(getattr(exp, "end_date", ""))
            m1 = re.search(r'\d{4}', s)
            m2 = re.search(r'\d{4}', e)

            start = int(m1.group(0)) if m1 else 0
            end = int(m2.group(0)) if m2 else datetime.now(tz=timezone.utc).date().year

            if start > 0 and end >= start:
                total_y += (end - start)

    prof_type = str(getattr(resume, "detected_profile", "")).lower()
    if "senior" in prof_type or "lead" in prof_type:
        is_senior = True

    if total_y >= 10 and is_senior:
        return True

    jd_title = str(getattr(jd, "title", "")).lower()
    if any(k in jd_title for k in _ACADEMIC_KEYWORDS):
        return True

    jd_resp = getattr(jd, "key_responsibilities", [])
    if isinstance(jd_resp, list):
        for r in jd_resp:
            r_low = str(r).lower()
            if any(k in r_low for k in _ACADEMIC_KEYWORDS):
                return True

    return False

def generate_resume_markdown(resume: Any, tailored: Any, jd: Any, language: str = "fr") -> str:
    md = []
    md.append(f"# {getattr(resume, 'name', 'N/A')}\n")

    contact = []
    if getattr(resume, "email", None):
        contact.append(str(resume.email))
    if getattr(resume, "phone", None):
        contact.append(str(resume.phone))
    if getattr(resume, "location", None):
        contact.append(str(resume.location))

    if contact:
        md.append(" | ".join(contact) + "\n")

    skills = []
    sk_obj = getattr(resume, "skills", None)
    if sk_obj:
        for t in getattr(sk_obj, "technical", []):
            skills.append(str(t))
        for t in getattr(sk_obj, "tools", []):
            skills.append(str(t))

    prof_type = str(getattr(resume, "detected_profile", "experienced"))
    exp_first = "experienced" in prof_type

    lang_map = _SECTION_HEADINGS.get(language, _SECTION_HEADINGS["en"])

    md.append(f"## {lang_map['skills']}")
    md.append(", ".join(skills) + "\n")

    ext = is_one_page_exception(resume, jd)

    edu_text = []
    edu_text.append(f"## {lang_map['education']}")
    for e in getattr(resume, "education", []):
        edu_text.append(f"- {getattr(e, 'institution', '')}, {getattr(e, 'degree', '')}, {getattr(e, 'field', '')}, {getattr(e, 'year', '')}")
    edu_text.append("\n")

    exp_text = []
    exp_text.append(f"## {lang_map['experience']}")

    rw_bulls = getattr(tailored, "rewritten_experience_bullets", [])
    raw_exps = getattr(resume, "experience", [])

    roles_limit = 999 if ext else 3
    bull_limit = 999 if ext else 4

    roles_added = 0
    if isinstance(raw_exps, list):
        for exp in raw_exps:
            if roles_added >= roles_limit:
                break

            cmp = getattr(exp, "company", "")
            ttl = getattr(exp, "title", "")
            sd = getattr(exp, "start_date", "")
            ed = getattr(exp, "end_date", "Present")
            exp_text.append(f"### {ttl} @ {cmp} ({sd} - {ed})")

            orig_bullets = [str(b) for b in getattr(exp, "bullets", [])]

            for b_added, o_b in enumerate(orig_bullets):
                if b_added >= bull_limit:
                    break
                r_text = o_b
                if isinstance(rw_bulls, list):
                    for r_obj in rw_bulls:
                        if getattr(r_obj, "original", "") == o_b:
                            r_text = getattr(r_obj, "rewritten", o_b)
                            break

                exp_text.append(f"- {r_text}")
            exp_text.append("\n")
            roles_added += 1

    if not exp_first:
        md.extend(edu_text)
        md.extend(exp_text)
    else:
        md.extend(exp_text)
        md.extend(edu_text)

    return "\n".join(md)

def generate_cover_letter_markdown(cover_letter_text: str, resume: Any, jd_title: str, jd_company: str) -> str:
    md = []
    md.append(f"# {getattr(resume, 'name', 'N/A')}")
    md.append(f"**Target Role:** {jd_title} @ {jd_company}\n")
    md.append(cover_letter_text)
    return "\n".join(md)

def generate_output_filename(company: str, title: str, doc_type: str, language: str) -> str:
    c = _FILENAME_SANITIZE_PATTERN.sub('', str(company).lower().replace(" ", "_"))
    t = _FILENAME_SANITIZE_PATTERN.sub('', str(title).lower().replace(" ", "_"))
    prefix = datetime.now(tz=timezone.utc).date().strftime("%Y%m%d")
    return f"{prefix}_{c}_{t}_{doc_type}_{language}.md"
