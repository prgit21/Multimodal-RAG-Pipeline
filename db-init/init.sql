CREATE EXTENSION IF NOT EXISTS vector;

DO $$
BEGIN
  IF to_regclass('public.embeddings') IS NOT NULL THEN
    EXECUTE 'CREATE INDEX embeddings_embedding_hnsw_idx
             ON embeddings USING hnsw (embedding vector_cosine_ops)';
  END IF;

  IF to_regclass('public.images') IS NOT NULL THEN
    EXECUTE 'CREATE INDEX images_embedding_hnsw_idx
             ON images USING hnsw (embedding vector_cosine_ops)';
    EXECUTE 'CREATE INDEX images_text_embedding_hnsw_idx
             ON images USING hnsw (text_embedding vector_cosine_ops)';
  END IF;
END $$;
