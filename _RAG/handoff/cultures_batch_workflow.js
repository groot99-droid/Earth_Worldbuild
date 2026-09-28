export const meta = {
  name: 'cultures-batch',
  description: 'Write, adversarially fact-verify and integrate batches of Peoples & Cultures notes (Earth Chronicle Brief 1)',
  phases: [
    { title: 'Write', detail: 'one agent per title: research online, write the note file' },
    { title: 'Verify', detail: 'independent skeptic per note: refute claims, repair in place, re-check word count and validator' },
    { title: 'Integrate', detail: 'validate, update hubs, validate, tally regions, try reindex' },
  ],
}

const RULES = `
HOUSE RULES (Earth Chronicle vault; working directory is the vault root, "Earth _WorldBuilding"; shell is Git Bash on Windows, always quote paths; forward slashes)

FILE: 03_Entities/Peoples-Cultures/<Title>.md  (filename = title + .md; title field must equal it exactly, diacritics fine).

FRONTMATTER (every value on ONE line, between two --- lines), in this order:
title: "<Title>"
type: culture
era: "[[<one of: Neolithic | Bronze Age | Iron Age | Classical Antiquity | Medieval Period | Early Modern Period | Industrial Age | Information Age>]]"   (era of main activity / florescence. Bounds: Neolithic -9600..-3300; Bronze Age -3300..-1200; Iron Age -1200..-500; Classical Antiquity -500..500; Medieval Period 500..1500; Early Modern Period 1500..1800; Industrial Age 1760..1945; Information Age 1945+)
region: "[[<exactly one of: Amazon Basin and South American Lowlands | Andes | Arabian Peninsula | Caribbean and Atlantic World | Central Asian Oases | Central Asian Steppe | East Asia | Europe | Iranian Plateau | Levant and Anatolia | Mediterranean Basin | Mesoamerica | Mesopotamia | Nile Valley | North America | Oceania | Siberia and the Arctic | South Asia | Southeast Asia | Sub-Saharan Africa>]]"  (use the region the task gives you unless it is plainly wrong; primary home)
themes: [one or more of: science, technology, religion, war, trade, kinship, language, art, earth-systems]
date_start: <integer, REQUIRED; 1 BCE = -1, no year 0; must be >= -11700>   (approximate start of florescence)
date_end: <integer, omit if the culture is living/ongoing or unknown>   (approximate end of florescence)
date_precision: <exact|year|decade|century|approx>
related: ["[[Existing Note]]", ...]   (only notes that EXIST in the vault right now)
sources: ["[[Encyclopaedia Britannica]]", "[[English Wikipedia]]"]   (usually these two; only cite a source whose note exists in 07_Sources)
confidence: <high|medium|low>   (low/medium when the culture is a scholarly construct, dates are traditional, or sources conflict)
status: seed
tags: []
NO fact_checks field. Never add one.

BODY, sections in this exact order:
## Summary        (1-3 sentences: subject, when, where)
## Facts          (4-6 short dated/checkable bullets covering geography, subsistence/economy, political organization, material culture, key events, decline or transformation - choose the most important; cut a bullet rather than run long)
## Context & Connections   (2-3 sentences with [[wikilinks]] to the era, region, theme hub(s) such as [[War and Conflict]] [[Trade and Economy]] [[Religion and Belief]] [[Kinship and Society]] [[Language and Writing]] [[Art and Ritual]] [[Science]] [[Technology]] [[Earth Systems and Life]], and related existing notes)
## Observer's Reading   (EXACTLY 3 short sentences. It ends with what a specialist could argue that would weaken it: "A specialist could argue ... which would weaken ...")
## Open Questions  (1-3 bullets, phrased as real questions)
Name the subject explicitly in every section (no dangling "it").

TWO-LAYER RULE: Summary, Facts, Context, Open Questions are neutral plain language with NO Observer vocabulary. Only the Observer's Reading may use it, and ONLY these terms: the species (=humans); meaning-engine (religion/ideology/cosmology); story-glue (shared narratives); claim-line (border/property line); exchange-web (trade network); kin-lattice (kinship/descent); sound-code / mark-code (speech / writing); memory-outsourcing (writing, archives); grief-rite (funerary practice); tool-lineage (technology as inheritance); sanctioned harm (organized approved violence); the Settling (agriculture); heat-domestication (fire); status-signal (prestige display); pattern-taming (science); ancestor-weight (pull of tradition). Tone: curious, never contemptuous; the same standard for every people, state, faith and ideology (modern and secular included); never sneer at belief; never rank peoples. State harm done (conquest, slavery, massacre, dispossession) plainly and without euphemism or relish; state contested or disputed claims as disputed.

LINK RULE: a [[wikilink]] may point ONLY to a note that exists right now (check with ls). Every mention of a not-yet-written culture/person/place is plain text, no brackets. Do not link to your own title.

LENGTH: body = everything after the second --- line. Measure with:
awk 'BEGIN{c=0} /^---$/{c++; next} c>=2{print}' "03_Entities/Peoples-Cultures/<Title>.md" | wc -w
TARGET 300-330 words (hard range 290-335). First drafts run long: write tight.

FACTS: never invent dates, numbers, quotations or citations. Verify anything specific online. If a figure or date cannot be corroborated, drop it or hedge it ("about", "traditionally", "by one estimate") and lower confidence. Paraphrase; do not copy source sentences.

VALIDATION of your own file: PYTHONUTF8=1 _RAG/.venv/Scripts/python.exe _RAG/tools/validate_vault.py 2>&1 | grep -F "<Title>.md"
must print NOTHING except possibly an orphan WARNING (hubs are regenerated later). Other sessions are editing the vault at the same time, so IGNORE validator lines about other files, and do not fix or touch any file that is not yours.
`

