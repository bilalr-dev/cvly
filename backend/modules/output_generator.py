"""Markdown/HTML resume and cover-letter output generation."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import markdown as md_lib

from backend.config import get_settings
from backend.utils.constants import (
    ACADEMIC_KEYWORDS as _ACADEMIC_KEYWORDS,
)
from backend.utils.constants import (
    LANG_NAMES_EN_TO_FR as _LANG_NAMES_EN_TO_FR,
)
from backend.utils.constants import (
    MAX_BULLETS_PER_ROLE,
    MAX_ROLES_LIMIT,
)
from backend.utils.constants import (
    PROFICIENCY_EN_TO_FR as _PROFICIENCY_EN_TO_FR,
)
from backend.utils.constants import (
    SECTION_HEADINGS as _SECTION_HEADINGS,
)
from backend.utils.constants import (
    TYPE_SUFFIXES as _TYPE_SUFFIXES,
)


def _strip_type_suffix(title: str) -> str:
    """Remove existing type suffixes from a job title to prevent duplication."""
    cleaned = title
    for suffix in _TYPE_SUFFIXES:
        cleaned = cleaned.replace(suffix, "")
    return cleaned.strip()

_FILENAME_SANITIZE_PATTERN = re.compile(r"[^\w]")

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
            m1 = re.search(r"\d{4}", s)
            m2 = re.search(r"\d{4}", e)

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


def _render_header(md: list, resume: Any, tailored: Any, _language: str) -> None:
    """Render name, contact info, and summary."""
    md.append(f"# {getattr(resume, 'name', '')}")
    contact = []
    for field in ["phone", "email", "portfolio", "linkedin", "location"]:
        val = getattr(resume, field, None)
        if val:
            contact.append(str(val))
    if contact:
        md.append(" | ".join(contact))

    summary_text = (
        tailored.get("translated_summary")
        if isinstance(tailored, dict) and tailored.get("translated_summary")
        else getattr(resume, "summary", None)
    )
    if summary_text:
        md.append("")
        md.append(str(summary_text))


def _render_education(md: list, resume: Any, language: str, lang_map: dict) -> None:
    """Render education section."""
    edu_list = getattr(resume, "education", []) or []
    if not edu_list:
        return
    md.append("")
    md.append(f"## {lang_map['education']}")
    for edu in edu_list:
        in_prog = getattr(edu, "in_progress", False)
        year = getattr(edu, "year", None)
        if in_prog:
            year_str = "en cours" if language == "fr" else "in progress"
        elif year:
            year_str = str(year)
        else:
            year_str = ""
        degree = getattr(edu, "degree", "")
        inst = getattr(edu, "institution", "")
        field = getattr(edu, "field", "")
        line = f"**{degree}**"
        if inst:
            line += f", *{inst}*"
        if field and field != degree:
            line += f", {field}"
        if year_str:
            line += f" ({year_str})"
        rhythm = getattr(edu, "alternance_rhythm", None)
        if rhythm:
            line += f" · {rhythm}"
        md.append(line)


def _build_bullet_map(tailored: Any) -> dict[str, str]:
    """Map original bullets to rewritten/tailored text."""
    if isinstance(tailored, dict):
        rw_bulls = tailored.get("rewritten_experience_bullets") or tailored.get("bullet_pairs") or []
    else:
        rw_bulls = getattr(tailored, "rewritten_experience_bullets", []) or []

    bullet_map: dict[str, str] = {}
    for rb in rw_bulls:
        if isinstance(rb, dict):
            orig = rb.get("original", "")
            rewritten = rb.get("rewritten") or rb.get("tailored", "")
        else:
            orig = getattr(rb, "original", "")
            rewritten = getattr(rb, "rewritten", "")
        if orig and rewritten:
            bullet_map[orig] = rewritten
    return bullet_map


def _render_experience(
    md: list,
    resume: Any,
    tailored: Any,
    language: str,
    lang_map: dict,
    is_exception: bool,
) -> None:
    """Render experience section with tailored bullets."""
    exp_list = getattr(resume, "experience", []) or []
    if not exp_list:
        return

    bullet_map = _build_bullet_map(tailored)

    md.append("")
    md.append(f"## {lang_map['experience']}")
    roles_limit = MAX_ROLES_LIMIT
    bull_limit = MAX_ROLES_LIMIT if is_exception else MAX_BULLETS_PER_ROLE
    for exp in exp_list[:roles_limit]:
        title = _strip_type_suffix(getattr(exp, "title", ""))
        company = getattr(exp, "company", "")
        start = getattr(exp, "start_date", "")
        end = getattr(exp, "end_date", None) or ("Présent" if language == "fr" else "Present")
        exp_type = getattr(exp, "type", "")
        if exp_type == "internship":
            type_label = " (Stage)" if language == "fr" else " (Internship)"
        elif exp_type == "alternance":
            type_label = " (Alternance)"
        elif exp_type == "volunteer":
            type_label = " (Bénévolat)" if language == "fr" else " (Volunteer)"
        else:
            type_label = ""
        md.append(f"**{title}{type_label}** @ {company} ({start} - {end})")
        bullets = getattr(exp, "bullets", []) or []
        for bullet in bullets[:bull_limit]:
            rewritten = bullet_map.get(str(bullet), None)
            if rewritten is None:
                rewritten = f"__TRANSLATE__{str(bullet)}__"
            md.append(f"- {rewritten}")
        md.append("")


def _render_skills(md: list, resume: Any, tailored: Any, _language: str, lang_map: dict) -> None:
    """Render technical skills, certifications, and soft skills."""
    sk = getattr(resume, "skills", None)
    if not sk:
        return
    technical = list(getattr(sk, "technical", []) or []) + list(getattr(sk, "tools", []) or [])
    if technical:
        md.append("")
        md.append(f"## {lang_map.get('skills_technical', 'Compétences techniques')}")
        md.append(", ".join(technical))
    certs = list(getattr(sk, "certifications", []) or [])
    if certs:
        md.append("")
        md.append(f"## {lang_map.get('certifications', 'Certifications')}")
        md.append(", ".join(certs))
    translated_soft = tailored.get("translated_soft_skills") if isinstance(tailored, dict) else None
    soft = translated_soft if translated_soft else list(getattr(sk, "soft", []) or [])
    if soft:
        md.append("")
        md.append(f"## {lang_map.get('skills_soft', 'Soft Skills')}")
        for skill in soft:
            if isinstance(skill, dict):
                name = skill.get("name", "")
                desc = skill.get("description", None)
            else:
                name = getattr(skill, "name", str(skill))
                desc = getattr(skill, "description", None)
            md.append(f"**{name}**")
            if desc:
                md.append(desc)
            md.append("")


def _render_languages(md: list, resume: Any, language: str, lang_map: dict) -> None:
    """Render languages section with translation."""
    langs = list(getattr(resume, "languages", []) or [])
    if not langs:
        return
    md.append("")
    md.append(f"## {lang_map.get('languages', 'Langues')}")

    if language == "fr":
        translated_langs = []
        for lang_entry in langs:
            translated = lang_entry
            # Split on ":" or " : " to separate name from level
            for sep in [":", " : "]:
                if sep in lang_entry:
                    parts = lang_entry.split(sep, 1)
                    name = parts[0].strip()
                    level = parts[1].strip() if len(parts) > 1 else ""
                    # Translate language name
                    name_lower = name.lower()
                    if name_lower in _LANG_NAMES_EN_TO_FR:
                        name = _LANG_NAMES_EN_TO_FR[name_lower]
                    # Translate proficiency level (but not CEFR codes)
                    level_lower = level.lower()
                    if level_lower in _PROFICIENCY_EN_TO_FR:
                        level = _PROFICIENCY_EN_TO_FR[level_lower]
                    translated = f"{name} : {level}"
                    break
            translated_langs.append(translated)
        md.append(" · ".join(translated_langs))
    else:
        md.append(" · ".join(langs))


def _render_projects(md: list, resume: Any, _language: str, lang_map: dict) -> None:
    """Render academic projects section."""
    projs = list(getattr(resume, "academic_projects", []) or [])
    if not projs:
        return
    md.append("")
    md.append(f"## {lang_map.get('projects', 'Projets académiques')}")
    for proj in projs:
        name = getattr(proj, "name", "")
        context = getattr(proj, "context", "")
        desc = getattr(proj, "description", "")
        techs = list(getattr(proj, "technologies", []) or [])
        md.append(f"**{name}** · *{context}*")
        if desc:
            md.append(desc)
        if techs:
            md.append(f"Technologies : {', '.join(techs)}")
        md.append("")


def _render_associations(md: list, resume: Any, _language: str, lang_map: dict) -> None:
    """Render associations and extracurriculars."""
    assocs = list(getattr(resume, "associations_and_extracurriculars", []) or [])
    if not assocs:
        return
    md.append("")
    md.append(f"## {lang_map.get('associations', 'Associations')}")
    for a in assocs:
        name = getattr(a, "name", "")
        role = getattr(a, "role", "")
        desc = getattr(a, "description", None)
        line = f"**{role}**, {name}"
        if desc:
            line += f" : {desc}"
        md.append(line)


def generate_resume_markdown_raw(resume: Any, tailored: Any, jd: Any, language: str | None = None) -> str:
    """Generate full tailored resume as raw markdown string."""
    language = language or get_settings().default_language
    md: list[str] = []
    lang_map = _SECTION_HEADINGS.get(language, _SECTION_HEADINGS["fr"])
    ext = is_one_page_exception(resume, jd)
    is_student = str(getattr(resume, "detected_profile", "")) in ("student_stage", "student_alternance")

    _render_header(md, resume, tailored, language)

    if is_student:
        _render_education(md, resume, language, lang_map)
        _render_experience(md, resume, tailored, language, lang_map, ext)
        _render_projects(md, resume, language, lang_map)
        _render_associations(md, resume, language, lang_map)
    else:
        _render_experience(md, resume, tailored, language, lang_map, ext)
        _render_education(md, resume, language, lang_map)

    _render_skills(md, resume, tailored, language, lang_map)
    _render_languages(md, resume, language, lang_map)

    return "\n".join(md)

def generate_resume_markdown(resume: Any, tailored: Any, jd: Any, language: str | None = None) -> str:
    """Generate full tailored resume as HTML rendered from markdown."""
    language = language or get_settings().default_language
    raw_md = generate_resume_markdown_raw(resume, tailored, jd, language)
    return md_lib.markdown(raw_md, extensions=["nl2br", "tables"])

def generate_cover_letter_markdown(cover_letter_text: str, resume: Any, jd_title: str, jd_company: str) -> str:
    md = []
    md.append(f"# {getattr(resume, 'name', 'N/A')}")
    md.append(f"**Target Role:** {jd_title} @ {jd_company}\n")
    md.append(cover_letter_text)
    return "\n".join(md)

def generate_output_filename(company: str, title: str, doc_type: str, language: str) -> str:
    c = _FILENAME_SANITIZE_PATTERN.sub("", str(company).lower().replace(" ", "_"))
    t = _FILENAME_SANITIZE_PATTERN.sub("", str(title).lower().replace(" ", "_"))
    prefix = datetime.now(tz=timezone.utc).date().strftime("%Y%m%d")
    return f"{prefix}_{c}_{t}_{doc_type}_{language}.md"
