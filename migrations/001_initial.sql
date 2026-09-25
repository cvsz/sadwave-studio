CREATE TABLE IF NOT EXISTS content_jobs (
    job_id UUID PRIMARY KEY,
    channel_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    state TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_content_jobs_channel_state
    ON content_jobs (channel_id, state);
