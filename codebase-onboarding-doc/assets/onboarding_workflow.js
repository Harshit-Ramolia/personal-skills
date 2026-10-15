export const meta = {
  name: 'codebase-onboarding-doc',
  description: 'Read a pinned repo area by area, write a junior-friendly onboarding doc, fact-check it, and apply only verified fixes',
  whenToUse: 'Run from the codebase-onboarding-doc skill after scouting the repo and planning reader areas',
  phases: [
    { title: 'Read', detail: 'one read-only reader per code area' },
    { title: 'Write', detail: 'one writer turns the notes into the doc' },
    { title: 'Check', detail: 'fact-checker and junior-reader critics in parallel' },
    { title: 'Fix', detail: 'verify every finding against code, apply only confirmed ones' },
  ],
}

// ---- args ---------------------------------------------------------------
const A = args || {}
const REQUIRED = ['skill_dir', 'repo', 'repo_name', 'sha', 'out', 'scratch', 'areas']
const missingArgs = REQUIRED.filter(k => A[k] === undefined || A[k] === null || A[k] === '')
if (missingArgs.length) throw new Error(`missing args: ${missingArgs.join(', ')}`)
if (!Array.isArray(A.areas) || A.areas.length === 0) throw new Error('args.areas must be a non-empty array')

const REF_DIR = `${A.skill_dir}/references`
const BRIEFS = `${REF_DIR}/prompts`
const list = (xs, fmt) => (Array.isArray(xs) && xs.length ? xs.map(fmt).join('\n') : '- none')
const asLines = v => (Array.isArray(v) ? v : v ? [String(v)] : [])

