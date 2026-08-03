# Getting Started

*(中文導讀在文末 · Chinese quick guide at the bottom)*

You interact with this knowledge base through **three daily actions**. Everything else
is done by the maintenance loop.

## Two roles

There are exactly two jobs around a vault, and most people only ever do the second one.

**Creator** — once per team. Instantiate this template into a new repo, fill
`_meta/instance.md`, grant your teammates write access, and share the vault URL.
See "Starting a new instance (creator, once per team)" below.

**Member** — once per machine. Install the Claude Code plugin and run
`kb-setup <vault URL>`. There is a path for Claude Code and a manual one for any other
agent — see "Joining a vault (member, once per machine)" right below.

The creator is also a member: creating the vault does not wire your own machine, so you
run `kb-setup` too.

## Joining a vault (member, once per machine)

Pick the path for the agent you use. Both end in the same place: a vault clone, and
a `~/.claude/<vault-name>.md` file holding one `KB_VAULT: <path>` line — the per-user
wiring every agent reads. The procedures themselves live in the vault
(`.claude/skills/*/SKILL.md`) and are agent-agnostic; only the way you *reach* them differs.
The framework ships ready-made entry points for Claude Code only — every other agent takes
the manual path below and reads the same files.

### Claude Code

You never run `git clone` yourself: the plugin machinery fetches the skills, and
`kb-setup` clones the vault for you. Install the plugin and say one sentence:

```
/plugin marketplace add jasonw-dev/loopkb
/plugin install loopkb@loopkb
```

```
kb-setup https://github.com/<org>/<vault-repo>.git
```

`kb-setup` asks you where to clone, clones it, checks it really is a loopkb vault, runs
the linter, and writes the per-user `~/.claude/<vault-name>.md` file that every wired
project repo imports. Then it tells you the three actions below. Nothing else to do.

### Any other agent

Four steps by hand — and yes, this path really does clone the vault yourself, because
there is no packaging mechanism to do it for you:

1. `git clone <vault repo URL> <dest>` — any path you like.
2. Create `~/.claude/<vault-name>.md` with a single line: `KB_VAULT: <dest>`.
   (Per-user file, never committed: it is why a personal path stays out of git.
   `<vault-name>` is the repo basename without `.git`.)
3. Verify the clone: `python3 <dest>/scripts/lint.py` must exit 0.
4. Point the agent at the vault: it starts at `<dest>/AGENTS.md` → `<dest>/CLAUDE.md`, and
   the four procedures are `<dest>/.claude/skills/<name>/SKILL.md` — say "read
   `<dest>/.claude/skills/kb-save/SKILL.md` and follow it" and it works. To wire a project
   repo so its agents do this on their own, see "Wiring a project repo" in
   `.claude/skills/kb-search/SKILL.md`.

This is also the fallback for Claude Code when you would rather not install anything.

### Multiple vaults on one machine

Fully supported. The plugin is installed once and serves every vault; run `kb-setup`
once per vault. Each vault gets its own `~/.claude/<vault-name>.md`, and each wired
project repo imports the file of the vault it belongs to — so a repo can point at the
team vault while another points at your personal one.

One caveat: **the vault repo basenames must be distinct across your vaults.** The
per-user file is named after the basename, so `team-kb` and `second-brain` coexist
happily, but two repos both named `kb` — even under different orgs or hosts — collide on
the same `~/.claude/kb.md`. Rename one of the repos, or accept that only one of them can
be wired on this machine.

## The three actions

### 1. Drop anything into `_inbox/`

Rough notes, pasted links, meeting transcripts — any Markdown (or plain text) file,
zero formatting required. Classification is not your job; the loop does it.

Then **commit and push** the drop (`git add _inbox && git commit && git push`) — or
run the loop from the same machine you dropped it on. An uncommitted file exists on
one disk only; a loop run anywhere else cannot see it.

