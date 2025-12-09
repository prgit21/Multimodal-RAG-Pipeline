
# Multimodal RAG Pipeline

**Text–Image Retrieval-Augmented Generation System**

A production-oriented **multimodal RAG pipeline** enabling semantic search and question answering over **documents and images** by combining **vector retrieval, distributed backend services, and multimodal LLMs**.

Built with **FastAPI**, **PostgreSQL + pgvector**, **Amazon S3**, **Dockerized services**, and **Angular + React micro-frontends**.

---

## Key Capabilities

* **Micro-frontend UI**: Angular + React composed via `single-spa`, routed through JWT-secured gateways
* **Backend services**: FastAPI REST APIs for ingestion, retrieval, and query orchestration
* **Vector retrieval**:

  * CLIP (HuggingFace) embeddings for text and images
  * pgvector-backed similarity search with **ANN indexes (IVF / HNSW)**
  * OCR-based enrichment for screenshots and diagrams
* **Object storage**: Images stored in **Amazon S3**, referenced via metadata and embeddings
* **RAG orchestration**: Retrieved image URLs, OCR text, and metadata composed into grounded LLM prompts

---

## End-to-End Flow

1. **Ingest** – Upload documents/images → store binaries in **S3**, metadata in **PostgreSQL**
2. **Embed** – Generate CLIP embeddings; optionally enrich with OCR/captions
3. **Index** – Persist vectors in pgvector with ANN indexing
4. **Retrieve** – Embed query → ANN search → hybrid retrieval over images + text
5. **Compose** – Assemble multimodal or text-only context
6. **Generate** – LLM responds with citations grounded in retrieved data

---

## Tech Stack

**Frontend**: Angular, React, micro-frontends (`single-spa`)
**Backend**: FastAPI, REST APIs, JWT auth
**Data**: PostgreSQL, pgvector, Amazon S3
**Search**: ANN (IVF / HNSW)
**ML**: CLIP embeddings, OCR pipelines, multimodal LLMs (GPT-4o / GPT-4o-mini)
**Infra**: Docker, docker-compose, Nginx

---

## Running Locally

```bash
docker compose -f docker-compose.dev.yml up --build
```

* Frontend root: `http://localhost:9000`
* Backend API: `http://localhost:8000`

---

## Secure User Provisioning

```bash
cd python-backend
CREATE_DEMO_USER=false DATABASE_URL=... JWT_SECRET=... \
python -m app.scripts.create_admin_user --username <admin> --password <password>
```

Passwords are hashed server-side and never logged.

---

## Design Goals

* Scalable retrieval over mixed media
* Clean separation of **storage, retrieval, and reasoning**
* Extensible foundation for future RAG and multimodal systems

---
