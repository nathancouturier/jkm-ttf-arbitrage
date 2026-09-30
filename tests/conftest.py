"""Make the src layout importable and give tests a private data directory.

pyproject.toml already sets pytest's pythonpath; this repeats it so the suite
also runs when pytest is invoked from another working directory.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pytest  # noqa: E402

from lngarb.sources import base  # noqa: E402


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    """Point every data directory and the manifest at a temporary directory.

    Tests must never touch the committed data/cache, the real data/private or
    data/manifest.json. All four directories are redirected, not only the
    cache, because the Adapter chooses between cache, seed and private by itself
    and a test that redirected one of them would write real bytes into the
    repository through another.
    """
    cache = tmp_path / "cache"
    cache.mkdir()
    monkeypatch.setattr(base, "DATA", tmp_path)
    monkeypatch.setattr(base, "CACHE", cache)
    monkeypatch.setattr(base, "SEED", tmp_path / "seed")
    monkeypatch.setattr(base, "FIXTURES", tmp_path / "fixtures")
    monkeypatch.setattr(base, "PRIVATE", tmp_path / "private")
    monkeypatch.setattr(base, "MANIFEST", tmp_path / "manifest.json")
    return tmp_path
