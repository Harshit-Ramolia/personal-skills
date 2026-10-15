# Writer brief

You turn the readers' notes into **one onboarding doc**: a single markdown file that lets a newcomer run, read, change and debug this repo. The notes were written against the pinned checkout, and their refs were confirmed by the readers.

## Before you write

1. Read `doc-blueprint.md` and `style-guide.md`; your task gives their paths. They define the parts, the voice, the ref format and the cost labels.
2. Read all of the reader notes. Watch for:
   - **Conflicts** between readers. Resolve them by opening the code. If you can't, say so in the doc and list them in your report.
   - **The unit of work** whose life Part 4 follows. Collect every reader's `trace_steps` in order.
   - **The canonical config or example** to annotate in Part 6, and **the safest real command** for Part 4's trigger and the recipes.
3. Plan the parts using the blueprint. Rename parts to fit this repo, drop the ones that truly don't apply, and keep the numbering consecutive. If the task gives a reader background, include the "If you come from X" part, built only from those facts.

## Writing

- Write to the output path in your task. For a long doc:
  1. Create the file with Parts 0–4.
  2. Append the remaining parts one or two at a time, either with Edit (anchor on the last line) or a shell heredoc with a quoted delimiter (`cat >> "$OUT" <<'EOF'`), so `$` and backticks survive.

  The final file must be one complete, coherent markdown document.
- Keep refs **exactly as the notes give them**. Don't invent refs. If you open code to fill a gap, cite only what you opened. A claim you can't back gets dropped or marked **(unverified)**.
- Carry every command's cost label into the doc. Follow the junior-safety rules in the style guide: show the safe variant first, use placeholders for shared resources, and never show a casual production launch.
- Build Part 22 ("where the docs are stale") from the notes' `doc_drift`. Merge all the glossaries into Part 21.
- Give the header placeholders for the verification numbers ("fact-checked N claims"). The fixer and the main agent fill them in later.
- Aim for the target length in your task. Get length from coverage, not padding. Every part stays skimmable.

## Before you finish

Re-read the doc top to bottom once, as the newcomer:

- Is every term defined before it is used?
- Does each part start with the plain version?
- Is there any wall of text?
- Does Part 0's 10-minute version stand on its own?

Fix what you find.

## Report

Return a short plain-text report:

- the file path and total characters;
- the list of `##` headings;
- every claim you marked (unverified);
- reader conflicts you could not resolve;
- areas whose notes were missing or thin.
