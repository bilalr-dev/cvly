"""Preview and approve tailored CVs and cover letters."""
from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Any

import markdown as md_lib
import nh3
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from backend.config import get_settings
from backend.modules.cover_letter import generate_cover_letter
from backend.modules.evaluator_agent import evaluate_tailored_output
from backend.modules.hallucination_checker import check_hallucinations
from backend.modules.output_generator import (
    generate_output_filename,
    generate_resume_markdown_raw,
)
from backend.modules.tailoring import rewrite_bullets
from backend.prompts import TRANSLATION_PROMPT
from backend.services.gemini_llm import GeminiAPIError, GeminiLLMService
from backend.state import app_state, get_translations, save_pipeline_data, templates
from backend.utils.constants import (
    CRITICAL_REVIEW_ACHIEVEMENT_LIMIT,
    FRENCH_DETECTION_WORDS,
    FRENCH_DETECTION_MIN_HITS,
    JOB_NOT_FOUND_DETAIL,
    MAX_KEYWORD_INJECTION_WORDS,
    MIN_BULLET_LENGTH,
    PREVIEW_TEMPLATE,
    SEVERITY_LABELS,
    TRANSLATION_CONTENT_PLACEHOLDER,
    TRANSLATION_TARGET_LANGUAGE_PLACEHOLDER,
    VIOLATION_LABELS,
)

logger = logging.getLogger(__name__)

_ALLOWED_TAGS = {
    "h1", "h2", "h3", "h4", "p", "br", "ul", "ol", "li",
    "strong", "em", "a", "code", "pre", "hr", "table",
    "thead", "tbody", "tr", "th", "td", "span", "div",
}
_ALLOWED_ATTRIBUTES = {"a": {"href", "target"}, "span": {"class"}, "div": {"class"}}


def _sanitize_html(html: str) -> str:
    """Remove script tags and dangerous attributes from LLM-generated HTML."""
    return nh3.clean(html, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRIBUTES)


def _is_valid_bullet(text: str) -> bool:
    """Return False if the bullet looks like a raw keyword injection."""
    text = text.strip()
    if not text:
        return False
    # Too short to be a real bullet (under 25 chars)
    if len(text) < MIN_BULLET_LENGTH:
        return False
    # Starts with a lowercase tech keyword pattern (no verb)
    is_keyword_injection = bool(
        re.match(r"^[a-z][\w\s\-\.]*$", text)
        and len(text.split()) <= MAX_KEYWORD_INJECTION_WORDS
    )
    return not is_keyword_injection


async def _translate(gemini: GeminiLLMService, content: str, target_language: str) -> str:
    if not content or not content.strip():
        return content
    prompt = (TRANSLATION_PROMPT
        .replace(TRANSLATION_TARGET_LANGUAGE_PLACEHOLDER, target_language)
        .replace(TRANSLATION_CONTENT_PLACEHOLDER, content)
    )
    try:
        return await gemini.agenerate_text(prompt, temperature=0.0)
    except (RuntimeError, ValueError, GeminiAPIError) as e:
        logger.warning("Translation failed: %s", e)
        return content  # fallback to original on error


async def _translate_markers(text: str, gemini: GeminiLLMService, target_language: str) -> str:
    """Find all __TRANSLATE__...__ markers and translate them in one batch call."""
    pattern = re.compile(r"__TRANSLATE__(.*?)__", re.DOTALL)
    matches = pattern.findall(text)

    if not matches:
        return text

    try:
        # Batch all markers into one call
        batch = "\n---\n".join(f"{i + 1}. {m.strip()}" for i, m in enumerate(matches))
        batch_prompt = (TRANSLATION_PROMPT
            .replace(TRANSLATION_TARGET_LANGUAGE_PLACEHOLDER, target_language)
            .replace(TRANSLATION_CONTENT_PLACEHOLDER, batch)
        )
        raw = await gemini.agenerate_text(batch_prompt, temperature=0.0)
        parts = raw.split("---")
        translated = [re.sub(r"^\s*\d+\.\s*", "", p.strip()) for p in parts]

        # Pad if needed
        while len(translated) < len(matches):
            translated.append(matches[len(translated)])

        # Replace markers in original text
        i = 0
        def replacer(m: Any) -> str:
            nonlocal i
            result = translated[i] if i < len(translated) else m.group(1)
            i += 1
            return result

        return pattern.sub(replacer, text)

    except (GeminiAPIError, RuntimeError, ValueError) as e:
        logger.debug("Marker translation failed: %s", e)
        # Fallback: remove markers, keep original text
        return pattern.sub(lambda m: m.group(1), text)


