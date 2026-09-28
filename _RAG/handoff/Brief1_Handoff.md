# Handoff: Earth Chronicle Brief 1 (People + Peoples & Cultures)

Prepared 2026-09-26; ledger updated after People Batch 6 (2026-09-26 14:15). Section 1 is the message to paste into the new chat. The rest is reference the new chat will read from this file.

**Batch 6 and Batch 7 are DONE.** Batch 7 (2026-09-27, ~14:40): Frida Kahlo, Kate Sheppard, Sacagawea, Ho Chi Minh, Sukarno, Kamehameha I, Vitus Bering, Sun Yat-sen. Validated at 0 errors, hubs and index already current (another session had run them). **Next is Batch 8.**

**IMPORTANT — a large uncoordinated parallel expansion happened between Batch 6 and Batch 7, now audited and folded in (user confirmed 2026-09-27).** Two other bursts of activity (2026-09-27 08:31-10:07 and 14:17-14:32) added 88 more files to `03_Entities/People/`. About 38 (Vincent van Gogh, Claude Monet, Frank Lloyd Wright, Gustav Klimt, Hilma af Klint, Georges Méliès, Lumière Brothers, Leo Tolstoy, Jane Austen, and more) are the tracked [[art-talk-integration]] pass, not Brief 1's. The other 37, from the 08:31-10:07 burst, are unexplained (not the user's usual four briefs, not Art-Talk) but the user confirmed on 2026-09-27 they are the user's own and should count toward Brief 1's quotas:

Peter the Great (M, Europe), Gorgo (F, Mediterranean Basin), Ambiorix (M, Europe), Teddy Roosevelt (M, North America), Pedro II (M, Amazon Basin and South American Lowlands), Suleiman the Magnificent (M, Levant and Anatolia — **collides with section 2.2**), Harald Hardrada (M, Europe), Queen Victoria (F, Europe), Trajan (M, Mediterranean Basin), Tamar of Georgia (F, Levant and Anatolia), Robert the Bruce (M, Europe), Philip II (M, Europe), Pericles (M, Mediterranean Basin — **collides**), Matthias Corvinus (M, Europe), Ludwig II (M, Europe), João III (M, Europe), Jadwiga (F, Europe), Frederick Barbarossa (M, Europe), Eleanor of Aquitaine (F, Europe — **collides**), Catherine de' Medici (F, Europe), Basil II (M, Mediterranean Basin), Dido (F, Mediterranean Basin), Gilgamesh (M, Mesopotamia), Wilfrid Laurier (M, North America), John Curtin (M, Oceania), Yongle Emperor (M, East Asia), Hojo Tokimune (M, East Asia), Tokugawa Ieyasu (M, East Asia — **collides**), Seondeok (F, East Asia), Amanitore (F, Nile Valley), Lautaro (M, Andes), Montezuma II (M, Mesoamerica — **same person as the candidate list's "Moctezuma II"; do not also write that spelling**), Lady Six Sky (F, Mesoamerica), Kupe (M, Oceania), Ba Trieu (F, Southeast Asia), Gitarja (F, Southeast Asia), Chandragupta Maurya (M, South Asia).

