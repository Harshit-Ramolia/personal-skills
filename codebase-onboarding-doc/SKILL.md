---
name: codebase-onboarding-doc
description: Generate a complete, junior-friendly, end-to-end onboarding doc for any code repository. It covers the big picture, the life of one request/task/job from trigger to result, entry points and config, the core control flow (orchestrator, runners, state machine, main loop), every major subsystem, where code physically runs, extension points, coding patterns, tests and CI, step-by-step recipes, gotchas, a first-week reading plan and a glossary. Every claim is tied to a path:line ref pinned to one commit, fact-checked by an independent critic and range-checked by script. Use this whenever someone wants to be onboarded to a repo or asks to "explain this codebase end to end", "dumb down how this repo works", "walk me through their code as a junior engineer", "write an onboarding / architecture guide", or is taking over, joining or ramping up on an unfamiliar codebase, even if they never say "doc". Not for explaining one function or file, reviewing a diff, or writing API reference docs.
---

# Codebase onboarding doc

You produce one long markdown file that lets a new engineer run, read, change and debug an unfamiliar repo. It reads like a patient senior engineer explaining the codebase to a smart new grad. The language is plain, but every claim is exact enough to act on, and every claim points at the line of code that proves it.

Earlier versions of this doc were judged to "cover the repo exactly the way I want". That came from four things, so protect them:

1. **Dumbed down without being wrong.** Each concept gets a plain version first, then the detail.
2. **End to end.** The doc follows one unit of work from the moment it is triggered to its final effect, and names the code at each step.
3. **The machinery is fully explained:** orchestrator, runners, workers, infrastructure, plus the coding patterns and house rules.
4. **It is trustworthy.** The doc is pinned to a commit and every ref is checked. A critic and a fixer catch errors, and anything uncertain is marked **(unverified)**.

## The process at a glance

```
1. Scope    (you, inline)       repo, reader, focus, output path; pin a commit
2. Scout    (script)            scripts/repo_scout.py → inventory + size tier
3. Plan     (you, inline)       split the repo into 3–8 reader areas → args JSON
4. Run      (Workflow)          Read → Write → Check (2 critics) → Fix
5. Verify   (you + scripts)     refcheck.py, doc_lint.py, spot-checks, live-state checks
6. Deliver  (you)               path, numbers, corrections, unverified items
```

Invoking this skill is the user's opt-in to the multi-agent workflow. That means readers, one writer, two critics and one fixer: about 7–12 agents in total. Tell the user the scale in one line before you launch. As a reference point, a large repo (about 3.5k tracked files) took about 70 minutes end to end:

| Phase | Time |
|---|---|
| Readers | ~20 min |
| Writer | ~15 min |
| Critic | ~30 min |
| Your own fixes | the rest |

Small repos are much faster.

## Ground rules (and why)

- **Read only.** Don't run the project's pipelines, servers, deploys, migrations or anything that costs money or touches shared systems. Reading code is enough. A doc about a system is no reason to change that system.
- **Pin one commit.** Every ref must be checked against one fixed SHA, or the line numbers drift while the agents work. Make a detached copy in your scratchpad, for example:
  - `git -C <repo> worktree add --detach <scratch>/<name>_head <sha>`
  - or a local `git clone` followed by `git checkout --detach <sha>`

  If the user wants the latest upstream, run `git fetch` first and pin `origin/<default>`. Otherwise pin local `HEAD`, and say which you pinned. Uncommitted changes are not covered; say so if any exist.
- **Trust code over docs.** READMEs and docs/ go stale. Disagreements are useful to a newcomer, so they get their own part ("where the docs are stale").
- **Never copy secrets.** Name the env var or secret instead. `doc_lint.py` scans the doc for leaks before you hand it over.
- **Junior safety.** A newcomer will copy-paste the first command they see. Never present a command that deploys, mutates shared state or spends real money without three things:
  - its cost label;
  - placeholders in place of live names;
  - the safe or cheap variant shown first.

## Step 1: Scope

Settle these from the conversation, memory and the repo. Ask only when the repo itself is ambiguous; everything else has a default.

| Input | Default |
|---|---|
| Repo | A local path, a GitHub URL (clone it read-only into the scratchpad) or a name you can resolve |
| Reader profile | "A smart junior engineer new to this repo" |
| Reader background | None. If the user says where the reader comes from (another team, codebase or stack), you get an optional "If you come from X" mapping part. Pass only facts you know (from the user, memory or docs), never guesses. |
| Focus | The whole repo. A named subsystem, branch or PR gets a deeper part of its own. |
| Branches | None. For a branch or PR that matters, record an alias, the ref, its SHA and the git dir. Refs on it are written `alias@path:line`. Check a PR's live head with `gh pr view <n> --json headRefName,headRefOid,state`, not a local `pr/<n>` ref, because local refs go stale. |
| Output path | `<cwd>/<repo-name>-onboarding-<YYYY-MM-DD>.md` |

## Step 2: Scout

```bash
python3 <skill_dir>/scripts/repo_scout.py <pinned_checkout> --out <scratch>/scout.json
```

It prints a short summary and writes JSON with:

- top-level folders with file counts and lines of code;
- languages, the largest files, and entry points (CLI scripts, package scripts, `main` files, Makefile targets, Dockerfiles, framework markers);
- CI workflows, test folders, docs and agent-instruction files;
- recent activity, a suggested **size tier**, a reader count, a target length and a claim count.

