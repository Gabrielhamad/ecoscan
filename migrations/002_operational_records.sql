-- Private pilot tables; does not import or overwrite local CSV records.
begin;
create table if not exists public.ecoscan_points (
  id uuid primary key,
  user_id text not null check (user_id not like 'visitor_%'),
  mission_id text not null,
  evidence_sha256 text not null,
  created_at timestamptz not null default now(),
  record jsonb not null,
  unique(user_id, mission_id, evidence_sha256),
  check (record->>'id' = id::text),
  check (record->>'user_id' = user_id),
  check (record->>'mission_id' = mission_id),
  check (record->>'evidence_sha256' = evidence_sha256),
  check ((record->>'points')::integer between 0 and 10000),
  check (octet_length(record::text) <= 16384)
);
create table if not exists public.ecoscan_field_tests (
  id uuid primary key,
  tester_id text not null,
  created_at timestamptz not null default now(),
  record jsonb not null,
  check (record->>'id' = id::text),
  check (record->>'tester_id' = tester_id),
  check (record->>'result_status' in ('acertou','errou','inconclusivo')),
  check (octet_length(record::text) <= 16384)
);
create index if not exists ecoscan_points_owner on public.ecoscan_points(user_id, created_at);
create index if not exists ecoscan_field_tests_owner on public.ecoscan_field_tests(tester_id, created_at);
alter table public.ecoscan_points enable row level security;
alter table public.ecoscan_field_tests enable row level security;
revoke all on public.ecoscan_points, public.ecoscan_field_tests from anon, authenticated;
grant select, insert on public.ecoscan_points, public.ecoscan_field_tests to service_role;

create or replace function public.ecoscan_limit_field_tests()
returns trigger language plpgsql set search_path = public as $$
begin
  perform pg_advisory_xact_lock(728915);
  if (select count(*) from public.ecoscan_field_tests) >= 10000 then
    raise exception 'Pilot test quota reached';
  end if;
  if exists(select 1 from public.ecoscan_field_tests where tester_id=new.tester_id
    and created_at > now() - interval '10 seconds') then
    raise exception 'Please wait before submitting another test';
  end if;
  return new;
end;
$$;
revoke all on function public.ecoscan_limit_field_tests() from public, anon, authenticated;
do $$
begin
  if not exists (select 1 from pg_trigger where tgname = 'ecoscan_test_limit'
    and tgrelid = 'public.ecoscan_field_tests'::regclass) then
    create trigger ecoscan_test_limit before insert on public.ecoscan_field_tests
    for each row execute function public.ecoscan_limit_field_tests();
  end if;
end;
$$;
commit;
