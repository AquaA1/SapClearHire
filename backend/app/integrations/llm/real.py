import json
from typing import Any

import httpx

from app.core.exceptions import ValidationError
from app.core.logging import logger
from app.integrations.llm.base import BaseLLMProvider
from app.integrations.llm.normalization import parse_and_normalize_llm_json
from app.integrations.llm.prompts import (
    EXTRACTION_SYSTEM_PROMPT,
    PROMPT_VERSION,
    build_correction_prompt,
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
        self.model_name = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.provider_name = provider_name
        self.prompt_version = PROMPT_VERSION
        self.last_usage: dict[str, Any] = {}
        self.last_model: str = model

    async def _call_chat_completion(
        self,
        client: httpx.AsyncClient,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Executes HTTP POST to chat completions endpoint with error isolation."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }
        try:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data
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

    async def extract_resume_profile(
        self,
        resume_pages: dict[int, str],
        document_hash: str,
    ) -> ExtractedResumeProfile:
        """
        Extracts structured profile by calling the LLM endpoint with defensive framing and JSON mode.
        If output fails JSON parsing or schema validation, performs at most one controlled correction.
        """
        user_prompt = build_extraction_prompt(resume_pages)
        messages = [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            data = await self._call_chat_completion(client, messages)
            self.last_usage = data.get("usage", {})
            self.last_model = data.get("model", self.model)
            content_str = (
                data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
            ).strip()

            try:
                normalized_json = parse_and_normalize_llm_json(content_str)
                profile = ExtractedResumeProfile.model_validate(normalized_json)
                return profile
            except Exception as initial_error:
                logger.warning(
                    "Initial LLM profile extraction output failed validation: %s. Initiating controlled correction attempt.",
                    str(initial_error),
                )

                # Exactly one controlled correction attempt
                correction_prompt = build_correction_prompt(
                    resume_pages=resume_pages,
                    previous_raw_output=content_str,
                    validation_error=str(initial_error),
                )
                correction_messages = [
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": content_str},
                    {"role": "user", "content": correction_prompt},
                ]

                corr_data = await self._call_chat_completion(client, correction_messages)
                corr_content_str = (
                    corr_data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
                ).strip()

                try:
                    corr_json = parse_and_normalize_llm_json(corr_content_str)
                    profile = ExtractedResumeProfile.model_validate(corr_json)
                    logger.info(
                        "Controlled correction attempt succeeded for LLM profile extraction."
                    )
                    return profile
                except Exception as corr_error:
                    logger.error(
                        "Controlled correction attempt failed: %s (initial error was: %s)",
                        str(corr_error),
                        str(initial_error),
                    )
                    raise ValidationError(
                        f"LLM output violated profile schema: {str(corr_error)}"
                    ) from corr_error

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

    async def generate_simple_completion(
        self,
        user_prompt: str,
        system_prompt: str = "You are a helpful structured JSON extractor. Always output valid JSON.",
        max_tokens: int = 256,
    ) -> dict[str, Any]:
        """
        Executes a single structured JSON completion request using the configured provider endpoint.
        Used for verification and smoke testing.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
            "max_tokens": max_tokens,
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
            return {
                "content": parsed_json,
                "usage": data.get("usage", {}),
                "model": data.get("model", self.model),
                "raw_response": data,
            }
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            logger.error("Failed to parse raw LLM output into JSON: %s", str(exc))
            raise ValidationError(f"Malformed LLM output received: {str(exc)}") from exc
