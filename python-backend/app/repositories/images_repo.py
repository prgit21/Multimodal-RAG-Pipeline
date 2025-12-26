"""Database access helpers for image and embedding records."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.embeddings import Embedding
from app.models.images import ImageMetadata


class ImageRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        url: str,
        hash_value: str,
        width: int,
        height: int,
        embedding: List[float],
        text: Optional[str] = None,
        text_embedding: Optional[List[float]] = None,
    ) -> ImageMetadata:
        metadata = ImageMetadata(
            url=url,
            hash=hash_value,
            width=width,
            height=height,
            embedding=embedding,
            text=text,
            text_embedding=text_embedding,
        )
        self._session.add(metadata)
        self._session.commit()
        self._session.refresh(metadata)
        return metadata

    def search_by_embedding_vector(
        self, vector: List[float], limit: int = 3
    ) -> List[tuple[ImageMetadata, float]]:
        """Return image rows ordered by visual embedding distance."""

        if not vector:
            return []

        distance = ImageMetadata.embedding.cosine_distance(vector)
        query = (
            self._session.query(ImageMetadata, distance.label("distance"))
            .order_by(distance)
        )
        if limit is not None:
            query = query.limit(limit)
        return [
            (record, float(dist))
            for record, dist in query.all()
        ]

    def search_by_text_embedding_vector(
        self, vector: List[float], limit: int = 3
    ) -> List[tuple[ImageMetadata, float]]:
        """Return image rows ordered by OCR/text embedding distance."""

        if not vector:
            return []

        distance = ImageMetadata.text_embedding.cosine_distance(vector)
        query = (
            self._session.query(ImageMetadata, distance.label("distance"))
            .filter(ImageMetadata.text_embedding.isnot(None))
            .order_by(distance)
        )
        if limit is not None:
            query = query.limit(limit)
        return [
            (record, float(dist))
            for record, dist in query.all()
        ]

    def list_missing_text_embeddings(
        self, limit: Optional[int] = None
    ) -> List[ImageMetadata]:
        query = (
            self._session.query(ImageMetadata)
            .filter(ImageMetadata.text.isnot(None))
            .filter(ImageMetadata.text != "")
            .filter(ImageMetadata.text_embedding.is_(None))
        )
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    def set_text_embedding(
        self, metadata: ImageMetadata, embedding: List[float]
    ) -> None:
        metadata.text_embedding = embedding
        self._session.add(metadata)

    def commit(self) -> None:
        self._session.commit()


class EmbeddingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, embedding: List[float], content: Optional[str] = None) -> Embedding:
        record = Embedding(embedding=embedding, content=content)
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record

    def search_by_vector(self, vector: List[float]) -> List[Embedding]:
        return (
            self._session.query(Embedding)
            .order_by(Embedding.embedding.cosine_distance(vector))
            .all()
        )


__all__ = ["ImageRepository", "EmbeddingRepository"]