That is 37 people, 12 women, 25 men; 17 in Europe or the Mediterranean Basin (12 Europe + 5 Mediterranean Basin; Levant and Anatolia kept separate as the brief's own list does). **Confirmed collisions, drop from section 2.2 and any batch plan: Eleanor of Aquitaine, Pericles, Suleiman the Magnificent, Tokugawa Ieyasu, and do not write "Moctezuma II" (Montezuma II already covers him).**

This file lives in `_RAG/handoff/`, which the vault validator and indexer skip. The original brief is saved next to it as `EarthChronicle_Brief1_People_and_Peoples-Cultures.md`.

---

## 0. Where things stand

Brief 1 asks for about +100 People (`03_Entities/People/`, `type: person`) and about +100 Peoples & Cultures (`03_Entities/Peoples-Cultures/`, `type: culture`), all with `date_start` of -11,700 or later. Anything earlier belongs to Brief 4 (Early Eras).

Notes are written straight into the vault in batches of 8. After each batch: validate, `update_hubs.py`, validate again, reindex, then stop and wait for the user to say "continue".

| | Start | Now | Target |
|---|---|---|---|
| People, Brief 1 quota (56 of its own + 37 folded-in, 38 Art-Talk excluded) | 49 | **142** | about 149 — **nearly done** |
| People (all files on disk, includes Art-Talk's 38) | 49 | **190** | n/a |
| Peoples & Cultures | 81 | 81 (**not started at all**) | about 181 |
| Women toward the quota | | **40** (28 Brief 1 + 12 folded-in) | at least 35 — **met** |
| Europe/Mediterranean toward the cap | | **19** (2 Brief 1 + 17 folded-in) | at most 20 — **almost full, 1 slot left** |

**Batch 8 is DONE (2026-09-27):** Indira Gandhi, Li Qingzhao, Queen Suriyothai, Eleanor Roosevelt, Akbar, Sun Tzu, Xuanzang, Sunni Ali. 0 Europe, 4 women (Indira Gandhi, Li Qingzhao, Queen Suriyothai, Eleanor Roosevelt). Validated at 0 errors (two notes, Queen Suriyothai and Sunni Ali, initially set `date_end` with no `date_start` for a death-year-only figure — wrong; the convention is `date_start` = the known year, `date_end` omitted, as with Ajuricaba), hubs updated, reindexed (the MCP `reindex` tool errored twice before succeeding on a third call — a concurrent session may have been reindexing at the same time; retry if it happens again).

**Updated totals: People quota 150 of about 149 — done. Women 44 of 35 — done. Europe/Mediterranean 19 of 20 — 1 slot left. Peoples & Cultures 0 of about 100 — not started.**

**The People phase for Brief 1 is complete.** Do not plan further People batches — the total and women targets are both met and Europe/Mediterranean has almost no room left. Re-verify the "existing People" list before ever writing another person note, since other sessions continue to add to this folder.

**Peoples & Cultures Batch 1 is DONE (2026-09-27):** all 11 belief traditions minus 3, i.e. the first 8 of section 6.3's plan — Judaism, Christianity, Islam, Buddhism, Hinduism, Jainism, Sikhism, Confucianism. Bodies 330-379 words by awk (Sikhism trimmed from 379). Two-layer rule and the "describe beliefs as held by adherents, never rank, never adjudicate truth claims" rule were followed throughout; each Reading states what a specialist could argue that would weaken it. Validated at 0 errors from these 8 notes (the vault's other errors are unrelated: `.claude/agents/chronicle-rewriter.md` and the new `_Rewrite/` project folder are not part of Brief 1 or the vault's note schema, same pattern as Art-Talk-main before it was added to `SKIP_DIRS` — leave them alone, they are someone else's in-progress work, not yours to fix). Hubs updated, reindexed. **Peoples & Cultures Batch 2 is DONE (2026-09-27/28):** Daoism, Shinto, Manichaeism (completing **all 11 required belief traditions**) plus Celts, Franks (Europe), Ancestral Puebloans, Cherokee (North America), Kalinago (Caribbean). Bodies 313-351 words by awk after one trim pass. Validated at 0 errors, hubs current. **The `reindex` step is NOT done for this batch**: the `earth-chronicle` MCP server timed out on connect (CONNECT_TIMEOUT), so run `reindex` first thing next session (it is a deferred tool: `ToolSearch select:mcp__earth-chronicle__reindex`; it may need a retry or two, and it has previously errored once or twice before succeeding). Cultures on disk: 97 (81 original + 16 new), so about 84 more are needed to reach about 181.

**Two links were left as plain text on purpose** because the targets do not exist yet: "Holy Roman Empire" (in Franks) and "Sasanian Empire" (in Manichaeism). Both are on the candidate list; when either is written, wrap the mention in `[[ ]]` (link-pass list below). Other plain-text mentions to wrap later: Buddhism/Islam/Christianity/Confucianism/Daoism now exist, so the section 6.4 link pass can start for them (Ashoka, Siddhartha Gautama, Wu Zetian: Buddhism; Muhammad: Islam; Ezana of Aksum: Christianity; Confucius: Confucianism; Laozi: Daoism; Sequoyah and Cherokee note: already linked; Charlemagne: Franks; Sitting Bull: Lakota still pending).

**Batch 3 (next): work the section 6.3 list, thinnest regions first.** Europe now has 3 culture notes (Celts, Franks + the original Norse/Romans etc.; Europe needs at least 12 new in total, so 10 more), North America 3 new needed, Oceania, Southeast Asia, Central Asia and Siberia, Sub-Saharan Africa, East Asia, South Asia, Levant/Mesopotamia and the Americas each still need at least 3. Suggested Batch 3: Etruscans, Yamnaya Culture, Anglo-Saxons, Lakota (North America), Mississippian Culture (North America), Garifuna (Caribbean), Hawaiian Kingdom (Oceania), Funan (Southeast Asia). Check title availability with `find` first, since other sessions are still active in this vault.

Validator state after Batch 6: **0 errors, 1 old warning about sources**, no filtering needed any more. The fact-check coverage line is falling (377 of 545) because new notes carry no `fact_checks`. That is expected.

**Not Brief 1's, but it changes the ledger:** at 14:04 to 14:05 on 2026-09-26 another session (the Art-Talk integration) added 9 artist People notes: Murasaki Shikibu (W), Leonardo da Vinci, Hieronymus Bosch, Jan van Eyck, Giotto (Europe), Behzad, Shen Zhou, Sesshū Tōyō and Amir Khusrau. They carry `art_talk:` and `tags: [artist, ...]` and cite `[[Art-Talk (Artist Profiles)]]`. It also added Art-Talk tags and a source to `Rumi.md`. So there are now 106 files in `03_Entities/People/` (97 by Brief 1's count plus these 9). **Murasaki Shikibu and Leonardo da Vinci are no longer available as candidates.** Whether these 8 count toward Brief 1's 35 women and 20 Europe cap is the user's call; the safe reading is to count them (that makes women 26 and Europe 6 so far).

`Art-Talk-main/` itself is now in `SKIP_DIRS` in `_RAG/vault.py`, so the earlier 56 validator errors and the false `Rumi` orphan are gone.

---

## 1. Message to paste

### A. New chat that can see the vault (Claude Code opened in the vault folder)

```text
Continue Earth Chronicle Brief 1 (People, then Peoples & Cultures). Read
_RAG/handoff/Brief1_Handoff.md first, then read two recent notes for house
style (03_Entities/People/Saladin.md and 03_Entities/People/Rumi.md) and the
two brief examples in the vault (03_Entities/People/Nzinga of Ndongo and
Matamba.md and 03_Entities/Peoples-Cultures/Lapita Culture.md).
Also read your memory note earth-chronicle-expansion-briefs.
Then write People Batch 6 (the eight titles in section 6.1 of the handoff)
directly into 03_Entities/People/, run the batch procedure in section 3, and
stop for my "continue".
```

### B. New chat with no vault access

Paste the original brief (`EarthChronicle_Brief1_People_and_Peoples-Cultures.md`), then send this line in place of the brief's `ALREADY DONE: (none yet)`:

