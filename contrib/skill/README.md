# Agent Skill — the recognition map, in a channel a model can read (task 200)

[`SKILL.md`](SKILL.md) is **generated** by [`scripts/gen_skill.py`](../../scripts/gen_skill.py) from
the tools the server registers and from the `which_tool` recognition map. Task 081 established that
an MCP client shows a model only **tools**, never prompts — so `which_tool`, the one artifact that
maps a question onto a tool across the whole surface, lives where no model can read it. An Agent
Skill is a file **you** install into **your** agent; it loads on demand and costs nothing in a
session that never triggers it.

## Install by hand

code-atlas does not write to your agent's settings — not here, not anywhere (tasks 036, 099).

1. Copy `SKILL.md` into your agent's skills directory as its own folder, e.g.
   `~/.claude/skills/code-atlas/SKILL.md`.
2. Restart the agent (or reload skills).

## Regenerate

```bash
python scripts/gen_skill.py --write
```

`tests/test_skill_drift.py` compares the committed bytes to the generator's output, so an edit by
hand — on either side — is a red test rather than a quiet disagreement.
