-- Phase 1 additive database hardening.
-- Run after supabase/schema.sql in the Supabase SQL Editor.
-- This script does not reassign existing demo-user rows.

create table if not exists profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table profiles enable row level security;

create index if not exists profiles_created_idx
  on profiles (created_at desc);

do $$
begin
  if not exists (select 1 from pg_policies where policyname = 'profiles_select_own' and tablename = 'profiles') then
    create policy profiles_select_own on profiles for select to authenticated
      using (id = auth.uid());
  end if;
  if not exists (select 1 from pg_policies where policyname = 'profiles_insert_own' and tablename = 'profiles') then
    create policy profiles_insert_own on profiles for insert to authenticated
      with check (id = auth.uid());
  end if;
  if not exists (select 1 from pg_policies where policyname = 'profiles_update_own' and tablename = 'profiles') then
    create policy profiles_update_own on profiles for update to authenticated
      using (id = auth.uid()) with check (id = auth.uid());
  end if;
  if not exists (select 1 from pg_policies where policyname = 'profiles_delete_own' and tablename = 'profiles') then
    create policy profiles_delete_own on profiles for delete to authenticated
      using (id = auth.uid());
  end if;
end $$;

grant select, insert, update, delete on profiles to authenticated;