A personal vault with no `origin` remote works fully offline: every skill skips the
pull and push and just commits.

### 2. Save from a conversation: kb-save

Just solved a problem with your AI agent? Say **"kb-save"** (or "save this to the
knowledge base") in that conversation. The agent extracts the knowledge, formats it,
classifies it, and commits it. One sentence of effort.

### 3. Run the loop weekly: kb-loop

Open the vault in Claude Code and say **"run kb-loop"**. The agent will:

1. **Triage** — classify and file everything in `_inbox/`.
2. **Refine** — improve a batch of notes: add links, fix formatting, re-check the
   oldest notes for staleness, propose merges.
3. **Reflect** — learn from your corrections (including the actions you rejected)
   and change the classification rules accordingly.
4. **Lint** — run `python3 scripts/lint.py` and fix what it reports.

Every run writes its report to **`_meta/digest.md`** — that file is your whole
interface to the loop. See "Reviewing the loop's work" below.

Only one loop run happens at a time — the run takes a lease (`scripts/lease.py`) on a
`kb-loop-lock` branch, so a second run started elsewhere stops instead of colliding.

Order of magnitude, so you can plan: one run touches about ten notes and takes minutes
of agent time (and the matching API cost). It is a weekly-coffee-break operation, not a
background daemon — a vault with hundreds of pending notes is drained over several runs,
by design.

#### When a run refuses to start

`lease: held by …` means the lock is taken — most often by a previous run that crashed,
since a healthy run releases it on the way out. Two legitimate ways out: **wait**, because
a lock goes stale after 2h and the next run replaces it by itself, or — when you know that
run is dead — clear it with `python3 scripts/lease.py release --force`. The `--force` is
required by design: a plain `release` refuses to delete a lock it does not hold, so a run
that lost the race cannot end the exclusivity of the run that won it. Your terminal is
never the session that took the lock — the loop run is — which is why clearing it by hand
takes `--force` rather than a plain `release`. `python3 scripts/lease.py status` shows who
holds it, since when, and whether it has gone stale.

If `release` exits non-zero because it could not reach `origin`, the lease is **not**
released: your local ref is gone but the lock on `origin` still stands, and every other
clone sees the vault as locked. Rerun `release` once you are back online.

## Reviewing the loop's work

The vault runs in one of two **governance modes**, set in `_meta/instance.md` →
Governance. It decides *when* you look at the agent's work, not how much you have to.

### `autonomous` — the default: review after the fact

The agent does everything by committing straight to `main`: filing, linking, merging
duplicates, deleting, renaming, even changing the classification rules. In exchange it
must itemize every risky action in the digest.

Your weekly duty, about two minutes:

1. Open `_meta/digest.md` — in Obsidian, or any Markdown editor. Read the header and the **Risky actions**
   section at the top — it lists every merge, deletion, rename, demotion and rule
   change, each with its commit SHA.
2. Disagree with one? `git revert <sha>`. That is the whole rejection mechanism —
   no approvals, no queue, nothing waiting on you.
3. Glance at **Stuck** (inbox items needing one sentence of context) and
   **Nominations** (notes the agent thinks deserve `evergreen`). Promote a nominated
   note by editing its `status:` and committing; ignore it and the nomination lapses.

A revert is a strong signal, not just an undo: the next run reads it, records the
action as rejected, and will not re-attempt it unless the notes involved really change.

### `reviewed` — approve before anything lands

Destructive actions and rule changes arrive as merge requests instead. The digest
lists the open MRs; you approve or close them. Closing one without merging is the
rejection signal, exactly as a revert is in `autonomous` mode. Additive work (filing,
links, tags, `raw → curated`) still commits directly in this mode too.

Two prerequisites before you pick it. It needs an **MR platform** (`gh`, `glab`, or the
platform's API — name it in `_meta/instance.md` → Policy overrides); with none, run
`autonomous`, which is the mode built for that case. And your project's **merge method
must be "merge commit"**: `scripts/verify_digest.py` reads a merge as the human review and
skips it, so an MR landed by squash or rebase arrives as a single commit it cannot tell
from one that skipped review — and your approved work is reported as missing from the
digest, on a run where you did everything right. If you cannot change the merge method,
every squashed MR has to be itemized in the digest exactly like a direct commit.

Pick `reviewed` when you do not yet trust the agent with your vault, and switch to
`autonomous` once you find yourself approving everything unread.

## Automating the loop (optional)

The manual flow is the default and stays fully supported: once a week, someone opens the
vault and says "run kb-loop". If you would rather it happen on a schedule, nothing in the
framework objects — the lease already makes a scheduled run and a manual one safe to
overlap (whoever starts second stops cleanly instead of colliding), and the digest is
written the same way either way.

The honest prerequisites, before the YAML:

- **A funded API key.** A headless agent run costs real money, and a schedule turns that
  into a recurring cost. Nothing here is free.
- **Push access for the runner.** The job commits to `main`, so its token needs push
  rights and — in `autonomous` mode — no branch protection standing in the way.
- **Someone still reads the digest.** Automating the run does not automate the review;
  it only changes who types the sentence.
- **Give the runner its own identity** via `KB_LOOP_HOLDER` (e.g. `ci-schedule`), so the
  lease messages and the digest header say plainly which runs were unattended.

**The two YAML snippets below are untested skeletons.** They show the shape of the job —
schedule, full history, install, one sentence — and nothing more: no scheduled loop run
has been exercised end to end by this project, so treat them as a starting point you will
debug, not a recipe that works on first push. Three things they deliberately do not solve,
and you must:

1. **Set the runner's git identity** — `user.name` and `user.email` in its checkout
   (`git config user.name "kb-loop bot"` and the matching address). This is the *commit*
   identity, not `KB_LOOP_HOLDER` above, and without it the run's first commit fails
   mid-run — after the lease was taken.
2. **Let the headless agent push.** A non-interactive agent still needs permission for git
   commands; unattended, an approval prompt is a hang, not a question. Grant it up front
   through your agent's allowlist or permission flags (Claude Code: settings `permissions`
   / `--allowedTools`), and confirm it can reach `origin` with a credential that may push
   `main`.
3. **Fund an API key.** A headless run costs real money and a schedule makes it recurring,
   as the list above says — verify the key works non-interactively before trusting a cron.

GitHub Actions, weekly:

```yaml
# .github/workflows/kb-loop.yml
name: kb-loop
on:
  schedule:
    - cron: "0 6 * * 1"           # Mondays, 06:00 UTC
  workflow_dispatch:
jobs:
  loop:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0          # reflect and the digest verifier both read history
      - run: npm install -g @anthropic-ai/claude-code
      - env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          KB_LOOP_HOLDER: github-actions
        run: claude -p "run kb-loop"
```

GitLab CI, same shape — add the job, then create the schedule under **Build → Pipeline
schedules**. The runner's clone needs a push credential (a project access token in the
remote URL); `GIT_DEPTH: 0` is the equivalent of `fetch-depth: 0`:

