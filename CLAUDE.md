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
| `_meta/instance.md` | **Instance-owned**: identity, governance mode, domain vocabulary, policy overrides |
| `_meta/taxonomy.md` | Type criteria, naming rules, source field, status lifecycle |
| `_meta/loop.md` | The 4-stage maintenance pipeline and its guardrails |
| `_meta/digest.md` | Framework-managed: the latest run's digest, overwritten every run |
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
disagree about what is valid, the script is right — fix the prose through the
`_meta/` rule-change channel of the active governance mode (see below).

## Governance modes

The vault runs in exactly one governance mode, declared in `_meta/instance.md` →
Governance. Read it before your first write. When the field is absent, assume
`autonomous` — it is the framework default.

- **`autonomous` (default) — default-open + audit.** Agents perform every operation
  by direct commit to `main`, destructive ones included. In exchange, every risky
  action is itemized in the run digest (`_meta/digest.md`). The human reads the
  digest and `git revert`s whatever they disagree with. Nothing blocks on the human,
  and no merge-request platform is involved at all.
- **`reviewed` — pre-approval.** Destructive operations and `_meta/` rule changes
  travel through a branch plus a merge request that a human approves before anything
  lands on `main`. Choose it when agent trust is not yet established.

The mode changes only *when* the human looks (before vs. after the write). It never
relaxes the guardrails below, and it never lets an agent confer `evergreen`.

## Write tiers

These tiers bind **agents only**. Humans always commit directly, without prefixes —
the reflect stage depends on those unprefixed commits as its correction signal.

**In `autonomous` mode every row below collapses to a single channel: direct commit
to `main`, plus a line in the digest's "Risky actions" section for every row marked
*risky*.** The one exception is `curated → evergreen`, which no agent may perform in
either mode. The "reviewed-mode channel" column applies to `reviewed` mode only.

| Operation | Risky (digest line in `autonomous`) | `reviewed`-mode channel |
|---|---|---|
| Add note, add links/tags, formatting fix, `raw → curated` promotion | no | Commit directly to `main` |
| Status demotion (one level down; reason required in commit message) | yes | Commit directly to `main` |
| Merge notes, delete, rename, move across folders, rewrite existing content | yes | Branch + merge request |
| Change `_meta/` rules (taxonomy / instance policy) | yes | Branch + merge request |
| `curated → evergreen` promotion | — | **Never agent-performed in either mode** |

`curated → evergreen` is human-conferred in both modes. An agent may only *nominate*:
in `autonomous` the nomination is a digest line (`nominate <note> for evergreen: <reason>`)
that the human acts on with a direct commit, or lets lapse; in `reviewed` it is an MR
that the human merges. An un-acted nomination costs the human nothing — it simply lapses.

"Move across folders" means moving an already-filed note between type folders.
Filing an item OUT of `_inbox/` is triage, which is additive → direct commit.

"Rewrite" boundary: reformatting that preserves meaning (layout, frontmatter fill,
typo fixes) is additive; changing or removing semantic content is a rewrite.
In `reviewed` mode a distillation that would end at `evergreen` travels as one MR:
the human merging it is the human conferring the status.

**MR fallback** (`reviewed` mode only): in a repo without an MR/PR platform, the MR
channel degrades to: commit on a branch `kb-loop/<topic>-<YYYYMMDD>`, have the human
review the diff locally (`git diff main...`), then merge. The review step never
disappears. In `autonomous` mode there is no MR channel to degrade — a vault with no
platform is exactly what that mode is built for.

## The run digest

Every loop run writes its report to **`_meta/digest.md`**, overwriting the previous
one — git history keeps every past digest — and repeats it in the body of the final
report commit. `_meta/digest.md` is framework-managed state, not a note: `scripts/lint.py`
never schema-checks it (`_meta/` is outside the note namespace).

Structure, in this order:

1. Header — date, governance mode, machine/holder.
2. **Risky actions** — first, and itemized: merges (which notes, why), deletions,
   moves/renames, `_meta/` rule changes, demotions. Say `none` when there were none.
   In `reviewed` mode this section lists the *open MRs* awaiting review instead of
   applied actions.
3. Triage / refine / reflect / lint summaries.
4. Stuck items and what context they need.
5. Evergreen nominations.

The digest is the human's whole interface to the loop: in `autonomous` mode, reading
it and reverting what looks wrong is the entire review duty.

## Commit conventions

- Agent commits MUST be prefixed: `[kb-save]` for new knowledge captured from a
  conversation; `[kb-loop]` for any maintenance action (triage, refine, reflect, lint) —
  including ad-hoc ones performed outside a full loop run.
  This is how the reflect stage separates human corrections from agent actions in git history.
- Human commits have no prefix.
- A human `git revert` of a prefixed agent commit is a **rejection signal** with the
  same weight as a closed MR: reflect reads it, and the reverted action must not be
  redone unless the notes involved materially changed (see `_meta/loop.md`, Stage 3).

## Guardrails (non-negotiable)

1. `git pull --rebase` before starting any work; push when done. On conflict: rebase
   and retry. Never force-push `main` or any shared branch; updating your own open
   `kb-loop/*` branch after a rebase uses `--force-with-lease`.
2. Never touch uncommitted changes outside `_inbox/` — that is work a human is still writing.
3. When merging notes, the full original content must stay reviewable in git — the
   merge commit deletes the originals so their full text appears in the deleted-file
   diff (in `reviewed` mode, in the MR diff). Never silently summarize away information.
4. Respect per-run limits defined in `_meta/loop.md`; unfinished work is picked up by the next run (the loop is stateless).
5. Once setup is complete — i.e. the domain vocabulary in `_meta/instance.md` is
   non-empty — the `_meta/` write rule for agents is active: MR-only in `reviewed`
   mode; direct commit plus a digest "Risky actions" line in `autonomous` mode.
   Before that gate, instantiation edits are allowed directly and unreported.

These hold in both governance modes. `autonomous` moves the human review *after* the
write; it does not remove the lease, the linter, the push rules, or the prefixes.

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