Then read README, CLAUDE.md/AGENTS.md and CONTRIBUTING (if present). Skim the main entry points until you can say in one sentence what the repo does and what its "unit of work" is: request, job, task, document, build, render…

## Step 3: Plan the reader areas

Read `references/area-planning.md`. Split the repo into 3–8 areas, each owned by one reader. It always includes three areas:

- **front door** (how things start, config);
- **brain** (core control flow);
- **conventions** (patterns, tests, CI, tooling).

The remaining areas follow the repo's real subsystems. Every important top-level folder lands in an area or is consciously marked "ignore". For each area, write repo-specific **deliverables** (numbered questions the reader must answer). Specific deliverables are the single biggest lever on doc quality, because a reader told "explain the orchestrator" writes much less useful notes than one told "draw the state machine; list every legal backward edge with its ref; say what happens on a timeout".

Write the workflow args to `<scratch>/onboarding-args.json`. The schema is in `references/area-planning.md`, and its required keys are:

- `skill_dir`, `repo`, `repo_name`, `sha`, `out`, `scratch`, `areas`.

## Step 4: Run the workflow

```
Workflow({ scriptPath: "<skill_dir>/assets/onboarding_workflow.js", args: <the args object> })
```

Pass `args` as a JSON object, not a string. The phases:

1. **Read.** One reader per area returns structured notes: walkthrough, refs, concepts, trace steps, patterns, gotchas, labelled commands and doc drift. Readers follow `references/prompts/reader.md`.
2. **Write.** One writer turns the notes into the doc, using `references/doc-blueprint.md` and `references/style-guide.md`.
3. **Check.** Two critics run in parallel:
   - a fact-checker that tests N load-bearing claims against the code;
   - a junior-reader, coverage and safety critic.
4. **Fix.** One fixer re-verifies every finding against the code before applying it. Critics are sometimes wrong; for example, one trusted a stale local branch ref. The fixer applies only confirmed findings and returns a ledger of what it applied, what it rejected, and what needs you.

If the Workflow tool is not available, run the same phases with the Agent tool:

- Spawn the readers in parallel in one message.
- Then run the writer, then the two critics in parallel, then the fixer.
- Give each agent the same prompt shape the script builds: "read `<brief>`; RUN CONTEXT; your area/task".
- Read `assets/onboarding_workflow.js` for the exact prompt text and output schemas.

## Step 5: Verify it yourself

The workflow's own checks are good, but you sign off on the doc, so run these:

```bash
python3 <skill_dir>/scripts/refcheck.py --doc <out> --repo <pinned_checkout> [--alias name=<git_dir>@<ref> ...]
python3 <skill_dir>/scripts/refcheck.py --doc <out> --repo <pinned_checkout> --sample 15   # prints cited code for spot-checks
python3 <skill_dir>/scripts/doc_lint.py <out>
```

1. **Bad refs.** Fix every BAD ref (line out of range), MISSING ref (no such file) and AMBIGUOUS ref (short path that matches several files). Open the file, find the right line, and edit the doc. Re-run until clean.
2. **Spot-check.** In the `--sample` output, confirm that the cited lines really show what the sentence claims. A ref can be in range and still point at the wrong thing.
3. **Fixer ledger.** Read it, and re-check 3–5 of the highest-severity applied fixes in the doc.
4. **Live-state claims.** Re-check every claim about live state (PR status, what is deployed, who owns what) with the authoritative source, such as `gh` or the service's API, not local git refs. Then update the doc.
5. **Lint.** Clear every finding from `doc_lint.py`. Zero secret hits is mandatory. If the doc has more than a handful of `(unverified)` marks, try to resolve the important ones.
6. **Clean up.** Remove a temporary worktree with `git -C <repo> worktree remove <path>` once you no longer need it.

## Step 6: Deliver

Reply briefly with:

- the doc path, the pinned SHA, its size and reading time (from `doc_lint.py`), and a one-line outline;
- how it was verified (claims checked, refs range-checked, fixes applied or rejected);
- the corrections a newcomer would most likely get wrong without the doc;
- what is still (unverified).

Offer in one line to publish it as a shareable page.

## Refreshing an existing doc

When the repo has moved on:

1. Pin the new SHA.
2. Run `git diff --stat <old>..<new>` to see which areas changed.
3. Run `refcheck.py` against the new checkout.
4. Re-run readers only for the changed areas, with the old doc as an extra source.
5. Patch the doc and update the pinned header.

## Reference files

| File | Read it when |
|---|---|
| `references/area-planning.md` | Step 3: how to split a repo, the area menu, adapting to the repo type, the args schema, a worked example |
| `references/doc-blueprint.md` | The writer reads it; you read it if you write or patch parts yourself. Part-by-part outline and length tiers. |
| `references/style-guide.md` | The writer, fixer and you: voice, concept cards, refs, cost labels, safety |
| `references/prompts/*.md` | The briefs for readers, writer, critics and fixer. The workflow points each agent at its brief. |
| `assets/onboarding_workflow.js` | The workflow script (also the source of the prompts and schemas for the fallback path) |
| `scripts/repo_scout.py`, `scripts/refcheck.py`, `scripts/doc_lint.py` | Inventory, ref checking, and the secret, reading-time and structure lint. Standard library only; read-only. |
