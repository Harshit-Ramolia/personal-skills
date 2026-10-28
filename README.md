# personal-skills

Skills for [Claude Code](https://claude.com/claude-code).

| Skill | What it does |
|---|---|
| [`codebase-onboarding-doc`](codebase-onboarding-doc/SKILL.md) | Writes an end-to-end onboarding doc for any repo, pitched at a junior engineer. It is pinned to one commit, and every claim cites a `path:line` ref. A multi-agent workflow produces it (readers → writer → fact-check and junior-reader critics → verified fixes), and scripts then range-check every ref and scan for secrets. |
| [`communication-style`](communication-style/SKILL.md) | Sets how Claude talks to you in every session. It gives the direct answer first in simple English with minimal words, pitches it at a junior engineer, and uses flows, tables and trees for quick understanding. |

## Install

Copy or symlink a skill folder into your personal skills directory:

```bash
git clone https://github.com/Harshit-Ramolia/personal-skills.git
ln -s "$PWD/personal-skills/codebase-onboarding-doc" ~/.claude/skills/codebase-onboarding-doc
```

Claude Code picks it up in the next session. Then ask something like "onboard me to this repo end to end" or "write a junior-friendly guide to how `<repo>` works".

`codebase-onboarding-doc` uses the Workflow tool when it is available. Otherwise it falls back to the Agent tool. Its scripts need Python 3.9+ (3.11+ also parses `pyproject.toml`) and `git`, and nothing else.

### Make `communication-style` always on

A skill only loads when Claude decides it is relevant. To apply this one to every reply, also add this block to `~/.claude/CLAUDE.md`:

```markdown
<communication-style>

# Communication style
Follow the `communication-style` skill (~/.claude/skills/communication-style/SKILL.md) in every reply, in every session. Core rules:
- Answer first. No preamble.
- Use simple English and minimal words, and explain it the way you would to a junior engineer.
- Use flows, tables or trees whenever they make it faster to understand.
- Stay on point. No filler and no recap.

</communication-style>
```
