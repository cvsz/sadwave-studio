from __future__ import annotations

import argparse
import hashlib
import getpass
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Mapping
from urllib.parse import quote, quote_plus

from psycopg.conninfo import conninfo_to_dict, make_conninfo

ALLOWED_CONNECTION_OPTIONS = {
    "application_name",
    "channel_binding",
    "connect_timeout",
    "dbname",
    "gssencmode",
    "host",
    "hostaddr",
    "keepalives",
    "keepalives_count",
    "keepalives_idle",
    "keepalives_interval",
    "port",
    "sslcert",
    "sslcrl",
    "sslcrldir",
    "sslkey",
    "sslmode",
    "sslrootcert",
    "ssl_max_protocol_version",
    "ssl_min_protocol_version",
    "target_session_attrs",
    "tcp_user_timeout",
    "user",
}


class BackupError(Exception):
    pass


def _connection_info(
    database_url: str, environ: Mapping[str, str]
) -> tuple[str, dict[str, str], str | None, str | None]:
    try:
        options = conninfo_to_dict(database_url)
    except Exception:
        raise BackupError("DATABASE_URL is not a valid PostgreSQL connection string") from None

    password = options.pop("password", None)
    if password is None:
        password = environ.get("PGPASSWORD")
    passfile = options.pop("passfile", None)
    unsupported = set(options) - ALLOWED_CONNECTION_OPTIONS
    if unsupported:
        raise BackupError("DATABASE_URL contains unsupported connection options")

    try:
        conninfo = make_conninfo(**options)
    except Exception:
        raise BackupError("DATABASE_URL is not a valid PostgreSQL connection string") from None
    return conninfo, options, password, passfile


def _escape_pgpass_field(value: str) -> str:
    if any(character in value for character in "\r\n\0"):
        raise BackupError("PostgreSQL credentials cannot be represented safely")
    return value.replace("\\", "\\\\").replace(":", "\\:")


def _write_pgpass(
    directory: Path,
    password: str,
    options: Mapping[str, str],
    environ: Mapping[str, str],
) -> Path:
    try:
        operating_user = getpass.getuser()
    except Exception:
        operating_user = "*"
    fields = (
        options.get("host") or options.get("hostaddr") or environ.get("PGHOST") or "localhost",
        options.get("port") or environ.get("PGPORT") or "5432",
        options.get("dbname") or environ.get("PGDATABASE") or "*",
        options.get("user") or environ.get("PGUSER") or operating_user,
        password,
    )
    entry = ":".join(_escape_pgpass_field(field) for field in fields) + "\n"
    path = directory / "pgpass"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(entry)
    return path


def _safe_diagnostics(diagnostics: str, database_url: str, password: str | None) -> str:
    secrets = {database_url}
    if password:
        secrets.update({password, quote(password, safe=""), quote_plus(password, safe="")})
    result = diagnostics
    for secret in sorted(secrets, key=len, reverse=True):
        if secret:
            result = result.replace(secret, "[REDACTED]")
    return result.strip()


def _run_client(
    executable: str,
    arguments: list[str],
    environ: Mapping[str, str],
    database_url: str,
    password: str | None,
) -> None:
    try:
        result = subprocess.run(
            [executable, *arguments],
            check=False,
            env=dict(environ),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError:
        raise BackupError("Could not start the PostgreSQL client utility") from None
    diagnostics = _safe_diagnostics(result.stderr, database_url, password)
    if result.returncode:
        detail = f": {diagnostics}" if diagnostics else ""
        raise BackupError(f"{Path(executable).name} failed (exit {result.returncode}){detail}")
    if diagnostics:
        print(diagnostics, file=sys.stderr)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as archive:
        for chunk in iter(lambda: archive.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_backup(output: Path, environ: Mapping[str, str] | None = None) -> dict[str, object]:
    source_environment = dict(os.environ if environ is None else environ)
    database_url = source_environment.get("DATABASE_URL", "").strip()
    if not database_url:
        raise BackupError("DATABASE_URL is required")
    if os.name != "posix":
        raise BackupError("Secure backup files currently require a POSIX filesystem")

    target = output.expanduser()
    if not target.parent.is_dir():
        raise BackupError("Backup destination directory must already exist")
    if target.exists() or target.is_symlink():
        raise BackupError("Backup destination already exists; refusing to overwrite it")

    pg_dump = shutil.which("pg_dump")
    pg_restore = shutil.which("pg_restore")
    if not pg_dump or not pg_restore:
        raise BackupError("pg_dump and pg_restore must be installed and available on PATH")

    conninfo, options, password, configured_passfile = _connection_info(
        database_url, source_environment
    )
    child_environment = source_environment.copy()
    child_environment.pop("PGPASSWORD", None)
    if configured_passfile:
        child_environment["PGPASSFILE"] = configured_passfile

    temporary_passfile: tempfile.TemporaryDirectory[str] | None = None
    descriptor = -1
    temporary_archive: Path | None = None
    published = False
    try:
        if password is not None:
            temporary_passfile = tempfile.TemporaryDirectory(prefix="sadwave-pgpass-")
            os.chmod(temporary_passfile.name, stat.S_IRWXU)
            passfile = _write_pgpass(
                Path(temporary_passfile.name), password, options, source_environment
            )
            child_environment["PGPASSFILE"] = str(passfile)

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
        )
        os.fchmod(descriptor, 0o600)
        os.close(descriptor)
        descriptor = -1
        temporary_archive = Path(temporary_name)

        _run_client(
            pg_dump,
            [
                "--format=custom",
                "--quote-all-identifiers",
                "--no-password",
                "--file",
                str(temporary_archive),
                "--dbname",
                conninfo,
            ],
            child_environment,
            database_url,
            password,
        )
        if not temporary_archive.is_file() or temporary_archive.stat().st_size == 0:
            raise BackupError("pg_dump did not create a non-empty archive")

        _run_client(
            pg_restore,
            ["--list", str(temporary_archive)],
            child_environment,
            database_url,
            password,
        )
        os.chmod(temporary_archive, 0o600)
        size_bytes = temporary_archive.stat().st_size
        checksum = _sha256(temporary_archive)
        with temporary_archive.open("rb") as archive:
            os.fsync(archive.fileno())
        os.link(temporary_archive, target)
        published = True
        temporary_archive.unlink()
        directory_descriptor = os.open(target.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
        return {
            "file_name": target.name,
            "size_bytes": size_bytes,
            "sha256": checksum,
        }
    except OSError as error:
        if published:
            target.unlink(missing_ok=True)
        if isinstance(error, FileExistsError):
            raise BackupError(
                "Backup destination already exists; refusing to overwrite it"
            ) from None
        raise BackupError("Could not safely write the backup archive") from None
    finally:
        try:
            if descriptor >= 0:
                os.close(descriptor)
        finally:
            try:
                if temporary_archive is not None:
                    temporary_archive.unlink(missing_ok=True)
            finally:
                if temporary_passfile is not None:
                    temporary_passfile.cleanup()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a protected PostgreSQL custom archive.")
    parser.add_argument(
        "output", type=Path, help="new backup file path; existing files are refused"
    )
    arguments = parser.parse_args()
    try:
        result = create_backup(arguments.output)
    except BackupError as error:
        parser.exit(1, f"backup failed: {error}\n")
    print("PostgreSQL backup verified:")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
