import hashlib
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import logger
from app.services.storage.base import BaseStorageService


class LocalStorageService(BaseStorageService):
    """
    Secure local file storage service for development and testing.
    Prevents path traversal and filename collisions by generating deterministic,
    safe storage filenames keyed by document UUID.
    """

    def __init__(self, base_dir: str | Path | None = None):
        settings = get_settings()
        self.base_dir = Path(base_dir or settings.STORAGE_LOCAL_DIR).resolve()
        self.documents_dir = self.base_dir / "documents"
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensures the destination directory exists."""
        self.documents_dir.mkdir(parents=True, exist_ok=True)

    def get_file_path(self, document_id: uuid.UUID) -> Path:
        """Returns the absolute path to a stored document by its UUID."""
        # Check if direct extension exists or fallback to .pdf
        direct = self.documents_dir / f"{document_id}.pdf"
        if direct.exists():
            return direct
        for candidate in self.documents_dir.glob(f"{document_id}.*"):
            return candidate
        return direct

    def save_file(
        self,
        file_content: bytes,
        original_filename: str,
        document_id: uuid.UUID,
    ) -> tuple[str, str, int]:
        """
        Saves uploaded file content to disk.
        Returns:
            tuple of (absolute_file_path_str, sha256_checksum, file_size_bytes)
        """
        self._ensure_directories()
        suffix = Path(original_filename).suffix.lower()
        if not suffix:
            suffix = ".pdf"
        target_path = self.documents_dir / f"{document_id}{suffix}"

        # Compute SHA-256 checksum
        hasher = hashlib.sha256()
        hasher.update(file_content)
        file_hash = hasher.hexdigest()
        file_size = len(file_content)

        # Write file
        target_path.write_bytes(file_content)
        logger.info(
            "Saved document %s (original: %s, %d bytes) to %s",
            document_id,
            original_filename,
            file_size,
            target_path,
        )

        return str(target_path), file_hash, file_size

    def get_file_bytes(self, document_id: uuid.UUID, file_path: str | None = None) -> bytes:
        """Reads file bytes from disk."""
        path = Path(file_path) if file_path else self.get_file_path(document_id)
        if not path.exists():
            raise FileNotFoundError(f"Stored file for document {document_id} not found at {path}")
        return path.read_bytes()

    def delete_file(self, file_path_or_id: str | Path | uuid.UUID) -> None:
        """Removes a file from disk if present."""
        if isinstance(file_path_or_id, uuid.UUID):
            path = self.get_file_path(file_path_or_id)
        else:
            path = Path(file_path_or_id)
        try:
            if path.exists() and path.is_file():
                path.unlink()
                logger.info("Deleted document file at %s", path)
        except Exception as exc:
            logger.warning("Failed to delete file %s: %s", path, str(exc))
