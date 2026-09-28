"""Hand-written parts of the Tier 4 patch (37 Wikipedia pages via the MediaWiki API, plus the generic
English Wikipedia note, 2026-09-27). Policy A as in Tier 3: fix contradictions, narrow checks to what the
page read supports, keep true-but-unconfirmed details in the note and log them in unresolved.md.

Writes specs/tier4_manual.json (per-source extras for t2_build.py) and specs/tier4_extra.json (source_updates
for the generic note, note patches, discrepancies, unresolved list).
"""
import json

import _paths
import fetch_source as fs

SP = _paths.WORK
SP.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------------------------------ per-source manual entries
# Most of the 37 pages needed no correction (see t4_missing.txt / t4_all_c.txt review); these are the ones with a
# genuine gap or contradiction, recorded here so t2_build.py's Caveats explain it (Wikipedia revision id is added
# automatically by the builder's route text, "MediaWiki API, revision <id>").
SRC = {
    "Wikipedia on Tin Sources and Trade during Antiquity": {
        "extra": "The article discusses the sourcing of tin for bronze generally (arsenical bronze preceding tin bronze, Cornwall and Afghanistan among the tin sources) but does not give 3300 BCE, or any single date, for the start of tin bronze use.",
    },
    "Wikipedia on the Crusades": {
        "extra": "The article dates the fall of Acre to 28 May 1291, not 18 May; the Crusades note was corrected.",
    },
    "Wikipedia on the Incense Trade Route": {
        "extra": "The article names Shabwa, Qataban, Saba', Ma'in, Dhofar, Najran, Petra and Gaza on the route, but does not name Hadramaut, the botanical name Boswellia sacra, Marib, or a date for camel domestication.",
    },
    "Wikipedia on Timur": {
        "extra": "The article spells the puppet khan's title Chaghatayid (the note used Chagatayid) and confirms directly that Timur 'could not claim the title of khan ... because he was not a descendant of Genghis Khan'.",
    },
    "Wikipedia on Safavid Iran": {
        "extra": "The article does not name the Battle of Chaldiran or give 23 August 1514 for it, although it confirms the Ottoman-Safavid rivalry and the other Safavid dates checked.",
    },
    "Wikipedia on the Late Shang and Oracle Bones": {
        "extra": "The article confirms Wu Ding beginning in the second half of the 13th century BCE and the Zhou conquest dated to 1046 BCE (following Pankenier's astronomical dating), and names Anyang, but does not give a specific radiocarbon range of 1254-1197 BCE for the oracle bones or the name Muye for the battle.",
    },
    "Wikipedia on the Arab Conquest of Sindh": {
        "used": "The Umayyad conquest of Sindh, 711-713, in which the Umayyad Caliphate defeated the Chach dynasty (the last Hindu dynasty to rule Sindh) and incorporated Sindh, part of southern Punjab and Makran as a caliphal province.",
        "extra": "The article is specifically about the Sindh campaign; it does not mention the conquest of Iberia or Abd al-Rahman I's emirate at Cordoba (756), which the Umayyad Caliphate note also checked against it. That part of the check now cites Britannica on Al-Andalus instead (read in Tier 3).",
    },
    "Rapa Nui History Sources (Rano Raraku, Slave Raids, Ecocide Debate)": {
        "citation": "Wikipedia, 'Rano Raraku.'",
        "cut_note": "EBSCO Research Starters, 'Slave Traders and Easter Island'; Hunt and Lipo, 'Revisiting Rapa Nui (Easter Island) Ecocide'; Science/AAAS, 'No, the people of Rapa Nui didn't commit ecocide' (none of these were fetched; only the Wikipedia URL in this note was read).",
        "access_override": {"access": "reference-text"},
        "used": "887 moai remain at the Rano Raraku quarry, which supplied the stone for about 95 percent of the island's known monolithic statues.",
        "extra": "The Rano Raraku Wikipedia article is about the quarry; it says nothing about the 1862-63 Peruvian slave raids, the 1877 population, or the ecocide debate. Those claims were never actually read (the note's other checks, citing Rano Raraku Moai Counts (Search Summaries) and Rapa Nui Ecocide Debate and the 1862 Slave Raids (Search Summaries), already give more precise figures for the slave raids from a Tier 6 source).",
    },
}

