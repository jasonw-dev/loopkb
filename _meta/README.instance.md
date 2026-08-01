<!-- INSTANCE README STUB — copy this over README.md when you instantiate the
     template, then replace every <angle-bracket placeholder> and delete this comment.
     Keep the "Joining this vault" block: once the framework README is gone, it is the
     only place a new teammate learns how to get in. -->

# <Vault name> — team knowledge base built on [loopkb](https://github.com/jasonw-dev/loopkb)

<One paragraph: what knowledge belongs here and who it is for — e.g. "Cross-repo
engineering knowledge for the platform group: build and CI failures, environment setup,
release procedures, and the decisions behind them. Notes are Markdown; an AI agent files
and maintains them; git is the sync, review and undo layer.">

**[▶ Visual intro（視覺化導覽）](https://claude.ai/code/artifact/9052bb5e-eb3b-4d83-84d1-96aa9276dfcf)** — a 3-minute illustrated tour of how the loop works.

## Joining this vault (once per machine)

You never run `git clone` yourself: the plugin machinery fetches the skills, and
`kb-setup` clones the vault for you.

In Claude Code, install the plugin:

```
/plugin marketplace add jasonw-dev/loopkb
/plugin install loopkb@loopkb
```

then say one sentence:

```
kb-setup <vault URL>
```

That clones the vault, validates it, and wires this machine. Nothing else to do.

## Daily use

Three actions: drop anything into `_inbox/`, say `kb-save` in a conversation right after
solving something, run `kb-loop` here about once a week. Details, governance and the
correction workflow: [GETTING-STARTED.md](GETTING-STARTED.md).

What the last loop run did: [`_meta/digest.md`](_meta/digest.md).
