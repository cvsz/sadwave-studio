from __future__ import annotations

import hashlib
import importlib.util
import stat
import subprocess
from pathlib import Path

import pytest

BACKUP_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "backup.py"
BACKUP_SPEC = importlib.util.spec_from_file_location("sadwave_backup", BACKUP_SCRIPT)
assert BACKUP_SPEC is not None and BACKUP_SPEC.loader is not None
backup = importlib.util.module_from_spec(BACKUP_SPEC)
BACKUP_SPEC.loader.exec_module(backup)


def test_backup_creates_private_archive_without_exposing_password(monkeypatch, tmp_path):
    database_url = "postgresql://backup-user:secret%3Avalue@db.test:5432/sadwave?sslmode=require"
    monkeypatch.setattr(backup.shutil, "which", lambda name: f"/usr/bin/{name}")
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        assert "PGPASSWORD" not in kwargs["env"]
        if Path(command[0]).name == "pg_dump":
            passfile = Path(kwargs["env"]["PGPASSFILE"])
            assert stat.S_IMODE(passfile.stat().st_mode) == 0o600
            assert passfile.read_text(encoding="utf-8") == (
                "db.test:5432:sadwave:backup-user:secret\\:value\n"
            )
            archive_path = Path(command[command.index("--file") + 1])
            archive_path.write_bytes(b"verified PostgreSQL archive")
        else:
            assert command[1] == "--list"
        return subprocess.CompletedProcess(command, 0, stderr="")

    monkeypatch.setattr(backup.subprocess, "run", run)
    result = backup.create_backup(
        tmp_path / "sadwave.dump",
        {
            "DATABASE_URL": database_url,
            "PGPASSWORD": "ignored-env-password",
        },
    )

    output = tmp_path / "sadwave.dump"
    assert result == {
        "file_name": "sadwave.dump",
        "size_bytes": len(b"verified PostgreSQL archive"),
        "sha256": hashlib.sha256(b"verified PostgreSQL archive").hexdigest(),
    }
    assert output.read_bytes() == b"verified PostgreSQL archive"
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert len(commands) == 2
    assert "--quote-all-identifiers" in commands[0]
    command_text = " ".join(commands[0])
    assert "secret" not in command_text
    assert "ignored-env-password" not in command_text
    assert not list(tmp_path.glob("*.tmp"))


def test_backup_refuses_to_overwrite_existing_destination(monkeypatch, tmp_path):
    output = tmp_path / "existing.dump"
    output.write_bytes(b"keep this archive")
    monkeypatch.setattr(
        backup.shutil,
        "which",
        lambda _name: pytest.fail("PostgreSQL clients must not run for an existing target"),
    )

    with pytest.raises(backup.BackupError, match="refusing to overwrite"):
        backup.create_backup(
            output,
            {"DATABASE_URL": "postgresql://backup-user@localhost/sadwave"},
        )

    assert output.read_bytes() == b"keep this archive"


def test_backup_failure_redacts_credentials_and_removes_partial_archive(monkeypatch, tmp_path):
    database_url = "postgresql://backup-user:private%40value@db.test:5432/sadwave"
    monkeypatch.setattr(backup.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fail_dump(command, **_kwargs):
        Path(command[command.index("--file") + 1]).write_bytes(b"partial archive")
        return subprocess.CompletedProcess(
            command,
            1,
            stderr="could not connect with password private@value (private%40value)",
        )

    monkeypatch.setattr(backup.subprocess, "run", fail_dump)
    output = tmp_path / "failed.dump"

    with pytest.raises(backup.BackupError) as error:
        backup.create_backup(output, {"DATABASE_URL": database_url})

    assert "private@value" not in str(error.value)
    assert "private%40value" not in str(error.value)
    assert not output.exists()
    assert not list(tmp_path.glob(".failed.dump.*.tmp"))


def test_backup_does_not_publish_an_archive_rejected_by_pg_restore(monkeypatch, tmp_path):
    monkeypatch.setattr(backup.shutil, "which", lambda name: f"/usr/bin/{name}")

    def reject_archive(command, **_kwargs):
        if Path(command[0]).name == "pg_dump":
            Path(command[command.index("--file") + 1]).write_bytes(b"invalid archive")
            return subprocess.CompletedProcess(command, 0, stderr="")
        return subprocess.CompletedProcess(
            command, 1, stderr="archive table of contents is invalid"
        )

    monkeypatch.setattr(backup.subprocess, "run", reject_archive)
    output = tmp_path / "invalid.dump"

    with pytest.raises(backup.BackupError, match="pg_restore failed"):
        backup.create_backup(
            output,
            {"DATABASE_URL": "postgresql://backup-user@localhost/sadwave"},
        )

    assert not output.exists()
    assert not list(tmp_path.glob(".invalid.dump.*.tmp"))


def test_backup_uses_password_from_libpq_environment(monkeypatch, tmp_path):
    monkeypatch.setattr(backup.shutil, "which", lambda name: f"/usr/bin/{name}")
    seen_passfile = []
    passfile_paths = []

    def run(command, **kwargs):
        if Path(command[0]).name == "pg_dump":
            passfile = Path(kwargs["env"]["PGPASSFILE"])
            passfile_paths.append(passfile)
            seen_passfile.append(passfile.read_text(encoding="utf-8"))
            Path(command[command.index("--file") + 1]).write_bytes(b"archive")
        return subprocess.CompletedProcess(command, 0, stderr="")

    monkeypatch.setattr(backup.subprocess, "run", run)
    backup.create_backup(
        tmp_path / "env-password.dump",
        {
            "DATABASE_URL": "postgresql://backup-user@db.test:5432/sadwave",
            "PGPASSWORD": "env:password",
        },
    )

    assert seen_passfile == ["db.test:5432:sadwave:backup-user:env\\:password\n"]
    assert len(passfile_paths) == 1
    assert not passfile_paths[0].exists()