def _atf_payload(atf: Any) -> dict[str, Any] | None:
    if not atf:
        return None
    match_info = getattr(atf, "match", None)
    return {
        "summary": getattr(atf, "summary", ""),
        "seniority": getattr(atf, "seniority", ""),
        "recommendation": getattr(atf, "recommendation", ""),
        "strengths": list(getattr(match_info, "strengths", [])) if match_info else [],
        "weaknesses": list(getattr(match_info, "weaknesses", [])) if match_info else [],
    }


def get_job_data(job_id: str) -> dict[str, Any] | None:
    """Retrieve job posting + match data by ID."""
    jobs = app_state.get("pipeline_results", [])
    match_results = app_state.get("match_results", {})

    for posting in jobs:
        if getattr(posting, "id", None) != job_id:
            continue
        match = match_results.get(job_id)
        atf = getattr(match, "atf_analysis", None) if match else None
        return {
            "id": posting.id,
            "company": posting.company,
            "title": posting.title,
            "location": posting.location,
            "url": posting.url,
            "contract": getattr(posting, "contract_type", "") or "",
            "description": posting.description_text,
            "score": round(getattr(match, "overall_score", 0)) if match else 0,
            "matched_keywords": list(getattr(match, "matched_keywords", [])) if match else [],
            "missing_keywords": list(getattr(match, "missing_keywords", [])) if match else [],
            "has_atf": bool(atf),
            "atf": _atf_payload(atf),
            "posting": posting,
            "match": match,
        }
    return None


async def _run_tailoring(resume: Any, jd: Any, match: Any, gemini: GeminiLLMService, language: str, country: str) -> Any:
    """Rewrite bullets and validate them."""
    tailored_output = await rewrite_bullets(
        resume=resume,
        jd=jd,
        match_result=match,
        gemini_service=gemini,
        language=language,
        country=country,
    )

    valid_bullets = [
        rb for rb in tailored_output.rewritten_experience_bullets
        if _is_valid_bullet(rb.rewritten)
    ]

    return tailored_output.model_copy(
        update={"rewritten_experience_bullets": valid_bullets}
    )


async def _run_evaluator(tailored_output: Any, gemini: GeminiLLMService, job_description: str, language: str) -> list[dict]:
    """Extract evaluator agent call + human-readable warning merge."""
    orig_texts = [rb.original for rb in tailored_output.rewritten_experience_bullets]
    rewritten_texts = [rb.rewritten for rb in tailored_output.rewritten_experience_bullets]

    verdict = await evaluate_tailored_output(
        original_bullets=orig_texts,
        rewritten_bullets=rewritten_texts,
        gemini_service=gemini,
        job_description=job_description,
        language=language,
    )

    eval_warnings = []
    violation_labels = VIOLATION_LABELS.get(language, VIOLATION_LABELS["en"])
    severity_labels = SEVERITY_LABELS.get(language, SEVERITY_LABELS["en"])
    for v in verdict.violations:
        human_label = violation_labels.get(v.violation_type, violation_labels["other"])
        human_severity = severity_labels.get(v.severity, v.severity)
        eval_warnings.append({
            "term": human_label,
            "severity": v.severity,
            "context": f"{human_severity}: {v.description}",
        })
    return eval_warnings


