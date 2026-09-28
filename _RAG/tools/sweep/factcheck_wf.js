export const meta = {
  name: 'factcheck-notes',
  description: 'Fact-check vault notes in parallel; each agent reads its note, verifies key claims via web sources, returns structured fact_checks + new source records',
  phases: [{ title: 'Fact-check', detail: 'one agent per note' }],
}

const VAULT = 'C:\\Users\\utopi\\OneDrive\\Desktop\\Earth _WorldBuilding\\'

const SCHEMA = {
  type: 'object',
  properties: {
    title: { type: 'string' },
    summary: { type: 'string' },
    checks: { type: 'array', items: { type: 'string' }, minItems: 2, maxItems: 5 },
    sources_new: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' }, citation: { type: 'string' }, url: { type: 'string' },
          kind: { type: 'string' }, reliability: { type: 'string' }, used: { type: 'string' },
          caveats: { type: 'string' }, access: { type: 'string' }, access_route: { type: 'string' },
          read_on: { type: 'string' },
        },
        required: ['title', 'citation', 'url', 'used', 'caveats', 'access'],
      },
    },
    corrections: { type: 'array', items: { type: 'string' } },
  },
  required: ['title', 'checks', 'sources_new', 'corrections'],
}

function prompt(n) {
  return `You are fact-checking ONE entry of a history vault (Earth Chronicle).

1. Read the note file: ${VAULT}${n.path}  (title: "${n.title}", type: ${n.type}). Read its frontmatter (including date_start/date_end) and its "## Facts" and "## Summary" sections.
2. The note's frontmatter cites only generic placeholder sources ("Encyclopaedia Britannica", "English Wikipedia" homepage notes) which are NOT valid citations. Verify the load-bearing claims (key dates, names, numbers, causal claims) against real pages you actually read with WebFetch/WebSearch. Prefer the specific Wikipedia article on this exact subject (Wikipedia is fetchable; Britannica usually returns 403 - try at most once via a Wayback URL like https://web.archive.org/web/2id_/<url>, otherwise skip it). Budget: about 2-4 page reads in total; do not exhaustively crawl.
3. Before proposing a source, Glob "${VAULT}07_Sources\\Wikipedia on <Topic>*.md". If a source note already exists for that page, reuse its exact title in your checks and do NOT list it in sources_new.

Return via the structured output:
- title: exactly "${n.title}"
- summary: one or two sentences on what you verified and any caveat (not shown to readers).
- checks: 2-5 strings, each one factual sentence followed by exactly one bracket citation, shaped like: <claim, no double-quote characters> [Source Title]  (two sources: [Source A; Source B]). Pick the most load-bearing claims (birth/death or founding dates, central facts, headline numbers). Every claim must be supported by text you actually read. Never invent or guess. If a claim in the note is contested, hedge it the way the source does.
- sources_new: one record per distinct Source Title cited that does not already exist in the vault, with title (convention: "Wikipedia on <Article Title>", exactly matching the bracket text), citation (use single quotes around the article title, never double quotes, e.g. Wikipedia. 'Article Title' (English edition).), url (the real page URL you read), kind "reference", reliability "medium" (or "high" for a specialist source), used (one sentence: what it supports), caveats (one sentence), access ("reference-text" only if you read the page text itself; "summary-only" if you only saw search snippets), access_route (how you read it), read_on "2026-09-27".
- corrections: if a claim in the note is WRONG or a frontmatter date conflicts with the sources, one line each: what the note says, what the source says (with source title). Do not put wrong claims in checks. Empty array if none.`
}

const items = args || []
const results = await parallel(items.map(n => () =>
  agent(prompt(n), { label: `fc:${n.title}`, phase: 'Fact-check', schema: SCHEMA })
    .then(r => r ? { ...r, _path: n.path } : null)))
const ok = results.filter(Boolean)
log(`${ok.length}/${items.length} notes returned`)
return ok
