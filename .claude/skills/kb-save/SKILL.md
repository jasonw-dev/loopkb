---
name: kb-save
description: Use when the user wants to save knowledge from the current conversation into the loopkb vault — "save this to the knowledge base", "kb-save", "把這個存進知識庫". Extracts the knowledge, classifies it, and files it (or inboxes it when unsure).
---

# kb-save

Save knowledge from the current conversation into the vault.

## Locate the vault

The vault path is personal machine configuration. Check, in order:
1. The `KB_VAULT` line in the project's `CLAUDE.local.md` (or CLAUDE.md) — the
   committed CLAUDE.md carries the vault's repo URL; the local path lives in
   `CLAUDE.local.md`, which is never committed.
2. Ask the user once, then offer to write the path into `CLAUDE.local.md`.

## Steps

1. **Extract**: Write the knowledge as a self-contained note — a reader with zero
   conversation context must understand it. Include exact commands, versions,
   error messages. Strip conversational noise.
2. **Classify**: Apply the decision rules in `<vault>/_meta/taxonomy.md`. Determine
   type, domains (closed vocabulary — never invent tags), projects.
3. **File it**:
   - **Confident** (clear type match, no obvious duplicate — grep the type folder
     for overlapping filenames/keywords first): instantiate
     `<vault>/_meta/templates/<type>.md`, fill it, name per naming rules, save to the
     type folder with `status: raw`, `source: conversation`.
   - **Not confident** (ambiguous type, possible duplicate, tag not in vocabulary):
     save the raw extraction to `<vault>/_inbox/<slug>.md` with a leading comment
     stating what is unclear. The loop will handle it.
4. **Commit and push** (in the vault):
   ```
   git pull --rebase
   git add <file> && git commit -m "[kb-save] <type>: <title>"
   git push
   ```
   If push fails on network (vault remote unreachable), commit locally and tell the
   user push is pending.

## Rules

- One note per distinct piece of knowledge. Two problems solved = two notes.
- Follow the vault's CLAUDE.md write tiers: kb-save only ADDS notes. Never modify
  existing notes from this skill — that is the loop's job.
- Body language: per the instance header in `_meta/taxonomy.md`.
