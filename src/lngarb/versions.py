"""Content hashes in index.html, so a deploy changes every URL whose bytes changed.

    PYTHONPATH=src python -m lngarb.versions            rewrite index.html if stale
    PYTHONPATH=src python -m lngarb.versions --check    fail naming each stale entry

WHY. GitHub Pages serves every file with a short max age and no version in its
name. The site is an ES module graph plus data/*.json, all fetched by plain
relative URLs, so after a deploy a browser or the CDN in front of Pages can hand
the page a mixed set: yesterday's src/now.js with today's data/now.json, and an
old module reading a new artifact can print a wrong number without any error.
The pattern is the sibling crack-spread-study's.

WHAT, with no build step and no bundler. This rewrites three things in
index.html and nothing else, each from the bytes on disk:

  1  an import map between the markers BLOCK_START and BLOCK_END, mapping every
     module in src/ and every artifact in data/ to the same path with
     ?v=<the first HASH_LENGTH hex digits of its sha256>. Every relative import
     between modules resolves through the map, so a module whose bytes changed
     gets a new URL even when the module importing it did not. The artifacts
     are in the same map because src/state.js asks for them through
     import.meta.resolve, which applies it.
  2  the ?v= on each stylesheet link to styles/*.css.
  3  the ?v= on the entry module, src/ui.js, which a script tag loads directly.

index.html itself carries no version: it names all the others, and a stale copy
of it names a consistent old set. What a query string cannot do (Pages ignores
it when choosing the bytes) is covered by src/state.js, which refuses any
artifact whose schema_version or name it does not know.

BYTE IDEMPOTENT. The map is sorted, written with LF and no timestamp; a second
run over an unchanged tree rewrites nothing.

THE HASH IS OF THE BYTES ON DISK. .gitattributes stores every text file with LF.
A file written with CRLF on Windows keeps git status clean while its hash in
index.html matches only that machine; crlf_entries is the guard, and --check
fails on it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX = "index.html"

#: Hex digits of the sha256 kept in a URL: 48 bits.
HASH_LENGTH = 12

BLOCK_START = "<!-- build:versions, written by lngarb.versions from the bytes on disk; do not edit by hand -->"
BLOCK_END = "<!-- /build:versions -->"

#: What is versioned, as (directory, suffix). Top level of each directory only:
#: src/lngarb is the Python package and never reaches the browser, and
#: data/cache, data/seed and data/fixtures are not read by the page.
MODULE_DIRECTORY = ("src", ".js")
ARTIFACT_DIRECTORY = ("data", ".json")
STYLE_DIRECTORY = ("styles", ".css")
ENTRY_MODULE = "src/ui.js"


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:HASH_LENGTH]


def _files(root: Path, directory: str, suffix: str) -> list[str]:
    folder = root / directory
    if not folder.is_dir():
        return []
    return sorted(
        "%s/%s" % (directory, path.name)
        for path in folder.iterdir()
        if path.is_file() and path.name.endswith(suffix)
    )


def hashes(root: Path = REPO_ROOT) -> dict[str, str]:
    """Every versioned file, by its path relative to index.html, to its hash."""
    out: dict[str, str] = {}
    for directory, suffix in (MODULE_DIRECTORY, ARTIFACT_DIRECTORY, STYLE_DIRECTORY):
        for relative in _files(root, directory, suffix):
            out[relative] = content_hash((root / relative).read_bytes())
    return out


def crlf_entries(root: Path = REPO_ROOT) -> list[str]:
    """Each versioned file whose bytes on disk carry a CRLF. Empty when clean."""
    return [relative for relative in sorted(hashes(root)) if b"\r\n" in (root / relative).read_bytes()]


def versioned(relative: str, digest: str) -> str:
    return "%s?v=%s" % (relative, digest)


def import_map(table: Mapping[str, str]) -> str:
    """The import map block, markers included, for the modules and artifacts."""
    imports = {
        "./" + relative: "./" + versioned(relative, digest)
        for relative, digest in sorted(table.items())
        if relative.startswith(MODULE_DIRECTORY[0] + "/") or relative.startswith(ARTIFACT_DIRECTORY[0] + "/")
    }
    body = json.dumps({"imports": imports}, indent=2, ensure_ascii=True, sort_keys=True)
    return "\n".join([BLOCK_START, '<script type="importmap">', body, "</script>", BLOCK_END])


_BLOCK = re.compile(re.escape(BLOCK_START) + r".*?" + re.escape(BLOCK_END), re.S)
_STYLE_LINK = re.compile(r'href="(styles/[\w.-]+\.css)(?:\?v=[0-9a-f]*)?"')
_ENTRY = re.compile(r'src="(' + re.escape(ENTRY_MODULE) + r')(?:\?v=[0-9a-f]*)?"')


class VersionsError(ValueError):
    """index.html has no place to write the versions into."""


def render(html: str, table: Mapping[str, str]) -> str:
    """index.html with the import map, the stylesheet links and the entry module
    carrying the hashes in `table`. Raises VersionsError when a marker, the entry
    module or a stylesheet named in the table has nowhere to go."""
    if html.count(BLOCK_START) != 1 or html.count(BLOCK_END) != 1:
        raise VersionsError("%s must hold the markers %r and %r exactly once each" % (INDEX, BLOCK_START, BLOCK_END))
    out = _BLOCK.sub(lambda _: import_map(table), html)

    def style(match: re.Match) -> str:
        relative = match.group(1)
        if relative not in table:
            raise VersionsError("%s links %s, which does not exist" % (INDEX, relative))
        return 'href="%s"' % versioned(relative, table[relative])

    out = _STYLE_LINK.sub(style, out)
    if len(_ENTRY.findall(out)) != 1:
        raise VersionsError("%s must load %s exactly once" % (INDEX, ENTRY_MODULE))
    return _ENTRY.sub(lambda m: 'src="%s"' % versioned(m.group(1), table[m.group(1)]), out)


def expected_index(root: Path = REPO_ROOT) -> str:
    return render((root / INDEX).read_bytes().decode("utf-8"), hashes(root))


def write(root: Path = REPO_ROOT) -> bool:
    """Rewrite index.html if its versions are stale. Returns True when written."""
    path = root / INDEX
    current = path.read_bytes()
    wanted = expected_index(root).encode("utf-8")
    if current == wanted:
        return False
    path.write_bytes(wanted)
    return True


def stale_entries(root: Path = REPO_ROOT) -> list[str]:
    """Each versioned path whose hash in index.html is not its bytes' hash, or
    that index.html does not version at all. Empty when index.html is fresh."""
    html = (root / INDEX).read_bytes().decode("utf-8")
    try:
        wanted = render(html, hashes(root))
    except VersionsError as exc:
        return [str(exc)]
    if wanted == html:
        return []
    out = [relative for relative, digest in hashes(root).items() if versioned(relative, digest) not in html]
    return out or ["index.html differs from its rebuild outside the versioned URLs"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if index.html is stale or a versioned file has CRLF")
    args = parser.parse_args(argv)
    crlf = crlf_entries()
    if crlf:
        print("versioned files with CRLF line endings, rewrite them with LF: " + ", ".join(crlf))
        return 1
    if args.check:
        stale = stale_entries()
        if stale:
            print("index.html is stale for: " + ", ".join(stale) + "; run PYTHONPATH=src python -m lngarb.versions")
            return 1
        print("ok index.html versions every module, artifact and stylesheet at its bytes")
        return 0
    print("index.html rewritten" if write() else "index.html already current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