```text
ALREADY DONE: Liliuokalani, Pakal the Great, Malinche, Khadija bint Khuwaylid, Zenobia, Jayavarman VII, Chico Mendes, Knud Rasmussen, Enheduanna, Amanirenas, Nefertiti, Trưng Sisters, Yaa Asantewaa, Truganini, Razia Sultana, Savitribai Phule, Saladin, Yermak Timofeyevich, Ajuricaba, Piye, Darius I, Sappho, Laozi, Fu Hao, Tomyris, Anacaona, Túpac Amaru II, Sequoyah, Harriet Tubman, Sitting Bull, Wangari Maathai, Al-Biruni, Tupaia, Ashurbanipal, Ban Zhao, Nur Jahan, Queen Amina of Zazzau, Ezana of Aksum, Rumi, José Rizal, Aisha bint Abi Bakr, Sor Juana Inés de la Cruz, Mirabai, Funmilayo Ransome-Kuti, Nezahualcoyotl, Ramesses II, Attila, José Martí, Murasaki Shikibu, Leonardo da Vinci, Hieronymus Bosch, Jan van Eyck, Giotto, Behzad, Shen Zhou, Sesshū Tōyō, Amir Khusrau
Women so far: 26. Europe/Mediterranean so far: 6 (Sappho, Attila, Leonardo da Vinci, Hieronymus Bosch, Jan van Eyck, Giotto). Start with People Batch 7 (section 6.1 titles), then follow the brief's output protocol. Link only to titles in the brief's EXISTING TITLES list or the notes in this ledger.
```

In that mode the user copies the fenced notes into Obsidian and runs the three commands in section 3 afterwards.

---

## 2. Ledger

### 2.1 People done (48, batches 1 to 6)

| Batch | Titles (W = woman) |
|---|---|
| 1 | Liliuokalani (W), Pakal the Great, Malinche (W), Khadija bint Khuwaylid (W), Zenobia (W), Jayavarman VII, Chico Mendes, Knud Rasmussen |
| 2 | Enheduanna (W), Amanirenas (W), Nefertiti (W), Trưng Sisters (W), Yaa Asantewaa (W), Truganini (W), Razia Sultana (W), Savitribai Phule (W) |
| 3 | Saladin, Yermak Timofeyevich, Ajuricaba, Piye, Darius I, Sappho (W), Laozi, Fu Hao (W) |
| 4 | Tomyris (W), Anacaona (W), Túpac Amaru II, Sequoyah, Harriet Tubman (W), Sitting Bull, Wangari Maathai (W), Al-Biruni |
| 5 | Tupaia, Ashurbanipal, Ban Zhao (W), Nur Jahan (W), Queen Amina of Zazzau (W), Ezana of Aksum, Rumi, José Rizal |
| 6 | Aisha bint Abi Bakr (W, Arabian Peninsula, Medieval), Sor Juana Inés de la Cruz (W, Mesoamerica, Early Modern), Mirabai (W, South Asia, Early Modern, low), Funmilayo Ransome-Kuti (W, Sub-Saharan Africa, Information Age), Nezahualcoyotl (Mesoamerica, Medieval), Ramesses II (Nile Valley, Bronze Age), Attila (Europe, Classical Antiquity), José Martí (Caribbean, Industrial) |

By era of the new 48: Bronze Age 4, Iron Age 6, Classical Antiquity 6, Medieval 9, Early Modern 10, Industrial 10, Information Age 3. **Information Age and Bronze Age are still the thinnest; favor them.**

Batch 6 bodies came out at 340 to 361 words by the awk count (target 300 to 330), so trim harder in Batch 7 (cut a Facts bullet before writing, and keep the Reading to three short sentences).

Region coverage: every region that had zero People at the start now has at least 2.

### 2.2 People still to choose from — **SUPERSEDED (2026-09-27): the People phase is complete (150 of about 149). This list still names people who have since been written (Akbar, Sun Tzu, Xuanzang, Sunni Ali, Sun Yat-sen, Ho Chi Minh, Sukarno, Kamehameha I, Vitus Bering, Indira Gandhi, Li Qingzhao, Queen Suriyothai, Eleanor Roosevelt, Frida Kahlo, Kate Sheppard, Sacagawea and others) and must not be used as a candidate pool. Before writing any further person, re-derive availability with `find`.** (138 candidates at the time: brief's list minus done, minus Murasaki Shikibu and Leonardo da Vinci, which the Art-Talk session wrote)

- **Nile Valley:** Narmer, Imhotep, Khufu, Tutankhamun
- **Mesopotamia and Iranian Plateau:** Sargon of Akkad, Nebuchadnezzar II, Xerxes I, Zoroaster, Mani, Shapur I, Omar Khayyam, Ferdowsi, Shah Abbas I, Mohammad Mosaddegh
- **Levant, Anatolia, Arabian Peninsula:** Suppiluliuma I, Suleiman the Magnificent, Ibn Saud, Harun al-Rashid, Ibn al-Haytham
- **Central Asian Steppe and Oases:** Modu Chanyu, Bumin Qaghan, Babur
- **South Asia:** Chanakya, Kalidasa, Aryabhata, Harsha, Akbar, Shah Jahan, Aurangzeb, Tipu Sultan, Guru Nanak, Kabir, Rajaraja Chola I, Srinivasa Ramanujan, Rabindranath Tagore, B. R. Ambedkar, Jawaharlal Nehru, Muhammad Ali Jinnah, Indira Gandhi (W)
- **Southeast Asia:** Suryavarman II, Gajah Mada, Hayam Wuruk, Anawrahta, Ramkhamhaeng, Naresuan, Queen Suriyothai (W), Sukarno, Ho Chi Minh, Aung San
- **East Asia:** Sun Tzu, Sima Qian, Emperor Wu of Han, Cai Lun, Xuanzang, Li Bai, Du Fu, Kublai Khan, Hongwu Emperor, Kangxi Emperor, Sun Yat-sen, Mao Zedong, Deng Xiaoping, Prince Shōtoku, Oda Nobunaga, Tokugawa Ieyasu, Sejong the Great, Yi Sun-sin, Li Qingzhao (W), Zhu Xi, Duke of Zhou
- **Sub-Saharan Africa:** Lalibela, Sunni Ali, Askia Muhammad, Moshoeshoe I, Samori Ture, Haile Selassie, Olaudah Equiano, Kwame Nkrumah, Patrice Lumumba, Steve Biko, Chinua Achebe, Thomas Sankara
- **Europe and Mediterranean (cap 20 in total; 2 used by Brief 1, 6 if the Art-Talk artists count):** Pericles, Socrates, Plato, Herodotus, Hannibal, Julius Caesar, Constantine the Great, Justinian I, Theodora (W), Augustine of Hippo, Hildegard of Bingen (W), Eleanor of Aquitaine (W), Thomas Aquinas, Dante Alighieri, Nicolaus Copernicus, Martin Luther, Elizabeth I (W), Catherine the Great (W), Napoleon Bonaparte, Voltaire, Mary Wollstonecraft (W), Karl Marx, Louis Pasteur, Florence Nightingale (W), Emmeline Pankhurst (W), Sigmund Freud, Vladimir Lenin, Winston Churchill, Simone de Beauvoir (W), Ötzi the Iceman
- **Mesoamerica and Andes:** Moctezuma II, Cuauhtémoc, Atahualpa
- **North America:** Tecumseh, Frederick Douglass, Abraham Lincoln, Martin Luther King Jr., Eleanor Roosevelt (W), Crazy Horse, Sacagawea (W)
- **Caribbean, South America, Amazon:** Hatuey, Jean-Jacques Dessalines, Marcus Garvey, José de San Martín, Benito Juárez, Emiliano Zapata, Frida Kahlo (W)
- **Oceania:** Kamehameha I, Te Rauparaha, Hone Heke, Pemulwuy, Eddie Mabo, James Cook, Kate Sheppard (W)
- **Siberia and the Arctic:** Vitus Bering, Semyon Dezhnev

