# Maintenance Loop

The loop is **stateless**: everything it needs is derived from the repo itself
(inbox contents, frontmatter status, git history) and — in `reviewed` mode only —
from the MR platform (open and recently closed proposals). It can run from any
machine, any time, and safely stop midway — the next run picks up naturally.

Run stages strictly in order. Respect the write tiers in `CLAUDE.md` and any
overrides in `_meta/instance.md`.

## Mode first

Read `_meta/instance.md` → Governance before Stage 1; absent field ⇒ `autonomous`.
The mode decides every channel below:

| | `autonomous` (default) | `reviewed` |
|---|---|---|
| Destructive actions (merge, delete, move, rename, rewrite) | direct commit + digest "Risky actions" line | branch + MR |
| `_meta/` rule change (reflect) | direct commit + digest line | branch + MR |
| Evergreen | digest nomination line | nomination MR |
| Rejection signal | human `git revert` of a `[kb-loop]`/`[kb-save]` commit | MR closed unmerged + review comments |
| Platform API needed | **no** — pure git | yes, degrading to git-only |
| MR budget / branch hygiene | n/a | applies |

Everything additive (triage filings, links, tags, formatting, `raw → curated`) is a
direct commit in both modes.

## Stage 0 — Take the lease

Only one loop run may be in flight at a time; two concurrent runs produce duplicate
work (competing commits in `autonomous`, duplicate proposals in `reviewed`), rebase
storms, and two digests that each describe half a run. This holds in both modes.

```
python3 scripts/lease.py acquire      # exit 1 = someone else is running; stop
...the run...
python3 scripts/lease.py release      # on every exit path AFTER a successful acquire
```

The lease is an orphan branch `kb-loop-lock` on `origin` recording holder and
acquisition time. A lock older than 2 hours is stale and may be replaced. With no
remote (solo vault) it degrades to a local ref with the same semantics. A run that
aborts for any reason releases the lease before reporting — provided it acquired one.
After a *failed* acquire there is nothing to release: the lock belongs to the run that
won the race, and `release` refuses to delete it (exit 1) until it goes stale, so the
loser cannot end the winner's exclusivity. `--force` exists for a run known to be dead
before its TTL. A release that cannot reach `origin` also exits 1 and says so: the local
ref is gone, but every other clone sees the lock until the TTL expires.

## Stage 1 — Triage (empty the inbox)

For each item in `_inbox/`:

1. Decide the type using `_meta/taxonomy.md` decision rules **together with the
   amendments in `_meta/instance.md` → "Classification rule amendments"** — the taxonomy
   is the framework's rule set, the amendments are what this vault has learned, and an
   amendment wins where the two disagree.
2. **Commit the original first**: if the item is untracked OR has uncommitted
   modifications, commit it as-is before filing — the raw original must exist in git
   history before filing rewrites it.
3. Instantiate the matching template from `_meta/templates/`, fill frontmatter
   (`status: raw`; `source` per taxonomy.md's Source field rules — `meeting` for
   meeting material, otherwise `inbox`; `created` = today), name per naming rules.
4. Move content into the type folder; delete the inbox item in the same commit.
5. If the type cannot be decided confidently: leave the item in `_inbox/` and prepend
   a visible callout (`> [!note] kb-loop: cannot classify — …`) so a human can add
   context. Never use HTML comments — they are invisible in Obsidian's reading view.
6. **Apparent secrets are never filed**: an item containing a credential, token, private
   key or personal data stays in `_inbox/` with the rotation callout — see
   `_meta/taxonomy.md` → "What does NOT belong", which also explains why rotation, not
   deletion, is the remedy.
7. **Contradiction reports are routed, not filed**: an item that reports two notes making
   conflicting claims (kb-search writes them, `[kb-save] contradiction: …`) is a work item,
   not knowledge — it names no new fact, so it gets no type folder. Leave it in `_inbox/`
   and hand it to Stage 2b of the same run, which resolves the conflict and deletes the item
   in the resolving commit, or leaves it for the human with a callout and a Stuck line.
