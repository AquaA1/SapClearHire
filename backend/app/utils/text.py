import difflib
import re


def normalize_whitespace(text: str) -> str:
    """Collapses consecutive whitespace and trims ends."""
    return re.sub(r"\s+", " ", text).strip()


def validate_excerpt_in_text(
    excerpt: str,
    target_text: str,
    min_similarity: float = 0.85,
) -> bool:
    """
    Validates whether an extracted source excerpt is genuinely grounded in the actual document text.

    RULES:
    - Never silently alter the excerpt string to make it pass.
    - Tests:
      1. Direct substring match after whitespace normalization.
      2. Case-insensitive substring match after whitespace normalization.
      3. Sliding-window sequence matcher for fuzzy alignment (handles OCR line wraps & hyphens).

    Returns True if grounded, False if hallucinated or fabricated.
    """
    if not excerpt or not target_text:
        return False

    norm_excerpt = normalize_whitespace(excerpt)
    norm_target = normalize_whitespace(target_text)

    # 1. Exact normalized match
    if norm_excerpt in norm_target:
        return True

    # 2. Case-insensitive normalized match
    if norm_excerpt.lower() in norm_target.lower():
        return True

    # 3. Fuzzy matching for long excerpts
    excerpt_len = len(norm_excerpt)
    if excerpt_len < 10:
        return False

    window_size = int(excerpt_len * 1.2)
    step = max(1, excerpt_len // 4)

    for i in range(0, max(1, len(norm_target) - excerpt_len), step):
        window = norm_target[i : i + window_size]
        matcher = difflib.SequenceMatcher(None, norm_excerpt.lower(), window.lower())
        if matcher.quick_ratio() >= min_similarity:
            if matcher.ratio() >= min_similarity:
                return True

    return False


def detect_prompt_injection_indicators(text: str) -> list[str]:
    """
    Detects known prompt-injection and jailbreak instruction patterns within untrusted text.
    Returns list of matched indicator descriptions.
    """
    indicators: list[str] = []
    lower_text = text.lower()

    injection_patterns = [
        (
            r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions?",
            "Instruction override attempt (ignore previous instructions)",
        ),
        (r"system\s*:\s*you\s+are", "Role impersonation attempt (system: you are)"),
        (
            r"you\s+must\s+(?:hire|accept|advance)\s+this\s+candidate",
            "Evaluation override attempt (must hire/accept)",
        ),
        (
            r"give\s+(?:this\s+candidate\s+)?(?:a\s+)?(?:100%|perfect\s+score)",
            "Scoring manipulation attempt (give 100% / perfect score)",
        ),
        (
            r"disregard\s+(?:all\s+)?(?:rules|guidelines)",
            "Guideline bypass attempt (disregard rules)",
        ),
        (
            r"<\|im_start\|>|<\|im_end\|>|\[inst\]|\[/inst\]",
            "LLM chat template delimiter injection attempt",
        ),
    ]

    for pattern, description in injection_patterns:
        if re.search(pattern, lower_text):
            indicators.append(description)

    return indicators


def detect_date_conflicts(start_date: str | None, end_date: str | None) -> str | None:
    """
    Validates chronological integrity between start_date and end_date.
    Returns error string if chronological order is violated, else None.
    """
    if not start_date or not end_date:
        return None

    if end_date.strip().lower() in ("present", "current", "now"):
        return None

    def _extract_year_month(d_str: str) -> tuple[int, int] | None:
        m = re.search(r"(\d{4})(?:-(\d{1,2}))?", d_str.strip())
        if m:
            year = int(m.group(1))
            month = int(m.group(2)) if m.group(2) else 1
            return (year, month)
        return None

    parsed_start = _extract_year_month(start_date)
    parsed_end = _extract_year_month(end_date)

    if parsed_start and parsed_end:
        if parsed_start > parsed_end:
            return f"End date ({end_date}) precedes start date ({start_date})"

    return None
