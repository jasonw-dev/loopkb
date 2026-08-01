---
name: kb-save
description: Use when the user wants to save knowledge from the current conversation into the loopkb vault — "save this to the knowledge base", "kb-save". Extracts the knowledge, classifies it, and files it (or inboxes it when unsure).
---

# kb-save

Save knowledge from the current conversation into the vault.

## Locate the vault

Check, in order:
0. If the current repo IS a loopkb vault (it contains `_meta/loop.md`), use it directly.
1. The `KB_VAULT` line already in your loaded context — wired projects' CLAUDE.md
   imports it from a per-user file (e.g. `@~/.claude/<vault-name>.md`).
2. Ask the user once, then offer to create that per-user file with the
   `KB_VAULT: /path` line (never write a personal path into a committed file).
   That file is normally written by `kb-setup` when the user joins the vault, so its
   absence usually means kb-setup was never run — offer that instead if they have no
   clone yet.

## Steps

1. **Extract**: Write the knowledge as a self-contained note — a reader with zero
   conversation context must understand it. Include exact commands, versions,
   error messages. Strip conversational noise.
2. **Classify**: Apply the decision rules in `<vault>/_meta/taxonomy.md`. Determine
   type, domains (closed vocabulary in `<vault>/_meta/instance.md` — never invent
   tags), projects.
3. **File it**:
   - **Confident** (clear type match, no obvious duplicate — grep the type folder
     for overlapping filenames/keywords first): instantiate
     `<vault>/_meta/templates/<type>.md`, fill it, name per naming rules, save to the
     type folder with `status: raw`; `source` per taxonomy.md's Source field rules
     (meeting material → `meeting`, otherwise `conversation`).
   - **Not confident** (ambiguous type, possible duplicate, tag not in vocabulary):
     save the raw extraction to `<vault>/_inbox/<slug>.md` with a leading comment
     stating what is unclear. The loop will handle it.
4. **Commit and push** (in the vault):
   ```
   git pull --rebase --autostash
   git add <file> && git commit -m "[kb-save] <type>: <title>"
   git push
   ```
   If the rebase hits conflicts: abort it, commit the new note locally, and tell the
   user sync is pending. If push fails on network (vault remote unreachable), commit
   locally and tell the user push is pending.

## Rules

- One note per distinct piece of knowledge, one note per commit. Two problems solved =
  two notes. A human who disagrees with a save reverts that commit, and the loop's
  reflect stage reads that revert as a correction signal — so a commit that carries
  two unrelated notes cannot be rejected cleanly.
- Follow the vault's CLAUDE.md write tiers: kb-save only ADDS notes. Never modify
  existing notes from this skill — that is the loop's job. This is additive in both
  governance modes, so kb-save never needs to know which mode the vault runs in.
- Body language: per `_meta/instance.md` → Identity (English when unset).
- New notes are always `status: raw`. Never write `curated` or `evergreen` here.
