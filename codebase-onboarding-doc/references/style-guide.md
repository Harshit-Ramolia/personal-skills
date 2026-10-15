# Style guide

The reader is a smart new grad on their first week. They are capable and motivated, but they don't yet know any of the words. Write the way a patient senior engineer explains things at a whiteboard. Be plain and concrete, and never vague.

## Voice

- **Plain words, short sentences, one idea per paragraph.** If a sentence needs a second read, split it.
- **Define every term the first time it appears**, even ones that feel obvious inside the team. Bold the term where it is defined.
- **Plain version first, detail second.** For anything hard, give a one-paragraph plain explanation, then the precise mechanism with refs.
- **Use an analogy only when it genuinely carries the idea.** For example: "a factory with stations, a foreman and a rulebook" for an orchestrator. Map it to the real classes right away, so the analogy never replaces the facts.
- **No marketing tone, no emojis, no filler** ("robust", "seamless", "powerful", "simply", "just").
- **Exact numbers with refs:** defaults, timeouts, limits, counts. "Retries 3 times (`path:line`)" beats "retries a few times".
- **Absolute dates** ("2026-10-15", not "yesterday").

## The concept card

Use this shape for every significant concept:

```markdown
**What it is.** One line.
**Why it exists.** The problem it solves, or the incident that created it.
**Where in code.** `path/to/file.py:120-180` (the key symbol), plus related refs.
**Watch out.** The trap, the surprising default, the thing that breaks. Leave it out if there is none.
```

Don't force the labels on every small item. Tables and bullets are fine. But the order (what → why → where → watch out) should hold everywhere.

## Layout

- **Tables** for anything with more than three parallel items: flags, configs, edges, files, traps.
- **Small ASCII diagrams** for flows, state machines, call sequences and system maps. Keep them under 80 columns where possible, and label the arrows.
- **No walls of text.** Break a paragraph longer than about 6 lines.
- **Skimmable headings**: numbered parts and sub-parts (`## 7.`, `### 7.5`), so people can cite "see 7.5".

## Code references

- **Form:** `` `path/to/file.ext:LINE` `` or `` `path/to/file.ext:START-END` ``. Use repo-relative paths in backticks.
- **Shorthand:** `` `:START-END` `` refers to the last full ref *on the same line* of the doc. Use it only right after a full ref of the same file.
- **Branch refs:** `` `alias@path:LINE` ``, with the alias defined in the header.
- **Never invent a ref.** Every ref comes from a reader's notes or from a file you opened. If you can't back a claim, drop it or mark it **(unverified)**.
- **Point at the symbol, not the import.** Point at the definition or the line that shows the behaviour. A ref that is in range but points at the wrong code is still wrong.
- **Prefer ranges for blocks** (a function, a table), and single lines for constants and defaults.

## Cost and safety labels

Every command shown in the doc carries one label:

| Tag | Meaning |
|---|---|
| `[FREE]` | Runs locally, makes no paid API call, touches no shared system. |
| `[READS PROD]` | Reads from a shared or production system and changes nothing important. |
| `[COSTS MONEY]` | Spends paid API tokens or cloud compute. |
| `[TOUCHES PROD]` | Writes to a shared system: a deployment, a database, a bucket, a shared index, a customer-facing platform. |

Rename or trim the labels to fit the repo; a pure library might only need `[FREE]` and `[NETWORK]`. Define them in Part 0.

**Junior safety.** People copy-paste the first command they see.

- Show the safest variant first (dry run, canary, local, a single item).
- Use placeholders, not live names, for anything that targets a shared resource: `<your-app-name>`, `<your-test-project>`.
- Never present the production launch command as a casual example. If the doc must show it, put it in its own block with `[TOUCHES PROD]` and one line on what it touches.
- Name secrets, never show them. Write "set `API_KEY` (Modal secret `prod-keys`)", never a value or even a prefix.

## Honesty markers

- **(unverified):** anything you could not confirm in code at the pinned SHA.
- **(as of YYYY-MM-DD):** live state that will change, such as PR status, deploy state or ownership. Check it with the authoritative source (for example `gh`) before stating it.
- **Code beats docs.** When a README or comment disagrees with the code, the doc follows the code and records the drift in "Where the docs are stale".

## Before / after

(The examples use a made-up repo.)

Too vague:
> The scheduler manages the jobs and handles errors robustly.

Better:
> **The scheduler** (`acme/core/scheduler.py:58`) is the foreman. It runs one step, writes the result to `state.json`, then asks the **rulebook** (`NextStepRules`, `acme/core/rules.py:40`) what runs next. Steps never pick the next step themselves. They only report what happened (`acme/core/step_result.py:1-12`).

Too dense:
> In remote mode, grading is delegated to `grade_remote()` with `max_avg`/`min_ok` and the local threshold knobs are ignored.

Better:
> **Who decides "too easy"?** It depends on where the grading runs.
> - Grading runs locally: the `pass_threshold` setting decides (`acme/config.py:310-318`).
> - Grading runs remotely (`grader: remote`): two different settings decide instead, `max_avg` (default 0.5) and `min_ok` (default 1) (`acme/config.py:352-355`). `pass_threshold` is **ignored**, so changing it does nothing.
