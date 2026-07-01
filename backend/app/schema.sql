CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS research_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status TEXT NOT NULL,
    provider_mode TEXT NOT NULL,
    input_type TEXT NOT NULL,
    request_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    progress_message TEXT NOT NULL DEFAULT '',
    product_reference JSONB,
    partial_brief JSONB,
    final_brief JSONB,
    retryable BOOLEAN NOT NULL DEFAULT FALSE,
    safe_error JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

ALTER TABLE research_jobs ADD COLUMN IF NOT EXISTS request_payload JSONB NOT NULL DEFAULT '{}'::JSONB;

CREATE TABLE IF NOT EXISTS uploaded_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES research_jobs(id) ON DELETE CASCADE,
    object_key TEXT NOT NULL,
    content_type TEXT NOT NULL,
    size_bytes BIGINT NOT NULL,
    checksum TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS job_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES research_jobs(id) ON DELETE CASCADE,
    stage TEXT NOT NULL,
    dependency TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    error_code TEXT,
    retryable BOOLEAN NOT NULL DEFAULT FALSE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS dependency_health (
    dependency TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    recent_failure_count INTEGER NOT NULL DEFAULT 0,
    recent_success_count INTEGER NOT NULL DEFAULT 0,
    opened_at TIMESTAMPTZ,
    cooldown_until TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
