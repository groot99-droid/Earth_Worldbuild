export const meta = {
  name: 'apply-corrections',
  description: 'For notes where fact-checking found discrepancies, propose minimal exact-once text edits (hedge or correct) and list frontmatter date issues',
  phases: [{ title: 'Corrections', detail: 'one agent per note with discrepancies' }],
}

const VAULT = 'C:\\Users\\utopi\\OneDrive\\Desktop\\Earth _WorldBuilding\\'

const SCHEMA = {
  type: 'object',
  properties: {
    title: { type: 'string' },
    replacements: {
      type: 'array',
      items: {
        type: 'object',
        properties: { old: { type: 'string' }, new: { type: 'string' }, why: { type: 'string' } },
        required: ['old', 'new'],
      },
    },
    frontmatter_issues: { type: 'array', items: { type: 'string' } },
    left_unchanged: { type: 'array', items: { type: 'string' } },
  },
  required: ['title', 'replacements', 'frontmatter_issues', 'left_unchanged'],
}

function prompt(n, file) {
  return `You are editing ONE note of a history vault (Earth Chronicle) after a fact-check found discrepancies between the note and web sources.

Note file: ${VAULT}${n.path}   (title "${n.title}")
Discrepancies file: ${file}  (a JSON object mapping note title -> array of discrepancy strings; read the array for "${n.title}").

Read both. For each discrepancy decide, with minimal editing:
- If the source clearly contradicts a specific figure/date/name in the note body: correct it (keep any existing hedge words like "about", "traditionally").
- If sources differ or the source merely does not confirm a detail the note states: hedge the wording lightly ("about", "traditionally", "sources differ") or leave it, do not delete true-but-unconfirmed content.
- If a discrepancy concerns a frontmatter field (date_start, date_end, precision), DO NOT edit frontmatter; instead describe it in frontmatter_issues (one line: field, current value, what the source says).
- Only edit body text (Summary, Facts, Context & Connections, Observer's Reading, Open Questions). Keep Summary and Facts consistent with each other. Keep the house style: plain sentences, numbers written like "1907 to 1954", no em dashes, no double-quote characters inside your new text, keep [[wikilinks]] intact.
- Do not add any new factual claim beyond what the discrepancy text itself states. Never introduce a name, number, date or place that is not literally present in the discrepancy text or already in the note; if the discrepancy text does not give the corrected detail, hedge or leave the note unchanged. If you doubt a discrepancy, you may do at most 2 WebFetch/WebSearch checks; otherwise trust the text.
- Prefer several small replacements over rewriting paragraphs.

Return via the structured output:
- title: exactly "${n.title}"
- replacements: list of {old, new, why}. "old" MUST be copied verbatim from the note file and occur EXACTLY ONCE in the file (extend the snippet with neighboring words until it is unique; it may span within a single line only). "new" is the replacement text. "why" is a short reason.
- frontmatter_issues: as described (empty array if none).
- left_unchanged: discrepancies you deliberately did not change, with a short reason (empty array if none).`
}

const CORR_FILE = args.file
const items = args.items || []
const results = await parallel(items.map(n => () =>
  agent(prompt(n, CORR_FILE), { label: `corr:${n.title}`, phase: 'Corrections', schema: SCHEMA })))
const ok = results.filter(Boolean)
log(`${ok.length}/${items.length} notes returned`)
return ok