# ------------------------------------------------------------------------------------------------- new source notes
# none needed in Tier 4: every check with a real gap could be narrowed or, for the Sindh/Al-Andalus case,
# re-pointed to a source note already created in Tier 3.

NEW = []

# --------------------------------------------------------------------------------------------------- note patches
def rc(old, new):
    return [old, new]


def note(name, *, rc_=(), rep=(), checks=(), src=()):
    d = {"note": name}
    if rc_:
        d["replace_checks"] = [list(x) for x in rc_]
    if rep:
        d["replace"] = [list(x) for x in rep]
    if checks:
        d["checks"] = list(checks)
    if src:
        d["sources"] = list(src)
    return d


NOTES = [
    note("Crusades",
         rc_=[rc("Council of Clermont in November 1095; Jerusalem captured in 1099; retaken by Saladin in October 1187; Fourth Crusade attacked Constantinople; Acre fell on 18 May 1291",
                 "Pope Urban II proclaimed the First Crusade at the Council of Clermont in November 1095; the First Crusade captured Jerusalem in 1099; Jerusalem surrendered to Saladin after a 12-day siege on 2 October 1187; the Fourth Crusade was diverted to the Byzantine Empire, culminating in the Sack of Constantinople and the Latin Empire of 1204; Qalawun's son Khalil took Acre, the last Crusader mainland stronghold, on 28 May 1291 [Wikipedia on the Crusades]")],
         rep=[rc("The last Crusader stronghold on the mainland, Acre, fell to the Mamluks in 1291.",
                 "The last Crusader stronghold on the mainland, Acre, fell to the Mamluks on 28 May 1291.")]),
    note("Bronze Age",
         rc_=[rc("Tin bronze from about 3300 BCE",
                 "Tin was traded over long distances for making tin-bronzes from the Bronze Age onward; current archaeological debate concerns the origins of tin in the earliest Bronze Age cultures of the Near East [Wikipedia on Tin Sources and Trade during Antiquity]")]),
    note("Bronze Metallurgy",
         rc_=[rc("Tin bronze from about 3300 BCE, preceded by arsenical bronze; tin from Afghanistan and Cornwall among other sources",
                 "The earliest bronze objects had tin or arsenic content of less than 2 percent and are believed to result from unintentional alloying of polymetallic ores; deposits worked for tin during the Bronze Age include sites in Afghanistan and in Cornwall and Devon in Britain, among other sources [Wikipedia on Tin Sources and Trade during Antiquity]")]),
    note("Incense Trade",
         rc_=[rc("Route from Dhofar and Hadramaut (Boswellia sacra) through Marib and Najran to Petra and Gaza; camel domestication in the late 2nd or early 1st millennium BCE",
                 "Aromatics from Dhofar were shipped from Qana and taken overland through Shabwa, then north through Najran, Mecca and Medina to Petra and on to Gaza; caravans also carried goods from Shabwa to the kingdoms of Qataban, Saba' and Ma'in [Wikipedia on the Incense Trade Route]")]),
    note("Arabian Peninsula",
         rc_=[rc("Incense route from Dhofar and Hadramaut to Petra and Gaza",
                 "Aromatics from Dhofar moved north through Shabwa to Najran, Mecca, Medina, Petra and on to Gaza [Wikipedia on the Incense Trade Route]")]),
    note("Timur",
         rc_=[rc("Ruled as amir, not khan, through a puppet Chagatayid khan; took the title güregen (royal son-in-law) by marrying a Genghisid; was not himself a descendant of Genghis Khan",
                 "By Mongol tradition Timur could not claim the title of khan because he was not a descendant of Genghis Khan; he set up a puppet Chaghatayid khan, Suyurghatmish, as nominal ruler, and claimed the title güregen (royal son-in-law) to a princess of the Chinggisid line [Wikipedia on Timur]")],
         rep=[rc("He was not a descendant of Genghis Khan and did not take the title khan. He ruled as amir through a puppet Chagatayid khan and took the title güregen (royal son-in-law) through his marriage to Saray Mulk Khanum, a Genghisid.",
                 "He was not a descendant of Genghis Khan and did not take the title khan. He ruled as amir through a puppet Chaghatayid khan, Suyurghatmish, and took the title güregen (royal son-in-law) through his marriage to Saray Mulk Khanum, of the Chinggisid line.")]),
    note("Shang Dynasty",
         rc_=[rc("Shang c. 1600-1046 BCE; oracle bones radiocarbon-dated to 1254-1197 BCE; Yin near Anyang; overthrown by Zhou at Muye in 1046 BCE",
                 "The Shang dynasty spans the reigns of its last nine kings from Wu Ding, beginning in the second half of the 13th century BCE, to the Zhou conquest, dated by astronomical evidence to 1046 BCE; the late Shang capital, Yin, was near modern Anyang [Wikipedia on the Late Shang and Oracle Bones]")]),
    note("Umayyad Caliphate",
         src=["Britannica on Al-Andalus"],
         rc_=[rc("Conquest of Sindh 711-713; conquest of Iberia from 711; Abd al-Rahman I established a Cordoba emirate in 756",
                 "Between 711 and 713 the Umayyad Caliphate defeated the Chach dynasty and incorporated Sindh, part of southern Punjab and Makran [Wikipedia on the Arab Conquest of Sindh]; Muslim forces crossed into Iberia in 711, and after 756 Abd al-Rahman I established an independent Umayyad emirate at Cordoba [Britannica on Al-Andalus]")]),
    note("Rapa Nui",
         rc_=[rc("887 moai at Rano Raraku, about 95 percent of statues quarried there; 1862-63 Peruvian slave raids took about 1,500 people; population 110 in 1877; ecocide account contested",
                 "887 moai remain at the Rano Raraku quarry, which supplied the stone for about 95 percent of the island's known monolithic sculptures [Rapa Nui History Sources (Rano Raraku, Slave Raids, Ecocide Debate)]")]),
]

