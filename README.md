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
  lint) that keeps improving the vault: linking, merging, distilling.
- **Rule evolution** — when humans correct the agent's filing, the reflect stage mines
  those corrections from git history and proposes rule changes via merge request.
  The taxonomy learns.

## Architecture

- **Vault = git repo = Obsidian vault.** Notes are plain Markdown + YAML frontmatter.
  Humans use Obsidian; agents use the filesystem. Git is the sync, review
  (MR diffs), and rollback layer.
- **Type folders × domain tags.** The stable axis (note type: troubleshooting,
  decisions, guides, references, meetings) is folders; the growing axis (domains) is a
  closed tag vocabulary in `_meta/taxonomy.md`.
- **Framework vs. instance.** This template carries the structure, schema, skills, and
  rule *formats*. Each instance (a team KB, a personal second brain) fills in its own
  vocabulary and policies. Scale by adding vaults, not by deepening one.
- **Write tiers.** Additive operations commit straight to main; destructive ones
  (merge, delete, move, rule changes) go through MRs a human reviews.

## Quick start

1. Create a repo from this template.
2. Read **[GETTING-STARTED.md](GETTING-STARTED.md)** — three daily actions, plus
   instance setup.
3. Agents start at **[CLAUDE.md](CLAUDE.md)** (Codex etc. via [AGENTS.md](AGENTS.md)).

Requirements: git, [Claude Code](https://claude.com/claude-code) (primary agent;
skills in `.claude/skills/`). Other agents work through the same rule files in `_meta/`.

## License

MIT

---

## 中文導讀

loopkb 是給 AI Agent 用的知識庫框架：Obsidian 相容、git 原生、會自我改善。

核心差異在 **loop engineering**——知識庫不是「寫入就結束」：agent 定期跑四階段維護迴圈
（歸檔 → 精煉 → 反省 → 健檢），持續補連結、合併重複、蒸餾筆記；而人類對 agent 分類的修正
會被反省階段從 git 歷史挖出來，變成分類規則的修改提案（走 MR）——規則會學習。

結構上：型態用資料夾、領域用封閉 tag 字彙；框架（本 template）與實例（各團隊/個人 vault）
分離，規模化靠開新 vault 而非加深單一 vault。從 [GETTING-STARTED.md](GETTING-STARTED.md) 開始。
