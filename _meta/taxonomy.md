# Taxonomy

Framework rules. Nothing in this file is instance-specific — the domain tag
vocabulary, the note body language, and any policy overrides live in
`_meta/instance.md`.

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

The set of type folders is whatever `_meta/templates/` defines — `scripts/lint.py`
derives it from there, so an instance that adds a type folder adds its template too
(and records it under "Extra type folders" in `_meta/instance.md`).

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
- **Secrets and personal data** — credentials, API tokens, private keys, passwords,
  connection strings that embed one, and personal data about identifiable people never
  enter the vault, in any type folder, at any status. Knowledge *about* a credential is
  welcome: say **where it lives** (the keychain entry, the secret manager path, the CI
  variable name) and how it is rotated — never the value itself.
- **Out of scope** — anything outside the vault scope declared in `_meta/instance.md`.
- During triage, reject such items: leave them in `_inbox/` with a note pointing to
  where the content should go instead.

**Apparent secrets get a different rejection.** If an inbox item contains what looks
like a credential, triage does NOT file it and does NOT quietly delete it. Leave the
item in `_inbox/` with a visible callout:

```
> [!warning] kb-loop: apparent credential — ROTATE it, then resubmit
> This item contains what looks like a secret, so it was not filed. Triage commits the
> original before filing (`_meta/loop.md`, Stage 1), so the value is already in git
> history: deleting the file is NOT a remedy. Rotate the credential at its source,
> then re-drop this item with the value removed.
```

Say the same thing in the digest's "Stuck" section. The commit-first rule makes this
the only honest response — history rewriting is not something the loop does, and a
rotated secret is worthless to whoever reads the history later.

## Domain tags (closed vocabulary)

`domains:` may ONLY use values listed in `_meta/instance.md` → "Domain tag
vocabulary". Adding a value is a rule change against `_meta/instance.md` (the
vocabulary is instance-owned) and goes through the reflect stage on the channel of
the active governance mode: direct commit plus a digest risky-action line in
`autonomous`, an MR in `reviewed` (see `_meta/loop.md`).

`domains: []` is legal on `raw` notes (triage may not know the domain yet); the
refine stage fills it. A note cannot be promoted to `curated` with empty domains.

## Project tags

`projects:` values are repo names of related projects. Open vocabulary, but must be
actual repo names (verifiable), not free text.

## Naming rules

- Filenames: English, kebab-case, descriptive, unique across the entire vault.
  Good: `release-build-stale-cache.md`. Bad: `note1.md`, `Release Build.md`.
- `meetings/` filenames start with the date: `YYYY-MM-DD-<topic>.md` — recurring
  meetings would otherwise collide with the uniqueness rule.
- **Agents**: a rename is destructive (it breaks inbound links until they are
  retargeted), so it is a risky action either way. `autonomous`: direct commit that
  retargets every inbound wikilink in the *same* commit, plus a digest risky-action
  line — a revertable rename must be revertable in one shot. `reviewed`: MR channel,
  retargeting every inbound wikilink in the same MR.
  **Humans**: rename freely by direct commit — lint reports whatever links went
  dangling and the refine stage repairs them.

`scripts/lint.py` is the executable definition of these rules.

## Source field

`source:` records how the content entered the vault: `inbox` (filed from `_inbox/`),
`conversation` (captured via kb-save), `meeting` (the origin material is a meeting
record — regardless of whether it arrived via inbox or kb-save).

## Status lifecycle

- `raw` — just filed; minimally cleaned up.
- `curated` — links, tags, and formatting verified; connected to related notes.
  Floor (enforced by `scripts/lint.py`): non-empty `domains` and ≥ 1 wikilink.
- `evergreen` — distilled, possibly merged from several notes; safe to trust
  long-term. **Evergreen is human-conferred**: it means a person stood behind the
  note. That is what makes kb-search's trust order worth anything.

| Transition | Who | Channel |
|---|---|---|
| `raw → curated` | Agent (refine stage) or human | Direct commit, once the curated floor is met (both modes) |
| `curated → evergreen` | **Human only, in both governance modes** | Human direct commit. An agent may only *nominate*: in `autonomous`, a `nominate <note> for evergreen: <reason>` line in `_meta/digest.md`, which the human acts on by direct commit or lets lapse; in `reviewed`, an MR that sets `evergreen` for the human to merge. Never by committing the promotion to `main` itself |
| Demotion (one level down) | Agent or human | Direct commit; reason required in the commit message. Risky action → digest line in `autonomous` |

Demotion lowers a trust claim, so it needs no review. Promotion to `evergreen`
raises one, so it needs a human — which is why `autonomous` mode, which otherwise
lets agents write anything, still stops here. A nomination the human never acts on
simply lapses; nothing in the loop blocks on it.
