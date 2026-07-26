from __future__ import annotations

import json
from typing import Type

import google.generativeai as genai
from pydantic import BaseModel, ValidationError


GEMINI_MODEL = "gemini-2.0-flash"


class GeminiAPIError(Exception):
    pass


class GeminiLLMService:

    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)

    def generate_json(self, prompt: str, response_schema: type[BaseModel], temperature: float = 0.0) -> BaseModel:
        model = genai.GenerativeModel(GEMINI_MODEL)
        generation_config = {
            "response_mime_type": "application/json",
            "response_schema": response_schema,
            "temperature": temperature,
        }

        # TODO: add safety settings test
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]

        try:
            response = model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            data = json.loads(response.text)
            return response_schema.model_validate(data)
        except ValidationError as e:
            raise GeminiAPIError(f"Schema validation failed: {str(e)}") from e
        except json.JSONDecodeError as e:
            raise GeminiAPIError(f"Invalid JSON returned: {str(e)}") from e
        except Exception as e:
            raise GeminiAPIError(f"API Error: {str(e)}") from e
