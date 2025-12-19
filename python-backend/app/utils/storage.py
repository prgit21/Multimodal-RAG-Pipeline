"""Storage helpers for uploaded files.

The default client persists uploads to Amazon S3 when a bucket name is
configured via settings. If no S3 bucket is configured, the system falls back
to local file-system storage to preserve backwards compatibility.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from app.core.config import Settings, get_settings

if TYPE_CHECKING:  # pragma: no cover - used for type checking only
    import boto3  # type: ignore
    from botocore.client import Config  # type: ignore
    from botocore.exceptions import ClientError, NoCredentialsError  # type: ignore


def _load_s3_dependencies():
    """Lazily import boto3 and botocore when S3 storage is requested."""

    if importlib.util.find_spec("boto3") is None:
        raise RuntimeError(
            "boto3 is required for S3 storage. Install it or unset S3_BUCKET to use local storage."
        )

    boto3 = importlib.import_module("boto3")
    botocore_client = importlib.import_module("botocore.client")
    botocore_exceptions = importlib.import_module("botocore.exceptions")
    return (
        boto3,
        botocore_client.Config,
        botocore_exceptions.ClientError,
        botocore_exceptions.NoCredentialsError,
    )


class LocalStorageClient:
    """File-system backed storage client used for uploaded assets."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._upload_dir = Path(self._settings.upload_dir)

    def ensure_bucket(self) -> None:
        """Ensure the upload directory exists."""

        self._upload_dir.mkdir(parents=True, exist_ok=True)

    def upload_file(
        self, object_name: str, data: bytes, content_type: Optional[str]
    ) -> str:
        self.ensure_bucket()
        target_path = self._upload_dir / object_name
        target_path.write_bytes(data)
        return self.object_url(object_name)

    def object_url(self, object_name: str) -> str:
        return f"/uploads/{object_name}"


class S3StorageClient:
    """S3-backed storage client used for uploaded assets."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        if not self._settings.s3_bucket:
            raise RuntimeError("S3_BUCKET must be configured for S3 storage")

        boto3, Config, self._client_error, self._no_credentials_error = _load_s3_dependencies()
        self._s3 = boto3.client(
            "s3",
            region_name=self._settings.s3_region,
            endpoint_url=self._settings.s3_endpoint_url,
            config=Config(s3={"addressing_style": "path" if self._settings.s3_use_path_style else "virtual"}),
        )

    def ensure_bucket(self) -> None:
        """Ensure the S3 bucket exists before uploading."""

        try:
            self._s3.head_bucket(Bucket=self._settings.s3_bucket)
        except self._no_credentials_error:
            logging.getLogger(__name__).warning(
                "S3_BUCKET is set to %s but no AWS credentials were found. "
                "Configure AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY (or an IAM role) "
                "to enable S3 uploads.",
                self._settings.s3_bucket,
            )
        except self._client_error as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code in {"404", "NoSuchBucket"}:
                self._create_bucket()
            else:  # pragma: no cover - defensive guard for AWS errors
                logging.getLogger(__name__).warning(
                    "Could not verify S3 bucket %s: %s", self._settings.s3_bucket, exc
                )
        except Exception as exc:  # pragma: no cover - defensive guard for AWS errors
            logging.getLogger(__name__).warning(
                "Could not verify S3 bucket %s: %s", self._settings.s3_bucket, exc
            )

    def _create_bucket(self) -> None:
        params = {"Bucket": self._settings.s3_bucket}
        if self._settings.s3_region:
            params["CreateBucketConfiguration"] = {
                "LocationConstraint": self._settings.s3_region
            }
        self._s3.create_bucket(**params)

    def upload_file(
        self, object_name: str, data: bytes, content_type: Optional[str]
    ) -> str:
        self.ensure_bucket()
        extra_args = {"ACL": "public-read"}
        if content_type:
            extra_args["ContentType"] = content_type

        self._s3.put_object(
            Bucket=self._settings.s3_bucket,
            Key=object_name,
            Body=data,
            **extra_args,
        )
        return self.object_url(object_name)

    def object_url(self, object_name: str) -> str:
        endpoint = self._settings.s3_endpoint_url
        bucket = self._settings.s3_bucket
        if endpoint:
            base = endpoint.rstrip("/")
            if self._settings.s3_use_path_style:
                return f"{base}/{bucket}/{object_name}"
            return f"https://{bucket}.{base.split('://')[-1]}/{object_name}"

        region = self._settings.s3_region or "us-east-1"
        return f"https://{bucket}.s3.{region}.amazonaws.com/{object_name}"


@lru_cache
def get_storage_client():
    settings = get_settings()
    if settings.s3_bucket:
        return S3StorageClient(settings)
    return LocalStorageClient(settings)


__all__ = ["LocalStorageClient", "S3StorageClient", "get_storage_client"]
