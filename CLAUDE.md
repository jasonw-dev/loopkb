# CLAUDE.md — Agent Entry Point

This repository is a **loopkb vault**: a git-backed, Obsidian-compatible knowledge base
maintained jointly by humans and AI agents. This file is the framework's source of truth
for agent behavior. Other agents (Codex CLI, etc.) are pointed here via `AGENTS.md`.

## What this vault is

- Every note is a Markdown file with YAML frontmatter. Obsidian is the human reading/editing UI;
  agents operate directly on the filesystem via git.
- Notes are classified by **type** (folder, single-valued) and **domain** (frontmatter tags, multi-valued).
- The vault is continuously improved by a maintenance loop (`/kb-loop`), not just appended to.

## Rule files — read before acting

| File | Purpose |
|---|---|
| `_meta/instance.md` | **Instance-owned**: identity, domain vocabulary, policy overrides |
| `_meta/taxonomy.md` | Type criteria, naming rules, source field, status lifecycle |
| `_meta/loop.md` | The 4-stage maintenance pipeline and its guardrails |
| `_meta/templates/` | One template per note type — always instantiate from these |
| `scripts/lint.py` | Executable definition of the schema; `scripts/lease.py` guards concurrent loop runs |
| `.claude/skills/*/SKILL.md` | Operating procedures for kb-save / kb-search / kb-loop — applies to ALL agents, not just Claude Code |

## Frontmatter schema

```yaml
---
type: troubleshooting            # single value; must match the folder the note lives in
domains: [ci-cd]                 # multi-value; ONLY values listed in _meta/instance.md
projects: [repo-name]            # optional; related project repos
created: 2026-08-01              # date the note was filed into the vault
source: inbox                    # inbox | conversation | meeting
status: raw                      # raw -> curated -> evergreen (see taxonomy.md)
---
```

`python3 scripts/lint.py` checks this schema mechanically. When prose and the script
disagree about what is valid, the script is right — fix the prose via MR.

## Write tiers

These tiers bind **agents only**. Humans always commit directly, without prefixes —
the reflect stage depends on those unprefixed commits as its correction signal.

| Operation | Channel |
|---|---|
| Add note, add links/tags, formatting fix, `raw → curated` promotion | Commit directly to `main` |
| Status demotion (one level down; reason required in commit message) | Commit directly to `main` |
| `curated → evergreen` promotion | **Never direct** — humans confer evergreen; an agent may only nominate via MR |
| Merge notes, delete, rename, move across folders, rewrite existing content, change `_meta/` rules | Branch + merge request |

"Move across folders" means moving an already-filed note between type folders.
Filing an item OUT of `_inbox/` is triage, which is additive → direct commit.

"Rewrite" boundary: reformatting that preserves meaning (layout, frontmatter fill,
typo fixes) is additive; changing or removing semantic content is a rewrite → MR.
A distillation that would end at `evergreen` travels as one MR: the human merging it
is the human conferring the status.

**MR fallback**: in a solo vault or a repo without an MR/PR platform, the MR channel
degrades to: commit on a branch `kb-loop/<topic>-<YYYYMMDD>`, have the human review
the diff locally (`git diff main...`), then merge. The review step never disappears.

## Commit conventions

- Agent commits MUST be prefixed: `[kb-save]` for new knowledge captured from a
  conversation; `[kb-loop]` for any maintenance action (triage, refine, reflect, lint) —
  including ad-hoc ones performed outside a full loop run.
  This is how the reflect stage separates human corrections from agent actions in git history.
- Human commits have no prefix.

## Guardrails (non-negotiable)

1. `git pull --rebase` before starting any work; push when done. On conflict: rebase
   and retry. Never force-push `main` or any shared branch; updating your own open
   `kb-loop/*` branch after a rebase uses `--force-with-lease`.
2. Never touch uncommitted changes outside `_inbox/` — that is work a human is still writing.
3. When merging notes, the full original content must be reviewable in the MR diff. Never silently summarize away information.
4. Respect per-run limits defined in `_meta/loop.md`; unfinished work is picked up by the next run (the loop is stateless).
5. Once setup is complete — i.e. the domain vocabulary in `_meta/instance.md` is
   non-empty — agents NEVER change anything under `_meta/` outside an MR. Before that
   gate, instantiation edits are allowed directly.

## Language policy

- Filenames, frontmatter keys, and tag values: English (kebab-case filenames, unique across the vault).
- Note body language: defined by the instance (`_meta/instance.md` → Identity);
  defaults to English when the instance does not define it.
- Links: Obsidian wikilinks `[[filename]]` without path, so moves never break links.

## Searching this vault (for agents of other repos)

1. Read `_meta/taxonomy.md` for the structure and `_meta/instance.md` for the tag vocabulary.
2. Grep by tag and keywords across type folders.
3. Trust order: `status: evergreen` > `curated` > `raw`.

---

Instance configuration and policy overrides live in `_meta/instance.md` — read it
after this file; its policies override these defaults.
