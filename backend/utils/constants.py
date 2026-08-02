"""Shared constants, enums, keyword maps, and configuration values."""
from __future__ import annotations

from enum import StrEnum

# Preview template / translation placeholders
PREVIEW_TEMPLATE: str = "preview.html"
TRANSLATION_TARGET_LANGUAGE_PLACEHOLDER: str = "{target_language}"
TRANSLATION_CONTENT_PLACEHOLDER: str = "{content}"

# Sheets tracker
SHEETS_NOT_CONNECTED_MSG: str = "Not connected. Call connect() first."

# UI limits and logic
MIN_BULLET_LENGTH: int = 25
MAX_BULLETS_PER_ROLE: int = 4
MAX_ROLES_LIMIT: int = 999
MAX_KEYWORD_INJECTION_WORDS: int = 5
CRITICAL_REVIEW_ACHIEVEMENT_LIMIT: int = 10

# Prompt placeholder fallbacks (shared across evaluators)
PROMPT_NOT_PROVIDED: str = "Not provided."
PROMPT_NONE_LISTED: str = "None listed."

# Display names for LLM language instructions
LANGUAGE_DISPLAY_NAMES: dict[str, str] = {
    "fr": "French",
    "en": "English",
}


def get_language_display_name(language: str) -> str:
    """Map language code to display name for LLM prompts."""
    return LANGUAGE_DISPLAY_NAMES.get(language, LANGUAGE_DISPLAY_NAMES["en"])


# HTTP
HTTP_OK: int = 200
HTTP_PARTIAL_CONTENT: int = 206
JOB_NOT_FOUND_DETAIL: str = "Job not found"

# Gemini
GEMINI_MODEL: str = "gemini-3.1-flash-lite"

# Groq service defaults (free tier ~30 RPM)
# 8B stays within free-tier token limits; 70B is higher quality but burns quota faster
GROQ_DEFAULT_MODEL: str = "llama-3.1-8b-instant"
GROQ_MAX_TOKENS: int = 2000
GROQ_TIMEOUT_SECONDS: int = 30
GROQ_RATE_LIMIT_CALLS: int = 28
GROQ_RATE_LIMIT_PERIOD_SECONDS: float = 60.0
GROQ_ERROR_BODY_CHARS: int = 200

# Self-corrector: reject truncated cover-letter corrections
MIN_CORRECTED_COVER_LENGTH: int = 100

# Hallucination / JD parsing thresholds
SHORT_TECH_NAME_MAX_LEN: int = 2
JD_MIN_DESCRIPTION_CHARS: int = 100
MIN_DESCRIPTION_LENGTH: int = 50
SENIOR_YEARS_ONE_PAGE_THRESHOLD: int = 10
FRENCH_DETECTION_MIN_HITS: int = 2

# Contracts that France Travail / Adzuna / JSearch cannot filter via API codes —
# append these keywords to the search query instead (stage ≠ alternance).
KEYWORD_BOOSTED_CONTRACTS: dict[str, list[str]] = {
    "stage": ["stage", "stagiaire"],
    "internship": ["stage", "stagiaire"],
}

# English title → French phrase for a second France Travail motsCles query (AND-safe).
EN_FR_TITLE_VARIANTS: dict[str, str] = {
    "project manager": "chef de projet",
    "software engineer": "ingenieur logiciel",
    "developer": "developpeur",
    "data analyst": "analyste donnees",
    "product manager": "chef de produit",
    "business analyst": "analyste metier",
}

