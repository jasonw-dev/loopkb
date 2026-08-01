#!/usr/bin/env python3
"""loopkb linter — the executable definition of the vault schema.

Usage:
    python3 scripts/lint.py [vault-path]

Exit code 0 when the vault is clean, 1 when it has violations.
Every violation is printed as one `path: problem` line, relative to the vault root.

Scope: the type folders only (one folder per template in `_meta/templates/`).
`_meta/`, `_inbox/`, `_attachments/`, `.obsidian/`, `integrations/` and other
framework directories are never schema-checked; `_inbox/` still participates in
the basename index so wikilink resolution and uniqueness see the whole vault.

Python 3 standard library only — no third-party dependencies, no YAML parser.
The frontmatter dialect used by this vault is deliberately small enough to
hand-parse: `key: scalar`, `key: [a, b]`, or a `-` block list.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

STATUSES = ("raw", "curated", "evergreen")
SOURCES = ("inbox", "conversation", "meeting")
REQUIRED_KEYS = ("type", "domains", "created", "source", "status")

# Directories that are never part of the note namespace.
SKIP_DIRS = {
    ".git",
    ".github",
    ".obsidian",
    ".claude",
    ".claude-plugin",
    "_meta",
    "_attachments",
    "docs",
    "integrations",
    "scripts",
    "tests",
}

# Collected into the basename index but deliberately schema-free — no warning.
NON_TYPE_FOLDERS = {"_inbox"}

KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATED_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$")
WIKILINK_RE = re.compile(r"\[\[([^\]\|#]+)")
# A vocabulary entry is a Markdown list item; everything after an em/en-dash or
# ` - ` separator is a human annotation the parser ignores.
VOCAB_ITEM_RE = re.compile(r"^[-*]\s+(\S.*)$")
VOCAB_ANNOTATION_RE = re.compile(r"\s+[—–-]\s+")
VOCAB_BACKTICK_RE = re.compile(r"^`([^`]*)`")


# --------------------------------------------------------------------------- #
# parsing helpers
# --------------------------------------------------------------------------- #


def strip_comments(text: str) -> str:
    """Remove HTML comment blocks — instance files carry examples inside them."""
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def parse_scalar(raw: str) -> str:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        raw = raw[1:-1]
    return raw.strip()


def parse_inline_list(raw: str) -> list[str]:
    inner = raw.strip()[1:-1].strip()
    if not inner:
        return []
    return [parse_scalar(part) for part in inner.split(",") if parse_scalar(part)]


def split_frontmatter(text: str) -> tuple[list[str] | None, str]:
    """Return (frontmatter lines, body). Frontmatter is None when absent."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], "\n".join(lines[i + 1 :])
    return None, text


def parse_frontmatter(fm_lines: list[str]) -> tuple[dict[str, object], list[str]]:
    """Hand-parse the vault's frontmatter dialect. Returns (data, parse errors)."""
    data: dict[str, object] = {}
    errors: list[str] = []
    i = 0
    while i < len(fm_lines):
        line = fm_lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        match = KEY_RE.match(line)
        if not match:
            errors.append(f"unparseable frontmatter line {i + 1}: {line.strip()!r}")
            i += 1
            continue
        key, rest = match.group(1), match.group(2).strip()
        if rest.startswith("[") and rest.endswith("]"):
            data[key] = parse_inline_list(rest)
            i += 1
        elif rest:
            data[key] = parse_scalar(rest)
            i += 1
        else:
            items: list[str] = []
            i += 1
            while i < len(fm_lines) and fm_lines[i].lstrip().startswith("- "):
                items.append(parse_scalar(fm_lines[i].lstrip()[2:]))
                i += 1
            data[key] = items
    return data, errors


def strip_code_fences(body: str) -> str:
    out: list[str] = []
    fenced = False
    for line in body.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            out.append(line)
    return "\n".join(out)


