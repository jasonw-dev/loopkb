"""The shipped documentation must agree with the files that are actually here.

The visual intro is in the repo so it cannot drift out of sync unnoticed (D9), and
the README says so — but the sync rule named a file that had already been renamed.
These tests hold the rule to its own standard: the page exists, nothing points at
the path it used to have, and the README still carries the public URL that every
first-contact link depends on.

These assertions are about **framework** files, and this suite also runs in every
instance's CI (GETTING-STARTED.md → "Verify after every merge"). So they must never
fail an instance for doing what the framework tells it to do: the note namespace is
excluded from the scan, because a note is free to mention anything, and the README-URL
check applies only while README.md is still the framework's own — rewriting it is a
documented step of instantiation, and the stub test below is what covers the URL after
that.
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PAGES_URL = "https://jasonw-dev.github.io/loopkb/"
SKIP_DIRS = {".git", ".obsidian", "__pycache__"}
TEXT_SUFFIXES = {".md", ".html", ".py", ".yml", ".yaml", ".json", ".txt"}
# The framework README's own title. An instance replaces it (_meta/README.instance.md).
FRAMEWORK_README_TITLE = "# loopkb"

# Assembled at runtime: spelling it out would make this file its own counter-example.
OLD_PAGE = "explainer" + ".html"


def note_namespace() -> set[str]:
    """The folders whose content belongs to the instance, not to the framework.

    The type folders (defined by the templates, exactly as `scripts/lint.py` derives
    them) plus `_inbox/`. Whatever a note says is the vault's business — an instance
    that files a troubleshooting note about a stale `explainer.html` link must not fail
    the framework's own anti-drift test.
    """
    templates = REPO_ROOT / "_meta" / "templates"
    folders = {path.stem for path in templates.glob("*.md")} if templates.is_dir() else set()
    return folders | {"_inbox"}


def text_files() -> list[Path]:
    """Framework text files: everything outside the note namespace and the skip list."""
    excluded = note_namespace()
    files: list[Path] = []
    for path in sorted(REPO_ROOT.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        rel = path.relative_to(REPO_ROOT)
        if any(part in SKIP_DIRS for part in rel.parts) or rel.parts[0] in excluded:
            continue
        files.append(path)
    return files


class DocsTest(unittest.TestCase):
    def test_the_visual_intro_is_served_from_the_pages_root(self) -> None:
        page = REPO_ROOT / "docs" / "index.html"
        self.assertTrue(page.is_file(), "docs/index.html is the GitHub Pages entry point")
        self.assertIn("<title>", page.read_text(encoding="utf-8"))

    def test_nothing_references_the_old_explainer_path(self) -> None:
        # errors="ignore": this runs in every instance's CI, where a file with one of
        # these suffixes may not be UTF-8. A stale path is what is under test; an
        # instance's encoding is not, and a decode error here would fail their CI.
        offenders = [
            str(path.relative_to(REPO_ROOT))
            for path in text_files()
            if path.name != Path(__file__).name
            and OLD_PAGE in path.read_text(encoding="utf-8", errors="ignore")
        ]
        self.assertEqual(offenders, [], f"stale reference to docs/{OLD_PAGE}")

    def test_readme_carries_the_pages_url(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        if not readme.lstrip().startswith(FRAMEWORK_README_TITLE + "\n"):
            # An instance rewrote README.md — the documented, expected thing. The URL is
            # carried through that rewrite by _meta/README.instance.md, asserted below.
            self.skipTest("README.md is instance-owned here")
        self.assertIn(PAGES_URL, readme)

    def test_the_instance_readme_stub_carries_it_too(self) -> None:
        # An instance rewrites README.md from this stub; the visual intro must survive it.
        stub = (REPO_ROOT / "_meta" / "README.instance.md").read_text(encoding="utf-8")
        self.assertIn(PAGES_URL, stub)

    def test_the_framework_readme_marker_discriminates(self) -> None:
        """The skip above is only safe while the marker tells the two READMEs apart."""
        stub = (REPO_ROOT / "_meta" / "README.instance.md").read_text(encoding="utf-8")
        self.assertNotIn(f"\n{FRAMEWORK_README_TITLE}\n", stub)

    def test_the_scan_leaves_the_note_namespace_alone(self) -> None:
        """A note may say anything; these are assertions about framework files."""
        excluded = note_namespace()
        self.assertIn("_inbox", excluded)
        self.assertTrue(excluded - {"_inbox"}, "the type folders come from _meta/templates/")
        scanned = {path.relative_to(REPO_ROOT).parts[0] for path in text_files()}
        self.assertEqual(scanned & excluded, set())


if __name__ == "__main__":
    unittest.main()
