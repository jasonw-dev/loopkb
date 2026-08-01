---
name: kb-loop
description: Use when asked to run the knowledge-base maintenance loop ("kb-loop", "run the loop") inside a loopkb vault. Executes triage → refine → reflect → lint per _meta/loop.md.
---

# kb-loop

Run the maintenance loop. You MUST be inside the vault repo.

## Pre-flight

1. Read `CLAUDE.md`, `_meta/instance.md` (its policies override CLAUDE.md),
   `_meta/taxonomy.md`, and `_meta/loop.md` in full. `_meta/loop.md` is the pipeline
   spec — this skill only orchestrates it.
2. **Setup gate**: if the domain tag vocabulary in `_meta/instance.md` is empty, STOP
   and tell the user to fill it first — triage cannot classify against an empty
   vocabulary, and an unset-up vault has no `_meta/` MR-only rule yet.
3. `git status` — if there are uncommitted changes outside `_inbox/`, STOP and ask the
   user; that is someone's work in progress.
4. **Take the lease**: `python3 scripts/lease.py acquire`. Exit 1 means another run
   holds it — report who and stop. Nothing below runs without the lease.
5. `git pull --rebase --autostash` (inbox may legitimately hold uncommitted human
   annotations — autostash carries them across the rebase).
   If the autostash pop conflicts: do not discard either side. Keep the rebased file
   as-is, write the stashed human text to a separate `_inbox/<name>-human-<YYYYMMDD>.md`
   file, remove every conflict marker from both files, report the split, and continue.

## Execute

Run the stages of `_meta/loop.md` strictly in order: Triage → Refine → Reflect → Lint.
Respect per-run limits. Apply write tiers from CLAUDE.md plus any instance overrides
(e.g. an instance may route ALL refine operations through MRs during a trial period).

MR mechanics (when a stage requires the MR channel):
```
git push origin main                      # push direct-commit work FIRST
git fetch origin
git checkout -b kb-loop/<short-topic>-$(date +%Y%m%d) origin/main
# ...changes...
git commit -m "[kb-loop] <what and why>"
git push -u origin kb-loop/<short-topic>-$(date +%Y%m%d)
# open MR via the platform CLI/API (gh / glab / REST), title prefixed [kb-loop]
git checkout main
```
Branching from `origin/main` keeps each MR diff limited to its own changes. Before
opening anything, list open `kb-loop/*` MRs and recently closed ones — do not
re-propose what is pending or what was already rejected (see loop.md, Stage 3).

Branch hygiene: delete `kb-loop/*` branches locally and on the remote once their MR
is merged or closed (`git push origin --delete <branch>`; `git branch -D <branch>`).

## After

1. Write the run report (per `_meta/loop.md` format) into the final commit message body.
2. Push main. On conflict: rebase and retry; if the conflict cannot be resolved,
   abort, keep the work on a local branch, and tell the user sync is pending.
   Never force-push main (see CLAUDE.md guardrails for the `kb-loop/*` branch rule).
3. **Release the lease**: `python3 scripts/lease.py release`. Do this on every exit
   path, including aborts and errors — a lease left behind blocks the next run for
   two hours.
4. Tell the user: what was processed, MRs awaiting review, items stuck in inbox and
   what context they need, and the final `scripts/lint.py` exit status.
