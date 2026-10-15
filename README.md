# personal-skills

Skills for [Claude Code](https://claude.com/claude-code).

| Skill | What it does |
|---|---|
| [`codebase-onboarding-doc`](codebase-onboarding-doc/SKILL.md) | Writes an end-to-end onboarding doc for any repo, pitched at a junior engineer. It is pinned to one commit, and every claim cites a `path:line` ref. A multi-agent workflow produces it (readers → writer → fact-check and junior-reader critics → verified fixes), and scripts then range-check every ref and scan for secrets. |

## Install

Copy or symlink a skill folder into your personal skills directory:

```bash
git clone https://github.com/Harshit-Ramolia/personal-skills.git
ln -s "$PWD/personal-skills/codebase-onboarding-doc" ~/.claude/skills/codebase-onboarding-doc
```

Claude Code picks it up in the next session. Then ask something like "onboard me to this repo end to end" or "write a junior-friendly guide to how `<repo>` works".

`codebase-onboarding-doc` uses the Workflow tool when it is available. Otherwise it falls back to the Agent tool. Its scripts need Python 3.9+ (3.11+ also parses `pyproject.toml`) and `git`, and nothing else.
