-- Additive hardening for tables created before the verified Supabase identity flow.
-- NOT VALID protects every new/updated row without blocking deployment when a
-- pilot project still contains legacy demo identifiers. Audit and remove those
-- rows before validating the constraints in production.
begin;
do $$
begin
  if not exists (select 1 from pg_constraint
    where conname = 'ecoscan_contributions_verified_reporter'
      and conrelid = 'public.ecoscan_contributions'::regclass) then
    alter table public.ecoscan_contributions
      add constraint ecoscan_contributions_verified_reporter
      check (reporter_id ~ '^supabase_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
      not valid;
  end if;
  if not exists (select 1 from pg_constraint
    where conname = 'ecoscan_points_verified_user'
      and conrelid = 'public.ecoscan_points'::regclass) then
    alter table public.ecoscan_points
      add constraint ecoscan_points_verified_user
      check (user_id ~ '^supabase_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
      not valid;
  end if;
  if not exists (select 1 from pg_constraint
    where conname = 'ecoscan_field_tests_verified_tester'
      and conrelid = 'public.ecoscan_field_tests'::regclass) then
    alter table public.ecoscan_field_tests
      add constraint ecoscan_field_tests_verified_tester
      check (tester_id ~ '^supabase_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
      not valid;
  end if;
end;
$$;
commit;
