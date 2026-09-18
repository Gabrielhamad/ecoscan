-- Run once in the SQL editor of a dedicated Supabase Free project.
begin;
create table if not exists public.ecoscan_contributions (
  id uuid primary key,
  reporter_id text not null,
  image_sha256 text not null,
  revision integer not null default 0 check (revision >= 0),
  created_at timestamptz not null default now(),
  record jsonb not null,
  unique (reporter_id, image_sha256),
  check (record->>'id' = id::text),
  check (record->>'reporter_id' = reporter_id),
  check (octet_length(record::text) <= 65536)
);
alter table public.ecoscan_contributions enable row level security;
revoke all on public.ecoscan_contributions from anon, authenticated;
grant select, insert, update, delete on public.ecoscan_contributions to service_role;

create or replace function public.ecoscan_limit_contributions()
returns trigger language plpgsql set search_path = public as $$
begin
  perform pg_advisory_xact_lock(728914);
  if (select count(*) from public.ecoscan_contributions) >= 200 then
    raise exception 'Pilot queue full';
  end if;
  if exists (select 1 from public.ecoscan_contributions
    where reporter_id = new.reporter_id and created_at > now() - interval '15 seconds') then
    raise exception 'Please wait before submitting again';
  end if;
  return new;
end;
$$;
revoke all on function public.ecoscan_limit_contributions() from public, anon, authenticated;
drop trigger if exists ecoscan_contribution_limit on public.ecoscan_contributions;
create trigger ecoscan_contribution_limit before insert on public.ecoscan_contributions
  for each row execute function public.ecoscan_limit_contributions();

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('ecoscan-contributions', 'ecoscan-contributions', false, 1048576, array['image/jpeg'])
on conflict (id) do nothing;
commit;
