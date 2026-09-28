# BRIEF 3 of 4: Technologies and Themes

Paste this whole brief into a new Claude chat, then send: "Start Part A."

## MISSION
Expand two thin parts of the Earth Chronicle vault, in three parts:
- **Part A. Theme hubs (`04_Themes/`, 9 notes, `type: theme`).** Rewrite each hub from a one-page stub into a rich field guide. The hubs are the main entry points for retrieval, so they matter more than their size suggests. Do not create new hubs or new theme slugs: the vault's validator accepts only the nine existing slugs.
- **Part B. Technologies (`03_Entities/Artifacts-Technologies/`, 24 notes today, `type: technology`).** Add about **+65** notes. Scope: technologies and artifacts whose `date_start` is -11,700 or later. Older tools (the handaxe, spears, needles, boats and so on) belong to a different brief (Early Eras).
- **Part C. Theme essays (`05_Observer_Notes/`, 11 essays today, `type: observer-note`).** Add about **+18** essays, two per theme.

Order: Part A (3 batches of 3 hubs), then Part B (about 8 batches of 8), then Part C (about 5 batches of 4 essays). The batch sizes for Parts A and C override the house rules.

## WHAT IS THIN TODAY (measured)
- Hubs: each is about a page: a 2-sentence Summary, 4 to 5 Key Threads bullets, a short Observer's Reading, one Open Question, and a generated member list. There is no era-by-era view, no regional view and no debates section.
- Technologies: only 2 Paleolithic, 3 Bronze Age, 3 Classical Antiquity, 1 Iron Age, 6 Medieval, 2 Early Modern, 6 Industrial, 1 Information Age. Nothing for optics, sanitation, aviation, semiconductors, GPS or gene editing. Non-Western technologies are thin (crucible steel, porcelain, qanats, chinampas, outrigger canoes).
- Essays: 11 exist (listed under EXISTING TITLES), but theme coverage is uneven: Science and Art and Ritual are tagged on only one essay each and Language and Writing on two, while Technology is on six and Kinship and Society on seven.

## PART A: HUB REWRITE RULES
For each of the nine hubs (Science, Technology, Religion and Belief, War and Conflict, Trade and Economy, Kinship and Society, Language and Writing, Art and Ritual, Earth Systems and Life), output ONLY the replacement text for everything between the frontmatter and the heading `## Notes Tagged With This Theme`. I will keep the existing frontmatter and the generated member block (the `<!-- AUTO:members -->` section) and never touch them. Label each with `### FILE: 04_Themes/<Hub Title>.md (replace body above "Notes Tagged With This Theme")`. Sections, in order:
1. `## Summary`: 3 to 5 sentences defining the theme so a search for it lands here, naming the span from earliest to latest.
2. `## Key Threads`: 10 to 14 bullets, each linking at least one existing note. Together they must touch at least 8 eras and at least 8 regions.
3. `## Through the Eras`: one line for each of Paleolithic, Neolithic, Bronze Age, Iron Age, Classical Antiquity, Medieval Period, Early Modern Period, Industrial Age and Information Age, each with links.
4. `## Regional Patterns`: 5 to 8 bullets, including at least three of Oceania, the Andes, Sub-Saharan Africa, Central Asia, the Arctic, Mesoamerica and Southeast Asia.
5. `## Debates and Limits`: 3 to 5 bullets on real scholarly disagreements and on what the vault does not yet cover.
6. `## Observer's Reading`: 2 to 5 sentences. Keep the hub's existing Observer term (for example pattern-taming for Science) and deepen it.
7. `## Open Questions`: 4 to 6 bullets.
Link only to titles in the lists below. If no listed note fits, write plain text instead of a link.

