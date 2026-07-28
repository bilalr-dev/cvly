from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

_templates_dir = BASE_DIR / "frontend" / "templates"
_templates_dir.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(_templates_dir))

TRANSLATIONS = {
    "fr": {
        "nav_dashboard": "Tableau de bord",
        "nav_settings": "Paramètres",
        "nav_results": "Résultats",
        "dashboard_title": "Tableau de bord",
        "jobs_found": "Offres trouvées",
        "avg_score": "Score moyen",
        "above_threshold": "Au-dessus du seuil (50+)",
        "run_pipeline": "Lancer le pipeline",
        "open_sheet": "Ouvrir Google Sheet ↗",
        "settings_title": "Paramètres",
        "resume_section": "CV",
        "resume_parsed": "CV analysé avec succès",
        "reupload": "Recharger le CV",
        "drop_zone_title": "Déposez votre CV ici, ou cliquez pour importer",
        "drop_zone_sub": "Formats .pdf et .docx acceptés",
        "pref_title": "Préférences de recherche",
        "field_titles": "Intitulés de poste ciblés",
        "field_location": "Localisation",
        "field_radius": "Rayon (km)",
        "field_remote": "Télétravail accepté",
        "field_seniority": "Séniorité",
        "field_contract": "Type de contrat",
        "field_exclude": "Mots-clés à exclure",
        "field_language": "Langue de sortie",
        "save_prefs": "Enregistrer les préférences",
        "results_title": "Résultats",
        "col_company": "Entreprise",
        "col_title": "Poste",
        "col_algo": "Algo",
        "col_recruiter": "Recruteur",
        "col_location": "Lieu",
        "col_contract": "Contrat",
        "col_date": "Date",
        "col_source": "Source",
        "col_actions": "Actions",
        "sort_by": "Trier par :",
        "empty_title": "Aucun résultat pour l'instant.",
        "empty_sub": "Lancez le pipeline depuis le tableau de bord.",
        "empty_link": "Aller au tableau de bord →",
        "back_to_results": "Retour aux résultats",
        "original_posting": "Voir l'offre originale →",
        "bullet_comparison": "Comparaison des points clés",
        "cover_letter": "Lettre de motivation",
        "approve_btn": "Approuver et enregistrer",
        "edit_btn": "Modifier",
        "cancel_edit": "Annuler",
        "save_edits": "Enregistrer les modifications",
        "tailored_resume_title": "CV adapté",
        "copy_resume": "Copier le CV",
        "regenerate_btn": "Régénérer",
        "footer": "Cvly - Agent IA de candidature",
        "last_run": "Dernière exécution : ",
        "no_pipeline_run": "Aucune exécution pour l'instant",
        "settings_subtitle": "Configurez votre CV et vos préférences de recherche.",
        "empty_results_msg": "Essayez d'élargir votre rayon ou votre séniorité.",
        "filter_btn": "Filtrer",
        "original_title": "Original",
        "hallucination_title": "Risque d'hallucination",
        "hallucination_desc": "Veuillez vérifier l'exactitude des points personnalisés.",
        "error_rate_limit": "Limite d'API atteinte. Veuillez patienter 30 secondes et réessayer.",
        "error_parsing": "Échec de l'analyse du CV. Veuillez réessayer.",
        "error_pipeline": "Une erreur est survenue lors de l'exécution du pipeline. Veuillez réessayer.",
        "error_upload_failed": "Échec de l'importation du fichier.",
        "resume_name_label": "Nom",
        "resume_profile_label": "Type de profil",
        "resume_skills_label": "Compétences détectées",
        "resume_experience_label": "Expérience",
        "resume_education_label": "Éducation",
        "skills_suffix": "compétences",
        "roles_suffix": "postes",
        "delete_resume": "Supprimer le CV",
        "prefs_saved": "Préférences enregistrées",
        "error_no_resume": "Veuillez d'abord importer un CV.",
        "error_no_prefs": "Veuillez d'abord enregistrer vos préférences.",
        "step_prefix": "Étape",
        "step_parsing": "Analyse du CV...",
        "step_discovering": "Recherche d'offres...",
        "step_parsing_jds": "Analyse des descriptions...",
        "step_scoring": "Calcul des scores...",
        "step_tailoring": "Adaptation du CV...",
        "pipeline_complete": "Pipeline terminé",
        "jobs_found_suffix": "offres trouvées",
        "pipeline_running_status": "Pipeline en cours d'exécution...",
        "pipeline_running_msg": "Le pipeline est en cours d'exécution. Cette opération peut prendre quelques minutes selon le nombre d'offres trouvées.",
        "pipeline_already_running": "Un pipeline est déjà en cours d'exécution. Veuillez patienter.",
        "pipeline_force_reset": "Forcer la réinitialisation",
        "last_run_prefix": "Dernière exécution :",
        "no_runs_yet": "Aucune exécution pour l'instant",
        "atf_analysis_title": "Analyse ATF",
        "strengths_title": "Points forts",
        "weaknesses_title": "Points faibles",
        "keywords_gap_title": "Analyse des mots-clés",
        "matched_keywords_title": "Mots-clés correspondants",
        "missing_keywords_title": "Mots-clés manquants",
        "close_details": "Fermer les détails",
        "no_atf_available": "Aucune analyse ATF disponible pour cette offre.",
        "seniority_label": "Séniorité",
        "recommendation_label": "Recommandation",

        "hallucination_section_title": "Points à vérifier",
        "unfillable": "Mots-clés non intégrables :",
        "error_tailoring": "Échec de la personnalisation. Veuillez réessayer.",
        "error_no_data": "CV ou description de poste indisponible pour la personnalisation.",
        "no_tailoring_data": "Aucune donnée de personnalisation disponible.",
        "ai_disclaimer": "Ce contenu a été généré par l'intelligence artificielle. Relisez attentivement chaque point et corrigez toute information inexacte avant d'envoyer votre candidature. Vous êtes le seul garant de l'exactitude de votre CV.",
    },
    "en": {
        "nav_dashboard": "Dashboard",
        "nav_settings": "Settings",
        "nav_results": "Results",
        "dashboard_title": "Dashboard",
        "jobs_found": "Jobs Found",
        "avg_score": "Avg Match Score",
        "above_threshold": "Above Threshold (50+)",
        "run_pipeline": "Run Pipeline",
        "open_sheet": "Open Google Sheet ↗",
        "settings_title": "Settings",
        "resume_section": "Resume",
        "resume_parsed": "Resume parsed successfully",
        "reupload": "Re-upload resume",
        "drop_zone_title": "Drop your resume here, or click to upload",
        "drop_zone_sub": "Accepts .pdf and .docx",
        "pref_title": "Search Preferences",
        "field_titles": "Target job titles",
        "field_location": "Location",
        "field_radius": "Radius (km)",
        "field_remote": "Remote OK",
        "field_seniority": "Seniority",
        "field_contract": "Contract type",
        "field_exclude": "Exclude keywords",
        "field_language": "Output language",
        "save_prefs": "Save Preferences",
        "results_title": "Results",
        "col_company": "Company",
        "col_title": "Title",
        "col_algo": "Algo",
        "col_recruiter": "Recruiter",
        "col_location": "Location",
        "col_contract": "Contract",
        "col_date": "Date",
        "col_source": "Source",
        "col_actions": "Actions",
        "sort_by": "Sort by:",
        "empty_title": "No results yet.",
        "empty_sub": "Run the pipeline from the Dashboard to discover matching jobs.",
        "empty_link": "Go to Dashboard →",
        "back_to_results": "Back to Results",
        "original_posting": "View original posting →",
        "bullet_comparison": "Bullet Comparison",
        "cover_letter": "Cover Letter",
        "approve_btn": "Approve & Save",
        "edit_btn": "Edit",
        "cancel_edit": "Cancel",
        "save_edits": "Save edits",
        "tailored_resume_title": "Tailored Resume",
        "copy_resume": "Copy Resume",
        "regenerate_btn": "Regenerate",
        "footer": "Cvly - AI Job Application Agent",
        "last_run": "Last run: ",
        "no_pipeline_run": "No pipeline runs yet",
        "settings_subtitle": "Configure your resume and job search preferences.",
        "empty_results_msg": "Try relaxing your location radius or seniority levels.",
        "filter_btn": "Filter",
        "original_title": "Original",
        "hallucination_title": "Hallucination Risk",
        "hallucination_desc": "Please verify the tailored points for accuracy.",
        "error_rate_limit": "API rate limit reached. Please wait 30 seconds and try again.",
        "error_parsing": "Failed to parse resume. Please try again.",
        "error_pipeline": "An error occurred while running the pipeline. Please try again.",
        "error_upload_failed": "File upload failed.",
        "resume_name_label": "Name",
        "resume_profile_label": "Profile type",
        "resume_skills_label": "Skills detected",
        "resume_experience_label": "Experience",
        "resume_education_label": "Education",
        "skills_suffix": "skills",
        "roles_suffix": "roles",
        "delete_resume": "Delete resume",
        "prefs_saved": "Preferences saved",
        "error_no_resume": "Please upload a resume first.",
        "error_no_prefs": "Please save your preferences first.",
        "step_prefix": "Step",
        "step_parsing": "Parsing resume...",
        "step_discovering": "Discovering jobs...",
        "step_parsing_jds": "Parsing job descriptions...",
        "step_scoring": "Scoring matches...",
        "step_tailoring": "Tailoring CVs...",
        "pipeline_complete": "Pipeline complete",
        "jobs_found_suffix": "jobs found",
        "pipeline_running_status": "Pipeline is running...",
        "pipeline_running_msg": "Pipeline is running. This may take a few minutes depending on the number of jobs found.",
        "pipeline_already_running": "A pipeline is already running. Please wait.",
        "pipeline_force_reset": "Force reset",
        "last_run_prefix": "Last run: ",
        "no_runs_yet": "No pipeline runs yet",
        "atf_analysis_title": "ATF Analysis",
        "strengths_title": "Strengths",
        "weaknesses_title": "Weaknesses",
        "keywords_gap_title": "Keywords Gap Analysis",
        "matched_keywords_title": "Matched keywords",
        "missing_keywords_title": "Missing keywords",
        "close_details": "Close details",
        "no_atf_available": "No ATF analysis available for this job.",
        "seniority_label": "Seniority",
        "recommendation_label": "Recommendation",

        "hallucination_section_title": "Points to review",
        "unfillable": "Keywords that could not be incorporated:",
        "error_tailoring": "Tailoring failed. Please try again.",
        "error_no_data": "Resume or job description not available for tailoring.",
        "no_tailoring_data": "No tailoring data available.",
        "ai_disclaimer": "This content was generated by artificial intelligence. Carefully review every point and correct any inaccurate information before submitting your application. You are solely responsible for the accuracy of your CV.",
    },
}

