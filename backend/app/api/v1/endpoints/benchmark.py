from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, UserRole, get_current_user, require_roles
from app.db.session import get_db_session
from app.integrations.successfactors.adapter import SuccessFactorsImportAdapter
from app.integrations.successfactors.fixtures import get_synthetic_applicant_feed
from app.integrations.successfactors.schemas import SFApplicantFeedBatch, SFImportResult
from app.services.benchmark.runner import BenchmarkRunner
from app.services.benchmark.schemas import BenchmarkReport

router = APIRouter(tags=["SuccessFactors Simulation & Benchmark"])


@router.get(
    "/integrations/successfactors/feed",
    response_model=SFApplicantFeedBatch,
    summary="Get Simulated SuccessFactors Applicant Feed",
    description=(
        "Returns a synthetic, simulated SAP SuccessFactors-style applicant feed batch. "
        "Explicitly labelled as simulated; does NOT connect to a real SAP SuccessFactors instance."
    ),
)
async def get_mock_successfactors_feed(
    current_user: CurrentUser = Depends(get_current_user),
) -> SFApplicantFeedBatch:
    """Returns synthetic SuccessFactors applicant feed for testing and benchmark workflows."""
    return get_synthetic_applicant_feed()


@router.post(
    "/integrations/successfactors/import",
    response_model=SFImportResult,
    summary="Import Simulated SuccessFactors Applicant Feed",
    description=(
        "Imports authorized applicant records from the simulated SuccessFactors feed into "
        "ClearHire's Job, JobCriterion, User, Document, and Application domain models. "
        "Restricted to Employer Administrators and System Auditors."
    ),
)
async def import_successfactors_feed(
    feed: SFApplicantFeedBatch | None = None,
    current_user: CurrentUser = Depends(
        require_roles(UserRole.EMPLOYER_ADMIN, UserRole.SYSTEM_AUDITOR)
    ),
    db: AsyncSession = Depends(get_db_session),
) -> SFImportResult:
    """Imports the provided or default synthetic feed into ClearHire."""
    batch_feed = feed or get_synthetic_applicant_feed()
    adapter = SuccessFactorsImportAdapter(db)
    result = await adapter.import_feed(batch_feed, current_user)
    await db.commit()
    return result


@router.get(
    "/benchmark/run",
    response_model=BenchmarkReport,
    summary="Run Before/After Keyword Screening Benchmark",
    description=(
        "Executes a reproducible before/after benchmark comparing a traditional literal-keyword "
        "screening baseline against ClearHire's evidence-matching pipeline on a labelled ground-truth dataset. "
        "Reports sample size, per-criterion comparisons, baseline failure modes, and metrics."
    ),
)
@router.post(
    "/benchmark/run",
    response_model=BenchmarkReport,
    include_in_schema=False,
)
async def run_screening_benchmark(
    current_user: CurrentUser = Depends(get_current_user),
) -> BenchmarkReport:
    """Runs the benchmark comparison and returns metrics and qualitative findings."""
    runner = BenchmarkRunner()
    return runner.run_benchmark()
