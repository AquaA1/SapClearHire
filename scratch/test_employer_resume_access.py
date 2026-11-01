import asyncio
import hashlib
import uuid
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import UserRole, create_access_token
from app.db.models.application import Application
from app.db.models.document import Document
from app.db.models.enums import ApplicationStatus, DocumentProcessingStatus, JobStatus
from app.db.models.job import Job
from app.db.models.user import User
from app.db.session import get_session_factory
from app.main import app
from app.services.storage import LocalStorageService


async def run_tests():
    print("=" * 70)
    print("STARTING TEST SUITE: Employer Resume Access & PDF Retrieval")
    print("=" * 70)

    factory = get_session_factory()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with factory() as session:
            # 1. Setup Test Users:
            # Employer 1 (Org A)
            emp1_id = uuid.uuid4()
            emp1 = User(
                id=emp1_id,
                email=f"emp1_{emp1_id.hex[:6]}@orga.com",
                password_hash="dummy_hash",
                role=UserRole.EMPLOYER_ADMIN,
                employer_id="org_alpha",
                full_name="Employer One",
                is_active=True,
            )
            session.add(emp1)

            # Employer 2 (Org B)
            emp2_id = uuid.uuid4()
            emp2 = User(
                id=emp2_id,
                email=f"emp2_{emp2_id.hex[:6]}@orgb.com",
                password_hash="dummy_hash",
                role=UserRole.EMPLOYER_ADMIN,
                employer_id="org_beta",
                full_name="Employer Two",
                is_active=True,
            )
            session.add(emp2)

            # Candidate A
            cand_a_id = uuid.uuid4()
            cand_a = User(
                id=cand_a_id,
                email=f"cand_a_{cand_a_id.hex[:6]}@example.com",
                password_hash="dummy_hash",
                role=UserRole.CANDIDATE,
                full_name="Candidate A",
                is_active=True,
            )
            session.add(cand_a)

            # Candidate B
            cand_b_id = uuid.uuid4()
            cand_b = User(
                id=cand_b_id,
                email=f"cand_b_{cand_b_id.hex[:6]}@example.com",
                password_hash="dummy_hash",
                role=UserRole.CANDIDATE,
                full_name="Candidate B",
                is_active=True,
            )
            session.add(cand_b)

            # Job 1 created by Employer 1 (Org A)
            job1_id = uuid.uuid4()
            job1 = Job(
                id=job1_id,
                employer_id=emp1_id,
                title="Lead Python Cloud Architect",
                status=JobStatus.ACTIVE,
                department="Engineering",
            )
            session.add(job1)

            # Create physical test PDF file in storage for Candidate A
            storage = LocalStorageService()
            doc_a_id = uuid.uuid4()
            fake_pdf_content = b"%PDF-1.4\n%Candidate A Authentic Resume PDF Content\n%%EOF"
            file_path, file_hash, file_size = storage.save_file(
                file_content=fake_pdf_content,
                original_filename="candidate_a_resume.pdf",
                document_id=doc_a_id,
            )

            doc_a = Document(
                id=doc_a_id,
                candidate_id=cand_a_id,
                file_name="candidate_a_resume.pdf",
                file_path=file_path,
                file_hash=file_hash,
                file_size_bytes=file_size,
                mime_type="application/pdf",
                processing_status=DocumentProcessingStatus.COMPLETED,
                page_count=1,
                extracted_text_by_page={"1": "Candidate A Experienced Python & FastAPI Developer"},
            )
            session.add(doc_a)

            # Application: Candidate A applies to Job 1 (Employer 1) with Document A
            app_a_id = uuid.uuid4()
            app_a = Application(
                id=app_a_id,
                job_id=job1_id,
                candidate_id=cand_a_id,
                primary_document_id=doc_a_id,
                status=ApplicationStatus.SUBMITTED,
            )
            session.add(app_a)

            # Create Document for Candidate B (NOT applied to any job of Employer 1)
            doc_b_id = uuid.uuid4()
            fake_pdf_content_b = b"%PDF-1.4\n%Candidate B Confidential Resume PDF Content\n%%EOF"
            file_path_b, file_hash_b, file_size_b = storage.save_file(
                file_content=fake_pdf_content_b,
                original_filename="candidate_b_confidential.pdf",
                document_id=doc_b_id,
            )

            doc_b = Document(
                id=doc_b_id,
                candidate_id=cand_b_id,
                file_name="candidate_b_confidential.pdf",
                file_path=file_path_b,
                file_hash=file_hash_b,
                file_size_bytes=file_size_b,
                mime_type="application/pdf",
                processing_status=DocumentProcessingStatus.COMPLETED,
                page_count=1,
                extracted_text_by_page={"1": "Candidate B Confidential Data"},
            )
            session.add(doc_b)

            await session.commit()

        # Create JWT Tokens
        token_emp1 = create_access_token(subject=str(emp1_id), role=UserRole.EMPLOYER_ADMIN, employer_id="org_alpha")
        token_emp2 = create_access_token(subject=str(emp2_id), role=UserRole.EMPLOYER_ADMIN, employer_id="org_beta")
        token_cand_a = create_access_token(subject=str(cand_a_id), role=UserRole.CANDIDATE)
        token_cand_b = create_access_token(subject=str(cand_b_id), role=UserRole.CANDIDATE)

        # ----------------------------------------------------------------------
        # TEST 1: Authorized Employer (Employer 1) retrieves Candidate A's PDF
        # ----------------------------------------------------------------------
        print("\n--- Test 1: Authorized Employer PDF Retrieval ---")
        res1 = await client.get(
            f"/api/v1/documents/{doc_a_id}/file?disposition=inline",
            headers={"Authorization": f"Bearer {token_emp1}"},
        )
        assert res1.status_code == 200, f"Expected 200, got {res1.status_code}: {res1.text}"
        assert res1.headers.get("content-type") == "application/pdf", f"Unexpected content type: {res1.headers.get('content-type')}"
        assert 'inline; filename="candidate_a_resume.pdf"' in res1.headers.get("content-disposition", ""), f"Unexpected Content-Disposition: {res1.headers.get('content-disposition')}"
        assert res1.content.startswith(b"%PDF-"), "Response does not start with PDF magic bytes"
        print("✓ PASS: Authorized employer successfully retrieved original PDF with proper headers and content.")

        # Test with disposition=attachment
        res1_att = await client.get(
            f"/api/v1/documents/{doc_a_id}/file?disposition=attachment",
            headers={"Authorization": f"Bearer {token_emp1}"},
        )
        assert res1_att.status_code == 200
        assert 'attachment; filename="candidate_a_resume.pdf"' in res1_att.headers.get("content-disposition", "")
        print("✓ PASS: Download disposition=attachment correctly set in header.")

        # ----------------------------------------------------------------------
        # TEST 2: Unauthorized Employer (Employer 2, Org B) cannot retrieve Candidate A's PDF
        # ----------------------------------------------------------------------
        print("\n--- Test 2: Unauthorized Employer Cross-Tenant Rejection ---")
        res2 = await client.get(
            f"/api/v1/documents/{doc_a_id}/file",
            headers={"Authorization": f"Bearer {token_emp2}"},
        )
        assert res2.status_code == 403, f"Expected 403 Forbidden, got {res2.status_code}: {res2.text}"
        print("✓ PASS: Cross-tenant employer blocked with HTTP 403 Forbidden.")

        # ----------------------------------------------------------------------
        # TEST 3: Candidate A cannot access Candidate B's PDF
        # ----------------------------------------------------------------------
        print("\n--- Test 3: Candidate Cross-User Isolation ---")
        res3_fail = await client.get(
            f"/api/v1/documents/{doc_b_id}/file",
            headers={"Authorization": f"Bearer {token_cand_a}"},
        )
        assert res3_fail.status_code == 403, f"Expected 403 Forbidden, got {res3_fail.status_code}: {res3_fail.text}"
        print("✓ PASS: Candidate A forbidden from accessing Candidate B's document (HTTP 403).")

        # Candidate B accessing their own document should succeed
        res3_ok = await client.get(
            f"/api/v1/documents/{doc_b_id}/file",
            headers={"Authorization": f"Bearer {token_cand_b}"},
        )
        assert res3_ok.status_code == 200, f"Expected 200, got {res3_ok.status_code}: {res3_ok.text}"
        print("✓ PASS: Candidate B can access their own uploaded document (HTTP 200).")

        # ----------------------------------------------------------------------
        # TEST 4: Invalid Document IDs
        # ----------------------------------------------------------------------
        print("\n--- Test 4: Invalid and Missing Document IDs ---")
        non_existent_id = uuid.uuid4()
        res4_404 = await client.get(
            f"/api/v1/documents/{non_existent_id}/file",
            headers={"Authorization": f"Bearer {token_emp1}"},
        )
        assert res4_404.status_code == 404, f"Expected 404, got {res4_404.status_code}: {res4_404.text}"
        print("✓ PASS: Non-existent document UUID returns HTTP 404 Not Found.")

        res4_422 = await client.get(
            "/api/v1/documents/not-a-valid-uuid/file",
            headers={"Authorization": f"Bearer {token_emp1}"},
        )
        assert res4_422.status_code == 422, f"Expected 422, got {res4_422.status_code}: {res4_422.text}"
        print("✓ PASS: Malformed document ID returns HTTP 422 Unprocessable Entity.")

        # Path traversal attempt
        res4_trav = await client.get(
            "/api/v1/documents/../../../etc/passwd/file",
            headers={"Authorization": f"Bearer {token_emp1}"},
        )
        assert res4_trav.status_code in (404, 422), f"Expected 404/422, got {res4_trav.status_code}"
        print("✓ PASS: Path traversal attempt safely rejected.")

        # ----------------------------------------------------------------------
        # TEST 5: Integrity Verification (Original PDF Checksum)
        # ----------------------------------------------------------------------
        print("\n--- Test 5: Original Document Integrity Checksum ---")
        hasher = hashlib.sha256()
        hasher.update(res1.content)
        received_hash = hasher.hexdigest()
        assert received_hash == file_hash, f"Hash mismatch: received {received_hash} vs expected {file_hash}"
        assert res1.content == fake_pdf_content, "Content binary does not match original"
        print(f"✓ PASS: Byte-for-byte checksum verification matched SHA-256: {received_hash}")

        # ----------------------------------------------------------------------
        # TEST 6: Extracted Text Matching Backend
        # ----------------------------------------------------------------------
        print("\n--- Test 6: Extracted Text Status Verification ---")
        res6 = await client.get(
            f"/api/v1/documents/{doc_a_id}/status",
            headers={"Authorization": f"Bearer {token_emp1}"},
        )
        assert res6.status_code == 200, f"Expected 200, got {res6.status_code}: {res6.text}"
        data6 = res6.json()
        assert data6["extracted_text_by_page"]["1"] == "Candidate A Experienced Python & FastAPI Developer"
        assert data6["processing_status"] == "completed"
        print("✓ PASS: Page-by-page extracted text matches backend records verbatim.")

        # ----------------------------------------------------------------------
        # TEST 7: Expired / Missing Authentication Handling
        # ----------------------------------------------------------------------
        print("\n--- Test 7: Authentication Enforcement ---")
        res7_no_auth = await client.get(f"/api/v1/documents/{doc_a_id}/file")
        assert res7_no_auth.status_code == 401, f"Expected 401, got {res7_no_auth.status_code}: {res7_no_auth.text}"
        print("✓ PASS: Unauthenticated request rejected with HTTP 401 Unauthorized.")

        res7_invalid_token = await client.get(
            f"/api/v1/documents/{doc_a_id}/file",
            headers={"Authorization": "Bearer invalid_or_expired_jwt_token"},
        )
        assert res7_invalid_token.status_code == 401, f"Expected 401, got {res7_invalid_token.status_code}: {res7_invalid_token.text}"
        print("✓ PASS: Invalid/expired token rejected with HTTP 401 Unauthorized.")

        # ----------------------------------------------------------------------
        # TEST 8: Verify Internal Storage Paths Are Never Exposed
        # ----------------------------------------------------------------------
        print("\n--- Test 8: Internal Storage Path Concealment ---")
        assert "storage/documents" not in res1.text
        assert str(storage.documents_dir) not in res1.headers.get("content-disposition", "")
        print("✓ PASS: Internal filesystem paths are completely concealed from client.")

    print("\n" + "=" * 70)
    print("ALL 8 AUTOMATED SECURITY & INTEGRATION TESTS PASSED CLEANLY!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_tests())
