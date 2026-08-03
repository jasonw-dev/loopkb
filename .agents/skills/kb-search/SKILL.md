---
name: kb-search
description: Use when solving a problem the team may have hit before — build, environment, dependency or tooling errors, release procedures — or when explicitly asked to "kb-search". Searches the loopkb knowledge base vault.
---

# kb-search — loopkb entry point

A pointer, not a procedure: the vault owns the procedure.

0. If the current repo contains `_meta/loop.md`, it IS the vault — use it as `<KB_VAULT>`
   and skip step 1 entirely. (This file ships inside every vault, so you are often already
   standing in one.)
1. Otherwise resolve the vault: use the `KB_VAULT:` line if it is already in context;
   otherwise list `~/.claude/*.md` and read each one for a `KB_VAULT:` line. Two or more
   vaults → ask which. None → this machine is not wired yet; run kb-setup first.
2. Read `<KB_VAULT>/.claude/skills/kb-search/SKILL.md` in full and follow it exactly.
   It is agent-agnostic; where it names Claude Code, use the equivalent here.