const CTX = `
=== RUN CONTEXT ===
Repo: ${A.repo_name}${A.purpose ? ` (${A.purpose})` : ''}
Ground truth (pinned checkout): ${A.repo} at ${A.sha}${A.sha_date ? ` (${A.sha_date})` : ''}. Cite code as repo-relative path:line from THIS checkout.
Branch refs (cite as alias@path:line; read with git -C <git_dir> show <ref>:<path>):
${list(A.branches, b => `- ${b.alias}@ = ${b.ref}${b.sha ? ` at ${b.sha}` : ''}, git dir ${b.git_dir}${b.note ? ` (${b.note})` : ''}`)}
Other local sources (read-only; may predate the pin, so re-verify anything you take from them):
${list(A.extra_sources, s => `- ${s.path}${s.note ? `: ${s.note}` : ''}`)}
Doc reader: ${A.reader_profile || 'a smart junior engineer who is new to this repo'}
${A.background ? `Reader background (facts for the "If you come from X" part only): ${A.background}\n` : ''}${A.focus ? `User's focus: ${A.focus}\n` : ''}Size tier: ${A.tier || 'medium'}
Today: ${A.today || 'see system date'}
Scratch directory (the only place you may write files, apart from the doc itself for the writer and fixer): ${A.scratch}
Repo-specific don'ts:
${list(A.constraints, c => `- ${c}`)}
=== END RUN CONTEXT ===
`

// ---- schemas ------------------------------------------------------------
const STR = { type: 'string' }
const arr = (props, required) => ({ type: 'array', items: { type: 'object', properties: props, required } })

const NOTES_SCHEMA = {
  type: 'object',
  properties: {
    area: STR,
    plain_summary: { type: 'string', description: '5-10 plain sentences a newcomer reads first' },
    walkthrough: { type: 'string', description: 'markdown narrative answering every deliverable, with path:line refs inline' },
    diagram: { type: 'string', description: 'ASCII diagram(s), or empty' },
    trace_steps: arr({ step: STR, what_happens: STR, ref: STR }, ['step', 'what_happens']),
    concepts: arr({ name: STR, plain_explanation: STR, analogy: STR, code_refs: { type: 'array', items: STR }, details: STR }, ['name', 'plain_explanation']),
    patterns: arr({ pattern: STR, example_ref: STR, why: STR }, ['pattern']),
    gotchas: arr({ gotcha: STR, ref: STR, impact: STR }, ['gotcha']),
    commands: arr({ cmd: STR, what: STR, label: { type: 'string', enum: ['FREE', 'READS PROD', 'COSTS MONEY', 'TOUCHES PROD'] }, source_ref: STR }, ['cmd', 'what', 'label']),
    key_files: arr({ path: STR, one_line: STR }, ['path', 'one_line']),
    glossary: arr({ term: STR, meaning: STR }, ['term', 'meaning']),
    doc_drift: { type: 'array', items: STR },
    open_questions: { type: 'array', items: STR },
  },
  required: ['area', 'plain_summary', 'walkthrough', 'concepts', 'key_files', 'glossary'],
}

const FACTS_SCHEMA = {
  type: 'object',
  properties: {
    factual_errors: arr({ doc_quote: STR, problem: STR, correct_fact: STR, evidence_ref: STR, severity: { type: 'string', enum: ['high', 'medium', 'low'] } }, ['doc_quote', 'problem', 'correct_fact', 'severity']),
    bad_refs: arr({ ref: STR, doc_quote: STR, problem: STR, correct_ref: STR }, ['ref', 'problem']),
    needs_live_check: arr({ doc_quote: STR, what_local_refs_show: STR }, ['doc_quote']),
    claims_checked: { type: 'integer' },
    claims_confirmed: { type: 'integer' },
    verdict: STR,
  },
  required: ['factual_errors', 'bad_refs', 'claims_checked', 'claims_confirmed', 'verdict'],
}

const READER_CRITIC_SCHEMA = {
  type: 'object',
  properties: {
    confusing: arr({ doc_quote: STR, why_confusing: STR, suggested_rewrite: STR }, ['doc_quote', 'why_confusing']),
    missing_topics: arr({ topic: STR, why_it_matters: STR, source_ref: STR, suggested_text: STR }, ['topic', 'why_it_matters']),
    safety_issues: arr({ doc_quote: STR, risk: STR, fix: STR }, ['doc_quote', 'risk', 'fix']),
    structure_issues: { type: 'array', items: STR },
    verdict: STR,
  },
  required: ['confusing', 'missing_topics', 'safety_issues', 'verdict'],
}

const FIX_SCHEMA = {
  type: 'object',
  properties: {
    applied: arr({ finding: STR, change_summary: STR, evidence_ref: STR }, ['finding', 'change_summary']),
    rejected: arr({ finding: STR, reason: STR, evidence_ref: STR }, ['finding', 'reason']),
    needs_main_agent: arr({ finding: STR, why: STR }, ['finding', 'why']),
    doc_chars: { type: 'integer' },
    summary: STR,
  },
  required: ['applied', 'rejected', 'needs_main_agent', 'summary'],
}

// ---- Read ---------------------------------------------------------------
phase('Read')
const n = A.areas.length
const notes = await parallel(A.areas.map((a, i) => () =>
  agent(`Your instructions are in ${BRIEFS}/reader.md. Read that file first and follow it.
