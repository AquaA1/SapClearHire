"""
Backward-compatibility adapter for app.services.storage.
Exports BaseStorageService, LocalStorageService, S3CompatibleStorageService, and get_storage_service.
"""

from app.services.storage.base import BaseStorageService
from app.services.storage.local import LocalStorageService
from app.services.storage.s3 import S3CompatibleStorageService
from app.services.storage import get_storage_service

__all__ = [
    "BaseStorageService",
    "LocalStorageService",
    "S3CompatibleStorageService",
    "get_storage_service",
]
