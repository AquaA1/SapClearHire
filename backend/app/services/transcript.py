import asyncio
import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.core.logging import logger
from app.db.models.application import Application
from app.db.models.enums import DocumentProcessingStatus, EvidenceStatus
from app.db.models.job import Job, JobCriterion
from app.db.models.transcript import InterviewTranscript, TranscriptQAItem
from app.db.session import get_session_factory
from app.integrations.llm import get_llm_provider
from app.integrations.llm.prompts import (
    INTERVIEW_ANALYSIS_SYSTEM_PROMPT,
    build_interview_analysis_prompt,
)
from app.repositories.audit import AuditEventRepository
from app.services.storage import get_storage_service
from app.utils.transcript import (
    estimate_line_numbers,
    extract_transcript_text,
    validate_transcript_quote_grounding,
)
from app.workers import get_background_worker


class InterviewTranscriptService:
    """
    Orchestrates interview transcript storage, dialogue parsing, Q&A extraction,
    and constructive coaching analysis for Phase 3 Interview Coach.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.storage = get_storage_service()

    async def create_and_store_transcript(
        self,
        application_id: uuid.UUID,
        uploader_id: uuid.UUID | None,
        file_content: bytes,
        filename: str,
        round_name: str,
        session: AsyncSession,
    ) -> InterviewTranscript:
        """
        Validates transcript content, stores raw file in storage, and initializes
        queued InterviewTranscript record with an immutable audit event.
        """
        # Validate format and extract plain text
        raw_text = extract_transcript_text(filename=filename, content=file_content)
        if not raw_text.strip():
            raise ValidationError("Transcript text content is empty.")

        transcript_id = uuid.uuid4()
        storage_path, file_hash, file_size = self.storage.save_file(
            file_content=file_content,
            original_filename=filename,
            document_id=transcript_id,
        )

        app_uuid = uuid.UUID(str(application_id)) if application_id else None
        uploader_uuid = uuid.UUID(str(uploader_id)) if uploader_id else None

        transcript = InterviewTranscript(
            id=transcript_id,
            application_id=app_uuid,
            uploader_id=uploader_uuid,
            round_name=round_name.strip() or "Technical Interview",
            file_name=filename,
            file_path=storage_path,
            file_hash=file_hash,
            file_size_bytes=file_size,
            mime_type="text/plain",
            processing_status=DocumentProcessingStatus.QUEUED,
            raw_text=raw_text,
            processing_error=None,
        )
        session.add(transcript)
        await session.flush()

        # Audit event
        audit_repo = AuditEventRepository(session)
        await audit_repo.log_event(
            action="TRANSCRIPT_UPLOADED",
            resource_type="interview_transcript",
            resource_id=str(transcript.id),
            actor_id=str(uploader_id) if uploader_id else "system",
            actor_role="employer",
            entity_version=1,
            prior_state=None,
            new_state={
                "processing_status": DocumentProcessingStatus.QUEUED.value,
                "application_id": str(application_id),
                "round_name": transcript.round_name,
                "file_hash": file_hash,
            },
            details={
                "file_name": filename,
                "round_name": transcript.round_name,
                "file_size_bytes": file_size,
            },
        )

        # Enqueue background analysis
        worker = get_background_worker()
        await worker.submit_job(
            job_type="analyze_transcript",
            payload={"transcript_id": str(transcript.id)},
        )

        return transcript

    async def process_transcript_analysis(
        self,
        transcript_id: uuid.UUID,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        """
        Background task: extracts Q&A exchanges, performs conceptual alignment,
        generates coaching tips, maps to job criteria, and records audit trail.
        """
        factory = session_factory or get_session_factory()
        async with factory() as session:
            stmt = (
                select(InterviewTranscript)
                .where(InterviewTranscript.id == transcript_id)
                .options(selectinload(InterviewTranscript.application).selectinload(Application.job).selectinload(Job.criteria))
            )
            res = await session.execute(stmt)
            transcript = res.scalar_one_or_none()

            if not transcript:
                logger.error("Interview transcript %s not found for analysis", transcript_id)
                return

            if transcript.processing_status == DocumentProcessingStatus.COMPLETED:
                return

            transcript.processing_status = DocumentProcessingStatus.PROCESSING
            await session.commit()

        # Extract criteria names for mapping
        job_criteria_names: list[str] = []
        criterion_lookup: dict[str, uuid.UUID] = {}
        if transcript.application and transcript.application.job:
            for c in transcript.application.job.criteria:
                job_criteria_names.append(c.name)
                criterion_lookup[c.name.strip().lower()] = c.id

        # Run extraction
        parsed_qa_list: list[dict[str, Any]] = []
        try:
            parsed_qa_list = await self._run_llm_qa_extraction(
                transcript_text=transcript.raw_text,
                job_criteria_names=job_criteria_names,
            )
        except Exception as exc:
            logger.error("LLM transcript extraction failed for %s: %s", transcript_id, exc)
            async with factory() as session:
                stmt = select(InterviewTranscript).where(InterviewTranscript.id == transcript_id)
                t = (await session.execute(stmt)).scalar_one_or_none()
                if t:
                    t.processing_status = DocumentProcessingStatus.FAILED
                    t.processing_error = {"message": str(exc), "code": "ANALYSIS_ERROR"}
                    await session.commit()
            return

        # Persist extracted Q&A items
        async with factory() as session:
            stmt = select(InterviewTranscript).where(InterviewTranscript.id == transcript_id)
            t = (await session.execute(stmt)).scalar_one_or_none()
            if not t:
                return

            for idx, item in enumerate(parsed_qa_list, start=1):
                interviewer_q = item.get("interviewer_question", "").strip()
                candidate_ans = item.get("candidate_answer_excerpt", "").strip()
                if not interviewer_q or not candidate_ans:
                    continue

                # Anti-hallucination check: ensure answer excerpt exists in transcript
                is_grounded = validate_transcript_quote_grounding(t.raw_text, candidate_ans)
                raw_status = str(item.get("evidence_status", "supported")).lower()
                if not is_grounded:
                    status_enum = EvidenceStatus.AMBIGUOUS
                    alignment = f"Ungrounded excerpt: '{candidate_ans[:50]}...' could not be matched verbatim in dialogue."
                elif raw_status == "supported":
                    status_enum = EvidenceStatus.SUPPORTED
                    alignment = item.get("alignment_summary", "Demonstrated required conceptual depth.")
                elif raw_status == "partially_supported":
                    status_enum = EvidenceStatus.PARTIALLY_SUPPORTED
                    alignment = item.get("alignment_summary", "Partially covered foundational concepts.")
                else:
                    status_enum = EvidenceStatus.AMBIGUOUS
                    alignment = item.get("alignment_summary", "Answer was unclear or tangential.")

                # Estimate line numbers in transcript
                start_l, end_l = estimate_line_numbers(t.raw_text, candidate_ans)

                # Map criterion
                mapped_skill = item.get("mapped_skill_name")
                mapped_crit_id = None
                if mapped_skill:
                    mapped_crit_id = criterion_lookup.get(mapped_skill.strip().lower())

                qa_record = TranscriptQAItem(
                    transcript_id=transcript_id,
                    question_index=idx,
                    interviewer_question=interviewer_q,
                    candidate_answer_excerpt=candidate_ans,
                    start_line=start_l,
                    end_line=end_l,
                    mapped_criterion_id=mapped_crit_id,
                    mapped_skill_name=mapped_skill,
                    evidence_status=status_enum,
                    expected_concept=item.get("expected_concept", "Standard engineering principles."),
                    alignment_summary=alignment,
                    coaching_suggestion=item.get(
                        "coaching_suggestion",
                        "Review production architecture patterns to strengthen conceptual depth.",
                    ),
                )
                session.add(qa_record)

            t.processing_status = DocumentProcessingStatus.COMPLETED
            t.processing_error = None
            await session.flush()

            # Audit event
            audit_repo = AuditEventRepository(session)
            await audit_repo.log_event(
                action="TRANSCRIPT_ANALYZED",
                resource_type="interview_transcript",
                resource_id=str(transcript_id),
                actor_id=str(t.uploader_id) if t.uploader_id else "system",
                actor_role="system",
                entity_version=2,
                prior_state={"processing_status": DocumentProcessingStatus.PROCESSING.value},
                new_state={
                    "processing_status": DocumentProcessingStatus.COMPLETED.value,
                    "qa_items_count": len(parsed_qa_list),
                },
                details={"qa_items_count": len(parsed_qa_list)},
            )
            await session.commit()
            logger.info("Successfully analyzed interview transcript %s with %d Q&A items", transcript_id, len(parsed_qa_list))

    async def _run_llm_qa_extraction(
        self,
        transcript_text: str,
        job_criteria_names: list[str],
    ) -> list[dict[str, Any]]:
        """Invokes LLM with strict JSON schema to segment questions and extract coaching advice."""
        llm = get_llm_provider()

        # If fake provider, synthesize realistic deterministic Q&A items based on text
        if self.settings.LLM_PROVIDER == "fake" or getattr(llm, "api_key", "") == "placeholder_api_key":
            return self._generate_simulated_qa_items(transcript_text, job_criteria_names)

        import httpx

        base_url = self.settings.LLM_BASE_URL.rstrip('/')
        model = self.settings.LLM_MODEL
        if self.settings.LLM_PROVIDER == "gemini":
            if not base_url or "api.openai.com" in base_url:
                base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
            if not model or model == "gpt-4o-mini":
                model = "gemini-2.5-flash"

        prompt = build_interview_analysis_prompt(transcript_text, job_criteria_names)
        headers = {
            "Authorization": f"Bearer {self.settings.LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": INTERVIEW_ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            raw_content = data["choices"][0]["message"]["content"]
            parsed = json.loads(raw_content)
            return parsed.get("qa_items", [])

    def _generate_simulated_qa_items(
        self,
        transcript_text: str,
        job_criteria_names: list[str],
    ) -> list[dict[str, Any]]:
        """Generates realistic deterministic Q&A items from dialogue lines for testing and fake provider."""
        lines = [line.strip() for line in transcript_text.splitlines() if line.strip()]
        qa_items: list[dict[str, Any]] = []

        current_q: str | None = None
        current_ans_parts: list[str] = []

        for line in lines:
            if line.lower().startswith(("interviewer:", "q:", "hr:", "question:", "lead:")):
                if current_q and current_ans_parts:
                    ans_text = " ".join(current_ans_parts)
                    mapped_crit = job_criteria_names[len(qa_items) % len(job_criteria_names)] if job_criteria_names else "Core Engineering"
                    qa_items.append(
                        {
                            "question_index": len(qa_items) + 1,
                            "interviewer_question": current_q,
                            "candidate_answer_excerpt": ans_text,
                            "mapped_skill_name": mapped_crit,
                            "evidence_status": "supported" if len(ans_text) > 40 else "partially_supported",
                            "expected_concept": f"Demonstrated practical understanding of {mapped_crit}, architectural patterns, and production trade-offs.",
                            "alignment_summary": f"Candidate directly addressed technical concepts relevant to {mapped_crit}.",
                            "coaching_suggestion": f"To strengthen future technical discussions in {mapped_crit}, mention quantitative benchmarks and monitoring considerations.",
                        }
                    )
                    current_ans_parts = []
                current_q = line.split(":", 1)[1].strip() if ":" in line else line
            elif line.lower().startswith(("candidate:", "a:", "answer:")):
                ans_text = line.split(":", 1)[1].strip() if ":" in line else line
                current_ans_parts.append(ans_text)
            elif current_q and not current_ans_parts:
                # Continuation or candidate speaking
                current_ans_parts.append(line)

        # Flush last item
        if current_q and current_ans_parts:
            ans_text = " ".join(current_ans_parts)
            mapped_crit = job_criteria_names[len(qa_items) % len(job_criteria_names)] if job_criteria_names else "Core Engineering"
            qa_items.append(
                {
                    "question_index": len(qa_items) + 1,
                    "interviewer_question": current_q,
                    "candidate_answer_excerpt": ans_text,
                    "mapped_skill_name": mapped_crit,
                    "evidence_status": "supported" if len(ans_text) > 40 else "partially_supported",
                    "expected_concept": f"Demonstrated practical understanding of {mapped_crit}.",
                    "alignment_summary": f"Candidate directly addressed {mapped_crit}.",
                    "coaching_suggestion": f"Incorporate production scalability trade-offs when discussing {mapped_crit}.",
                }
            )

        # Fallback if transcript lacked Interviewer/Candidate labels
        if not qa_items and len(lines) >= 2:
            mapped_crit = job_criteria_names[0] if job_criteria_names else "System Architecture"
            qa_items.append(
                {
                    "question_index": 1,
                    "interviewer_question": lines[0],
                    "candidate_answer_excerpt": lines[1],
                    "mapped_skill_name": mapped_crit,
                    "evidence_status": "supported",
                    "expected_concept": "Foundational technical problem solving and software architecture.",
                    "alignment_summary": "Candidate provided concrete examples of technical implementation.",
                    "coaching_suggestion": "Highlight system observability and error handling in similar technical questions.",
                }
            )

        return qa_items

    async def submit_qa_clarification(
        self,
        qa_item_id: uuid.UUID,
        candidate_id: uuid.UUID,
        clarification_text: str,
        session: AsyncSession,
    ) -> TranscriptQAItem:
        """
        Allows candidate to submit clarification regarding an interview response
        if context was omitted or abbreviated in transcript notes.
        """
        stmt = (
            select(TranscriptQAItem)
            .where(TranscriptQAItem.id == qa_item_id)
            .options(selectinload(TranscriptQAItem.transcript).selectinload(InterviewTranscript.application))
        )
        res = await session.execute(stmt)
        qa = res.scalar_one_or_none()

        if not qa:
            raise NotFoundError(f"Transcript Q&A item {qa_item_id} not found")

        # Verify candidate ownership
        if str(qa.transcript.application.candidate_id) != str(candidate_id):
            raise AuthorizationError("You are not authorized to submit clarification for this transcript.")

        qa.clarification_requested = True
        qa.candidate_clarification_text = clarification_text.strip()

        # Audit event
        audit_repo = AuditEventRepository(session)
        await audit_repo.log_event(
            action="TRANSCRIPT_QA_CLARIFIED",
            resource_type="transcript_qa_item",
            resource_id=str(qa_item_id),
            actor_id=str(candidate_id),
            actor_role="candidate",
            entity_version=2,
            prior_state={"clarification_requested": False},
            new_state={
                "clarification_requested": True,
                "clarification_text": qa.candidate_clarification_text,
            },
            details={"clarification_length": len(qa.candidate_clarification_text)},
        )

        await session.commit()
        return qa

    async def get_transcripts_by_application(
        self,
        application_id: uuid.UUID,
        session: AsyncSession,
    ) -> list[InterviewTranscript]:
        """Fetches all transcripts and Q&A items for an application."""
        stmt = (
            select(InterviewTranscript)
            .where(InterviewTranscript.application_id == application_id)
            .options(selectinload(InterviewTranscript.qa_items))
            .order_by(InterviewTranscript.created_at.desc())
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())