def wikilinks(body: str) -> list[str]:
    return [t.strip() for t in WIKILINK_RE.findall(strip_code_fences(body)) if t.strip()]


# --------------------------------------------------------------------------- #
# vault model
# --------------------------------------------------------------------------- #


def vocabulary_tag(item: str) -> str | None:
    """The tag of one vocabulary list item, or None when it carries no valid tag.

    The item may carry a trailing annotation — `- ``tooling`` — dev environment` —
    which is for humans only: the tag is the first backtick-quoted token, else the
    first whitespace-delimited token, of the part before the ` — ` / ` - ` separator.
    """
    head = VOCAB_ANNOTATION_RE.split(item, 1)[0].strip()
    quoted = VOCAB_BACKTICK_RE.match(head)
    candidate = quoted.group(1).strip() if quoted else head.split()[0] if head.split() else ""
    return candidate if KEBAB_RE.match(candidate) else None


def read_vocabulary(vault: Path) -> tuple[set[str], list[str], list[str]]:
    """Parse the closed domain vocabulary out of _meta/instance.md.

    Returns (vocabulary, violations, warnings). A list item in the vocabulary
    section that yields no tag is warned about rather than dropped in silence —
    a silently lost tag reads to its author as a tag that exists, and every note
    using it is then flagged out-of-vocabulary for no visible reason.
    """
    instance = vault / "_meta" / "instance.md"
    if not instance.is_file():
        return (
            set(),
            ["_meta/instance.md: missing — the instance configuration file is required"],
            [],
        )
    text = strip_comments(instance.read_text(encoding="utf-8"))
    vocab: set[str] = set()
    warnings: list[str] = []
    in_section = False
    for line in text.splitlines():
        if line.startswith("#"):
            in_section = line.lstrip("#").strip().lower().startswith("domain tag vocabulary")
            continue
        if not in_section:
            continue
        item = VOCAB_ITEM_RE.match(line.strip())
        if not item:
            continue
        tag = vocabulary_tag(item.group(1))
        if tag is None:
            warnings.append(
                f"_meta/instance.md: warning: vocabulary line carries no kebab-case tag and is "
                f"ignored — {line.strip()!r}"
            )
            continue
        vocab.add(tag)
    return vocab, [], warnings


def type_folders(vault: Path) -> list[str]:
    """Type folders are defined by the templates the instance ships."""
    templates = vault / "_meta" / "templates"
    if not templates.is_dir():
        return []
    return sorted(p.stem for p in templates.glob("*.md"))


def collect_notes(vault: Path) -> list[Path]:
    """Every .md file in the note namespace (type folders, _inbox, instance folders)."""
    notes: list[Path] = []
    for path in sorted(vault.rglob("*.md")):
        rel = path.relative_to(vault)
        if len(rel.parts) < 2:
            continue  # top-level framework docs are not notes
        if any(part in SKIP_DIRS for part in rel.parts[:-1]):
            continue
        notes.append(path)
    return notes


# --------------------------------------------------------------------------- #
# checks
# --------------------------------------------------------------------------- #


