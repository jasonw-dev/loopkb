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
2. **Read the governance mode**: `_meta/instance.md` → Governance → Mode. `autonomous`
   or `reviewed`; an absent or unrecognised value means `autonomous` (the framework
   default). Every channel decision below and in `_meta/loop.md` depends on it — decide
   it once here, state it in the digest header, and never mix the two within a run.
3. **Setup gate**: if the domain tag vocabulary in `_meta/instance.md` is empty, STOP
   and tell the user to fill it first — triage cannot classify against an empty
   vocabulary, and an unset-up vault has no `_meta/` write rule in force yet.
4. `git status` — if there are uncommitted changes outside `_inbox/`, STOP and ask the
   user; that is someone's work in progress.
5. **Take the lease**: `python3 scripts/lease.py acquire`. Exit 1 means another run
   holds it — report who and stop. Nothing below runs without the lease.
6. `git pull --rebase --autostash` (inbox may legitimately hold uncommitted human
   annotations — autostash carries them across the rebase).
   If the autostash pop conflicts: do not discard either side. Keep the rebased file
   as-is, write the stashed human text to a separate `_inbox/<name>-human-<YYYYMMDD>.md`
   file, remove every conflict marker from both files, report the split, and continue.

## Execute

Run the stages of `_meta/loop.md` strictly in order: Triage → Refine → Reflect → Lint.
Respect per-run limits. Apply write tiers from CLAUDE.md for the active mode, plus any
instance overrides.

### `autonomous` mode (the default)

Everything is a direct commit on `main` — merges, deletions, moves, renames, rewrites
and `_meta/` rule changes included. No branches, no MRs, no platform API.

- Keep each risky action in **one self-contained commit** so `git revert <sha>` undoes
  it cleanly: a merge deletes the originals and retargets inbound wikilinks in that
  same commit; a rename retargets its links in that same commit.
- Record every risky action for the digest as you go — action, notes involved, reason,
  commit SHA. Do not reconstruct the list at the end.
- Before redoing anything: check the rejection memory (loop.md Stage 3). A human
  `git revert` of a `[kb-loop]`/`[kb-save]` commit is a rejection; do not re-attempt
  that action unless the notes involved have materially changed.
- `curated → evergreen` is still off-limits — nominate it in the digest instead.

### `reviewed` mode

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
Budget: 3 MRs per run, 1 reserved for reflect.

Branch hygiene: delete `kb-loop/*` branches locally and on the remote once their MR
is merged or closed (`git push origin --delete <branch>`; `git branch -D <branch>`).

## After

1. Write the digest to `_meta/digest.md` (overwrite it; the structure is in
   `_meta/loop.md` → The digest) and commit it with the same text in the message body:
   `[kb-loop] run report: <YYYY-MM-DD>`. "Risky actions" comes first and carries the
   commit SHAs in `autonomous` mode, or the open MR URLs in `reviewed` mode; write
   `none` when the section is empty.
2. Push main. On conflict: rebase and retry; if the conflict cannot be resolved,
   abort, keep the work on a local branch, and tell the user sync is pending.
   Never force-push main (see CLAUDE.md guardrails for the `kb-loop/*` branch rule).
3. **Release the lease**: `python3 scripts/lease.py release`. Do this on every exit
   path, including aborts and errors — a lease left behind blocks the next run for
   two hours.
4. Tell the user: what was processed; the risky actions they may want to revert
   (`autonomous`) or the MRs awaiting review (`reviewed`); evergreen nominations;
   items stuck in inbox and what context they need; and the final `scripts/lint.py`
   exit status. Point them at `_meta/digest.md` — that is where it all lives.
