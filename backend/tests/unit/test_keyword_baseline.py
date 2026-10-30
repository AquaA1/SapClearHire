from app.services.benchmark.baseline import LiteralKeywordScreeningBaseline
from app.services.benchmark.dataset import get_ground_truth_benchmark_dataset


def test_keyword_baseline_exact_match_success():
    """Test that literal keyword baseline correctly finds direct verbatim skill mentions."""
    dataset = get_ground_truth_benchmark_dataset()
    alex_case = next(c for c in dataset if c.case_id == "TC-01")

    baseline = LiteralKeywordScreeningBaseline()
    result = baseline.screen_candidate(alex_case)

    # All criteria mentioned verbatim -> all supported
    assert result["per_criterion"]["Python"] == "supported"
    assert result["per_criterion"]["PostgreSQL"] == "supported"
    assert result["per_criterion"]["Kubernetes"] == "supported"
    assert result["per_criterion"]["Docker"] == "supported"
    assert result["overall_status"] == "supported"


def test_keyword_baseline_misses_synonyms():
    """
    Test that traditional keyword baseline fails on acronyms and synonyms
    ('K8s' instead of 'Kubernetes', 'Postgres' instead of 'PostgreSQL').
    """
    dataset = get_ground_truth_benchmark_dataset()
    marcus_case = next(c for c in dataset if c.case_id == "TC-02")

    baseline = LiteralKeywordScreeningBaseline()
    result = baseline.screen_candidate(marcus_case)

    # Keyword baseline produces FALSE NEGATIVES on synonyms
    assert result["per_criterion"]["Python"] == "supported"
    assert result["per_criterion"]["PostgreSQL"] == "not_found"  # Missed 'Postgres'
    assert result["per_criterion"]["Kubernetes"] == "not_found"  # Missed 'K8s'
    assert result["overall_status"] == "not_found"  # Candidate unjustly disqualified


def test_keyword_baseline_susceptible_to_buzzword_stuffing():
    """
    Test that literal keyword baseline produces FALSE POSITIVES on keyword-stuffed lists
    with no accompanying professional experience.
    """
    dataset = get_ground_truth_benchmark_dataset()
    jordan_case = next(c for c in dataset if c.case_id == "TC-04")

    baseline = LiteralKeywordScreeningBaseline()
    result = baseline.screen_candidate(jordan_case)

    # Baseline blindly passes buzzword dump
    assert result["per_criterion"]["Python"] == "supported"
    assert result["per_criterion"]["PostgreSQL"] == "supported"
    assert result["per_criterion"]["Kubernetes"] == "supported"
    assert result["per_criterion"]["Docker"] == "supported"
    assert result["overall_status"] == "supported"  # Candidate falsely approved


def test_keyword_baseline_susceptible_to_prompt_injection():
    """
    Test that literal keyword baseline produces FALSE POSITIVES by matching keywords
    injected in an adversarial attack.
    """
    dataset = get_ground_truth_benchmark_dataset()
    alice_case = next(c for c in dataset if c.case_id == "TC-08")

    baseline = LiteralKeywordScreeningBaseline()
    result = baseline.screen_candidate(alice_case)

    # Baseline matches 'PostgreSQL' and 'Kubernetes' which only exist in the injected attack!
    assert result["per_criterion"]["PostgreSQL"] == "supported"
    assert result["per_criterion"]["Kubernetes"] == "supported"
