# PostgreSQL backup and restore

This runbook covers operator initiated logical backups of one SadwaveStudio database. The repository
does not schedule backups, retain them, encrypt them at rest, or copy them off-host. Those controls
must be provided by the operator's approved storage and secret-management environment before this
procedure is used for production data.

## Create a backup

Install PostgreSQL client utilities for the same major version as the server. `pg_dump` can dump an
older server, but a dump from a newer client is not guaranteed to restore to an older server. The
backup utility requires both `pg_dump` and `pg_restore` on `PATH` and the project's Python
dependencies installed. It currently requires POSIX filesystem permission semantics; run it from a
Linux/macOS host or a Linux-based WSL environment.

The backup identity must be authorized to read every object and row being backed up. The runtime
`sadwave_app` role is deliberately restricted and is not the backup identity. Use an approved
read-capable database role, and keep its password in a mode-0600 libpq password file or injected
`PGPASSWORD` environment variable. The utility removes `PGPASSWORD` from the child process and, when
it receives a password, passes it through a temporary mode-0600 password file that is deleted when
the command exits. Passwords are removed from the connection string passed to client processes.

Create the backup directory with operator-only access, then run:

```sh
umask 077
mkdir -p /secure/backups/sadwave
DATABASE_URL='postgresql://backup_user@db-host:5432/sadwave?sslmode=verify-full&sslrootcert=/path/to/ca.crt' \
  PGPASSFILE='/run/secrets/postgres-backup.pgpass' \
  python scripts/backup.py "/secure/backups/sadwave/sadwave-$(date -u +%Y%m%dT%H%M%SZ).dump"
```

The destination directory must already exist, and the destination filename must be new. The command
creates a compressed custom-format archive with mode `0600`, validates its archive table of contents
with `pg_restore --list`, and prints its filename, byte size, and SHA-256 digest. It never overwrites
an existing backup. Store the digest beside the backup using the approved storage process.

This is a logical, single-database backup, not a cluster-level backup. It does not back up
cluster-global roles, tablespace definitions or storage, WAL archives, point-in-time recovery,
backup scheduling, retention, or off-host copies. It excludes the optimizer statistics PostgreSQL
rebuilds with `ANALYZE` after restore. Do not call it a complete disaster-recovery solution until
those operational controls and recovery objectives are defined.

## Verify and restore to a new database

Only restore archives from a trusted source. PostgreSQL warns that restoring an archive can execute
SQL chosen by a source database superuser. Keep the source database and archive within the approved
trust boundary.

1. Verify the expected SHA-256 digest through the approved backup-storage process.
2. Inspect the archive table of contents:

   ```sh
   pg_restore --list "$BACKUP_FILE" >/dev/null
   ```

3. Have the database administrator create a **new, empty** target database on the intended recovery
   server. Do not use `pg_restore --clean` or `--create` for this runbook.
4. Set `DATABASE_URL` to that target using a connection string without an embedded password. Supply
   authentication through a protected `PGPASSFILE`. Run the restore as the authorized
   migration/database owner:

   ```sh
   pg_restore --no-password --exit-on-error --single-transaction \
     --no-owner --no-acl --no-tablespaces --dbname "$DATABASE_URL" "$BACKUP_FILE"
   ```

   `--single-transaction` makes the restore all-or-nothing. If it fails, leave the target isolated,
   investigate the failure, and recreate a new empty target before retrying; do not retry into a
   partially populated database.
5. With `DATABASE_URL` still pointing at the recovered database, inject the approved
   `APP_DATABASE_USER` and `APP_DATABASE_PASSWORD` values and run `python scripts/migrate.py`. The
   migration runner provisions or re-grants the restricted runtime role without rerunning migration
   versions already recorded in the restored database.
6. Run `ANALYZE` on the recovered database, verify expected rows and sequence values against the
   recorded source counts, run the PostgreSQL integration tests against this disposable recovery
   database, and verify application readiness before any operator authorizes a cutover:

   ```sh
   psql -X --no-password --dbname "$DATABASE_URL" -c 'ANALYZE'
   psql -X --no-password --dbname "$DATABASE_URL" \
     -c 'SELECT count(*) FROM content_jobs' \
     -c 'SELECT count(*) FROM job_queue' \
     -c 'SELECT count(*) FROM audit_events'
   ```

Never point this drill at production or overwrite a live database. Record the server versions,
archive digest, restore duration, row-count checks, and outcome in the approved operations record.
Production RPO/RTO, automated retention, encrypted off-host storage, alerting, and a production
recovery exercise remain separate release gates.
