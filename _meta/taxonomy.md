# Taxonomy

<!-- INSTANCE HEADER — fill in when instantiating:
Note body language: <e.g. Traditional Chinese (Taiwan), technical terms kept in English>
Vault scope: <e.g. mobile team engineering knowledge>
-->

## Types (folders)

A note has exactly ONE type. The type decides the folder and the template
(`_meta/templates/<type>.md`). Decision rules, in order — first match wins:

| Type | It is a match when… | Not a match when… |
|---|---|---|
| `troubleshooting` | A concrete problem occurred and was (or is being) solved: symptom → cause → fix | General "how to do X" with no triggering failure → `guides` |
| `decisions` | A choice was made between alternatives and the reasoning matters later (lightweight ADR) | Meeting notes that contain a decision → extract the decision into `decisions/`, keep the meeting in `meetings/` |
| `guides` | Repeatable instructions: how to set up, build, release, configure | A one-off fix for a specific failure → `troubleshooting` |
| `references` | Summary of external material: article, official docs, release notes | Original team knowledge → one of the other types |
| `meetings` | Record of a meeting or discussion, tied to a date | — |

If none of these fit confidently, the item stays in `_inbox/` with a note explaining why.

## What does NOT belong in this vault

- **Repo-local facts** — anything a single repo's own files or docs define (versions,
  build config, internal quirks of that repo). Those belong in that repo's README /
  CLAUDE.md / an MR fixing the root cause. The vault records knowledge that spans
  repos, processes, or environments — and *where the source of truth lives*, never a
  copy of the truth itself (copies rot). This includes unfixed traps inside a single
  repo: document them in that repo (or fix the root cause), not here.
- **Machine-local setup** — personal tooling choices not adopted by the team.
- **Agent-imported content** — anything an agent brings in on its own initiative
  (from its memory, prior conversations, or test fixtures) with no human contributor
  standing behind it. Knowledge enters the vault only when a person deliberately
  contributes it (inbox drop or kb-save). Test data used to exercise the loop must be
  removed when the test ends.
- During triage, reject such items: leave them in `_inbox/` with a note pointing to
  where the content should go instead.

## Domain tags (closed vocabulary)

`domains:` may ONLY use values from this list. Adding a value requires a
rule-change MR (see `_meta/loop.md`, reflect stage).

`domains: []` is legal on `raw` notes (triage may not know the domain yet); the
refine stage fills it. A note cannot be promoted to `curated` with empty domains.
In this template the list below is intentionally empty — an instance MUST fill it
before its first triage run.

<!-- INSTANCE: fill in. Example for a mobile team:
- `flutter`
- `android`
- `ios`
- `cross-platform`
- `ci-cd`
- `tooling`
-->

## Project tags

`projects:` values are repo names of related projects. Open vocabulary, but must be
actual repo names (verifiable), not free text.

## Naming rules

- Filenames: English, kebab-case, descriptive, unique across the entire vault.
  Good: `flutter-ios-codesign-fastlane.md`. Bad: `note1.md`, `iOS問題.md`.
- A rename counts as a destructive operation (breaks inbound links until updated) → MR channel.

## Source field

`source:` records how the content entered the vault: `inbox` (filed from `_inbox/`),
`conversation` (captured via kb-save), `meeting` (the origin material is a meeting
record — regardless of whether it arrived via inbox or kb-save).

## Status lifecycle

- `raw` — just filed; minimally cleaned up.
- `curated` — links, tags, and formatting verified; connected to related notes.
- `evergreen` — distilled, possibly merged from several notes; safe to trust long-term.

Promotion is done by the loop (refine stage) or by humans. Demotion (evergreen → curated)
is allowed when content is found stale — record why in the commit message.
