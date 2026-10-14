#!/usr/bin/env bash
# Only creates a disposable private cluster. Never uses POSTGRES_* credentials.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.."
scb_pg_bin=${SCB_PG_BIN:-/usr/lib/postgresql/16/bin}
for binary in initdb pg_ctl createdb psql; do
    test -x "$scb_pg_bin/$binary"
done
export SCB_HOMO_SOCKET
SCB_HOMO_SOCKET=$(mktemp -d /tmp/scb-pedro-03.XXXXXXXX)
stop_cluster() {
    "$scb_pg_bin/pg_ctl" -D "$SCB_HOMO_SOCKET/data" -m fast -w stop > "$SCB_HOMO_SOCKET/stop.log" 2>&1 || true
}
trap stop_cluster EXIT
printf 'Synthetic homologation evidence: %s\n' "$SCB_HOMO_SOCKET"
"$scb_pg_bin/initdb" -D "$SCB_HOMO_SOCKET/data" -U scb_homologation --auth-local=trust --auth-host=reject --encoding=UTF8 --locale=C.UTF-8 > "$SCB_HOMO_SOCKET/initdb.log"
"$scb_pg_bin/pg_ctl" -D "$SCB_HOMO_SOCKET/data" -l "$SCB_HOMO_SOCKET/server.log" -o "-k $SCB_HOMO_SOCKET -h '' -p 55483" -w start
"$scb_pg_bin/createdb" -h "$SCB_HOMO_SOCKET" -p 55483 -U scb_homologation scb_pedro03
.venv/bin/python manage.py migrate --settings=config.settings.postgres_homologation --noinput > "$SCB_HOMO_SOCKET/migrations.log" 2>&1
.venv/bin/python manage.py sync_backoffice_roles --settings=config.settings.postgres_homologation > "$SCB_HOMO_SOCKET/rbac.log" 2>&1
"$scb_pg_bin/psql" -X -v ON_ERROR_STOP=1 -h "$SCB_HOMO_SOCKET" -p 55483 -U scb_homologation -d scb_pedro03 -f scripts/audits/pedro_destination_readonly.sql > "$SCB_HOMO_SOCKET/readonly-synthetic.log"
.venv/bin/python manage.py test src.backoffice src.customers src.salespeople src.sales_intelligence src.commerce src.institutional.infrastructure.django.tests.AuthenticationRoutesTests --settings=config.settings.postgres_homologation --noinput > "$SCB_HOMO_SOCKET/tests.log" 2>&1
.venv/bin/python manage.py makemigrations --check --dry-run --settings=config.settings.postgres_homologation > "$SCB_HOMO_SOCKET/migration-drift.log" 2>&1
printf 'Homologation passed. Review evidence in %s; private cluster will be stopped.\n' "$SCB_HOMO_SOCKET"
