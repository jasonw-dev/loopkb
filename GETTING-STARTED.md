# Getting Started

*(中文導讀在文末 · Chinese quick guide at the bottom)*

You interact with this knowledge base through **three daily actions**. Everything else
is done by the maintenance loop.

## The three actions

### 1. Drop anything into `_inbox/`

Rough notes, pasted links, meeting transcripts — any Markdown (or plain text) file,
zero formatting required. Classification is not your job; the loop does it.

### 2. Save from a conversation: kb-save

Just solved a problem with your AI agent? Say **"kb-save"** (or "save this to the
knowledge base") in that conversation. The agent extracts the knowledge, formats it,
classifies it, and commits it. One sentence of effort.

### 3. Run the loop weekly: kb-loop

Open the vault in Claude Code and say **"run kb-loop"**. The agent will:

1. **Triage** — classify and file everything in `_inbox/`.
2. **Refine** — improve a batch of notes: add links, fix formatting, propose merges.
3. **Reflect** — learn from your corrections and propose classification-rule changes.
4. **Lint** — find broken links and schema violations.

Then review what it reports: merge requests need your approval; items stuck in the
inbox need one sentence of added context.

## Concepts in plain words

**Why a loop?** A write-only knowledge base rots: duplicates pile up, nothing links to
anything, and in six months it is a junk drawer. The loop is the difference — the vault
gets *better* over time because an agent keeps re-organizing, connecting, and distilling it.

**Status lifecycle** (`raw → curated → evergreen`): every note carries a quality label.
`raw` = just filed. `curated` = linked and cleaned. `evergreen` = distilled, trustworthy
long-term. The loop pushes notes up this ladder; readers (human and agent) trust higher
statuses more.

**Why do corrections matter?** When the agent files something wrong, just move/fix it
yourself and commit (no special commit message needed — and don't bother updating the
note's frontmatter; the loop's lint stage reconciles it). The loop's reflect stage reads
git history, notices your correction, and proposes a rule change so the same mistake
stops happening. Your corrections ARE the training signal.

## Starting a new instance from this template

Work through this checklist — the instance is ready when every box is checked:

- [ ] Create a new repo from this template (GitHub "Use this template", or copy the tree).
- [ ] Fill the instance header (body language, vault scope) at the top of `_meta/taxonomy.md`.
- [ ] Fill the domain tag vocabulary in `_meta/taxonomy.md` — the loop refuses to
      run while it is empty.
- [ ] Adjust instance policy in `CLAUDE.md` below the `INSTANCE OVERRIDES` marker
      (e.g. stricter MR rules during a trial period; solo vaults: MRs become
      "commit to a branch, self-review the diff, merge").
- [ ] Add/remove type folders if the domain calls for it (e.g. a personal vault may
      add `journal/`) — update `_meta/taxonomy.md` and `_meta/templates/` to match.
- [ ] Ensure `main` allows direct pushes by members and agents (no branch protection
      blocking them) — the additive write tier depends on it. If your platform
      enforces protection, route ALL writes through MRs via an instance override.
- [ ] Rewrite the README for your instance (the template README describes the framework).
- [ ] Wire your project repos: see "Wiring a project repo" in `.claude/skills/kb-search/SKILL.md`.
- [ ] Open the vault in Obsidian once to confirm it reads well.

---

## 中文導讀

日常只有三個動作：

1. **丟東西進 `_inbox/`**——隨手筆記、連結、逐字稿，不用整理格式，分類是 agent 的事。
2. **對話中說 kb-save**——剛跟 AI 解完一個問題，順口一句「存進知識庫」，agent 會萃取、格式化、分類、commit。
3. **每週跑一次 kb-loop**——agent 會清空 inbox、精煉筆記、從你的修正中學習、健檢連結。跑完看報告：MR 要你批准、卡在 inbox 的東西補一句說明即可。

**為什麼要 loop**：只寫不理的知識庫半年就變垃圾場。loop 讓它隨時間變好——agent 持續重整、連結、蒸餾。

**status 生命週期**：`raw`（剛歸檔）→ `curated`（整理過）→ `evergreen`(可長期信賴)。loop 負責往上推，讀的人優先信任高 status。

**你的修正就是訓練訊號**：agent 分錯了，直接自己搬正、commit 即可（不用特殊格式）。loop 的反省階段會從 git 歷史看到你的修正，提議改分類規則，讓同樣的錯不再發生。
