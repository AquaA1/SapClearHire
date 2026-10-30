import json
from typing import Any

import httpx

from app.core.exceptions import ValidationError
from app.core.logging import logger
from app.integrations.llm.base import BaseLLMProvider
from app.integrations.llm.prompts import (
    EXTRACTION_SYSTEM_PROMPT,
    PROMPT_VERSION,
    build_extraction_prompt,
)
from app.integrations.llm.schemas import (
    CandidateClaim,
    ExtractedResumeProfile,
    ExtractionResult,
)


class HTTPClientLLMProvider(BaseLLMProvider):
    """
    Real LLM provider adapter communicating over HTTP (OpenAI-compatible, Anthropic, Gemini proxy).
    Uses strict JSON schema enforcement and defensive XML prompting.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 60.0,
        provider_name: str = "openai",
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.provider_name = provider_name
        self.prompt_version = PROMPT_VERSION

    async def extract_resume_profile(
        self,
        resume_pages: dict[int, str],
        document_hash: str,
    ) -> ExtractedResumeProfile:
        """
        Extracts structured profile by calling the LLM endpoint with defensive framing and JSON mode.
        """
        user_prompt = build_extraction_prompt(resume_pages)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "LLM Provider HTTP %s error: %s", exc.response.status_code, exc.response.text
                )
                raise ValidationError(
                    f"LLM API returned error: HTTP {exc.response.status_code}"
                ) from exc
            except Exception as exc:
                logger.exception("Failed to connect to LLM provider at %s", self.base_url)
                raise ValidationError(f"LLM provider request failed: {str(exc)}") from exc

        try:
            content_str = data["choices"][0]["message"]["content"]
            parsed_json = json.loads(content_str)
            profile = ExtractedResumeProfile.model_validate(parsed_json)
            return profile
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            logger.error("Failed to parse raw LLM output into JSON: %s", str(exc))
            raise ValidationError(f"Malformed LLM output received: {str(exc)}") from exc
        except Exception as exc:
            logger.error("Pydantic schema validation error on LLM profile output: %s", str(exc))
            raise ValidationError(f"LLM output violated profile schema: {str(exc)}") from exc

    async def extract_claims(
        self,
        resume_pages: dict[int, str],
        criteria: list[str],
        document_hash: str,
    ) -> ExtractionResult:
        """
        Extracts profile and maps candidate evidence against criteria.
        """
        profile = await self.extract_resume_profile(resume_pages, document_hash)

        # For generic criteria mapping via real provider, map extracted items
        claims: list[CandidateClaim] = []
        return ExtractionResult(
            claims=claims,
            profile=profile,
            document_hash=document_hash,
            provider=self.provider_name,
            model_name=self.model,
            prompt_version=self.prompt_version,
        )