```yaml
# .gitlab-ci.yml
kb-loop:
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule"
  image: node:22
  variables:
    GIT_DEPTH: 0
    KB_LOOP_HOLDER: gitlab-schedule
  script:
    - npm install -g @anthropic-ai/claude-code
    - claude -p "run kb-loop"
```

**Lint in CI** is far cheaper than automating the loop and worth it either way — it
catches schema violations at push time instead of at the weekly run. This repo ships
`.github/workflows/lint.yml`, which works unchanged for any GitHub-hosted instance — and
unlike the skeletons above it is not untested: it runs on this repository on every push.
There
is deliberately no root `.gitlab-ci.yml`: that file would switch CI on for every instance
the moment it merged a template update, so GitLab instances opt in by pasting this:

```yaml
# .gitlab-ci.yml
lint:
  image: python:3-slim
  script:
    - python3 scripts/lint.py
    - python3 -m unittest discover -s tests
```

## Concepts in plain words

**Why a loop?** A write-only knowledge base rots: duplicates pile up, nothing links to
anything, and in six months it is a junk drawer. The loop is the difference — the vault
gets *better* over time because an agent keeps re-organizing, connecting, and distilling it.

**Status lifecycle** (`raw → curated → evergreen`): every note carries a quality label.
`raw` = just filed. `curated` = linked and cleaned, promoted by the agent once it meets
a mechanical floor. `evergreen` = distilled and trustworthy long-term — **only a human
grants it, in either governance mode**; the agent can nominate a note (a digest line, or
a merge request) but never promote it itself. That is exactly why readers can trust
`evergreen` more.