## PART B: TECHNOLOGY COVERAGE RULES
- At least 20 of the +65 must originate outside Europe and North America. At least 8 must be from the last 200 years, and at least 8 from before 500 BCE.
- Include some artifacts (objects that carry knowledge), as the existing notes do with the Rosetta Stone.
- `date_start` is the earliest firm evidence (not a legend), `date_end` stays empty unless the technology is fully obsolete, and `region` is where the earliest evidence is (Planet-wide if independently invented in many places).
- Facts: what it does, earliest evidence with dates and sites, main improvements, how it spread (regions and dates), which earlier tools it depended on, what it changed. Avoid single-inventor myths and say where priority is contested.
- Observer's Reading angles: tool-lineage, memory-outsourcing, ancestor-weight, why the same tool appeared independently in different places.

## PART B CANDIDATES (suggestions; choose about 65, skip anything under EXISTING TITLES)
- Food and land: Plough, Irrigation Canals, Qanat, Chinampas, Terrace Farming, Haber-Bosch Process, Refrigeration, Canning, Brewing and Fermentation, Salt Production
- Materials and metals: Glassmaking, Crucible Steel, Porcelain, Roman Concrete, Lost-Wax Casting, Loom, Sericulture, Bessemer Process, Plastics, Soap
- Energy and machines: Water Mill, Windmill, Internal Combustion Engine, Electric Motor, Battery, Electric Lighting, Petroleum Refining, Photovoltaic Cell
- Transport and navigation: Outrigger Canoe, Lateen Sail, Astrolabe, Caravel, Stirrup, Roman Roads, Automobile, Airplane, Jet Engine, Liquid-Fueled Rocket, Container Shipping, Cartography
- Information and communication: Papyrus, Codex, Photography, Telephone, Radio, Television, Transistor, Integrated Circuit, Internet, World Wide Web, GPS, Smartphone, Abacus
- Medicine and health: Sanitation and Sewers, Anesthesia, X-ray Imaging, Insulin, Oral Rehydration Therapy, Hormonal Contraception, Water Chlorination, CRISPR Gene Editing, mRNA Vaccines, Variolation
- Instruments: Telescope, Microscope, Eyeglasses, Seismoscope, Radiocarbon Dating
- War: Chariot, Composite Bow, Crossbow, Cannon, Machine Gun, Tank, Nuclear Weapons, Chemical Weapons
- Institutions as technologies: Coinage, Paper Money, Double-Entry Bookkeeping, Calendars, Water Clock
- Built environment: Arch and Vault, Aqueduct, Skyscraper, Elevator
- Artifacts: Antikythera Mechanism, Code of Hammurabi, Cyrus Cylinder, Dead Sea Scrolls, Gutenberg Bible, Nebra Sky Disc, Voynich Manuscript, Terracotta Army

## PART C: ESSAY RULES
Essays use type `observer-note`, are written for the `05_Observer_Notes/` folder, and have a different structure. Frontmatter: title, type: observer-note, `era` (exactly one era), `themes`, `related`, `sources`, `confidence`, `status: seed`, `tags: []` (no region field and no date fields). Body sections in this order: `## Question` (one puzzle an outside observer would pose), `## What the Record Shows` (5 to 8 neutral, checkable bullets with wikilinks, spanning at least 4 regions and 3 eras), `## Observer's Reading` (3 to 6 sentences using glossary terms, including at least one alternative reading), `## Limits of This Reading` (2 to 4 sentences on where the frame may distort). Roughly 350 to 500 words. Use the title style "Short Title - Subtitle" as the existing essays do. Work in batches of 4 essays, and write the essays for Science, Art and Ritual and Language and Writing first, since those themes have the fewest.

