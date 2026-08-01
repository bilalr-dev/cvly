"""Gemini text embedding service wrapper."""
from __future__ import annotations

import google.generativeai as genai

from backend.services.gemini_llm import GeminiAPIError
from backend.utils.constants import GEMINI_EMBEDDING_MODEL


class GeminiEmbeddingsService:

    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)

    def embed_text(self, text: str) -> list[float]:

        try:
            model = genai.GenerativeModel(GEMINI_EMBEDDING_MODEL)
            result = model.embed_content(text)
            return result["embedding"]
        except Exception as e:
            raise GeminiAPIError(f"Embedding failed: {e}") from e
