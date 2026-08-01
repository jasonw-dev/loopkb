# loopkb

**A loop-driven knowledge base framework for AI agents.** Obsidian-compatible,
git-native, and continuously self-improving.

*(中文導讀在文末)*

## What makes it different

Most "AI + notes" setups stop at write time: the agent files a note and never looks
back. loopkb treats the knowledge base as something an agent **maintains**, not just
appends to:

- **Auto-classification** — drop anything into `_inbox/`; the agent classifies it
  against explicit, versioned rules.
- **Maintenance loop** — a stateless 4-stage pipeline (triage → refine → reflect →
  lint) that keeps improving the vault: linking, merging, distilling, re-checking
  old notes for staleness.
- **Rule evolution** — when humans correct the agent's filing — by fixing it directly,
  by reverting its commit, or by closing its merge request — the reflect stage mines
  those corrections and changes the classification rules. The taxonomy learns.
- **Executable schema** — `scripts/lint.py` (stdlib-only Python 3) is the definition
  of what a valid note is, so "is the vault healthy?" has a deterministic answer.

## Architecture

- **Vault = git repo = Obsidian vault.** Notes are plain Markdown + YAML frontmatter.
  Humans use Obsidian; agents use the filesystem. Git is the sync layer, the review
  layer (diffs — post-hoc via the digest, or in MRs), and the undo layer (`git revert`).
- **Type folders × domain tags.** The stable axis (note type: troubleshooting,
  decisions, guides, references, meetings) is folders; the growing axis (domains) is a
  closed tag vocabulary declared by the instance.
- **Framework vs. instance.** This template carries the structure, schema, skills, and
  rule *formats*. Every instance-specific setting lives in exactly one file,
  `_meta/instance.md` — so an instance can pull template updates with a plain
  `git merge upstream/main` and never hit a conflict in its own configuration.
  Scale by adding vaults, not by deepening one.
- **Governance: post-hoc revert or pre-approval, per instance.** In the default
  `autonomous` mode agents commit everything to main — merges, deletions, rule changes
  included — and must itemize each risky action in `_meta/digest.md`; the human spends
  two minutes a week reading it and `git revert`s what they disagree with, so nothing
  ever blocks on them and no MR platform is involved. `reviewed` mode is the opt-in
  alternative: destructive actions wait in merge requests. Either way `evergreen` is
  human-conferred (agents nominate, never promote), reverts and closed MRs are read as
  the same rejection signal, and humans always commit freely.

## What it looks like

```
vault/
├── _inbox/            ← drop anything here; the loop classifies it
├── _meta/             ← instance config, taxonomy, loop spec, note templates
├── scripts/           ← lint.py (schema check) · lease.py (one loop run at a time)
├── troubleshooting/   ← symptom → cause → fix
├── decisions/         ← lightweight ADRs
├── guides/            ← how-to
├── references/        ← external material, summarized
└── meetings/
```

A filed note:

```markdown
---
type: troubleshooting
domains: [ci-cd]
created: 2026-08-01
source: inbox
status: curated
---
# Release build fails on stale cache

## Symptom
CI release job fails with checksum mismatch after a dependency bump.

## Cause / ## Fix / ## Related
…
```

## Quick start

1. Create a repo from this template.
2. Read **[GETTING-STARTED.md](GETTING-STARTED.md)** — three daily actions, plus
   instance setup (one file to fill in) and how to pull template updates.
3. Joining a vault that already exists? Install the plugin (below) and say
   `kb-setup <vault repo URL>` — that is the whole onboarding.
4. Agents start at **[CLAUDE.md](CLAUDE.md)** (Codex etc. via [AGENTS.md](AGENTS.md)).

Requirements: git, Python 3 (stdlib only, for `scripts/`),
[Claude Code](https://claude.com/claude-code) as the primary agent. Other agents work
through the same rule files in `_meta/`.

## Using the skills outside a vault

The vault's four skills live in `.claude/skills/` and load automatically when you
open the vault itself. To get them in *other* repos — so `kb-save` and `kb-search`
work while you are debugging some project — install this repo as a Claude Code plugin:

```
/plugin marketplace add jasonw-dev/loopkb
/plugin install loopkb@loopkb
```

They then appear as `/loopkb:kb-setup`, `/loopkb:kb-save`, `/loopkb:kb-search`,
`/loopkb:kb-loop`. Joining an existing vault is then one sentence —
`kb-setup <vault repo URL>` clones it, validates it, and wires the machine.
The plugin manifest points straight at `.claude/skills/`, so the vault's skill files
remain the single source of truth — there is no second copy to drift.

## Design

The reasoning behind the framework's load-bearing choices is recorded in
[docs/design-decisions.md](docs/design-decisions.md).

## License

MIT

---

## 中文導讀

loopkb 是給 AI Agent 用的知識庫框架：Obsidian 相容、git 原生、會自我改善。

核心差異在 **loop engineering**——知識庫不是「寫入就結束」：agent 定期跑四階段維護迴圈
（歸檔 → 精煉 → 反省 → 健檢），持續補連結、合併重複、蒸餾筆記、重新檢查老筆記是否過期；
而人類對 agent 的修正（直接改掉、`git revert` 掉、或把 agent 開的 MR 關掉不合併）會被
反省階段挖出來，變成分類規則的修改——規則會學習。

**治理模式**：預設 `autonomous`——agent 全部直接 commit 到 main，但每個高風險動作都要列進
`_meta/digest.md`；人類每週讀兩分鐘、不同意就 `git revert`，整條 loop 不卡在人身上，也不需要
任何 MR 平台。想要事前審查就改成 `reviewed`，破壞性動作改走 MR。`evergreen` 兩種模式下都只有
人類能授予。

結構上：型態用資料夾、領域用封閉 tag 字彙；框架（本 template）與實例（各團隊/個人 vault）
分離，實例設定全部集中在 `_meta/instance.md` 一個檔案，所以拉模板更新只要 `git merge upstream/main`
就好。規模化靠開新 vault 而非加深單一 vault。從 [GETTING-STARTED.md](GETTING-STARTED.md) 開始。
