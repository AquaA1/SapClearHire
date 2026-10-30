from app.services.benchmark.runner import BenchmarkRunner
from app.services.benchmark.schemas import BENCHMARK_DISCLAIMER


def test_benchmark_runner_full_evaluation():
    """
    Test that BenchmarkRunner evaluates the 8 scenarios and generates
    reproducible metrics, discrepancy breakdowns, and qualitative findings.
    """
    runner = BenchmarkRunner()
    report = runner.run_benchmark()

    # 1. Structural assertions
    assert report.is_synthetic is True
    assert report.benchmark_disclaimer == BENCHMARK_DISCLAIMER
    assert report.sample_size == 8
    assert report.total_criteria_evaluations == 32
    assert len(report.candidate_results) == 8

    # 2. Metric comparisons
    b_metrics = report.baseline_metrics
    ch_metrics = report.clearhire_metrics

    # ClearHire demonstrates higher accuracy on the ground-truth benchmark
    assert ch_metrics.accuracy > b_metrics.accuracy
    assert ch_metrics.correct_evaluations > b_metrics.correct_evaluations

    # Baseline has significant false positives (buzzwords, prompt injection) and false negatives (synonyms)
    assert b_metrics.false_positives > 0
    assert b_metrics.false_negatives > 0

    # ClearHire correctly identifies ambiguous cases and avoids false negatives on synonyms
    assert ch_metrics.ambiguous_identified > 0
    assert ch_metrics.false_negatives == 0

    # 3. Specific failure mode breakdown
    misses = report.keyword_baseline_misses_breakdown
    assert misses["synonym_false_negatives"] >= 2  # K8s, Postgres
    assert misses["buzzword_false_positives"] >= 4  # All 4 criteria in Jordan's dump
    assert misses["prompt_injection_false_positives"] >= 2  # Postgres, Kubernetes in attack

    # 4. Report qualitative sections
    assert len(report.clearhire_findings) >= 4
    assert len(report.extraction_limitations) >= 3


def test_benchmark_runner_deterministic_repeatability():
    """Test that running the benchmark multiple times yields identical mathematical results."""
    runner = BenchmarkRunner()
    r1 = runner.run_benchmark()
    r2 = runner.run_benchmark()

    assert r1.baseline_metrics.accuracy == r2.baseline_metrics.accuracy
    assert r1.clearhire_metrics.accuracy == r2.clearhire_metrics.accuracy
    assert r1.baseline_metrics.precision == r2.baseline_metrics.precision
    assert r1.clearhire_metrics.precision == r2.clearhire_metrics.precision
    assert r1.baseline_metrics.f1_score == r2.baseline_metrics.f1_score
    assert r1.clearhire_metrics.f1_score == r2.clearhire_metrics.f1_score
