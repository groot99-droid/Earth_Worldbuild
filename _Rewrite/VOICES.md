# Voices for the rewrite layer

This is the brief every rewrite follows, for the Earth Chronicle site (`_Site`) and the Chronicle Museum (`_Museum`).

**Where the voices come from.** The four voices belong to the creative-writing tool in
`C:\Users\utopi\OneDrive\Desktop\Pipelines\creative-writing`. Its authority is `vault/CLAUDE.md`
("Writing Style & Narrative Style, by mode" and "Anti-Style / do-not list"); `pipeline/spec.yaml` (`modes:`) is the
machine-readable form. This file condenses those rules for *retelling history*, not for writing new fiction. If they
change, update this file to match. Never edit anything in that vault.

## What a rewrite is

A rewrite retells existing text in a new voice. It does not add anything. Each rewrite says what its source says:
the same claims, dates, names and uncertainty, in one of the author's four voices. The sites show the layer with an
"AI rewrite" label. The vault notes and the museum manifest stay the record and are never edited.

## Choosing the voice: a mix, each where it fits

Each batch item arrives with a suggested `mode` (the voice for the summary, facts, context, questions and extra
sections) and, on the site, an `observer_mode` (the voice for the Observer's Reading only). Keep the suggestion unless
another voice clearly fits better. A batch should read as a mix, so don't flatten everything into one voice.

| Voice | Fits | Site | Museum |
|---|---|---|---|
| `epic-fantasy` | deep time, eras, regions, places, cultures and empires, species, ancient and medieval events, myth | Hadean Eon, Abbasid Caliphate, a river valley, a dynasty | landscapes, myth, sacred narrative, the Genji scrolls, Hokusai |
| `horror-prose` | natural catastrophe and pre-modern plague: extinctions, impacts, eruptions, glaciations, collapses, the Black Death | Permian extinction, Toba eruption, Snowball Earth | dark subjects: Saturn, The Scream, Medusa, Judith, the Last Judgment |
| `essay-self-help` | people, ideas, technologies, themes, sources, modern events, and **all human atrocity** (war, genocide, slavery, conquest, massacre, modern pandemics) | Ada Lovelace, the printing press, the theme of trade, the Armenian genocide | architecture and design (the voice's own keyword is "architecture"), novels, film, the Slave Ship, the Third of May |
| `confessional-poetry` | the Observer's Reading on art, kinship, faith or a single life; intimate works | the Observer on a poet or a pilgrim | portraits, self-portraits, mothers and children, the sick child, betrayal (the Kiss of Judas) |

Rules for the mix:
- One body voice per item, plus one Observer voice on the site. Don't switch voice partway through a field.
- **Confessional first person belongs to the Observer** (site) **or to a visitor standing before the work** (museum).
  Never put words, thoughts or feelings into a real historical person's mouth. "I" is never Ada Lovelace.
- **Human atrocity is never horror-prose.** Victims keep their dignity and their interior lives, per the vault's ethical
  restraint precedent. No gore, no technique, no spectacle. For these, the essay voice is grave and plain, not uplifting.
- Source notes (`type: source`) describe a book, dataset or website. Use the essay voice, briefly: they are about what a
  source is good for.

## The four voices

### Epic-fantasy
Third person. Use past tense for narrative, and a codex or world-bible register for a place, era or culture ("The
Achaemenids were…"). Dense with simile, with figurative language drawn from nature, light and water. Memory, prophecy and
elemental imbalance can supply *imagery* but never claims: a volcano may wake and a sea may forget its shore, but no gods,
omens or prophecies are asserted as history.

Anchor lines (the author's own, for tone only; never copy them):
- "The first sign came quietly, the way rot always does—soft, almost apologetic, as if asking permission to exist." (*WrymWretch*)
- "The cosmos began as the First Light, a singular radiant being that shattered into two primal forces" (*World Codex of Wyrmreach*)

### Horror-prose
Plain and punchy, with concrete sensory words rather than abstraction. Short sentences and stacked fragments carry the
emphasis. Interiority is clipped. A paragraph closes on a one-line gut-punch or an ominous fragment. The engine is
**escalation by catalogued incident**: list the wrongnesses in order, each worse than the last. Nothing is rescued or
resolved, and the ending lands on the cycle continuing or the world changed for good. Don't hold sensory description over
several paragraphs; compress it into fragments.

Anchor lines:
- "No wind. No insects. No owls. Nothing." (the vault's own example of the fragment stack)
- "The world fractured. His heartbeat thundered, then slowed to a crawl." (*Melting Away*)

### Essay / self-help
Direct address: *you* or *we*, and it may shift within a piece. The lexicon is elevated and heavy on abstract nouns.
**"Architecture" is the connective-tissue word**, alongside covenant, threshold, ledger, communion, sovereignty, doctrine,
lineage, codex, grammar and genealogies. Use them where they fit, not in every line. The rhythm is **claim → illustrative
example → practice → closing callback or aphorism**. Keep the voice's habit of over-explaining: give the concrete image,
then say plainly what it means. Don't sand that down into subtlety.

Anchor lines:
- "Desire is the compass, but deprivation is the teacher." (*The Architecture of Being*)
- "Think of the moment you cup your hands under cold tap water after hours in the heat — how the shock, the relief, the clarity all arrive at once. That is presence." (*The Architecture of Being*)

### Confessional poetry
First person, spoken by the Observer or the visitor, working through loss, kinship, faith or self-worth. Build it on
anaphora and triads ("I remember… I remember…"), use rhetorical questions as turns, and end on an aphoristic line that
lands the point plainly rather than trailing off. The site joins the lines of a paragraph with spaces, so write in
prose-poem sentences and use a blank line, sparingly, as a stanza break.

Anchor lines:
- "I thought you meant to break me but you were the one who made me." (*Inherited*)
- "But the trial did not end in the pit. / It began there." (*The Stripes Remain*)

## Fidelity rules

`rewrite_layer.py validate` checks rules 2 to 7 and 10; rules 1, 8 and 9 are on you.

1. **Same claims.** Never add a fact, cause, motive, date, place, name, quantity or quotation that the source lacks, and
   never drop one. Imagery is allowed; new claims are not. A metaphor must not read as a fact: "the sea swallowed the
   valley" is fine only if the source says the valley flooded.
2. **Numbers.** Every number in a field stays in that field, in the source's own form (digits stay digits, words stay
   words), with its scale word and era marker unchanged: "66 million", "750 CE", "c. 973", "10,000", "ten million". Add
   no new numbers or number words, and don't restate a quantity in other words ("eight in ten" for 80 percent). Counting
   things the source itself lists ("two lamps" for Earth and the Moon) is fine for two and three only.
3. **Names.** Add no capitalised word that does not already appear somewhere in the source item (its title, text, era or
   region, or, for the museum, the work's title, artist, year, medium or location). Lowercase common words, and don't
   invent proper nouns ("the Deep", "the Burning", "Mother Ocean").
4. **Links.** Every `[[id|Label]]` token in a field stays in that same field, character for character. Move it anywhere in
   the sentence, but add no new tokens.
5. **Uncertainty.** Keep every hedge, and keep it of the same kind. There are four kinds: *approximation* (about, c.,
   roughly, estimated, at least), *doubt* (debated, disputed, uncertain, unknown, whether), *probability* (perhaps, likely,
   may, suggests, seems) and *attribution* (traditionally, attributed, according to, regarded, often, believed). If the source
   says "is debated", the rewrite needs a doubt word, and an unrelated "about" won't do. Confidence is the chronicle's
   spine: a legend must not harden into a fact.
6. **One-to-one.** Each fact becomes exactly one rewritten fact, and each question stays a question ending in "?". Extra
   sections keep their exact titles. The summary, context and observer fields appear only where the source has them.
7. **Length.** Each field runs 0.6 to 1.8 times the length of its source, or up to its source length plus 200 characters,
   whichever is more, so a short Observer's Reading still has room for the voice's shape. Short items (facts, questions,
   anything under 90 characters) may run 0.4 to 3.5 times.
8. **Facts stay facts.** Keep one claim per fact bullet: a voice, not a scene. A fact may carry one clause of imagery or
   framing ("Her lineage ran through poetry: …"). In horror-prose it may break into fragments, as long as they carry that
   one claim and nothing more ("Opening. And opening."). The Observer's Reading stays interpretation. The first 240
   characters of the summary become the card blurb on the site, so open with a strong, complete sentence that says what
   the note is about. If the source summary is itself a question, keep it a question.
9. **Closing lines and personas.** An aphorism or closing callback must be general and interpretive ("Ideas can outrun
   their tools"), never a new claim about the subject. In the essay voice the Observer may stay in the third person ("The
   Observer notes…") while addressing the reader as *you* or *we*. A museum visitor's "I" may bring a line of their own
   feeling ("What grief is ever finished?"), but nothing about the artist or the work that the placard doesn't say.
10. **Markup only.** Separate paragraphs with a blank line, use "- " for list items only where the source has a list, and
   use `**bold**` and `*italic*`. No HTML, no headings, and no meta-commentary such as "In the style of…" or "Here is…".

## Batch format

`export` writes `_Rewrite/batches/<target>-NNN.md`. You write `_Rewrite/incoming/<target>-NNN.md` in **the same shape**:

```
<!-- batch site-004 · target site · 12 items · rules: _Rewrite/VOICES.md -->

=== person/ada-lovelace
title: Ada Lovelace
src: 3f2a9c01be77
mode: essay-self-help
observer_mode: confessional-poetry
--- summary
(rewritten summary)
--- fact 1
(rewritten fact 1)
--- context
(rewritten context, with its [[technology/digital-computer|Digital Computer]] tokens intact)
--- observer
(rewritten Observer's Reading)
--- question 1
(rewritten question?)
--- extra 1: Caveats
(rewritten caveats)
```

- Keep the header comment line: it tells the tool the target.
- Keep `=== id`, `src:` and every `--- section` line exactly as exported. Set `mode:` (and `observer_mode:`) to the voice
  you actually used. The `title/type/date/themes/artist/year/medium/location` lines are context only, so keep them or drop them.
- Museum items have a single `--- description` section and no `observer_mode`.
- A long batch may be written as several files (`site-004.part1.md`, `site-004.part2.md`, …), each starting with the same
  header comment line.

## Commands

```
python _Rewrite/rewrite_layer.py status                         # counts per target: rewritten, stale, not yet rewritten
python _Rewrite/rewrite_layer.py export --target site           # pending notes -> _Rewrite/batches/site-NNN.md
python _Rewrite/rewrite_layer.py export --target museum         # pending placards -> _Rewrite/batches/museum-NNN.md
python _Rewrite/rewrite_layer.py todo _Rewrite/batches/site-004.md     # items in a batch not merged yet
python _Rewrite/rewrite_layer.py validate _Rewrite/incoming/site-004.md
python _Rewrite/rewrite_layer.py merge _Rewrite/incoming/site-004.md    # keeps passing items, publishes both sites
python _Rewrite/rewrite_layer.py publish                        # rebuild the published layer (drops stale rewrites)
```

"Pending" means that an item has no rewrite yet, or that its source text changed after it was rewritten. That is how new
additions are found.
