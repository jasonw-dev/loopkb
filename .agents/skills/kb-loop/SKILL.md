---
name: kb-loop
description: Use when asked to run the loopkb knowledge-base maintenance loop ("kb-loop", "run the loop"). Executes triage → refine → reflect → lint inside the vault repo per its _meta/loop.md.
---

# kb-loop — loopkb entry point

A pointer, not a procedure: the vault owns the procedure.

0. If the current repo contains `_meta/loop.md`, it IS the vault — use it as `<KB_VAULT>`
   and skip step 1 entirely. This is the intended way to run the loop: the vault is the
   workspace, so no write lands outside it. (This file ships inside every vault.)
1. Otherwise resolve the vault: the `KB_VAULT:` line in context, else a `KB_VAULT:` line
   in one of `~/.claude/*.md`. Two or more vaults → ask which. None → run kb-setup first.
2. Work inside `<KB_VAULT>` — this loop only runs in the vault repo itself. Git pushes
   and pulls need network, which the default sandbox denies until you approve them.
3. Read `<KB_VAULT>/.claude/skills/kb-loop/SKILL.md` in full and follow it exactly,
   including the pre-flight lease and the digest verification before the report commit.
