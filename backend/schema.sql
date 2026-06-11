CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS guideline_documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  guideline_id text NOT NULL UNIQUE,
  title text NOT NULL,
  institution text NOT NULL,
  source_type text NOT NULL CHECK (
    source_type IN ('GPC', 'RIAS', 'PROTOCOLO')
  ),
  source_url text NOT NULL,
  publication_year integer,
  version text,
  sha256 text NOT NULL,
  file_bytes bigint,
  page_count integer,
  status text NOT NULL DEFAULT 'pending' CHECK (
    status IN ('pending', 'processing', 'ready', 'rejected')
  ),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS guideline_documents_sha256_idx
  ON guideline_documents (sha256);

CREATE TABLE IF NOT EXISTS guideline_chunks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid NOT NULL
    REFERENCES guideline_documents(id) ON DELETE CASCADE,
  ordinal integer NOT NULL,
  guideline_id text NOT NULL,
  title text NOT NULL,
  condition text,
  source_type text,
  publisher text,
  year integer,
  audience text,
  priority text,
  country text NOT NULL DEFAULT 'Colombia',
  clinical_area text,
  section_guess text,
  recommendation_type_guess text,
  population text,
  care_level text,
  urgency text,
  heading text,
  page_start integer,
  page_end integer,
  url text NOT NULL,
  content text NOT NULL,
  retrieval_eligible boolean NOT NULL DEFAULT true,
  source_sha256 text NOT NULL,
  embedding_model text NOT NULL,
  embedding vector(1536) NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (document_id, ordinal)
);

CREATE INDEX IF NOT EXISTS guideline_chunks_embedding_hnsw
  ON guideline_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS guideline_chunks_condition_idx
  ON guideline_chunks (condition);
CREATE INDEX IF NOT EXISTS guideline_chunks_source_type_idx
  ON guideline_chunks (source_type);
CREATE INDEX IF NOT EXISTS guideline_chunks_section_idx
  ON guideline_chunks (section_guess);
CREATE INDEX IF NOT EXISTS guideline_chunks_retrieval_eligible_idx
  ON guideline_chunks (retrieval_eligible)
  WHERE retrieval_eligible = true;
CREATE INDEX IF NOT EXISTS guideline_chunks_metadata_gin
  ON guideline_chunks USING gin (metadata);

CREATE TABLE IF NOT EXISTS clinical_queries (
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

CREATE TABLE IF NOT EXISTS answer_feedback (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  query_id uuid NOT NULL
    REFERENCES clinical_queries(id) ON DELETE CASCADE,
  rating smallint CHECK (rating BETWEEN 1 AND 5),
  critical_omission boolean NOT NULL DEFAULT false,
  incorrect_citation boolean NOT NULL DEFAULT false,
  comment text,
  created_at timestamptz NOT NULL DEFAULT now()
);
