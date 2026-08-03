---
name: kb-setup
description: Use when asked to set up or join a loopkb vault — "kb-setup <git url>", "set up the knowledge base", "join the team vault". Clones the vault, validates it, and wires this machine's KB_VAULT path.
---

# kb-setup — loopkb entry point

A pointer, not a procedure. Usually no vault exists yet, so read whichever copy is
reachable:

0. If the current repo contains `_meta/loop.md`, it IS a loopkb vault — no URL to ask
   for and nothing to clone. Read `./.claude/skills/kb-setup/SKILL.md` and follow its own
   step 0, which takes this repo's root as the vault and skips to validation and wiring.
   (This file ships inside every vault, so opening a vault in Codex is the common way to
   land here.)
1. A `KB_VAULT:` line in context or in one of `~/.claude/*.md` whose path has
   `_meta/loop.md` → read `<KB_VAULT>/.claude/skills/kb-setup/SKILL.md`.
2. Otherwise fetch `https://raw.githubusercontent.com/jasonw-dev/loopkb/main/.claude/skills/kb-setup/SKILL.md`
   (the default sandbox denies network — approve the request when Codex asks).
3. Follow it exactly; never run `git clone` before the user has confirmed the path.
   Neither copy reachable → GETTING-STARTED.md → "Joining a vault" → "Any other agent".