def _warning_from_issue(
    issue: dict[str, Any],
    violation_labels: dict[str, str],
    severity_labels: dict[str, str],
    severity: str,
) -> dict[str, str]:
    """Map a critical-evaluator issue dict to a UI warning."""
    issue_type = issue.get("type", "other")
    human_severity = severity_labels.get(severity, severity)
    return {
        "term": violation_labels.get(issue_type, violation_labels["other"]),
        "severity": severity,
        "context": f"{human_severity}: {issue.get('explanation', '')}",
    }


def _resume_achievements(resume: Any) -> list[str]:
    """Flatten experience bullets from a resume profile."""
    return [
        bullet
        for exp in getattr(resume, "experience", []) or []
        for bullet in getattr(exp, "bullets", []) or []
        if isinstance(bullet, str)
    ]


async def _fetch_bullet_review(
    critic: Any,
    tailored_output: Any,
    job: dict[str, Any],
    language: str,
) -> dict[str, Any]:
    """Run Groq bullet review; return raw review dict."""
    orig_texts = [rb.original for rb in tailored_output.rewritten_experience_bullets]
    rewritten_texts = [rb.rewritten for rb in tailored_output.rewritten_experience_bullets]
    if not orig_texts or not rewritten_texts:
        return {"issues": []}

    return await critic.review_bullets(
        original_bullets=orig_texts,
        rewritten_bullets=rewritten_texts,
        job_description=job.get("description", ""),
        language=language,
    )


async def _fetch_cover_review(
    critic: Any,
    cover_letter_text: str,
    job: dict[str, Any],
    resume: Any,
    language: str,
) -> dict[str, Any]:
    """Run Groq cover-letter review; return raw review dict."""
    if not cover_letter_text:
        return {"issues": []}

    return await critic.review_cover_letter(
        cover_letter_text=cover_letter_text,
        candidate_summary=getattr(resume, "summary", "") if resume else "",
        candidate_achievements=_resume_achievements(resume)[:CRITICAL_REVIEW_ACHIEVEMENT_LIMIT],
        target_company=job.get("company", ""),
        job_description=job.get("description", ""),
        language=language,
    )


def _bullet_issue_warnings(
    issues: list[dict],
    violation_labels: dict[str, str],
    severity_labels: dict[str, str],
) -> list[dict]:
    return [
        _warning_from_issue(issue, violation_labels, severity_labels, "HIGH")
        for issue in issues
    ]


def _cover_issue_warnings(
    issues: list[dict],
    violation_labels: dict[str, str],
    severity_labels: dict[str, str],
) -> list[dict]:
    return [
        _warning_from_issue(
            issue,
            violation_labels,
            severity_labels,
            "HIGH" if issue.get("type") == "entity_bleed" else "MEDIUM",
        )
        for issue in issues
    ]


def _apply_corrected_bullets(tailored_output: Any, corrected_bullets: list[str]) -> Any:
    """Replace rewritten text on each bullet; preserve original + keywords."""
    updated = [
        rb.model_copy(update={"rewritten": corrected_bullets[i]})
        if i < len(corrected_bullets)
        else rb
        for i, rb in enumerate(tailored_output.rewritten_experience_bullets)
    ]
    return tailored_output.model_copy(update={"rewritten_experience_bullets": updated})


async def _identity(value: Any) -> Any:
    """Awaitable no-op used as a gather placeholder when a branch is skipped."""
    await asyncio.sleep(0)
    return value


async def _gemini_correct_outputs(
    critic_inputs: tuple[list[str], list[str], str],
    bullet_issues: list[dict],
    cover_issues: list[dict],
    gemini: GeminiLLMService,
    language: str,
) -> tuple[list[str], str]:
    """Run Gemini correction for bullets and cover letter in parallel."""
    from backend.modules.self_corrector import correct_bullets, correct_cover_letter

    orig_texts, rewritten_texts, cover_letter_text = critic_inputs
    return await asyncio.gather(
        correct_bullets(
            original_bullets=orig_texts,
            rewritten_bullets=rewritten_texts,
            issues=bullet_issues,
            gemini_service=gemini,
            language=language,
        ) if bullet_issues else _identity(rewritten_texts),
        correct_cover_letter(
            cover_letter=cover_letter_text,
            issues=cover_issues,
            gemini_service=gemini,
            language=language,
        ) if cover_issues else _identity(cover_letter_text),
    )


