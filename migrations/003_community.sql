-- Additive migration. No local CSV import, no deletion, no public photo access.
begin;
create table if not exists public.ecoscan_campaigns (
  id text primary key check (id = 'active'),
  revision integer not null check (revision >= 0),
  updated_by text not null check (updated_by ~ '^supabase_[0-9a-f-]{36}$'),
  updated_at timestamptz not null default now(),
  record jsonb not null check (jsonb_typeof(record) = 'object'),
  check (octet_length(record::text) <= 65536),
  check (coalesce(jsonb_typeof(record->'missions') = 'array', false))
);
create table if not exists public.ecoscan_civic_reports (
  id uuid primary key,
  reporter_id text not null check (reporter_id ~ '^supabase_[0-9a-f-]{36}$'),
  request_hash text not null check (request_hash ~ '^[0-9a-f]{64}$'),
  evidence_sha256 text not null check (evidence_sha256 ~ '^[0-9a-f]{64}$'),
  revision integer not null default 0 check (revision >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  updated_by text not null check (updated_by ~ '^supabase_[0-9a-f-]{36}$'),
  record jsonb not null check (jsonb_typeof(record) = 'object'),
  reviews jsonb not null default '[]'::jsonb check (jsonb_typeof(reviews) = 'array'),
  check (coalesce(record->>'id' = id::text, false)),
  check (coalesce(record->>'submitted_by' = reporter_id, false)),
  check (coalesce(record->>'evidence_sha256' = evidence_sha256, false)),
  check (coalesce(record->>'evidence_path' = '', false)),
  check (octet_length(record::text) <= 16384),
  check (jsonb_array_length(reviews) <= 100),
  check (octet_length(reviews::text) <= 1048576)
);
create index if not exists ecoscan_civic_owner
  on public.ecoscan_civic_reports(reporter_id, created_at desc, id desc);
create table if not exists public.ecoscan_community_audit (
  sequence bigint generated always as identity primary key,
  entity text not null,
  entity_id text not null,
  revision integer not null,
  actor text not null,
  created_at timestamptz not null default now(),
  snapshot jsonb not null,
  unique(entity, entity_id, revision)
);
alter table public.ecoscan_campaigns enable row level security;
alter table public.ecoscan_civic_reports enable row level security;
alter table public.ecoscan_community_audit enable row level security;
revoke all on public.ecoscan_campaigns, public.ecoscan_civic_reports,
  public.ecoscan_community_audit from public, anon, authenticated;
grant select, insert, update on public.ecoscan_campaigns,
  public.ecoscan_civic_reports to service_role;
grant select on public.ecoscan_community_audit to service_role;

create or replace function public.ecoscan_community_guard()
returns trigger language plpgsql set search_path = public as $$
begin
  if tg_op = 'INSERT' then
    if new.revision <> 0 then raise exception 'Initial revision must be zero'; end if;
    if tg_table_name = 'ecoscan_civic_reports' then
      perform pg_advisory_xact_lock(728916);
      if (select count(*) from public.ecoscan_civic_reports) >= 200 then
        raise exception 'Pilot report quota reached';
      end if;
      if jsonb_array_length(new.reviews) <> 0 or new.updated_by <> new.reporter_id then
        raise exception 'Initial report cannot contain a review';
      end if;
      if exists(select 1 from public.ecoscan_civic_reports where reporter_id = new.reporter_id
        and created_at > now() - interval '15 seconds') then
        raise exception 'Please wait before submitting another report';
      end if;
    end if;
  else
    if new.id <> old.id or new.revision <> old.revision + 1 then
      raise exception 'Invalid revision';
    end if;
    if tg_table_name = 'ecoscan_civic_reports' then
      if new.reporter_id <> old.reporter_id or new.request_hash <> old.request_hash
        or new.evidence_sha256 <> old.evidence_sha256 or new.record <> old.record
        or new.created_at <> old.created_at then
        raise exception 'Original report is immutable';
      end if;
      if jsonb_array_length(new.reviews) <> jsonb_array_length(old.reviews) + 1
        or (new.reviews - (jsonb_array_length(new.reviews) - 1)) <> old.reviews
        or not coalesce(new.reviews->-1->>'decision' in
          ('encaminhar','arquivar','solicitar_nova_foto'), false)
        or not coalesce(new.reviews->-1->>'admin_user_id' = new.updated_by, false)
        or not coalesce(length(new.reviews->-1->>'note') between 1 and 2000, false) then
        raise exception 'Invalid review history';
      end if;
    end if;
  end if;
  new.updated_at = now();
  return new;
end;
$$;
create or replace function public.ecoscan_community_audit_write()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.ecoscan_community_audit(entity, entity_id, revision, actor, snapshot)
    values(tg_table_name, new.id::text, new.revision, new.updated_by, to_jsonb(new));
  return new;
end;
$$;
revoke all on function public.ecoscan_community_guard(),
  public.ecoscan_community_audit_write() from public, anon, authenticated;
do $$
declare target text;
begin
  foreach target in array array['ecoscan_campaigns','ecoscan_civic_reports'] loop
    if not exists(select 1 from pg_trigger where tgname = 'ecoscan_community_guard'
      and tgrelid = ('public.' || target)::regclass) then
      execute format('create trigger ecoscan_community_guard before insert or update on public.%I for each row execute function public.ecoscan_community_guard()', target);
      execute format('create trigger ecoscan_community_audit after insert or update on public.%I for each row execute function public.ecoscan_community_audit_write()', target);
    end if;
  end loop;
end;
$$;
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('ecoscan-civic-evidence', 'ecoscan-civic-evidence', false, 1048576, array['image/jpeg'])
on conflict (id) do nothing;
commit;