# ------------------------------------------------------------------------- the generic homepage note
_m = json.loads((fs.CACHE / "english-wikipedia.meta.json").read_text(encoding="utf-8"))
GENERIC_UPDATE = {
    "title": "English Wikipedia",
    "set": {"access": "not-consulted", "access_route": "none: the Wikipedia home page stands for the whole encyclopedia; no article was read under this title"},
    "used": "Stands for English Wikipedia as a whole when a note cites it without naming an article. No article was read under this title, so a check that cites only this note is not confirmed by any text read; wherever a Tier 4 fetch of the specific article succeeded, the check now cites that article's source note instead (see the source notes titled Wikipedia on ...).",
    "caveats": ("The home page (https://en.wikipedia.org/) is not an article and cannot be fetched through the MediaWiki API "
                f"(attempted {_m['retrieved']}, no text returned). Most checks that cite this note also cite another source (Encyclopaedia Britannica, World History Encyclopedia, "
                "UNESCO, a named person's page) not yet read, or a specific Wikipedia article outside the 37 fetched in Tier 4; both remain for Tiers 5-6. "
                "A tertiary, editable source: check primary or scholarly sources for anything that matters."),
    "mark": "done",
}

# ------------------------------------------------------------------------------------------------- discrepancies
def d(note_, source, was, says, action):
    return {"note": note_, "source": source, "was": was, "text_says": says, "action": action}


