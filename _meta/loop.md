# Maintenance Loop

The loop is **stateless**: everything it needs is derived from the repo itself
(inbox contents, frontmatter status, git history). It can run from any machine,
any time, and safely stop midway — the next run picks up naturally.

Run stages strictly in order. Respect the write tiers in `CLAUDE.md`.

## Stage 1 — Triage (empty the inbox)

For each item in `_inbox/`:

1. Decide the type using `_meta/taxonomy.md` decision rules.
2. Instantiate the matching template from `_meta/templates/`, fill frontmatter
   (`status: raw`, `source: inbox`, today's date), name the file per naming rules.
3. Move content into the type folder; delete the inbox item in the same commit.
4. If the type cannot be decided confidently: leave the item in `_inbox/` and prepend
   a visible callout (`> [!note] kb-loop: cannot classify — …`) so a human can add
   context. Never use HTML comments — they are invisible in Obsidian's reading view.

Channel: direct commit (additive).

## Stage 2 — Refine (push notes up the status ladder)

Pick up to **10 notes** (all `raw` before any `curated`; within a status, oldest
frontmatter `created` first, ties broken by filename):

- Add wikilinks to related notes (search by tags and keywords first).
- Fix formatting to match the type template; fill missing frontmatter.
- Promote status when criteria are met (see taxonomy.md lifecycle).
- If two or more notes overlap heavily: propose a merge. Merges go through an MR,
  with the full original texts visible in the diff.
- If several `troubleshooting` notes share a theme: propose distilling them into
  one `guides` note (MR; originals are linked, not deleted, until the MR is approved).

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
3. If a pattern emerges (same kind of correction ≥ 2 times), draft a change to
   `_meta/taxonomy.md` that would have prevented the misclassification.
4. Open an MR titled `[kb-loop] taxonomy proposal: <summary>` explaining:
   the observed corrections (with commit refs), the proposed rule change, expected effect.

Rules are the constitution — NEVER change `_meta/` outside an MR.

## Stage 4 — Lint (health check)

Scan the type folders only — skip `_meta/`, `_inbox/`, `_attachments/`, and
`.obsidian/` (templates contain placeholder frontmatter by design). Check for:

- Broken wikilinks (target file does not exist).
- Frontmatter violating the schema (missing keys, type ≠ folder, invalid status).
- `domains` values not in the taxonomy vocabulary.
- Filename rule violations.

Auto-fix what is safe (formatting, obvious key omissions) via direct commit.
List the rest in the run report.

## Per-run limits

- Refine: max 10 notes. Open MRs: max 3 per run. If limits hit, stop — next run continues.

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
