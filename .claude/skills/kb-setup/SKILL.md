---
name: kb-setup
description: Use when asked to set up or join a loopkb vault — "kb-setup <git url>", "set up the knowledge base", "join the team vault". Clones the vault, validates it, and wires this machine's KB_VAULT path.
---

# kb-setup

Make this machine ready to use a loopkb vault. One pass, no retry loops.

## 0. Are we already in the vault?

If the current repo contains `_meta/loop.md`, it **is** a loopkb vault: there is no URL
to ask for and nothing to clone. Take `<dest>` = this repo's root and skip straight to
step 5 (Validate) — steps 1–4 are for joining a vault from outside. Opening a vault clone
and saying `kb-setup` is the common way to land here, and every vault carries the entry
points that route to this file, so expect this branch often.

Derive `<vault-name>` from the repo rather than from a URL:

```
git remote get-url origin        # basename, with any trailing `.git` removed
```

`git@host:team/team-kb.git` → `team-kb`. No `origin` remote (a solo vault that never
pushes) → the vault directory's own basename.

## 1. Input

Take the vault's git URL from the request. If none was given, ask for it and wait —
nothing below works without it. Derive `<vault-name>` from the repo name
(`git@host:team/team-kb.git` → `team-kb`).

## 2. Existing clone?

If a `KB_VAULT` line for this vault is already in your loaded context, or the user says
they already have a clone, check that `<path>/_meta/loop.md` exists.
Exists → skip to step 5 with that path. Missing → the path is unusable; continue at step 3.

## 3. Destination

Propose a default path, then ask the user to confirm or change it. Follow the directory
conventions visible in their environment (where their other repos live, an existing
projects directory); fall back to `~/<vault-name>`. **Never run `git clone` before the
user has seen the path.**

## 4. Clone

```
git clone <url> <dest>
```

On network failure, name the host that was unreachable and ask whether a VPN, proxy or
different remote is needed. Ask once and retry once after the answer — do not loop.

## 5. Validate

- `<dest>/_meta/loop.md` must exist. If it does not, this repo is **not a loopkb vault** —
  say so and stop. Nothing below applies.
- Run `python3 <dest>/scripts/lint.py` and report its output and exit status. Non-zero is
  the vault's problem, not the setup's: report it and carry on.

## 6. Wire the machine

Create `~/.claude/<vault-name>.md` containing:

```
KB_VAULT: <dest>
```

This is the per-user file that wired project repos import
(`@~/.claude/<vault-name>.md`), so the path is set once per machine and every wired repo
picks it up. A personal path never belongs in a committed file.

If that file already exists with a different path, show both paths and ask which one
wins before overwriting. If that existing path is a clone of a **different** vault, this
is a name collision, not a moved clone: several vaults on one machine are fine, but their
repo basenames must differ, because this file is named after the basename. Say so — the
fix is renaming one of the vault repos, since overwriting silently unwires the other one.

## 7. Setup gate

Read `<dest>/_meta/instance.md` → "Domain tag vocabulary". An empty list means the vault
is not configured yet: `kb-loop` refuses to run and triage has nothing to classify
against. Say so, then:

- **They created this vault** → point at `GETTING-STARTED.md` → "Starting a new instance
  (creator, once per team)" and offer to work the checklist with them.
- **They are joining someone else's vault** → tell them to ask the vault owner to finish
  it. `kb-save` and `kb-search` still work meanwhile; only the loop is blocked.

## 8. Orient the user

Close with at most six lines:

- Drop anything into `_inbox/`, then commit and push it.
- Say `kb-save` in any conversation right after solving something.
- Run `kb-loop` in the vault about once a week.
- The run report lives in `<dest>/_meta/digest.md`.
- To wire a project repo so its agents search the vault, see
  `<dest>/.claude/skills/kb-search/SKILL.md` → "Wiring a project repo".
