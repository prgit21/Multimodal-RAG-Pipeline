
# RAG Knowledge Hub

**Micro-frontends | Multimodal Chatbot | Retrieval-Augmented Generation (RAG)**

A knowledge hub that lets users upload, search, and query across documents and images using **retrieval-augmented multimodal generation**. Built with **Angular + React micro-frontends, FastAPI backend, Dockerized services, Postgres + pgvector, MinIO object storage, and HuggingFace embeddings**.

---

##  Features

* **Micro-frontend architecture**: Angular + React unified via `single-spa`, JWT-protected routing, Nginx proxy.
* **Multimodal chatbot**: Natural language + image queries through FastAPI REST endpoints.
* **Vector search pipeline**:

  * S3 for image storage.
  * PostgreSQL for metadata (URLs, hashes, dimensions).
  * pgvector + CLIP embeddings (image + text).
  * OCR text extraction for screenshots/diagrams.
* **ANN indexing**: IVF/HNSW for fast similarity search (cosine/dot product).
* **Context composition**:

  * Multimodal models (GPT-4o / GPT-4o-mini) consume both images + OCR/captions.
  * Text-only models consume captions/metadata.

---

##  RAG Flow (Conceptual)

1. **Upload & Store**

   * User uploads an image → store bytes in **S3**.
   * Save metadata in **Postgres** (URL, hash, width/height).

2. **Represent**

   * Generate global visual embeddings (**CLIP-style**).
   * Optional: run OCR/captioning → embed text → enrich search.

3. **Index**

   * Store vectors in **pgvector**.
   * Build **ANN index** (IVF/HNSW).

4. **Retrieve**

   * Query text → embed with CLIP text tower → ANN search over image vectors.
   * Hybrid retrieval (image + OCR/captions).
   * Return top-k candidates.

5. **Compose Context**

   * **Multimodal models**: Pass image URLs + OCR text.
   * **Text-only models**: Pass OCR/captions/metadata.

6. **Answer**

   * LLM answers using retrieved items, with citations.

---

##  Tech Stack

* **Frontend**: Angular + React (micro-frontends, single-spa).
* **Backend**: FastAPI REST services.
* **Auth**: JWT.
* **Database**: PostgreSQL + pgvector, S3.
* **Search**: ANN (IVF/HNSW).
* **Embeddings**: HuggingFace CLIP + OCR text.
* **Containerization**: Docker + docker-compose.
* **Reasoning**: OpenAI GPT-4o / GPT-4o-mini multimodal models.

---

##  Getting Started

```bash

# Start docker services
docker compose -f docker-compose.dev.yml up --build
```

Frontend apps run on `localhost:9000` (root-config), `4201` (Angular), `4202` (React).
Backend available on `localhost:8000`.

### Secure admin provisioning

* Demo environments can opt-in to seed the `user/password` credentials by setting `CREATE_DEMO_USER=true` in the backend environment. Production deployments should leave this unset (default) to avoid installing test accounts.
* To create real administrator accounts, use the FastAPI backend's CLI helper after exporting the required database environment variables:

  ```bash
  cd python-backend
  CREATE_DEMO_USER=false DATABASE_URL=... JWT_SECRET=... \
    python -m app.scripts.create_admin_user --username <admin> --password <strong-password>
  ```

  Omitting `--password` will prompt securely. The command hashes the password server-side and persists the user without exposing credentials in application logs.

---