Candidates (theme, then suggested era):
- Religion and Belief: "Why Prophets Appear in Clusters" (Iron Age); "Why Every Meaning-Engine Splits" (Medieval Period)
- Science: "Institutionalized Doubt - How Strangers Learned to Check Each Other" (Early Modern Period); "Why the Same Discovery Happens Twice" (Industrial Age)
- Technology: "The Ratchet and Its Gaps - Why Some Tool-Lineages Stall" (Classical Antiquity); "Who Gets Credit for the Machine" (Industrial Age)
- Trade and Economy: "Why Strangers Trust Strangers - Money as Story-Glue" (Iron Age); "Cargo That Was Not Goods - What Exchange-Webs Carry" (Classical Antiquity)
- War and Conflict: "Why Empires Keep Forming" (Iron Age); "The Aftermath Problem - How Societies Remember Their Wars" (Industrial Age)
- Kinship and Society: "The Kin-Lattice at Scale - From Households to States" (Bronze Age); "Who Counts as a Person - The Long Argument over Status" (Industrial Age)
- Language and Writing: "Why Languages Die and Why Some Spread" (Early Modern Period); "Scripts as Borders - Writing and Identity" (Medieval Period)
- Art and Ritual: "Why the Species Makes Things That Do Nothing" (Paleolithic); "Sacred Ground - Why Some Places Are Special" (Neolithic)
- Earth Systems and Life: "The Long Partnership - Domesticates and the Species" (Neolithic); "Plague Years - Disease as a Historical Actor" (Medieval Period)

## EXAMPLE 1 (technology)
---
title: "Quipu"
type: technology
era: "[[Medieval Period]]"
region: "[[Andes]]"
themes: [language, technology, trade]
date_start: 1000
date_end: 1650
date_precision: approx
related: ["[[Inca Empire]]", "[[Caral]]", "[[The Great Outsourcing of Memory]]"]
sources: ["[[Encyclopaedia Britannica]]"]
confidence: medium
status: seed
tags: []
---

## Summary
A quipu (khipu) is a recording device made of knotted cords, used across the Andes and best known from the Inca Empire.

## Facts
- The position and type of knots recorded numbers in a decimal system.
- About 900 to 1,000 quipus survive, and their color and structure may encode more than numbers; this is debated.
- Trained specialists called quipucamayocs kept and read them.
- Spanish colonial authorities banned or destroyed many of them.

## Context & Connections
The quipu was central to how the [[Inca Empire]] governed millions without conventional writing. Compare [[Invention of Writing]].

## Observer's Reading
The Observer regards the quipu as a distinct solution to memory-outsourcing. It shows that a complex state can be run on a record system that looks unlike anything in the written tradition.

## Open Questions
- Did quipus record narrative as well as numbers?

## EXAMPLE 2 (essay)
---
title: "The Fiction of Claim-Lines"
type: observer-note
era: "[[Industrial Age]]"
themes: [war, kinship, trade]
related: ["[[Age of Revolutions]]", "[[Ottoman Empire]]", "[[Han Dynasty]]", "[[Romans]]"]
sources: ["[[The Transformation of the World (Osterhammel)]]", "[[Cambridge World History]]"]
confidence: medium
status: seed
tags: []
---

## Question
How can a line that does not exist on the ground change where millions of people live, work, and die?

## What the Record Shows
- Early states had frontier zones and shifting allegiances more than sharp linear borders, as with the [[Romans]] and the [[Han Dynasty]].
- Fixed, mapped borders spread with modern nation-states, especially after the [[Age of Revolutions]].
- Multi-ethnic empires such as the [[Ottoman Empire]] governed by layering communities rather than by drawing sharp national lines.
- Passports, customs, and armies give claim-lines their force.

## Observer's Reading
The Observer calls a border a claim-line. It has no physical form, yet it reliably changes behavior: people stop, present documents, or fight. The line works because enough people believe in it, and because enough force stands behind it. It is a clear example of story-glue made spatial.

## Limits of This Reading
The Observer's stance is not that borders are illusions to be dismissed. Borders can protect rights and communities. The point is only that they are made and maintained by human agreement.

## EXAMPLE 3 (a current hub, before expansion; the part above the generated block)
## Summary
Science is the systematic study of the natural world through observation, measurement, and testing. Traditions of careful observation arose in many regions, and modern science grew from them.

