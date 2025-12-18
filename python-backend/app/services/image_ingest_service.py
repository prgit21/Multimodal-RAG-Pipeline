"""Service responsible for the image ingestion pipeline."""

from __future__ import annotations

import uuid
from functools import lru_cache
from io import BytesIO
from typing import Optional

from PIL import Image
from sqlalchemy.orm import Session

from app.models.images import ImageMetadata
from app.repositories.images_repo import ImageRepository
from app.services.embedding_service import (
    EmbeddingService,
    get_embedding_service,
)
from app.services.ocr_service import OCRService, get_ocr_service
from app.utils.hashing import sha256_hash
from app.utils.storage import LocalStorageClient, get_storage_client


class ImageIngestService:
    def __init__(
        self,
        storage_client: LocalStorageClient,
        embedding_service: EmbeddingService,
        ocr_service: OCRService,
    ) -> None:
        self._storage_client = storage_client
        self._embedding_service = embedding_service
        self._ocr_service = ocr_service

    def ingest(
        self,
        *,
        db: Session,
        data: bytes,
        filename: str,
        content_type: Optional[str],
    ) -> ImageMetadata:
        object_name = f"{uuid.uuid4()}_{filename}"
        url = self._storage_client.upload_file(object_name, data, content_type)

        image = Image.open(BytesIO(data)).convert("RGB")
        width, height = image.size
        hash_value = sha256_hash(data)

        embedding_vector = self._embedding_service.encode_image(image)
        text = self._ocr_service.extract_text(image)
        text_embedding = (
            self._embedding_service.encode_text(text) if text else None
        )

        repository = ImageRepository(db)
        metadata = repository.create(
            url=url,
            hash_value=hash_value,
            width=width,
            height=height,
            embedding=embedding_vector,
            text=text,
            text_embedding=text_embedding,
        )
        return metadata


@lru_cache
def get_image_ingest_service() -> ImageIngestService:
    return ImageIngestService(
        storage_client=get_storage_client(),
        embedding_service=get_embedding_service(),
        ocr_service=get_ocr_service(),
    )


__all__ = ["ImageIngestService", "get_image_ingest_service"]
