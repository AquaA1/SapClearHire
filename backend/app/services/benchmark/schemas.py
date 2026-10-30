from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

BENCHMARK_DISCLAIMER = (
    "NOTICE: This benchmark operates on synthetic, ground-truth-labelled resume scenarios specifically "
    "designed to evaluate ATS screening limitations and evidence-matching performance. "
    "Metrics (Precision, Recall, Accuracy, F1) reflect performance strictly on this defined synthetic dataset "
    "and should not be interpreted as empirical real-world hiring outcomes."
)


class BenchmarkScenarioType(StrEnum):
    """Categorization of candidate resume screening scenarios."""

    DIRECT_SKILL = "direct_skill"
    SYNONYM_EVIDENCE = "synonym_evidence"
    SKILLS_IN_PROJECTS = "skills_in_projects"
    SKILLS_WITHOUT_CONTEXT = "skills_without_context"
    MISSING_EVIDENCE = "missing_evidence"
    CONFLICTING_DATES = "conflicting_dates"
    NON_STANDARD_LAYOUT = "non_standard_layout"
    PROMPT_INJECTION = "prompt_injection"


class BenchmarkTestCase(BaseModel):
    """Single labelled ground-truth test case in the benchmark dataset."""

    model_config = ConfigDict(from_attributes=True)

    case_id: str
    candidate_name: str
    scenario: BenchmarkScenarioType
    scenario_description: str
    resume_pages: dict[int, str]
    criteria: list[dict[str, str]] = Field(
        description="Job criteria list: [{'name': 'Python', 'category': 'required'}, ...]"
    )
    ground_truth_per_criterion: dict[str, str] = Field(
        description="Factual ground-truth status ('supported', 'not_found', 'ambiguous') for each criterion"
    )
    ground_truth_overall: str = Field(
        description="Expected overall application status ('supported', 'not_found', 'ambiguous')"
    )


class CriterionComparison(BaseModel):
    """Side-by-side evaluation outcome for a single criterion."""

    model_config = ConfigDict(from_attributes=True)

    criterion_name: str
    ground_truth: str
    baseline_status: str
    clearhire_status: str
    baseline_correct: bool
    clearhire_correct: bool
    notes: str


class CandidateBenchmarkResult(BaseModel):
    """Benchmark outcome for a candidate application."""

    model_config = ConfigDict(from_attributes=True)

    case_id: str
    candidate_name: str
    scenario: BenchmarkScenarioType
    ground_truth_overall: str
    baseline_overall: str
    clearhire_overall: str
    baseline_correct: bool
    clearhire_correct: bool
    criterion_comparisons: list[CriterionComparison]
    summary_findings: str


class ScreeningMetrics(BaseModel):
    """Confusion matrix metrics computed strictly against verified ground truth."""

    model_config = ConfigDict(from_attributes=True)

    total_evaluations: int
    correct_evaluations: int
    true_positives: int = Field(description="Directly supported criteria correctly identified")
    true_negatives: int = Field(description="Missing criteria correctly identified as not_found")
    ambiguous_identified: int = Field(
        description="Uncertain / conflicting criteria correctly identified as ambiguous"
    )
    false_positives: int = Field(
        description="Missing/ambiguous criteria wrongly marked supported (e.g. keyword stuffing)"
    )
    false_negatives: int = Field(
        description="Supported criteria missed (e.g. synonym variant unreached)"
    )
    accuracy: float = Field(
        description="Ratio of correct predictions over total evaluations (0.0 to 1.0)"
    )
    precision: float | None = Field(default=None, description="TP / (TP + FP) where defined")
    recall: float | None = Field(default=None, description="TP / (TP + FN) where defined")
    f1_score: float | None = Field(
        default=None, description="Harmonic mean of precision and recall"
    )


class BenchmarkReport(BaseModel):
    """Complete, reproducible benchmark report comparing baseline ATS against ClearHire."""

    model_config = ConfigDict(from_attributes=True)

    is_synthetic: Literal[True] = True
    benchmark_disclaimer: str = BENCHMARK_DISCLAIMER
    sample_size: int = Field(description="Number of candidate test cases evaluated")
    total_criteria_evaluations: int = Field(
        description="Total criterion-level evaluations conducted"
    )
    baseline_metrics: ScreeningMetrics
    clearhire_metrics: ScreeningMetrics
    candidate_results: list[CandidateBenchmarkResult]
    keyword_baseline_misses_breakdown: dict[str, int] = Field(
        description="Factual count of baseline failure modes (synonym misses, buzzword false positives, injection susceptibility)"
    )
    clearhire_findings: list[str] = Field(
        description="Key observable behaviors and strengths of evidence matching"
    )
    extraction_limitations: list[str] = Field(
        description="Known limitations and boundaries of AI extraction"
    )