const WRITE_SCHEMA = {
  type: 'object',
  properties: {
    title: { type: 'string' },
    status: { type: 'string', enum: ['written', 'skipped_taken', 'failed'] },
    path: { type: 'string' },
    region: { type: 'string' },
    era: { type: 'string' },
    date_start: { type: 'number' },
    date_end: { type: 'number' },
    confidence: { type: 'string' },
    wordCount: { type: 'number' },
    linksUsed: { type: 'array', items: { type: 'string' } },
    plainTextMentions: { type: 'array', items: { type: 'string' } },
    unverifiedOrDisputedClaims: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['title', 'status'],
}

const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    title: { type: 'string' },
    verdict: { type: 'string', enum: ['ok', 'fixed', 'problem'] },
    claimsChecked: { type: 'number' },
    changes: { type: 'array', items: { type: 'string' } },
    remainingConcerns: { type: 'array', items: { type: 'string' } },
    wordCount: { type: 'number' },
    ownFileValidatorLines: { type: 'array', items: { type: 'string' } },
    finalConfidence: { type: 'string' },
  },
  required: ['title', 'verdict', 'wordCount'],
}

const INTEG_SCHEMA = {
  type: 'object',
  properties: {
    notesOnDiskInFolder: { type: 'number' },
    errorsTotal: { type: 'number' },
    errorsInBatchFiles: { type: 'number' },
    batchFileErrorLines: { type: 'array', items: { type: 'string' } },
    otherFileErrorSummary: { type: 'string' },
    orphanWarningsAfterHubs: { type: 'number' },
    hubsRan: { type: 'boolean' },
    wordCounts: { type: 'array', items: { type: 'object', properties: { title: { type: 'string' }, words: { type: 'number' } }, required: ['title', 'words'] } },
    regionTally: { type: 'string' },
    reindex: { type: 'string' },
  },
  required: ['notesOnDiskInFolder', 'errorsInBatchFiles', 'hubsRan'],
}

function writerPrompt(it) {
  return 'You are writing ONE new Peoples & Cultures note for the Earth Chronicle vault: "' + it.title + '" (suggested region: ' + it.region + '; ' + (it.hint || 'choose era/dates yourself from the evidence') + ').\n\n' +
    'STEPS\n' +
    '1. Check the title is free vault-wide (other sessions add notes fast): find . -iname "' + it.title + '.md" -not -path "./_RAG/*"  . If ANY file exists, write nothing and return status skipped_taken.\n' +
    '2. Read two house-style models: 03_Entities/Peoples-Cultures/Celts.md and 03_Entities/Peoples-Cultures/Kalinago.md. Copy their structure and register, not their content.\n' +
    '3. List valid link targets: ls 03_Entities/Peoples-Cultures 03_Entities/Events 03_Entities/People 03_Entities/Places 03_Entities/Artifacts-Technologies ; the era, region and theme hubs are 01_Eras, 02_Regions, 04_Themes ; confirm any source note exists in 07_Sources.\n' +
    '4. Research with WebSearch (several distinct queries: overview, chronology, economy/subsistence, political organization, material culture, decline; add a query for scholarly disagreement on the name/definition/dating). WebFetch on Wikipedia has been failing; try britannica.com or other pages via WebFetch, but rely on search results if fetches fail. Cross-check every date and figure you plan to use against at least two results.\n' +
    '5. Write the file with the Write tool, then measure words, trim to 300-330, and validate your own file (rules below). Use the era/date bounds in the rules. A culture note describes the people/polity: geography, subsistence and economy, political organization, material culture, key events, decline or transformation. Observer reading angles: how the group held strangers together, marked claim-lines, treated its dead, and what survives.\n' +
    '6. Return the structured result. In unverifiedOrDisputedClaims list any statement you could not corroborate or that scholars dispute (the next agent will scrutinize those first). In plainTextMentions list other cultures/people/places you mention in plain text that are natural future link targets.\n' + RULES
}

