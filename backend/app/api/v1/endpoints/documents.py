import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.security import CurrentUser, UserRole, get_current_user
from app.db.models.user import User
from app.db.session import get_db_session
from app.repositories.domain import DocumentRepository, UserRepository
from app.schemas.document import DocumentStatusResponse, DocumentUploadResponse
from app.services.document import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload Candidate Resume",
    description=(
        "Uploads a PDF resume, validates format and size, stores it securely, "
        "and enqueues background text extraction without blocking."
    ),
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF resume file to upload"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DocumentUploadResponse:
    candidate_id = uuid.UUID(current_user.id)

    # Ensure user record exists for database foreign key integrity
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(candidate_id)
    if not user:
        user = User(
            id=candidate_id,
            email=current_user.email,
            full_name=current_user.email.split("@")[0],
            role=current_user.role,
            employer_id=current_user.employer_id,
        )
        db.add(user)
        await db.flush()

    service = DocumentService()
    doc = await service.create_and_store_document(
        file=file,
        candidate_id=candidate_id,
        session=db,
    )

    # Schedule background extraction task
    background_tasks.add_task(
        service.process_document_extraction,
        doc.id,
    )

    return DocumentUploadResponse.model_validate(doc)


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    summary="Poll Document Extraction Status",
    description="Retrieves the processing status, page count, and extracted text per page.",
)
async def get_document_status(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DocumentStatusResponse:
    repo = DocumentRepository(db)
    doc = await repo.get_by_id(document_id)

    if not doc:
        raise NotFoundError(f"Document {document_id} was not found")

    # Candidates are strictly restricted to their own documents
    if current_user.role == UserRole.CANDIDATE and doc.candidate_id != uuid.UUID(current_user.id):
        raise AuthorizationError("You are not authorized to view this document")

    return DocumentStatusResponse.model_validate(doc)
