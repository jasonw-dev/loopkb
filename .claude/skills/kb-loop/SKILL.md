---
name: kb-loop
description: Use when asked to run the knowledge-base maintenance loop ("kb-loop", "run the loop") inside a loopkb vault. Executes triage → refine → reflect → lint per _meta/loop.md.
---

# kb-loop

Run the maintenance loop. You MUST be inside the vault repo.

## Before anything

1. Read `CLAUDE.md` (write tiers, guardrails, instance overrides), `_meta/taxonomy.md`,
   and `_meta/loop.md` in full. `_meta/loop.md` is the pipeline spec — this skill only
   orchestrates it.
2. If the domain tag vocabulary in `_meta/taxonomy.md` is empty, STOP and tell the
   user to fill it first — triage cannot classify against an empty vocabulary.
3. `git status` — if there are uncommitted changes outside `_inbox/`, STOP and ask the
   user; that is someone's work in progress.
4. `git pull --rebase`.

## Execute

Run the four stages of `_meta/loop.md` strictly in order: Triage → Refine → Reflect → Lint.
Respect per-run limits. Apply write tiers from CLAUDE.md (including any instance
overrides — e.g. an instance may route ALL refine operations through MRs during a
trial period).

MR mechanics (when a stage requires the MR channel):
```
git checkout -b kb-loop/<short-topic>
# ...changes...
git commit -m "[kb-loop] <what and why>"
git push -u origin kb-loop/<short-topic>
# open MR via the platform CLI/API (glab / gh / REST), title prefixed [kb-loop]
git checkout main
```

## After

1. Write the run report (per `_meta/loop.md` format) into the final commit message body.
2. Push main. On conflict: rebase, retry. Never force-push.
3. Tell the user: what was processed, MRs awaiting review, items stuck in inbox and
   what context they need.
