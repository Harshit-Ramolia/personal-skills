# Planning the reader areas

Each reader owns one area of the repo and reads it deeply. The writer only knows what the readers found, so this split decides how good the doc can be.

## Contents

1. How many readers
2. The area menu
3. Adapting to the repo type
4. Writing good deliverables
5. The args schema
6. Worked example

---

## 1. How many readers

Use the tier from `repo_scout.py`. It counts code lines and excludes vendored and generated files.

| Tier | Code lines | Readers | Target doc length | Claims the fact-checker tests |
|---|---|---|---|---|
| small | < 15k | 3–4 | 25k–45k chars | 30 |
| medium | 15k–150k | 5–6 | 50k–80k chars | 45 |
| large | > 150k | 7–8 | 80k–130k chars | 60 |

Total agents = readers + 4 (writer, two critics, fixer). If the session has a workflow-size guideline, fit the reader count to it. Fewer, broader areas beat skipping the critics.

An area should be something one reader can actually read: as a rough guide, under about 40k lines of code. For a huge file (a 10k-line runner, say), don't ask for the whole file. Ask for its skeleton, its main method and its seams.

## 2. The area menu

Every plan has the first two areas and the last one. Fill the middle with the repo's real subsystems.

| Area | Always? | Covers | Feeds doc parts |
|---|---|---|---|
| **front_door** | yes | How anything starts: CLI commands and flags with defaults, HTTP routes or the app entry point, the config loading and schema, run modes, one-time setup | 4, 5, 6 |
| **brain** | yes | The core control flow: orchestrator, main loop, state machine, request pipeline, scheduler. Also: the data contracts between steps, routing, retries, error handling, persisted state, concurrency, and the entry points for workers | 4, 7 |
| *component areas* | as needed | The main steps, handlers, services, modules or packages, one group per reader | 8, 11, 12 |
| *agents / workers* | if present | Whatever does the heavy lifting outside the main process: LLM agents and model routing, job workers, subprocess tools, external CLIs | 9 |
| *infra / runners* | if present | Where code physically runs: containers, cloud functions, queues, images, deploy, secrets (names only), timeouts and limits, observing a live run | 10 |
| *integrations* | if present | External services and platforms: their object model, the sequence of calls, auth, failure handling | 13 |
| *data / storage / observability* | if present | Databases, schemas, migrations, caches, files, logs, metrics, traces | 14 |
| *focus / branch lanes* | if asked | The subsystem, branch or PR the user cares about most. Diff it against the default branch and explain what it adds and its state | 12 |
| **conventions** | yes | Coding patterns with real examples, naming, tests (layout, fakes, how CI runs them), CI jobs, lint and type tooling, agent-instruction files (CLAUDE.md/AGENTS.md), commit and PR conventions, what a newcomer can ignore | 15, 16, 17 |

Merge small areas and split big ones. Infra plus integrations, or agents plus infra, are common merges for medium repos.

## 3. Adapting to the repo type

The "unit of work" whose life Part 4 follows changes with the repo:

| Repo type | Unit of work | Brain usually is | Notes |
|---|---|---|---|
| Pipeline / batch system | one task, job or record | orchestrator plus state machine | Infra and workers matter a lot |
| Web service / API | one request | the router and middleware chain → handler → service → DB | Add auth, migrations, background jobs |
| Frontend app | one user action, or one page load | the router, state store, data fetching | Add the build and dev server, and component conventions |
| Library / SDK | one public API call | the public API surface → internals | Infra is usually skipped. Add versioning and release, plus the compatibility rules |
| CLI tool | one command invocation | the command dispatch | Front door and brain may merge |
| Compiler / interpreter | one input file | the phases: parse → analyze → transform → emit | Each phase is a component area |
| Monorepo | depends on the user's focus | ask, or pick the package the user works in | Give a short map of all packages, and depth only for the focus |
| ML / training repo | one experiment run | the training loop / pipeline | Add data, configs, checkpoints, eval |

## 4. Writing good deliverables

A deliverable is a question about this repo. Answering it means opening code. Good deliverables:

- **name real things:** files, classes, flags, config keys, functions you saw while scouting;
- **ask for the mechanism**, not a summary. "Function by function, what happens between typing `<cmd>` and the first worker starting, with refs" beats "explain the CLI";
- **ask for defaults and numbers:** flag defaults, timeouts, retry counts, limits;
- **ask for traps:** "is X on by default? what breaks if Y?";
- **ask the "current state" questions the user cares about:** "does path A still have the bug the old notes describe? report what main does now";
- **ask for a diagram** when there is a flow;
- end with **commands** a newcomer needs, each labeled `FREE / READS PROD / COSTS MONEY / TOUCHES PROD`.

