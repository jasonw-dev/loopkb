# Instance Configuration

<!-- TEMPLATE SKELETON — this is the ONE file you fill in when instantiating.
     Replace every <angle-bracket placeholder> below and delete this comment. -->

This file is **owned by the instance**. Framework files (`CLAUDE.md`,
`_meta/taxonomy.md`, `_meta/loop.md`, `_meta/templates/`, `.claude/skills/`,
`scripts/`) never carry instance-specific content, so pulling template updates
(`git merge upstream/main`) leaves what you configure here alone. One exception,
once: an instance's history is unrelated to the template's, so the very first
merge needs `--allow-unrelated-histories` and conflicts on this file — keep your
version (`git checkout --ours`). See GETTING-STARTED.md → "Updating an instance".

**Precedence**: policies in this file OVERRIDE the framework defaults in
`CLAUDE.md`. Agents read `CLAUDE.md` first, then this file.

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

## Project tags

`projects:` values are repo names of related projects. Open vocabulary, but each
value must be a real repo name (verifiable), not free text.

- **Repo namespace**: <e.g. all repos under github.com/<org> · or: n/a for a personal vault>

## Policy overrides

Framework defaults apply unless overridden here. Delete the ones you do not need.

- **MR platform** (`reviewed` mode only; ignored in `autonomous`): <e.g. GitHub pull
  requests via `gh` · GitLab MRs via `glab` · none — use the MR fallback in CLAUDE.md>
- **Write tiers**: <e.g. defaults for the declared mode apply · or, in `reviewed`
  mode during a trial period: ALL refine operations go through MRs, including
  link/tag/format edits>
- **Evergreen promotion**: human-only in both modes (`_meta/taxonomy.md`). <Name the
  people who confer it, if that is worth recording.>
- **Per-run limits**: <e.g. defaults apply (10 notes refined; in `reviewed` mode also
  3 MRs per run)>
- **Extra type folders**: <e.g. none · or: `journal/` — add a matching template in `_meta/templates/`>
- **Lease**: <e.g. defaults apply (2h TTL) · or: solo vault, lock stays local>
