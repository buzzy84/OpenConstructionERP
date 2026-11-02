"""Regression tests for updating modules installed from ZIP archives."""
from __future__ import annotations

import asyncio
import io
import json
import zipfile
from pathlib import Path

import pytest

from app.core import module_package as pkg


def archive(version: str) -> bytes:
    manifest = (
        "from app.core.module_loader import ModuleManifest\n"
        "manifest = ModuleManifest(\n"
        "    name='oe_zipdemo',\n"
        f"    version='{version}',\n"
        "    display_name='ZIP demo',\n"
        "    category='community',\n"
        "    depends=[],\n"
        ")\n"
    )
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("zipdemo/__init__.py", "")
        zf.writestr("zipdemo/manifest.py", manifest)
        zf.writestr("zipdemo/router.py", "from fastapi import APIRouter\nrouter = APIRouter()\n")
    return data.getvalue()


@pytest.fixture
def old_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "modules"
    target = root / "zipdemo"
    target.mkdir(parents=True)
    (target / "__init__.py").write_text("")
    (target / "old.txt").write_text("preserved")
    (target / pkg.MARKER_FILE).write_text(json.dumps({
        "name": "oe_zipdemo", "version": "1.0.0", "archive_sha256": "old", "ui": None,
    }))
    monkeypatch.setenv("OE_RUNTIME_MODULES_DIR", str(root))
    monkeypatch.setattr(pkg, "platform_version", lambda: "18.9.0")
    return target


def inspect_new(data: bytes) -> pkg.Preview:
    return pkg.inspect_archive(data, known_modules={"oe_zipdemo": "community"})


def test_newer_zip_is_reviewable_as_update(old_package: Path) -> None:
    preview = inspect_new(archive("1.1.0"))
    assert preview.installable, preview.checks
    assert preview.action == "update"
    assert preview.installed_version == "1.0.0"
    assert "manifest.update_restart" in {c.rule_id for c in preview.checks}


@pytest.mark.parametrize("version", ["1.0.0", "0.9.9"])
def test_same_or_older_version_cannot_replace_module(old_package: Path, version: str) -> None:
    preview = inspect_new(archive(version))
    assert not preview.installable
    assert "manifest.update_version" in {c.rule_id for c in preview.checks}


def test_unmanaged_module_cannot_be_overwritten(old_package: Path) -> None:
    (old_package / pkg.MARKER_FILE).unlink()
    preview = inspect_new(archive("2.0.0"))
    assert not preview.installable
    assert "manifest.collision" in {c.rule_id for c in preview.checks}


def test_upgrade_retains_old_files_and_is_not_hot_loaded(old_package: Path) -> None:
    data = archive("1.1.0")
    preview = inspect_new(data)
    result = asyncio.run(pkg._upgrade("deadbeef", data, preview, actor="admin"))
    assert result["status"] == "restart_required"
    assert pkg.read_marker(old_package)["version"] == "1.1.0"
    backup = old_package.parent / ".oe-rollback" / "zipdemo"
    assert (backup / "old.txt").read_text() == "preserved"
    assert pkg.read_marker(backup)["version"] == "1.0.0"
    assert [m["name"] for m in pkg.installed_packages()] == ["oe_zipdemo"]
