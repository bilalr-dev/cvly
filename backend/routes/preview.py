from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from backend.config import AppSettings
from backend.modules.cover_letter import generate_cover_letter
from backend.modules.evaluator_agent import evaluate_tailored_output
from backend.modules.hallucination_checker import check_hallucinations
from backend.modules.output_generator import generate_resume_markdown_raw
from backend.modules.tailoring import rewrite_bullets
from backend.prompts import TRANSLATION_PROMPT
from pydantic import BaseModel
import markdown as md_lib
from backend.services.gemini_llm import GeminiAPIError, GeminiLLMService
from backend.state import app_state, get_translations, templates

logger = logging.getLogger(__name__)

# Human-readable labels for evaluator violation types
_VIOLATION_LABELS = {
    "fr": {
        "fabricated_metric": "Un chiffre semble avoir été inventé, vérifiez qu'il correspond à votre expérience réelle",
        "invented_skill": "Une compétence ou un outil a été ajouté qui ne figure pas dans votre CV original",
        "jd_attribution": "Cette phrase semble venir de l'offre d'emploi, pas de votre parcours",
        "scope_inflation": "Votre rôle semble décrit de façon plus importante que dans votre CV original",
        "other": "Un point a été modifié, vérifiez qu'il correspond à votre expérience",
    },
    "en": {
        "fabricated_metric": "A number seems to have been added, check it matches your real experience",
        "invented_skill": "A skill or tool was added that isn't in your original CV",
        "jd_attribution": "This seems to come from the job posting, not from your background",
        "scope_inflation": "Your role seems described as bigger than in your original CV",
        "other": "Something was changed, check it matches your experience",
    },
}

_SEVERITY_LABELS = {
    "fr": {
        "HIGH": "À corriger avant d'envoyer",
        "MEDIUM": "À vérifier avant d'envoyer",
        "LOW": "Point mineur — à votre appréciation",
    },
    "en": {
        "HIGH": "Fix this before sending",
        "MEDIUM": "Check this before sending",
        "LOW": "Minor point — your call",
    },
}

def _is_valid_bullet(text: str) -> bool:
    """Return False if the bullet looks like a raw keyword injection."""
    text = text.strip()
    if not text:
        return False
    # Too short to be a real bullet (under 25 chars)
    if len(text) < 25:
        return False
    # Starts with a lowercase tech keyword pattern (no verb)
    if re.match(r'^[a-z][\w\s\-\.]*$', text) and len(text.split()) <= 5:
        return False
    return True


def _translate(gemini: GeminiLLMService, content: str, target_language: str) -> str:
    if not content or not content.strip():
        return content
    prompt = (TRANSLATION_PROMPT
        .replace("{target_language}", target_language)
        .replace("{content}", content)
    )
    try:
        return gemini.generate_text(prompt, temperature=0.0)
    except (RuntimeError, ValueError) as e:
        logger.warning("Translation failed: %s", e)
        return content  # fallback to original on error

def _translate_markers(text: str, gemini: GeminiLLMService, target_language: str) -> str:
    """Find all __TRANSLATE__...__ markers and translate them in one batch call."""
    pattern = re.compile(r'__TRANSLATE__(.*?)__', re.DOTALL)
    matches = pattern.findall(text)

    if not matches:
        return text

    try:
        # Batch all markers into one call
        batch = "\n---\n".join(f"{i + 1}. {m.strip()}" for i, m in enumerate(matches))
        batch_prompt = (TRANSLATION_PROMPT
            .replace("{target_language}", target_language)
            .replace("{content}", batch)
        )
        raw = gemini.generate_text(batch_prompt, temperature=0.0)
        parts = raw.split("---")
        translated = [re.sub(r'^\s*\d+\.\s*', '', p.strip()) for p in parts]

        # Pad if needed
        while len(translated) < len(matches):
            translated.append(matches[len(translated)])

        # Replace markers in original text
        i = 0
        def replacer(m):
            nonlocal i
            result = translated[i] if i < len(translated) else m.group(1)
            i += 1
            return result

        return pattern.sub(replacer, text)

    except (GeminiAPIError, Exception):
        # Fallback: remove markers, keep original text
        return pattern.sub(lambda m: m.group(1), text)

router = APIRouter(prefix="/preview")


def get_job_data(job_id: str) -> dict[str, Any] | None:
    """Retrieve job posting + match data by ID."""
    jobs = app_state.get("pipeline_results", [])
    match_results = app_state.get("match_results", {})

    for posting in jobs:
        if getattr(posting, "id", None) == job_id:
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
                "atf": {
                    "summary": getattr(atf, "summary", ""),
                    "seniority": getattr(atf, "seniority", ""),
                    "recommendation": getattr(atf, "recommendation", ""),
                    "strengths": list(getattr(atf.match, "strengths", [])) if hasattr(atf, "match") else [],
                    "weaknesses": list(getattr(atf.match, "weaknesses", [])) if hasattr(atf, "match") else [],
                } if atf else None,
                "posting": posting,
                "match": match,
            }
    return None


