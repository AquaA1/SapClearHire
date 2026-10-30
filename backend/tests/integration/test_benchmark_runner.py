import uuid

import pytest
from httpx import AsyncClient

from app.core.security import UserRole, create_access_token


@pytest.mark.asyncio
async def test_run_benchmark_endpoint_authenticated(client: AsyncClient):
    """
    Test GET /api/v1/benchmark/run returns reproducible benchmark results
    with metrics, candidate comparisons, and limitations disclaimer.
    """
    user_id = str(uuid.uuid4())
    headers = {"Authorization": f"Bearer {create_access_token(user_id, UserRole.EMPLOYER_ADMIN)}"}

    res = await client.get("/api/v1/benchmark/run", headers=headers)
    assert res.status_code == 200
    report = res.json()

    assert report["is_synthetic"] is True
    assert "NOTICE:" in report["benchmark_disclaimer"]
    assert report["sample_size"] == 8
    assert report["total_criteria_evaluations"] == 32
    assert len(report["candidate_results"]) == 8

    # Baseline vs ClearHire metrics
    b_metrics = report["baseline_metrics"]
    ch_metrics = report["clearhire_metrics"]
    assert ch_metrics["accuracy"] > b_metrics["accuracy"]
    assert b_metrics["false_positives"] > 0
    assert b_metrics["false_negatives"] > 0
    assert ch_metrics["ambiguous_identified"] > 0

    # Failure mode counts
    misses = report["keyword_baseline_misses_breakdown"]
    assert misses["synonym_false_negatives"] >= 2
    assert misses["buzzword_false_positives"] >= 4
    assert misses["prompt_injection_false_positives"] >= 2


@pytest.mark.asyncio
async def test_run_benchmark_endpoint_unauthenticated_rejected(client: AsyncClient):
    """Test that unauthenticated requests to the benchmark endpoint return 401 Unauthorized."""
    res = await client.get("/api/v1/benchmark/run")
    assert res.status_code == 401
