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

    Uses:
    1. Direct substring match after whitespace normalization.
    2. Case-insensitive substring match.
    3. Sliding-window sequence matcher for fuzzy alignment (handles OCR/whitespace variations).

    Returns True if grounded, False if hallucinated or altered.
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
    # Extract candidate chunks of similar length to check ratio
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