**Why do corrections matter?** When the agent files something wrong, just move/fix it
yourself and commit (no special commit message needed — and don't bother updating the
note's frontmatter; the loop's lint stage reconciles it). Reverting an agent commit
counts too, as does closing an agent's merge request without merging. The loop's
reflect stage reads git history (and, in `reviewed` mode, the MR platform), notices your
correction, and changes the rules so the same mistake stops happening. Your corrections
ARE the training signal — and in `autonomous` mode, `git revert` is the *only* control
you need, which is why it must stay meaningful: revert what is actually wrong.

## Starting a new instance (creator, once per team)

Work through this checklist — the instance is ready when every box is checked:

- [ ] Create a new repo from this template. On GitHub: "Use this template". On **any
      other git host** (GitLab, Bitbucket, self-hosted), create an empty repo there
      first — no README, no initial commit — then:
  ```bash
  git clone --depth 1 https://github.com/jasonw-dev/loopkb.git <vault-name>
  cd <vault-name> && rm -rf .git && git init -b main
  git add -A && git commit -m "chore: instantiate vault from loopkb template"
  git remote add origin <your platform's repo URL>
  git push -u origin main
  git remote add upstream https://github.com/jasonw-dev/loopkb.git
  ```
  Dropping `.git` gives the vault a fresh history of its own — the template's provenance
  lives in that first commit message instead. The `upstream` remote is what later merges
  template updates in ("Updating an instance" below); adding it now means you never have
  to remember where the template came from. Either route (template button or this recipe)
  leaves your history unrelated to the template's, so the *first* update merge needs
  `--allow-unrelated-histories` and conflicts by design — "Updating an instance" walks
  through it.
- [ ] Fill `_meta/instance.md`: identity (note body language, vault scope), the domain
      tag vocabulary, and any policy overrides. Leave "Classification rule amendments"
      empty — that section is where the loop writes the rules it learns from your
      corrections, and it stays yours across template updates. This is the **only** file
      you fill in —
      every other file is framework-owned, which is what keeps template updates
      mergeable (see "Updating an instance" below). *Adding* files is a different matter
      and stays open to you: an instance may ship its own team skills as thin pointers in
      `.claude/skills/<name>/SKILL.md` that point at the instance's own canonical guide in
      the vault — every clone gets them with nothing to install, and since upstream never
      ships those names, a template merge leaves them alone.
- [ ] Choose the governance mode in `_meta/instance.md` → Governance. Default:
      `autonomous` (agent commits everything, you review `_meta/digest.md` and revert).
      Switch to `reviewed` if destructive actions should wait for your approval — see
      "Reviewing the loop's work" above, including its two prerequisites: an MR platform,
      and a merge method set to "merge commit".
- [ ] The domain vocabulary must be non-empty: it is the machine-checkable definition
      of "setup complete". While it is empty, `kb-loop` refuses to run and agents may
      still edit `_meta/` directly and unreported; once it is filled, `_meta/` changes
      are either itemized in the digest (`autonomous`) or gated by a merge request
      (`reviewed`).