# Job API client defaults
JOB_API_TIMEOUT_SECONDS: int = 15
JOB_API_HTML_FETCH_TIMEOUT_SECONDS: int = 10
JOB_DESC_EXTRACT_MIN_CHARS: int = 200
JOB_DESC_EXTRACT_MAX_CHARS: int = 3000
TRUNCATED_DESCRIPTION_MAX_CHARS: int = 400
DEFAULT_MAX_RESULTS_PER_SOURCE: int = 20
PIPELINE_RATE_LIMIT_CALLS: int = 10
PIPELINE_RATE_LIMIT_PERIOD_SECONDS: float = 60.0
PIPELINE_TOTAL_STEPS: int = 5
REMOTIVE_RESULT_LIMIT: str = "50"
ARBEITNOW_BASE_URL: str = "https://www.arbeitnow.com/api/job-board-api"
REMOTIVE_BASE_URL: str = "https://remotive.com/api/remote-jobs"
ADZUNA_SEARCH_URL: str = "https://api.adzuna.com/v1/api/jobs/fr/search/1"
ADZUNA_RESULTS_PER_PAGE: str = "20"
GEMINI_EMBEDDING_MODEL: str = "models/text-embedding-004"
JOBICY_DEFAULT_COUNT: str = "50"
JOBICY_BASE_URL: str = "https://jobicy.com/api/v2/remote-jobs"
JOBICY_JOB_PAGE_URL: str = "https://jobicy.com/jobs/{slug}"
TITLE_DESC_PREVIEW_CHARS: int = 200
FRANCE_TRAVAIL_AUTH_URL: str = (
    "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire"
)
FRANCE_TRAVAIL_SEARCH_URL: str = (
    "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
)
FRANCE_TRAVAIL_RATE_LIMIT_CALLS: int = 9
FRANCE_TRAVAIL_RATE_LIMIT_PERIOD_SECONDS: float = 1.0
# Pagination: API default is small; max per request is 150 (0-149).
FRANCE_TRAVAIL_RANGE: str = "0-149"

# La Bonne Alternance (free API key: https://api.apprentissage.beta.gouv.fr)
LBA_BASE_URL: str = "https://api.apprentissage.beta.gouv.fr/api/job/v1/search"
LBA_SOURCES: str = "offres_emploi_lba,offres_emploi_partenaires"
LBA_DEFAULT_RADIUS_KM: int = 30
LBA_MAX_RADIUS_KM: int = 200  # API rejects radius > 200

# European Qualification Framework levels for LBA API.
# Maps education keywords from parsed resumes to EQF levels.
EDUCATION_TO_EQF_LEVEL: dict[str, int] = {
    "master": 7,
    "msc": 7,
    "m.sc": 7,
    "ingénieur": 7,
    "engineer": 7,
    "bac+5": 7,
    "licence": 6,
    "bachelor": 6,
    "bac+3": 6,
    "bts": 5,
    "dut": 5,
    "deust": 5,
    "bac+2": 5,
    "bac": 4,
    "cap": 3,
    "bep": 3,
}

# Google Sheets / Drive
GOOGLE_SHEETS_SCOPES: tuple[str, ...] = (
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
)
GOOGLE_SHEETS_EDIT_URL: str = "https://docs.google.com/spreadsheets/d/{sheet_id}/edit"

# Country-to-region mapping (Jobicy + future geo-aware APIs)
COUNTRY_GEO_MAP: dict[str, str] = {
    "FR": "europe",
    "GB": "europe",
    "DE": "europe",
    "US": "usa",
    "CA": "usa",
}

# Language Detection
FRENCH_DETECTION_WORDS: list[str] = [" est ", " sont ", " avec ", " dans ", " pour ", " une ", " les ", " des ", " par ", " sur ", " au ", " du ", " ce ", " qui ", " que "]

# Hallucination checker: words too common to be flagged as fabricated tech terms.
HALLUCINATION_COMMON_WORDS: frozenset[str] = frozenset([
    "the", "and", "or", "for", "with", "from", "to", "in", "on", "at",
    "by", "a", "an", "is", "of", "le", "la", "les", "des", "pour",
    "avec", "dans", "et", "ou", "en", "sur", "au", "aux"
])

# Hallucination checker: short abbreviations that must be present verbatim in the original CV.
HALLUCINATION_SHORT_TECH_NAMES: frozenset[str] = frozenset([
    "go", "r", "c", "c#", "c++", "ai", "ml", "qa", "ux", "ui", "ci", "cd", "js", "ts"
])

# SheetsTracker application status keywords
SHEETS_TRACKER_STATUS_VALUES: dict[str, list[str]] = {
    "fr": ["À postuler", "Postulé", "Entretien", "Refusé", "Offre"],
    "en": ["To apply", "Applied", "Interview", "Rejected", "Offer"],
}

