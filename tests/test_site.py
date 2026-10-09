"""The page's shell: index.html versions every file at its bytes, and the page's checks pass."""

from __future__ import annotations

import shutil
import subprocess

import pytest

from lngarb import versions
from lngarb.sources import base

ROOT = base.REPO_ROOT
node = shutil.which("node")


def test_index_html_versions_every_module_artifact_and_stylesheet_at_its_bytes():
    assert versions.crlf_entries() == [], "rewrite these with LF line endings"
    assert versions.stale_entries() == [], "run PYTHONPATH=src python -m lngarb.versions"


def test_a_stale_hash_is_reported(tmp_path):
    for folder in ("src", "data", "styles"):
        (tmp_path / folder).mkdir()
    (tmp_path / "src" / "ui.js").write_bytes(b"export {};\n")
    (tmp_path / "data" / "now.json").write_bytes(b"{}\n")
    (tmp_path / "styles" / "tokens.css").write_bytes(b":root {}\n")
    (tmp_path / "index.html").write_bytes((
        versions.BLOCK_START + "\n" + versions.BLOCK_END + "\n"
        '<link rel="stylesheet" href="styles/tokens.css">\n<script type="module" src="src/ui.js"></script>\n'
    ).encode("utf-8"))
    assert versions.stale_entries(tmp_path)
    assert versions.write(tmp_path) is True
    assert versions.stale_entries(tmp_path) == []
    assert versions.write(tmp_path) is False
    (tmp_path / "data" / "now.json").write_bytes(b'{"a": 1}\n')
    assert versions.stale_entries(tmp_path) == ["data/now.json"]


@pytest.mark.skipif(node is None, reason="node is not installed")
@pytest.mark.parametrize("tool", ["check-paths.mjs", "check-literals.mjs", "check-styles.mjs", "validate-artifacts.mjs"])
def test_the_page_checks_pass(tool):
    run = subprocess.run([node, str(ROOT / "tools" / tool)], capture_output=True, text=True, cwd=ROOT)
    assert run.returncode == 0, run.stdout + run.stderr


def test_no_text_file_holds_a_control_character():
    """A tab, a line feed or a carriage return, and nothing else below a space:
    a stray control character prints as nothing and breaks a pattern silently."""
    run = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], capture_output=True,
                         text=True, cwd=ROOT)
    bad = []
    for name in run.stdout.split():
        path = ROOT / name
        if name.startswith(("vendor/", "tests/fixtures/")) or not path.is_file():
            continue
        if path.suffix.lower() not in {".py", ".js", ".mjs", ".css", ".html", ".json", ".md", ".csv", ".toml", ".txt", ".yml", ""}:
            continue
        data = path.read_bytes()
        if any(byte < 32 and byte not in (9, 10, 13) for byte in data):
            bad.append(name)
    assert bad == []


def test_a_publisher_whose_terms_forbid_links_is_linked_from_nothing_the_page_reads():
    """JOGMEC's terms forbid linking to its website without its permission.

    Its address stays in the registry, for the code that reads it privately,
    and its domain appears in nothing the page loads or links to.
    """
    from urllib.parse import urlsplit

    from lngarb.config import SOURCES

    # the registrable domain, so a link to any of the publisher's hosts fails
    domains = {".".join(urlsplit(s.page_url).hostname.split(".")[-3:]) for s in SOURCES.values() if not s.linkable}
    assert domains == {"jogmec.go.jp"}
    page = [ROOT / "index.html", ROOT / "README.md", ROOT / "NOTICE",
            *sorted((ROOT / "data").glob("*.json")), *sorted((ROOT / "src").glob("*.js"))]
    for path in page:
        text = path.read_text(encoding="utf-8")
        for domain in domains:
            assert domain not in text, "%s carries %s" % (path.relative_to(ROOT), domain)


def test_the_provenance_row_of_an_unlinkable_publisher_has_no_page_url():
    import json

    rows = json.loads((ROOT / "data" / "provenance.json").read_text(encoding="utf-8"))["series"]
    row = next(r for r in rows if r["id"] == "jogmec_spot_lng_monthly")
    assert row["page_url"] is None
    entries = base.manifest_read()["series"]
    entry = next(e for e in entries if e["series"] == "jogmec_spot_lng_monthly")
    assert (entry["linkable"], entry["url"], entry["page_url"]) == (False, None, None)
