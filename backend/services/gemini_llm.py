from __future__ import annotations

import json
from typing import Any

import google.generativeai as genai
from pydantic import BaseModel, ValidationError

GEMINI_MODEL = "gemini-3.1-flash-lite"


class GeminiAPIError(Exception):
    pass


def _replace_null_lists(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _replace_null_lists(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_replace_null_lists(item) for item in data]
    return data


def _compact_schema_hint(schema_class: type[BaseModel], indent: int = 0) -> str:
    fields = schema_class.model_fields
    lines = []
    prefix = "  " * (indent + 1)
    for name, field_info in fields.items():
        annotation = field_info.annotation
        origin = getattr(annotation, "__origin__", None)
        args = getattr(annotation, "__args__", ())

        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            nested = _compact_schema_hint(annotation, indent + 1)
            lines.append(f'{prefix}"{name}": {nested}')
        elif origin is list and args and isinstance(args[0], type) and issubclass(args[0], BaseModel):
            nested = _compact_schema_hint(args[0], indent + 1)
            lines.append(f'{prefix}"{name}": [{nested}]')
        else:
            type_name = getattr(annotation, "__name__", str(annotation))
            if field_info.is_required():
                lines.append(f'{prefix}"{name}": {type_name}')
            else:
                lines.append(f'{prefix}"{name}": {type_name} (optional)')
    open_brace = "  " * indent + "{"
    close_brace = "  " * indent + "}"
    return open_brace + "\n" + ",\n".join(lines) + "\n" + close_brace


class GeminiLLMService:

    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)

    def generate_json(self, prompt: str, response_schema: type[BaseModel], temperature: float = 0.0) -> BaseModel:
        model = genai.GenerativeModel(GEMINI_MODEL)

        schema_hint = _compact_schema_hint(response_schema)

        full_prompt = (
            f"{prompt}\n\n"
            f"Return your response as valid JSON with these fields:\n"
            f"{schema_hint}\n"
            f"Return ONLY valid JSON. No markdown fences, no explanation."
        )

        try:
            response = model.generate_content(
                full_prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": temperature,
                },
                safety_settings=[
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ],
            )

            raw_text = response.text.strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[1] if "\n" in raw_text else raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3].strip()

            data = json.loads(raw_text)
            data = _replace_null_lists(data)
            return response_schema.model_validate(data)
        except ValidationError as e:
            raise GeminiAPIError(f"Schema validation failed: {e!s}") from e
        except json.JSONDecodeError as e:
            raise GeminiAPIError(f"Invalid JSON returned: {e!s}") from e
        except GeminiAPIError:
            raise
        except Exception as e:
            raise GeminiAPIError(f"API Error: {e!s}") from e

    def generate_text(self, prompt: str, temperature: float = 0.5) -> str:
        """Send a prompt to Gemini and return plain text."""
        model = genai.GenerativeModel(GEMINI_MODEL)
        try:
            response = model.generate_content(
                prompt,
                generation_config={"temperature": temperature},
            )
            return response.text.strip()
        except Exception as e:
            raise GeminiAPIError(f"API Error: {e!s}") from e