# SheetsTracker column headers
SHEETS_TRACKER_HEADERS: dict[str, list[str]] = {
    "fr": [
        "Date", "Entreprise", "Poste", "Localisation", "Type contrat",
        "Score algo (0-100)", "Score recruteur (0-10)", "Mots-clés manquants",
        "Statut", "URL", "CV fichier", "LM fichier", "Recommandation", "Notes",
    ],
    "en": [
        "Date", "Company", "Title", "Location", "Contract type",
        "Algo score (0-100)", "Recruiter score (0-10)", "Missing keywords",
        "Status", "URL", "Resume file", "Cover letter file", "Recommendation", "Notes",
    ],
}

# Output generator heading mappings by language
SECTION_HEADINGS: dict[str, dict[str, str]] = {
    "fr": {
        "skills": "Compétences",
        "skills_technical": "Compétences techniques",
        "skills_soft": "Soft Skills",
        "certifications": "Certifications",
        "experience": "Expérience professionnelle",
        "education": "Éducation",
        "projects": "Projets académiques",
        "associations": "Associations",
        "languages": "Langues",
    },
    "en": {
        "skills": "Skills",
        "skills_technical": "Technical Skills",
        "skills_soft": "Soft Skills",
        "certifications": "Certifications",
        "experience": "Professional Experience",
        "education": "Education",
        "projects": "Academic Projects",
        "associations": "Associations",
        "languages": "Languages",
    },
}

# Type suffixes that may already appear in resume titles (both languages)
TYPE_SUFFIXES: list[str] = [
    "(Internship)", "(Stage)", "(Alternance)", "(Volunteer)",
    "(Bénévolat)", "(Freelance)",
    "(internship)", "(stage)", "(alternance)", "(volunteer)",
    "(bénévolat)", "(freelance)",
]

# Keywords that indicate an academic or research role in output_generator
ACADEMIC_KEYWORDS: frozenset[str] = frozenset([
    "professor", "researcher", "postdoc", "faculty",
    "chercheur", "enseignant-chercheur", "maître de conférences"
])

# Deterministic language name translations (EN → FR)
LANG_NAMES_EN_TO_FR: dict[str, str] = {
    "arabic": "Arabe", "chinese": "Chinois", "dutch": "Néerlandais",
    "english": "Anglais", "french": "Français", "german": "Allemand",
    "hindi": "Hindi", "italian": "Italien", "japanese": "Japonais",
    "korean": "Coréen", "portuguese": "Portugais", "russian": "Russe",
    "spanish": "Espagnol", "turkish": "Turc", "ukrainian": "Ukrainien",
    "polish": "Polonais", "romanian": "Roumain", "swedish": "Suédois",
    "danish": "Danois", "norwegian": "Norvégien", "finnish": "Finnois",
    "greek": "Grec", "hebrew": "Hébreu", "persian": "Persan",
    "thai": "Thaï", "vietnamese": "Vietnamien", "czech": "Tchèque",
    "hungarian": "Hongrois", "bengali": "Bengali", "malay": "Malais",
    "indonesian": "Indonésien", "tagalog": "Tagalog",
}

# Deterministic proficiency level translations (EN → FR)
# CEFR codes (A1, A2, B1, B2, C1, C2) are NOT translated; they stay as-is
PROFICIENCY_EN_TO_FR: dict[str, str] = {
    "native": "Natif", "bilingual": "Bilingue", "fluent": "Courant",
    "advanced": "Avancé", "intermediate": "Intermédiaire",
    "beginner": "Débutant", "elementary": "Élémentaire",
    "professional": "Professionnel",
    "native or bilingual": "Natif ou bilingue",
    "full professional": "Courant professionnel",
    "limited working": "Niveau professionnel limité",
}

# Canonical contract types recognised by the pipeline. Keep in sync with ContractType in models/job.py.
SUPPORTED_CONTRACT_TYPES: tuple[str, ...] = (
    "CDD",
    "CDI",
    "alternance_apprentissage",
    "alternance_professionnalisation",
    "freelance",
    "stage",
)

# Canonical language codes supported by the app. Keep in sync with SupportedLanguage in models/job.py.
SUPPORTED_LANGUAGES: tuple[str, ...] = ("en", "fr")