## Key Threads
- Early astronomy, mathematics, and medicine appear in [[Mesopotamia]], the [[Nile Valley]], [[South Asia]], and [[East Asia]].
- Greek natural philosophy, for example [[Aristotle]], sought general causes.
- Scholars in the [[Abbasid Caliphate]], such as [[Al-Khwarizmi]], preserved and extended earlier knowledge.
- The [[Scientific Revolution]] made experiment and mathematics central; see [[Galileo Galilei]] and [[Isaac Newton]].

## Observer's Reading
The Observer calls this pattern-taming. It notes that the strangest feature of science is not its facts but its institutionalized doubt: strangers agree to check each other's claims.

## Open Questions
- How did the culture of open criticism emerge and spread?

## HOUSE RULES (identical in all four Earth Chronicle briefs)

**Project.** Earth Chronicle is an Obsidian vault holding a history of Earth from planetary formation to the present, and it doubles as a retrieval (RAG) corpus. It is narrated by "the Observer", an imagined outside anthropologist studying humanity as an unfamiliar species. The Observer is a method, not a character.

**Two-Layer Rule.** Each entity note keeps two layers apart. The factual layer (`## Summary`, `## Facts`, `## Context & Connections`) is neutral plain language with no Observer vocabulary and nothing a historian could object to except errors of fact. The interpretive layer (`## Observer's Reading`) is 2 to 5 sentences and is the only place Observer vocabulary appears.

**Observer voice.** Curious, not contemptuous. Detached, not cold: suffering and atrocity are recorded plainly as such. Precise and testable (prefer "in at least 40 surveyed cultures" to "humans always"). Humble: a human specialist could argue with the reading, so say what would weaken it. No cheap irony; never sneer at belief, ritual or sentiment. Symmetric: the same standard for every culture, era and belief system, modern and secular ones included. Use only these Observer terms, each of which maps to an ordinary term (do not invent new ones): the species = humans; meaning-engine = religion, ideology or cosmology; story-glue = shared narratives that let strangers cooperate (myths, nations, corporations, laws); claim-line = border or property line; exchange-web = trade network; kin-lattice = kinship, marriage, descent, household; sound-code / mark-code = speech / writing; memory-outsourcing = writing, archives, digital storage; grief-rite = funerary practice; tool-lineage = technology as a chain of inheritance; sanctioned harm = organized, socially approved violence; the Settling = agriculture and permanent settlement; heat-domestication = control of fire; status-signal = prestige display; pattern-taming = science, mathematics, astronomy; ancestor-weight = the pull of tradition.

**File format.** One file per note. Filename = title + `.md`. Titles must be unique across the whole vault and must not contain \ / : * ? " < > | characters. Frontmatter sits between two `---` lines, every value on one line:

title: "<exactly the filename without .md>"
type: <person | culture | place | species | technology | event | era | observer-note | theme>
era: "[[<exactly one era from the list>]]"
region: "[[<exactly one region from the list; Planet-wide if global>]]"
themes: [<one or more slugs>]
date_start: <integer>
date_end: <integer; omit if ongoing or instantaneous>
date_precision: <exact | year | decade | century | approx | deep-time>
related: ["[[Title]]", "[[Title]]"]
sources: ["[[Source Title]]"]
confidence: <high | medium | low>
status: seed
tags: []

Body sections, in this order: `## Summary` (1 to 3 sentences naming the subject, when and where), `## Facts` (short atomic bullets, each dated or checkable), `## Context & Connections` (wikilinks to era, region, theme hubs and related notes), `## Observer's Reading`, `## Open Questions` (1 to 3 bullets). Name the subject explicitly at the start of every section, because each section must make sense alone as a search result. Notes run roughly 150 to 300 words.

