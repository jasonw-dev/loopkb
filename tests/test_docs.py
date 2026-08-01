"""The shipped documentation must agree with the files that are actually here.

The visual intro is in the repo so it cannot drift out of sync unnoticed (D9), and
the README says so — but the sync rule named a file that had already been renamed.
These tests hold the rule to its own standard: the page exists, nothing points at
the path it used to have, and the README still carries the public URL that every
first-contact link depends on.
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PAGES_URL = "https://jasonw-dev.github.io/loopkb/"
SKIP_DIRS = {".git", ".obsidian", "__pycache__"}
TEXT_SUFFIXES = {".md", ".html", ".py", ".yml", ".yaml", ".json", ".txt"}

# Assembled at runtime: spelling it out would make this file its own counter-example.
OLD_PAGE = "explainer" + ".html"


def text_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(REPO_ROOT.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(REPO_ROOT).parts):
            continue
        files.append(path)
    return files


class DocsTest(unittest.TestCase):
    def test_the_visual_intro_is_served_from_the_pages_root(self) -> None:
        page = REPO_ROOT / "docs" / "index.html"
        self.assertTrue(page.is_file(), "docs/index.html is the GitHub Pages entry point")
        self.assertIn("<title>", page.read_text(encoding="utf-8"))

    def test_nothing_references_the_old_explainer_path(self) -> None:
        offenders = [
            str(path.relative_to(REPO_ROOT))
            for path in text_files()
            if path.name != Path(__file__).name and OLD_PAGE in path.read_text(encoding="utf-8")
        ]
        self.assertEqual(offenders, [], f"stale reference to docs/{OLD_PAGE}")

    def test_readme_carries_the_pages_url(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(PAGES_URL, readme)

    def test_the_instance_readme_stub_carries_it_too(self) -> None:
        # An instance rewrites README.md from this stub; the visual intro must survive it.
        stub = (REPO_ROOT / "_meta" / "README.instance.md").read_text(encoding="utf-8")
        self.assertIn(PAGES_URL, stub)


if __name__ == "__main__":
    unittest.main()
