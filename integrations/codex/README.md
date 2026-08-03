# loopkb for Codex CLI

**There is nothing to install.** Every vault carries `.agents/skills/{kb-setup,kb-save,
kb-search,kb-loop}/SKILL.md`, and [Codex CLI](https://developers.openai.com/codex/) loads
`.agents/skills` from your working directory up to the repository root. So the four
skills are live the moment you open a vault — or any repo that carries copies of them —
with no setup step at all. Type `$` in the composer to invoke one (`/skills` to browse);
Codex also picks them up implicitly when a request matches a skill's `description`.

Those four files are **pointers, not copies**: each one resolves the vault — step 0 is
"if this repo has `_meta/loop.md`, this repo IS the vault" — then reads
`<KB_VAULT>/.claude/skills/<name>/SKILL.md` and follows it. The vault's `.claude/skills/`
files stay the single source of truth for all agents, so there is nothing here to keep in
sync. That is why the four files are only a dozen lines each — if you find yourself
editing a procedure in `.agents/skills/`, it belongs in `.claude/skills/` instead.

## Optional: install them globally

Codex also loads skills from `$HOME/.agents/skills`, which applies in *every* repo. That
is worth doing for two reasons: using `kb-search` and `kb-save` while you work in repos
that carry no copies of these files, and **bootstrapping** — `$kb-setup <vault URL>` has
to come from somewhere, and before your first clone there is no vault to load it from.
Copy them out of any vault clone:

```bash
mkdir -p ~/.agents/skills
cp -R <vault>/.agents/skills/kb-* ~/.agents/skills/
```

No vault clone yet? Fetch the framework copies, then `$kb-setup <vault repo URL>`:

```bash
mkdir -p ~/.agents/skills
for s in kb-setup kb-save kb-search kb-loop; do
  mkdir -p ~/.agents/skills/$s
  curl -fsSL -o ~/.agents/skills/$s/SKILL.md \
    https://raw.githubusercontent.com/jasonw-dev/loopkb/main/.agents/skills/$s/SKILL.md
done
```

Restart Codex if the skills do not appear. A global copy can go stale while the vault's
own copy cannot — refresh it from a vault clone whenever the framework changes.

## Where the vault path is stored

`kb-setup` writes the per-user wiring file `~/.claude/<vault-name>.md`, containing one
`KB_VAULT: <path>` line. The `~/.claude/` location is historical — the file is plain
text with no Claude Code semantics, and it is deliberately the *only* definition of that
contract, so a machine running both agents is wired once, not twice. Read it directly:
`@~/.claude/<vault-name>.md` is Claude Code import syntax and means nothing to Codex.
Inside the vault itself you never need this file: the skills' step 0 answers "which
vault" before the question is asked.

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

One more consequence worth knowing: run from *another* repo, the vault is outside the
workspace you opened Codex in, so writing to it needs an approval too, or the vault path
added as a writable root in `config.toml`. Opening the vault itself as the workspace —
the zero-install case above, and how `kb-loop` is meant to be run — removes those
out-of-workspace writes and leaves only the network approvals.

## Shipping your own team skills the same way

An instance is free to add its own skills alongside the kb ones. The arrangement that
serves both agent ecosystems at once is a pair of byte-identical thin pointers —
`.claude/skills/<name>/SKILL.md` and `.agents/skills/<name>/SKILL.md` — each pointing at
the instance's own canonical guide in the vault. Claude Code reads the first, Codex the
second, and every clone gets them with no install.

## Legacy: custom prompts

Codex's older custom-prompt mechanism (`~/.codex/prompts/<name>.md`, invoked as
`/prompts:<name>`) is **deprecated** in favour of skills, and its files must sit directly
in that folder — subdirectories are not scanned. If you are pinned to a build without
skills, the same pointer works as a prompt: copy the body (everything after the YAML
frontmatter) of any file in `.agents/skills/` into `~/.codex/prompts/kb-search.md` and
call it with `/prompts:kb-search`. Prefer skills wherever they are available.