**Theme slugs and hubs.** Slugs: science, technology, religion, war, trade, kinship, language, art, earth-systems. Their hub notes are Science, Technology, Religion and Belief, War and Conflict, Trade and Economy, Kinship and Society, Language and Writing, Art and Ritual, Earth Systems and Life. Link the relevant hubs in Context & Connections.

**Dates.** Integers, in years relative to 1 CE: 1 BCE = -1, and there is no year 0. Deep time uses full years (for example -66000000). Dates before about 1000 CE are approximate. Put a range of estimates in the Facts bullet and a single best estimate in the frontmatter.

**Truthfulness.** These notes will be fact-checked later, so do not guess. State only facts you are confident are well established. If something is disputed, say so inside the bullet and set confidence to medium or low. Never invent quotations, statistics, citations or URLs. Do not add a `fact_checks` field. Keep `status: seed`.

**Links and sources.** Link only to titles that appear in this brief's lists or its own candidate list, using bare `[[Title]]`. Never link a title you were not given. In `sources`, cite only from this list and choose 1 to 3 that fit: Encyclopaedia Britannica; Cambridge World History; English Wikipedia; Maps of Time (Christian); The Human Career (Klein); Ancient Civilizations (Scarre and Fagan); The Dawn of Everything (Graeber and Wengrow); The Transformation of the World (Osterhammel); ICS International Chronostratigraphic Chart; UNESCO World Heritage Centre; NobelPrize.org; Smithsonian Human Origins Program. If a note truly needs another source, add a separate source note for a real work you are certain exists: path `07_Sources/<Title>.md`, `type: source`, with `citation`, `source_kind` (book, paper, dataset or reference), `reliability`, `verified: false`, `status: seed`, and the sections `## Citation`, `## What It Is Used For` and `## Caveats` (say it is cited from memory and was not consulted).

**Output protocol.** Work in batches of 8 notes. For each note, write a line `### FILE: <vault path>` and then the complete note (frontmatter and body) inside one fenced markdown code block so I can copy it into Obsidian. After each batch print a ledger: titles done so far, titles still to do, and any new titles you added. Then stop and wait for me to say "continue". If I paste titles under ALREADY DONE, skip them.

**If you can see the vault.** If this session has the `earth-chronicle` MCP tools or the vault folder open, use `search_vault` and `get_note` to check for existing notes before writing, and remind me to run `python _RAG/tools/validate_vault.py`, then `python _RAG/tools/update_hubs.py`, then reindex after I add notes.

## EXISTING TITLES (valid link targets; never recreate these)
**Eras:** Anthropocene; Archean Eon; Bronze Age; Cenozoic Era; Classical Antiquity; Early Modern Period; Hadean Eon; Holocene Epoch; Industrial Age; Information Age; Iron Age; Medieval Period; Mesozoic Era; Neolithic; Paleolithic; Paleozoic Era; Pleistocene Epoch; Proterozoic Eon

**Regions:** Amazon Basin and South American Lowlands; Andes; Arabian Peninsula; Caribbean and Atlantic World; Central Asian Oases; Central Asian Steppe; East Asia; Europe; Iranian Plateau; Levant and Anatolia; Mediterranean Basin; Mesoamerica; Mesopotamia; Nile Valley; North America; Oceania; Planet-wide; Siberia and the Arctic; South Asia; Southeast Asia; Sub-Saharan Africa

