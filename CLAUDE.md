# CLAUDE.md — Agent Entry Point

This repository is a **loopkb vault**: a git-backed, Obsidian-compatible knowledge base
maintained jointly by humans and AI agents. This file is the single source of truth for
agent behavior. Other agents (Codex CLI, etc.) are pointed here via `AGENTS.md`.

## What this vault is

- Every note is a Markdown file with YAML frontmatter. Obsidian is the human reading/editing UI;
  agents operate directly on the filesystem via git.
- Notes are classified by **type** (folder, single-valued) and **domain** (frontmatter tags, multi-valued).
- The vault is continuously improved by a maintenance loop (`/kb-loop`), not just appended to.

## Rule files — read before acting

| File | Purpose |
|---|---|
| `_meta/taxonomy.md` | Type criteria, tag vocabulary (closed), naming rules |
| `_meta/loop.md` | The 4-stage maintenance pipeline and its guardrails |
| `_meta/templates/` | One template per note type — always instantiate from these |
| `.claude/skills/*/SKILL.md` | Operating procedures for kb-save / kb-search / kb-loop — applies to ALL agents, not just Claude Code |

## Frontmatter schema

```yaml
---
type: troubleshooting            # single value; must match the folder the note lives in
domains: [flutter, ios]          # multi-value; ONLY values listed in _meta/taxonomy.md
projects: [repo-name]            # optional; related project repos
created: 2026-08-01              # date the note was filed into the vault
source: inbox                    # inbox | conversation | meeting
status: raw                      # raw -> curated -> evergreen (see taxonomy.md)
---
```

## Write tiers

| Operation | Channel |
|---|---|
| Add note, add links/tags, formatting fix, status promotion | Commit directly to `main` |
| Status demotion (one level down; reason required in commit message) | Commit directly to `main` |
| Merge notes, delete, rename, move across folders, rewrite existing content, change `_meta/` rules | Branch + merge request |

"Move across folders" means moving an already-filed note between type folders.
Filing an item OUT of `_inbox/` is triage, which is additive → direct commit.

"Rewrite" boundary: reformatting that preserves meaning (layout, frontmatter fill,
typo fixes) is additive; changing or removing semantic content is a rewrite → MR.
Promotion to `evergreen` that involves distilling/merging content travels in the
same MR as the distillation, not as a separate direct commit.

**MR fallback**: in a solo vault or a repo without an MR/PR platform, the MR channel
degrades to: commit on a branch `kb-loop/<topic>`, have the human review the diff
locally (`git diff main...`), then merge. The review step never disappears.

## Commit conventions

- Agent commits MUST be prefixed: `[kb-save]` for new knowledge captured from a
  conversation; `[kb-loop]` for any maintenance action (triage, refine, reflect, lint) —
  including ad-hoc ones performed outside a full loop run.
  This is how the reflect stage separates human corrections from agent actions in git history.
- Human commits have no prefix.

## Guardrails (non-negotiable)

1. `git pull --rebase` before starting any work; push when done. On conflict: rebase and retry. Never force-push.
2. Never touch uncommitted changes outside `_inbox/` — that is work a human is still writing.
3. When merging notes, the full original content must be reviewable in the MR diff. Never silently summarize away information.
4. Respect per-run limits defined in `_meta/loop.md`; unfinished work is picked up by the next run (the loop is stateless).

## Language policy

- Filenames, frontmatter keys, and tag values: English (kebab-case filenames, unique across the vault).
- Note body language: defined by the instance (see `_meta/taxonomy.md` header);
  defaults to English when the header does not define it.
- Links: Obsidian wikilinks `[[filename]]` without path, so moves never break links.

## Searching this vault (for agents of other repos)

1. Read `_meta/taxonomy.md` to learn the structure and tag vocabulary.
2. Grep by tag and keywords across type folders.
3. Trust order: `status: evergreen` > `curated` > `raw`.

<!-- INSTANCE OVERRIDES: instances may append stricter rules below this line. -->