Women still available: 7 outside Europe (Indira Gandhi, Queen Suriyothai, Li Qingzhao, Eleanor Roosevelt, Sacagawea, Frida Kahlo, Kate Sheppard) and 9 in Europe. Women so far are 25 by Brief 1's count and 26 counting Murasaki Shikibu from the Art-Talk session, so 9 or 10 more are needed; all 7 plus 2 or 3 from Europe reach 35. The brief allows adding others if a gap remains.

### 2.3 Peoples & Cultures candidate pool (147 at the start; **STALE as a done-list: 16 are now written (the 11 belief traditions, Celts, Franks, Ancestral Puebloans, Cherokee, Kalinago); the live batch plan and ledger are in section 9 below**)

- **Europe (need at least 12):** Celts, Etruscans, Franks, Visigothic Kingdom, Huns, Early Slavs, Anglo-Saxons, Normans, Kievan Rus, Holy Roman Empire, Venetian Republic, Polish-Lithuanian Commonwealth, Habsburg Monarchy, Dutch Republic, Sami, Basques, Beaker Culture, Yamnaya Culture, Corded Ware Culture, Linear Pottery Culture, Cucuteni-Trypillia Culture, Hallstatt and La Tène Cultures, British Empire, Spanish Empire, Portuguese Empire, Russian Empire, Soviet Union
- **Levant, Anatolia, Mesopotamia, Iranian Plateau:** Akkadian Empire, Babylonian Empire, Elamites, Urartu, Lydians, Kingdom of Israel and Judah, Carthaginian Empire, Seleucid Empire, Parthian Empire, Sasanian Empire, Seljuk Empire, Ayyubid Sultanate, Mamluk Sultanate, Fatimid Caliphate, Rashidun Caliphate, Ilkhanate, Kingdom of Himyar, Halaf and Ubaid Cultures
- **Central Asian Steppe, Oases, Siberia:** Sarmatians, Yuezhi, Xianbei, Avars, Khazar Khaganate, Kipchaks, Uyghur Khaganate, Golden Horde, Kazakh Khanate, Kara-Khitan Khanate, Evenki, Chukchi, Nenets, Yupik and Unangan, Dorset Culture
- **East Asia:** Zhou Dynasty, Sui Dynasty, Yuan Dynasty, Liao Dynasty, Jin Dynasty, Western Xia, Goguryeo, Silla, Joseon Dynasty, Yamato Court, Ainu, Kingdom of Ryukyu, Yayoi Culture, Yangshao Culture, Liangzhu Culture, Sanxingdui Culture
- **South Asia:** Magadha, Gandhara, Pallava Dynasty, Pala Empire, Vijayanagara Empire, Maratha Empire, Sikh Empire, Anuradhapura Kingdom, Tibetan Empire
- **Southeast Asia:** Funan, Dvaravati, Đại Việt, Sukhothai Kingdom, Lan Xang, Sultanate of Aceh, Bugis, Dong Son Culture, Kingdom of Mataram
- **Sub-Saharan Africa and Nile Valley:** Nok Culture, Igbo-Ukwu Culture, Oyo Empire, Asante Empire, Kingdom of Dahomey, Buganda, Luba Empire, Khoisan Peoples, Ptolemaic Kingdom, Berbers, Almoravid Dynasty, Kingdom of Makuria, Ethiopian Empire, Hausa City-States
- **Oceania:** Tui Tonga Empire, Hawaiian Kingdom, Torres Strait Islanders, Moriori, Chamorro, Papuan Highlanders
- **Americas:** Zapotec Civilization, Mixtec, Toltec, Purépecha, Chavín Culture, Moche Culture, Nazca Culture, Wari Empire, Tiwanaku, Chimú, Tupi-Guarani, Yanomami, Ancestral Puebloans, Mississippian Culture, Hopewell Tradition, Lakota, Cherokee, Comanche, Navajo, Kalinago, Garifuna, Maroon Communities
- **Belief traditions (all 11 required):** Judaism, Christianity, Islam, Buddhism, Hinduism, Jainism, Sikhism, Confucianism, Daoism, Shinto, Manichaeism

To re-derive what is left at any time, a candidate is done if a file with that title exists anywhere in the vault: `find . -iname "Title.md" -not -path "./_RAG/*"`.

---

## 3. Batch procedure (run after every batch of 8)

