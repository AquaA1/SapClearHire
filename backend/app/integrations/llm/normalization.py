"""
Safe LLM output normalization utilities for ClearHire.
Normalizes raw model responses and JSON payloads prior to strict Pydantic schema validation.
"""

import json
import re
from typing import Any

from app.core.exceptions import ValidationError
from app.core.logging import logger


def strip_markdown_code_fences(content: str) -> str:
    """
    Extracts the JSON payload from LLM completion text, stripping Markdown code fences
    (e.g., ```json ... ``` or ``` ... ```) and any surrounding conversational text.
    """
    cleaned = content.strip()
    if not cleaned:
        return cleaned

    # Check for markdown code fences
    fence_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
    match = fence_pattern.search(cleaned)
    if match:
        return match.group(1).strip()

    # If no closing fence but starts with fence, strip the opening fence
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    # If text is enclosed in braces with surrounding chatter, extract the outer JSON object
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return cleaned[first_brace : last_brace + 1].strip()

    return cleaned


def normalize_llm_json_payload(data: Any) -> Any:
    """
    Normalizes structured dictionary data parsed from LLM JSON output.

    Safety and Integrity Rules:
    1. Null top-level or nested collections (e.g., 'skills': null, 'education': null)
       are normalized to empty lists ([]).
    2. Optional string fields with literal 'null', 'none', 'n/a', or empty strings
       are converted to None.
    3. Null boolean flags (e.g. is_current: null) are converted to default False.
    4. Null confidence scores default to 1.0.
    5. Numeric string values for page_number (e.g. '1') are coerced to int if purely numeric.
    6. Genuinely required structural fields (e.g., skill_name, exact_excerpt, page_number)
       are NEVER fabricated or assigned synthetic filler. If they are missing or invalid,
       they remain unchanged so that Pydantic validation rejects them cleanly.
    """
    if not isinstance(data, dict):
        return data

    normalized = dict(data)

    # Top-level list fields in ExtractedResumeProfile
    list_fields = [
        "skills",
        "experiences",
        "projects",
        "education",
        "certifications",
        "detected_conflicts",
    ]
    for lf in list_fields:
        if lf in normalized:
            if normalized[lf] is None:
                normalized[lf] = []
            elif isinstance(normalized[lf], list):
                # Process nested items
                if lf == "skills":
                    normalized[lf] = [_clean_skill_dict(item) for item in normalized[lf]]
                elif lf == "experiences":
                    normalized[lf] = [_clean_experience_dict(item) for item in normalized[lf]]
                elif lf == "projects":
                    normalized[lf] = [_clean_project_dict(item) for item in normalized[lf]]
                elif lf == "education":
                    normalized[lf] = [_clean_education_dict(item) for item in normalized[lf]]
                elif lf == "certifications":
                    normalized[lf] = [_clean_certification_dict(item) for item in normalized[lf]]
                elif lf == "detected_conflicts":
                    normalized[lf] = [
                        str(c).strip() for c in normalized[lf] if c and str(c).strip()
                    ]

    # Optional top-level string fields
    if "candidate_name" in normalized:
        normalized["candidate_name"] = _clean_optional_str(normalized["candidate_name"])

    return normalized


def _clean_optional_str(val: Any) -> str | None:
    """Cleans an optional string: converts null-equivalents or blanks to None."""
    if val is None:
        return None
    if isinstance(val, str):
        s = val.strip()
        if not s or s.lower() in ("null", "none", "n/a", "not specified", "unspecified"):
            return None
        return s
    return str(val).strip()


def _clean_source_quote_dict(val: Any) -> Any:
    """Normalizes SourceQuote dictionary without fabricating missing excerpts or pages."""
    if not isinstance(val, dict):
        return val

    sq = dict(val)
    # Coerce string page numbers like '1' to integer 1
    if "page_number" in sq and isinstance(sq["page_number"], str):
        if sq["page_number"].strip().isdigit():
            sq["page_number"] = int(sq["page_number"].strip())

    # Strip exact_excerpt if present
    if "exact_excerpt" in sq and isinstance(sq["exact_excerpt"], str):
        sq["exact_excerpt"] = sq["exact_excerpt"].strip()

    return sq


