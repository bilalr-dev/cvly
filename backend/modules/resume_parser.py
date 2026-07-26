from __future__ import annotations

from pathlib import Path

import docx
from docx.opc.exceptions import PackageNotFoundError
import pdfplumber

from backend.models.resume import ResumeProfile
from backend.prompts import RESUME_PARSE_PROMPT
from backend.services.gemini_llm import GeminiLLMService


def extract_text_from_pdf(file_path: str) -> str:
    text_chunks = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_chunks.append(page_text)
    return "\n".join(text_chunks)


def extract_text_from_docx(file_path: str) -> str:
    try:
        doc = docx.Document(file_path)
    except (ValueError, OSError, PackageNotFoundError) as e:
        raise FileNotFoundError(f"File not found: {file_path}") from e

    text_chunks = [p.text for p in doc.paragraphs if p.text]
    return "\n".join(text_chunks)


def extract_text(file_path: str) -> str:
    suffix = Path(file_path).suffix.lower()

    if suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    if suffix == ".docx":
        return extract_text_from_docx(file_path)

    raise ValueError(f"Unsupported file extension: {file_path}")


class ResumeParser:
    def __init__(self, api_key: str):
        self.gemini_service = GeminiLLMService(api_key=api_key)

    def parse_resume(self, file_path: str) -> ResumeProfile:
        raw_text = extract_text(file_path)

        if not raw_text.strip():
            raise ValueError("Resume file contains no extractable text")

        prompt = RESUME_PARSE_PROMPT.format(raw_text=raw_text)

        return self.gemini_service.generate_json(
            prompt=prompt,
            response_schema=ResumeProfile,
            temperature=0.0
        )
