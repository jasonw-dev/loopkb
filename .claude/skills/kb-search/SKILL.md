---
name: kb-search
description: Use when solving a problem that the team may have hit before — build/environment/dependency errors, tooling setup, release procedures — or when explicitly asked to search the knowledge base ("kb-search").
---

# kb-search

Search the team knowledge base before re-deriving a solution from scratch.

## Locate the vault

Same resolution as kb-save: the `KB_VAULT` line in your loaded context (imported
from the per-user file); else glob `~/.claude/*.md` for a `KB_VAULT:` line before
asking anything — `kb-setup` may have written one this repo does not import; else
ask once and offer to create that file — or run `kb-setup <vault url>`, which is
what normally creates it.
If the vault clone is missing or stale, `git -C <vault> pull --rebase` first (skip on network failure — search the local copy).

## Steps

1. Read `<vault>/_meta/taxonomy.md` for the type folders and `<vault>/_meta/instance.md`
   for the domain tag vocabulary and vault scope.
2. Search in this order:
   - Filename scan of the likely type folder (filenames are descriptive kebab-case).
   - `grep -ril` across the vault for error-message fragments, tool names, tag values.
3. Rank hits: `status: evergreen` > `curated` > `raw`. Prefer newer `created` on conflict.
   The order is not decoration: `curated` means an agent met a mechanical floor, while
   `evergreen` means a human stood behind the note and conferred that status by hand.
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

The import above loads the per-user KB_VAULT setting. It is normally written by
kb-setup. If undefined, run kb-setup with the vault URL above, or ask the user for
their clone path and offer to create ~/.claude/<vault-name>.md with a
`KB_VAULT: /path` line.
The kb-save / kb-search / kb-loop procedures are defined in
`<KB_VAULT>/.claude/skills/<name>/SKILL.md` — read the relevant file before acting.
On build/environment/dependency problems, search the knowledge base first (kb-search).
After solving a non-trivial problem worth sharing, save it with kb-save.
```

Substitute `<vault repo URL>` and `<vault-name>` with the real values; leave `<KB_VAULT>`
literal — it is not a placeholder for you to fill, agents resolve it at runtime from the
imported per-user file.

`<vault-name>` is the vault repo's basename without `.git` (`git@host:team/team-kb.git` →
`team-kb`) — the same rule `kb-setup` uses when it writes the file. Use any other name and
kb-setup writes a file this import never reads.

Each person creates `~/.claude/<vault-name>.md` once — `kb-setup` writes it when they
join the vault. Every repo wired to the same vault imports the same file, so the path
is configured a single time per machine.

For Claude Code users, installing the vault as a plugin (see the framework README)
loads these procedures in every repo as `/loopkb:kb-search` and `/loopkb:kb-save`,
without the per-repo wiring above. The `KB_VAULT` line is still needed to say *which*
vault to read.

If the project repo also serves non-Claude agents, put the same section (or a
pointer to CLAUDE.md) in its AGENTS.md — those agents do not read CLAUDE.md by default.
`@~/.claude/<vault-name>.md` is **Claude Code import syntax**, not a general convention:
a non-Claude agent must open `~/.claude/<vault-name>.md` itself and read the `KB_VAULT:`
line out of it. Say that explicitly in the AGENTS.md copy.
