#!/usr/bin/env python3
"""Structural checks for an EyeOnian document repo (privacy / eula / release-notes).

This file is the canonical copy. It is mirrored into each document repo at
tools/check_docs.py and run by that repo's CI on every push -- hand-edits happen
there, so that is where they must be caught.

Checks (numbered as in project-docs/Offline-Docs-Implementation-Brief.md section 8):

  3. The repo root serves the current document, byte-equal to the newest /vN.N/.
     The root URL is what the Play listing and App Store Connect point at, so it
     must keep serving the document itself -- never an index.
  4. No file under an existing /vN.N/ directory has been modified. Released
     versions are frozen; corrections go into a new version directory.
  7. archive/index.md references every /vN.N/ directory in the repo.

Check 1 (vendored == hosted) runs in the app repo instead: it is the side that
holds the vendored copy and the manifest, and reaching across repos would need a
cross-repo token for no added safety -- check 4 already catches the hand-edit
this repo can cause.

Usage:
    python3 tools/check_docs.py            # checks 3 and 7
    python3 tools/check_docs.py --base ORIGIN_SHA   # adds check 4
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE_START = "<!-- store-links:start -->"
STORE_END = "<!-- store-links:end -->"
# A pinned /vN.N/ page states its own version and links back to the archive
# (brief 7.2). That banner is page furniture, not document text, so it is
# stripped before comparing or hashing -- otherwise it would make the pinned
# copy differ from the root by construction and check 3 could never pass.
PIN_START = "<!-- pinned-header:start -->"
PIN_END = "<!-- pinned-header:end -->"

failures: list[str] = []


def fail(check: int, msg: str) -> None:
    failures.append(f"check {check}: {msg}")


def normalize(md: str) -> str:
    """Canonical document body -- must match tools/vendor_legal.py:normalize()."""
    if md.startswith("---"):
        m = re.match(r"^---\r?\n.*?^---\r?\n", md, re.DOTALL | re.MULTILINE)
        if not m:
            m = re.match(r"^---\r?\n---\r?\n", md)
        if m:
            md = md[m.end():].lstrip("\n")
    for start, end in ((STORE_START, STORE_END), (PIN_START, PIN_END)):
        if start in md:
            md = re.sub(re.escape(start) + r".*?" + re.escape(end), "", md,
                        flags=re.DOTALL)
    return md.strip() + "\n"


def version_dirs() -> list[Path]:
    dirs = [p for p in ROOT.glob("v*") if p.is_dir() and re.fullmatch(r"v\d+\.\d+", p.name)]
    return sorted(dirs, key=lambda p: tuple(int(n) for n in p.name[1:].split(".")))


def root_document() -> Path | None:
    for name in ("index.md", "README.md"):
        p = ROOT / name
        if p.exists():
            return p
    return None


def check_root_matches_newest() -> None:
    versions = version_dirs()
    if not versions:
        fail(3, "no /vN.N/ directory exists")
        return
    newest = versions[-1]
    pinned = newest / "index.md"
    doc = root_document()
    if doc is None:
        fail(3, "no root document (index.md or README.md)")
        return
    if not pinned.exists():
        fail(3, f"{newest.name}/index.md is missing")
        return
    if normalize(doc.read_text()) != normalize(pinned.read_text()):
        fail(3, f"root {doc.name} does not match {newest.name}/index.md "
                f"(the root must be a copy of the newest version)")


def check_frozen_versions(base: str) -> None:
    proc = subprocess.run(
        ["git", "diff", "--name-only", base, "HEAD"],
        capture_output=True, text=True, cwd=ROOT,
    )
    if proc.returncode != 0:
        fail(4, f"could not diff against {base}: {proc.stderr.strip()}")
        return
    touched = [
        f for f in proc.stdout.split("\n")
        if re.match(r"^v\d+\.\d+/", f.strip())
    ]
    # A brand-new version directory is fine; modifying an existing one is not.
    added = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=A", base, "HEAD"],
        capture_output=True, text=True, cwd=ROOT,
    ).stdout.split("\n")
    modified = [f for f in touched if f not in added]
    if modified:
        fail(4, "released version directories are frozen; these were modified: "
                + ", ".join(modified)
                + ". Publish a correction as a NEW version directory instead.")


def check_archive_lists_all() -> None:
    archive = ROOT / "archive" / "index.md"
    versions = version_dirs()
    if not versions:
        return  # already reported by check 3
    if not archive.exists():
        fail(7, "archive/index.md is missing")
        return
    text = archive.read_text()
    missing = [v.name for v in versions if v.name not in text]
    if missing:
        fail(7, "archive/index.md does not list: " + ", ".join(missing))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", help="git ref to diff against for check 4")
    args = ap.parse_args()

    check_root_matches_newest()
    check_archive_lists_all()
    if args.base:
        check_frozen_versions(args.base)

    if failures:
        print("Document repo checks FAILED:\n")
        for f in failures:
            print(f"  ✗ {f}")
        print("\nSee the implementation brief, section 7, for the rules these enforce.")
        return 1
    print("✓ document repo checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
