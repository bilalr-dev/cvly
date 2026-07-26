from __future__ import annotations

import logging
from datetime import date
import gspread
from google.oauth2.service_account import Credentials

from backend.models import RawJobPosting, ParsedJobDescription, MatchResult

logger = logging.getLogger(__name__)

STATUS_VALUES = {
    "fr": ["À postuler", "Postulé", "Entretien", "Refusé", "Offre"],
    "en": ["To apply", "Applied", "Interview", "Rejected", "Offer"],
}

_HEADERS = {
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

class SheetsTracker:

    def __init__(self, credentials_path: str, sheet_id: str | None = None) -> None:
        self.credentials_path = credentials_path
        self.sheet_id = sheet_id
        self.client = None
        self.worksheet = None

    def connect(self) -> None:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file"
        ]
        creds = Credentials.from_service_account_file(self.credentials_path, scopes=scopes)
        self.client = gspread.authorize(creds)

        if self.sheet_id is not None:
            spreadsheet = self.client.open_by_key(self.sheet_id)
        else:
            spreadsheet = self.client.create("Cvly Job Tracker")
            self.sheet_id = spreadsheet.id

        self.worksheet = spreadsheet.get_worksheet(0)
        logger.info(f"Connected to Google Sheet: {self.sheet_id}")

    def setup_headers(self, language: str = "fr") -> None:
        if self.worksheet is None:
            raise RuntimeError("Not connected. Call connect() first.")

        headers = _HEADERS.get(language, _HEADERS["en"])
        self.worksheet.update("A1:N1", [headers])

    def append_job(
        self,
        posting: RawJobPosting,
        jd: ParsedJobDescription,
        match_result: MatchResult,
        resume_path: str,
        cover_letter_path: str,
        language: str = "fr"
    ) -> None:
        if self.worksheet is None:
            raise RuntimeError("Not connected. Call connect() first.")

        date_str = date.today().strftime("%Y-%m-%d")

        algo_score = round(getattr(match_result, "overall_score", 0))

        atf = getattr(match_result, "atf_analysis", None)
        recruiter_score = getattr(atf, "recruiter_score", "") if atf else ""
        recommendation = getattr(atf, "recommendation", "") if atf else ""

        miss_k = getattr(match_result, "missing_keywords", [])
        if not isinstance(miss_k, list):
            miss_k = []

        kw_str = ", ".join(str(k) for k in miss_k)
        status = STATUS_VALUES.get(language, STATUS_VALUES["en"])[0]

        company = getattr(posting, "company", "")
        title = getattr(posting, "title", "")

        row_data = [
            date_str,
            company,
            title,
            getattr(posting, "location", ""),
            getattr(posting, "contract_type", ""),
            algo_score,
            recruiter_score,
            kw_str,
            status,
            getattr(posting, "url", ""),
            resume_path,
            cover_letter_path,
            recommendation,
            ""
        ]

        self.worksheet.append_row(row_data)
        logger.info(f"Appended job row: {company} - {title}")
