# Maintenance Loop

The loop is **stateless**: everything it needs is derived from the repo itself
(inbox contents, frontmatter status, git history) and from the MR platform
(open and recently closed proposals). It can run from any machine, any time, and
safely stop midway — the next run picks up naturally.

Run stages strictly in order. Respect the write tiers in `CLAUDE.md` and any
overrides in `_meta/instance.md`.

## Stage 0 — Take the lease

Only one loop run may be in flight at a time; two concurrent runs produce
duplicate proposals and rebase storms.

```
python3 scripts/lease.py acquire      # exit 1 = someone else is running; stop
...the run...
python3 scripts/lease.py release      # also on every abort path
```

The lease is an orphan branch `kb-loop-lock` on `origin` recording holder and
acquisition time. A lock older than 2 hours is stale and may be replaced. With no
remote (solo vault) it degrades to a local ref with the same semantics. A run that
aborts for any reason releases the lease before reporting.

## Stage 1 — Triage (empty the inbox)

For each item in `_inbox/`:

1. Decide the type using `_meta/taxonomy.md` decision rules.
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
6. **Skip items already annotated**: if an item already carries a kb-loop callout and
   has had no human modification since the last run (`git log` on the file shows no
   unprefixed commit after the annotating one, and it has no uncommitted changes),
   leave it untouched and list it in the run report instead of re-annotating.

Channel: direct commit (additive).

## Stage 2 — Refine (push notes up the status ladder)

Budget: **10 notes per run**, shared by both steps below.

### 2a — Freshness check (1–2 notes)

Take the 1–2 `curated`/`evergreen` notes whose last *content* change is oldest
(`git log --follow --format='%H %ad' -- <file>`; ignore commits that only touched
formatting or frontmatter when that is determinable from the diff). For each:

- Verify the content is still accurate (check the sources it cites, the commands it
  gives, the versions it names).
- Still accurate → record the check in the run report, change nothing.
- Stale but not wrong → demote one level with the reason in the commit message
  (direct commit — demotion is additive-tier).
- Wrong, content must change → open a correction MR (rewrite → MR channel).

### 2b — Improve notes (the remaining budget)

Pick notes: all `raw` before any `curated`; within a status, oldest frontmatter
`created` first, ties broken by filename.

- Add wikilinks to related notes (search by tags and keywords first).
- Fix formatting to match the type template; fill missing frontmatter.
- Promote `raw → curated` when the floor in `_meta/taxonomy.md` is met (direct commit).
  `curated → evergreen` is human-conferred: an agent may only *nominate* it in an MR.
- Before proposing any merge/distill: list existing open `kb-loop/*` branches and MRs;
  skip anything already pending review (the repo alone is not the whole state —
  the platform holds open proposals). Also skip anything a previous proposal was
  closed over (Stage 3, rejection memory).
- If two or more notes overlap heavily: propose a merge via MR. The MR itself
  deletes the originals (their full text is reviewable in the deleted-file diff)
  and retargets every inbound wikilink in the same MR — no follow-up commits.
- If several `troubleshooting` notes share a theme: propose distilling them into
  one `guides` note (same MR mechanics: originals deleted, inbound links retargeted,
  everything reviewable in one diff).

Channel: direct commit for links/tags/format/`raw → curated`; MR for merge/distill/move/
rewrite/evergreen nomination.

## Stage 3 — Reflect (learn from human corrections)

### Signals

The window starts at the **previous run's report commit** (message starting
`[kb-loop] run report`) and excludes commits made by the current run. First run ever:
scan the full history. (Do NOT use "last `[kb-loop]` commit" as the marker — the
current run's own triage commits would shrink the window to zero.)

Two kinds of correction signal carry equal weight:

1. **Unprefixed human commits that override agent actions** — moved files, changed
   types/tags, renamed files, reverted agent commits. Ignore merge commits (e.g.
   platform-generated merges of `kb-loop/*` branches): they carry no prefix but are
   not corrections.
2. **`[kb-loop]` MRs closed WITHOUT merge** since the last reflect, together with
   their review comments. A closed proposal is a strong correction signal — a human
   looked at the agent's reasoning and rejected it — and it feeds pattern analysis
   exactly like a file-level correction.

**Rejection memory**: a merge or distill proposal that was closed unmerged must NOT
be re-proposed unless the notes involved have materially changed since (their content
changed, not just frontmatter or formatting). Record rejected pairs/sets in the run
report so the next run can see them without the platform.

**Platform unavailable** (solo vault, offline, no MR platform): degrade to git-only
signals. A `kb-loop/*` branch that was deleted locally without ever being merged into
`main` approximates a rejection; treat it as signal 2. Say in the report that the run
was git-only.

### Analysis

1. Group corrections by kind. A **pattern** is the same kind of correction seen ≥ 2
   times, counted across the full history — the window bounds discovery of NEW
   corrections; pattern counting accumulates.
2. **Counting resets per pattern** once a proposal addressing that pattern is merged
   *or* closed: count only corrections that happened after that MR's resolution. A
   merged proposal fixed the rule; a closed one means the human rejected that reading,
   and re-proposing on the same old evidence is noise.
3. Do not propose while an open `[kb-loop]` proposal MR already covers the pattern —
   dedup against open proposals before drafting anything.
4. Draft the change to `_meta/taxonomy.md` (framework rules) or `_meta/instance.md`
   (vocabulary, policy) that would have prevented the misclassification.
5. Open an MR titled `[kb-loop] taxonomy proposal: <summary>` explaining: the observed
   corrections (with commit refs and closed-MR refs), the proposed rule change, the
   expected effect.

Rules are the constitution — once setup is complete (the domain vocabulary in
`_meta/instance.md` is non-empty), agents NEVER change `_meta/` outside an MR.
Instantiation edits before that gate are the one exemption.

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
  targets, domains that would need a new vocabulary value) goes into the run report,
  or into the reflect MR when it is a rule problem.

Re-run the script after fixing; the run report states the final exit status.
Instances with CI should run the same command on every push.

## Per-run limits

- Refine: max 10 notes (freshness check included). Open MRs: max 3 per run, of which
  1 is reserved for reflect's taxonomy proposal (refine may use at most 2). Hitting a
  limit skips the remaining work of that stage only — the pipeline always continues
  through to the final report commit.

## MR mechanics

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
- **Report carrier**: every run ends with a dedicated report commit on main, message
  `[kb-loop] run report: <YYYY-MM-DD>` with the report in the body (use
  `git commit --allow-empty` when there is nothing else to commit). This commit is
  also the reflect stage's window marker for the next run.
- **MR descriptions**: MRs are created mid-run; update their description with the run
  report after lint completes.
- **"Connected to related notes"** (curated criterion) is vacuously satisfied while
  the vault has no related notes — say so in the MR when it applies. Note that
  `scripts/lint.py` still requires ≥ 1 wikilink on a `curated` note, so a lone first
  note stays `raw` until it has a sibling to link to.

## Run report

End every run with the dedicated report commit described above, containing: what was
triaged (including items skipped as already-annotated), what was refined, which notes
were freshness-checked, what was proposed, the lint exit status and anything it left
unfixed, rejected proposals recorded for the next run, and what is stuck and why.
Copy the report into the MR descriptions when MRs were opened.
