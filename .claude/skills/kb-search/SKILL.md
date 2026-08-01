---
name: kb-search
description: Use when solving a problem that the team may have hit before — build/environment/dependency errors, tooling setup, release procedures — or when explicitly asked to search the knowledge base ("kb-search", "查知識庫").
---

# kb-search

Search the team knowledge base before re-deriving a solution from scratch.

## Locate the vault

Same resolution as kb-save: the `KB_VAULT` line in your loaded context (imported
from the per-user file), else ask once and offer to create that file.
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

@~/.claude/<vault-name>.md

The import above loads the per-user KB_VAULT setting. If undefined, ask the user
for their clone path and offer to create ~/.claude/<vault-name>.md with a
`KB_VAULT: /path` line.
On build/environment/dependency problems, search the knowledge base first (kb-search skill in the vault's .claude/skills/).
```

Each person creates `~/.claude/<vault-name>.md` once — every repo wired to the same
vault imports the same file, so the path is configured a single time per machine.
