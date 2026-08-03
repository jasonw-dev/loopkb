# Instance Configuration

<!-- TEMPLATE SKELETON — this is the ONE file you fill in when instantiating.
     Replace every <angle-bracket placeholder> below and delete this comment. -->

This file is **owned by the instance**. Framework files (`CLAUDE.md`,
`_meta/taxonomy.md`, `_meta/loop.md`, `_meta/templates/`, `scripts/`, and the four
`kb-*` skills under `.claude/skills/`) never carry
instance-specific content, so pulling template updates
(`git merge upstream/main`) leaves what you configure here alone — including the
classification rules the loop learns from your corrections, which land in this file
too (see "Classification rule amendments" below). One exception,
once: an instance's history is unrelated to the template's, so the very first
merge needs `--allow-unrelated-histories` and conflicts on this file — keep your
version (`git checkout --ours`). See GETTING-STARTED.md → "Updating an instance".
The skills directory is shared rather than exclusively framework-owned: an
instance may add its own team skills beside the `kb-*` four, and since upstream never
ships those names, a merge leaves them alone as well.

**Precedence**: policies in this file OVERRIDE the framework defaults in
`CLAUDE.md`. Agents read `CLAUDE.md` first, then this file.

**Do not rename or translate the section headings below.** `scripts/lint.py` locates the
domain vocabulary by heading text, and agents locate the classification rule amendments
the same way; a renamed heading reads to both as an empty section.

## Identity

- **Note body language**: <e.g. English · or: Traditional Chinese (Taiwan), technical terms kept in English>
- **Vault scope**: <one sentence: what knowledge belongs to this vault, e.g. "cross-repo engineering knowledge for the platform group">

Filenames, frontmatter keys, and tag values are always English regardless of the
body language (see `CLAUDE.md` → Language policy).

## Governance

- **Mode**: `autonomous`

Pick one; the definitions live in `CLAUDE.md` → "Governance modes" and the
stage-by-stage effects in `_meta/loop.md`.

- `autonomous` (framework default) — agents do everything by direct commit to
  `main`, destructive actions included, and itemize each risky one in
  `_meta/digest.md`; you review afterwards and `git revert` what you disagree with.
- `reviewed` — destructive actions and `_meta/` rule changes wait for you in a merge
  request; nothing lands on `main` until you approve it.

`curated → evergreen` stays human-conferred in both modes.

## Domain tag vocabulary (closed)

`domains:` values MUST come from this list. Adding a value is a `_meta/` rule change
(`_meta/loop.md`, reflect stage) and travels through the channel of the active
governance mode. `scripts/lint.py` reads the vocabulary from the list items in this
section — one kebab-case tag per line, backticks optional, and an optional annotation
after the tag (``- `tag` — optional description``). A list item the linter cannot read a
tag out of is reported as a warning, never dropped in silence.

**Setup gate**: this vault counts as *set up* once this list is non-empty. Until
then, `kb-loop` refuses to run and agents may still edit `_meta/` directly and
unreported. Once it is non-empty, the `_meta/` write rule for agents is active.

<!-- Fill in below. Example for an engineering vault:
- `ci-cd` — pipelines, runners, release automation
- `tooling` — dev environment: toolchains, IDE setup
- `infrastructure`
- `frontend`
- `backend`
-->

## Classification rule amendments

**Instance-owned — this is where the taxonomy learns.** `_meta/taxonomy.md` is
framework-owned and read-only for agents, so every classification rule the reflect stage
learns (`_meta/loop.md`, Stage 3) lands *here* instead, as a dated amendment entry that
EXTENDS or OVERRIDES the framework rules. Agents read `_meta/taxonomy.md` and this
section **together, and an amendment wins over the taxonomy line it contradicts.**

That split is what makes template updates safe: `git merge upstream/main` replaces
`_meta/taxonomy.md` wholesale but never touches this file, so nothing your vault learned
is lost to a framework release (GETTING-STARTED.md → "Updating an instance").

One entry per amendment, newest last, dated:

```
### 2026-08-01 — a meeting note that is only a decision files as `decisions`
- **Amends**: `_meta/taxonomy.md` → Types → `meetings` (overrides)
- **Evidence**: 2 human corrections — a1b2c3d, e4f5a6b
- **Rule**: when a meeting note's entire content is one decision and its reasoning, file
  it as `decisions`; `meetings` keeps records that carry more than the decision.
```

Empty is the correct starting state — a fresh vault has learned nothing yet. Entries are
also removable: an amendment a human reverts is gone, and that revert is next run's
rejection signal.

## Project tags

`projects:` values are repo names of related projects. Open vocabulary, but each
value must be a real repo name (verifiable), not free text.

- **Repo namespace**: <e.g. all repos under github.com/<org> · or: n/a for a personal vault>

## Policy overrides

Framework defaults apply unless overridden here. Delete the ones you do not need.

- **MR platform** (`reviewed` mode only; ignored in `autonomous`): <e.g. GitHub pull
  requests via `gh` · GitLab MRs via `glab`. `reviewed` mode needs one — with no MR
  platform, run `autonomous`.>
- **Write tiers**: <e.g. defaults for the declared mode apply · or, in `reviewed`
  mode during a trial period: ALL refine operations go through MRs, including
  link/tag/format edits>
- **Evergreen promotion**: human-only in both modes (`_meta/taxonomy.md`). <Name the
  people who confer it, if that is worth recording.>
- **Per-run limits**: <e.g. defaults apply (10 notes refined; in `reviewed` mode also
  3 MRs per run)>
- **Extra type folders**: <e.g. none · or: `journal/` — add a matching template in `_meta/templates/`>
- **Lease**: <e.g. defaults apply (2h TTL) · or: solo vault, lock stays local>