- [ ] Add/remove type folders if the domain calls for it (e.g. a personal vault may
      add `journal/`) — add the matching `_meta/templates/<type>.md`, since the linter
      derives the type-folder set from the templates.
- [ ] Run `python3 scripts/lint.py` — it must exit 0 on the fresh instance.
      *(Maintainer note: `python3 -m unittest discover -s tests` runs the framework's own
      stdlib test suite — every linter rule, the lease's compare-and-swap, and the digest
      verifier. Run it whenever you touch anything under `scripts/`; CI runs both.)*
- [ ] Ensure `main` allows direct pushes by members and agents (no branch protection
      blocking them) — every write tier in `autonomous` mode and the additive tier in
      `reviewed` mode depend on it. Platform defaults often fight this:
      **GitLab** protects the default branch on creation and may block all pushes —
      Settings → Repository → Protected branches, set "Allowed to push and merge" to
      Developers + Maintainers, and leave force-push off (or do it via the protected
      branches API).
      **GitHub** pushes are open by default — just do not add a branch protection or
      ruleset that blocks them, or add a bypass for the people and agents who push.
      If your platform enforces branch protection you cannot lift, you cannot run
      `autonomous`: use `reviewed`, and route ALL writes through MRs via an instance
      policy override.
- [ ] Rewrite the README for your instance (the template README describes the framework):
      copy `_meta/README.instance.md` over `README.md` and fill in the blanks. **Keep the
      join block** — the two plugin-install commands plus `kb-setup <your vault URL>` — or
      at minimum link to GETTING-STARTED.md → "Joining a vault (member, once per
      machine)". Once the framework README is gone, that block is the only place a new
      teammate finds the way in.
- [ ] Run `kb-setup <your vault URL>` on your own machine too — creating the vault did
      not wire this machine. It is what writes the per-user `~/.claude/<vault-name>.md`
      that every wired project repo imports.
- [ ] Wire your project repos: see "Wiring a project repo" in `.claude/skills/kb-search/SKILL.md`.
- [ ] *Optional*: open the vault in Obsidian once to confirm it reads well. Obsidian is a
      human reading UI, nothing more — the vault is fully usable without it.
- [ ] Grant your teammates write access to the repo — `autonomous` mode needs everyone
      able to push `main` — then tell them how to join: install the Claude Code plugin,
      then `kb-setup <your vault repo URL>`. Send them "Joining a vault (member, once per
      machine)" above; it has the Claude Code path and the manual one for any other agent.

If you run CI, wire `python3 scripts/lint.py` into it — one job per push keeps schema
violations from ever reaching the weekly loop.

## Updating an instance

The framework and the instance own disjoint files, so template updates arrive as an
ordinary merge — from the second one onward. The first has a one-off wrinkle; read
"The first merge" below before running this:

```bash
git fetch upstream
git merge upstream/main
```

(`upstream` is the remote added when you instantiated the vault. A repo made with
GitHub's "Use this template" has none — add it once with
`git remote add upstream https://github.com/jasonw-dev/loopkb.git`.)

### The first merge: unrelated histories

The first merge is the awkward one, and it is awkward for **every** instance. Both ways
of instantiating give the vault a history with no commit in common with the template's —
GitHub's "Use this template" starts a fresh initial commit, and the clone-and-reinit
recipe deletes `.git` on purpose (that is the point: the vault owns its history). So the
command above fails the first time you run it:

```
fatal: refusing to merge unrelated histories
```

Say it explicitly, once:

```bash
git merge upstream/main --allow-unrelated-histories
```

**Expect conflicts on this first merge — they are the expected outcome, not a failure.**
With no common ancestor, git cannot tell "you changed it" from "it was always like that",
so every file present in both trees that differs at all comes back as an add/add conflict
(`AA` in `git status --short`): every framework file that moved upstream since you
instantiated, plus the files you own. Resolving them is mechanical rather than a
judgement call — framework files take upstream, instance-owned files keep yours:

