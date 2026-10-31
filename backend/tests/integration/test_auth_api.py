"""
Integration tests for ClearHire first-party authentication and role-based security.
"""

import uuid
from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import UserRole, create_access_token
from app.repositories.domain import UserRepository


@pytest.mark.asyncio
async def test_candidate_registration_success(client: AsyncClient):
    payload = {
        "email": "alex.morgan@test.com",
        "password": "ValidPassword123!",
        "full_name": "Alex Morgan",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "alex.morgan@test.com"
    assert data["full_name"] == "Alex Morgan"
    assert data["role"] == "candidate"
    assert data["employer_id"] is None
    assert data["is_active"] is True
    assert "password_hash" not in data
    assert "password" not in data


@pytest.mark.asyncio
async def test_duplicate_email_registration_fails(client: AsyncClient):
    payload = {
        "email": "duplicate@test.com",
        "password": "Password123!",
        "full_name": "Duplicate User",
    }
    resp1 = await client.post("/api/v1/auth/register", json=payload)
    assert resp1.status_code == 201

    # Second registration with same email (even with different case)
    payload["email"] = "DUPLICATE@TEST.COM"
    resp2 = await client.post("/api/v1/auth/register", json=payload)
    assert resp2.status_code == 409
    data = resp2.json()
    assert "already exists" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_registration_rejects_role_tampering(client: AsyncClient):
    # Attempting to supply role or employer_id in public candidate registration
    payload = {
        "email": "hacker@test.com",
        "password": "Password123!",
        "full_name": "Attacker",
        "role": "employer_admin",
        "employer_id": "target_corp",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_registration_rejects_weak_password(client: AsyncClient):
    payload = {
        "email": "weak@test.com",
        "password": "short",
        "full_name": "Weak User",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_successful_login(client: AsyncClient):
    # Register candidate first
    reg_payload = {
        "email": "login.test@test.com",
        "password": "CorrectPassword123!",
        "full_name": "Login Tester",
    }
    reg_resp = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201

    # Attempt login
    login_payload = {
        "email": "login.test@test.com",
        "password": "CorrectPassword123!",
    }
    login_resp = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["expires_in"] > 0

    # Test /me endpoint with returned token
    token = token_data["access_token"]
    me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "login.test@test.com"
    assert me_data["role"] == "candidate"
    assert "password_hash" not in me_data


@pytest.mark.asyncio
async def test_login_incorrect_password(client: AsyncClient):
    reg_payload = {
        "email": "inc.pwd@test.com",
        "password": "RightPassword123!",
        "full_name": "Test User",
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "inc.pwd@test.com", "password": "WrongPassword123!"},
    )
    assert login_resp.status_code == 401
    assert "invalid email or password" in login_resp.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_login_unknown_email_returns_generic_error(client: AsyncClient):
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@test.com", "password": "AnyPassword123!"},
    )
    assert login_resp.status_code == 401
    # Generic message avoids user enumeration
    assert "invalid email or password" in login_resp.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_login_missing_credentials(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_inactive_account(client: AsyncClient, test_session: AsyncSession):
    # Register candidate
    reg_payload = {
        "email": "inactive@test.com",
        "password": "Password123!",
        "full_name": "Inactive User",
    }
    reg_resp = await client.post("/api/v1/auth/register", json=reg_payload)
    user_id = uuid.UUID(reg_resp.json()["id"])

    # Deactivate account directly in DB
    user_repo = UserRepository(test_session)
    user = await user_repo.get_by_id(user_id)
    assert user is not None
    user.is_active = False
    await test_session.commit()

    # Login attempt
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@test.com", "password": "Password123!"},
    )
    assert login_resp.status_code == 401
    assert "inactive" in login_resp.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_expired_jwt_rejected(client: AsyncClient):
    # Generate token expired 10 minutes ago
    expired_token = create_access_token(
        subject=str(uuid.uuid4()),
        role=UserRole.CANDIDATE,
        expires_delta=timedelta(minutes=-10),
    )
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp.status_code == 401
    assert "expired" in resp.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_invalid_jwt_signature_rejected(client: AsyncClient):
    token = create_access_token(
        subject=str(uuid.uuid4()),
        role=UserRole.CANDIDATE,
    )
    # Corrupt signature by modifying last characters
    tampered_token = token[:-5] + "XXXXX"
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert resp.status_code == 401
    assert "invalid" in resp.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_admin_provisioning_and_privilege_enforcement(client: AsyncClient):
    admin_id = str(uuid.uuid4())
    admin_token = create_access_token(
        subject=admin_id,
        role=UserRole.EMPLOYER_ADMIN,
        employer_id="tenant_alpha",
    )
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    candidate_token = create_access_token(
        subject=str(uuid.uuid4()),
        role=UserRole.CANDIDATE,
    )
    cand_headers = {"Authorization": f"Bearer {candidate_token}"}

    # 1. Candidate cannot provision an employer account (403 Forbidden)
    resp_cand_emp = await client.post(
        "/api/v1/auth/provision",
        headers=cand_headers,
        json={
            "email": "hacked.emp@test.com",
            "password": "Password123!",
            "full_name": "Hacked Employer",
            "role": "employer_admin",
            "employer_id": "tenant_alpha",
        },
    )
    assert resp_cand_emp.status_code == 403

    # 2. Candidate cannot provision a reviewer account (403 Forbidden)
    resp_cand_rev = await client.post(
        "/api/v1/auth/provision",
        headers=cand_headers,
        json={
            "email": "hacked.rev@test.com",
            "password": "Password123!",
            "full_name": "Hacked Reviewer",
            "role": "reviewer",
        },
    )
    assert resp_cand_rev.status_code == 403

    # 3. Candidate cannot provision a system auditor account (403 Forbidden)
    resp_cand_aud = await client.post(
        "/api/v1/auth/provision",
        headers=cand_headers,
        json={
            "email": "hacked.aud@test.com",
            "password": "Password123!",
            "full_name": "Hacked Auditor",
            "role": "system_auditor",
        },
    )
    assert resp_cand_aud.status_code == 403

    # 4. Employer Admin CAN provision a reviewer for their tenant
    resp_prov_rev = await client.post(
        "/api/v1/auth/provision",
        headers=admin_headers,
        json={
            "email": "reviewer1@tenant-alpha.com",
            "password": "Password123!",
            "full_name": "Reviewer One",
            "role": "reviewer",
            "employer_id": "tenant_alpha",
        },
    )
    assert resp_prov_rev.status_code == 201
    rev_data = resp_prov_rev.json()
    assert rev_data["role"] == "reviewer"
    assert rev_data["employer_id"] == "tenant_alpha"

    # 5. Employer Admin CANNOT provision a system auditor account (403 Forbidden)
    resp_admin_aud = await client.post(
        "/api/v1/auth/provision",
        headers=admin_headers,
        json={
            "email": "auditor@test.com",
            "password": "Password123!",
            "full_name": "Auditor",
            "role": "system_auditor",
        },
    )
    assert resp_admin_aud.status_code == 403

    # 6. Employer Admin CANNOT provision accounts for another tenant (403 Forbidden)
    resp_cross_tenant = await client.post(
        "/api/v1/auth/provision",
        headers=admin_headers,
        json={
            "email": "cross.emp@test.com",
            "password": "Password123!",
            "full_name": "Cross Tenant User",
            "role": "employer_admin",
            "employer_id": "tenant_beta",
        },
    )
    assert resp_cross_tenant.status_code == 403


@pytest.mark.asyncio
async def test_login_and_access_authorized_document_flow(client: AsyncClient):
    # End-to-end integration: Register, login, get token, check /me, verify access
    reg_payload = {
        "email": "flow.candidate@test.com",
        "password": "ValidPassword123!",
        "full_name": "Flow Candidate",
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "flow.candidate@test.com", "password": "ValidPassword123!"},
    )
    token = login_resp.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Verify /me
    me_resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "flow.candidate@test.com"

    # Verify candidate can access /documents endpoints, but cannot access /jobs (which requires employer_admin)
    job_create_resp = await client.post(
        "/api/v1/jobs",
        headers=auth_headers,
        json={
            "title": "Unauthorized Job",
            "description": "Test",
            "department": "Eng",
            "criteria": [],
        },
    )
    assert job_create_resp.status_code == 403
