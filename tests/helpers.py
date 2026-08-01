"""Shared fixtures for the loopkb test suite — standard library only.

Not a test module (the discovery pattern is `test*.py`), just the vault and git
scaffolding the three test modules share.

Run the suite from the repo root:

    python3 -m unittest discover -s tests
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"

TYPE_FOLDERS = ("troubleshooting", "decisions", "guides", "references", "meetings")

CLEAN_NOTE = """---
type: guides
domains: [ci-cd]
created: 2026-08-01
source: inbox
status: curated
---
# {title}

Body text.

## Related
- [[{link}]]
"""


def isolated_env(home: Path) -> dict[str, str]:
    """A git environment that cannot see the developer's own config or identity."""
    env = dict(os.environ)
    env.update(
        {
            "HOME": str(home),
            "GIT_CONFIG_GLOBAL": str(home / ".gitconfig"),
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Test Human",
            "GIT_AUTHOR_EMAIL": "human@example.invalid",
            "GIT_COMMITTER_NAME": "Test Human",
            "GIT_COMMITTER_EMAIL": "human@example.invalid",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    for leaked in ("KB_LOOP_HOLDER", "KB_LOOP_SESSION"):
        env.pop(leaked, None)
    return env


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def make_vault(root: Path, vocabulary: tuple[str, ...] = ("ci-cd", "tooling")) -> Path:
    """A minimal but complete loopkb vault: instance config, templates, type folders."""
    write(
        root / "_meta" / "instance.md",
        "# Instance Configuration\n\n"
        "## Identity\n\n- **Note body language**: English\n\n"
        "## Domain tag vocabulary (closed)\n\n"
        + "".join(f"- `{tag}`\n" for tag in vocabulary),
    )
    write(root / "_meta" / "taxonomy.md", "# Taxonomy\n\nFramework rules.\n")
    write(root / "_meta" / "digest.md", "# Run digest\n\nNo runs yet.\n")
    for folder in TYPE_FOLDERS:
        write(root / "_meta" / "templates" / f"{folder}.md", f"---\ntype: {folder}\n---\n# Title\n")
        write(root / folder / ".gitkeep", "")
    write(root / "_inbox" / ".gitkeep", "")
    return root


def add_clean_pair(vault: Path) -> None:
    """Two mutually linked `curated` notes — the baseline that must lint clean."""
    write(vault / "guides" / "alpha-note.md", CLEAN_NOTE.format(title="Alpha", link="beta-note"))
    write(vault / "guides" / "beta-note.md", CLEAN_NOTE.format(title="Beta", link="alpha-note"))


class TempDirTestCase(unittest.TestCase):
    """Gives every test a private temp dir and a git environment isolated from HOME."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="loopkb-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.env = isolated_env(self.home)

    def git(self, repo: Path, *args: str, check: bool = True) -> str:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True, env=self.env
        )
        if check and proc.returncode != 0:
            self.fail(f"git {' '.join(args)} failed in {repo}: {proc.stderr.strip()}")
        return proc.stdout.strip()

    def script(self, name: str, *args: str, cwd: Path | None = None, env: dict | None = None):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / name), *args],
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
            env=env or self.env,
        )