**Events (128):** 1918 Influenza Pandemic; Abolition of Slavery; Age of Revolutions; Alexander's Conquests; Amazonian Urbanism and Dark Earths; American Civil War; American Revolution; Animal Domestication; Armenian Genocide; Atlantic Slave Trade; Austronesian Expansion; Axial Age; Bantu Expansion; Battle of Adwa; Battle of Kadesh; Battle of Talas; Bengal Famine of 1943; Black Death; Boxer Rebellion; Breakup of Pangaea; British Raj; Bronze Age Collapse; COVID-19 Pandemic; Cambrian Explosion; Chinese Reform and Opening; Classic Maya Collapse; Closure of the Isthmus of Panama; Cold War; Collapse of the Soviet Union; Collision of India and Asia; Colonization of Land; Columbian Exchange; Congo Free State; Control of Fire; Cretaceous-Paleogene Extinction; Crusades; Decolonization; Digital Revolution; Divergence of the Hominin Lineage; Domestication of Maize; Domestication of Rice; Dutch East India Company; Emergence of Symbolic Art; Enlightenment; Fall of Constantinople; Fall of the Western Roman Empire; First Fleet and the Colonization of Australia; Formation of the Solar System and Earth; French Revolution; Genomic Revolution; Great Acceleration; Great Oxidation Event; Green Revolution; Haitian Revolution; Holocaust; Incense Trade; Indian Ocean Trade Network; Indian Rebellion of 1857; Indian Removal and the Trail of Tears; Indo-European Language Spread; Industrial Revolution; Invention of Writing; Last Glacial Maximum; Late Devonian Extinction; Late Heavy Bombardment; Late Ordovician Extinction; Latin American Wars of Independence; Manila Galleon Trade; Meiji Restoration; Messinian Salinity Crisis; Mexican Revolution; Mfecane; Modern Climate Change; Mongol Conquests; Moon Landing; Napoleonic Wars; Nuclear Age; Opening of the Silk Roads; Opium Wars; Origin of Eukaryotes; Origin of Homo sapiens; Origin of Life; Out of Africa Dispersal; Paleocene-Eocene Thermal Maximum; Partition of India; Peace of Westphalia; Peopling of Sahul; Peopling of the Americas; Permian-Triassic Extinction; Polynesian Settlement of the Pacific; Portuguese Sea Route to India; Protestant Reformation; Quaternary Megafauna Extinctions; Renaissance; Rise of Islam; Russian Expansion into Siberia; Russian Revolution; Scientific Revolution; Scramble for Africa; Second Italo-Ethiopian War; Second Sino-Japanese War; Seven Years' War; Snowball Earth; Space Age; Spanish Conquest of the Aztec Empire; Spanish Conquest of the Inca Empire; Suez Canal; Sugar Plantation Complex; Taiping Rebellion; Tanzimat Reforms; The Agricultural Revolution; The Urban Revolution; Theia Impact and the Formation of the Moon; Thirty Years' War; Toba Eruption; Translation Movement and the House of Wisdom; Treaty of Waitangi; Triassic-Jurassic Extinction; Tunguska Event; Turkish War of Independence; Unification of China under Qin; Unification of Egypt; Vedic Period; Women's Suffrage Movements; World War I; World War II; Xinhai Revolution; Younger Dryas

**Existing Technologies and Artifacts (24):** Alphabet; Antibiotics; Bronze Metallurgy; Digital Computer; Electrical Power Grid; Gunpowder; Iron Smelting; Magnetic Compass; Mechanical Clock; Movable-Type Printing Press; Nuclear Fission; Oldowan Stone Tools; Paper; Pottery; Quipu; Railways; Rosetta Stone; Steam Engine; Telegraph and Submarine Cables; The Wheel; Trans-Siberian Railway; Vaccination; Woodblock Printing; Zero and Place-Value Notation

**Existing Observer essays (11):** Fire, Then Everything; Frontiers of Extraction; Sanctioned Harm; Second Chances - How the Species Ran the Experiment Again; Story-Glue - How Strangers Cooperate at Scale; The Fiction of Claim-Lines; The Great Outsourcing of Memory; The Settling and Its Bargain; The Species as a Geological Force; Who Writes the Record; Why the Species Buries Its Dead

