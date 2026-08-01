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

*Qualified by practice.* That promise holds from the second merge onward: every instance
starts with a history unrelated to the template's (both "Use this template" and the
clone-and-reinit recipe produce fresh history), so the first merge needs
`--allow-unrelated-histories` and conflicts add/add on every file changed since
instantiation — a one-off mechanical resolution documented in GETTING-STARTED.md →
"Updating an instance", not a hole in the file-ownership split.

*Extended by D8.* The instance-owned set grew by one field — the governance mode —
while the *definitions* of the two modes stay framework-owned (`CLAUDE.md`,
`_meta/loop.md`). The instance picks; the framework says what the pick means.

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

*Extended by D9.* The plugin gained a fourth skill, `kb-setup`, which turns the plugin
from "the skills work anywhere" into "installing the plugin is the whole onboarding".

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

*Superseded in part by D8.* The principle stands, the mechanism became mode-dependent:
closed MRs are the rejection signal in `reviewed` mode only. In `autonomous` mode the
signal is a human `git revert` of a prefixed agent commit, which removes the platform
dependency entirely rather than bounding it — reflect is then pure git.

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

*Amended by D8 (decision intact, channel widened).* Human-conferred in both governance
modes — this is the one rule `autonomous` mode does not relax. Only the nomination
channel differs: an MR in `reviewed` mode, a digest line in `autonomous`, which the
human promotes by direct commit or lets lapse.

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

*Superseded in part by D8.* "Wrong → correction MR" is the `reviewed`-mode channel;
in `autonomous` mode the correction is a direct commit itemized in the digest.

## D8 — Governance modes: pre-approval or post-hoc revert

**Context.** Every destructive action the agent wanted to take — merging duplicates,
deleting, renaming, changing a rule — waited in a merge request for one person. That
made the vault owner a blocking dependency of the loop: proposals queue up, the weekly
run's most valuable work is exactly the work that stalls, and the framework's own
premise ("the vault gets better over time") depends on someone's review latency. The
review also assumes an MR platform exists and that `main` is not the natural place to
work — neither is true for a solo vault or a personal one. Meanwhile git already offers
an undo that is cheaper than an approval: `git revert`.

**Decision.** Safety becomes a per-instance choice between two named modes, declared in
`_meta/instance.md` → Governance, with the definitions in `CLAUDE.md` and the
stage-level effects in `_meta/loop.md`.

- **`autonomous`, the framework default** — default-open plus audit. Agents perform
  every operation by direct commit to `main`: merges, deletions, moves, renames,
  rewrites, and `_meta/` rule changes (taxonomy changes auto-apply). In exchange every
  risky action is itemized, with its SHA, at the top of the run digest. The human reads
  the digest and reverts what they disagree with. A revert of a `[kb-loop]`/`[kb-save]`
  commit is read by reflect exactly as a closed MR was: the action is not redone unless
  the notes involved materially changed, and it feeds pattern analysis. Because reverts
  are plain git, reflect needs **no platform API at all** in this mode.
- **`reviewed`** — the previous behaviour verbatim, now opt-in: destructive tier and
  taxonomy changes via MR, closed-MR and review-comment signals, branch hygiene, the
  3-MR budget with a slot reserved for reflect. For teams where agent trust is not yet
  established, or where `main` is protected.

Two things do not move. `evergreen` stays human-conferred in both modes — in
`autonomous` the agent nominates with a digest line the human may act on or ignore, so
it creates zero forced work. And the guardrails are mode-independent: the lease, the
linter, no force-push on `main`, originals reviewable in git history after a merge, and
the agent commit prefixes.

The run report becomes **`_meta/digest.md`**, overwritten every run (git history keeps
the old ones) and repeated in the report commit body. "Risky actions" is its first
section precisely because it is the only part that can require action today.

**Consequence.** The loop stops waiting on humans: throughput is bounded by the run
budget rather than by review latency, and a solo vault with no MR platform is now a
first-class case instead of a degradation. Review cost drops from "approve N proposals"
to "read one page, revert what is wrong" — and un-acted items cost nothing, since
lapsing is the safe default for nominations and silence is consent for everything else.
The price is real: a wrong action is live until someone notices, so the digest's
completeness is now load-bearing — an unreported risky action is a framework violation,
not a formatting slip. It also demands that every risky action be one self-contained,
revertable commit (a merge deletes originals and retargets links in the same commit),
and it makes `autonomous` unusable where branch protection forbids direct pushes to
`main`, which is exactly when an instance should pick `reviewed`.

