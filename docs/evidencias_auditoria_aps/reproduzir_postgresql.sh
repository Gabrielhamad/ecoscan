#!/usr/bin/env bash
# Apenas PostgreSQL descartável local. Nunca apontar ao Supabase.
set -euo pipefail
name="ecoscan-audit-pg-${RANDOM}"
docker_local=(env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH docker --host=unix:///var/run/docker.sock)
"${docker_local[@]}" info >/dev/null
"${docker_local[@]}" run -d --name "$name" -e POSTGRES_PASSWORD=audit-local-only postgres:16@sha256:f9a7b9ebf6f56201f949db745e47bc423c0f0f8294bafe991cc10bf74b029657
trap '"${docker_local[@]}" rm -f "$name" >/dev/null' EXIT
"${docker_local[@]}" cp tests "$name":/audit-tests
"${docker_local[@]}" cp migrations "$name":/audit-migrations
for attempt in {1..30}; do
  if "${docker_local[@]}" exec "$name" pg_isready -U postgres; then break; fi
  sleep 1
done
psql_local=("${docker_local[@]}" exec "$name" psql -U postgres -v ON_ERROR_STOP=1)
"${psql_local[@]}" -f /audit-tests/community_database_fixture.sql
for file in 001_contributions.sql 002_operational_records.sql 003_community.sql 003_community.sql 004_verified_identity_constraints.sql 004_verified_identity_constraints.sql; do
  "${psql_local[@]}" -f "/audit-migrations/$file"
done
"${psql_local[@]}" -c BEGIN -f /audit-tests/community_database_checks.sql