Run from the vault root, `C:\Users\utopi\OneDrive\Desktop\Earth _WorldBuilding`. The folder name has a space, so quote paths. The shell is Git Bash on Windows.

1. Before writing: check each title is free vault-wide (titles must be unique across all note types).
2. Write the 8 notes with the Write tool into `03_Entities/People/` (or `03_Entities/Peoples-Cultures/`). Filename is the title plus `.md`, and the `title:` field must equal the filename without `.md`. Diacritics are fine (Trưng, Túpac, José).
3. Word count check. The counter used so far treats the body as everything after the second `---`, headings and link markup included:
   `awk 'BEGIN{c=0} /^---$/{c++; next} c>=2{print}' "03_Entities/People/NAME.md" | wc -w`
   Aim for about 300 to 330. The brief says 150 to 300, but the required Facts content and the "what would weaken this" clause push it up. First drafts were 350 to 420, so trim.
4. `_RAG/.venv/Scripts/python.exe _RAG/tools/validate_vault.py 2>&1 | grep -v Art-Talk-main` (expect 0 errors once the `Art-Talk-main/` noise is filtered out; new notes show orphan warnings until step 5).
5. `_RAG/.venv/Scripts/python.exe _RAG/tools/update_hubs.py` (regenerates era, region, theme hubs and timelines; idempotent).
6. Validate again (expect 0 errors, orphan warnings gone).
7. Reindex with the MCP tool `reindex` of the `earth-chronicle` server. In Claude Code it is a deferred tool, so load it first with ToolSearch `select:mcp__earth-chronicle__reindex,mcp__earth-chronicle__search_vault,mcp__earth-chronicle__get_note`.
8. Report a table (title, region, era, confidence), what was verified, what is uncertain, the running tallies (People count, women, Europe cap), and propose the next batch. Then stop for "continue".

Also update the memory note `earth-chronicle-expansion-briefs` (the "Brief 1 in progress" paragraph) after each batch.

---

## 4. Decisions already taken (stay consistent)

- **Links.** Link only to titles that exist in the vault right now. Mention a not-yet-written candidate in plain text (no brackets). This keeps validation at 0 errors. A link pass comes later (section 6.3).
- **Era and region.** `era` is one of the 18 top-level eras and `region` one of the 21 regions (lists in section 5). Use the era of the main activity. Do not use the geological period notes that Brief 4 is adding (Cambrian Period, Quaternary Period and so on) as an era for People or Cultures.
- **Unknown birth years.** When the birth year is unknown (Amanirenas, Trưng Sisters, Piye, Fu Hao, Queen Amina of Zazzau), `date_start` and `date_end` mark the reign or the revolt, and the Summary and Facts say so. For Ajuricaba only the death year (1727) is used, with `date_end` omitted and confidence low.
- **Legendary or contested figures** (Tomyris, Laozi, Queen Amina, Malinche, Ajuricaba): the Facts say "traditional" where it applies, `confidence: low`, and Open Questions ask what would separate person from narrative.
- **Verify shaky facts online before writing.** WebSearch and WebFetch were used for Ajuricaba, Yermak, Fu Hao, Piye, Anacaona, Sequoyah, Wangari Maathai, Tomyris, Tupaia, Ezana, Ban Zhao and Queen Amina. Do the same for anything thin or disputed. Never invent dates, quotations, numbers, or citations.
- **Controversy is stated plainly**, including harm done and disputed claims (Wangari Maathai's 2004 HIV remarks: reported, she denied saying it and said she did not hold the belief; the Truganini "last Tasmanian" label rejected by Tasmanian Aboriginal people; Saladin's 1187 ransom terms including those enslaved).
- **Sources** are 1 to 3 from the brief's list, usually Encyclopaedia Britannica plus English Wikipedia (add NobelPrize.org for Nobel laureates, UNESCO World Heritage Centre for sites).
- **Observer's Reading** is 3 to 5 sentences, uses only the approved Observer terms, and ends with what would weaken the reading.
- **Do not add a `fact_checks` field.** Keep `status: seed`.

---

## 5. House rules digest (full text is in the original brief)

**Frontmatter** (every value on one line, between two `---` lines):
`title`, `type: person|culture`, `era: "[[X]]"`, `region: "[[X]]"`, `themes: [slugs]`, `date_start: integer`, `date_end: integer` (omit if none), `date_precision: exact|year|decade|century|approx|deep-time`, `related: ["[[Title]]"]`, `sources: ["[[Source]]"]`, `confidence: high|medium|low`, `status: seed`, `tags: []`.

**Sections in order:** `## Summary` (1 to 3 sentences naming subject, when, where), `## Facts` (short dated or checkable bullets), `## Context & Connections` (wikilinks to era, region, theme hubs and related notes), `## Observer's Reading`, `## Open Questions` (1 to 3 bullets). Name the subject explicitly in every section.

**Two-layer rule:** Summary, Facts and Context are neutral plain language with no Observer vocabulary. Only the Reading uses it.

**Observer terms (use only these):** the species = humans; meaning-engine = religion, ideology or cosmology; story-glue = shared narratives; claim-line = border or property line; exchange-web = trade network; kin-lattice = kinship and descent; sound-code / mark-code = speech / writing; memory-outsourcing = writing, archives; grief-rite = funerary practice; tool-lineage = technology as inheritance; sanctioned harm = organized approved violence; the Settling = agriculture; heat-domestication = fire; status-signal = prestige display; pattern-taming = science; ancestor-weight = pull of tradition. Curious, not contemptuous; the same standard for every culture, modern and secular ones included; never sneer at belief.

**Themes:** science, technology, religion, war, trade, kinship, language, art, earth-systems. Hubs: Science; Technology; Religion and Belief; War and Conflict; Trade and Economy; Kinship and Society; Language and Writing; Art and Ritual; Earth Systems and Life.