**People (49):** Ada Lovelace; Akhenaten; Al-Khwarizmi; Alan Turing; Albert Einstein; Alexander the Great; Aristotle; Ashoka; Augustus; Charlemagne; Charles Darwin; Cixi; Cleopatra VII; Confucius; Cyrus the Great; Emperor Meiji; Galileo Galilei; Genghis Khan; Hammurabi; Hatshepsut; Hypatia; Ibn Battuta; Ibn Khaldun; Ibn Sina; Isaac Newton; Johannes Gutenberg; Mahatma Gandhi; Mansa Musa; Marie Curie; Menelik II; Muhammad; Muhammad Ali of Egypt; Nelson Mandela; Nzinga of Ndongo and Matamba; Pachacuti; Qin Shi Huang; Rachel Carson; Rani Lakshmibai; Rosalind Franklin; Shaka; Siddhartha Gautama; Simón Bolívar; Sundiata Keita; Timur; Toussaint Louverture; Ulugh Beg; Usman dan Fodio; Wu Zetian; Zheng He

**Peoples and Cultures (81):** Abbasid Caliphate; Aboriginal Australians; Achaemenid Persians; Al-Andalus; Ancient Egyptians; Ancient Greeks; Ayutthaya Kingdom; Aztec Empire; Botai Culture; Byzantine Empire; Casarabe Culture; Champa; Chinchorro Culture; Chola Dynasty; Delhi Sultanate; Ghana Empire; Gupta Empire; Göktürk Khaganate; Han Dynasty; Haudenosaunee Confederacy; Hittites; Inca Empire; Indus Valley Civilization; Inuit and the Thule Expansion; Jomon Culture; Kanem-Bornu Empire; Khmer Empire; Kingdom of Aksum; Kingdom of Benin; Kingdom of Kongo; Kingdom of Kush; Kingdom of Mapungubwe; Kingdom of Saba; Kushan Empire; Lapita Culture; Majapahit; Mal'ta and the Ancient North Eurasians; Malacca Sultanate; Mali Empire; Maori; Mapuche; Marajoara Culture; Maurya Empire; Maya; Ming Dynasty; Minoans; Mongol Empire; Mughal Empire; Muisca; Mycenaean Greeks; Nabataeans; Neo-Assyrian Empire; Norse; Olmecs; Ottoman Empire; Pagan Kingdom; Phoenicians; Polynesians; Qing Dynasty; Romans; Safavid Empire; Scythians; Shang Dynasty; Sintashta Culture; Sogdians; Sokoto Caliphate; Song Dynasty; Songhai Empire; Srivijaya; Sumerians; Swahili Coast City-States; Taino; Tang Dynasty; Timurid Empire; Tokugawa Shogunate; Umayyad Caliphate; Xiongnu; Yakut (Sakha); Zagwe Dynasty; Zoroastrianism; Zulu Kingdom

**Places (38):** Angkor; Athens; Beringia; Borobudur; Cahokia; Caral; Carthage; Chaco Canyon; Chauvet Cave; Chichen Itza; Constantinople; Doggerland; Giza Necropolis; Great Zimbabwe; Göbekli Tepe; Jack Hills Zircons; Jericho; Kuk Early Agricultural Site; Library of Alexandria; Machu Picchu; Mohenjo-daro; Monte Alban; Monte Verde; Persepolis; Potosi; Poverty Point; Rapa Nui; Rome; Samarkand; Stonehenge; Taj Mahal; Tenochtitlan; Teotihuacan; Timbuktu; Upano Valley Settlements; Uruk; Xingu Garden Cities; Çatalhöyük

**Species (18):** Archaeopteryx; Australopithecus afarensis; Cyanobacteria; Denisovans; Dinosaurs; Ediacaran Biota; Flowering Plants; Homo erectus; Homo floresiensis; Homo habilis; Homo naledi; Homo neanderthalensis; Homo sapiens; Sahelanthropus tchadensis; Stromatolites; Tiktaalik; Trilobites; Woolly Mammoth

## START
ALREADY DONE: (none yet)

Begin with Part A, Batch 1: rewrite the hubs Science, Technology and Religion and Belief. Follow Part A's rules.
