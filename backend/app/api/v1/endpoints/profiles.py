import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError
from app.core.security import CurrentUser, UserRole, get_current_user
from app.db.session import get_db_session
from app.repositories.domain import ExtractionRepository
from app.schemas.evaluation import CandidateProfileSkillsResponse, ProfileSkillItem

router = APIRouter(prefix="/profiles", tags=["Candidate Profiles"])


@router.get(
    "/{id}/skills",
    response_model=CandidateProfileSkillsResponse,
    summary="Get Candidate Profile Skill Inventory",
    description="Retrieves the verified skill inventory extracted from candidate resumes.",
)
async def get_candidate_skills(
    id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CandidateProfileSkillsResponse:
    if current_user.role == UserRole.CANDIDATE and current_user.id != str(id):
        raise AuthorizationError("Candidates may only access their own profile skill inventory.")

    extraction_repo = ExtractionRepository(db)
    raw_skills = await extraction_repo.get_skills_for_candidate(id)

    # Deduplicate skills by normalized name, keeping highest confidence
    seen_skills: dict[str, ProfileSkillItem] = {}
    for s in raw_skills:
        norm_name = s.skill_name.strip().lower()
        item = ProfileSkillItem(
            id=s.id,
            skill_name=s.skill_name,
            category=s.category,
            confidence=s.confidence,
            source_page=s.source_page,
            source_excerpt=s.source_excerpt,
        )
        if norm_name not in seen_skills or item.confidence > seen_skills[norm_name].confidence:
            seen_skills[norm_name] = item

    unique_skills = list(seen_skills.values())

    return CandidateProfileSkillsResponse(
        candidate_id=id,
        total_skills=len(unique_skills),
        skills=unique_skills,
    )
