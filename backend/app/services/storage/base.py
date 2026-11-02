import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncGenerator


class BaseStorageService(ABC):
    """
    Abstract interface for document file storage.
    Enables zero-code switching between local filesystem storage and
    cloud object storage (SAP BTP Object Store, AWS S3, MinIO, Azure Blob).
    """

    @abstractmethod
    def get_file_path(self, document_id: uuid.UUID) -> Path:
        """
        Returns local Path if available, or temporary cached file path.
        """
        pass

    @abstractmethod
    def save_file(
        self,
        file_content: bytes,
        original_filename: str,
        document_id: uuid.UUID,
    ) -> tuple[str, str, int]:
        """
        Persists document file bytes to storage.
        Returns:
            tuple of (storage_location_or_path, sha256_checksum, file_size_bytes)
        """
        pass

    @abstractmethod
    def get_file_bytes(self, document_id: uuid.UUID, file_path: str | None = None) -> bytes:
        """
        Retrieves raw document bytes from storage.
        """
        pass

    @abstractmethod
    def delete_file(self, file_path_or_id: str | Path | uuid.UUID) -> None:
        """
        Deletes stored file from storage.
        """
        pass