import os  # noqa: E402
if "PYTEST_CURRENT_TEST" in os.environ or "pytest" in os.environ.get("_", "").lower():
    import tempfile
    _STATE_DIR = Path(tempfile.gettempdir()) / "cvly_test_cache"
else:
    _STATE_DIR = Path(__file__).resolve().parent.parent / "cache"

_RESUME_FILE = _STATE_DIR / "resume_profile.json"
_PREFERENCES_FILE = _STATE_DIR / "preferences.json"


def save_resume_profile(profile: object) -> None:
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    _RESUME_FILE.write_text(
        json.dumps(profile.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_resume_profile() -> dict | None:
    if _RESUME_FILE.exists():
        return json.loads(_RESUME_FILE.read_text(encoding="utf-8"))
    return None


def delete_resume_profile() -> None:
    app_state["resume_profile"] = None
    if _RESUME_FILE.exists():
        _RESUME_FILE.unlink()


def save_preferences(prefs: dict) -> None:
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    _PREFERENCES_FILE.write_text(
        json.dumps(prefs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_preferences() -> dict | None:
    if _PREFERENCES_FILE.exists():
        return json.loads(_PREFERENCES_FILE.read_text(encoding="utf-8"))
    return None


app_state: dict[str, Any] = {
    "resume_profile": None,
    "preferences": None,
    "pipeline_results": [],
    "tailored_outputs": {},
    "match_results": {},
    "parsed_jds": {},
    "last_run": None,
    "language": "fr",
}

_saved_prefs = load_preferences()
if _saved_prefs:
    app_state["preferences"] = _saved_prefs

_saved_resume = load_resume_profile()
if _saved_resume:
    from backend.models.resume import ResumeProfile
    try:
        app_state["resume_profile"] = ResumeProfile.model_validate(_saved_resume)
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning("Failed to load resume profile: %s", e)


_PIPELINE_RESULTS_FILE = _STATE_DIR / "pipeline_results.json"
_MATCH_RESULTS_FILE = _STATE_DIR / "match_results.json"
_PARSED_JDS_FILE = _STATE_DIR / "parsed_jds.json"
_PIPELINE_META_FILE = _STATE_DIR / "pipeline_meta.json"

def save_pipeline_data() -> None:
    """Save pipeline results, match results, and parsed JDs to disk."""
    _STATE_DIR.mkdir(parents=True, exist_ok=True)

    # Save postings
    postings = app_state.get("pipeline_results", [])
    _PIPELINE_RESULTS_FILE.write_text(
        json.dumps([p.model_dump() for p in postings], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Save match results
    matches = app_state.get("match_results", {})
    _MATCH_RESULTS_FILE.write_text(
        json.dumps({k: v.model_dump() for k, v in matches.items()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Save parsed JDs
    jds = app_state.get("parsed_jds", {})
    _PARSED_JDS_FILE.write_text(
        json.dumps({k: v.model_dump() for k, v in jds.items()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Save meta (last_run, status, duration, error)
    meta = {
        "last_run": app_state.get("last_run"),
        "pipeline_status": app_state.get("pipeline_status", "idle"),
        "pipeline_duration": app_state.get("pipeline_duration"),
        "pipeline_error": app_state.get("pipeline_error")
    }
    _PIPELINE_META_FILE.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_pipeline_data() -> None:
    """Load pipeline data from disk if it exists."""
    if _PIPELINE_RESULTS_FILE.exists():
        try:
            from backend.models.job import RawJobPosting
            raw = json.loads(_PIPELINE_RESULTS_FILE.read_text(encoding="utf-8"))
            app_state["pipeline_results"] = [RawJobPosting.model_validate(p) for p in raw]
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning("Failed to load pipeline results: %s", e)

    if _MATCH_RESULTS_FILE.exists():
        try:
            from backend.models.match import MatchResult
            raw = json.loads(_MATCH_RESULTS_FILE.read_text(encoding="utf-8"))
            app_state["match_results"] = {k: MatchResult.model_validate(v) for k, v in raw.items()}
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning("Failed to load match results: %s", e)

    if _PARSED_JDS_FILE.exists():
        try:
            from backend.models.job import ParsedJobDescription
            raw = json.loads(_PARSED_JDS_FILE.read_text(encoding="utf-8"))
            app_state["parsed_jds"] = {k: ParsedJobDescription.model_validate(v) for k, v in raw.items()}
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning("Failed to load parsed JDs: %s", e)

    if _PIPELINE_META_FILE.exists():
        try:
            meta = json.loads(_PIPELINE_META_FILE.read_text(encoding="utf-8"))
            app_state["last_run"] = meta.get("last_run")
            status = meta.get("pipeline_status", "idle")
            # Don't restore "running" — it means the server crashed mid-pipeline
            app_state["pipeline_status"] = "complete" if status == "running" else status
            app_state["pipeline_duration"] = meta.get("pipeline_duration")
            app_state["pipeline_error"] = meta.get("pipeline_error")
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning("Failed to load pipeline meta: %s", e)


load_pipeline_data()


def get_translations() -> dict[str, str]:
    lang = app_state.get("language", "fr")
    return TRANSLATIONS.get(lang, TRANSLATIONS["fr"])