DISC = [
    d("Crusades", "Wikipedia on the Crusades", "Acre fell on 18 May 1291", "Acre fell to Qalawun's son Khalil on 28 May 1291.",
      "Facts bullet and check corrected to 28 May 1291."),
    d("Timur", "Wikipedia on Timur", "puppet Chagatayid khan", "The article spells it Chaghatayid and names him Suyurghatmish.",
      "Facts bullet and check corrected to Chaghatayid and the khan's name added."),
    d("Umayyad Caliphate", "Wikipedia on the Arab Conquest of Sindh",
      "Conquest of Sindh 711-713; conquest of Iberia from 711; Abd al-Rahman I established a Cordoba emirate in 756 (all three cited to the Sindh conquest article)",
      "The article is specifically about the Sindh campaign and does not mention Iberia or Cordoba.",
      "Check split: the Sindh atoms stay on the Wikipedia article, the Iberia and Cordoba atoms now cite Britannica on Al-Andalus (already read in Tier 3)."),
    d("Rapa Nui", "Rapa Nui History Sources (Rano Raraku, Slave Raids, Ecocide Debate)",
      "887 moai at Rano Raraku, about 95 percent quarried there; 1862-63 Peruvian slave raids took about 1,500 people; population 110 in 1877; ecocide account contested (all four cited to one source note whose citation bundled three pages that were never fetched)",
      "Only the Wikipedia 'Rano Raraku' URL in this note was actually read; it confirms the moai count and percentage but says nothing about slave raids, population or the ecocide debate.",
      "Check narrowed to the moai count; the slave-raid and population atoms are logged in unresolved.md (the note's other checks, citing two Search Summaries sources, already give more precise slave-raid figures)."),
]

# ------------------------------------------------------------------------------------------------ unresolved.md
U = [
    ("Bronze Age; Bronze Metallurgy", "Tin bronze specifically dated to about 3300 BCE (page: no single start date for tin bronze; 3300 BCE is the Near Eastern Bronze Age's start per Wikipedia on the List of Archaeological Periods, a different claim)", "Wikipedia on Tin Sources and Trade during Antiquity"),
    ("Incense Trade; Arabian Peninsula", "Hadramaut, the species name Boswellia sacra, Marib, and a date for camel domestication in the late 2nd or early 1st millennium BCE", "Wikipedia on the Incense Trade Route"),
    ("Safavid Empire", "Ottoman victory at Chaldiran on 23 August 1514", "Wikipedia on Safavid Iran"),
    ("Shang Dynasty", "Oracle bones radiocarbon-dated to 1254-1197 BCE; the Zhou victory named as the Battle of Muye", "Wikipedia on the Late Shang and Oracle Bones"),
    ("Rapa Nui", "1862-63 Peruvian slave raids took about 1,500 people; population 110 in 1877; the ecocide account as contested (already better covered by the note's other, Tier 6, checks)", "Rapa Nui History Sources (Rano Raraku, Slave Raids, Ecocide Debate)"),
]


def write_unresolved(date):
    log = fs.CACHE / "unresolved.md"
    text = log.read_text(encoding="utf-8")
    if f"## Tier 4 ({date})" in text:
        print("unresolved.md already has this Tier 4 section; not appended")
        return
    rows = "\n".join(f"- **{n}**: {a} [cited to {s}]" for n, a, s in U)
    log.write_text(text.rstrip("\n") + f"\n\n## Tier 4 ({date})\n{rows}\n", encoding="utf-8", newline="\n")
    print(f"unresolved.md: {len(U)} Tier 4 entries written")


if __name__ == "__main__":
    import sys
    (SP / "tier4_manual.json").write_text(json.dumps(SRC, indent=1, ensure_ascii=False), encoding="utf-8")
    (SP / "tier4_extra.json").write_text(json.dumps({"sources_new": NEW, "source_updates": [GENERIC_UPDATE], "notes": NOTES, "discrepancies": DISC},
                                                    indent=1, ensure_ascii=False), encoding="utf-8")
    print(len(SRC), "source manual entries;", len(NEW), "new sources;", len(NOTES), "note patches;", len(DISC), "discrepancies;", len(U), "unresolved")
    if "--unresolved" in sys.argv:
        write_unresolved(__import__("datetime").date.today().isoformat())
