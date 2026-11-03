-- Additive migration for resumable upload/analysis compensation.
-- Apply only after review in the intended environment.
alter table resumes add column if not exists workflow_token uuid;
create index if not exists resumes_workflow_token_idx
  on resumes (workflow_token)
  where workflow_token is not null;