def check_note(path: Path, rel: Path, folder: str, vocab: set[str], index: dict[str, list[str]]) -> list[str]:
    problems: list[str] = []
    text = path.read_text(encoding="utf-8")
    fm_lines, body = split_frontmatter(text)

    # --- filename rules -----------------------------------------------------
    stem = path.stem
    if folder == "meetings":
        dated = DATED_RE.match(stem)
        if not dated:
            problems.append("filename must start with the meeting date: YYYY-MM-DD-<topic>.md")
        elif not KEBAB_RE.match(dated.group(2)):
            problems.append("filename topic must be kebab-case English after the date")
    elif not KEBAB_RE.match(stem):
        problems.append("filename must be kebab-case English (a-z, 0-9, hyphens)")

    # --- frontmatter --------------------------------------------------------
    if fm_lines is None:
        problems.append("missing YAML frontmatter block")
        return [f"{rel}: {p}" for p in problems]

    data, parse_errors = parse_frontmatter(fm_lines)
    problems.extend(parse_errors)

    for key in REQUIRED_KEYS:
        if key not in data:
            problems.append(f"missing required frontmatter key: {key}")

    note_type = data.get("type")
    if isinstance(note_type, str) and note_type != folder:
        problems.append(f"type '{note_type}' does not match its folder '{folder}' (the folder wins)")

    status = data.get("status")
    if isinstance(status, str) and status not in STATUSES:
        problems.append(f"status '{status}' is not one of {'/'.join(STATUSES)}")

    source = data.get("source")
    if isinstance(source, str) and source not in SOURCES:
        problems.append(f"source '{source}' is not one of {'/'.join(SOURCES)}")

    created = data.get("created")
    if isinstance(created, str) and not DATE_RE.match(created):
        problems.append(f"created '{created}' is not a YYYY-MM-DD date")

    domains = data.get("domains")
    if domains is not None and not isinstance(domains, list):
        problems.append("domains must be a list, e.g. domains: [ci-cd]")
        domains = None
    if isinstance(domains, list):
        for value in domains:
            if value not in vocab:
                problems.append(f"domain '{value}' is not in the vocabulary of _meta/instance.md")
        if not domains and status != "raw":
            problems.append(f"domains may only be empty on raw notes (status is '{status}')")

    # --- wikilinks ----------------------------------------------------------
    links = wikilinks(body)
    for target in links:
        if target not in index:
            problems.append(f"wikilink [[{target}]] has no matching note in the vault")

    # --- curated/evergreen floor -------------------------------------------
    if status in ("curated", "evergreen") and not links:
        problems.append(f"a {status} note must link to at least one related note ([[wikilink]])")

    return [f"{rel}: {p}" for p in problems]


def lint(vault: Path) -> tuple[list[str], list[str], int]:
    """Returns (violations, warnings, notes checked). Warnings never fail the run."""
    problems: list[str] = []
    warnings: list[str] = []
    vocab, vocab_problems, vocab_warnings = read_vocabulary(vault)
    problems.extend(vocab_problems)
    warnings.extend(vocab_warnings)

    folders = type_folders(vault)
    if not folders:
        problems.append("_meta/templates: no note templates found — type folders are undefined")

    notes = collect_notes(vault)

    index: dict[str, list[str]] = {}
    for path in notes:
        index.setdefault(path.stem, []).append(str(path.relative_to(vault)))
    for stem, owners in sorted(index.items()):
        if len(owners) > 1:
            problems.append(f"{owners[0]}: basename '{stem}' is not unique — also at {', '.join(owners[1:])}")

    checked = 0
    for path in notes:
        rel = path.relative_to(vault)
        folder = rel.parts[0]
        if folder not in folders:
            # `_inbox` is schema-free by design; anything else here is a folder the
            # schema cannot see, which is almost always an accident.
            if folder not in NON_TYPE_FOLDERS:
                warnings.append(
                    f"{rel}: warning: '{folder}' is not a type folder, so this note is invisible to "
                    f"the schema — move it into a type folder, or add _meta/templates/{folder}.md"
                )
            continue
        checked += 1
        problems.extend(check_note(path, rel, folder, vocab, index))

    return problems, warnings, checked


def main(argv: list[str]) -> int:
    vault = Path(argv[1]).resolve() if len(argv) > 1 else Path(__file__).resolve().parent.parent
    if not vault.is_dir():
        print(f"{vault}: not a directory", file=sys.stderr)
        return 1

    problems, warnings, checked = lint(vault)
    for warning in warnings:
        print(warning)
    for problem in problems:
        print(problem)
    suffix = f", {len(warnings)} warning(s)" if warnings else ""
    if problems:
        print(f"\nlint: {len(problems)} violation(s) across {checked} note(s) checked{suffix}")
        return 1
    print(f"lint: clean ({checked} note(s) checked{suffix})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
