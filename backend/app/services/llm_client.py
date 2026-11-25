from __future__ import annotations

import json
import logging
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from app.config import Settings
from app.utils.exceptions import AppException

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """Thin wrapper around the OpenAI chat completions API with JSON validation."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._client: OpenAI | None = None

    def _get_client(self) -> OpenAI:
        if not self._settings.llm_api_key:
            raise AppException(
                "LLM service is not configured. Please set GROQ_API_KEY or OPENAI_API_KEY "
                "in the backend environment.",
                status_code=503,
            )

        if self._client is None:
            self._client = OpenAI(
                api_key=self._settings.llm_api_key,
                base_url=self._settings.llm_base_url,
            )
        return self._client

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        max_retries: int | None = None,
    ) -> T:
        retries = max_retries if max_retries is not None else self._settings.llm_max_retries
        client = self._get_client()
        last_error: str | None = None

        for attempt in range(retries + 1):
            try:
                response = client.chat.completions.create(
                    model=self._settings.llm_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.3,
                )

                raw_content = response.choices[0].message.content
                if not raw_content:
                    raise ValueError("LLM returned an empty response")

                payload = json.loads(raw_content)
                return response_model.model_validate(payload)

            except json.JSONDecodeError as exc:
                last_error = "LLM returned invalid JSON"
                logger.warning("LLM JSON parse failed (attempt %d): %s", attempt + 1, exc)
            except ValidationError as exc:
                last_error = "LLM response did not match the required schema"
                logger.warning(
                    "LLM validation failed (attempt %d): %s\nRaw output: %s",
                    attempt + 1,
                    exc,
                    raw_content if 'raw_content' in locals() else 'N/A',
                )
            except AppException:
                raise
            except Exception as exc:
                last_error = "LLM service request failed"
                logger.warning("LLM request failed (attempt %d): %s", attempt + 1, exc)

        raise AppException(
            last_error or "Failed to get a valid response from the LLM. Please try again.",
            status_code=502,
        )
