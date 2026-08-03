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

*Extended by D12.* It grew again, and this time by the thing the loop produces: the
classification rules reflect learns are instance-owned amendments in `_meta/instance.md`,
not edits to the framework's `_meta/taxonomy.md`. Without that move this decision's own
merge recipe would have deleted them.

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

*Extended by D11.* The "one copy, no drift" property is the reusable part of this
decision, not the plugin format: `integrations/` gives other agents their own thin entry
points that resolve to the same `.claude/skills/` files.

*That extension is gone (2026-08-03, see D11's reversal).* The plugin is again the only
packaging the framework ships, so this decision stands alone rather than as one instance
of a pattern — "one copy, no drift" is now a property of the manifest pointing at
`.claude/skills/`, and nothing else points at those files.

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

*Superseded in part by D12.* Two corrections. Rejection *memory* is re-derived from the
full history on every run rather than carried forward in the digest — this decision's
"record the rejected pairs" instruction made a display document load-bearing. And the
git-only degradation above is withdrawn: "a deleted unmerged `kb-loop/*` branch
approximates a rejection" guesses at the one signal that must not be guessed, since a
wrong rejection suppresses a correct action forever and branch deletion is as often
hygiene after a merge. Reflect now runs on signal 1 alone when the platform is
unreachable, and says so in the digest.

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

*Amended: "releases on every exit path" means after a successful acquire.* Read literally
it defeated the decision — a run whose acquire was *rejected* would, on its way out,
delete the lock of the run that had just won it. `release` now refuses a live lock whose
holder or session is not its own (exit 1, `--force` for a run known to be dead), and a
release that cannot reach `origin` reports that the local ref is gone while the remote
lock stands until the TTL, instead of printing "released". Mutual exclusion is a property
of the exit path too, not only of the entry.

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

*Amended: demotion is risky-tier, not additive-tier.* "Demotion stays additive-tier for
both" described the tiers as they were when this was written. It no longer holds: a
demotion carries a digest "Risky actions" line in `autonomous` mode, and it is one of the
four classes `scripts/verify_digest.py` re-derives straight from git (D10). The *channel*
is what stayed additive — a direct commit in both modes, reason in the commit message,
never an MR — but the action is itemized, so the human sees every note the loop pushed
back down the ladder.

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
one has no digest line. Four of the five classes, precisely: a rewrite that changes a
note's meaning is indistinguishable from reformatting in a diff, so that line still rests
on the agent's honesty, with git and the freshness check (D7) as its recovery path. The
docs now say which is which rather than claiming the check covers everything.

*Amended by D12, twice.* "Taxonomy changes auto-apply" survives as a property but not as
a file: the rule change lands as an amendment in `_meta/instance.md`, and `_meta/taxonomy.md`
became read-only for agents. And the digest is confirmed as **display**, not state — the
rejection memory it lists is re-derived each run, so this decision's one artefact carries
no information the loop depends on.

*Narrowed again: `reviewed` requires merge commits too.* D10's verifier skips merge
commits because in this mode a merge *is* the human review — which silently made the
platform's merge method a prerequisite of the mode. Squash- and rebase-merge put a
single-parent `[kb-loop]` commit on `main`'s first-parent chain, indistinguishable from
one that bypassed the MR channel, so the verifier reports approved work as missing from
the digest. Stated as a prerequisite wherever the mode is chosen rather than detected:
separating a squashed MR from a direct commit is guesswork, and guessing would blunt the
tripwire. Instances that cannot change the merge method itemize squashed MRs like direct
commits.

*Narrowed in passing.* `reviewed` mode now requires an MR platform; the documented
fallback (branch + local `git diff main...` review + merge, for a repo without one) is
cut. The team it served — wanting pre-approval, owning no MR platform — is the empty set
in practice, and `autonomous` mode is precisely the design for a vault with no platform,
so the fallback only offered a worse version of a mode that already fits.

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

*Extended in passing.* The visual intro both READMEs open with now ships as
`docs/index.html`, served at the GitHub Pages root instead of behind a private artifact
link, so the first-contact path is versioned with the framework and reviewable in the same
diffs. `tests/test_docs.py` checks the file exists and that no document names the old
path — an anti-drift rule that had itself drifted for two commits.

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

*Amended: a run states its session id; it is not inferred.* The session that closed the
last hole above defaulted to the parent process id, which identifies a run only while all
of its lease commands share one shell. An agent's do not — `acquire` and `release` are
separate commands in separate shells — so once D5's amendment made `release` refuse a lock
that is not its own, that default had every agent-driven run refusing to release its *own*
lock, leaving the vault locked for the full TTL after a healthy run. `acquire` and
`release` now take `--session <run-id>`; the loop passes one id to both, `acquire` prints
the id when it had to invent one, and `status` reports the id the lock carries. The
property is unchanged — two terminals are still two runs — but it is now stated by the run
instead of inferred from its process tree, which is the same lesson as the lock itself:
identity that matters must be recorded, not derived from the environment that happens to
be running the command.

## D11 — Per-platform entry points, one procedure

**Context.** The rule system was agent-agnostic from the start — `AGENTS.md`, `CLAUDE.md`,
`_meta/*.md` and `scripts/` are plain files any agent can read — but the *procedures* were
packaged for exactly one agent. `.claude/skills/*/SKILL.md` load automatically only in
Claude Code, and D2's plugin, the thing that makes them available in other repos, is a
Claude Code format. So "any agent works here" was true of the rules and false of the
ergonomics: a Codex user could be told to read a SKILL.md, but nothing made it happen, and
onboarding (D9's one-sentence `kb-setup`) had no equivalent at all. The tempting fixes are
both wrong: rewriting the skills into some neutral format abandons the agent most people
use, and copying them per platform reintroduces exactly the drift D2 designed away.

**Decision.** Keep `.claude/skills/*/SKILL.md` as the single definition of every
procedure, and add `integrations/<platform>/` — thin, per-platform *entry points* that
resolve the vault and then read the vault's own SKILL.md. The first is
`integrations/codex/`: four Codex skills of about a dozen lines each, installed to
`~/.agents/skills/`, each of which locates `KB_VAULT` and hands off to
`<KB_VAULT>/.claude/skills/<name>/SKILL.md`. `kb-setup` is the one asymmetric case — there
is no vault to read from yet — so it falls back to the framework copy of that same file
over HTTPS rather than restating the steps. Onboarding documentation splits by platform
(Claude Code / Codex CLI / any other agent) rather than treating non-Claude agents as a
footnote, and the manual path says plainly that it does clone the vault itself.

Verified rather than assumed, because it moved: Codex's custom prompts
(`~/.codex/prompts/<name>.md`, `/prompts:<name>`) are deprecated in favour of skills, so
the integration targets skills and mentions prompts only as a legacy fallback. Codex reads
`AGENTS.md` from `$CODEX_HOME` and from the repo root down, which is what makes the
optional global snippet possible; and its default sandbox denies network access, so every
git operation the skills perform surfaces as an approval prompt — documented rather than
worked around.

**Consequence.** Adding a platform is a directory of pointers, not a fork of the
procedures: there is still exactly one copy of each SKILL.md, and a change to a procedure
reaches every agent with no regeneration step. The cost is a small per-platform surface
that can rot when a vendor changes its conventions — the prompts-to-skills move happened
before this decision was even written — which is why each integration README states the
mechanism and its doc source, so a stale one is recognisable rather than merely broken.
Two smaller prices: the per-user wiring file stays at `~/.claude/<vault-name>.md` for
every agent, an inaccurate name kept deliberately so the contract has one definition
instead of one per vendor; and `integrations/` joins `docs/`, `scripts/` and `tests/` in
the linter's non-note directories, since a `SKILL.md` under it is not a note and four of
them would otherwise collide on basename uniqueness.

*Amended: the entry points ship in the vault, not in `$HOME`.* The decision is intact —
one procedure, thin per-platform pointers — but the delivery moved. Codex loads
`.agents/skills` from the working directory up to the repository root as well as from
`$HOME/.agents/skills`, so the four pointers now live at `.agents/skills/*/SKILL.md` in
the vault itself and every clone gets them with nothing installed; `integrations/codex/`
keeps only the README that explains the mechanism, and the global install is demoted to
optional — its one remaining job is the kb skills in repos that carry no copies. What
prompted it was an instance shipping its own team skills exactly that way, which made the
asymmetry obvious: the vault was asking Codex users to install by hand what it could
simply carry. Two consequences follow. The pointers now also run *inside* vaults, so each
gained a step 0 — a repo containing `_meta/loop.md` is the vault, and `KB_VAULT`
resolution is skipped — which incidentally makes `kb-loop`'s recommended
vault-as-workspace setup the zero-configuration path. And instances inherit the pattern:
a team skill shipped as byte-identical twins in `.claude/skills/` and `.agents/skills/`,
both pointing at the instance's own canonical guide, serves both agent ecosystems with no
install and no second copy of the procedure. The price is that `.agents` joins the
linter's non-note directories for the same reason `integrations/` did, and that a repo
carrying copies can hold a stale pointer — bounded, since a pointer only ever names a
path.

*Reversed (2026-08-03): the Codex packaging is removed.* `.agents/skills/kb-*` and the
whole of `integrations/` are deleted; the framework ships entry points for Claude Code
only. The rationale is upkeep, not a change of mind about the design: maintaining a second
ecosystem's entry points — four pointer files, an explanation README, and a per-platform
onboarding path in every shipped document, all of which had to be re-verified whenever a
vendor moved its conventions (this decision's own body records one such move) — was not
carrying its weight against the use it saw. What this decision got right survives without
the packaging: the rules stay agent-agnostic (`AGENTS.md` → `CLAUDE.md`, `_meta/*.md`,
`scripts/`), there is still exactly one copy of every procedure in `.claude/skills/`, and a
non-Claude agent reaches it the way this decision's own "any other agent" path always
did — told to read the SKILL.md it needs. What is lost is honestly stated rather than
papered over: that path is documentation, not ergonomics, so a Codex user gets no
`$kb-setup`, and re-adding a platform means re-adding a directory of pointers. Two
residues are deliberate: `.agents` stays in `scripts/lint.py`'s SKIP_DIRS, because an
instance may still carry team skills of its own there and a template merge must not start
linting them as notes; and the instance-side pattern this decision inspired is now
documented as `.claude/skills/` pointers alone.

## D12 — Learned rules are instance-owned; rejection memory is derived, not carried

**Context.** A final pre-freeze review put two of the framework's own promises side by
side and found they could not both be kept.

The first is a collision between D1 and D4. D4 gave the loop a way to learn: reflect
mines human corrections and changes the classification rules. Those changes were written
to `_meta/taxonomy.md`. D1 gave every instance a way to stay current: template updates
arrive as `git merge upstream/main`, and the documented first-merge resolution is
`git checkout --theirs -- .` — framework files take upstream. `_meta/taxonomy.md` is a
framework file. So the first update an instance pulled would silently delete every rule
its own corrections had taught it, and "the taxonomy learns" and "updates are one merge"
were each true only while the other went unused.

The second is a chain of prose copying. Rejection memory — the set of actions a human
already said no to, which reflect must never re-attempt — was to be "recorded in the
digest so the next run sees it without re-deriving anything". That makes a human-facing
report into machine state: it survives only as long as each run faithfully copies the
previous run's list forward, a hand-off with no check on it, in a loop whose stated
premise (D5, D8) is that it is stateless and can safely stop midway. A digest that is
lost, truncated under budget pressure, or edited by the human who wrote a note in it
takes the loop's memory with it.

**Decision.** Split ownership by who *produces* the content, not by which file feels
like rules.

- **`_meta/taxonomy.md` is framework-owned and read-only for agents.** It carries the
  rule *format* and the framework's defaults, and a template merge may overwrite it
  wholesale without losing anything.
- **`_meta/instance.md` gains "Classification rule amendments"** — dated entries that
  extend or override the taxonomy, written by reflect (Stage 3) on the channel of the
  active governance mode. Agents read the taxonomy and the amendments together on every
  classification, and **the amendment wins**. The vocabulary and policy sections of the
  same file already worked this way; type criteria, naming and source rules now join them.
- **Rejection memory is re-derived from scratch every run**, never copied forward: in
  `autonomous` mode by walking the FULL history for reverts (`git log --no-merges
  --grep="This reverts"`), resolving each reverted SHA and keeping the agent-prefixed
  ones; in `reviewed` mode by querying the platform's closed-MR list per run. The digest
  still lists the set — for the human, as display only.

**Consequence.** The two promises hold simultaneously and the merge recipe can now say so
plainly: `git checkout --theirs -- .` cannot touch a learned rule, because no learned rule
lives in a framework file. The digest returns to being a report — losing one, or reading a
stale one, costs the loop nothing, which is what "stateless" was supposed to mean.

The prices are real and accepted. Classification now reads two places instead of one, so
an agent that skips the amendments silently uses stale rules — mitigated only by every
skill and stage saying to read both, and by the amendments living in the file agents
already must read for the vocabulary. Amendments accumulate in the one file a human edits
by hand, so a long-lived vault's instance.md grows a rule log that nobody prunes; entries
are removable by hand, and a human's revert of one is itself the rejection signal that
stops it coming back. And re-deriving the rejection set costs a full-history `git log`
every run — cheap now, linear in history forever, and the price of not trusting a document
to be a database.

## D13 — Contradictions are found by consumers, not by a sweep

**Context.** The loop self-corrects only the contradictions it happens to *see*: refine's
merge candidates, the freshness check, a human correction. Nothing looks for two notes
that quietly disagree, and the read path made that worse — kb-search ranks hits by trust
order, so an agent could pick a side and answer as though there were no conflict, leaving
the losing note in the vault for the next reader to believe.

**Decision.** Make every consumer a detector and let refine reconcile on sight. kb-search,
on retrieving contradictory notes, still answers by the trust order but must *say* so —
which notes, which claims, which one it followed and why — and must record the conflict
back to `_inbox/` as a report naming both notes in `[[wikilinks]]`, committed and pushed
under kb-save's git rules. Triage routes that report without filing it as a note (it
carries no new fact), and refine (Stage 2b) resolves conflicts the moment its link search
or such a report reveals one: merge or correct through the normal channels; when it cannot
tell which side is right, demote the doubtful note one level with the reason and list the
conflict under the digest's Stuck section. A dedicated consistency-sweep stage was
rejected — a fifth stage comparing note against note is quadratic in vault size to find
what reading surfaces for free.

**Consequence.** Detection now scales with how much the vault is *read* rather than how
big it grows, and the notes that get checked are the ones people actually use. A
contradiction between two unread notes stays undetected, which is accepted: it misleads
nobody until someone reads it, and reading it is what triggers the check. The prices are
that the read path gained a write side effect — one inbox item and one commit per
contradiction found, inheriting kb-save's failure modes when the remote is unreachable —
and that refine now spends budget on conflicts it did not schedule, which is the intended
priority: a wrong note outranks an unlinked one.

*Extended by D14.* The two detection points named here — read time and refine time — are
joined by a third, write time: an agent rewriting a note reconciles that note's wikilink
neighborhood before committing, which catches the contradictions a rewrite itself creates
instead of waiting for a later reader to trip over them. The quadratic sweep stays
rejected; a neighborhood is the link graph, not the vault.

## D14 — A rewrite re-reads its own neighborhood

**Context.** D13 gave contradiction detection two moments: read time, where kb-search
names the conflict it retrieved and files a report, and refine time, where Stage 2b
reconciles what its link search surfaces. A real case showed the third one missing. Two
rule-bearing notes — a spec and a card that wikilinked it — were left flatly contradicting
each other because an agent rewrote one of them without re-reading the other. Neither D13
detector was due to fire: nobody was searching those notes, and refine had scheduled
neither, so a contradiction *created* by a write would have sat latent until an execution
under time pressure hit it and had to guess which note to believe. The moment a note's
meaning changes is also the cheapest moment to check it against its neighbors, and the
only one where the agent already knows exactly what changed.

**Decision.** Any agent rewriting an existing note first re-reads that note's wikilink
neighborhood — the outbound links in the note itself, plus the inbound ones found
mechanically with `grep -rl "\[\[<basename>\]\]"` over the type folders — and applies
Stage 2b's reconcile-on-sight duty to what it finds: reconcile through the normal channels
for those actions; where it cannot tell which side is right, demote the doubtful note one
level with the reason and list the conflict under the digest's Stuck section; risky actions
itemized as usual. It lands as a numbered guardrail in `CLAUDE.md` rather than as a loop
stage, because it binds every rewrite an agent performs, inside a loop run or not, and
Stage 2b cross-references the guardrail so loop-time and ad-hoc rewrites obey one rule.
The neighborhood is the link graph and nothing beyond it — comparing a rewritten note
against every other note is D13's rejected quadratic sweep wearing a different hat.

**Consequence.** Contradiction detection now covers all three moments a note can take part
in one — read, refine, write — and the new one is the only check that runs *before* the
contradiction exists, so the failure that motivated it is caught by the very agent that
would otherwise have caused it. The prices are two. A rewrite costs one grep plus reading
the neighbors it returns, which is negligible for a leaf note and genuinely heavy for a
hub with many inbound links — bounded by the graph rather than the vault, but not small,
and it competes with the same refine budget as everything else. And the check sees only
what is linked: a note contradicting an unlinked stranger passes write time unnoticed,
which is the same limit D13 already accepted and leaves to read time to find. That is also
a standing argument for adding wikilinks eagerly in refine — links are now what makes
contradictions findable, not just what makes notes navigable.
