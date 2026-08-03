#!/usr/bin/env python3
"""loopkb digest verifier — the digest's completeness as a check, not a promise.

Usage:
    python3 scripts/verify_digest.py [vault-path]

Exit 0 when every risky agent commit in this run's window is itemized in
`_meta/digest.md`; exit 1, listing what is missing, when it is not.

Why it exists: in `autonomous` mode the digest is the human's entire view of what
the agent did, so an unreported risky action is a framework violation rather than
a formatting slip (see `docs/design-decisions.md` → D8, D10). Prose asked agents
to itemize; this script checks that they did.

When it runs: the loop writes `_meta/digest.md` LAST but BEFORE the report commit,
so every risky commit already exists and already has a SHA by then. `kb-loop`
runs this between writing the digest and committing the report. Running it again
after the report commit also works — the window then covers the run that just
ended.

Window: the first-parent chain of HEAD back to the previous report commit
(subject starting `[kb-loop] run report`), exclusive. No earlier report commit —
the first run ever — means the whole history.

Risky = an agent commit (subject prefixed `[kb-loop]` or `[kb-save]`) that either

  * deletes or renames a file under a type folder, or
  * changes anything under `_meta/` other than `_meta/digest.md`, or
  * demotes a note's `status:` field (a removed value ranking above the added one).

What this script does NOT see, stated plainly because the digest's credibility
depends on knowing its edges: a **semantic rewrite** of a note's content. To a
diff, an agent rewriting a note's meaning and an agent fixing its formatting are
the same operation, and no heuristic separates them reliably — so that one class
of risky action still rests on the agent's own honesty in writing its digest
line. What backs it up instead is git (every rewrite is a diff on `main`, and
`git revert` undoes it whenever it is noticed) and the refine stage's freshness
check, which re-reads the oldest curated/evergreen notes and demotes what no
longer holds. Treat a clean exit as "the four mechanical classes are accounted
for", not as "the digest is complete".

Merge commits are skipped: in `reviewed` mode agent work reaches `main` through a
human-approved merge, which is a review, not an unreported action.

Reviewed-mode prerequisite — MRs must land as merge commits. That skip is how a
reviewed action is recognised, so it is also the mode's one requirement on the
platform: configure `kb-loop/*` MRs to merge with a merge commit. Squash-merge and
rebase-merge produce a single-parent commit on `main`'s first-parent chain that
still carries the `[kb-loop]` prefix, and nothing in that commit distinguishes
human-approved work from an action that bypassed review — so this script reports
it as missing from the digest. That is a known limitation, documented rather than
detected: no heuristic separates a squashed MR from a direct commit, and guessing
would silence the tripwire this verifier exists to be. An instance that cannot
change its merge method must itemize squashed MRs in the digest exactly as if they
were direct commits.

Reviewed-mode note: in `reviewed` mode a risky agent commit should not sit on the
first-parent chain of `main` at all — it belongs on a `kb-loop/*` branch behind an
MR. This verifier flagging one there is therefore correct behaviour and a useful
tripwire: it means something bypassed the MR channel. Itemizing it in the digest
silences the verifier but does not make the bypass legitimate.

Python 3 standard library only; all git access goes through subprocess.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

AGENT_PREFIXES = ("[kb-loop]", "[kb-save]")
REPORT_SUBJECT = "[kb-loop] run report"
DIGEST_PATH = "_meta/digest.md"
META_DIR = "_meta"

STATUS_RANK = {"raw": 0, "curated": 1, "evergreen": 2}

SHA_RE = re.compile(r"\b[0-9a-fA-F]{7,40}\b")
STATUS_DIFF_RE = re.compile(r"^([-+])status:\s*(.+?)\s*$")
DIFF_FILE_RE = re.compile(r"^\+\+\+ b/(.*)$")
UNIT = "\x1f"


# --------------------------------------------------------------------------- #
# git plumbing
# --------------------------------------------------------------------------- #


def git(repo: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip("\n")


def first_parent_chain(repo: Path) -> list[tuple[str, str, int]]:
    """(sha, subject, parent count) newest-first along HEAD's first-parent chain."""
    out = git(repo, "log", "--first-parent", f"--format=%H{UNIT}%s{UNIT}%P", "HEAD", check=False)
    commits: list[tuple[str, str, int]] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        sha, _, rest = line.partition(UNIT)
        subject, _, parents = rest.partition(UNIT)
        commits.append((sha, subject, len(parents.split())))
    return commits


def name_status(repo: Path, sha: str) -> list[tuple[str, list[str]]]:
    out = git(repo, "show", "--first-parent", "-M", "--name-status", "--format=", sha)
    entries: list[tuple[str, list[str]]] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        entries.append((parts[0], parts[1:]))
    return entries