**Eras (top-level, with bounds):** Neolithic -9600 to -3300; Bronze Age -3300 to -1200; Iron Age -1200 to -500; Classical Antiquity -500 to 500; Medieval Period 500 to 1500; Early Modern Period 1500 to 1800; Industrial Age 1760 to 1945; Information Age 1945 on. Dates are integers relative to 1 CE (1 BCE = -1, no year 0).

**Regions:** Amazon Basin and South American Lowlands; Andes; Arabian Peninsula; Caribbean and Atlantic World; Central Asian Oases; Central Asian Steppe; East Asia; Europe; Iranian Plateau; Levant and Anatolia; Mediterranean Basin; Mesoamerica; Mesopotamia; Nile Valley; North America; Oceania; Planet-wide; Siberia and the Arctic; South Asia; Southeast Asia; Sub-Saharan Africa. (Greek and Roman subjects use Mediterranean Basin, as the existing notes do.)

**Allowed sources:** Encyclopaedia Britannica; Cambridge World History; English Wikipedia; Maps of Time (Christian); The Human Career (Klein); Ancient Civilizations (Scarre and Fagan); The Dawn of Everything (Graeber and Wengrow); The Transformation of the World (Osterhammel); ICS International Chronostratigraphic Chart; UNESCO World Heritage Centre; NobelPrize.org; Smithsonian Human Origins Program. Confirm the source note exists in `07_Sources/` before citing it.

**Link targets to find:** events `ls 03_Entities/Events`, places `ls 03_Entities/Places`, technologies `ls 03_Entities/Artifacts-Technologies`, cultures `ls 03_Entities/Peoples-Cultures`, people `ls 03_Entities/People`.

**Culture notes.** Facts cover geography, subsistence and economy, political organization, material culture, key events, decline or transformation. Reading angles: how the group held strangers together, marked claim-lines, treated its dead, and what survives. Polities (empires, dynasties, city-state networks) count as cultures. `date_start` and `date_end` are the approximate start and end of florescence.

**Belief traditions** (11 notes, one `culture` each). Describe beliefs as held by adherents, never rank, never adjudicate truth claims, and use the same skeleton for all 11. Facts: origins, founding texts or figures, main branches, rough adherent numbers with a date, historical spread. Read the existing `Zoroastrianism` note for the pattern. Suggested placement: Judaism and Christianity in Levant and Anatolia; Islam in Arabian Peninsula; Buddhism, Hinduism, Jainism, Sikhism in South Asia; Confucianism, Daoism, Shinto in East Asia; Manichaeism in Mesopotamia. Use century precision for origins, low or medium confidence where founding dates are traditional, and omit `date_end` for living traditions.

---

## 6. Plan

### 6.1 People Batches 7 to 9 (concrete; Batch 6 done, plan revised after the Art-Talk additions)

Constraint check: women reach 35 by the end of Batch 9; Europe stays far under the cap; every batch touches at least five regions.

| Batch | Titles | Women | Notes |
|---|---|---|---|
| 6 | DONE (see 2.1) | 4 (total 25) | |
| 7 | DONE. Frida Kahlo (W), Kate Sheppard (W), Sacagawea (W), Ho Chi Minh, Sukarno, Kamehameha I, Vitus Bering, Sun Yat-sen | 3 (total 28) | All 8 verified online before writing. Sacagawea's death date and origin are genuinely disputed and stated as such. |
| 8 | Indira Gandhi (W), Li Qingzhao (W), Queen Suriyothai (W), Eleanor Roosevelt (W), Akbar, Sun Tzu, Xuanzang, Sunni Ali | 4 (total 32; 33 counting Murasaki) | Sun Tzu: traditional, confidence low. Queen Suriyothai: birth unknown, use the reign convention. |
| 9 | Theodora (W), Hildegard of Bingen (W), Pericles, Julius Caesar, Justinian I, Sargon of Akkad, Xerxes I, Narmer | 2 (total 34; 35 counting Murasaki) | First planned Europe batch (Europe total about 10 of 20 with Sappho, Attila and the four Art-Talk artists). Narmer: contested identity, confidence low. |

### 6.2 People Batches 10 to 13 (pools, choose about 24 to reach about 100)

- Favor **Information Age** and **Bronze Age** subjects: Mao Zedong, Deng Xiaoping, Jawaharlal Nehru, Muhammad Ali Jinnah, B. R. Ambedkar, Aung San, Kwame Nkrumah, Patrice Lumumba, Steve Biko, Chinua Achebe, Thomas Sankara, Martin Luther King Jr., Eddie Mabo, Mohammad Mosaddegh, Ibn Saud, Khufu, Imhotep, Tutankhamun, Suppiluliuma I.
- Fill remaining regions: Sun Yat-sen, Sima Qian, Kublai Khan, Hongwu Emperor, Sejong the Great, Prince Shōtoku (Japan has only Emperor Meiji), Suleiman the Magnificent, Babur, Haile Selassie, Askia Muhammad, Frederick Douglass, Atahualpa, Moctezuma II, Dessalines, Marcus Garvey, Te Rauparaha, Pemulwuy, Semyon Dezhnev.
- Europe (up to 13 more): prefer Hannibal, Constantine the Great, Augustine of Hippo, Eleanor of Aquitaine, Leonardo da Vinci, Nicolaus Copernicus, Martin Luther, Elizabeth I, Mary Wollstonecraft, Napoleon Bonaparte, Karl Marx, Florence Nightingale, Simone de Beauvoir. Skip Ötzi unless a gap remains (no named historical person).
- Stop at about 100 new People (the last batch can be shorter than 8).

### 6.3 Peoples & Cultures (about +100, about 13 batches)

Rules: at least 3 new notes for every region, at least 12 for Europe, all 11 belief traditions. Suggested order:

