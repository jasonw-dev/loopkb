# Maintenance Loop

The loop is **stateless**: everything it needs is derived from the repo itself
(inbox contents, frontmatter status, git history). It can run from any machine,
any time, and safely stop midway — the next run picks up naturally.

Run stages strictly in order. Respect the write tiers in `CLAUDE.md`.

## Stage 1 — Triage (empty the inbox)

For each item in `_inbox/`:

1. Decide the type using `_meta/taxonomy.md` decision rules.
2. If the item is untracked, commit it as-is first — the raw original must exist in
   git history before filing rewrites it.
3. Instantiate the matching template from `_meta/templates/`, fill frontmatter
   (`status: raw`; `source` per taxonomy.md's Source field rules — `meeting` for
   meeting material, otherwise `inbox`; `created` = today), name per naming rules.
4. Move content into the type folder; delete the inbox item in the same commit.
5. If the type cannot be decided confidently: leave the item in `_inbox/` and prepend
   a visible callout (`> [!note] kb-loop: cannot classify — …`) so a human can add
   context. Never use HTML comments — they are invisible in Obsidian's reading view.

Channel: direct commit (additive).

## Stage 2 — Refine (push notes up the status ladder)

Pick up to **10 notes** (all `raw` before any `curated`; within a status, oldest
frontmatter `created` first, ties broken by filename):

- Add wikilinks to related notes (search by tags and keywords first).
- Fix formatting to match the type template; fill missing frontmatter.
- Promote status when criteria are met (see taxonomy.md lifecycle).
- Before proposing any merge/distill: list existing open `kb-loop/*` branches and MRs;
  skip anything already pending review (the repo alone is not the whole state —
  the platform holds open proposals).
- If two or more notes overlap heavily: propose a merge via MR. The MR itself
  deletes the originals (their full text is reviewable in the deleted-file diff)
  and retargets every inbound wikilink in the same MR — no follow-up commits.
- If several `troubleshooting` notes share a theme: propose distilling them into
  one `guides` note (same MR mechanics: originals deleted, inbound links retargeted,
  everything reviewable in one diff).

Channel: direct commit for links/tags/format/status; MR for merge/distill/move.

## Stage 3 — Reflect (learn from human corrections)

1. `git log` since the **previous run's report commit** (message starting
   `[kb-loop] run report`), excluding commits made by the current run. First run
   ever: scan the full history. (Do NOT use "last `[kb-loop]` commit" as the
   marker — the current run's own triage commits would shrink the window to zero.)
2. Find human commits (no prefix) that override agent actions: moved files, changed
   types/tags, renamed files, reverted agent commits. Ignore merge commits (e.g.
   platform-generated merges of `kb-loop/*` branches) — they carry no prefix but
   are not corrections.
3. If a pattern emerges (same kind of correction ≥ 2 times **counted across the
   full history**, not only inside the current window — the window bounds discovery
   of NEW corrections; pattern counting accumulates over all past ones), draft a
   change to `_meta/taxonomy.md` that would have prevented the misclassification.
4. Open an MR titled `[kb-loop] taxonomy proposal: <summary>` explaining:
   the observed corrections (with commit refs), the proposed rule change, expected effect.

Rules are the constitution — once instance setup is complete, agents NEVER change
`_meta/` outside an MR (initial instantiation edits are the one exemption).

## Stage 4 — Lint (health check)

Scan the type folders only — skip `_meta/`, `_inbox/`, `_attachments/`, and
`.obsidian/` (templates contain placeholder frontmatter by design). Check for:

- Broken wikilinks (target file does not exist).
- Frontmatter violating the schema (missing keys, type ≠ folder, invalid status).
- `domains` values not in the taxonomy vocabulary.
- Filename rule violations.

Auto-fix what is safe (formatting, obvious key omissions) via direct commit.
For `type` ≠ folder mismatches, **the folder wins** — humans correct filings by
moving files, so updating `type:` to match the folder is a safe auto-fix; never
"fix" the mismatch by moving the file back.
List the rest in the run report.

## Per-run limits

- Refine: max 10 notes. Open MRs: max 3 per run, of which 1 is reserved for
  reflect's taxonomy proposal (refine may use at most 2). Hitting a limit skips the
  remaining work of that stage only — the pipeline always continues through to the
  final report commit.

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
  the vault has no related notes — say so in the MR when it applies.

## Run report

End every run with the dedicated report commit described above (Mechanics
clarifications), containing a short report: what was triaged, refined, proposed,
linted; what is stuck and why. Copy the report into the MR descriptions when MRs
were opened.
