# Getting Started

*(中文導讀在文末 · Chinese quick guide at the bottom)*

You interact with this knowledge base through **three daily actions**. Everything else
is done by the maintenance loop.

## The three actions

### 1. Drop anything into `_inbox/`

Rough notes, pasted links, meeting transcripts — any Markdown (or plain text) file,
zero formatting required. Classification is not your job; the loop does it.

Then **commit and push** the drop (`git add _inbox && git commit && git push`) — or
run the loop from the same machine you dropped it on. An uncommitted file exists on
one disk only; a loop run anywhere else cannot see it.

### 2. Save from a conversation: kb-save

Just solved a problem with your AI agent? Say **"kb-save"** (or "save this to the
knowledge base") in that conversation. The agent extracts the knowledge, formats it,
classifies it, and commits it. One sentence of effort.

### 3. Run the loop weekly: kb-loop

Open the vault in Claude Code and say **"run kb-loop"**. The agent will:

1. **Triage** — classify and file everything in `_inbox/`.
2. **Refine** — improve a batch of notes: add links, fix formatting, re-check the
   oldest notes for staleness, propose merges.
3. **Reflect** — learn from your corrections (including the proposals you rejected)
   and propose classification-rule changes.
4. **Lint** — run `python3 scripts/lint.py` and fix what it reports.

Then review what it reports: merge requests need your approval; items stuck in the
inbox need one sentence of added context.

Only one loop run happens at a time — the run takes a lease (`scripts/lease.py`) on a
`kb-loop-lock` branch, so a second run started elsewhere stops instead of colliding.

## Concepts in plain words

**Why a loop?** A write-only knowledge base rots: duplicates pile up, nothing links to
anything, and in six months it is a junk drawer. The loop is the difference — the vault
gets *better* over time because an agent keeps re-organizing, connecting, and distilling it.

**Status lifecycle** (`raw → curated → evergreen`): every note carries a quality label.
`raw` = just filed. `curated` = linked and cleaned, promoted by the agent once it meets
a mechanical floor. `evergreen` = distilled and trustworthy long-term — **only a human
grants it**; the agent can nominate a note via merge request but never promote it
itself. That is exactly why readers can trust `evergreen` more.

**Why do corrections matter?** When the agent files something wrong, just move/fix it
yourself and commit (no special commit message needed — and don't bother updating the
note's frontmatter; the loop's lint stage reconciles it). Closing an agent's merge
request without merging counts too. The loop's reflect stage reads git history and the
platform, notices your correction, and proposes a rule change so the same mistake stops
happening. Your corrections ARE the training signal.

## Starting a new instance from this template

Work through this checklist — the instance is ready when every box is checked:

- [ ] Create a new repo from this template (GitHub "Use this template", or copy the tree).
- [ ] Fill `_meta/instance.md`: identity (note body language, vault scope), the domain
      tag vocabulary, and any policy overrides. This is the **only** file you fill in —
      every other file is framework-owned, which is what keeps template updates
      mergeable (see "Updating an instance" below).
- [ ] The domain vocabulary must be non-empty: it is the machine-checkable definition
      of "setup complete". While it is empty, `kb-loop` refuses to run and agents may
      still edit `_meta/` directly; once it is filled, agents may only change `_meta/`
      through merge requests.
- [ ] Add/remove type folders if the domain calls for it (e.g. a personal vault may
      add `journal/`) — add the matching `_meta/templates/<type>.md`, since the linter
      derives the type-folder set from the templates.
- [ ] Run `python3 scripts/lint.py` — it must exit 0 on the fresh instance.
- [ ] Ensure `main` allows direct pushes by members and agents (no branch protection
      blocking them) — the additive write tier depends on it. If your platform
      enforces protection, route ALL writes through MRs via an instance policy override.
- [ ] Rewrite the README for your instance (the template README describes the framework).
- [ ] Wire your project repos: see "Wiring a project repo" in `.claude/skills/kb-search/SKILL.md`.
- [ ] Open the vault in Obsidian once to confirm it reads well.

If you run CI, wire `python3 scripts/lint.py` into it — one job per push keeps schema
violations from ever reaching the weekly loop.

## Updating an instance

The framework and the instance own disjoint files, so template updates arrive as an
ordinary merge:

```bash
git remote add upstream https://github.com/jasonw-dev/loopkb.git   # once
git fetch upstream
git merge upstream/main
```

Instance-owned content never conflicts: the template ships `_meta/instance.md` as an
empty skeleton and nothing else carries instance-specific content. The one case that
needs hands is when the **skeleton itself** changed upstream (a new section, a renamed
one): git will report a conflict in `_meta/instance.md` — keep your values, adopt the
new structure around them, and commit the merge.

Everything else (CLAUDE.md, `_meta/taxonomy.md`, `_meta/loop.md`, `_meta/templates/`,
`.claude/skills/`, `scripts/`) is framework-owned. If you edited one of those files
locally, the merge will conflict there — that is the signal to move the customization
into `_meta/instance.md` as a policy override instead.

---

## 中文導讀

日常只有三個動作：

1. **丟東西進 `_inbox/`**——隨手筆記、連結、逐字稿，不用整理格式，分類是 agent 的事。丟完記得 commit + push，不然別台機器跑 loop 看不到。
2. **對話中說 kb-save**——剛跟 AI 解完一個問題，順口一句「存進知識庫」，agent 會萃取、格式化、分類、commit。
3. **每週跑一次 kb-loop**——agent 會清空 inbox、精煉筆記、從你的修正中學習、跑 lint。跑完看報告：MR 要你批准、卡在 inbox 的東西補一句說明即可。

**為什麼要 loop**：只寫不理的知識庫半年就變垃圾場。loop 讓它隨時間變好——agent 持續重整、連結、蒸餾。

**status 生命週期**：`raw`（剛歸檔）→ `curated`（整理過，agent 可自行升級）→ `evergreen`（可長期信賴，**只有人類能授予**；agent 只能開 MR 提名）。讀的人優先信任高 status。

**你的修正就是訓練訊號**：agent 分錯了，直接自己搬正、commit 即可（不用特殊格式）；把 agent 開的 MR 關掉不合併也算一種修正訊號。loop 的反省階段會從 git 歷史與平台看到這些修正，提議改分類規則，讓同樣的錯不再發生。

**開新實例**：只需要填 `_meta/instance.md` 一個檔案（語言、範圍、領域標籤字彙、政策覆寫）；其餘都是框架檔案，所以之後 `git merge upstream/main` 拉模板更新不會衝突。