```bash
git checkout --theirs -- .                            # framework files: upstream wins
git checkout --ours  -- README.md _meta/instance.md \
                        _meta/digest.md               # yours: README, config, last report
git add -A
git commit
```

`_meta/digest.md` is on the `--ours` line for the same reason `README.md` is: the
template ships it saying "No runs yet.", and yours is your last run's report — the one
`scripts/verify_digest.py` checks your recent risky actions against. Framework-managed,
but the *content* is your vault's.

**Nothing your vault has learned is at risk here.** `git checkout --theirs -- .` replaces
`_meta/taxonomy.md` with upstream's copy, and that is safe because the loop never writes
that file: every classification rule the reflect stage learns is a dated entry under
`_meta/instance.md` → "Classification rule amendments", which the `--ours` line above
keeps. The framework owns the rule *format*; your instance owns the rules it learned.

Two caveats on that recipe. If upstream restructured the `_meta/instance.md` skeleton,
`--ours` keeps your values and you adopt the new sections by hand before committing. And
if you deliberately edited a framework file, `--theirs -- .` throws that edit away — which
is the framework's intended answer (express it as a policy override in
`_meta/instance.md`); reinstate it by hand only if you really mean to keep the fork.

Once that merge is committed, the two histories are connected. Every later update is the
plain two-liner above, and behaves as described next.

### Later merges

`_meta/digest.md` is framework-managed but pure run state, and upstream stopped touching
it after v1.1 — so however many runs have overwritten it in your instance, a template
merge will not conflict there.

Instance-owned content does not conflict once the histories are joined: the template
ships `_meta/instance.md` as an empty skeleton and nothing else carries instance-specific
content — including the classification rules your loop learned, which live in that same
file under "Classification rule amendments" and are therefore never touched by a merge.
The one case that needs hands is when the **skeleton itself** changed upstream (a
new section, a renamed one): git will report a conflict in `_meta/instance.md` — keep your
values, adopt the new structure around them, and commit the merge.

One file changes hands: **`README.md` becomes instance-owned** the moment you rewrite it
(checklist above). Upstream keeps editing the template README, so that file — and only
that file — will conflict on every merge that touches it. Keep yours:

```bash
git checkout --ours README.md && git add README.md
```

Everything else (CLAUDE.md, `_meta/taxonomy.md`, `_meta/loop.md`, `_meta/templates/`,
the `kb-*` skills in `.claude/skills/`, `scripts/`) is framework-owned and stays
conflict-free from the second merge onward. If you edited one of those files locally,
the merge will conflict there —
that is the signal to move the customization into `_meta/instance.md` as a policy
override instead.

### Verify after every merge

A template update can change the linter, the schema it enforces, the templates or the
scripts, so run the framework's own checks before you push the merge — after the first
merge especially, since you just resolved conflicts by hand:

```bash
python3 scripts/lint.py                   # the vault still satisfies the schema
python3 -m unittest discover -s tests     # the framework's scripts still work
python3 scripts/verify_digest.py          # the digest still accounts for every risky action
```

All three must exit 0. A failure here is a merge to fix, not a vault to worry about: the
usual cause is a linter rule that got stricter upstream, and its message names the notes
to correct.

---

## 中文導讀

**兩種角色**：**建立者**（每個團隊一次：從 template 開新 repo、填 `_meta/instance.md`、給團隊成員權限、把 vault URL 發出去）與**成員**（每台機器一次：裝 plugin、跑 `kb-setup <vault URL>`）。建立者自己也是成員——建好 vault 不等於這台機器已經接好。

**加入一個 vault**：兩條路徑，終點相同（一份 vault clone + `~/.claude/<vault-name>.md` 裡的 `KB_VAULT:` 一行）。**Claude Code**：你不用自己 `git clone`——裝好 plugin（`/plugin marketplace add jasonw-dev/loopkb` → `/plugin install loopkb@loopkb`）後說一句 `kb-setup <vault 的 git URL>`，clone、驗證、寫檔都由 agent 完成。**其他 agent**：上面英文段落有手動四步驟——這條路徑確實要你自己 clone。