8. **Skip items already annotated**: if an item already carries a kb-loop callout and
   has had no human modification since the last run (`git log` on the file shows no
   unprefixed commit after the annotating one, and it has no uncommitted changes),
   leave it untouched and list it in the digest instead of re-annotating.

Channel: direct commit (additive) — both modes.

## Stage 2 — Refine (push notes up the status ladder)

Budget: **10 notes per run**, shared by both steps below.

### 2a — Freshness check (1–2 notes)

Take the 1–2 `curated`/`evergreen` notes whose last *content* change is oldest
(`git log --follow --format='%H %ad' -- <file>`; ignore commits that only touched
formatting or frontmatter when that is determinable from the diff). For each:

- Verify the content is still accurate (check the sources it cites, the commands it
  gives, the versions it names).
- Still accurate → record the check in the digest, change nothing.
- Stale but not wrong → demote one level with the reason in the commit message
  (direct commit in both modes; `autonomous` also logs it as a risky action).
- Wrong, content must change → rewrite channel: `autonomous` = direct commit plus a
  digest risky-action line stating what changed and why; `reviewed` = correction MR.

### 2b — Improve notes (the remaining budget)

Pick notes: all `raw` before any `curated`; within a status, oldest frontmatter
`created` first, ties broken by filename.

- Add wikilinks to related notes (search by tags and keywords first).
- Fix formatting to match the type template; fill missing frontmatter.
- Promote `raw → curated` when the floor in `_meta/taxonomy.md` is met (direct commit).
  `curated → evergreen` is human-conferred in both modes: an agent may only *nominate* —
  a digest line in `autonomous`, an MR in `reviewed`.
- Before merging or distilling anything, derive the rejection memory (Stage 3 — from git,
  not from the last digest) and skip what it names. In `reviewed` mode additionally list open
  `kb-loop/*` branches and MRs and skip anything already pending review — the repo
  alone is not the whole state there, the platform holds open proposals. In
  `autonomous` mode there is nothing pending by construction: work either landed on
  `main` or was reverted.
- **Reconcile contradictions on sight.** The tag/keyword search above (and any
  contradiction report triage handed over from `_inbox/` — kb-search writes them) will surface
  notes that make *conflicting* claims, not just related ones. Resolve them in this run
  rather than deferring: merge the pair, or correct the wrong note, through the normal
  channels for those actions (risky → itemized in the digest as usual). This is the only
  systematic contradiction detection the framework has, so a conflict seen and postponed is
  a conflict nobody looks for again.
  When you cannot tell which side is right — both notes cite plausible sources, neither is
  reproducible from here — do not guess: **demote the doubtful note one level** with the
  reason in the commit message (name the other note), and list the conflict under the
  digest's **Stuck** section with both notes, the conflicting claims, and what would decide
  it. A contradiction report from `_inbox/` is consumed the same way: resolved here, or
  moved to Stuck. It counts against the refine budget like any other note worked on.
  The same duty attaches to **any** rewrite of an existing note, in this stage or outside
  a loop run entirely: re-read the note's wikilink neighborhood — outbound links plus
  inbound ones found with `grep -rl "\[\[<basename>\]\]"` — and reconcile what it
  surfaces (`CLAUDE.md` → Guardrails 6, which states the rule for all agents).
- If two or more notes overlap heavily: merge them. One commit (or one MR in
  `reviewed` mode) deletes the originals — their full text stays reviewable in the
  deleted-file diff — and retargets every inbound wikilink; no follow-up commits.
- If several `troubleshooting` notes share a theme: distil them into one `guides`
  note, same mechanics (originals deleted, inbound links retargeted, everything
  reviewable in one diff).

Channel: direct commit for links/tags/format/`raw → curated` in both modes. For
merge/distill/move/rewrite: `autonomous` = direct commit, one digest risky-action line
per action naming the notes involved and the reason; `reviewed` = MR.