class PipelineStatus(StrEnum):
    """Canonical values for app_state['pipeline_status']."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"




# Common bilingual stop-words excluded from job-title relevance matching.
TITLE_RELEVANCE_STOPWORDS: frozenset[str] = frozenset({
    "de", "du", "le", "la", "les",
    "the", "a", "an", "and",
    "et", "en", "in", "of",
    "-", "\u2013",
})

# Sources that already filter by relevance at the API level (ROME codes, etc.).
# Title relevance filter is skipped for these.
# Sources whose API already filters by occupation codes tightly enough that
# title relevance can be skipped. LBA ROME codes are broad families, so LBA
# is NOT included — irrelevant titles like "Chargé de Partenariats" must still
# go through the title filter.
API_PREFILTERED_SOURCES: frozenset[str] = frozenset()


SENIORITY_KEYWORDS = {
    "stagiaire": ["stagiaire", "intern", "stage"],
    "alternant": ["alternant", "alternance", "apprenti"],
    "junior": ["junior", "jr"],
    "mid": ["mid", "intermédiaire", "confirmé"],
    "senior": ["senior", "sr", "expérimenté", "experienced"],
    "lead": ["lead", "principal", "staff", "head"],
}

# Canonical seniority levels. Keep in sync with SeniorityLevel in models/match.py.
SUPPORTED_SENIORITY_LEVELS: tuple[str, ...] = (
    "alternant",
    "intermédiaire",
    "junior",
    "lead",
    "mid",
    "senior",
    "stagiaire",
)

KEYWORD_INDEPENDANT: str = "indépendant"
KEYWORD_CONTRAT_PRO: str = "contrat pro"

CONTRACT_KEYWORDS = {
    "CDI": ["cdi", "permanent", "full-time", "full time", "unbefristet"],
    "CDD": ["cdd", "fixed-term", "fixed term", "contract", "temporary"],
    "stage": ["stage", "internship", "intern", "stagiaire"],
    "alternance_apprentissage": ["alternance", "apprentissage", "apprenti", "work-study"],
    "alternance_professionnalisation": ["alternance", "professionnalisation"],
    "freelance": ["freelance", "contractor", "independent", KEYWORD_INDEPENDANT],
}

# Keywords that indicate a CDD is actually an apprenticeship contract.
# France Travail encodes these as "CDD - Contrat apprentissage".
ALTERNANCE_KEYWORDS: list[str] = [
    "apprentissage", "apprenti", "alternance", KEYWORD_CONTRAT_PRO,
    "professionnalisation", "work-study",
]

# Keywords for detecting contract type from a job title.
TITLE_CONTRACT_SIGNALS: dict[str, list[str]] = {
    "stage": ["internship", "stage", "intern", "stagiaire"],
    "freelance": ["freelance", "contractor", KEYWORD_INDEPENDANT, "freelancer", "independent"],
    "alternance_professionnalisation": ["professionnalisation", KEYWORD_CONTRAT_PRO],
    "alternance_apprentissage": ["alternance", "apprenti", "apprentissage", "apprenticeship", "work-study"],
}

# UI / preference labels → canonical contract types used by the pipeline filter.
CONTRACT_PREFERENCE_ALIASES: dict[str, str] = {
    "cdi": "cdi",
    "cdd": "cdd",
    "freelance": "freelance",
    "stage": "stage",
    "alternance": "alternance_apprentissage",
    "apprentissage": "alternance_apprentissage",
    "alternance_apprentissage": "alternance_apprentissage",
    "alternance (apprentissage)": "alternance_apprentissage",
    "professionnalisation": "alternance_professionnalisation",
    "alternance_professionnalisation": "alternance_professionnalisation",
    "alternance (professionnalisation)": "alternance_professionnalisation",
}

# Free-text contract_type field → canonical key (first matching keyword wins).
CONTRACT_TYPE_STRING_SIGNALS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("cdi", "permanent", "unbefristet"), "cdi"),
    (("cdd", "fixed", "temporary", "interim"), "cdd"),
    (("freelance", "independent", KEYWORD_INDEPENDANT), "freelance"),
    (("professionnalisation", KEYWORD_CONTRAT_PRO), "alternance_professionnalisation"),
    (("alternance", "apprentissage"), "alternance_apprentissage"),
    (("stage", "internship"), "stage"),
)

# Phrase-level signals in job descriptions (avoids false positives like "apprentissage continu").
DESCRIPTION_CONTRACT_SIGNALS: dict[str, tuple[str, ...]] = {
    "alternance_professionnalisation": (
        "professionnalisation",
        "contrat de professionnalisation",
        KEYWORD_CONTRAT_PRO,
    ),
    "alternance_apprentissage": (
        "en alternance",
        "contrat d'alternance",
        "contrat d’alternance",
        "contrat d'apprentissage",
        "contrat d’apprentissage",
        "contrat d apprentissage",
        "contrat apprentissage",
        "alternance apprentissage",
        "work-study",
        "work study",
    ),
    "stage": (
        "offre de stage",
        "stage de",
        "stage chez",
        "internship",
        "stagiaire",
        "as an intern",
        "intern position",
    ),
    "freelance": (
        "freelance",
        KEYWORD_INDEPENDANT,
        "independent contractor",
    ),
}

# Continuous-learning phrase that must NOT count as apprenticeship.
APPRENTICESHIP_FALSE_POSITIVE: str = "apprentissage continu"

# Contract types that get benefit-of-the-doubt when type is unknown.
BROAD_CONTRACT_TYPES: frozenset[str] = frozenset({"cdi", "cdd"})

# Language-specific conventions for LLM cover letter generation.
COVER_LETTER_CONVENTIONS: dict[str, str] = {
    "fr": (
        '- Use professional vouvoiement throughout.\n'
        '- Open with "Madame, Monsieur,"\n'
        '- Close with "Je vous prie d\'agréer, Madame, Monsieur, '
        'l\'expression de mes salutations distinguées."\n'
        '- Do NOT use any English salutations or closings.'
    ),
    "en": (
        '- Use professional but natural English register.\n'
        '- Open with "Dear Hiring Manager,"\n'
        '- Close with "Sincerely,"\n'
        '- Do NOT use any French salutations, closings, or vouvoiement.'
    ),
}

# INSEE commune codes for major French cities.
# France Travail's `distance` parameter requires a `commune` code, not free-text.
CITY_INSEE_CODES: dict[str, str] = {
    "paris": "75056",
    "lyon": "69123",
    "marseille": "13055",
    "toulouse": "31555",
    "nice": "06088",
    "nantes": "44109",
    "strasbourg": "67482",
    "montpellier": "34172",
    "bordeaux": "33063",
    "lille": "59350",
    "rennes": "35238",
    "grenoble": "38185",
    "metz": "57463",
    "nancy": "54395",
    "rouen": "76540",
    "tours": "37261",
    "dijon": "21231",
    "angers": "49007",
    "clermont-ferrand": "63113",
    "reims": "51454",
    "aix-en-provence": "13001",
    "brest": "29019",
    "le havre": "76351",
    "limoges": "87085",
    "toulon": "83137",
}

# Lat/lon for APIs that require coordinates (e.g. La Bonne Alternance).
CITY_COORDINATES: dict[str, tuple[float, float]] = {
    "paris": (48.8566, 2.3522),
    "lyon": (45.7640, 4.8357),
    "marseille": (43.2965, 5.3698),
    "toulouse": (43.6047, 1.4442),
    "nice": (43.7102, 7.2620),
    "nantes": (47.2184, -1.5536),
    "strasbourg": (48.5734, 7.7521),
    "montpellier": (43.6108, 3.8767),
    "bordeaux": (44.8378, -0.5792),
    "lille": (50.6292, 3.0573),
    "rennes": (48.1173, -1.6778),
    "grenoble": (45.1885, 5.7245),
}

# Substring signals in France Travail typeContrat / typeContratLibelle → canonical contract type.
# Order matters: first match wins (dict insertion order).
FT_CONTRACT_TYPE_SIGNALS: dict[str, tuple[str, ...]] = {
    "CDI": ("cdi",),
    "CDD": ("cdd",),
    "stage": ("stage",),
    "alternance_apprentissage": ("alternance", "apprentissage"),
    "freelance": ("freelance",),
}

# France Travail natureOffre codes. E2 is both CDD and apprenticeship.
FRANCE_TRAVAIL_CONTRACT_CODES: dict[str, list[str]] = {
    "cdi": ["E1"],
    "cdd": ["E2"],
    "alternance (apprentissage)": ["E2"],
    "alternance_apprentissage": ["E2"],
    "alternance": ["E2", "FS"],
    "apprentissage": ["E2"],
    "alternance (professionnalisation)": ["FS"],
    "alternance_professionnalisation": ["FS"],
    "professionnalisation": ["FS"],
    "freelance": ["NS"],
    "stage": [],  # France Travail doesn't have a natureOffre for stage
}

# Default query params for JSearch search-v2 (query/country are set per request).
JSEARCH_DEFAULT_PARAMS: dict[str, str] = {
    "page": "1",
    "num_pages": "1",
}

# Used by preview.py to translate LLM verdict violations into user-facing warnings.
VIOLATION_LABELS: dict[str, dict[str, str]] = {
    "fr": {
        "fabricated_metric": "Un chiffre semble avoir été inventé, vérifiez qu'il correspond à votre expérience réelle",
        "invented_skill": "Une compétence ou un outil a été ajouté qui ne figure pas dans votre CV original",
        "jd_attribution": "Cette phrase semble venir de l'offre d'emploi, pas de votre parcours",
        "scope_inflation": "Votre rôle semble décrit de façon plus importante que dans votre CV original",
        "entity_bleed": "Cette phrase semble confondre l'entreprise cible avec votre parcours",
        "hallucinated_achievement": "Une réalisation mentionnée ne figure pas dans votre CV",
        "jd_parroting": "Cette phrase semble copiée de l'offre d'emploi",
        "language_mixing": "Mélange de langues détecté dans le document",
        "tone_mismatch": "Le ton ne correspond pas au marché visé",
        "other": "Un point a été modifié, vérifiez qu'il correspond à votre expérience",
    },
    "en": {
        "fabricated_metric": "A number seems to have been added, check it matches your real experience",
        "invented_skill": "A skill or tool was added that isn't in your original CV",
        "jd_attribution": "This seems to come from the job posting, not from your background",
        "scope_inflation": "Your role seems described as bigger than in your original CV",
        "entity_bleed": "This sentence seems to confuse the target company with your background",
        "hallucinated_achievement": "An achievement mentioned is not in your CV",
        "jd_parroting": "This sentence seems copied from the job posting",
        "language_mixing": "Language mixing detected in the document",
        "tone_mismatch": "The tone doesn't match the target market",
        "other": "Something was changed, check it matches your experience",
    },
}

# Severity labels, keyed by language code then severity level.
SEVERITY_LABELS: dict[str, dict[str, str]] = {
    "fr": {
        "HIGH": "À corriger avant d'envoyer",
        "MEDIUM": "À vérifier avant d'envoyer",
        "LOW": "Point mineur, à votre appréciation",
    },
    "en": {
        "HIGH": "Fix this before sending",
        "MEDIUM": "Check this before sending",
        "LOW": "Minor point, your call",
    },
}


TRANSLATIONS = {
    "fr": {
        "nav_dashboard": "Tableau de bord",
        "nav_settings": "Paramètres",
        "nav_results": "Résultats",
        "dashboard_title": "Tableau de bord",
        "jobs_found": "Offres trouvées",
        "avg_score": "Score moyen",
        "above_threshold": "Au-dessus du seuil (50+)",
        "run_pipeline": "Lancer la recherche",
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
        "error_no_preferences": "Veuillez configurer vos préférences de recherche (titres et localisation)",
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
        "edit_cover_letter": "Modifier",
        "unfillable": "Mots-clés non intégrables :",
        "error_tailoring": "Échec de la personnalisation. Veuillez réessayer.",
        "error_no_data": "CV ou description de poste indisponible pour la personnalisation.",
        "error_unexpected": "Erreur inattendue",
        "no_tailoring_data": "Aucune donnée de personnalisation disponible.",
        "ai_disclaimer": "Ce contenu a été généré par l'intelligence artificielle. Relisez attentivement chaque point et corrigez toute information inexacte avant d'envoyer votre candidature. Vous êtes le seul garant de l'exactitude de votre CV.",
        "cover_letter_title": "Lettre de motivation",
        "tailored_cv_title": "CV adapté",
        "copy_cv": "Copier le CV",
        "approve_save": "Approuver et enregistrer",
        "action_expand": "Voir les détails",
        "action_tailor": "Adapter le CV",
        "action_skip": "Ignorer",
        "job_approved_msg": "CV et lettre de motivation sauvegardés. Prêt à postuler",
        "copied": "Copié !",
        "print_btn": "Imprimer / PDF",
        "copy_btn": "Copier",
        "view_cv": "Voir le CV",
        "view_cover": "Voir la lettre",
        "no_details": "Pas de détails",
        "saved_badge": "Sauvegardé",
        "col_status": "Statut",
        "status_saved": "Sauvegardé",
        "status_pending": "À traiter",
        "filter_min_score": "Score minimum",
        "filter_status": "Statut",
        "filter_all": "Tous",
        "company_not_specified": "Entreprise non précisée",
        "pipeline_running_warning": "Pipeline en cours",
        "pipeline_nav_warning_body": (
            "Le pipeline est en cours d'exécution. Si vous quittez maintenant, "
            "les résultats en cours seront perdus."
        ),
        "stay_on_page": "Rester sur la page",
        "leave_anyway": "Quitter quand même",
        "lang_fr": "Passer en français",
        "lang_en": "Switch to English",
        "filter_score_all": "Filtrer : tous les scores",
        "filter_score_40": "Filtrer : score 40% et plus",
        "filter_score_60": "Filtrer : score 60% et plus",
        "filter_score_80": "Filtrer : score 80% et plus",
        "filter_status_all": "Filtrer : tous les statuts",
        "filter_status_saved": "Filtrer : sauvegardés",
        "filter_status_pending": "Filtrer : à traiter",
        "upload_resume_btn": "Téléverser le CV",
        "delete_resume_aria": "Supprimer le CV",
        "original_bullets": "Original",
        "col_match": "Match",
        "expand_details": "Voir détails",
        "edit_job": "Modifier",
        "skip_job": "Ignorer",
    },
    "en": {
        "nav_dashboard": "Dashboard",
        "nav_settings": "Settings",
        "nav_results": "Results",
        "dashboard_title": "Dashboard",
        "jobs_found": "Jobs Found",
        "avg_score": "Avg Match Score",
        "above_threshold": "Above Threshold (50+)",
        "run_pipeline": "Start Search",
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
        "error_no_preferences": "Please configure your search preferences (titles and location)",
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
        "edit_cover_letter": "Edit",
        "unfillable": "Keywords that could not be incorporated:",
        "error_tailoring": "Tailoring failed. Please try again.",
        "error_no_data": "Resume or job description not available for tailoring.",
        "error_unexpected": "Unexpected error",
        "no_tailoring_data": "No tailoring data available.",
        "ai_disclaimer": "This content was generated by artificial intelligence. Carefully review every point and correct any inaccurate information before submitting your application. The applicant alone is responsible for the accuracy of the CV.",
        "cover_letter_title": "Cover Letter",
        "tailored_cv_title": "Tailored Resume",
        "copy_cv": "Copy Resume",
        "approve_save": "Approve & Save",
        "action_expand": "View details",
        "action_tailor": "Tailor Resume",
        "action_skip": "Skip",
        "job_approved_msg": "CV and cover letter saved. Ready to apply",
        "copied": "Copied!",
        "print_btn": "Print / PDF",
        "copy_btn": "Copy",
        "view_cv": "View CV",
        "view_cover": "View cover letter",
        "no_details": "No details",
        "saved_badge": "Saved",
        "col_status": "Status",
        "status_saved": "Saved",
        "status_pending": "Pending",
        "filter_min_score": "Minimum score",
        "filter_status": "Status",
        "filter_all": "All",
        "company_not_specified": "Company not specified",
        "pipeline_running_warning": "Pipeline running",
        "pipeline_nav_warning_body": (
            "The pipeline is running. If you leave now, current results will be lost."
        ),
        "stay_on_page": "Stay on page",
        "leave_anyway": "Leave anyway",
        "lang_fr": "Switch to French",
        "lang_en": "Switch to English",
        "filter_score_all": "Filter: all scores",
        "filter_score_40": "Filter: score 40% and up",
        "filter_score_60": "Filter: score 60% and up",
        "filter_score_80": "Filter: score 80% and up",
        "filter_status_all": "Filter: all statuses",
        "filter_status_saved": "Filter: saved",
        "filter_status_pending": "Filter: pending",
        "upload_resume_btn": "Upload resume",
        "delete_resume_aria": "Delete resume",
        "original_bullets": "Original",
        "col_match": "Match",
        "expand_details": "Expand details",
        "edit_job": "Edit",
        "skip_job": "Skip",
    },
}
