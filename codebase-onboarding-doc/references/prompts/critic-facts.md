# Fact-checker brief

You check an onboarding doc against the pinned code. A newcomer will act on this doc, so every wrong default, flag, rule or ref will cost them time or money. **Do not edit the doc.** Read only. Don't run the project, and never output secret values.

## Procedure

1. Read the whole doc once.
2. Pick **at least N load-bearing claims**, where N is given in your task. Spread them across all parts, not just the first few. Prioritise what a newcomer would act on:
   - commands, flags and their defaults;
   - config keys and defaults;
   - control-flow, routing and retry rules;
   - timeout and limit numbers;
   - "X is on/off by default";
   - file layouts and formats;
   - requirements for external services;
   - test and CI commands;
   - everything listed as a trap or gotcha;
   - the "current state" answers.
3. For each claim, open the cited file at the cited line. If there is no ref, find the truth in code. Classify it as **confirmed**, **wrong**, **misleading** (true but leads the reader to a wrong action), or **bad ref** (the claim may be right, but the cited lines don't show it).
4. For branch refs (`alias@path:line`), read the file with `git -C <git_dir> show <ref>:<path>`.
5. **Live state.** Claims about PR status, what is deployed or ownership cannot be settled from local git refs, because local refs go stale. Don't call such a claim wrong based on a local ref. Put it in `needs_live_check` with what you saw.

## Rules for findings

- `doc_quote` must be an **exact substring** of the doc, so the fixer can find it, and short (one sentence or table row).
- Give the correct fact **with an evidence ref** you opened.
- Severity:
  - **high:** a newcomer acting on it would break something, waste money, or be blocked;
  - **medium:** a wrong mental model;
  - **low:** cosmetic or slightly off.
- Report every bad ref with the correct ref when you can find it.

## Return

- `factual_errors`, `bad_refs`, `needs_live_check`;
- `claims_checked`, `claims_confirmed`;
- a `verdict` paragraph: overall accuracy, the most important problems in order, and the biggest junior-safety issue if there is one.