1. **Belief traditions first** (C1 and part of C2), written in one sitting for symmetry. Seven existing People notes (Ashoka, Siddhartha Gautama, Wu Zetian, Confucius, Ezana of Aksum, Laozi, Muhammad) already mention Buddhism, Islam, Christianity, Confucianism or Daoism in plain text, so this also unlocks links.
2. Regions with the fewest existing cultures (Europe, North America, Caribbean have one each), then Oceania, Southeast Asia, Central Asia and Siberia, Sub-Saharan Africa, East Asia, South Asia, Levant and Mesopotamia, the Americas.
3. Keep Europe at 12 to 15, not all 27.

### 6.4 Link pass (do after Cultures exist)

Plain-text mentions in existing notes that should become `[[links]]` once the target is written:

- Akhenaten, Nefertiti: Tutankhamun
- Aristotle: Plato
- Attila: Huns (plain-text, once the culture exists)
- Battle of Kadesh, Hittites, Karnak: Ramesses II (now written; wrap the plain-text mentions)
- Ashoka, Siddhartha Gautama, Wu Zetian: Buddhism
- Augustus, Cleopatra VII: Julius Caesar
- Charlemagne: Franks
- Cleopatra VII: Ptolemaic Kingdom
- Confucius: Emperor Wu of Han, Confucianism
- Darius I: Xerxes I
- Enheduanna: Sargon of Akkad
- Ezana of Aksum: Christianity
- Laozi: Sima Qian, Daoism
- Malinche: Moctezuma II
- Muhammad: Islam
- Nur Jahan: Shah Jahan
- Saladin: Fatimid Caliphate
- Sequoyah: Cherokee
- Simón Bolívar: José de San Martín
- Sitting Bull: Lakota
- Timur: Golden Horde
- Tomyris: Herodotus
- Toussaint Louverture: Jean-Jacques Dessalines
- Tupaia: James Cook

Re-run a scan for new ones before the pass, since later batches will add more. Do not edit existing notes other than to wrap the mention; do not change their `fact_checks` or content. After the pass, run the batch procedure again.

### 6.5 Known soft spots for the later fact-check pass