def _clean_skill_dict(val: Any) -> Any:
    if not isinstance(val, dict):
        return val

    item = dict(val)
    if "skill_name" in item and isinstance(item["skill_name"], str):
        item["skill_name"] = item["skill_name"].strip()

    if "category" in item:
        item["category"] = _clean_optional_str(item["category"])

    if "years_of_experience" in item:
        if item["years_of_experience"] is None or item["years_of_experience"] == "":
            item["years_of_experience"] = None

    if "confidence" in item:
        if item["confidence"] is None or item["confidence"] == "":
            item["confidence"] = 1.0

    if "source_quote" in item:
        item["source_quote"] = _clean_source_quote_dict(item["source_quote"])

    return item


def _clean_experience_dict(val: Any) -> Any:
    if not isinstance(val, dict):
        return val

    item = dict(val)
    for f in ("job_title", "company", "start_date", "end_date"):
        if f in item:
            item[f] = _clean_optional_str(item[f])

    if "is_current" in item:
        if item["is_current"] is None:
            item["is_current"] = False

    if "responsibilities" in item:
        if item["responsibilities"] is None:
            item["responsibilities"] = []
        elif isinstance(item["responsibilities"], list):
            item["responsibilities"] = [
                str(r).strip() for r in item["responsibilities"] if r and str(r).strip()
            ]

    if "source_quote" in item:
        item["source_quote"] = _clean_source_quote_dict(item["source_quote"])

    return item


def _clean_project_dict(val: Any) -> Any:
    if not isinstance(val, dict):
        return val

    item = dict(val)
    for f in ("project_name", "description"):
        if f in item:
            item[f] = _clean_optional_str(item[f])

    if "technologies" in item:
        if item["technologies"] is None:
            item["technologies"] = []
        elif isinstance(item["technologies"], list):
            item["technologies"] = [
                str(t).strip() for t in item["technologies"] if t and str(t).strip()
            ]

    if "source_quote" in item:
        item["source_quote"] = _clean_source_quote_dict(item["source_quote"])

    return item


def _clean_education_dict(val: Any) -> Any:
    if not isinstance(val, dict):
        return val

    item = dict(val)
    for f in ("institution", "degree", "field_of_study", "graduation_date"):
        if f in item:
            item[f] = _clean_optional_str(item[f])

    if "source_quote" in item:
        item["source_quote"] = _clean_source_quote_dict(item["source_quote"])

    return item


def _clean_certification_dict(val: Any) -> Any:
    if not isinstance(val, dict):
        return val

    item = dict(val)
    for f in (
        "certification_name",
        "issuing_organization",
        "issue_date",
        "expiration_date",
        "credential_id",
    ):
        if f in item:
            item[f] = _clean_optional_str(item[f])

    if "source_quote" in item:
        item["source_quote"] = _clean_source_quote_dict(item["source_quote"])

    return item


def parse_and_normalize_llm_json(content: str) -> dict[str, Any]:
    """
    Strips markdown formatting, parses raw JSON, and normalizes optional and collection fields.
    Raises ValidationError if JSON is unparseable or not a dictionary.
    """
    clean_str = strip_markdown_code_fences(content)
    try:
        data = json.loads(clean_str)
    except json.JSONDecodeError as exc:
        logger.warning("Failed to decode JSON from LLM output: %s", str(exc))
        raise ValidationError(f"Invalid JSON returned by LLM: {str(exc)}") from exc

    if not isinstance(data, dict):
        raise ValidationError("LLM output must be a JSON object, received " + type(data).__name__)

    return normalize_llm_json_payload(data)
