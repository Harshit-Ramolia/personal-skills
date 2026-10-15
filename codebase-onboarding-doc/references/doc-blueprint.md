# Doc blueprint

The outline of the onboarding doc, part by part. Rename parts to fit the repo: "Life of one request" for a web service, "The pipeline phases" for a compiler. Drop a part that truly does not apply, such as infra for a pure library, and renumber.

These parts are always kept, whatever their names:

- 0 (how to read, plus the 10-minute version)
- 3 (repo tour)
- 4 (life of one unit)
- 7 (the brain)
- 15 (patterns)
- 16 (tests and CI)
- 17 (recipes)
- 18 (gotchas)
- 20 (first week)
- 21 (glossary)

## Length

| Tier | Target | Notes |
|---|---|---|
| small | 25k–45k chars | Parts 9–14 often collapse into one or two parts |
| medium | 50k–80k chars | |
| large | 80k–130k chars | Several deep-dive parts |

Every part must stay skimmable: tables, short paragraphs, small diagrams. Length comes from coverage, never from padding.

---

## Header (before Part 0)

```markdown
# <Repo> onboarding: the whole codebase, explained simply

> **Pinned to:** `<branch>` at `<sha>` (<date>).
> **Branches** (if any): <alias> = `<ref>` at `<sha>` (<one-line note>).
> Every `path:line` reference was checked at those SHAs. An independent reviewer fact-checked <N> claims against the code, and the errors it found are fixed here. A ref prefixed `<alias>@` lives on that branch (read it with `git show <ref>:<path>`). Anything not confirmed in code is marked **(unverified)**.
```

Fill in the real numbers after verification; the fixer and you update them.

## Part 0. How to read this doc

- **Who this is for:** one paragraph naming the reader and what they need to do (run, read, change, debug).
- **How each concept is written up:** What it is → Why it exists → Where in code → Watch out.
- **Cost labels:** a table of the labels used for commands (see the style guide).
- **Reading order:** which parts to read in one sitting and how long that takes, then "jump to what you're working on", pointing at the recipes and gotchas.
- **The 10-minute version** (a sub-section). It contains:
  - a blockquote, **"If you remember only five sentences:"**, with five numbered plain sentences that cover the whole system;
  - **what it makes or does**, in one paragraph;
  - **the main flow**, as one ASCII diagram, with a one-line note on any backward or loop edges;
  - **where it runs**, as 2–4 bullets (laptop, cloud, sandboxes...);
  - **how it fits with its neighbours** (the external systems it depends on or feeds);
  - **the five files to open first**: a table of #, file, why, with `path:line` of the key symbol.

## Part 1. The big picture

- **1.1 What the unit of work is.** What a "task", "request", "job" or "document" is in this repo. If it has an on-disk or wire format, show it as an annotated tree or schema, and give its invariants.
- **1.2 Who consumes the output.**
- **1.3 The systems involved.** A table of system → what it is → what this repo uses it for, plus one ASCII diagram of how they connect.

## Part 2. The words you need right now

10–15 terms in a table of **word** → plain meaning. Say that the full glossary is in Part 21.

## Part 3. Repo tour

Cover every top-level folder in a table of folder → what it holds → size (files, lines) → **read now / later / ignore**. Add a line on the dependency direction if there is one ("plugins import the engine, never the reverse").

## Part 4. Life of one <unit>, end to end

- **The big picture first.** One big ASCII diagram from trigger to final effect, naming the function at each hop.
- **Step by step.** Numbered steps, each with what happens, why, and `path:line`. Build it from the readers' `trace_steps`, in order.
- Use a safe command (dry run, canary, local) as the example trigger, never a live production launch.

## Part 5. The front door

- the commands or entry points;
- run modes (local, remote, detached, dry run...);
- routes (where you can start, and what you skip);
- the flags you will actually use, as a table of flag → default → what it does;
- canary or dry-run vs real;
- one-time setup;
- what happens after launch;
- recovery and replay flags.

## Part 6. The config

- the config schema classes;
- the top-level keys, grouped;
- inheritance or overrides;
- an **annotated walk through the canonical config file** (the one production uses), top to bottom;
- how config flows into the code.

## Part 7. The brain

