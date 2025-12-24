"""FastAPI application setup and router composition."""

from __future__ import annotations

import logging
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text as sa_text
from sqlalchemy.exc import NoSuchTableError

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.repositories.users_repo import UserRepository
from app.routers import auth, images, search
from app.utils.hashing import hash_password
from app.utils.storage import get_storage_client


logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI()
    storage_client = get_storage_client()

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    storage_client.ensure_bucket()
    application.mount(
        "/uploads",
        StaticFiles(directory=settings.upload_dir),
        name="uploads",
    )

    include_routers(application)

    @application.on_event("startup")
    def on_startup() -> None:
        init_database()
        init_default_user()
        storage_client.ensure_bucket()

    @application.get("/api/hello")
    async def read_hello() -> dict[str, str]:
        return {"message": "Hello from FastAPI"}

    return application


def include_routers(application: FastAPI) -> None:
    application.include_router(auth.router)
    application.include_router(images.router)
    application.include_router(search.router)


_hnsw_index_creation_scheduled = threading.Event()


def init_database() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        inspector = inspect(connection)
        table_exists = True
        try:
            columns = {column["name"] for column in inspector.get_columns("images")}
        except NoSuchTableError:
            table_exists = False
            columns = set()
        if table_exists and "text" not in columns:
            connection.execute(sa_text("ALTER TABLE images ADD COLUMN text TEXT"))
        if table_exists and "text_embedding" not in columns:
            connection.execute(
                sa_text("ALTER TABLE images ADD COLUMN text_embedding vector(512)")
            )

        try:
            embedding_columns = inspector.get_columns("embeddings")
        except NoSuchTableError:
            embedding_columns = []
        embedding_dimension = next(
            (
                getattr(column["type"], "dim", None)
                or getattr(column["type"], "dimension", None)
                for column in embedding_columns
                if column["name"] == "embedding"
            ),
            None,
        )
        if embedding_dimension is not None and embedding_dimension != 512:
            connection.execute(
                sa_text("DROP INDEX IF EXISTS embeddings_embedding_hnsw_idx")
            )
            connection.execute(
                sa_text("ALTER TABLE embeddings ALTER COLUMN embedding TYPE vector(512)")
            )

    _schedule_hnsw_index_creation()


def _schedule_hnsw_index_creation() -> None:
    if _hnsw_index_creation_scheduled.is_set():
        return

    _hnsw_index_creation_scheduled.set()
    logger.info(
        "Launching background task to ensure HNSW indexes exist so uploads stay responsive while they build."
    )
    threading.Thread(
        target=_ensure_hnsw_indexes,
        name="hnsw-index-init",
        daemon=True,
    ).start()


def _ensure_hnsw_indexes() -> None:
    # Ensure HNSW indexes exist so cosine similarity searches remain fast. They must
    # be created concurrently using an autocommit connection so inserts remain
    # non-blocking while PostgreSQL finishes building them in the background.
    hnsw_index_statements = (
        (
            "embeddings_embedding_hnsw_idx",
            "CREATE INDEX CONCURRENTLY embeddings_embedding_hnsw_idx "
            "ON embeddings USING hnsw (embedding vector_cosine_ops)",
        ),
        (
            "images_embedding_hnsw_idx",
            "CREATE INDEX CONCURRENTLY images_embedding_hnsw_idx "
            "ON images USING hnsw (embedding vector_cosine_ops)",
        ),
        (
            "images_text_embedding_hnsw_idx",
            "CREATE INDEX CONCURRENTLY images_text_embedding_hnsw_idx "
            "ON images USING hnsw (text_embedding vector_cosine_ops)",
        ),
    )

    created_indexes: list[str] = []
    skipped_indexes: list[str] = []

    try:
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            for index_name, statement in hnsw_index_statements:
                exists = connection.execute(
                    sa_text("SELECT to_regclass(:index_name)"),
                    {"index_name": index_name},
                ).scalar()
                if exists:
                    skipped_indexes.append(index_name)
                    continue

                logger.info(
                    "Creating HNSW index %s concurrently so uploads remain available.",
                    index_name,
                )
                connection.execute(sa_text(statement))
                created_indexes.append(index_name)
    except Exception:  # pragma: no cover - defensive logging for unexpected failures.
        logger.exception("Failed to create HNSW indexes concurrently.")
        _hnsw_index_creation_scheduled.clear()
        return

    if created_indexes:
        logger.info(
            "Finished concurrent build for HNSW vector indexes: %s. They stay synchronized "
            "automatically on inserts.",
            ", ".join(created_indexes),
        )
    if skipped_indexes:
        logger.info(
            "HNSW vector indexes already exist; skipping creation: %s.",
            ", ".join(skipped_indexes),
        )


def init_default_user() -> None:
    settings = get_settings()
    if not settings.create_demo_user:
        logger.info("Skipping demo user creation; CREATE_DEMO_USER is disabled.")
        return

    session = SessionLocal()
    try:
        repository = UserRepository(session)
        if repository.get_by_username("user") is None:
            repository.create(
                username="user",
                hashed_password=hash_password("password"),
            )
    finally:
        session.close()


app = create_app()


__all__ = ["create_app", "app"]