async def _rereview_corrected(
    critic: Any,
    orig_texts: list[str],
    corrected_bullets: list[str],
    corrected_cover: str,
    job: dict[str, Any],
    resume: Any,
    language: str,
    bullet_issues: list[dict],
    cover_issues: list[dict],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Re-run Groq only on tracks that had issues."""
    summary = (getattr(resume, "summary", "") or "") if resume else ""
    achievements = _resume_achievements(resume)[:CRITICAL_REVIEW_ACHIEVEMENT_LIMIT] if resume else []
    return await asyncio.gather(
        critic.review_bullets(
            original_bullets=orig_texts,
            rewritten_bullets=corrected_bullets,
            job_description=job.get("description", ""),
            language=language,
        ) if bullet_issues else _identity({"issues": []}),
        critic.review_cover_letter(
            cover_letter_text=corrected_cover,
            candidate_summary=summary,
            candidate_achievements=achievements,
            target_company=job.get("company", ""),
            job_description=job.get("description", ""),
            language=language,
        ) if cover_issues else _identity({"issues": []}),
    )


async def _run_critical_with_correction(  # noqa: PLR0913
    tailored_output: Any,
    cover_letter_text: str,
    job: dict[str, Any],
    resume: Any,
    language: str,
    gemini: GeminiLLMService,
) -> tuple[Any, str, list[dict]]:
    """Groq review → optional one-round Gemini correction → Groq re-review.

    Returns (possibly corrected tailored_output, cover_letter, remaining warnings).
    Only issues that persist after correction are returned as warnings.
    """
    settings = get_settings()
    if not settings.groq_api_key:
        return tailored_output, cover_letter_text, []

    violation_labels = VIOLATION_LABELS.get(language, VIOLATION_LABELS["en"])
    severity_labels = SEVERITY_LABELS.get(language, SEVERITY_LABELS["en"])

    try:
        from backend.modules.critical_evaluator import CriticalEvaluator
        from backend.services.groq_llm import GroqAPIError, GroqLLMService
    except ImportError as e:
        logger.debug("Critical evaluator unavailable: %s", e)
        return tailored_output, cover_letter_text, []

    try:
        critic = CriticalEvaluator(GroqLLMService(api_key=settings.groq_api_key))
        bullet_review, cover_review = await asyncio.gather(
            _fetch_bullet_review(critic, tailored_output, job, language),
            _fetch_cover_review(critic, cover_letter_text, job, resume, language),
        )

        bullet_issues = list(bullet_review.get("issues") or [])
        cover_issues = list(cover_review.get("issues") or [])
        if not bullet_issues and not cover_issues:
            return tailored_output, cover_letter_text, []

        orig_texts = [rb.original for rb in tailored_output.rewritten_experience_bullets]
        rewritten_texts = [rb.rewritten for rb in tailored_output.rewritten_experience_bullets]

        corrected_bullets, corrected_cover = await _gemini_correct_outputs(
            (orig_texts, rewritten_texts, cover_letter_text),
            bullet_issues,
            cover_issues,
            gemini,
            language,
        )

        if bullet_issues and corrected_bullets is not None:
            tailored_output = _apply_corrected_bullets(tailored_output, corrected_bullets)
        if cover_issues and corrected_cover is not None:
            cover_letter_text = corrected_cover

        final_bullet_review, final_cover_review = await _rereview_corrected(
            critic,
            orig_texts,
            corrected_bullets,
            corrected_cover,
            job,
            resume,
            language,
            bullet_issues,
            cover_issues,
        )

        remaining_warnings = (
            _bullet_issue_warnings(
                list(final_bullet_review.get("issues") or []),
                violation_labels,
                severity_labels,
            )
            + _cover_issue_warnings(
                list(final_cover_review.get("issues") or []),
                violation_labels,
                severity_labels,
            )
        )
        return tailored_output, cover_letter_text, remaining_warnings
    except (GeminiAPIError, GroqAPIError, RuntimeError, ValueError, TypeError, KeyError, AttributeError) as e:
        logger.debug("Critical evaluator / correction skipped: %s", e)
        return tailored_output, cover_letter_text, []

def _detect_resume_language(resume: Any) -> str:
    """Detect French vs English based on French stopwords presence in raw bullet points."""
    all_bullets = " " + " ".join(
        str(b) for exp in (getattr(resume, "experience", []) or [])
        for b in (getattr(exp, "bullets", []) or [])
    ) + " "

    french_hits = sum(1 for fw in FRENCH_DETECTION_WORDS if fw in all_bullets.lower())
    return "fr" if french_hits >= FRENCH_DETECTION_MIN_HITS else "en"


def _build_tailored_data(tailored_output: Any, cover_letter_text: str, warnings: list[dict]) -> dict:
    """Construct the standardized output dictionary for display and storage."""
    bullet_pairs = [
        {
            "original": rb.original,
            "tailored": rb.rewritten,
            "keywords_added": rb.keywords_added,
        }
        for rb in tailored_output.rewritten_experience_bullets
    ]

    return {
        "bullet_pairs": bullet_pairs,
        "cover_letter": cover_letter_text,
        "resume_markdown": "",
        "unfillable_gaps": list(tailored_output.unfillable_gaps),
        "warnings": warnings,
    }


def _preview_context(request: Request, job: dict, language: str, t: dict, tailored: dict | None = None, error: str | None = None) -> dict:
    """Return standard partial context state."""
    return {
        "request": request,
        "job": job,
        "tailored": tailored,
        "language": language,
        "t": t,
        "active_page": "results",
        "error": error,
    }


async def _translate_full_document(
    resume_md_raw: str,
    gemini: GeminiLLMService,
    lang_name: str,
) -> str:
    """Translate the entire markdown document when no bullets were rewritten."""
    translation_prompt_text = (TRANSLATION_PROMPT
        .replace(TRANSLATION_TARGET_LANGUAGE_PLACEHOLDER, lang_name)
        .replace(TRANSLATION_CONTENT_PLACEHOLDER, resume_md_raw)
    )
    try:
        return await gemini.agenerate_text(translation_prompt_text, temperature=0.0)
    except GeminiAPIError as e:
        logger.warning("Document translation failed, using markers: %s", e)
        return resume_md_raw


async def _translate_summary_and_skills(
    resume: Any,
    tailored_data: dict,
    gemini: GeminiLLMService,
    lang_name: str,
) -> None:
    """Translate summary and soft skills in-place in tailored_data."""
    items = [resume.summary or ""]
    soft_skills = list(getattr(getattr(resume, "skills", None), "soft", []) or [])
    for skill in soft_skills:
        items.append(getattr(skill, "name", "") or "")
        items.append(getattr(skill, "description", "") or "")

    if not any(items):
        return

    batch = "\n---ITEM---\n".join(items)
    batch_prompt = (TRANSLATION_PROMPT
        .replace(TRANSLATION_TARGET_LANGUAGE_PLACEHOLDER, lang_name)
        .replace(TRANSLATION_CONTENT_PLACEHOLDER, batch)
    )
    try:
        translated_batch = await gemini.agenerate_text(batch_prompt, temperature=0.0)
        parts = translated_batch.split("---ITEM---")
        while len(parts) < len(items):
            parts.append(items[len(parts)])

        tailored_data["translated_summary"] = parts[0].strip()
        translated_soft = []
        for i, skill in enumerate(soft_skills):
            name_idx = 1 + (i * 2)
            desc_idx = 2 + (i * 2)
            translated_soft.append({
                "name": parts[name_idx].strip() if name_idx < len(parts) else getattr(skill, "name", ""),
                "description": parts[desc_idx].strip() if desc_idx < len(parts) else getattr(skill, "description", ""),
            })
        tailored_data["translated_soft_skills"] = translated_soft
    except GeminiAPIError as e:
        logger.warning("Batch translation failed: %s", e)


async def _render_and_translate(resume: Any, tailored_data: dict, jd: Any, gemini: GeminiLLMService, language: str) -> str:
    """Complete document rendering logic including potential full vs partial translations."""
    resume_md_raw = generate_resume_markdown_raw(
        resume=resume,
        tailored=tailored_data,
        jd=jd,
        language=language,
    )

    original_lang = _detect_resume_language(resume)
    lang_name = "French" if language == "fr" else "English"
    bullet_pairs = tailored_data.get("bullet_pairs", [])

    should_translate = (
        (language == "fr" and original_lang == "en")
        or (language == "en" and original_lang == "fr")
    )

    if should_translate and not bullet_pairs:
        resume_md_raw = await _translate_full_document(resume_md_raw, gemini, lang_name)
    elif should_translate:
        await _translate_summary_and_skills(resume, tailored_data, gemini, lang_name)
        resume_md_raw = generate_resume_markdown_raw(
            resume=resume,
            tailored=tailored_data,
            jd=jd,
            language=language,
        )

    if "__TRANSLATE__" in resume_md_raw:
        resume_md_raw = await _translate_markers(resume_md_raw, gemini, lang_name)

    return md_lib.markdown(resume_md_raw, extensions=["nl2br", "tables"])


async def _save_output_files(
    job: dict,
    tailored: dict | None,
    language: str,
    output_dir: Path,
) -> tuple[str, str]:
    """Save resume and cover letter .md files. Returns (resume_path, cover_path)."""
    if not tailored:
        return "", ""

    resume_filename = generate_output_filename(
        company=job["company"],
        title=job["title"],
        doc_type="resume",
        language=language,
    )
    resume_path = str(output_dir / resume_filename)
    resume_content = tailored.get("resume_markdown", "")
    await asyncio.to_thread(Path(resume_path).write_text, resume_content, "utf-8")

    cover_filename = generate_output_filename(
        company=job["company"],
        title=job["title"],
        doc_type="cover",
        language=language,
    )
    cover_path = str(output_dir / cover_filename)
    cover_content = tailored.get("cover_letter", "")
    await asyncio.to_thread(Path(cover_path).write_text, cover_content, "utf-8")

    return resume_path, cover_path


async def _track_in_sheets(
    job: dict,
    resume_path: str,
    cover_path: str,
    language: str,
) -> None:
    """Append a row to Google Sheets. Fails silently with a warning log."""
    settings = get_settings()
    if not (settings.google_service_account_path and settings.google_sheet_id):
        return

    try:
        import gspread

        from backend.models.job import ParsedJobDescription
        from backend.modules.sheets_tracker import SheetsTracker

        def _append() -> None:
            tracker = SheetsTracker(
                credentials_path=settings.google_service_account_path,
                sheet_id=settings.google_sheet_id,
            )
            tracker.connect()
            posting = job.get("posting")
            jd = app_state.get("parsed_jds", {}).get(job["id"]) or ParsedJobDescription()
            if posting is not None:
                tracker.append_job(
                    posting=posting,
                    _jd=jd,
                    match_result=job.get("match"),
                    resume_path=resume_path,
                    cover_letter_path=cover_path,
                    language=language,
                )

        await asyncio.to_thread(_append)
    except (gspread.exceptions.GSpreadException, OSError, ValueError, KeyError, TypeError) as e:
        logger.warning("Google Sheets tracking failed: %s", e)


router = APIRouter(prefix="/preview")

_RESPONSES_404 = {404: {"description": JOB_NOT_FOUND_DETAIL}}


@router.get("/{job_id}", response_class=HTMLResponse, responses=_RESPONSES_404)
async def preview_job(request: Request, job_id: str) -> HTMLResponse:
    """Preview tailored CV for a specific job."""
    t = get_translations()
    logger.debug("Preview - job_id=%s", job_id)

    job = get_job_data(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=JOB_NOT_FOUND_DETAIL)

    language = app_state.get("language") or get_settings().default_language
    tailored_cache = app_state.setdefault("tailored_outputs", {})
    cached = tailored_cache.get(f"{job_id}_{language}")

    if cached:
        return templates.TemplateResponse(
            request=request, name=PREVIEW_TEMPLATE,
            context=_preview_context(request, job, language, t, tailored=cached),
        )

    resume = app_state.get("resume_profile")
    jd = app_state.get("parsed_jds", {}).get(job_id)

    if not resume or not jd:
        return templates.TemplateResponse(
            request=request, name=PREVIEW_TEMPLATE,
            context=_preview_context(request, job, language, t, error=t.get("error_no_data", "Resume or job description not available for tailoring.")),
        )

    try:
        settings = get_settings()
        gemini = GeminiLLMService(api_key=settings.gemini_api_key)
        country = (app_state.get("preferences") or {}).get("country") or get_settings().default_country

        if isinstance(resume, BaseModel):
            resume = resume.model_copy(deep=True)

        # Phase A: rewrite and cover letter are independent (both need resume/JD only)
        tailored_output, cover_letter = await asyncio.gather(
            _run_tailoring(resume, jd, job["match"], gemini, language, country),
            generate_cover_letter(resume, jd, job["match"], gemini, language, country),
        )

        # Phase B: Gemini evaluator ∥ Groq review + optional one-round correction
        eval_warnings, (tailored_output, cover_letter, groq_warnings) = await asyncio.gather(
            _run_evaluator(tailored_output, gemini, job["description"], language),
            _run_critical_with_correction(
                tailored_output=tailored_output,
                cover_letter_text=cover_letter,
                job=job,
                resume=resume,
                language=language,
                gemini=gemini,
            ),
        )

        # Hallucination check on final (possibly corrected) bullets
        warnings = check_hallucinations(tailored_output, resume)

        all_warnings = (
            [{"term": w.term, "severity": w.severity, "context": w.context_sentence} for w in warnings]
            + eval_warnings
            + groq_warnings
        )

        tailored_data = _build_tailored_data(tailored_output, cover_letter, all_warnings)
        resume_md = await _render_and_translate(resume, tailored_data, jd, gemini, language)
        tailored_data["resume_markdown"] = _sanitize_html(resume_md)

        tailored_cache[f"{job_id}_{language}"] = tailored_data

        return templates.TemplateResponse(
            request=request, name=PREVIEW_TEMPLATE,
            context=_preview_context(request, job, language, t, tailored=tailored_data),
        )

    except GeminiAPIError as e:
        error_msg = t.get("error_rate_limit", "...") if "429" in str(e) else t.get("error_tailoring", "Tailoring failed. Please try again.")
        return templates.TemplateResponse(
            request=request, name=PREVIEW_TEMPLATE,
            context=_preview_context(request, job, language, t, error=error_msg),
        )
    except (RuntimeError, ValueError) as e:
        return templates.TemplateResponse(
            request=request, name=PREVIEW_TEMPLATE,
            context=_preview_context(request, job, language, t, error=f"{t.get('error_unexpected', 'Unexpected error')}: {e!s}"),
        )


@router.post("/{job_id}/approve", responses=_RESPONSES_404)
async def approve_job(request: Request, job_id: str) -> RedirectResponse:
    """Approve tailored CV: save files to disk and track in Google Sheets."""
    job = get_job_data(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=JOB_NOT_FOUND_DETAIL)

    language = app_state.get("language") or get_settings().default_language
    cache_key = f"{job_id}_{language}"
    tailored = app_state.get("tailored_outputs", {}).get(cache_key)

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    resume_path, cover_path = await _save_output_files(job, tailored, language, output_dir)
    await _track_in_sheets(job, resume_path, cover_path, language)

    approved = app_state.setdefault("approved_jobs", set())
    approved.add(job_id)

    saved_files = app_state.setdefault("saved_files", {})
    saved_files[job_id] = {
        "resume_path": resume_path,
        "cover_path": cover_path,
    }

    app_state["last_approved"] = {
        "title": job["title"],
        "company": job["company"],
    }

    save_pipeline_data()

    logger.debug(
        "Job approved: %s at %s; files saved to %s",
        job["title"], job["company"], output_dir,
    )
    return RedirectResponse(url="/results", status_code=302)


@router.get("/{job_id}/view/resume", response_class=HTMLResponse, responses=_RESPONSES_404)
async def view_resume(request: Request, job_id: str) -> HTMLResponse:
    """Render the tailored resume as a styled, printable HTML page."""
    t = get_translations()
    language = app_state.get("language") or get_settings().default_language
    cache_key = f"{job_id}_{language}"
    tailored = app_state.get("tailored_outputs", {}).get(cache_key)

    if not tailored or not tailored.get("resume_markdown"):
        raise HTTPException(status_code=404, detail="No tailored resume found. Preview the job first.")

    job = get_job_data(job_id)
    return templates.TemplateResponse(
        request=request,
        name="view_document.html",
        context={
            "request": request,
            "content": tailored["resume_markdown"],
            "doc_type": t.get("tailored_cv_title", "CV adapté"),
            "job_title": job["title"] if job else "",
            "job_company": job["company"] if job else "",
            "language": language,
            "t": t,
        },
    )


@router.get("/{job_id}/view/cover", response_class=HTMLResponse, responses=_RESPONSES_404)
async def view_cover_letter(request: Request, job_id: str) -> HTMLResponse:
    """Render the cover letter as a styled, printable HTML page."""
    t = get_translations()
    language = app_state.get("language") or get_settings().default_language
    cache_key = f"{job_id}_{language}"
    tailored = app_state.get("tailored_outputs", {}).get(cache_key)

    if not tailored or not tailored.get("cover_letter"):
        raise HTTPException(status_code=404, detail="No cover letter found. Preview the job first.")

    job = get_job_data(job_id)

    cover_text = tailored["cover_letter"]
    cover_html = _sanitize_html(md_lib.markdown(cover_text, extensions=["nl2br"]))

    return templates.TemplateResponse(
        request=request,
        name="view_document.html",
        context={
            "request": request,
            "content": cover_html,
            "doc_type": t.get("cover_letter_title", "Lettre de motivation"),
            "job_title": job["title"] if job else "",
            "job_company": job["company"] if job else "",
            "language": language,
            "t": t,
        },
    )


@router.post("/{job_id}/regenerate")
async def regenerate_job(request: Request, job_id: str) -> RedirectResponse:
    """Clear cache and regenerate tailored CV."""
    tailored_cache = app_state.setdefault("tailored_outputs", {})
    language = app_state.get("language") or get_settings().default_language
    tailored_cache.pop(f"{job_id}_{language}", None)
    return RedirectResponse(url=f"/preview/{job_id}", status_code=302)


@router.post("/{job_id}/save-edits")
async def save_edits(job_id: str, request: Request) -> JSONResponse:
    """Save user edits to the tailored output cache."""
    data = await request.json()
    new_cover_letter = data.get("cover_letter", "")

    language = app_state.get("language") or get_settings().default_language
    cache_key = f"{job_id}_{language}"
    tailored_cache = app_state.setdefault("tailored_outputs", {})

    if cache_key in tailored_cache:
        existing = dict(tailored_cache[cache_key])
        existing["cover_letter"] = new_cover_letter
        tailored_cache[cache_key] = existing

    return JSONResponse(content={"status": "saved"})
