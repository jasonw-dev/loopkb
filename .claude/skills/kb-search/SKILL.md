---
name: kb-search
description: Use when solving a problem that the team may have hit before — build/environment/dependency errors, tooling setup, release procedures — or when explicitly asked to search the knowledge base ("kb-search", "查知識庫").
---

# kb-search

Search the team knowledge base before re-deriving a solution from scratch.

## Locate the vault

Same resolution as kb-save: `KB_VAULT` line in the project's `CLAUDE.local.md`
(or CLAUDE.md), else ask once and offer to persist it in `CLAUDE.local.md`.
If the vault clone is missing or stale, `git -C <vault> pull` first (skip on network failure — search the local copy).

## Steps

1. Read `<vault>/_meta/taxonomy.md` — learn the type folders and tag vocabulary.
2. Search in this order:
   - Filename scan of the likely type folder (filenames are descriptive kebab-case).
   - `grep -ril` across the vault for error-message fragments, tool names, tag values.
3. Rank hits: `status: evergreen` > `curated` > `raw`. Prefer newer `created` on conflict.
4. Follow `[[wikilinks]]` from hits — related notes often hold the missing half of the answer.
5. Apply the found solution, citing the note (`filename`) so the user knows the source.
6. **Miss with pain**: if nothing was found and solving it took real effort, offer to
   `/kb-save` the new solution — that is how the base grows.

## Wiring a project repo (one-time)

Add to the project's **committed** CLAUDE.md (team facts only — never a personal path):

```
## Knowledge base
Team knowledge base: <vault repo URL>
KB_VAULT (your local clone path) lives in CLAUDE.local.md, not committed.
If undefined, ask the user and offer to write it into CLAUDE.local.md.
On build/environment/dependency problems, search the knowledge base first (kb-search skill in the vault's .claude/skills/).
```

Each person then puts `KB_VAULT: /their/path` in their own `CLAUDE.local.md`
(ensure it is git-ignored — `.git/info/exclude` works without touching the repo).