def status_demotions(repo: Path, sha: str) -> list[tuple[str, str, str]]:
    """(file, old status, new status) for every demotion in the commit's diff."""
    out = git(repo, "show", "--first-parent", "-M", "-U0", "--format=", sha)
    removed: dict[str, list[str]] = {}
    added: dict[str, list[str]] = {}
    current = ""
    for line in out.splitlines():
        if line.startswith("+++"):
            # `+++ /dev/null` means this hunk's file is being deleted: reset the tracker
            # rather than leaving the previous file's name in it, or the deleted file's
            # `-status:` lines get attributed to whichever file came before it.
            file_match = DIFF_FILE_RE.match(line)
            current = file_match.group(1) if file_match else ""
            continue
        if line.startswith("---"):
            continue
        match = STATUS_DIFF_RE.match(line)
        if not match or not current:
            continue
        bucket = removed if match.group(1) == "-" else added
        bucket.setdefault(current, []).append(match.group(2).strip().strip("\"'"))

    demotions: list[tuple[str, str, str]] = []
    for path in removed:
        pairs = zip(removed[path], added.get(path, []))
        for old, new in pairs:
            if old in STATUS_RANK and new in STATUS_RANK and STATUS_RANK[old] > STATUS_RANK[new]:
                demotions.append((path, old, new))
    return demotions


# --------------------------------------------------------------------------- #
# vault model
# --------------------------------------------------------------------------- #


def type_folders(vault: Path) -> set[str]:
    """Type folders are defined by the templates the instance ships (as in lint.py)."""
    templates = vault / "_meta" / "templates"
    if not templates.is_dir():
        return set()
    return {p.stem for p in templates.glob("*.md")}


def digest_text(vault: Path) -> str:
    path = vault / DIGEST_PATH
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def mentioned(digest: str, full_sha: str) -> bool:
    """True when the digest names this commit by any abbreviation git would accept."""
    lowered = full_sha.lower()
    return any(lowered.startswith(token.lower()) for token in SHA_RE.findall(digest))


# --------------------------------------------------------------------------- #
# analysis
# --------------------------------------------------------------------------- #


def window(commits: list[tuple[str, str, int]]) -> list[tuple[str, str, int]]:
    """Commits back to — but excluding — the previous report commit.

    HEAD itself is never treated as the marker: when the verifier runs after the
    report commit, the window must still cover the run that report describes.
    """
    for index, (_, subject, _) in enumerate(commits):
        if index > 0 and subject.startswith(REPORT_SUBJECT):
            return commits[:index]
    return commits


def is_agent_commit(subject: str) -> bool:
    return subject.startswith(AGENT_PREFIXES)


def risky_reasons(repo: Path, sha: str, folders: set[str]) -> list[str]:
    reasons: list[str] = []

    def add(reason: str) -> None:
        if reason not in reasons:
            reasons.append(reason)

    for status, paths in name_status(repo, sha):
        code = status[0]
        for path in paths:
            if path.split("/")[0] == META_DIR and path != DIGEST_PATH:
                add(f"_meta/ rule change: {path}")
        in_type_folder = [p for p in paths if p.split("/")[0] in folders]
        if code == "D" and in_type_folder:
            add(f"deleted {in_type_folder[0]}")
        elif code == "R" and in_type_folder:
            add(f"renamed {paths[0]} -> {paths[-1]}")

    for path, old, new in status_demotions(repo, sha):
        add(f"demoted {path}: {old} -> {new}")

    return reasons


def verify(vault: Path) -> tuple[int, list[str]]:
    """Returns (exit code, output lines)."""
    commits = first_parent_chain(vault)
    if not commits:
        return 0, ["verify-digest: no commits yet — nothing to verify"]

    scanned = window(commits)
    folders = type_folders(vault)
    digest = digest_text(vault)

    risky: list[tuple[str, str, list[str]]] = []
    for sha, subject, parents in scanned:
        if parents > 1 or not is_agent_commit(subject):
            continue
        reasons = risky_reasons(vault, sha, folders)
        if reasons:
            risky.append((sha, subject, reasons))

    missing = [entry for entry in risky if not mentioned(digest, entry[0])]
    if missing:
        lines = []
        for sha, subject, reasons in reversed(missing):
            short = git(vault, "rev-parse", "--short", sha)
            lines.append(f"missing from digest: {short} {subject}")
            lines.append(f"  risky because: {'; '.join(reasons)}")
        lines.append(
            f"\nverify-digest: {len(missing)} risky action(s) not itemized in {DIGEST_PATH} "
            f"({len(risky)} risky of {len(scanned)} commit(s) in the window). "
            "Add a line per action with its short SHA, then rerun."
        )
        return 1, lines

    marker = "since the previous run report" if len(scanned) < len(commits) else "over the full history"
    return 0, [
        f"verify-digest: clean — {len(risky)} risky action(s) across {len(scanned)} commit(s) "
        f"{marker}, all itemized in {DIGEST_PATH}"
    ]


def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    vault = Path(argv[1]).resolve() if len(argv) > 1 else Path(__file__).resolve().parent.parent
    if not vault.is_dir():
        print(f"{vault}: not a directory", file=sys.stderr)
        return 1
    if subprocess.run(
        ["git", "-C", str(vault), "rev-parse", "--git-dir"], capture_output=True, text=True
    ).returncode != 0:
        print(f"{vault}: not inside a git repository", file=sys.stderr)
        return 1

    code, lines = verify(vault)
    for line in lines:
        print(line)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
