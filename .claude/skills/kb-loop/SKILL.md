---
name: kb-loop
description: Use when asked to run the knowledge-base maintenance loop ("kb-loop", "run the loop") inside a loopkb vault. Executes triage → refine → reflect → lint per _meta/loop.md.
---

# kb-loop

Run the maintenance loop. You MUST be inside the vault repo.

## Pre-flight

1. Read `CLAUDE.md`, `_meta/instance.md` (its policies override CLAUDE.md, and its
   "Classification rule amendments" section overrides `_meta/taxonomy.md`),
   `_meta/taxonomy.md`, and `_meta/loop.md` in full. Taxonomy and amendments are one
   rule set read together. `_meta/loop.md` is the pipeline spec — this skill only
   orchestrates it.
2. **Read the governance mode**: `_meta/instance.md` → Governance → Mode. `autonomous`
   or `reviewed`; an absent or unrecognised value means `autonomous` (the framework
   default). Every channel decision below and in `_meta/loop.md` depends on it — decide
   it once here, state it in the digest header, and never mix the two within a run.
3. **Setup gate**: if the domain tag vocabulary in `_meta/instance.md` is empty, STOP
   and tell the user to fill it first — triage cannot classify against an empty
   vocabulary, and an unset-up vault has no `_meta/` write rule in force yet.
4. `git status` — if there are uncommitted changes outside `_inbox/`, STOP and ask the
   user; that is someone's work in progress.
5. **Take the lease**: pick a run id for this run (`kb-loop-<YYYYMMDD-HHMMSS>` will do)
   and pass it to every lease command of the run:
   `python3 scripts/lease.py acquire --session <run-id>`. Exit 1 means another run
   holds it — report who and stop. Nothing below runs without the lease.
   State the run id explicitly: each command you issue is a separate process, and the
   lock's default session identity is the parent shell — so a `release` without
   `--session <run-id>` refuses the very lock this run holds, and the vault stays
   locked for the rest of the TTL.
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
- Before redoing anything, **re-derive the rejection memory from git** — never read it
  out of the previous digest: `git log --no-merges --grep="This reverts" --format='%H %s'`
  over the FULL history, then resolve each `This reverts commit <sha>` and keep the ones
  whose reverted subject carries a `[kb-loop]`/`[kb-save]` prefix. Those actions are not
  re-attempted unless the notes involved have materially changed (loop.md Stage 3).
- Rule changes learned this run go into `_meta/instance.md` → "Classification rule
  amendments", never into `_meta/taxonomy.md` (framework-owned).
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
opening anything, query the platform for open `kb-loop/*` MRs and recently closed ones —
per run, from the platform itself, not from the last digest — and do not re-propose what
is pending or what was already rejected (see loop.md, Stage 3).
Budget: 3 MRs per run, 1 reserved for reflect.

Branch hygiene: delete `kb-loop/*` branches locally and on the remote once their MR
is merged or closed (`git push origin --delete <branch>`; `git branch -D <branch>`).

## After

1. Write the digest to `_meta/digest.md` (overwrite it; the structure is in
   `_meta/loop.md` → The digest) — but do **not** commit it yet. "Risky actions" comes
   first and carries the short commit SHA of every risky action in `autonomous` mode,
   or the open MR URLs in `reviewed` mode; write `none` when the section is empty. Every
   risky commit already exists at this point, so every SHA is available.
2. Run `python3 scripts/verify_digest.py`; if it fails, complete the digest and rerun —
   never commit the report over a failing verifier. It lists any risky action of this
   run (deletion or rename under a type folder, `_meta/` change, status demotion) whose
   short SHA is missing from the digest.
3. Commit the digest with the same text in the message body:
   `[kb-loop] run report: <YYYY-MM-DD>`. This is the last commit of the run — it is the
   window marker both reflect and the verifier use next time.
4. Push main — unless the vault has no `origin` remote, in which case skip the push
   (and the pre-flight pull): a local-only vault is a valid setup, not an error.
   On conflict: rebase and retry; if the conflict cannot be resolved,
   abort, keep the work on a local branch, and tell the user sync is pending.
   Never force-push main (see CLAUDE.md guardrails for the `kb-loop/*` branch rule).
5. **Release the lease**: `python3 scripts/lease.py release --session <run-id>` — the same
   run id pre-flight acquired with. Do this on every exit path
   after a *successful* acquire, aborts and errors included — a lease left behind blocks
   the next run for two hours. If pre-flight step 5 failed, do NOT release: that lock is
   the other run's, and `release` refuses it (exit 1) for exactly that reason. A release
   that exits 1 for any reason — someone else's live lock, or an unreachable `origin` —
   means the lease is still held; report it rather than treating the run as clean.
6. Tell the user: what was processed; the risky actions they may want to revert
   (`autonomous`) or the MRs awaiting review (`reviewed`); evergreen nominations;
   items stuck in inbox and what context they need; and the final `scripts/lint.py`
   exit status. Point them at `_meta/digest.md` — that is where it all lives.
