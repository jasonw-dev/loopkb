# CLAUDE.md — Agent Entry Point

This repository is a **loopkb vault**: a git-backed, Obsidian-compatible knowledge base
maintained jointly by humans and AI agents. This file is the framework's source of truth
for agent behavior. Agents that read `AGENTS.md` instead are pointed here by it.

## What this vault is

- Every note is a Markdown file with YAML frontmatter. Obsidian is the human reading/editing UI;
  agents operate directly on the filesystem via git.
- Notes are classified by **type** (folder, single-valued) and **domain** (frontmatter tags, multi-valued).
- The vault is continuously improved by a maintenance loop (`/kb-loop`), not just appended to.

## Rule files — read before acting

| File | Purpose |
|---|---|
| `_meta/instance.md` | **Instance-owned**: identity, governance mode, domain vocabulary, **classification rule amendments**, policy overrides |
| `_meta/taxonomy.md` | **Framework-owned, read-only for agents**: type criteria, naming rules, source field, status lifecycle — read it together with instance.md's amendments, which win |
| `_meta/loop.md` | The 4-stage maintenance pipeline and its guardrails |
| `_meta/digest.md` | Framework-managed: the latest run's digest, overwritten every run |
| `_meta/templates/` | One template per note type — always instantiate from these |
| `scripts/` | `lint.py` = executable definition of the schema · `lease.py` = one loop run at a time · `verify_digest.py` = proves the digest itemizes every risky action |
| `.claude/skills/*/SKILL.md` | Operating procedures for kb-setup / kb-save / kb-search / kb-loop — applies to ALL agents, not just Claude Code |

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
| Change `_meta/` rules — amendments in `_meta/instance.md` (never `_meta/taxonomy.md`) | yes | Branch + merge request |
| `curated → evergreen` promotion | — | **Never agent-performed in either mode** |

`curated → evergreen` is human-conferred in both modes. An agent may only *nominate*:
in `autonomous` the nomination is a digest line (`nominate <note> for evergreen: <reason>`)
that the human acts on with a direct commit, or lets lapse; in `reviewed` it is an MR
that the human merges. An un-acted nomination costs the human nothing — it simply lapses.

"Move across folders" means moving an already-filed note between type folders.
Filing an item OUT of `_inbox/` is triage, which is additive → direct commit.

"Change `_meta/` rules" always means writing `_meta/instance.md`: a dated entry under
"Classification rule amendments" for a type/naming/source rule, or the vocabulary and
policy sections for those. `_meta/taxonomy.md` is framework-owned — agents read it and
never write it, since the next `git merge upstream/main` would overwrite the edit while
an amendment survives untouched (`_meta/loop.md`, Stage 3).

"Rewrite" boundary: reformatting that preserves meaning (layout, frontmatter fill,
typo fixes) is additive; changing or removing semantic content is a rewrite.
In `reviewed` mode a distillation that would end at `evergreen` travels as one MR:
the human merging it is the human conferring the status. In `autonomous` mode the
same distillation lands as a `curated` note by direct commit, and the agent nominates
it for `evergreen` in the digest — an agent never writes `evergreen` itself.

**`reviewed` mode requires an MR platform** (`gh`, `glab`, or the platform's API) —
name it in `_meta/instance.md` → Policy overrides. There is no platform-less variant of
it: a vault with no MR platform runs `autonomous`, which is the mode built for exactly
that case and asks nothing of a platform at any point.

**It also requires that MRs land as merge commits.** `scripts/verify_digest.py` skips
merge commits because in this mode a merge *is* the human review; squash- and rebase-merge
flatten an approved MR into a single-parent `[kb-loop]` commit that the script cannot tell
from one which bypassed review, and it then reports human-approved work as missing from
the digest. Set the project's merge method to "merge commit" before choosing `reviewed`,
or itemize every squashed MR in the digest exactly like a direct commit
(`_meta/loop.md` → MR mechanics).

## The run digest

Every loop run writes its report to **`_meta/digest.md`**, overwriting the previous
one — git history keeps every past digest — and repeats it in the body of the final
report commit. `_meta/digest.md` is framework-managed state, not a note: `scripts/lint.py`
never schema-checks it (`_meta/` is outside the note namespace).

Structure, in this order:

1. Header — date, governance mode, machine/holder.
2. **Risky actions** — first, and itemized: merges (which notes, why), deletions,
   moves/renames, `_meta/` rule changes, demotions. **Every line carries that action's
   short commit SHA** — it makes `git revert <sha>` copy-pasteable and it is what
   `scripts/verify_digest.py` matches against. Say `none` when there were none.
   In `reviewed` mode this section lists the *open MRs* awaiting review instead of
   applied actions.
3. Triage / refine / reflect / lint summaries.
4. Stuck items and what context they need.
5. Evergreen nominations.

The digest is the human's whole interface to the loop: in `autonomous` mode, reading
it and reverting what looks wrong is the entire review duty.

Its completeness is therefore checked where it can be. Write the digest first, then run
`python3 scripts/verify_digest.py`, then make the report commit — the script re-derives
four classes of risky action from git (deletions and renames under the type folders,
`_meta/` changes other than the digest, and `status:` demotions) and exits 1 naming any
whose short SHA is missing from `_meta/digest.md`. Never commit the report over a failing
verifier (`_meta/loop.md` → The digest → Verification).

**A clean verifier is not a complete digest.** The fifth class — rewriting a note's
meaning — is indistinguishable from reformatting in a diff, so no script derives it: it
rests on the agent writing that line honestly. Its recovery path is git (the rewrite is a
diff on `main`, revertable whenever it is spotted) and the freshness check, which
re-reads the oldest notes and demotes what no longer holds.

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
6. **Rewriting an existing note means re-reading its link neighborhood first.** Before
   committing a rewrite, read the note's outbound wikilinks and find its inbound ones
   mechanically — `grep -rl "\[\[<basename>\]\]"` over the type folders, `<basename>`
   being the filename without `.md` — then apply Stage 2b's reconcile-on-sight duty
   (`_meta/loop.md`) to whatever they say: reconcile through the normal channels for
   those actions, and where you cannot tell which side is right, demote the doubtful
   note one level with the reason and add a digest **Stuck** line naming both notes.
   Risky actions stay itemized as usual. The neighborhood is the link graph and nothing
   more — never the whole vault. This binds every agent rewrite, inside a loop run or not.

These hold in both governance modes. `autonomous` moves the human review *after* the
write; it does not remove the lease, the linter, the push rules, or the prefixes.

## Language policy

- Filenames, frontmatter keys, and tag values: English (kebab-case filenames, unique across the vault).
- Note body language: defined by the instance (`_meta/instance.md` → Identity);
  defaults to English when the instance does not define it.
- Links: Obsidian wikilinks `[[filename]]` without path, so moves never break links.

## Searching this vault (for agents of other repos)

1. Read `_meta/taxonomy.md` for the structure and `_meta/instance.md` for the tag
   vocabulary and the classification rule amendments (they override the taxonomy).
2. Grep by tag and keywords across type folders.
3. Trust order: `status: evergreen` > `curated` > `raw`.

---

Instance configuration and policy overrides live in `_meta/instance.md` — read it
after this file; its policies override these defaults.
