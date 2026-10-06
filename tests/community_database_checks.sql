-- Run inside a transaction after migration 003; ALWAYS finish with ROLLBACK.
-- Synthetic records only. No real accounts, contacts, reports or photos.
do $$
declare
  target text;
  identifier uuid := gen_random_uuid();
  actor text := 'supabase_' || gen_random_uuid()::text;
  affected integer;
begin
  foreach target in array array['ecoscan_campaigns','ecoscan_civic_reports','ecoscan_community_audit'] loop
    if not (select relrowsecurity from pg_class where oid = ('public.' || target)::regclass) then
      raise exception 'Missing RLS: %', target;
    end if;
    if has_table_privilege('anon', 'public.' || target, 'SELECT')
      or has_table_privilege('authenticated', 'public.' || target, 'SELECT')
      or has_table_privilege('authenticated', 'public.' || target, 'INSERT')
      or has_table_privilege('authenticated', 'public.' || target, 'UPDATE') then
      raise exception 'Unwanted browser privilege: %', target;
    end if;
  end loop;
  if exists(select 1 from storage.buckets where id = 'ecoscan-civic-evidence' and public) then
    raise exception 'Evidence bucket cannot be public';
  end if;
  if exists(select 1 from public.ecoscan_campaigns) then
    raise exception 'Run first-publication test in an isolated environment: active campaign exists';
  end if;
  begin
    set local role authenticated;
    perform * from public.ecoscan_civic_reports;
    raise exception 'BROWSER_ACCESS_TEST_FAILED';
  exception when insufficient_privilege then
    null;
  end;
  set local role service_role;
  insert into public.ecoscan_campaigns(id, revision, updated_by, record)
    values('active', 0, actor, '{"title":"Synthetic validation","missions":[]}'::jsonb);
  update public.ecoscan_campaigns set revision=1 where id='active' and revision=0;
  get diagnostics affected = row_count;
  if affected <> 1 then raise exception 'Campaign CAS failed'; end if;
  update public.ecoscan_campaigns set revision=1 where id='active' and revision=0;
  get diagnostics affected = row_count;
  if affected <> 0 then raise exception 'Stale campaign update succeeded'; end if;

  insert into public.ecoscan_civic_reports(id, reporter_id, request_hash, evidence_sha256,
    updated_by, record) values(identifier, actor, repeat('a',64), repeat('b',64), actor,
    jsonb_build_object('id', identifier::text, 'submitted_by',actor,
      'evidence_sha256',repeat('b',64),'evidence_path',''));
  begin
    update public.ecoscan_civic_reports set revision=1, record=record || '{"description":"tampered"}'::jsonb
      where id=identifier;
    raise exception 'IMMUTABILITY_TEST_FAILED';
  exception when raise_exception then
    if sqlerrm <> 'Original report is immutable' then raise; end if;
  end;
  update public.ecoscan_civic_reports set revision=1,
    reviews=jsonb_build_array(jsonb_build_object('decision','arquivar', 'note','Synthetic response',
      'admin_user_id',actor, 'timestamp_utc',now()::text))
    where id=identifier and revision=0;
  get diagnostics affected = row_count;
  if affected <> 1 then raise exception 'Report CAS failed'; end if;
  update public.ecoscan_civic_reports set revision=2 where id=identifier and revision=0;
  get diagnostics affected = row_count;
  if affected <> 0 then raise exception 'Stale report update succeeded'; end if;
  begin
    update public.ecoscan_civic_reports set revision=2, reviews='[]'::jsonb where id=identifier;
    raise exception 'HISTORY_TEST_FAILED';
  exception when raise_exception then
    if sqlerrm <> 'Invalid review history' then raise; end if;
  end;
  if (select count(*) from public.ecoscan_community_audit
    where entity='ecoscan_civic_reports' and entity_id=identifier::text) <> 2 then
    raise exception 'Audit missing';
  end if;
end;
$$;
reset role;
select 'M2 schema, RLS, CAS, immutable evidence metadata and audit: OK; transaction rolled back' as validation;
rollback;
