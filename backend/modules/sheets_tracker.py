"""Google Sheets tracker for approved job applications."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import gspread
from google.oauth2.service_account import Credentials
from gspread.utils import rowcol_to_a1

from backend.models import MatchResult, ParsedJobDescription, RawJobPosting
from backend.utils.constants import (
    GOOGLE_SHEETS_SCOPES,
    SHEETS_NOT_CONNECTED_MSG,
    SHEETS_TRACKER_HEADERS as _HEADERS,
    SHEETS_TRACKER_STATUS_VALUES as STATUS_VALUES,
)

logger = logging.getLogger(__name__)


class SheetsTracker:

    def __init__(self, credentials_path: str, sheet_id: str | None = None) -> None:
        self.credentials_path = credentials_path
        self.sheet_id = sheet_id
        self.client = None
        self.spreadsheet = None
        self.worksheet = None

    def connect(self) -> None:
        scopes = list(GOOGLE_SHEETS_SCOPES)
        creds = Credentials.from_service_account_file(self.credentials_path, scopes=scopes)
        self.client = gspread.authorize(creds)

        if self.sheet_id is not None:
            spreadsheet = self.client.open_by_key(self.sheet_id)
        else:
            spreadsheet = self.client.create("Cvly Job Tracker")
            self.sheet_id = spreadsheet.id

        self.spreadsheet = spreadsheet
        self.worksheet = spreadsheet.get_worksheet(0)
        logger.debug("Connected to Google Sheet: %s", self.sheet_id)

    def setup_headers(self, language: str = "fr") -> None:
        if self.worksheet is None:
            raise RuntimeError(SHEETS_NOT_CONNECTED_MSG)

        headers = _HEADERS.get(language, _HEADERS["en"])
        self.worksheet.update("A1:N1", [headers])

    def _style_headers(self) -> None:
        """Apply visual styling to the header row (indigo, bold white, frozen, auto-sized)."""
        if self.worksheet is None or self.spreadsheet is None:
            return

        header_count = len(self.worksheet.row_values(1))
        if header_count == 0:
            return

        header_range = f"A1:{rowcol_to_a1(1, header_count)}"

        self.worksheet.format(header_range, {
            "backgroundColor": {"red": 0.25, "green": 0.27, "blue": 0.7},
            "textFormat": {
                "bold": True,
                "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                "fontSize": 11,
            },
            "horizontalAlignment": "CENTER",
        })

        sheet_id = self.worksheet.id
        self.spreadsheet.batch_update({
            "requests": [
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": sheet_id,
                            "gridProperties": {"frozenRowCount": 1},
                        },
                        "fields": "gridProperties.frozenRowCount",
                    }
                },
                {
                    "autoResizeDimensions": {
                        "dimensions": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": 0,
                            "endIndex": header_count,
                        }
                    }
                },
            ]
        })

    def _ensure_headers(self, language: str = "fr") -> None:
        """Write column headers once if the sheet is still empty."""
        if self.worksheet is None:
            raise RuntimeError(SHEETS_NOT_CONNECTED_MSG)
        if not self.worksheet.acell("A1").value:
            self.setup_headers(language)
            self._style_headers()

    def append_job(
        self,
        posting: RawJobPosting,
        _jd: ParsedJobDescription,
        match_result: MatchResult,
        resume_path: str,
        cover_letter_path: str,
        language: str = "fr"
    ) -> None:
        if self.worksheet is None:
            raise RuntimeError(SHEETS_NOT_CONNECTED_MSG)

        self._ensure_headers(language)

        date_str = datetime.now(tz=timezone.utc).strftime("%d/%m/%Y")

        algo_score = round(getattr(match_result, "overall_score", 0)) if match_result else 0

        atf = getattr(match_result, "atf_analysis", None) if match_result else None
        recruiter_score = getattr(atf, "recruiter_score", "") if atf else ""
        recommendation = getattr(atf, "recommendation", "") if atf else ""

        miss_k = getattr(match_result, "missing_keywords", []) if match_result else []
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
        logger.debug("Appended job row: %s - %s", company, title)