Aim for 5–9 deliverables per area. Put the files list first: folders, key files, docs and tests that belong to the area.

## 5. The args schema

```json
{
  "skill_dir": "/abs/path/to/codebase-onboarding-doc",
  "repo": "/abs/path/to/pinned/checkout",
  "repo_name": "acme-pipeline",
  "purpose": "one line: what the repo does",
  "sha": "1a2b3c4d5",
  "sha_date": "2026-10-15",
  "out": "/abs/path/acme-pipeline-onboarding-2026-10-15.md",
  "scratch": "/abs/path/to/scratchpad/onboard",
  "scout_path": "/abs/path/to/scratchpad/onboard/scout.json",
  "title": "acme-pipeline onboarding: the whole codebase, explained simply",
  "reader_profile": "a junior engineer joining the platform team",
  "background": "optional: verified facts about the reader's previous codebase, for the 'If you come from X' part",
  "focus": "optional: the subsystem / branch the user cares most about",
  "tier": "medium",
  "target_chars": "50,000–80,000",
  "claims_to_check": 45,
  "today": "2026-10-16",
  "branches": [
    { "alias": "feat", "ref": "origin/alice/new-exporter", "sha": "9f8e7d6c5", "git_dir": "/abs/path/to/full/clone", "note": "PR #123, open" }
  ],
  "extra_sources": [
    { "path": "/abs/path/notes.md", "note": "earlier research written against an older SHA; re-verify" }
  ],
  "constraints": [
    "do not run `acme run` or anything under deploy/; it launches cloud workers"
  ],
  "areas": [
    {
      "key": "front_door",
      "title": "Front door: how a run starts and how it is configured",
      "files": ["acme/cli.py", "acme/config/", "configs/", "README.md"],
      "deliver": [
        "Function by function, what happens between `acme run configs/x.yaml` and workers starting (refs).",
        "Every flag a newcomer needs, one line each, with its default.",
        "An annotated walk through configs/prod.yaml, top to bottom."
      ]
    }
  ]
}
```

Required keys: `skill_dir`, `repo`, `repo_name`, `sha`, `out`, `scratch`, `areas` (non-empty). Every other key is optional and improves the result.

`scratch` must be a directory the agents may write to: your scratchpad, or a folder inside it. Put the output doc where the user wants it. Agents write only the doc and scratch files.

## 6. Worked example (a made-up pipeline repo, large tier)

`acme-pipeline` is a Python system that turns input records into graded artifacts. The scout shows:

| Folder | Size |
|---|---|
| `acme/` | engine, 180k lines |
| `plugins/` | per-product plugins, 120k lines |
| `deploy/` | cloud runner |
| `configs/` | 300 YAML jobs |
| `tests/` | 600 files |

The README says "four stages", but the code has six. The user is joining the team that owns `plugins/exporter/` and wants to understand PR #123.

The plan:

| key | title | deliverables (abridged) |
|---|---|---|
| front_door | How a run starts and is configured | launch sequence with refs; flags plus defaults; annotated `configs/prod.yaml`; dry-run vs real; the cheapest safe run |
| brain | Contracts, orchestrator, state machine | stage order and where it is fixed; how each stage's input is built; the transition table and every backward edge; retry budgets; the state file's shape and when it is written; worker entry points; an ASCII state machine |
| stages | The six stages one by one | for each stage: job, input → output, steps, hooks, pass/fail/feedback rules, key config knobs; go deep on the two hardest stages |
| workers | Agents and external tools | what runs the heavy lifting; the call chain from stage to process; launch flags and env (names only); model or tool routing; the default-on flag that surprises people |
| infra | Where it runs | local vs cloud vs detached; what one worker is (timeout, CPU, lifetime); the image; secrets (names); every timeout layer; how to watch a run |
| exporter | The exporter plugin and PR #123 | how a plugin plugs in (with a minimal example); what the exporter overrides; how to add a new plugin step by step; what PR #123 adds (`git diff main...feat --stat`) and its live state |
| integrations | Downstream platform, storage, telemetry | the platform object model; the call sequence for one task (as a diagram); dedup and corpus; where metrics and logs go |
| conventions | Patterns, tests, CI, house rules | 10–15 patterns with refs; how CI runs the tests (exact commands); the CI jobs table; agent-instruction rules; commit and PR style; what to ignore |

That makes 8 readers plus 4 other agents, 12 in total. If the size guideline is tighter, merge `infra` into `workers` and `integrations` into `conventions`.
