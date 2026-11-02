import hashlib
import tempfile
import uuid
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.logging import logger
from app.services.storage.base import BaseStorageService


class S3CompatibleStorageService(BaseStorageService):
    """
    S3-compatible object storage service for AWS S3, MinIO, and SAP BTP Object Store.
    Supports credentials from settings or auto-detected SAP BTP VCAP_SERVICES['objectstore'].
    """

    def __init__(
        self,
        bucket_name: str | None = None,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        region_name: str = "us-east-1",
    ):
        settings = get_settings()

        # Check SAP BTP credentials first
        from app.core.sap import get_sap_objectstore_credentials

        sap_creds = get_sap_objectstore_credentials() or {}

        self.bucket_name = (
            bucket_name
            or sap_creds.get("bucket")
            or settings.S3_BUCKET_NAME
        )
        self.endpoint_url = (
            endpoint_url
            or sap_creds.get("endpoint_url")
            or settings.S3_ENDPOINT_URL
        )
        self.access_key = (
            access_key
            or sap_creds.get("access_key")
            or settings.S3_ACCESS_KEY
        )
        self.secret_key = (
            secret_key
            or sap_creds.get("secret_key")
            or settings.S3_SECRET_KEY
        )
        self.region_name = (
            sap_creds.get("region")
            or region_name
            or settings.S3_REGION_NAME
        )
        self._temp_cache_dir = Path(tempfile.gettempdir()) / "clearhire_storage_cache"
        self._temp_cache_dir.mkdir(parents=True, exist_ok=True)
        self._client: Any = None

    def _get_boto3_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import boto3
            from botocore.config import Config

            cfg = Config(signature_version="s3v4", s3={"addressing_style": "virtual"})
            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region_name,
                config=cfg,
            )
            return self._client
        except ImportError:
            raise RuntimeError(
                "boto3 package is required for S3/SAP Object Store support. "
                "Install it via `pip install boto3` or use local storage."
            )

    def _get_object_key(self, document_id: uuid.UUID, original_filename: str | None = None) -> str:
        ext = Path(original_filename).suffix.lower() if original_filename else ".pdf"
        if not ext:
            ext = ".pdf"
        return f"resumes/{document_id}{ext}"

    def get_file_path(self, document_id: uuid.UUID) -> Path:
        """Returns local cached path, downloading from S3 if necessary."""
        cached = self._temp_cache_dir / f"{document_id}.pdf"
        if cached.exists():
            return cached
        # Attempt download from S3
        content = self.get_file_bytes(document_id)
        cached.write_bytes(content)
        return cached

    def save_file(
        self,
        file_content: bytes,
        original_filename: str,
        document_id: uuid.UUID,
    ) -> tuple[str, str, int]:
        """Saves file to S3 bucket."""
        hasher = hashlib.sha256()
        hasher.update(file_content)
        file_hash = hasher.hexdigest()
        file_size = len(file_content)

        key = self._get_object_key(document_id, original_filename)
        client = self._get_boto3_client()
        client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=file_content,
            Metadata={"sha256": file_hash, "original_filename": original_filename},
        )
        logger.info("Uploaded document %s to s3://%s/%s", document_id, self.bucket_name, key)

        # Cache locally
        cached_path = self._temp_cache_dir / f"{document_id}.pdf"
        cached_path.write_bytes(file_content)

        return f"s3://{self.bucket_name}/{key}", file_hash, file_size

    def get_file_bytes(self, document_id: uuid.UUID, file_path: str | None = None) -> bytes:
        """Fetches file bytes from S3."""
        key = file_path.replace(f"s3://{self.bucket_name}/", "") if file_path and file_path.startswith("s3://") else self._get_object_key(document_id)
        client = self._get_boto3_client()
        response = client.get_object(Bucket=self.bucket_name, Key=key)
        return response["Body"].read()

    def delete_file(self, file_path_or_id: str | Path | uuid.UUID) -> None:
        """Deletes object from S3."""
        if isinstance(file_path_or_id, uuid.UUID):
            key = self._get_object_key(file_path_or_id)
        elif str(file_path_or_id).startswith("s3://"):
            key = str(file_path_or_id).replace(f"s3://{self.bucket_name}/", "")
        else:
            key = str(file_path_or_id)

        try:
            client = self._get_boto3_client()
            client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info("Deleted S3 object s3://%s/%s", self.bucket_name, key)
        except Exception as exc:
            logger.warning("Failed to delete S3 object: %s", exc)