## Stage 3 — Reflect (learn from human corrections)

### Signals

The window starts at the **previous run's report commit** (message starting
`[kb-loop] run report`) and excludes commits made by the current run. First run ever:
scan the full history. (Do NOT use "last `[kb-loop]` commit" as the marker — the
current run's own triage commits would shrink the window to zero.)

Two kinds of correction signal carry equal weight. Signal 1 is the same in both
modes; signal 2 is where the modes differ.

1. **Unprefixed human commits that override agent actions** — moved files, changed
   types/tags, renamed files, hand-undone agent edits. Ignore merge commits (e.g.
   platform-generated merges of `kb-loop/*` branches): they carry no prefix but are
   not corrections. A revert commit is unprefixed too — classify it as signal 2 and
   count it **once**, not as both signals.

2. **The rejection signal, per mode:**

   - `autonomous` — **a human `git revert` of a `[kb-loop]` or `[kb-save]` commit**.
     Find them with `git log --no-merges` over the window and match either the
     `Revert "<original subject>"` subject or the `This reverts commit <sha>` line
     git writes into the body; resolve `<sha>` and check whether its subject carries
     an agent prefix. A revert is an explicit "no" to a specific action — it is the
     exact equivalent of a closed MR and feeds pattern analysis identically.
     **This mode needs no platform API at all**: reverts are plain git, so reflect is
     fully functional offline, in a solo vault, and on any host.
   - `reviewed` — **`[kb-loop]` MRs closed WITHOUT merge** since the last reflect,
     together with their review comments. A closed proposal is a strong correction
     signal: a human looked at the agent's reasoning and rejected it.

**Rejection memory** covers both forms, and every run **re-derives the whole set from
scratch** — it is never copied forward from the last digest. In `autonomous` mode, over
the FULL history (not the window):

```
git log --no-merges --grep="This reverts" --format='%H %s'
```

For each hit, resolve the `This reverts commit <sha>` line in its body and keep the ones
whose reverted commit's subject carries an agent prefix. That set *is* the rejection
memory — plain git, no state file, nothing to lose. In `reviewed` mode the platform's
closed-MR list is queried per run for the same reason.

An action that was rejected — a reverted commit in `autonomous`, an unmerged closed MR in
`reviewed` — must NOT be redone unless the notes involved have materially changed since
(their *content* changed, not just frontmatter or formatting).

The digest still **lists** the rejection set, for the human. That listing is display only:
a lost, stale or hand-edited digest costs the loop nothing, because the next run derives
the same set again from history.

Nothing distinguishes a revert of a merge from a revert of a rename: the rule is
per-action. Re-attempting a reverted action without new evidence is the single worst
failure mode of `autonomous` mode, because it costs the human the same revert twice.

**Platform unreachable** (`reviewed` mode, offline or the API is down): run on signal 1
alone, take no rejection signal from guesswork, and say in the digest that the run was
git-only so the human knows the closed-MR half was not read. Do **not** infer rejections
from branch state: a deleted `kb-loop/*` branch is as likely to be hygiene after a merge
as a rejection, and a wrong rejection is permanent — it suppresses a correct action
forever. Wait for the platform instead. In `autonomous` mode none of this applies: the
rejection signal is `git revert`, which is always available.

### Analysis

1. Group corrections by kind. A **pattern** is the same kind of correction seen ≥ 2
   times, counted across the full history — the window bounds discovery of NEW
   corrections; pattern counting accumulates.
2. **Counting resets per pattern** once a rule change addressing that pattern lands
   *or* is rejected: count only corrections that happened after that resolution. A
   landed change fixed the rule; a rejection (revert in `autonomous`, closed MR in
   `reviewed`) means the human rejected that reading, and re-proposing on the same
   old evidence is noise.
3. `reviewed` mode: do not propose while an open `[kb-loop]` proposal MR already
   covers the pattern — dedup against open proposals before drafting anything.
   `autonomous` mode: do not re-apply a rule change the human reverted.
4. Draft the change **into `_meta/instance.md`** — never into `_meta/taxonomy.md`, which
   is framework-owned and read-only for agents (a template merge would overwrite anything
   written there). A type-criteria, naming or source-field change becomes a dated entry
   under "Classification rule amendments" that extends or overrides the taxonomy line it
   addresses; a new domain tag or a policy change goes to its own section, as before.
   Amendments are read together with `_meta/taxonomy.md` on every classification, and
   they win — which is also what makes them survive `git merge upstream/main`.
5. Land it through the mode's `_meta/` channel:
   - `autonomous` — commit it to `main` directly, message
     `[kb-loop] rule amendment: <summary>`, and give it a digest risky-action line
     stating the observed corrections (with commit refs), the rule change, and the
     expected effect. The human reverts the commit if they disagree; that revert is
     next run's signal 2.
   - `reviewed` — open an MR titled `[kb-loop] rule amendment proposal: <summary>` with
     the same explanation (commit refs and closed-MR refs), and wait.

Rules are the constitution. Once setup is complete (the domain vocabulary in
`_meta/instance.md` is non-empty), a `_meta/` change is never silent: it is either an
MR (`reviewed`) or a commit itemized in the digest (`autonomous`). Instantiation edits
before that gate are the one exemption.

## Stage 4 — Lint (health check)

```
python3 scripts/lint.py
```

The script is the schema's executable definition — it replaces any prose checklist.
It reports one `file: problem` line per violation and exits 1 when the vault is dirty.
It checks the type folders only (`_meta/`, `_inbox/`, `_attachments/`, `.obsidian/`
are skipped) and derives the type-folder set from `_meta/templates/`.

The agent fixes what the script reports:

- Auto-fix what is safe (formatting, missing frontmatter keys, obvious key omissions,
  dangling links whose target was clearly renamed) via direct commit.
- For `type` ≠ folder mismatches, **the folder wins** — humans correct filings by
  moving files, so updating `type:` to match the folder is a safe auto-fix; never
  "fix" the mismatch by moving the file back.
- Anything that needs a judgement call (real content decisions, ambiguous link
  targets, domains that would need a new vocabulary value) goes into the digest, or
  into the reflect rule change when it is a rule problem.

Re-run the script after fixing; the digest states the final exit status.
Instances with CI should run the same command on every push.

## Per-run limits

- Refine: max 10 notes (freshness check included), both modes.
- `reviewed` mode only — open MRs: max 3 per run, of which 1 is reserved for
  reflect's rule-amendment proposal (refine may use at most 2). `autonomous` mode has no
  MR budget; the refine budget alone bounds the run, and reflect lands at most one
  rule change per run.
- Hitting a limit skips the remaining work of that stage only — the pipeline always
  continues through to the digest and the final report commit.

## MR mechanics (`reviewed` mode only)

Skip this whole section in `autonomous` mode: there are no `kb-loop/*` branches, no
MRs and no branch hygiene there — every action is a commit on `main`.

- **Push main first**: push all direct-commit work to `origin/main` before creating the
  first MR branch of the run.
- **Branch from `origin/main`**: `git checkout -b kb-loop/<topic>-<YYYYMMDD> origin/main`,
  so each MR diff contains only its own changes.
- **Date suffix**: branch names end in `-YYYYMMDD` to avoid colliding with leftovers
  from earlier runs.
- **Hygiene**: delete `kb-loop/*` branches (local and remote) once their MR is merged
  or closed. A branch surviving its MR is a lie about what is pending.

## Mechanics clarifications

- **Rejected inbox items**: commit the annotated item (`[kb-loop]` prefix) so the
  rejection survives across machines and runs. Moving the content to its proper home
  and deleting the item is the human's job.
- **Report carrier**: every run ends by writing `_meta/digest.md`, running
  `python3 scripts/verify_digest.py`, and only then committing the digest on `main`
  with the message `[kb-loop] run report: <YYYY-MM-DD>` and the same digest in the
  commit body (use `git commit --allow-empty` only if the digest itself is somehow
  unchanged). This commit is also the reflect stage's window marker for the next run —
  and the verifier's, which is why it must be the last commit of the run.
- **MR descriptions** (`reviewed` mode): MRs are created mid-run; update their
  description with the digest after lint completes.
- **"Connected to related notes"** (curated criterion) is vacuously satisfied while
  the vault has no related notes — say so in the digest (and in the MR when one
  applies). Note that `scripts/lint.py` still requires ≥ 1 wikilink on a `curated`
  note, so a lone first note stays `raw` until it has a sibling to link to.

## The digest

Every run overwrites **`_meta/digest.md`** and repeats it in the report commit body.
Past digests live in git history — never keep an archive in the file. It is
framework-managed state under `_meta/`, so `scripts/lint.py` never schema-checks it.

Sections, in this order:

1. **Header** — date, governance mode, machine (the lease holder).
2. **Risky actions** — FIRST, because it is the only section that can need a human
   today. In `autonomous` mode, one line per applied risky action: merges (which
   notes, why), deletions, moves/renames, `_meta/` rule changes, demotions — each
   line carrying that action's **short commit SHA** so `git revert <sha>` is
   copy-pasteable, and so `scripts/verify_digest.py` can check the list is complete
   (see "Verification" below). Write `none` when there were none. In `reviewed` mode
   this section lists the open MRs awaiting review instead, with their URLs.
3. **Triage** — what was filed, and items skipped as already-annotated.
4. **Refine** — what was improved, which notes were freshness-checked and the verdict.
5. **Reflect** — corrections observed, patterns counted, what was landed or proposed,
   and the rejection memory (reverted SHAs / closed MRs) as it stands. That listing is
   for the human to read, not for the next run to consume: the next run re-derives it.
6. **Lint** — the exit status and anything left unfixed.
7. **Stuck** — inbox items that need human context, and what context each needs; plus
   contradictions refine could not resolve (both notes, the conflicting claims, which one
   was demoted, and what would decide it).
8. **Nominations** — `nominate <note> for evergreen: <reason>`, one per line.
   Un-acted nominations lapse; the next run may re-nominate.

A human reading only the header, "Risky actions" and "Stuck" must be able to decide
whether to act. Everything else is the audit trail.

### Verification — before the report commit

The digest is written LAST but BEFORE the report commit, so every risky action of the
run already exists as a commit and already has a SHA by the time its line is written.
With the digest written and all other work committed:

```
python3 scripts/verify_digest.py      # exit 1 = a risky action has no digest line
```

The script re-derives the risky actions from git — deletions and renames under the type
folders, `_meta/` changes other than `_meta/digest.md` itself, and `status:` demotions —
across the agent commits since the previous report commit, and fails when any of their
short SHAs is absent from `_meta/digest.md`. It prints `missing from digest: <sha>
<subject>` for each. Complete the digest and rerun; **never make the report commit over
a failing verifier.** In `autonomous` mode the digest is the human's only view of the
run, so an unreported risky action is a framework violation, not a formatting slip.

It derives four of the five risky classes. The fifth — a **rewrite** that changes a
note's meaning — looks exactly like a formatting fix to a diff, so the script cannot see
it and a clean exit does not mean the digest is complete: that line is written honestly
or not at all. Git and the freshness check are the recovery path, not the verifier.

In `reviewed` mode a risky agent commit should not be sitting on `main` at all — it
belongs on a `kb-loop/*` branch behind an MR. The verifier flagging one there is
correct behaviour and a useful tripwire: something bypassed the MR channel. Adding a
digest line silences the script but does not make the bypass legitimate — say so in the
digest and route the next one properly.