**跨平台**：真正的操作程序只有一份，就在 vault 的 `.claude/skills/*/SKILL.md`；框架只替 Claude Code 準備現成的進入點，其他 agent 直接被指去讀同一份檔案——規則檔（`_meta/`、`CLAUDE.md`、`AGENTS.md`）本來就是任何 agent 都讀得懂的純文字，所以程序不會有第二份會走鐘的副本。

日常只有三個動作：

1. **丟東西進 `_inbox/`**——隨手筆記、連結、逐字稿，不用整理格式，分類是 agent 的事。丟完記得 commit + push，不然別台機器跑 loop 看不到。
2. **對話中說 kb-save**——剛跟 AI 解完一個問題，順口一句「存進知識庫」，agent 會萃取、格式化、分類、commit。
3. **每週跑一次 kb-loop**——agent 會清空 inbox、精煉筆記、從你的修正中學習、跑 lint。跑完打開 `_meta/digest.md` 看報告。

**兩種治理模式**（在 `_meta/instance.md` → Governance 選）：

- `autonomous`（預設，**事後審查**）：agent 全部直接 commit 到 `main`，包含合併、刪除、改名、改規則；但每一個高風險動作都必須列在 digest 最上面的 Risky actions 區、附 commit SHA。你每週花兩分鐘讀 digest，不同意就 `git revert <sha>`。**沒有任何事情卡在你身上**。
- `reviewed`（**事前審查**）：破壞性動作與規則變更走 MR，等你批准才會進 `main`；關掉不合併就是拒絕訊號。還不信任 agent 時用這個。

**為什麼要 loop**：只寫不理的知識庫半年就變垃圾場。loop 讓它隨時間變好——agent 持續重整、連結、蒸餾。

**status 生命週期**：`raw`（剛歸檔）→ `curated`（整理過，agent 可自行升級）→ `evergreen`（可長期信賴，**兩種模式下都只有人類能授予**；agent 只能提名——`autonomous` 寫在 digest 一行，`reviewed` 開 MR。你不理它，提名就自動失效，不會累積待辦）。讀的人優先信任高 status。

**你的修正就是訓練訊號**：agent 分錯了，直接自己搬正、commit 即可（不用特殊格式）；`git revert` 掉 agent 的 commit（`autonomous`）或把 agent 開的 MR 關掉不合併（`reviewed`）同樣算修正訊號。loop 的反省階段會從 git 歷史看到這些修正，改掉分類規則，讓同樣的錯不再發生——同一個被 revert 的動作，除非相關筆記真的變了，否則不會再做一次（被拒絕過的動作每一圈都是「當場從 git 歷史重新推導」，不是從上一份 digest 抄來的，所以 digest 不見也不會失憶）。學到的規則會寫進 `_meta/instance.md` 的「Classification rule amendments」段落——那是你的檔案，`_meta/taxonomy.md` 則屬於框架、agent 只讀不寫，所以之後拉模板更新不會把學到的規則蓋掉。

**開新實例**：只需要填 `_meta/instance.md` 一個檔案（語言、範圍、治理模式、領域標籤字彙、政策覆寫）；其餘都是框架檔案，所以之後 `git merge upstream/main` 拉模板更新幾乎不會衝突。唯一的例外是**第一次**：實例的 git 歷史與模板無關，第一次合併要加 `--allow-unrelated-histories`，而且一定會在所有變動過的檔案上產生 add/add 衝突——框架檔案取 upstream（`git checkout --theirs`）、`README.md` 與 `_meta/instance.md` 保留自己的（`git checkout --ours`），commit 之後歷史就接起來了，往後的合併就如上所述。細節見英文段落 "Updating an instance"。
