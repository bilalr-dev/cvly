"""Pipeline orchestration: job discovery, parsing, scoring, and ATF analysis."""

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import HTMLResponse
from starlette.requests import Request

from backend.config import AppSettings, get_settings
from backend.models.preferences import RomeCodeLookupResult, SearchPreferences
from backend.modules.atf_analyser import analyse_atf
from backend.modules.cv_analyser import analyse_cv
from backend.modules.jd_parser import parse_job_description
from backend.modules.job_discovery import JobDiscovery
from backend.prompts import ROME_CODE_LOOKUP_PROMPT
from backend.services.gemini_embeddings import GeminiEmbeddingsService
from backend.services.gemini_llm import GeminiAPIError, GeminiLLMService
from backend.services.job_apis.adzuna import AdzunaClient
from backend.services.job_apis.arbeitnow import ArbeitnowClient
from backend.services.job_apis.france_travail import FranceTravailClient
from backend.services.job_apis.jobicy import JobicyClient
from backend.services.job_apis.jsearch import JSearchClient
from backend.services.job_apis.la_bonne_alternance import LaBonneAlternanceClient
from backend.services.job_apis.remotive import RemotiveClient
from backend.services.rate_limiter import AsyncRateLimiter
from backend.state import app_state, get_translations, save_pipeline_data, templates
from backend.utils.constants import (
    ALTERNANCE_KEYWORDS,
    API_PREFILTERED_SOURCES,
    APPRENTICESHIP_FALSE_POSITIVE,
    BROAD_CONTRACT_TYPES,
    CONTRACT_PREFERENCE_ALIASES,
    CONTRACT_TYPE_STRING_SIGNALS,
    DEFAULT_MAX_RESULTS_PER_SOURCE,
    DESCRIPTION_CONTRACT_SIGNALS,
    EDUCATION_TO_EQF_LEVEL,
    EN_FR_TITLE_VARIANTS,
    MIN_DESCRIPTION_LENGTH,
    PIPELINE_RATE_LIMIT_CALLS,
    PIPELINE_RATE_LIMIT_PERIOD_SECONDS,
    PIPELINE_TOTAL_STEPS,
    SENIORITY_KEYWORDS,
    TITLE_CONTRACT_SIGNALS,
    TITLE_DESC_PREVIEW_CHARS,
    TITLE_RELEVANCE_STOPWORDS,
    PipelineStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline")

# Cache title → ROME lookups across pipeline runs (avoids repeat Gemini calls)
_rome_cache: dict[str, list[str]] = {}
_ROME_CODE_RE = re.compile(r"^[A-Za-z]\d{4}$")


def _build_api_clients(settings: AppSettings) -> list[Any]:
    """Build and return the list of configured job API clients."""
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
    logger.debug("Arbeitnow client configured")

    api_clients.append(RemotiveClient())
    logger.debug("Remotive client configured")

    api_clients.append(JobicyClient())
    logger.debug("Jobicy client configured")

    if settings.la_bonne_alternance_api_key:
        api_clients.append(LaBonneAlternanceClient(api_key=settings.la_bonne_alternance_api_key))
        logger.debug("La Bonne Alternance client configured")

    return api_clients


def _detect_diploma_level(resume: Any) -> int | None:
    """Detect the highest EQF diploma level from a parsed resume."""
    if not resume:
        return None

    best: int | None = None
    # Longer keywords first so "bachelor" wins over "bac", "bac+5" over "bac"
    keywords = sorted(EDUCATION_TO_EQF_LEVEL.items(), key=lambda item: -len(item[0]))

    for edu in getattr(resume, "education", None) or []:
        degree = (getattr(edu, "degree", "") or "").lower()
        institution = (getattr(edu, "institution", "") or getattr(edu, "school", "") or "").lower()
        combined = f"{degree} {institution}"
        for keyword, level in keywords:
            if keyword in combined:
                best = level if best is None else max(best, level)
                break
    return best


def _resolve_rome_codes(titles: list[str], gemini_service: GeminiLLMService) -> list[str]:
    """Resolve job titles to ROME codes via Gemini (cached across pipeline runs)."""
    cache_key = ",".join(sorted(t.lower() for t in titles))
    if cache_key in _rome_cache:
        return _rome_cache[cache_key]

    prompt = ROME_CODE_LOOKUP_PROMPT.format(titles=", ".join(titles))
    try:
        result = gemini_service.generate_json(
            prompt=prompt,
            response_schema=RomeCodeLookupResult,
            temperature=0.0,
        )
        codes = [
            code.strip().upper()
            for code in result.rome_codes
            if isinstance(code, str) and _ROME_CODE_RE.match(code.strip())
        ][:5]
        if codes:
            _rome_cache[cache_key] = codes
            logger.info("ROME lookup for %s → %s", titles, codes)
            return codes
    except Exception as e:
        logger.warning("ROME lookup failed for %s: %s", titles, e)

    return []


def _needs_rome_codes(preferences: SearchPreferences) -> bool:
    """LBA needs ROME codes only for alternance/stage searches."""
    contracts = {str(c).lower() for c in (preferences.contracts or [])}
    return any(
        "alternance" in c or "apprentissage" in c or "stage" in c
        for c in contracts
    )


def _coerce_titles(raw: Any) -> list[str]:
    """Normalize a raw titles value to a list of non-empty stripped strings."""
    if isinstance(raw, str):
        return [t.strip() for t in raw.split(",") if t.strip()]
    if isinstance(raw, list):
        return list(raw)
    return []


def _coerce_radius(raw: Any) -> int:
    """Parse a radius value to a non-negative integer, defaulting to 0."""
    if raw is None or raw == "":
        return 0
    try:
        return max(0, int(float(str(raw).replace(",", "."))))
    except (ValueError, TypeError):
        return 0


def _coerce_seniority(raw: Any) -> str | None:
    """Return the first valid seniority keyword from a list, or None."""
    if not isinstance(raw, list):
        return None
    valid = [s.lower() for s in raw if str(s).lower() in SENIORITY_KEYWORDS]
    return valid[0] if valid else None


def _coerce_exclude_keywords(raw: Any) -> list[str]:
    """Normalize exclude_keywords to a list of stripped strings."""
    if isinstance(raw, str):
        return [k.strip() for k in raw.split(",") if k.strip()]
    if isinstance(raw, list):
        return raw
    return []


def _parse_preferences(
    prefs_data: dict,
    resume: Any = None,
) -> tuple[SearchPreferences, list[str], str]:
    """Parse user preferences dict into a SearchPreferences object and return routing keys."""
    settings = get_settings()

    for_titles = _coerce_titles(prefs_data.get("titles"))
    location = (prefs_data.get("location") or "").strip()

    preferences = SearchPreferences(
        titles=for_titles,
        location=location,
        radius_km=_coerce_radius(prefs_data.get("radius_km")),
        remote_ok=bool(prefs_data.get("remote_ok")),
        seniority=_coerce_seniority(prefs_data.get("seniority") or []),
        exclude_keywords=_coerce_exclude_keywords(prefs_data.get("exclude_keywords")),
        max_results_per_source=DEFAULT_MAX_RESULTS_PER_SOURCE,
        language=prefs_data.get("language") or settings.default_language,
        country=prefs_data.get("country") or settings.default_country,
        contracts=list(prefs_data.get("contract") or []),
        diploma_level=_detect_diploma_level(resume),
    )
    return preferences, for_titles, location


def _filter_by_seniority(postings: list, prefs_data: dict) -> list:
    """Filter postings based on excluded seniority levels."""
    selected_seniority = {s.lower() for s in (prefs_data.get("seniority") or [])}
    if not selected_seniority:
        return postings

    excluded_keywords = set()
    for level, keywords in SENIORITY_KEYWORDS.items():
        if level not in selected_seniority:
            excluded_keywords.update(keywords)

    # Alternance/stage ads are often titled "Junior … Apprenticeship".
    # Don't treat junior/intern markers as disqualifiers for those tracks.
    if selected_seniority & {"alternant", "stagiaire"}:
        excluded_keywords -= {"junior", "jr", "intern", "stage", "stagiaire"}

    excluded_patterns = [
        re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
        for kw in excluded_keywords
    ]

    filtered = []
    for p in postings:
        if any(pat.search(p.title) for pat in excluded_patterns):
            continue
        filtered.append(p)
    logger.debug("Filtered to %d jobs after seniority filter", len(filtered))
    return filtered


def _reclassify_contracts(postings: list) -> list:
    """Detect alternating/apprenticeship contracts mislabeled as CDD."""
    for i, p in enumerate(postings):
        contract_str = (p.contract_type or "").lower()
        description_start = (p.description_text or "")[:300].lower()

        if "cdd" in contract_str and any(kw in contract_str or kw in description_start for kw in ALTERNANCE_KEYWORDS):
            postings[i] = p.model_copy(update={"contract_type": "alternance_apprentissage"})
            logger.debug("Reclassified %s from CDD to alternance (apprentissage detected)", p.id)
    return postings


def _normalize_selected_contracts(selected_contracts: list) -> set[str]:
    normalized: set[str] = set()
    for raw in selected_contracts:
        key = str(raw).strip().lower()
        normalized.add(CONTRACT_PREFERENCE_ALIASES.get(key, key))
    return normalized


def _contract_type_from_string(contract_str: str) -> str | None:
    """Map free-text contract_type to a normalized key."""
    if not contract_str:
        return None
    for keywords, normalized in CONTRACT_TYPE_STRING_SIGNALS:
        if any(kw in contract_str for kw in keywords):
            return normalized
    return None


def _detect_contract_from_title(title_lower: str) -> str | None:
    for contract_key, signals in TITLE_CONTRACT_SIGNALS.items():
        if any(signal in title_lower for signal in signals):
            return contract_key
    return None


def _detect_contract_from_description(description: str) -> str | None:
    """Infer niche contract types from the start of the job description.

    Uses phrase-level signals to avoid false positives like
    continuous-learning mentions that contain apprenticeship vocabulary.
    """
    if not description:
        return None
    description_start = description[:500].lower()

    for contract_key in ("alternance_professionnalisation", "alternance_apprentissage"):
        phrases = DESCRIPTION_CONTRACT_SIGNALS[contract_key]
        if any(phrase in description_start for phrase in phrases):
            return contract_key

    # Standalone "alternance" as a contract mention (avoid bare "apprentissage")
    if (
        "alternance" in description_start
        and APPRENTICESHIP_FALSE_POSITIVE not in description_start
    ):
        return "alternance_apprentissage"

    for contract_key in ("stage", "freelance"):
        phrases = DESCRIPTION_CONTRACT_SIGNALS[contract_key]
        if any(phrase in description_start for phrase in phrases):
            return contract_key
    return None


def _resolve_effective_contract_type(posting) -> str | None:
    """Resolve contract type; niche title signals override broad API labels.

    France Travail often tags stages as CDI/CDD. A title like "STAGE - …"
    must win over that mislabel so niche-only filters stay accurate.
    """
    title_lower = posting.title.lower()
    title_type = _detect_contract_from_title(title_lower)
    if title_type and title_type not in BROAD_CONTRACT_TYPES:
        return title_type

    return (
        _contract_type_from_string((posting.contract_type or "").lower())
        or title_type
        or _detect_contract_from_description(posting.description_text or "")
    )


def _filter_by_contract(postings: list, selected_contracts: list) -> list:
    if not selected_contracts:
        return postings

    selected_normalized = _normalize_selected_contracts(selected_contracts)
    has_broad = bool(selected_normalized & BROAD_CONTRACT_TYPES)

    filtered = []
    for p in postings:
        effective_type = _resolve_effective_contract_type(p)

        if effective_type:
            if effective_type in selected_normalized:
                filtered.append(p)
        elif has_broad:
            # Unknown type: benefit of the doubt only when CDI/CDD selected
            filtered.append(p)

    logger.debug(
        "Contract filter: %d → %d (selected=%s, strict=%s)",
        len(postings),
        len(filtered),
        selected_normalized,
        not has_broad,
    )
    return filtered


def _title_relevance_keywords(search_titles: list[str]) -> set[str]:
    """Build title-token keywords, including known EN→FR title variants."""
    relevance_keywords: set[str] = set()
    search_titles_lower = [t.lower() for t in search_titles]

    for title in search_titles_lower:
        # Split on spaces and hyphens so "full-stack" matches title tokens
        # "full" / "stack" after title_lower.replace("-", " ")
        relevance_keywords.update(title.replace("-", " ").split())
        relevance_keywords.add(title.replace(" ", "-"))
        relevance_keywords.add(title)

        french = EN_FR_TITLE_VARIANTS.get(title.strip())
        if french:
            relevance_keywords.update(french.replace("-", " ").split())
            relevance_keywords.add(french)

    return relevance_keywords - TITLE_RELEVANCE_STOPWORDS


def _filter_by_title_relevance(postings: list, search_titles: list[str]) -> list:
    """Pre-filter by title relevance to reduce JD parsing API calls."""
    if not postings:
        return []
    if not search_titles:
        return postings

    search_titles_lower = [t.lower() for t in search_titles]
    relevance_keywords = _title_relevance_keywords(search_titles)

    pre_filter_before = len(postings)
    relevant_postings = []
    skipped_postings = []

    for p in postings:
        # Trust API-level filtering (e.g. ROME codes) for these sources
        if getattr(p, "source", None) in API_PREFILTERED_SOURCES:
            relevant_postings.append(p)
            continue

        title_lower = p.title.lower()
        title_words = set(title_lower.replace("-", " ").split())
        overlap = title_words & relevance_keywords

        if overlap:
            relevant_postings.append(p)
        elif getattr(p, "source", None) != "jobicy" and p.description_text:
            # Only check the opening of the description. Full text often
            # buries search terms in company blurbs for unrelated roles.
            # Skip Jobicy: its tag search already injects those blurbs.
            desc_preview = p.description_text[:TITLE_DESC_PREVIEW_CHARS].lower()
            if any(kw in desc_preview for kw in search_titles_lower):
                relevant_postings.append(p)
            else:
                skipped_postings.append(p)
        else:
            skipped_postings.append(p)

    logger.debug(
        "Title pre-filter: %d → %d postings (skipped %d irrelevant, saved ~%d API calls)",
        pre_filter_before, len(relevant_postings), len(skipped_postings), len(skipped_postings)
    )
    return relevant_postings


def _filter_postings(
    postings: list,
    prefs_data: dict,
    for_titles: list[str],
    max_parse: int,
) -> list:
    """Apply all post-discovery filters in sequence."""
    postings = _filter_by_seniority(postings, prefs_data)
    postings = _reclassify_contracts(postings)
    postings = _filter_by_contract(postings, prefs_data.get("contract") or [])
    postings = _filter_by_title_relevance(postings, for_titles)

    before = len(postings)
    postings = [
        p for p in postings
        if len((p.description_text or "").strip()) >= MIN_DESCRIPTION_LENGTH
    ]
    logger.debug("Description filter: %d -> %d", before, len(postings))

    if len(postings) > max_parse:
        logger.info("Capping at %d postings for JD parsing", max_parse)
        postings = postings[:max_parse]

    return postings


async def _parse_job_descriptions(postings: list, gemini_service: GeminiLLMService, rate_limiter: AsyncRateLimiter, app_state: dict) -> dict:
    """Parse all valid job descriptions via LLM and return a dict of parsed representations."""
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
            app_state["parsed_jds"] = parsed_jds
        except GeminiAPIError as e:
            logger.warning("Failed to parse JD for %s: %s", posting.id, e)
            continue

    logger.debug("Parsed %d/%d job descriptions", len(parsed_jds), len(postings))
    return parsed_jds


def _patch_company_names(postings: list, parsed_jds: dict) -> list:
    """Patch missing company names directly into standard raw jobs list."""
    for i, posting in enumerate(postings):
        if not posting.company or posting.company.strip() == "":
            parsed = parsed_jds.get(posting.id)
            if parsed and parsed.company:
                postings[i] = posting.model_copy(update={"company": parsed.company})
                logger.debug("Patched company name for %s from JD: %s", posting.id, parsed.company)

    # label postings with no company name
    for i, posting in enumerate(postings):
        if not posting.company or posting.company.strip() == "":
            postings[i] = posting.model_copy(update={"company": "__MISSING_COMPANY__"})

    return postings


async def _score_matches(postings: list, parsed_jds: dict, resume: Any, embeddings_service: GeminiEmbeddingsService, alias_map: dict, app_state: dict) -> dict:
    """Score candidate resume matches against all parsed JDs via vector engine."""
    match_results = {}
    for i, posting in enumerate(postings, 1):
        app_state["pipeline_step_detail"] = f"{i}/{len(postings)}"
        jd = parsed_jds.get(posting.id)
        if jd is None:
            continue
        try:
            match_result = await analyse_cv(
                resume=resume,
                jd=jd,
                embeddings_service=embeddings_service,
                alias_map=alias_map,
            )
            if match_result is not None:
                match_results[posting.id] = match_result
        except (GeminiAPIError, ValueError, TypeError) as e:
            logger.warning("Failed to score %s: %s", posting.id, e)
            continue

    logger.info("Scoring matches... %d scored", len(match_results))
    return match_results


async def _run_atf_analysis(postings: list, match_results: dict, parsed_jds: dict, resume: Any, gemini_service: GeminiLLMService, rate_limiter: AsyncRateLimiter, threshold: int, language: str, app_state: dict) -> dict:
    """Generate high-level ATF pipeline summaries for passing jobs."""
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
    return match_results


def _preferences_incomplete(prefs_data: dict) -> bool:
    """True if titles or location are missing."""
    titles_val = prefs_data.get("titles")
    if isinstance(titles_val, str):
        has_titles = bool(titles_val.strip())
    elif isinstance(titles_val, list):
        has_titles = bool(titles_val)
    else:
        has_titles = False
    has_location = bool((prefs_data.get("location") or "").strip())
    return not has_titles or not has_location


def _split_approved_postings(
    postings: list,
    approved: set,
    previous_by_id: dict,
) -> tuple[list, list]:
    """Pull already-approved jobs aside so we don't re-score them."""
    if not approved:
        return [], postings

    approved_postings: list = []
    seen: set[str] = set()
    for p in postings:
        if p.id in approved and p.id not in seen:
            approved_postings.append(p)
            seen.add(p.id)
    for jid in approved:
        if jid not in seen and jid in previous_by_id:
            approved_postings.append(previous_by_id[jid])
            seen.add(jid)

    before = len(postings)
    remaining = [p for p in postings if p.id not in approved]
    if before > len(remaining):
        logger.debug("Skipped %d already-approved jobs", before - len(remaining))
    return approved_postings, remaining


def _finalize_approved_only(
    approved_postings: list,
    previous_matches: dict,
    previous_jds: dict,
) -> None:
    """Save approved jobs and mark the run complete when nothing new remains."""
    kept_matches = {
        p.id: previous_matches[p.id]
        for p in approved_postings
        if p.id in previous_matches
    }
    kept_jds = {
        p.id: previous_jds[p.id]
        for p in approved_postings
        if p.id in previous_jds
    }
    app_state["pipeline_results"] = approved_postings
    app_state["match_results"] = kept_matches
    app_state["parsed_jds"] = kept_jds
    app_state["pipeline_status"] = PipelineStatus.COMPLETE
    app_state["last_run"] = datetime.now(tz=timezone.utc).isoformat()
    save_pipeline_data()


def _merge_approved_into_results(
    approved_postings: list,
    postings: list,
    match_results: dict,
    parsed_jds: dict,
    previous_matches: dict,
    previous_jds: dict,
) -> None:
    """Put approved jobs back into the results set and persist the run."""
    for p in approved_postings:
        if p.id in previous_matches and p.id not in match_results:
            match_results[p.id] = previous_matches[p.id]
        if p.id in previous_jds and p.id not in parsed_jds:
            parsed_jds[p.id] = previous_jds[p.id]

    app_state["pipeline_results"] = approved_postings + postings
    app_state["parsed_jds"] = parsed_jds
    app_state["match_results"] = match_results
    app_state["pipeline_status"] = PipelineStatus.COMPLETE
    app_state["last_run"] = datetime.now(tz=timezone.utc).isoformat()
    save_pipeline_data()

    duration = (
        int(time.time() - app_state["pipeline_start_time"])
        if "pipeline_start_time" in app_state
        else 0
    )
    minutes, seconds = divmod(duration, 60)
    logger.info(
        "Pipeline complete : %d jobs in %dm %ds",
        len(app_state["pipeline_results"]),
        minutes,
        seconds,
    )


async def execute_pipeline() -> None:
    """Orchestrate the full job discovery and analysis pipeline."""
    settings = get_settings()
    rate_limiter = AsyncRateLimiter(
        max_calls=PIPELINE_RATE_LIMIT_CALLS,
        period_seconds=PIPELINE_RATE_LIMIT_PERIOD_SECONDS,
    )

    try:
        app_state["pipeline_status"] = PipelineStatus.RUNNING
        app_state["pipeline_step"] = 1
        app_state["pipeline_step_detail"] = ""
        logger.info("Pipeline started")

        api_clients = _build_api_clients(settings)
        if not api_clients:
            logger.warning("No job API clients configured, check your .env file")
            app_state["pipeline_status"] = PipelineStatus.ERROR
            app_state["pipeline_error"] = "No job API credentials configured"
            return

        app_state["pipeline_step"] = 2
        prefs_data = app_state.get("preferences") or {}
        if _preferences_incomplete(prefs_data):
            t = get_translations()
            app_state["pipeline_status"] = PipelineStatus.ERROR
            app_state["pipeline_error"] = t.get(
                "error_no_preferences",
                "Please configure your search preferences first",
            )
            return

        preferences, for_titles, location = _parse_preferences(
            prefs_data,
            resume=app_state.get("resume_profile"),
        )

        gemini_service = GeminiLLMService(api_key=settings.gemini_api_key)
        if (
            settings.la_bonne_alternance_api_key
            and for_titles
            and _needs_rome_codes(preferences)
        ):
            rome_codes = _resolve_rome_codes(for_titles, gemini_service)
            preferences = preferences.model_copy(update={"rome_codes": rome_codes})

        logger.info("Discovering jobs... %d sources", len(api_clients))
        logger.debug("Discovering jobs for titles=%s, location=%s", for_titles, location)

        discovery_engine = JobDiscovery()
        postings = await discovery_engine.discover_jobs(
            preferences=preferences, api_clients=api_clients,
        )
        raw_count = len(postings)

        previous_by_id = {p.id: p for p in app_state.get("pipeline_results", [])}
        previous_matches = dict(app_state.get("match_results", {}))
        previous_jds = dict(app_state.get("parsed_jds", {}))
        approved_postings, postings = _split_approved_postings(
            postings,
            app_state.get("approved_jobs", set()),
            previous_by_id,
        )

        postings = _filter_postings(postings, prefs_data, for_titles, settings.max_jd_parse)
        if not postings:
            _finalize_approved_only(approved_postings, previous_matches, previous_jds)
            return

        logger.info("Found %d jobs → %d after filtering", raw_count, len(postings))
        logger.info("Parsing job descriptions... %d jobs", len(postings))

        app_state["pipeline_step"] = 3
        embeddings_service = GeminiEmbeddingsService(api_key=settings.gemini_api_key)
        parsed_jds = await _parse_job_descriptions(
            postings, gemini_service, rate_limiter, app_state,
        )

        language = prefs_data.get("language") or settings.default_language
        postings = _patch_company_names(postings, parsed_jds)

        app_state["pipeline_step"] = 4
        resume = app_state["resume_profile"]
        match_results = await _score_matches(
            postings, parsed_jds, resume, embeddings_service, {}, app_state,
        )

        app_state["pipeline_step"] = 5
        match_results = await _run_atf_analysis(
            postings, match_results, parsed_jds, resume,
            gemini_service, rate_limiter, settings.match_threshold, language, app_state,
        )

        _merge_approved_into_results(
            approved_postings, postings, match_results, parsed_jds,
            previous_matches, previous_jds,
        )

    except (GeminiAPIError, ValueError, TypeError) as e:
        app_state["pipeline_status"] = PipelineStatus.ERROR
        app_state["pipeline_error"] = str(e)
        save_pipeline_data()
        logger.warning("Pipeline failed: %s", e)
    finally:
        if "pipeline_start_time" in app_state:
            app_state["pipeline_duration"] = int(time.time() - app_state["pipeline_start_time"])
        if app_state.get("pipeline_status") == PipelineStatus.RUNNING:
            app_state["pipeline_status"] = PipelineStatus.ERROR
            app_state["pipeline_error"] = "Pipeline interrupted"


@router.post("/run")
async def run_pipeline(request: Request, background_tasks: BackgroundTasks) -> HTMLResponse:
    t = get_translations()

    if app_state.get("pipeline_status") == PipelineStatus.RUNNING:
        return HTMLResponse(
            content=f"""
            <div class="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800 mb-3">
                ⏳ {t.get("pipeline_already_running", "Un pipeline est déjà en cours. Veuillez patienter.")}
            </div>
            <button hx-post="/pipeline/reset" hx-target="#pipeline-status" hx-swap="innerHTML"
                    class="text-sm text-red-600 hover:text-red-800 cursor-pointer bg-transparent border-none font-medium">
                {t.get("pipeline_force_reset", "Forcer la réinitialisation")}
            </button>""",
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
    app_state["pipeline_status"] = PipelineStatus.RUNNING
    app_state["pipeline_start_time"] = time.time()
    app_state["pipeline_step"] = 1
    app_state["pipeline_total_steps"] = PIPELINE_TOTAL_STEPS

    background_tasks.add_task(execute_pipeline)

    return templates.TemplateResponse(
        request=request,
        name="partials/progress.html",
        context={
            "request": request,
            "t": t,
            "step": 1,
            "total": PIPELINE_TOTAL_STEPS,
            "step_label": t.get("step_parsing", "Parsing resume..."),
        },
    )

@router.post("/reset")
async def reset_pipeline() -> HTMLResponse:
    app_state["pipeline_status"] = PipelineStatus.IDLE
    app_state["pipeline_step"] = 0
    app_state["pipeline_step_detail"] = ""
    t = get_translations()
    return HTMLResponse(
        content=f"""<div class="flex items-center gap-3.5">
            <button hx-post="/pipeline/run" hx-target="#pipeline-status" hx-swap="innerHTML"
                    class="btn-primary px-5 py-3 text-[15px]">
                {t.get("run_pipeline", "Run Pipeline")}
            </button>
        </div>""",
        status_code=200,
    )

@router.get("/progress")
async def get_progress(request: Request) -> HTMLResponse:
    t = get_translations()
    status = app_state.get("pipeline_status", PipelineStatus.IDLE)
    step = app_state.get("pipeline_step", 0)

    step_labels = {
        1: t.get("step_parsing", "Parsing resume..."),
        2: t.get("step_discovering", "Discovering jobs..."),
        3: t.get("step_parsing_jds", "Parsing job descriptions..."),
        4: t.get("step_scoring", "Scoring matches..."),
        5: t.get("step_tailoring", "Tailoring CVs..."),
    }

    if status == PipelineStatus.COMPLETE:
        job_count = len(app_state.get("pipeline_results", []))
        duration = app_state.get("pipeline_duration") or 0
        minutes, seconds = divmod(int(duration), 60)
        dur_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
        return HTMLResponse(
            content=f"""
            <div class="bg-green-50 border border-green-200 rounded-lg p-4 text-sm text-green-800"
                 hx-get="/" hx-trigger="load delay:2s" hx-target="body" hx-swap="outerHTML" hx-push-url="true">
                ✓ {t.get("pipeline_complete", "Pipeline complete")}: {job_count} {t.get("jobs_found_suffix", "jobs found")} ({dur_str})
            </div>""",
            status_code=200,
        )

    if status == PipelineStatus.ERROR:
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
            "total": PIPELINE_TOTAL_STEPS,
            "step_label": step_labels.get(step, ""),
            "step_detail": step_detail,
        },
    )
