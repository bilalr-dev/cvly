import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import HTMLResponse
from starlette.requests import Request

from backend.config import AppSettings
from backend.models.preferences import SearchPreferences
from backend.modules.atf_analyser import analyse_atf
from backend.modules.cv_analyser import analyse_cv
from backend.modules.jd_parser import parse_job_description
from backend.modules.job_discovery import JobDiscovery
from backend.services.gemini_embeddings import GeminiEmbeddingsService
from backend.services.gemini_llm import GeminiAPIError, GeminiLLMService
from backend.services.job_apis.adzuna import AdzunaClient
from backend.services.job_apis.arbeitnow import ArbeitnowClient
from backend.services.job_apis.france_travail import FranceTravailClient
from backend.services.job_apis.jsearch import JSearchClient
from backend.services.job_apis.remotive import RemotiveClient
from backend.services.rate_limiter import AsyncRateLimiter
from backend.state import app_state, get_translations, save_pipeline_data, templates
from backend.utils.constants import (
    ALTERNANCE_KEYWORDS,
    CONTRACT_KEYWORDS,
    SENIORITY_KEYWORDS,
    TITLE_CONTRACT_SIGNALS,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline")

async def execute_pipeline() -> None:
    logger = logging.getLogger(__name__)
    settings = AppSettings()
    rate_limiter = AsyncRateLimiter(max_calls=10, period_seconds=60.0)

    try:
        app_state["pipeline_status"] = "running"
        logger.info("Pipeline started")
        app_state["pipeline_step"] = 1
        app_state["pipeline_step_detail"] = ""
        api_clients = []

        if settings.france_travail_client_id and settings.france_travail_client_secret:
            api_clients.append(
                FranceTravailClient(
                    client_id=settings.france_travail_client_id,
                    client_secret=settings.france_travail_client_secret,
                )
            )
            logger.debug("France Travail client configured")

        if settings.adzuna_app_id and settings.adzuna_app_key:
            api_clients.append(
                AdzunaClient(
                    app_id=settings.adzuna_app_id,
                    app_key=settings.adzuna_app_key,
                )
            )
            logger.debug("Adzuna client configured")

        if settings.jsearch_api_key:
            api_clients.append(
                JSearchClient(api_key=settings.jsearch_api_key)
            )
            logger.debug("JSearch client configured")

        # free external APIs (no credentials required)
        api_clients.append(ArbeitnowClient())
        logger.debug("Arbeitnow client configured (free, no key)")

        api_clients.append(RemotiveClient())
        logger.debug("Remotive client configured (free, no key)")

        if not api_clients:
            logger.warning("No job API clients configured — check your .env file")
            app_state["pipeline_status"] = "error"
            app_state["pipeline_error"] = "No job API credentials configured"
            return

        prefs_data = app_state.get("preferences", {})

        titles = prefs_data.get("titles")
        if isinstance(titles, str):
            titles = [t.strip() for t in titles.split(",") if t.strip()]
        for_titles = titles if titles else ["Developer"]

        location = prefs_data.get("location", "Paris")
        if not location:
            location = "Paris"

        raw_radius = prefs_data.get("radius_km", 30.0)
        try:
            radius_km = int(float(str(raw_radius).replace(",", ".")))
        except ValueError:
            radius_km = 30

        seniorities = prefs_data.get("seniority", [])
        seniority = "junior"
        if seniorities and isinstance(seniorities, list):
            valid = [s.lower() for s in seniorities if str(s).lower() in ["stagiaire", "alternant", "junior", "mid", "senior", "lead"]]
            seniority = valid[0] if valid else "junior"

        exclude = prefs_data.get("exclude_keywords")
        exclude_list = []
        if isinstance(exclude, str):
            exclude_list = [k.strip() for k in exclude.split(",") if k.strip()]
        elif isinstance(exclude, list):
            exclude_list = exclude

        app_state["pipeline_step"] = 2
        logger.info("Discovering jobs... %d sources", len(api_clients))
        logger.debug("Discovering jobs for titles=%s, location=%s", for_titles, location)

        preferences = SearchPreferences(
            titles=for_titles,
            location=location,
            radius_km=radius_km,
            remote_ok=prefs_data.get("remote_ok", False),
            seniority=seniority,
            exclude_keywords=exclude_list,
            max_results_per_source=20,
            language=prefs_data.get("language", "fr"),
            country="FR",
        )

        discovery_engine = JobDiscovery()
        postings = await discovery_engine.discover_jobs(
            preferences=preferences,
            api_clients=api_clients,
            rate_limiter=rate_limiter,
        )
        raw_count = len(postings)


        selected_seniority = {s.lower() for s in prefs_data.get("seniority", [])}

        if selected_seniority:
            # Build excluded keywords from seniority levels NOT selected
            excluded_keywords = set()
            for level, keywords in SENIORITY_KEYWORDS.items():
                if level not in selected_seniority:
                    excluded_keywords.update(keywords)

            import re as _re

            # Build word-boundary patterns to prevent false positives
            # e.g., "sr" must not match "SRE" or "Sri Lanka"
            excluded_patterns = [
                _re.compile(r'\b' + _re.escape(kw) + r'\b', _re.IGNORECASE)
                for kw in excluded_keywords
            ]

            # Filter postings
            filtered = []
            for p in postings:
                if any(pat.search(p.title) for pat in excluded_patterns):
                    continue
                filtered.append(p)

            postings = filtered
            logger.debug("Filtered to %d jobs after seniority filter", len(postings))

        # Pre-process: detect apprenticeship hidden inside "CDD" contracts.
        # France Travail uses "CDD - 12 Mois / Contrat apprentissage" which
        # is actually alternance, not a standard CDD.
        for i, p in enumerate(postings):
            contract_str = (p.contract_type or "").lower()
            description_start = (p.description_text or "")[:300].lower()

            # If contract contains both CDD and apprenticeship terms,
            # reclassify as alternance
            if "cdd" in contract_str and any(kw in contract_str or kw in description_start for kw in ALTERNANCE_KEYWORDS):
                postings[i] = p.model_copy(update={"contract_type": "alternance_apprentissage"})
                logger.debug("Reclassified %s from CDD to alternance (apprentissage detected)", p.id)

        # Filter by contract type if user selected specific types
        selected_contracts = prefs_data.get("contract_types", [])
        if selected_contracts:
            # Build allowed keywords from selected contract types
            allowed_keywords = set()
            for ct in selected_contracts:
                ct_lower = ct.lower()
                if ct_lower in CONTRACT_KEYWORDS:
                    allowed_keywords.update(CONTRACT_KEYWORDS[ct_lower])

            if allowed_keywords:
                before_count = len(postings)
                filtered_by_contract = []
                for p in postings:
                    title_lower = p.title.lower()
                    contract_str = (p.contract_type or "").lower()

                    # If the posting has an explicit contract type that matches, keep it
                    if contract_str and any(kw in contract_str for kw in allowed_keywords):
                        filtered_by_contract.append(p)
                        continue

                    # Detect contract type from the title for untagged postings.
                    # Signals are bare keywords -- no parentheses -- so they match
                    # any title format (e.g. '(Internship)', '- Internship', 'Internship').
                    title_contract_detected = None
                    for contract_type_key, signals in TITLE_CONTRACT_SIGNALS.items():
                        if any(signal in title_lower for signal in signals):
                            title_contract_detected = contract_type_key
                            break

                    if title_contract_detected:
                        selected_lower = [c.lower() for c in selected_contracts]
                        if title_contract_detected not in selected_lower:
                            continue  # Skip -- contract type not selected by user
                        else:
                            filtered_by_contract.append(p)
                            continue  # Explicitly selected -- accept and move on

                    # No contract signal detected in title -- keep (benefit of the doubt)
                    filtered_by_contract.append(p)

                postings = filtered_by_contract
                logger.debug("Contract filter: %d → %d postings", before_count, len(postings))

        if not postings:
            app_state["pipeline_status"] = "complete"
            app_state["pipeline_results"] = []
            app_state["last_run"] = datetime.now(tz=timezone.utc).isoformat()
            return

        # Pre-filter
        search_titles_lower = [t.lower() for t in prefs_data.get("titles", [])]

        # Build relevance keywords from user's search titles
        relevance_keywords = set()
        for title in search_titles_lower:
            relevance_keywords.update(title.split())
            relevance_keywords.add(title.replace(" ", "-"))
            relevance_keywords.add(title)

        stopwords = {"de", "du", "le", "la", "les", "the", "a", "an", "and", "et", "en", "in", "of", "-", "–"}
        relevance_keywords -= stopwords

        pre_filter_before = len(postings)
        relevant_postings = []
        skipped_postings = []

        for p in postings:
            title_lower = p.title.lower()
            title_words = set(title_lower.replace("-", " ").split())

            overlap = title_words & relevance_keywords

            if overlap:
                relevant_postings.append(p)
            elif p.description_text and any(kw in p.description_text.lower() for kw in search_titles_lower):
                relevant_postings.append(p)
            else:
                skipped_postings.append(p)

        postings = relevant_postings
        logger.debug(
            "Title pre-filter: %d → %d postings (skipped %d irrelevant, saved ~%d API calls)",
            pre_filter_before, len(postings), len(skipped_postings), len(skipped_postings)
        )

        # Cap JD parsing to keep pipeline under 5 minutes
        max_parse = settings.max_jd_parse
        if len(postings) > max_parse:
            logger.debug("Capping JD parsing at %d (had %d)", max_parse, len(postings))
            postings = postings[:max_parse]

        logger.info("Found %d jobs → %d after filtering", raw_count, len(postings))
        logger.info("Parsing job descriptions... %d jobs", len(postings))

        app_state["pipeline_step"] = 3
        gemini_service = GeminiLLMService(api_key=settings.gemini_api_key)
        embeddings_service = GeminiEmbeddingsService(api_key=settings.gemini_api_key)

        parsed_jds = {}
        for i, posting in enumerate(postings, 1):
            app_state["pipeline_step_detail"] = f"Description {i} sur {len(postings)}"
            try:
                await rate_limiter.acquire()
                parsed_jd = await parse_job_description(
                    description_text=posting.description_text,
                    job_id=posting.id,
                    gemini_service=gemini_service,
                )

                parsed_jd = parsed_jd.model_copy(update={
                    "job_id": posting.id,
                    "title": parsed_jd.title or posting.title,
                    "company": parsed_jd.company or posting.company,
                })

                parsed_jds[posting.id] = parsed_jd
                # save incrementally to avoid losing work on failure
                app_state["parsed_jds"] = parsed_jds
                save_pipeline_data()
            except GeminiAPIError as e:
                logger.warning("Failed to parse JD for %s: %s", posting.id, e)
                continue

        logger.debug("Parsed %d/%d job descriptions", len(parsed_jds), len(postings))

        # Patch missing company names from parsed JD data
        for posting in postings:
            if not posting.company or posting.company.strip() == "":
                parsed = parsed_jds.get(posting.id)
                if parsed and parsed.company:
                    # create copy to patch company on frozen model
                    idx = postings.index(posting)
                    postings[idx] = posting.model_copy(update={"company": parsed.company})
                    logger.debug("Patched company name for %s from JD: %s", posting.id, parsed.company)

        # label postings with no company name
        for i, posting in enumerate(postings):
            if not posting.company or posting.company.strip() == "":
                postings[i] = posting.model_copy(update={"company": "__MISSING_COMPANY__"})

        app_state["pipeline_step"] = 4
        resume = app_state["resume_profile"]
        alias_map = {}

        match_results = {}
        for i, posting in enumerate(postings, 1):
            app_state["pipeline_step_detail"] = f"{i}/{len(postings)}"
            if posting.id not in parsed_jds:
                continue
            jd = parsed_jds[posting.id]
            try:
                match_result = await analyse_cv(
                    resume=resume,
                    jd=jd,
                    embeddings_service=embeddings_service,
                    alias_map=alias_map,
                )
                match_results[posting.id] = match_result
            except (GeminiAPIError, ValueError, TypeError) as e:
                logger.warning("Failed to score %s: %s", posting.id, e)
                continue

        logger.info("Scoring matches... %d scored", len(match_results))

        app_state["pipeline_step"] = 5
        threshold = settings.match_threshold
        language = prefs_data.get("language", "fr")

        above_count = sum(1 for m in match_results.values() if m.overall_score >= threshold)
        logger.info("Running ATF analysis... %d above threshold", above_count)
        processed = 0

        for posting in postings:
            if posting.id not in match_results:
                continue
            match = match_results[posting.id]
            if match.overall_score >= threshold and posting.id in parsed_jds:
                processed += 1
                app_state["pipeline_step_detail"] = f"Analyse {processed} sur {above_count}"
                try:
                    await rate_limiter.acquire()
                    atf = await analyse_atf(
                        resume_text=str(resume.model_dump() if hasattr(resume, "model_dump") else resume),
                        jd_text=posting.description_text,
                        gemini_service=gemini_service,
                        language=language,
                    )
                    match_results[posting.id] = match.model_copy(update={"atf_analysis": atf})
                except GeminiAPIError as e:
                    logger.warning("ATF analysis failed for %s: %s", posting.id, e)
        app_state["pipeline_results"] = postings
        app_state["parsed_jds"] = parsed_jds
        app_state["match_results"] = match_results
        app_state["pipeline_status"] = "complete"
        app_state["last_run"] = datetime.now(tz=timezone.utc).isoformat()
        save_pipeline_data()

        import time
        duration = int(time.time() - app_state["pipeline_start_time"]) if "pipeline_start_time" in app_state else 0
        minutes = duration // 60
        seconds = duration % 60
        logger.info("Pipeline complete — %d jobs in %dm %ds", len(postings), minutes, seconds)

    except (GeminiAPIError, ValueError, TypeError) as e:
        app_state["pipeline_status"] = "error"
        app_state["pipeline_error"] = str(e)
        save_pipeline_data()
        logger.exception("Pipeline failed")
    finally:
        if "pipeline_start_time" in app_state:
            import time
            app_state["pipeline_duration"] = int(time.time() - app_state["pipeline_start_time"])
        if app_state.get("pipeline_status") == "running":
            app_state["pipeline_status"] = "error"
            app_state["pipeline_error"] = "Pipeline interrupted"

@router.post("/run")
async def run_pipeline(request: Request, background_tasks: BackgroundTasks) -> HTMLResponse:
    t = get_translations()

    if app_state.get("pipeline_status") == "running":
        return HTMLResponse(
            content=f'''
            <div class="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800 mb-3">
                ⏳ {t.get("pipeline_already_running", "Un pipeline est déjà en cours. Veuillez patienter.")}
            </div>
            <button hx-post="/pipeline/reset" hx-target="#pipeline-status" hx-swap="innerHTML"
                    class="text-sm text-red-600 hover:text-red-800 cursor-pointer bg-transparent border-none font-medium">
                {t.get("pipeline_force_reset", "Forcer la réinitialisation")}
            </button>''',
            status_code=200,
        )

    if not app_state.get("resume_profile"):
        return HTMLResponse(
            content=f'<div class="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-800">{t.get("error_no_resume", "Please upload a resume first.")}</div>',
            status_code=200,
        )

    if not app_state.get("preferences"):
        return HTMLResponse(
            content=f'<div class="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-800">{t.get("error_no_prefs", "Please save your preferences first.")}</div>',
            status_code=200,
        )

    import time
    app_state["pipeline_status"] = "running"
    app_state["pipeline_start_time"] = time.time()
    app_state["pipeline_step"] = 1
    app_state["pipeline_total_steps"] = 5

    background_tasks.add_task(execute_pipeline)

    return templates.TemplateResponse(
        request=request,
        name="partials/progress.html",
        context={
            "request": request,
            "t": t,
            "step": 1,
            "total": 5,
            "step_label": t.get("step_parsing", "Parsing resume..."),
        },
    )
@router.post("/reset")
async def reset_pipeline() -> HTMLResponse:
    app_state["pipeline_status"] = "idle"
    app_state["pipeline_step"] = 0
    app_state["pipeline_step_detail"] = ""
    t = get_translations()
    return HTMLResponse(
        content=f'''<div class="flex items-center gap-3.5">
            <button hx-post="/pipeline/run" hx-target="#pipeline-status" hx-swap="innerHTML"
                    class="bg-indigo-600 hover:bg-indigo-700 text-white border-none rounded-lg px-5 py-3 text-[15px] font-semibold cursor-pointer">
                {t.get("run_pipeline", "Run Pipeline")}
            </button>
        </div>''',
        status_code=200,
    )

@router.get("/progress")
async def get_progress(request: Request) -> HTMLResponse:
    t = get_translations()
    status = app_state.get("pipeline_status", "idle")
    step = app_state.get("pipeline_step", 0)

    step_labels = {
        1: t.get("step_parsing", "Parsing resume..."),
        2: t.get("step_discovering", "Discovering jobs..."),
        3: t.get("step_parsing_jds", "Parsing job descriptions..."),
        4: t.get("step_scoring", "Scoring matches..."),
        5: t.get("step_tailoring", "Tailoring CVs..."),
    }

    if status == "complete":
        job_count = len(app_state.get("pipeline_results", []))
        duration = app_state.get("pipeline_duration") or 0
        minutes, seconds = divmod(int(duration), 60)
        dur_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
        return HTMLResponse(
            content=f'''
            <div class="bg-green-50 border border-green-200 rounded-lg p-4 text-sm text-green-800"
                 hx-get="/" hx-trigger="load delay:2s" hx-target="body" hx-swap="outerHTML" hx-push-url="true">
                ✓ {t.get("pipeline_complete", "Pipeline complete")} — {job_count} {t.get("jobs_found_suffix", "jobs found")} ({dur_str})
            </div>''',
            status_code=200,
        )

    if status == "error":
        return HTMLResponse(
            content=f'<div class="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-800">{t.get("error_pipeline", "Pipeline failed.")}</div>',
            status_code=200,
        )
    step_detail = app_state.get("pipeline_step_detail", "")

    return templates.TemplateResponse(
        request=request,
        name="partials/progress.html",
        context={
            "request": request,
            "t": t,
            "step": step,
            "total": 5,
            "step_label": step_labels.get(step, ""),
            "step_detail": step_detail,
        },
    )
