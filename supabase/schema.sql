create extension if not exists pgcrypto;

create table if not exists resumes (
  id uuid primary key default gen_random_uuid(),
  owner_id text not null,
  filename text not null,
  mime_type text not null,
  size_bytes integer not null check (size_bytes > 0),
  extracted_text text not null,
  storage_path text,
  created_at timestamptz not null default now()
);

alter table resumes add column if not exists storage_path text;

create table if not exists analyses (
  id uuid primary key default gen_random_uuid(),
  owner_id text not null,
  resume_id uuid not null references resumes(id) on delete cascade,
  job_description text not null,
  result jsonb not null,
  created_at timestamptz not null default now()
);

create table if not exists research_experiments (
  id uuid primary key default gen_random_uuid(),
  owner_id text not null,
  name text not null,
  kind text not null check (kind in ('counterfactual', 'robustness', 'baseline')),
  config jsonb not null,
  created_at timestamptz not null default now()
);

create table if not exists research_runs (
  id uuid primary key default gen_random_uuid(),
  owner_id text not null,
  experiment_id uuid not null references research_experiments(id) on delete cascade,
  status text not null,
  result jsonb not null,
  executed_at timestamptz not null default now()
);

create table if not exists manuscript_sections (
  id uuid primary key default gen_random_uuid(),
  owner_id text not null,
  title text not null,
  content text not null default '',
  position integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists manuscript_revisions (
  id uuid primary key default gen_random_uuid(),
  owner_id text not null,
  section_id uuid not null references manuscript_sections(id) on delete cascade,
  content text not null,
  created_at timestamptz not null default now()
);

create index if not exists resumes_owner_created_idx
  on resumes (owner_id, created_at desc);

create index if not exists analyses_owner_created_idx
  on analyses (owner_id, created_at desc);

create index if not exists research_runs_owner_executed_idx
  on research_runs (owner_id, executed_at desc);

create index if not exists manuscript_sections_owner_position_idx
  on manuscript_sections (owner_id, position, created_at);

alter table resumes enable row level security;
alter table analyses enable row level security;
alter table research_experiments enable row level security;
alter table research_runs enable row level security;
alter table manuscript_sections enable row level security;
alter table manuscript_revisions enable row level security;

-- Existing demo-owner rows are intentionally not reassigned. New writes must
-- use the authenticated Supabase user UUID as owner_id.
do $$
begin
  if not exists (select 1 from pg_policies where policyname = 'resumes_select_own' and tablename = 'resumes') then
    create policy resumes_select_own on resumes for select to authenticated using (owner_id = auth.uid()::text);
    create policy resumes_insert_own on resumes for insert to authenticated with check (owner_id = auth.uid()::text);
    create policy resumes_update_own on resumes for update to authenticated using (owner_id = auth.uid()::text) with check (owner_id = auth.uid()::text);
    create policy resumes_delete_own on resumes for delete to authenticated using (owner_id = auth.uid()::text);
  end if;
  if not exists (select 1 from pg_policies where policyname = 'analyses_select_own' and tablename = 'analyses') then
    create policy analyses_select_own on analyses for select to authenticated using (owner_id = auth.uid()::text);
    create policy analyses_insert_own on analyses for insert to authenticated with check (
      owner_id = auth.uid()::text and exists (select 1 from resumes where resumes.id = analyses.resume_id and resumes.owner_id = auth.uid()::text)
    );
    create policy analyses_update_own on analyses for update to authenticated using (owner_id = auth.uid()::text) with check (owner_id = auth.uid()::text);
    create policy analyses_delete_own on analyses for delete to authenticated using (owner_id = auth.uid()::text);
  end if;
  if not exists (select 1 from pg_policies where policyname = 'research_experiments_select_own' and tablename = 'research_experiments') then
    create policy research_experiments_select_own on research_experiments for select to authenticated using (owner_id = auth.uid()::text);
    create policy research_experiments_insert_own on research_experiments for insert to authenticated with check (owner_id = auth.uid()::text);
    create policy research_experiments_update_own on research_experiments for update to authenticated using (owner_id = auth.uid()::text) with check (owner_id = auth.uid()::text);
    create policy research_experiments_delete_own on research_experiments for delete to authenticated using (owner_id = auth.uid()::text);
  end if;
  if not exists (select 1 from pg_policies where policyname = 'research_runs_select_own' and tablename = 'research_runs') then
    create policy research_runs_select_own on research_runs for select to authenticated using (owner_id = auth.uid()::text);
    create policy research_runs_insert_own on research_runs for insert to authenticated with check (
      owner_id = auth.uid()::text and exists (select 1 from research_experiments where research_experiments.id = research_runs.experiment_id and research_experiments.owner_id = auth.uid()::text)
    );
    create policy research_runs_update_own on research_runs for update to authenticated using (owner_id = auth.uid()::text) with check (owner_id = auth.uid()::text);
    create policy research_runs_delete_own on research_runs for delete to authenticated using (owner_id = auth.uid()::text);
  end if;
  if not exists (select 1 from pg_policies where policyname = 'manuscript_sections_select_own' and tablename = 'manuscript_sections') then
    create policy manuscript_sections_select_own on manuscript_sections for select to authenticated using (owner_id = auth.uid()::text);
    create policy manuscript_sections_insert_own on manuscript_sections for insert to authenticated with check (owner_id = auth.uid()::text);
    create policy manuscript_sections_update_own on manuscript_sections for update to authenticated using (owner_id = auth.uid()::text) with check (owner_id = auth.uid()::text);
    create policy manuscript_sections_delete_own on manuscript_sections for delete to authenticated using (owner_id = auth.uid()::text);
  end if;
  if not exists (select 1 from pg_policies where policyname = 'manuscript_revisions_select_own' and tablename = 'manuscript_revisions') then
    create policy manuscript_revisions_select_own on manuscript_revisions for select to authenticated using (
      owner_id = auth.uid()::text and exists (select 1 from manuscript_sections where manuscript_sections.id = manuscript_revisions.section_id and manuscript_sections.owner_id = auth.uid()::text)
    );
    create policy manuscript_revisions_insert_own on manuscript_revisions for insert to authenticated with check (
      owner_id = auth.uid()::text and exists (select 1 from manuscript_sections where manuscript_sections.id = manuscript_revisions.section_id and manuscript_sections.owner_id = auth.uid()::text)
    );
    create policy manuscript_revisions_update_own on manuscript_revisions for update to authenticated using (owner_id = auth.uid()::text) with check (owner_id = auth.uid()::text);
    create policy manuscript_revisions_delete_own on manuscript_revisions for delete to authenticated using (owner_id = auth.uid()::text);
  end if;
end $$;

grant select, insert, update, delete on resumes, analyses, research_experiments, research_runs, manuscript_sections, manuscript_revisions to authenticated;

insert into storage.buckets (id, name, public)
values ('resumes', 'resumes', false)
on conflict (id) do update set public = false;

do $$
begin
  if not exists (select 1 from pg_policies where policyname = 'resume_objects_select_own' and tablename = 'objects') then
    create policy resume_objects_select_own on storage.objects for select to authenticated using (
      bucket_id = 'resumes' and (storage.foldername(name))[1] = auth.uid()::text
    );
    create policy resume_objects_insert_own on storage.objects for insert to authenticated with check (
      bucket_id = 'resumes' and (storage.foldername(name))[1] = auth.uid()::text
    );
    create policy resume_objects_update_own on storage.objects for update to authenticated using (
      bucket_id = 'resumes' and (storage.foldername(name))[1] = auth.uid()::text
    ) with check (
      bucket_id = 'resumes' and (storage.foldername(name))[1] = auth.uid()::text
    );
    create policy resume_objects_delete_own on storage.objects for delete to authenticated using (
      bucket_id = 'resumes' and (storage.foldername(name))[1] = auth.uid()::text
    );
  end if;
end $$;