*Hardened by D10: digest completeness is now machine-checked.* The load-bearing promise
of this decision — every risky action appears in the digest — stopped being a promise:
`scripts/verify_digest.py` re-derives the risky actions from git and fails the run when
one has no digest line.

## D9 — Onboarding is a skill, not a checklist

**Context.** Joining a vault took four manual steps — clone it, hand-write
`~/.claude/<vault-name>.md`, verify the clone, wire a project repo — spread across the
README and kb-search's SKILL.md. Every step is a drop-off point, and the framework's
value only starts after the last one.

**Decision.** Ship a fourth skill, `kb-setup`, through the same plugin manifest: it takes
a vault URL, confirms a destination with the user before cloning, refuses anything
without `_meta/loop.md`, runs the linter, writes the per-user `KB_VAULT` file, reports
whether the vault has passed its setup gate, and ends by naming the three daily actions.

**Consequence.** With the plugin installed, onboarding is one sentence, and the steps
that used to be prose a human might skip are now steps an agent cannot. The manual four
remain documented as a collapsed fallback for non-Claude-Code users, so the
`~/.claude/<vault-name>.md` contract still has exactly one definition. The cost is that
the plugin now touches the user's home directory, which is why the destination path and
any conflicting existing file are always shown before being written. A later first-contact
review found the gap on the other side of this decision — an instance that rewrites the
framework README deletes the very instructions that make onboarding one sentence — so the
template also ships `_meta/README.instance.md`, a stub that carries the join block through
the rewrite.

## D10 — Mechanical verification of what the framework promises

**Context.** D8 made the digest load-bearing: in `autonomous` mode an unreported risky
action is invisible, so the human's revert-based control depends entirely on the agent
having itemized everything. That promise lived in prose, and prose is exactly what an
agent under budget pressure summarizes away. Two other promises had the same shape. The
lease claimed mutual exclusion but implemented check-then-force-push: two machines could
each read "free", each push, and the later force-push would silently steal a lock the
other run believed it held. And the linter — the framework's one deterministic check —
had no tests, so every rule in it was a rule that could regress unnoticed.

**Decision.** Turn each promise into something a machine checks.

- **`scripts/verify_digest.py`** re-derives the run's risky actions from git — deletions
  and renames under the type folders, `_meta/` changes other than the digest itself, and
  `status:` demotions — over the agent commits since the previous report commit, and
  exits 1 naming any whose short SHA is absent from `_meta/digest.md`. The loop therefore
  writes the digest, verifies, and only then makes the report commit; digest lines carry
  short SHAs as a mechanical requirement rather than a convenience. In `reviewed` mode the
  same script doubles as a tripwire: a risky agent commit sitting on `main` there means
  something bypassed the MR channel.
- **The lease becomes a real compare-and-swap.** Taking a free lock pushes without
  `--force`, so git's own non-fast-forward rejection is the atomic test; stale takeover
  and refresh push with `--force-with-lease=<ref>:<sha we read>`. A session id in the lock
  closes the last hole, where two terminals sharing a holder name each "refreshed" their
  way into a concurrent run.
- **A stdlib `unittest` suite** (`python3 -m unittest discover -s tests`) covers every
  violation class the linter knows, the lease against a real bare remote with two clones,
  and the verifier's window and detection rules. It runs in CI alongside the linter.

Two smaller items ride along, both content policy rather than mechanism: secrets and
personal data are named as content that never enters the vault, with rotation — not
deletion — as the remedy, since the commit-first rule has already written the value into
history; and the linter warns (without failing) about notes in folders the schema cannot
see.

**Consequence.** The framework's three guarantees — the digest is complete, one run at a
time, a note is valid — are now checkable rather than asserted, and a regression in any
of them shows up as a failing exit code instead of as a quiet loss of trust months later.
The cost is that the loop has one more mandatory step before its report commit, that the
lease is slightly less forgiving (a run whose process died is cleared by `release` or the
TTL, not inherited by the next terminal), and that changing a linter rule now means
changing its test too. All three are the intended price: they make the rule harder to
change accidentally, which is what a rule binding every instance should be.
