from app.core.config import get_settings
from app.services.storage.base import BaseStorageService
from app.services.storage.local import LocalStorageService
from app.services.storage.s3 import S3CompatibleStorageService

_storage_instance: BaseStorageService | None = None


def get_storage_service() -> BaseStorageService:
    """
    Factory creating storage service singleton based on configuration.
    Auto-detects SAP BTP Object Store via VCAP_SERVICES or STORAGE_BACKEND setting.
    """
    global _storage_instance
    if _storage_instance is not None:
        return _storage_instance

    settings = get_settings()

    # Check if SAP BTP Object Store is bound or S3 backend is explicitly chosen
    from app.core.sap import get_sap_objectstore_credentials

    sap_creds = get_sap_objectstore_credentials()
    if sap_creds or settings.STORAGE_BACKEND == "s3":
        _storage_instance = S3CompatibleStorageService()
    else:
        _storage_instance = LocalStorageService()

    return _storage_instance


__all__ = [
    "BaseStorageService",
    "LocalStorageService",
    "S3CompatibleStorageService",
    "get_storage_service",
]
