import pytest

from app.integrations.llm.fake import FakeLLMProvider
from app.integrations.llm.schemas import EvidenceStatus


@pytest.mark.asyncio
async def test_fake_llm_provider_determines_supported_and_not_found():
    provider = FakeLLMProvider()

    mock_resume_pages = {
        1: "Jane Doe. Experienced Backend Engineer with 5 years in Python and FastAPI microservices.",
        2: "Led migration of legacy databases to PostgreSQL. Designed distributed worker queues with Python.",
    }

    criteria = ["FastAPI", "PostgreSQL", "Kubernetes"]
    doc_hash = "abc123456789hash"

    result = await provider.extract_claims(
        resume_pages=mock_resume_pages,
        criteria=criteria,
        document_hash=doc_hash,
    )

    assert result.document_hash == doc_hash
    assert result.provider == "fake"
    assert len(result.claims) == 3

    # FastAPI should be supported on page 1
    fastapi_claim = next(c for c in result.claims if c.criterion_name == "FastAPI")
    assert fastapi_claim.status == EvidenceStatus.SUPPORTED
    assert len(fastapi_claim.source_quotes) == 1
    assert fastapi_claim.source_quotes[0].page_number == 1
    assert "FastAPI" in fastapi_claim.source_quotes[0].exact_excerpt

    # PostgreSQL should be supported on page 2
    postgres_claim = next(c for c in result.claims if c.criterion_name == "PostgreSQL")
    assert postgres_claim.status == EvidenceStatus.SUPPORTED
    assert len(postgres_claim.source_quotes) == 1
    assert postgres_claim.source_quotes[0].page_number == 2
    assert "PostgreSQL" in postgres_claim.source_quotes[0].exact_excerpt

    # Kubernetes was not in resume
    k8s_claim = next(c for c in result.claims if c.criterion_name == "Kubernetes")
    assert k8s_claim.status == EvidenceStatus.NOT_FOUND
    assert len(k8s_claim.source_quotes) == 0


@pytest.mark.asyncio
async def test_fake_llm_provider_flags_ambiguous_evidence():
    provider = FakeLLMProvider()

    mock_resume_pages = {
        1: "John Smith. Basic familiarity and student exposure to Docker containerization.",
    }

    criteria = ["Docker"]
    result = await provider.extract_claims(
        resume_pages=mock_resume_pages,
        criteria=criteria,
        document_hash="hash987",
    )

    docker_claim = next(c for c in result.claims if c.criterion_name == "Docker")
    assert docker_claim.status == EvidenceStatus.AMBIGUOUS
    assert len(docker_claim.source_quotes) == 1
    assert docker_claim.source_quotes[0].page_number == 1


@pytest.mark.asyncio
async def test_http_client_llm_provider_controlled_correction_success(monkeypatch):
    """Verifies HTTPClientLLMProvider performs at most one controlled correction on schema error."""
    import httpx

    from app.integrations.llm.real import HTTPClientLLMProvider

    call_count = 0

    req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")

    async def mock_post(self, url, headers=None, json=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First attempt returns invalid schema (skills is string instead of list)
            return httpx.Response(
                200,
                request=req,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": '{"candidate_name": "Test", "skills": "not_a_list"}'
                            }
                        }
                    ]
                },
            )
        else:
            # Second attempt (correction) returns valid JSON
            return httpx.Response(
                200,
                request=req,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": """{
                                "candidate_name": "Test",
                                "skills": [{
                                    "skill_name": "Python",
                                    "source_quote": {"page_number": 1, "exact_excerpt": "Python"}
                                }],
                                "experiences": [],
                                "education": [],
                                "projects": [],
                                "certifications": [],
                                "detected_conflicts": []
                            }"""
                            }
                        }
                    ]
                },
            )

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    provider = HTTPClientLLMProvider(api_key="mock_key")
    profile = await provider.extract_resume_profile(
        resume_pages={1: "Python developer"},
        document_hash="test_hash",
    )

    assert call_count == 2
    assert profile.candidate_name == "Test"
    assert len(profile.skills) == 1
    assert profile.skills[0].skill_name == "Python"


@pytest.mark.asyncio
async def test_http_client_llm_provider_controlled_correction_failure(monkeypatch):
    """Verifies HTTPClientLLMProvider raises ValidationError when correction also fails."""
    import httpx

    from app.core.exceptions import ValidationError
    from app.integrations.llm.real import HTTPClientLLMProvider

    call_count = 0
    req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")

    async def mock_post(self, url, headers=None, json=None):
        nonlocal call_count
        call_count += 1
        return httpx.Response(
            200,
            request=req,
            json={"choices": [{"message": {"content": "still invalid json {"}}]},
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    provider = HTTPClientLLMProvider(api_key="mock_key")
    with pytest.raises(ValidationError) as exc:
        await provider.extract_resume_profile(
            resume_pages={1: "Sample"},
            document_hash="test_hash",
        )

    # 1 initial + 1 correction = 2 calls max
    assert call_count == 2
    assert "LLM output violated profile schema" in str(exc.value)
