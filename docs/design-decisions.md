# Design Decisions

ADR-style record of the framework's load-bearing choices. Each entry: the context
that forced a choice, the decision, and what it commits us to. These describe the
*framework*; instance-level policy lives in `_meta/instance.md`.

## D1 — One instance-owned file

**Context.** A template that instances copy diverges immediately: every instance edits
the same framework files to record its own vocabulary and policy, so pulling template
improvements means resolving conflicts in files nobody wanted to fork.

**Decision.** All instance-specific configuration lives in `_meta/instance.md` alone —
identity (body language, vault scope), the closed domain vocabulary, and policy
overrides. Framework files (`CLAUDE.md`, `_meta/taxonomy.md`, `_meta/loop.md`,
templates, skills, scripts) carry no fill-in sections; `CLAUDE.md` ends with a pointer
saying instance policy overrides its defaults. The template ships `instance.md` as a
marked skeleton.

**Consequence.** Updating an instance is `git remote add upstream … && git fetch
upstream && git merge upstream/main`, and instance-owned content never conflicts —
only a changed *skeleton* needs manual merging. The cost: any customization outside
`instance.md` will conflict on merge, which is deliberate — it is the signal to
express the customization as a policy override instead.

## D2 — Plugin wrapper over vault-local skills

**Context.** The three skills are most useful in *other* repos (kb-search while
debugging a project, kb-save at the end of it), but they live in the vault's
`.claude/skills/`, which only loads when the vault itself is open.

**Decision.** Ship the repo as a Claude Code plugin plus a single-entry marketplace
(`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`). The manifest's
`skills` field points at `./.claude/skills/`, which the plugin format supports
directly, so the plugin contains no copies of the skill files.

**Consequence.** `/plugin marketplace add jasonw-dev/loopkb` + `/plugin install
loopkb@loopkb` exposes `/loopkb:kb-save`, `/loopkb:kb-search`, `/loopkb:kb-loop`
anywhere. There is exactly one copy of each SKILL.md, so drift between the vault and
the plugin is structurally impossible and no generation step exists to forget to run.

## D3 — The linter is the schema

**Context.** The lint stage was a prose checklist, so "is this note valid?" depended on
the agent's reading of the prose that day, and the same rules were restated in three
files that could disagree.

**Decision.** `scripts/lint.py` (single file, Python 3 stdlib, hand-parsed frontmatter)
is the executable definition: frontmatter presence and parseability, required keys,
type-matches-folder, status/source enums, domains ⊆ instance vocabulary, kebab-case
filenames, dated meeting filenames, basename uniqueness, wikilink resolution, and the
`curated`/`evergreen` floor. Loop stage 4 runs it; the agent fixes what it reports.

**Consequence.** Vault health is a deterministic exit code that CI can gate on, and the
prose checklist is deleted rather than duplicated. Rule changes now mean changing code,
which is a heavier edit — intentionally so, since the linter binds every instance.

## D4 — Rejections are correction signals

**Context.** Reflect only mined unprefixed human commits. A human who reviewed an
agent's merge proposal and closed it produced no such commit, so the strongest possible
correction — an explicit "no" — was invisible, and the next run happily re-proposed it.

**Decision.** Reflect reads two signal kinds: overriding human commits, and `[kb-loop]`
MRs closed without merge (plus their review comments) since the last reflect. A
rejected proposal must not be re-proposed unless the notes involved materially changed.
Reflect dedups against open proposals, and pattern counting resets per pattern once a
proposal addressing it is merged *or* closed. Without a platform API, degrade to
git-only signals (a deleted unmerged `kb-loop/*` branch approximates a rejection).

**Consequence.** The loop stops nagging: every proposal outcome, positive or negative,
advances its understanding. The cost is a platform dependency for full fidelity, which
the git-only degradation bounds rather than removes.

## D5 — A lease, not an assumption

**Context.** The loop is stateless and runnable from any machine — which also means two
people can start it at the same time, producing duplicate MRs, competing rebases, and a
report commit that describes neither run.

**Decision.** `scripts/lease.py acquire|release|status` maintains an orphan branch
`kb-loop-lock` on `origin` whose single empty commit records holder and ISO timestamp.
Acquire fails when the lock exists and is younger than 2 hours; older locks are stale
and replaceable. kb-loop acquires in pre-flight and releases on every exit path,
including aborts. With no remote, the lock is local with identical semantics.

**Consequence.** Concurrent runs stop cleanly instead of colliding, using only git — no
service, no state file to reconcile. A crashed run blocks the next for at most the TTL,
which is the price of not having a heartbeat.

## D6 — Evergreen is human-conferred

**Context.** `evergreen` is the top of the trust ladder that both humans and agents read
when deciding what to believe. An agent that can promote to it is an agent grading its
own work, which makes the label mean only "an agent liked this".

**Decision.** `raw → curated` stays an agent-direct-commit gated by the linter's floor.
`curated → evergreen` is human-only: agents may nominate via MR, never promote on
`main`; humans promote by direct commit. Demotion stays additive-tier for both.

**Consequence.** `evergreen` carries a real claim — a person stood behind this note —
which is what makes kb-search's trust order worth obeying. Evergreen therefore grows
only as fast as human attention allows, which is the intended rate.

## D7 — Freshness is checked, not assumed

**Context.** Promotion is one-directional in practice: notes climb to `curated` or
`evergreen` and then sit there while the world moves on. A confidently wrong evergreen
note is worse than no note.

**Decision.** Each refine stage takes the 1–2 `curated`/`evergreen` notes whose last
content change (per `git log`, ignoring pure-formatting commits when determinable) is
oldest and verifies they are still accurate. Stale → demote one level with a reason
(direct commit); wrong → correction MR. It counts against the 10-note refine budget.

**Consequence.** Every note is eventually re-examined at a bounded, predictable cost per
run, and the status ladder becomes two-directional. Older notes are checked first, so
staleness is caught roughly in the order it accumulates.
