CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE guideline_documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL,
  institution text NOT NULL,
  source_type text NOT NULL CHECK (source_type IN ('GPC', 'RIAS', 'PROTOCOLO')),
  source_url text NOT NULL,
  publication_year integer,
  version text,
  sha256 text NOT NULL UNIQUE,
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'processing', 'ready', 'rejected')),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE guideline_chunks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid NOT NULL REFERENCES guideline_documents(id) ON DELETE CASCADE,
  ordinal integer NOT NULL,
  disease_ids text[] NOT NULL DEFAULT '{}',
  population_tags text[] NOT NULL DEFAULT '{}',
  care_setting text,
  heading text,
  page_start integer,
  page_end integer,
  content text NOT NULL,
  scope_note text,
  recommendation_strength text,
  evidence_quality text,
  embedding vector(1536) NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE (document_id, ordinal)
);

CREATE INDEX guideline_chunks_embedding_hnsw
  ON guideline_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX guideline_chunks_disease_ids_gin
  ON guideline_chunks USING gin (disease_ids);
CREATE INDEX guideline_chunks_population_tags_gin
  ON guideline_chunks USING gin (population_tags);

CREATE TABLE clinical_queries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid,
  query_hash text NOT NULL,
  filters jsonb NOT NULL DEFAULT '{}'::jsonb,
  retrieved_chunk_ids uuid[] NOT NULL DEFAULT '{}',
  abstained boolean NOT NULL,
  confidence text NOT NULL,
  safety_flags text[] NOT NULL DEFAULT '{}',
  latency_ms integer,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE answer_feedback (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  query_id uuid NOT NULL REFERENCES clinical_queries(id) ON DELETE CASCADE,
  rating smallint CHECK (rating BETWEEN 1 AND 5),
  critical_omission boolean NOT NULL DEFAULT false,
  incorrect_citation boolean NOT NULL DEFAULT false,
  comment text,
  created_at timestamptz NOT NULL DEFAULT now()
);