@router.get("/{job_id}", response_class=HTMLResponse)
async def preview_job(request: Request, job_id: str) -> HTMLResponse:
    """Preview tailored CV for a specific job."""
    t = get_translations()
    logger.info("Preview - job_id=%s", job_id)

    job = get_job_data(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    resume = app_state.get("resume_profile")
    parsed_jds = app_state.get("parsed_jds", {})
    jd = parsed_jds.get(job_id)
    language = app_state.get("language", "fr")
    prefs = app_state.get("preferences") or {}
    country = prefs.get("country", "FR")

    # Check if already tailored (cached)
    tailored_cache = app_state.setdefault("tailored_outputs", {})
    cache_key = f"{job_id}_{language}"
    cached = tailored_cache.get(cache_key)

    if cached:
        return templates.TemplateResponse(request=request, name="preview.html", context={
            "request": request,
            "job": job,
            "tailored": cached,
            "language": language,
            "t": t,
            "active_page": "results",
        })

    # If no resume or JD, show preview without tailoring
    if not resume or not jd:
        return templates.TemplateResponse(request=request, name="preview.html", context={
            "request": request,
            "job": job,
            "tailored": None,
            "language": language,
            "t": t,
            "active_page": "results",
            "error": t.get("error_no_data", "Resume or job description not available for tailoring."),
        })

    # Run tailoring
    try:
        settings = AppSettings()
        gemini = GeminiLLMService(api_key=settings.gemini_api_key)

        if isinstance(resume, BaseModel):
            resume = resume.model_copy(deep=True)


        # Get original bullets from resume
        original_bullets = []
        for exp in resume.experience:
            for bullet in exp.bullets:
                original_bullets.append({"role": f"{exp.title} at {exp.company}", "text": bullet})

        # Rewrite bullets
        tailored_output = await rewrite_bullets(
            resume=resume,
            jd=jd,
            match_result=job["match"],
            gemini_service=gemini,
            language=language,
            country=country,
        )

        # Filter out malformed bullets (keyword injections)
        valid_bullets = [
            rb for rb in tailored_output.rewritten_experience_bullets
            if _is_valid_bullet(rb.rewritten)
        ]
        tailored_output = tailored_output.model_copy(
            update={"rewritten_experience_bullets": valid_bullets}
        )

        # Generate cover letter
        cover_letter_text = await generate_cover_letter(
            resume=resume,
            jd=jd,
            match_result=job["match"],
            gemini_service=gemini,
            language=language,
            country=country,
        )

        # Check hallucinations
        warnings = check_hallucinations(tailored_output, resume)

        # Evaluator agent QA gate — independent LLM critic
        orig_texts = [rb.original for rb in tailored_output.rewritten_experience_bullets]
        rewritten_texts = [rb.rewritten for rb in tailored_output.rewritten_experience_bullets]

        verdict = await evaluate_tailored_output(
            original_bullets=orig_texts,
            rewritten_bullets=rewritten_texts,
            gemini_service=gemini,
            job_description=job["description"],
            language=language,
        )

        # Build display data
        bullet_pairs = []
        for rb in tailored_output.rewritten_experience_bullets:
            bullet_pairs.append({
                "original": rb.original,
                "tailored": rb.rewritten,
                "keywords_added": rb.keywords_added,
            })

        unfillable = list(tailored_output.unfillable_gaps)

        hallucination_warnings = [
            {"term": w.term, "severity": w.severity, "context": w.context_sentence}
            for w in warnings
        ]

        # Translate evaluator violations into user-facing warnings
        violation_labels = _VIOLATION_LABELS.get(language, _VIOLATION_LABELS["en"])
        severity_labels = _SEVERITY_LABELS.get(language, _SEVERITY_LABELS["en"])
        for v in verdict.violations:
            human_label = violation_labels.get(v.violation_type, violation_labels["other"])
            human_severity = severity_labels.get(v.severity, v.severity)
            hallucination_warnings.append({
                "term": human_label,
                "severity": v.severity,
                "context": f"{human_severity} — {v.description}",
            })

        tailored_data = {
            "bullet_pairs": bullet_pairs,
            "cover_letter": cover_letter_text,
            "resume_markdown": "",
            "unfillable_gaps": unfillable,
            "warnings": hallucination_warnings,
        }

        # Generate raw markdown in the original CV language
        resume_md_raw = generate_resume_markdown_raw(
            resume=resume,
            tailored=tailored_data,
            jd=jd,
            language=language,
        )

        # Translate the full document if needed
        # Reliable French detection: look for French-only words
        # These words cannot appear in standard English text
        all_bullets = " " + " ".join(
            str(b) for exp in (getattr(resume, "experience", []) or [])
            for b in (getattr(exp, "bullets", []) or [])
        ) + " "

        french_only = [" est ", " sont ", " avec ", " dans ", " pour ", " une ", " les ", " des ", " par ", " sur ", " au ", " du ", " ce ", " qui ", " que "]
        french_hits = sum(1 for fw in french_only if fw in all_bullets.lower())
        original_lang = "fr" if french_hits >= 2 else "en"

        lang_name = "French" if language == "fr" else "English"

        # Safety net: if target is FR and we detect English bullets, always translate
        if language == "fr" and original_lang == "en":
            should_translate = True
        elif language == "en" and original_lang == "fr":
            should_translate = True
        else:
            should_translate = False

        logger.info("Translation check - language=%s original_lang=%s french_hits=%d should_translate=%s",
                    language, original_lang, french_hits, should_translate)

        if should_translate and not bullet_pairs:
            # Full document translation only when NO bullets were rewritten at all
            translation_prompt_text = (TRANSLATION_PROMPT
                .replace("{target_language}", lang_name)
                .replace("{content}", resume_md_raw)
            )
            try:
                resume_md_raw = gemini.generate_text(translation_prompt_text, temperature=0.0)
                logger.info("Full document translated to %s", lang_name)
            except GeminiAPIError as e:
                logger.warning("Document translation failed, using markers: %s", e)
        elif should_translate:
            # Translate summary and soft skills only (not bullets — already translated by tailoring)
            items = [resume.summary or ""]
            soft_skills = list(getattr(resume.skills, "soft", []) or [])
            for skill in soft_skills:
                items.append(getattr(skill, "name", "") or "")
                items.append(getattr(skill, "description", "") or "")

            if any(items):
                batch = "\n---ITEM---\n".join(items)
                batch_prompt = (TRANSLATION_PROMPT
                    .replace("{target_language}", lang_name)
                    .replace("{content}", batch)
                )
                try:
                    translated_batch = gemini.generate_text(batch_prompt, temperature=0.0)
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

            # Regenerate markdown with translated summary/soft skills
            resume_md_raw = generate_resume_markdown_raw(
                resume=resume,
                tailored=tailored_data,
                jd=jd,
                language=language,
            )

        # Apply marker translation for untailored bullets (if marker system is used)
        if "__TRANSLATE__" in resume_md_raw:
            resume_md_raw = _translate_markers(resume_md_raw, gemini, lang_name)
        tailored_data["resume_markdown"] = md_lib.markdown(resume_md_raw, extensions=["nl2br", "tables"])

        # Cache it
        tailored_cache[cache_key] = tailored_data

        return templates.TemplateResponse(request=request, name="preview.html", context={
            "request": request,
            "job": job,
            "tailored": tailored_data,
            "language": language,
            "t": t,
            "active_page": "results",
        })

    except GeminiAPIError as e:
        logger.warning("Tailoring failed for %s: %s", job_id, e)
        error_msg = t.get("error_rate_limit", "API rate limit reached. Please wait and try again.") if "429" in str(e) else t.get("error_tailoring", "Tailoring failed. Please try again.")
        return templates.TemplateResponse(request=request, name="preview.html", context={
            "request": request,
            "job": job,
            "tailored": None,
            "language": language,
            "t": t,
            "active_page": "results",
            "error": error_msg,
        })
    except (RuntimeError, ValueError) as e:
        logger.exception("Unexpected error during tailoring for %s", job_id)
        return templates.TemplateResponse(request=request, name="preview.html", context={
            "request": request,
            "job": job,
            "tailored": None,
            "language": language,
            "t": t,
            "active_page": "results",
            "error": f"Erreur inattendue: {e!s}",
        })


@router.post("/{job_id}/approve")
async def approve_job(request: Request, job_id: str) -> RedirectResponse:
    """Approve tailored CV."""
    job = get_job_data(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Mark as approved in app state
    approved = app_state.setdefault("approved_jobs", set())
    approved.add(job_id)

    # Store approval info for the results page flash message
    app_state["last_approved"] = {
        "title": job["title"],
        "company": job["company"],
    }

    logger.info("Job approved: %s at %s", job["title"], job["company"])
    # TODO: wire up sheets_tracker.append_job and file output (Milestone #1)
    return RedirectResponse(url="/results", status_code=302)


@router.post("/{job_id}/regenerate")
async def regenerate_job(request: Request, job_id: str) -> RedirectResponse:
    """Regenerate tailored CV — clear cache and re-run."""
    tailored_cache = app_state.setdefault("tailored_outputs", {})
    language = app_state.get("language", "fr")
    tailored_cache.pop(f"{job_id}_{language}", None)
    # Redirect to GET which will re-run tailoring
    return RedirectResponse(url=f"/preview/{job_id}", status_code=302)


@router.post("/{job_id}/save-edits")
async def save_edits(job_id: str, request: Request) -> JSONResponse:
    """Save user edits to the tailored output cache."""
    data = await request.json()
    new_cover_letter = data.get("cover_letter", "")

    language = app_state.get("language", "fr")
    cache_key = f"{job_id}_{language}"
    tailored_cache = app_state.setdefault("tailored_outputs", {})

    if cache_key in tailored_cache:
        # Update cover letter in cache
        existing = dict(tailored_cache[cache_key])
        existing["cover_letter"] = new_cover_letter
        tailored_cache[cache_key] = existing
        logger.info("Cover letter edits saved for %s", job_id)

    return JSONResponse(content={"status": "saved"})