function verifierPrompt(it, w) {
  return 'You are an independent SKEPTIC and editor. Another agent just wrote 03_Entities/Peoples-Cultures/' + it.title + '.md (suggested region ' + it.region + '). Your job: try to REFUTE it, then repair it in place.\n\n' +
    'STEPS\n' +
    '1. Read the file. Then list every checkable claim: each date, number, named person/place/ruler, and each causal or superlative statement, plus era/region/date_start/date_end/date_precision/confidence in the frontmatter. The writer flagged these as shaky: ' + JSON.stringify(w.unverifiedOrDisputedClaims || []) + ' - start there.\n' +
    '2. For each claim run WebSearch aimed at contradicting it (and read at least two independent results for any date or number). Default to skepticism: a claim you cannot corroborate must be softened ("about", "traditionally") or removed; a wrong claim must be corrected. Also check that the note does not overstate a scholarly construct as a single self-aware people, and that ancient/medieval dates are consistent with era bounds.\n' +
    '3. Check the note against every house rule below (structure, section order, two-layer rule with approved Observer terms only in the Reading, exactly 3 short sentences in the Reading ending with the specialist-could-argue clause, no fact_checks field, every wikilink resolves to an existing note - verify each with ls/find, neutral treatment and plain statement of harm, no ranking, no copied phrasing).\n' +
    '4. Repair with surgical Edit calls only (never rewrite the whole file, never touch any other file). After editing, re-measure the body word count (must end 300-330; hard range 290-335) and re-run the own-file validator check.\n' +
    '5. Return the structured verdict: ok (nothing needed changing), fixed (you changed things), or problem (something you could not resolve; explain in remainingConcerns).\n' + RULES
}

function integratePrompt(b, titles) {
  return 'Integration step for Peoples & Cultures batch ' + b.n + '. Run from the vault root ("Earth _WorldBuilding"); Git Bash; quote paths. Do NOT edit any note. Do NOT kill any processes.\n' +
    'Batch files (titles): ' + JSON.stringify(titles) + '\n\n' +
    '1. Count files: ls 03_Entities/Peoples-Cultures | wc -l  -> notesOnDiskInFolder.\n' +
    '2. For each batch title print the body word count: awk \'BEGIN{c=0} /^---$/{c++; next} c>=2{print}\' "03_Entities/Peoples-Cultures/TITLE.md" | wc -w  -> wordCounts.\n' +
    '3. Validate: PYTHONUTF8=1 _RAG/.venv/Scripts/python.exe _RAG/tools/validate_vault.py > /tmp/v_b' + b.n + '.txt 2>&1 ; count ERROR lines (errorsTotal) and how many mention one of the batch filenames (errorsInBatchFiles, list them in batchFileErrorLines). Another session sometimes causes a burst of "fact_checks cites unknown source" errors in OTHER files; summarize any errors outside the batch in otherFileErrorSummary and re-run the validator once if errorsTotal is large, but never fix them.\n' +
    '4. Run PYTHONUTF8=1 _RAG/.venv/Scripts/python.exe _RAG/tools/update_hubs.py (idempotent; regenerates hubs). hubsRan=true if it exited 0.\n' +
    '5. Validate again; report errorsInBatchFiles from THIS run and orphanWarningsAfterHubs (WARN lines that mention a batch file).\n' +
    '6. Region tally: grep -h "^region:" 03_Entities/Peoples-Cultures/*.md | sort | uniq -c | sort -rn  -> regionTally (as text).\n' +
    '7. Try the reindex ONCE: PYTHONUTF8=1 timeout 240 _RAG/.venv/Scripts/python.exe _RAG/build_index.py 2>&1 | tail -5 . It may fail with "database is locked" because another session holds vault.db; that is expected, just record the outcome in reindex. Never retry in a loop and never delete vault.db or its journal.'
}

const A = (typeof args === 'string') ? JSON.parse(args) : args
const out = []
for (const b of A.batches) {
  log('Batch ' + b.n + ': ' + b.items.length + ' notes')
  const chains = await pipeline(
    b.items,
    (it) => agent(writerPrompt(it), { label: 'write:' + it.title, phase: 'Write', schema: WRITE_SCHEMA }),
    (w, it) => (w && w.status === 'written')
      ? agent(verifierPrompt(it, w), { label: 'verify:' + it.title, phase: 'Verify', schema: VERIFY_SCHEMA }).then(v => ({ title: it.title, region: it.region, write: w, verify: v }))
      : { title: it.title, region: it.region, write: w, verify: null }
  )
  const written = chains.filter(c => c && c.write && c.write.status === 'written').map(c => c.title)
  const skipped = chains.filter(c => !c || !c.write || c.write.status !== 'written').map((c, i) => (c && c.title) || b.items[i].title)
  if (skipped.length) log('Batch ' + b.n + ' not written (taken/failed): ' + skipped.join(', '))
  const integ = await agent(integratePrompt(b, written), { label: 'integrate:B' + b.n, phase: 'Integrate', schema: INTEG_SCHEMA, effort: 'low' })
  out.push({ batch: b.n, chains, skipped, integ })
  if (integ && integ.errorsInBatchFiles > 0) {
    log('HALT: batch ' + b.n + ' has validator errors in its own files; stopping for review')
    break
  }
}
return out
