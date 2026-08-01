---
name: kb-save
description: Use when the user wants to save knowledge from the current conversation into the loopkb vault — "save this to the knowledge base", "kb-save". Extracts the knowledge, classifies it, and files it (or inboxes it when unsure).
---

# kb-save — loopkb entry point

A pointer, not a procedure: the vault owns the procedure.

1. Resolve the vault. If the current repo contains `_meta/loop.md` it IS the vault. Else
   use the `KB_VAULT:` line already in context; else list `~/.claude/*.md` and read each
   one for a `KB_VAULT:` line. Two or more vaults → ask which. None → run kb-setup first.
2. Read `<KB_VAULT>/.claude/skills/kb-save/SKILL.md` in full and follow it exactly —
   including the commit prefix, the secret-stripping rule and the write tiers.