- **7.1 Mental model:** an analogy, such as "a factory with a foreman and a rulebook", mapped to the real classes.
- **7.2 Where the order or graph of steps lives** (code or config) and why.
- **7.3 Contracts:** a table of each step's input → output.
- **7.4 Results and errors:** the result type, the error and feedback types.
- **7.5 The main loop:** an annotated pseudo-trace with line numbers.
- **7.6 Transitions:** legal edges and the routing table (error → where it goes → which budget).
- **7.7 Budgets, deadlines, terminal states.**
- **7.x Current-state questions** the user cares about, with refs.
- **7.y State and persistence:** the progress or state file, the workspace.
- **7.z Worker entry points** and resume or preemption behaviour.
- **Per-run wiring** (registries, dependency injection).

## Part 8. The main steps or components, one by one

For each one:

- a nickname in quotes ("SEED: come up with a good idea");
- its job, input → output, and its steps;
- the hooks or seams you can override;
- what makes it pass, fail or send feedback;
- its key knobs.

Go deeper on the hardest one or two.

## Part 9. The heavy lifters (agents, workers, external tools)

- what an adapter or harness is;
- a menu table;
- the call chain;
- exactly how the main external tool is launched (argv, env names);
- model or tool routing;
- default-on traps;
- guards, keys and cost accounting.

## Part 10. Runners and infrastructure

- what one worker or container is (function, timeout, CPU and memory, lifetime, volume);
- the image;
- secrets (names only);
- how checks and evals execute;
- **every timeout or limit layer**, in a table;
- watching a live run.

## Part 11. Extension points (plugins, handlers, benchmarks...)

- the base class and registry;
- hooks vs whole-component overrides;
- per-run wiring;
- a **minimal code example** of a new plugin;
- a tour of the existing plugins (one line each, with "do you need to care?").

## Part 12. Deep dive(s)

The focus subsystem or lane the user cares about. Cover:

- what it overrides;
- its sub-concepts (domains, profiles...);
- its subsystems in plain words;
- for branches or PRs: what each adds, how it runs, and its state, with live-checked PR status.

## Part 13. Integrations

- the external platform's object model and which IDs config needs;
- preflight checks;
- the call sequence for one unit (ASCII sequence diagram);
- each remote feature (review, eval, export...) in plain words;
- other hosts of this code, if any.

## Part 14. Data, dedup, telemetry and observability

- where data lives;
- dedup or corpus logic;
- what is emitted, and where to look (dashboards, collections, logs);
- the "never block on telemetry" style rules.

## Part 15. Coding patterns and house rules

A table of **#** → pattern → why → example `path:line`, with 10–15 rows. Then one **Style** paragraph on logging, naming, env-var prefixes and commit or branch conventions.

## Part 16. Tests and CI

- **16.1 Layout and fakes:** test count, conftest or fixtures behaviour, fakes and stubs, golden files, opt-in live tests and their env flags.
- **16.2 How to run (as CI does):** exact commands, each with a cost label and a rough duration.
- **16.3 CI jobs:** a table of workflow → when → what, and which jobs are required.
- **16.4 Testing rules** from the agent-instruction or contributing files.

## Part 17. How-to recipes

Numbered, step-by-step. Each recipe heading carries a cost label. Typical recipes:

- run the cheapest real thing;
- run the tests;
- inspect or debug a run;
- add a new <plugin / domain / endpoint / component>;
- add or swap a model, tool or dependency;
- change a prompt or config safely;
- debug a failed <unit>.

## Part 18. Gotchas and traps

A numbered table of **trap** (with `path:line`) → **what to do**, with 10–25 rows. These are the things that cost real people hours: default-on flags, silent fallbacks, shared deployments, gitignored folders, retry budgets that interact, timeouts that must be ordered.

## Part 19. If you come from <background> (optional)

Only include this part if the args include a `background`. Use a table of their concept → this repo's equivalent → the key difference. Use only the facts given in `background`.

## Part 20. Your first week

- **20.1 Reading order:** a table of day → what to read (files with line ranges) → why. End the week with "run the tests" and one safe real run.
- **20.2 File index:** the ~20–40 files that matter, one line each.

## Part 21. Full glossary

Alphabetical, merged from all readers. Each entry is the term → a plain meaning, plus a ref when useful.

## Part 22. Where the docs are stale

A table of **doc says** (with `path:line`) → **code says** (with `path:line`), built from the readers' `doc_drift`. Start with: "Trust the code. Known drift at `<sha>`:".
