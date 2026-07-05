"""Shared pytest fixtures for crash_recovery tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    """A throw-away DB path inside pytest's tmp_path."""
    return tmp_path / "crash-recovery.db"