${CTX}
YOUR AREA (${i + 1} of ${n}): ${a.title}
Files and folders to read: ${asLines(a.files).join(', ') || 'decide from the area title'}
Deliverables (answer each one explicitly in your walkthrough):
${asLines(a.deliver).map((d, j) => `${j + 1}. ${d}`).join('\n') || '1. Explain this area end to end.'}
The other readers cover: ${A.areas.filter((_, j) => j !== i).map(o => o.title).join('; ') || 'nothing else'}. Stay in your area, but note the hand-off points into theirs.`,
  { label: `read:${a.key}`, phase: 'Read', schema: NOTES_SCHEMA })
    .then(r => (r ? { key: a.key, title: a.title, ...r } : null))))

const good = notes.filter(Boolean)
const lost = A.areas.map(a => a.key).filter(k => !good.some(g => g.key === k))
if (lost.length) log(`No notes from: ${lost.join(', ')}. The writer will cover those areas thinly from code.`)
log(`${good.length}/${n} area notes collected`)
if (!good.length) return { error: 'no reader notes came back', out: A.out }

// ---- Write --------------------------------------------------------------
phase('Write')
const writeReport = await agent(`Your instructions are in ${BRIEFS}/writer.md. Read it first, then read ${REF_DIR}/doc-blueprint.md and ${REF_DIR}/style-guide.md.
${CTX}
Write the doc to: ${A.out}
Title: ${A.title || `${A.repo_name} onboarding: the whole codebase, explained simply`}
Target length: ${A.target_chars || '50,000–80,000'} characters.
Scout inventory (repo facts: folders, sizes, entry points, CI): ${A.scout_path || 'not provided'}
${lost.length ? `These areas have NO notes because their readers failed: ${lost.join(', ')}. Cover them briefly from code you open yourself, and mark them as thin.\n` : ''}
READER NOTES (JSON):
${JSON.stringify(good)}`, { label: 'write:doc', phase: 'Write' })

// ---- Check --------------------------------------------------------------
phase('Check')
const [facts, readerCritique] = await parallel([
  () => agent(`Your instructions are in ${BRIEFS}/critic-facts.md. Read it first.
${CTX}
Doc to check: ${A.out}
Check at least ${A.claims_to_check || 45} load-bearing claims, spread across all parts.
Writer's report, for context:
${String(writeReport || '').slice(0, 4000)}`, { label: 'check:facts', phase: 'Check', schema: FACTS_SCHEMA }),
  () => agent(`Your instructions are in ${BRIEFS}/critic-reader.md. Read it first, plus ${REF_DIR}/doc-blueprint.md for the expected parts.
${CTX}
Doc to review: ${A.out}
Scout inventory: ${A.scout_path || 'not provided; list the top-level folders yourself'}
Planned reader areas: ${A.areas.map(a => a.title).join('; ')}`, { label: 'check:reader', phase: 'Check', schema: READER_CRITIC_SCHEMA }),
])
if (!facts) log('Fact-checker returned nothing. The main agent must run a manual fact pass.')
if (!readerCritique) log('Reader critic returned nothing. The main agent must do a manual read-through.')

// ---- Fix ----------------------------------------------------------------
phase('Fix')
let fix = null
if (facts || readerCritique) {
  fix = await agent(`Your instructions are in ${BRIEFS}/fixer.md. Read it first, then ${REF_DIR}/style-guide.md.
${CTX}
Doc to fix (edit it in place): ${A.out}
Fact-checker claims_checked = ${facts ? facts.claims_checked : 'n/a'}.
FINDINGS (JSON):
${JSON.stringify({ fact_checker: facts, reader_critic: readerCritique })}`, { label: 'fix:doc', phase: 'Fix', schema: FIX_SCHEMA })
}

return {
  out: A.out,
  sha: A.sha,
  readers: { ok: good.map(g => g.key), missing: lost },
  open_questions: good.flatMap(g => (g.open_questions || []).map(q => `[${g.key}] ${q}`)),
  write_report: String(writeReport || '').slice(0, 3000),
  facts: facts && {
    claims_checked: facts.claims_checked,
    claims_confirmed: facts.claims_confirmed,
    factual_errors: facts.factual_errors.length,
    bad_refs: facts.bad_refs.length,
    needs_live_check: facts.needs_live_check || [],
    verdict: facts.verdict,
  },
  reader_critic: readerCritique && {
    confusing: readerCritique.confusing.length,
    missing_topics: readerCritique.missing_topics.length,
    safety_issues: readerCritique.safety_issues.length,
    structure_issues: readerCritique.structure_issues || [],
    verdict: readerCritique.verdict,
  },
  fix,
}
