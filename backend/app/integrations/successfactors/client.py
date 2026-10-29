from typing import Any

from app.core.logging import logger


class SuccessFactorsClient:
    """
    Client interface for SAP SuccessFactors Recruiting OData API.
    Provides integration hooks for synchronizing Job Requisitions and Applications.
    """

    def __init__(self, api_endpoint: str | None = None, api_key: str | None = None):
        self.api_endpoint = api_endpoint or "https://api.successfactors.eu/odata/v2"
        self.api_key = api_key

    async def get_job_requisition(self, requisition_id: str) -> dict[str, Any]:
        """Fetch job requisition details and criteria from SAP SuccessFactors."""
        logger.info("Stub: fetching SAP SuccessFactors job requisition: %s", requisition_id)
        # Interface stub for Phase 2 integration
        return {
            "id": requisition_id,
            "title": "Senior Cloud Developer",
            "department": "SAP Business Technology Platform",
            "criteria": ["Python", "PostgreSQL", "Cloud Native", "FastAPI"],
        }
