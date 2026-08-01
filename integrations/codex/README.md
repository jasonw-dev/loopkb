# loopkb for Codex CLI

Four thin entry points that let [Codex CLI](https://developers.openai.com/codex/) run the
vault's `kb-setup` / `kb-save` / `kb-search` / `kb-loop` procedures in any repo.

They are **pointers, not copies**: each one resolves the vault, then reads
`<KB_VAULT>/.claude/skills/<name>/SKILL.md` and follows it. The vault's SKILL.md files
stay the single source of truth for all agents, so there is nothing here to keep in sync.
That is also why the four files are only a dozen lines each — if you find yourself
editing a procedure here, it belongs in the vault instead.

## Install

Codex loads skills from `$HOME/.agents/skills` (personal, every repo) and from
`.agents/skills` in the working directory up to the repository root (per-repo). Personal
is what you want — the point is having `kb-search` while you debug *other* projects:

```bash
mkdir -p ~/.agents/skills
for s in kb-setup kb-save kb-search kb-loop; do
  mkdir -p ~/.agents/skills/$s
  curl -fsSL -o ~/.agents/skills/$s/SKILL.md \
    https://raw.githubusercontent.com/jasonw-dev/loopkb/main/integrations/codex/skills/$s/SKILL.md
done
```

Already have a vault clone? Every vault carries this directory, so copy from it instead:
`cp -R <vault>/integrations/codex/skills/kb-* ~/.agents/skills/`.

Then restart Codex if the skills do not appear. Invoke one by typing `$` in the composer
(or `/skills` to browse) — Codex also picks them up implicitly when a request matches a
skill's `description`. First time on this machine: `$kb-setup <vault repo URL>`.

## Where the vault path is stored

`kb-setup` writes the per-user wiring file `~/.claude/<vault-name>.md`, containing one
`KB_VAULT: <path>` line. The `~/.claude/` location is historical — the file is plain
text with no Claude Code semantics, and it is deliberately the *only* definition of that
contract, so a machine running both agents is wired once, not twice. Read it directly:
`@~/.claude/<vault-name>.md` is Claude Code import syntax and means nothing to Codex.

## Optional: a global AGENTS.md note

Codex reads `AGENTS.md` (or `AGENTS.override.md`) from `$CODEX_HOME` — `~/.codex` by
default — and then from the repo root down to your working directory, concatenating them.
Adding this to `~/.codex/AGENTS.md` points every session at the vault even in repos that
were never wired:

```md
## Knowledge base (loopkb)
The vault path is the `KB_VAULT:` line in `~/.claude/<vault-name>.md` — open that file
and read it; it is not imported for you. The kb-setup / kb-save / kb-search / kb-loop
procedures are defined in `<KB_VAULT>/.claude/skills/<name>/SKILL.md`; read the relevant
file before acting. Search the vault before re-deriving a fix, and save non-trivial
solutions back to it.
```

Per-repo wiring is the same block in the project's own `AGENTS.md` — see
"Wiring a project repo" in `.claude/skills/kb-search/SKILL.md`.

## Sandbox and approvals

Codex defaults to the `workspace-write` sandbox with `on-request` approvals, and
**network access is off by default**. Every skill here eventually touches the network —
`kb-setup` clones, `kb-save` pushes, `kb-loop` pulls, pushes and takes its lease on a
remote branch — so Codex will ask for approval at those points. Approve them, or lift the
restriction for a vault session (`--sandbox danger-full-access --ask-for-approval never`),
or allow the specific command prefixes in `~/.codex/config.toml`. A vault with no `origin`
remote is fully offline by design and never triggers any of this.

Two more consequences worth knowing:

- The vault is usually **outside** the workspace you opened Codex in, so writing to it
  needs an approval too, or the vault path added as a writable root in `config.toml`.
- `kb-loop` is best run with the vault itself as the workspace — that removes the
  out-of-workspace writes and leaves only the network approvals.

## Legacy: custom prompts

Codex's older custom-prompt mechanism (`~/.codex/prompts/<name>.md`, invoked as
`/prompts:<name>`) is **deprecated** in favour of skills, and its files must sit directly
in that folder — subdirectories are not scanned. If you are pinned to a build without
skills, the same pointer works as a prompt: copy the body (everything after the YAML
frontmatter) of any file in `skills/` into `~/.codex/prompts/kb-search.md` and call it
with `/prompts:kb-search`. Prefer skills wherever they are available.
