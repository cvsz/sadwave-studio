import os
import re
from pathlib import Path

import psycopg
from psycopg import sql

MIGRATION_NAME = re.compile(r"^\d{3,}_[a-z0-9_]+\.sql$")


def main() -> None:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    migration_dir = Path(__file__).resolve().parents[1] / "migrations"
    migrations = sorted(
        path for path in migration_dir.iterdir() if MIGRATION_NAME.fullmatch(path.name)
    )
    if not migrations:
        raise SystemExit(f"No migration files found in {migration_dir}")

    app_role = os.environ.get("APP_DATABASE_USER", "").strip()
    app_password = os.environ.get("APP_DATABASE_PASSWORD", "")
    if bool(app_role) != bool(app_password):
        raise SystemExit("APP_DATABASE_USER and APP_DATABASE_PASSWORD must be set together")
    if app_role and (len(app_role) > 63 or len(app_password) < 32):
        raise SystemExit(
            "APP_DATABASE_USER must be at most 63 characters and app password at least 32"
        )

    with psycopg.connect(database_url) as connection:
        connection.execute("SELECT pg_advisory_xact_lock(73428301, 1)")
        if app_role:
            _ensure_application_role(connection, app_role, app_password)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        applied = {
            row[0] for row in connection.execute("SELECT version FROM schema_migrations").fetchall()
        }
        for migration in migrations:
            if migration.name in applied:
                continue
            connection.execute(migration.read_text(encoding="utf-8"))
            connection.execute(
                "INSERT INTO schema_migrations (version) VALUES (%s)",
                (migration.name,),
            )
            print(f"applied {migration.name}")
        if app_role:
            _grant_application_access(connection, app_role)


def _ensure_application_role(connection, role_name: str, password: str) -> None:
    admin_name = connection.execute("SELECT current_user").fetchone()[0]
    if role_name == admin_name:
        raise SystemExit("APP_DATABASE_USER must differ from the migration administrator")
    role_row = connection.execute(
        "SELECT oid FROM pg_roles WHERE rolname = %s", (role_name,)
    ).fetchone()
    if role_row is not None:
        owns_database = connection.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM pg_database
                WHERE datname = current_database() AND datdba = %s
            ) OR EXISTS (
                SELECT 1 FROM pg_shdepend
                WHERE refclassid = 'pg_authid'::regclass AND refobjid = %s AND deptype = 'o'
            )
            """,
            (role_row[0], role_row[0]),
        ).fetchone()[0]
        if owns_database:
            raise SystemExit(
                "APP_DATABASE_USER must not own the database or PostgreSQL objects; "
                "migrate ownership with the administrator first"
            )
    role = sql.Identifier(role_name)
    secret = sql.Literal(password)
    if role_row is not None:
        statement = sql.SQL(
            "ALTER ROLE {} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
            "NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD {}"
        ).format(role, secret)
    else:
        statement = sql.SQL(
            "CREATE ROLE {} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
            "NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD {}"
        ).format(role, secret)
    connection.execute(statement)
    memberships = connection.execute(
        """
        SELECT granted.rolname FROM pg_auth_members membership
        JOIN pg_roles granted ON granted.oid = membership.roleid
        JOIN pg_roles member ON member.oid = membership.member
        WHERE member.rolname = %s
        """,
        (role_name,),
    ).fetchall()
    for (granted_role,) in memberships:
        connection.execute(sql.SQL("REVOKE {} FROM {}").format(sql.Identifier(granted_role), role))


def _grant_application_access(connection, role_name: str) -> None:
    role = sql.Identifier(role_name)
    database = sql.Identifier(connection.execute("SELECT current_database()").fetchone()[0])
    connection.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(database, role))
    connection.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
    for table, privileges in (
        ("content_jobs", "SELECT, INSERT, UPDATE"),
        ("job_queue", "SELECT, INSERT, UPDATE"),
        ("audit_events", "INSERT"),
        ("rate_limit_buckets", "SELECT, INSERT, UPDATE"),
    ):
        connection.execute(
            sql.SQL("GRANT " + privileges + " ON TABLE {} TO {}").format(
                sql.Identifier(table), role
            )
        )
    connection.execute(sql.SQL("GRANT USAGE ON SEQUENCE job_queue_queue_id_seq TO {}").format(role))


if __name__ == "__main__":
    main()
