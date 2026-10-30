import re
from typing import Any

from app.services.benchmark.schemas import BenchmarkTestCase


class LiteralKeywordScreeningBaseline:
    """
    Simulates a traditional literal-keyword ATS screening parser.
    Relies purely on exact regex/substring word-boundary matches without semantic understanding,
    synonym expansion, source grounding, exposure depth analysis, or prompt-injection defense.
    """

    def screen_candidate(self, test_case: BenchmarkTestCase) -> dict[str, Any]:
        """
        Evaluates a candidate's resume pages against the criteria using simple literal matching.
        Returns per-criterion statuses and computed overall application outcome.
        """
        full_text = " ".join(test_case.resume_pages.values()).lower()
        criterion_results: dict[str, str] = {}

        for crit in test_case.criteria:
            crit_name = crit["name"].strip()
            # Strict literal regex word-boundary match
            pattern = r"\b" + re.escape(crit_name.lower()) + r"\b"
            if re.search(pattern, full_text):
                criterion_results[crit_name] = "supported"
            else:
                criterion_results[crit_name] = "not_found"

        # Traditional binary rule: If all required criteria are present -> supported, else -> not_found
        required_criteria = [
            c["name"] for c in test_case.criteria if c.get("category", "required") == "required"
        ]
        all_required_present = all(
            criterion_results.get(c) == "supported" for c in required_criteria
        )

        overall_status = "supported" if all_required_present else "not_found"

        return {
            "per_criterion": criterion_results,
            "overall_status": overall_status,
        }