Batch 6 soft spots: Aisha (birth about 614; death date 678; the reported ages at marriage; hadith count of about 2,000; the Battle of the Camel toll left out on purpose); Sor Juana (birth 1648 versus 1651; the 1693 to 1694 events and the fate of her library; Carta atenagórica date); Mirabai (everything is traditional; only two poems in pre-1700s manuscripts; 1516 marriage and 1521 death of Bhoj Raj); Funmilayo Ransome-Kuti (Abeokuta Women's Union name change about 1946 and the 20,000 figure; Alake's 1949 departure; 1953 Federation; 1977 raid account); Nezahualcoyotl (1402 birth; 1428 versus 1431; the dike and Tetzcotzingo attributions; 34 poems); Ramesses II (1279 to 1213 chronology; treaty year 21; Hittite marriage left out of the note; more than 90 children; Merneptah as thirteenth son); Attila (birth about 406; the 350, 700 and 2,100 pound tribute figures; 445 for Bleda's death; Nedao date left unstated); José Martí (arrest circumstances in 1869; 1902 independence wording).

These are the least certain statements in the first 40 notes, so they should be checked first: Razia Sultana (details of death, "led armies", coins); Amanirenas (identification with Strabo's Candace; reign dates); Trưng Sisters (Su Ding and Thi Sách story, three-year rule); Yaa Asantewaa (council speech is tradition; 1901 capture); Malinche (Bernal Díaz's account of her origin; Jaramillo marriage date); Khadija (age at marriage; four daughters); Zenobia (coins showing Aurelian and Vaballathus; date_end 274 is approximate); Jayavarman VII (102 hospitals, 1181 coronation date); Nur Jahan (her role in 1626); Sitting Bull (role at the Little Bighorn); Tupaia (Taiata's death timing; 74 versus about 130 islands); Ajuricaba (1727 versus 1728; Dutch alliance); Yermak (birth about 1532; death 1584 or 1585; size of force); Piye (reign 744 to 714; father Kashta counted first by some); Fu Hao (Wu Ding's reign dates; tomb counts); Laozi (entirely traditional); Queen Amina (1576 to 1610 is one source's dating); Ezana (conversion date; Athanasius consecration).

---

## 7. Watch-outs

- **Another session may be running Brief 4 (Early Eras) in the same vault.** Validator and hub runs are shared. If validation shows errors in files outside your batch (`01_Eras/`, `03_Entities/Events/` and so on), they belong to that session's batch in progress. Do not fix them; re-run after a minute.
- **`Art-Talk-main/` is resolved.** It is now in `SKIP_DIRS` in `_RAG/vault.py`, so the validator and indexer ignore it and no `grep -v Art-Talk-main` filter is needed. Do not edit that folder. A separate Art-Talk session also wrote 9 artist People notes into `03_Entities/People/` at 14:04 to 14:05 (list in section 0). Before writing any batch, re-check that every title is still free with `find . -iname "Title.md" -not -path "./_RAG/*"`, because that session may add more.
- **Title collisions:** titles are unique across all note types. Known trap: "Lalibela" the person versus the place already renamed "Rock-Hewn Churches of Lalibela". Check before writing.
- **Do not put files at the vault root or anywhere outside `03_Entities/...` unless they are notes;** the scanner reads every `.md` outside `_RAG`, `_Templates`, `.obsidian`.
- **Windows quirks:** always quote paths (the vault folder has a space); use forward slashes in Bash; the Python is `_RAG/.venv/Scripts/python.exe`.
- **The user has been saying "continue" after each batch.** Do not run several batches unprompted.

## 8. Done criteria

**People phase:** about 100 new People (about 149 total); at least 35 new women; at most 20 Europe and Mediterranean; every region has at least 2 and the formerly empty regions at least 2; spread across eras including Bronze Age, Iron Age, Early Modern and Information Age; validator at 0 errors.

**Cultures phase:** about +100 Cultures; at least 3 new per region; at least 12 for Europe; all 11 belief traditions; link pass done; validator at 0 errors; memory note updated. The later fact-check pass is separate work.

## 9. Live Cultures plan (written 2026-09-27 evening; supersedes 2.3 and the candidate lists above)

**State:** 97 culture files on disk (81 original + 16 new). Validator 0 errors on a clean run (it flickers to about 200 `fact_checks cites unknown source` errors while another session's fact-check pass is mid-write; re-run after a minute and filter by your own filenames). **Batch 2 is still NOT reindexed:** `reindex` fails because `_RAG/index/vault.db` is write-locked by another live session (`build_index.py` directly gives `sqlite3.OperationalError: database is locked`; a stale `vault.db-journal` from 21:37 exists; about 7 `mcp_server.py` processes and a `fetch_source.py --tier 5` run were alive). Do not kill other sessions' processes; retry `reindex` later (it is a full rescan, so one successful run after all batches gives the same result as per-batch runs). None of the titles below collides with the existing 97 (checked 2026-09-27).

**Batches (8 each; re-check every title with `find . -iname "Title.md" -not -path "./_RAG/*"` at write time):**
- B3: Etruscans, Yamnaya Culture, Anglo-Saxons (Europe); Lakota, Mississippian Culture (N. America); Garifuna (Caribbean); Hawaiian Kingdom (Oceania); Funan (SE Asia)
- B4: Huns, Normans (Europe); Hopewell Tradition (N. America); Maroon Communities (Caribbean); Zapotec Civilization (Mesoamerica); Chavín Culture (Andes); Sasanian Empire (Iranian Plateau); Akkadian Empire (Mesopotamia)
- B5: Kievan Rus, Holy Roman Empire (Europe); Tupi-Guarani, Yanomami (Amazon); Ptolemaic Kingdom, Kingdom of Makuria (Nile Valley); Nok Culture (Sub-Saharan Africa); Tui Tonga Empire (Oceania)
- B6: Venetian Republic, Dutch Republic (Europe); Toltec (Mesoamerica); Moche Culture (Andes); Kingdom of Himyar (Arabia); Babylonian Empire (Mesopotamia); Sukhothai Kingdom (SE Asia); Parthian Empire (Iranian Plateau)
- B7: Soviet Union, Beaker Culture (Europe); Mixtec (Mesoamerica); Wari Empire (Andes); Rashidun Caliphate (Arabia); Kingdom of Israel and Judah (Levant); Oyo Empire (Sub-Saharan Africa); Moriori (Oceania)
- B8: Sarmatians, Khazar Khaganate, Golden Horde (Steppe); Yuezhi, Kara-Khitan Khanate (Oases); Evenki, Nenets (Siberia); Elamites (Iranian Plateau)
- B9: Chukchi (Siberia); Carthaginian Empire, Berbers, Almoravid Dynasty (Mediterranean); Igbo-Ukwu Culture, Asante Empire (Sub-Saharan Africa); Mamluk Sultanate (Nile Valley); Đại Việt (SE Asia). After B9 the region floor is met except Amazon (needs 1 more) and Central Asian Oases (needs 1 more).
- B10: Tapajós Culture (Amazon, floor gap), Khwarazmian Empire (Oases, floor gap), Zhou Dynasty, Sui Dynasty, Yuan Dynasty, Goguryeo, Silla, Joseon Dynasty
- B11: Yamato Court, Ainu, Yayoi Culture, Magadha, Gandhara, Vijayanagara Empire, Maratha Empire, Sikh Empire
- B12: Pala Empire, Tibetan Empire, Habsburg Monarchy, Polish-Lithuanian Commonwealth, Basques, Sami, Navajo, Comanche
- B13 (6): Tiwanaku, Chimú, Buganda, Luba Empire, Kingdom of Dahomey, Khoisan Peoples
- Reserve pool if a title is taken or unsourceable: Visigothic Kingdom, Early Slavs, Corded Ware Culture, Linear Pottery Culture, Cucuteni-Trypillia Culture, Seleucid Empire, Urartu, Lydians, Avars, Xianbei, Kipchaks, Uyghur Khaganate, Liao Dynasty, Pallava Dynasty, Dvaravati, Lan Xang, Dong Son Culture, Nazca Culture, Purépecha, Torres Strait Islanders, Chamorro, Ethiopian Empire, Hausa City-States, Seljuk Empire, Ayyubid Sultanate, Fatimid Caliphate, Ilkhanate.

Totals: B3-B13 is 78 notes, giving about 175 culture files (the floor of 153 is met after B9).

**Style facts confirmed from Celts, Kalinago and Zoroastrianism:** frontmatter `title, type: culture, era, region, themes, date_start, [date_end], date_precision, related, sources, confidence, status: seed, tags: []`, no `fact_checks`; sources normally `["[[Encyclopaedia Britannica]]", "[[English Wikipedia]]"]`; the Reading is 3 short sentences, ends with "A specialist could argue ... which would weaken ...", and uses only approved Observer terms; body 300-330 words by the awk count; every wikilink (related, Context) must resolve to an existing note, otherwise plain text.

**Intended orchestration (not yet run):** a Workflow script parameterized by batch list. Pilot B3 first (8 chains of write-with-research then independent adversarial verify-and-repair, each validating only its own file), one integration agent (word counts, validate, `update_hubs.py`, validate, region tally), review, then B4-B13 (writer + verifier per note, batch gate on validator errors), then reindex retry loop, a completeness critic against the region floors, and only then the link pass (Step 3 of the plan) with surgical Edits when no other session is editing.

**Status update 2026-09-28: Batch 3 (Etruscans, Yamnaya Culture, Anglo-Saxons, Lakota, Mississippian Culture, Garifuna, Hawaiian Kingdom, Funan) is DONE** via the workflow in `cultures_batch_workflow.js` (105 culture files, validator 0 errors, hubs updated, Batch 3 not yet in the search index). The live state, lessons, remaining Batch 4-13 list with care flags and the post-batch steps are in **`_RAG/handoff/HANDOFF_Brief1_Cultures_Remaining.md`**; use that file as the entry point.
