"""Hand-written parts of the Tier 5 patch (113 other reference sites read directly or via Wayback, 2026-09-27/28).
Policy A as in Tiers 3-4: fix contradictions, narrow checks to what the page read supports, keep true-but-unconfirmed
details in the note and log them in unresolved.md.

The generic notes 'World History Encyclopedia' and 'UNESCO World Heritage Centre' had each been fetched from ONE unrelated
page (Ibn Battuta; Cahokia Mounds), so their checks were unconfirmed. The specific pages were fetched instead (see
t5_fetch_new.py) and become new source notes; the checks are re-pointed to them, and the generic notes are set to
not-consulted like the Britannica and English Wikipedia notes.

Writes specs/tier5_manual.json (per-source extras for t2_build.py) and specs/tier5_extra.json (sources_new, source_updates,
note patches, discrepancies). --unresolved appends a Tier 5 section to unresolved.md.
"""
import json
import re
import sys
from urllib.parse import urlparse

import _paths
import fetch_source as fs

SP = _paths.WORK
SP.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------------------------- new source notes
def meta_of(title):
    return json.loads((fs.CACHE / f"{fs.slugify(title)}.meta.json").read_text(encoding="utf-8"))


HOSTS = {
    "www.worldhistory.org": ("World History Encyclopedia", "medium", "worldhistory.org"),
    "whc.unesco.org": ("UNESCO World Heritage Centre", "high", "whc.unesco.org"),
    "en.wikipedia.org": ("Wikipedia", "medium", "en.wikipedia.org"),
    "www.nobelprize.org": ("NobelPrize.org", "high", "nobelprize.org"),
    "gml.noaa.gov": ("NOAA Global Monitoring Laboratory", "high", "gml.noaa.gov"),
}


NOT_FETCHED = {}   # new-source title -> fetch metadata, for pages no route could read in this pass (2026-11-19)


def new_src(title, url, page, used, extra=""):
    """A new source note, or None when the page was not read in this pass (no cache, or a fetch that failed).
    The access level and route follow what the fetch actually did; a page is never marked full-text unless it was read."""
    try:
        m = meta_of(title)
    except FileNotFoundError:
        m = {"level": None, "attempts": []}
    if not m.get("level"):
        NOT_FETCHED[title] = m
        return None
    pub, rel, host = HOSTS[urlparse(url).netloc]
    if m["route"] not in ("wikipedia-api", "direct"):
        raise SystemExit(f"{title}: route {m['route']!r} has no Caveats wording here; add a branch to new_src")
    if m["route"] == "wikipedia-api":
        route = f"MediaWiki API raw wikitext, revision {m['revid']}"
        cav = (f"Read in full on {m['retrieved']} as raw wikitext from the MediaWiki API, revision {m['revid']} ({m['chars']:,} characters converted "
               "from wikitext markup). Wikipedia is not authoritative and this revision may have since been edited. ")
        access = "reference-text"
    else:
        route = f"{host} page fetched directly"
        cav = f"Read in full on {m['retrieved']} from {host} fetched directly ({m['chars']:,} characters). "
        access = "full-text"
    cit = f"{pub}. '{page}.'" if pub != "Wikipedia" else f"Wikipedia, '{page}.'"
    return {"title": title, "citation": cit, "url": url, "kind": "reference", "reliability": rel, "access": access,
            "access_route": route, "read_on": m["retrieved"], "used": used, "caveats": (cav + extra).strip()}


W = "https://www.worldhistory.org/"
U = "https://whc.unesco.org/en/list/"
WP = "https://en.wikipedia.org/wiki/"
NOBEL = "https://www.nobelprize.org/prizes/"
NOAA = "https://gml.noaa.gov/webdata/ccgg/trends/co2/"
ADD = "Added in Tier 5 to replace the generic {g} citation on the {n} note{s}. "

NEW = [
    # ---- World History Encyclopedia
    new_src("World History Encyclopedia on Akhenaten", W + "Akhenaten/", "Akhenaten",
            "Akhenaten's reign (1353-1336 BCE) as a pharaoh of the 18th Dynasty and his move of the capital from Thebes to Akhetaten (Amarna).",
            ADD.format(g="World History Encyclopedia", n="Akhenaten", s="")),
    new_src("World History Encyclopedia on Alexander the Great", W + "Alexander_the_Great/", "Alexander the Great",
            "Alexander's life (21 July 356 BCE to 10 or 11 June 323 BCE), the battle of Gaugamela in 331 BCE, the mutiny of his army in 326 BCE, and his return to Babylon in 323 BCE.",
            ADD.format(g="World History Encyclopedia and Britannica", n="Alexander the Great and Alexander's Conquests", s="s") +
            "The page dates his death to 10 or 11 June 323 BCE, not 13 June, and does not name the Hyphasis for the mutiny."),
    new_src("World History Encyclopedia on Augustus", W + "Augustus/", "Augustus",
            "Augustus (27 BCE to 14 CE) as the first Roman emperor, born Gaius Octavius Thurinus on 23 September 63 BCE.",
            ADD.format(g="World History Encyclopedia and Britannica", n="Augustus", s="") + "The page does not give the day of his death (19 August 14 CE); Wikipedia on Augustus does."),
    new_src("World History Encyclopedia on Genghis Khan", W + "Genghis_Khan/", "Genghis Khan",
            "Genghis Khan as founder of the Mongol Empire, which he ruled from 1206 until his death in 1227, and the secrecy of the location of his tomb.",
            ADD.format(g="World History Encyclopedia and Britannica", n="Genghis Khan", s="") + "The page gives his death as 18 August 1227."),
    new_src("World History Encyclopedia on Hammurabi", W + "Hammurabi/", "Hammurabi: Conquerer, King, and Law-Giver",
            "Hammurabi's reign (1792-1750 BCE) as sixth king of the Amorite First Dynasty of Babylon, and the discovery of the stele of his law code at Susa in 1901.",
            ADD.format(g="World History Encyclopedia and Britannica", n="Hammurabi", s="") + "The page does not give 282 laws, a date of about 1754 BCE for the code, or the Louvre."),
    new_src("World History Encyclopedia on Pachacuti", W + "Pachacuti/", "Pachacuti Inca Yupanqui: Founder of the Inca Empire",
            "Pachacuti (1438-1471 CE) as founder of the Inca empire, with conquests in the Cuzco Valley and beyond, and Tupac Inca Yupanqui succeeding him as Sapa Inca.",
            ADD.format(g="World History Encyclopedia", n="Pachacuti", s="") + "The page gives 1438-1471, not 1438-1472."),
    new_src("World History Encyclopedia on the Aztec Empire", W + "Aztec_Civilization/", "Aztec Civilization: The Last Mesoamerican Empire",
            "The Aztec empire (c. 1345-1521) with its capital at Tenochtitlan, and its collapse under Cuauhtemoc on 13 August 1521.",
            ADD.format(g="World History Encyclopedia and Britannica", n="Aztec Empire", s="") + "The page does not give 1519 for the start of the Spanish conquest."),
    new_src("World History Encyclopedia on the Inca Empire", W + "Inca_Civilization/", "Inca Civilization",
            "The Inca defeat of the Chanca in 1438 and expansion under Pachacuti, an empire of some 10 million subjects speaking over 30 languages, the civil war between Waskar and Atahualpa as Europeans arrived, and the empire's span between 1400 and 1533 CE.",
            ADD.format(g="World History Encyclopedia and UNESCO", n="Inca Empire", s="") + "The page does not give 1532 for Atahualpa's capture, the taking of Cusco in 1533, or a road network of 30,000-40,000 km (its '40,000' is the number of Incas who governed the empire)."),
    new_src("World History Encyclopedia on the Khmer Empire", W + "Khmer_Empire/", "Khmer Empire",
            "The Khmer Empire from 802 CE to 1431 CE, Jayavarman II's campaigns, and Angkor Wat begun by Suryavarman II around 1122 CE.",
            ADD.format(g="World History Encyclopedia", n="Khmer Empire and Southeast Asia", s="s") + "The page does not give the reign 1113-1150 for Suryavarman II."),
    new_src("World History Encyclopedia on the Mali Empire", W + "Mali_Empire/", "Mali Empire",
            "The defeat of the Sosso at Kirina in 1235 and the reign of Mansa Musa I (1312-1337).",
            ADD.format(g="World History Encyclopedia", n="Mali Empire and Medieval Period", s="s")),
    new_src("World History Encyclopedia on the Indus Valley Civilization", W + "Indus_Valley_Civilization/", "Indus Valley Civilization",
            "The Mature Harappan phase of the Indus Valley Civilization (c. 2600-1900 BCE).",
            ADD.format(g="World History Encyclopedia", n="Indus Valley Civilization, South Asia and Bronze Age", s="s")),
    new_src("World History Encyclopedia on Cuneiform", W + "Cuneiform/", "Cuneiform: The Writing System That Made History",
            "Cuneiform as first developed by the Sumerians of Mesopotamia circa 3600/3500 BCE and further developed at Uruk circa 3200 BCE.",
            ADD.format(g="World History Encyclopedia", n="Invention of Writing, Mesopotamia and Bronze Age", s="s") +
            "The page gives circa 3600/3500 BCE for the first cuneiform and 3200 BCE for the development at Uruk, where the notes give 3400-3200 BCE."),
    new_src("World History Encyclopedia on Writing", W + "writing/", "Writing: The Preservation of Human Thought and Action",
            "Egyptian writing already in use before the Early Dynastic Period (circa 3150 BCE), Chinese writing from oracle-bone divination circa 1200 BCE, and Mesoamerican writing arising independently with some evidence as early as 500 BCE.",
            ADD.format(g="World History Encyclopedia", n="Invention of Writing", s="") +
            "The page gives circa 3150 BCE for Egypt (no Abydos) and as early as 500 BCE for Mesoamerica, where the note gives about 3200 BCE and by 600 BCE."),
    new_src("World History Encyclopedia on the Late Bronze Age Collapse", W + "Bronze_Age_Collapse/", "Bronze Age Collapse: The Decline and Fall of Mediterranean Civilization",
            "The date 1177 BCE as a kind of scholarly shorthand for the beginning of the Late Bronze Age collapse, not a definitive date.",
            ADD.format(g="World History Encyclopedia", n="Bronze Age Collapse and Bronze Age", s="s") + "The page does not mention Medinet Habu or Ramesses III's year 8."),
    new_src("World History Encyclopedia on Uruk", W + "uruk/", "Uruk: The First Great City",
            "The Uruk Period (4000-3100 BCE), during which cities began to develop across Mesopotamia and Uruk became the most influential.",
            ADD.format(g="World History Encyclopedia", n="Mesopotamia and The Urban Revolution", s="s") + "The page gives no population figure for Uruk."),
    new_src("World History Encyclopedia on the Abbasid Caliphate", W + "Abbasid_Caliphate/", "Abbasid Dynasty",
            "The Abbasids' assumption of the caliphate in 750 CE and the end of their rule in 1258 CE when the Mongols destroyed Baghdad.",
            ADD.format(g="World History Encyclopedia and Britannica", n="Medieval Period, Mongol Conquests and Rise of Islam", s="s")),
    new_src("World History Encyclopedia on the Peloponnesian War", W + "Peloponnesian_War/", "Peloponnesian War",
            "The Peloponnesian War fought from 431 to 404 BCE (after an earlier conflict from 460 to 446 BCE).",
            ADD.format(g="World History Encyclopedia and Britannica", n="Ancient Greeks and Athens", s="s")),
    new_src("World History Encyclopedia on the Punic Wars", W + "Punic_Wars/", "Punic Wars",
            "The Punic Wars between Carthage and Rome (264-146 BCE) and Hannibal's march over the Alps in the Second Punic War (218-201 BCE).",
            ADD.format(g="Britannica", n="Carthage", s="") + "The page dates the Second Punic War to 218-201 BCE and describes Hannibal's march over the Alps, but does not give 218 BCE for the crossing itself."),
    new_src("World History Encyclopedia on Aksum", W + "Kingdom_of_Axum/", "Kingdom of Axum",
            "King Ezana I's adoption of Christianity in the mid-4th century CE.",
            ADD.format(g="World History Encyclopedia", n="Sub-Saharan Africa", s="") + "The page says mid-4th century CE and does not give 333 CE."),
    # ---- UNESCO World Heritage Centre
    new_src("UNESCO on Angkor", U + "668/", "Angkor", "Inscription of Angkor on the World Heritage List in 1992.",
            ADD.format(g="UNESCO World Heritage Centre", n="Angkor and Southeast Asia", s="s") + "The page gives the year of inscription, not the day (14 December 1992)."),
    new_src("UNESCO on Caral-Supe", U + "1269/", "The Sacred City of Caral-Supe", "The 5000-year-old site of Caral-Supe and its inscription on the World Heritage List in 2009.",
            ADD.format(g="UNESCO World Heritage Centre", n="Caral", s="")),
    new_src("UNESCO on the Site of Carthage", U + "37/", "Site of Carthage", "Carthage's destruction by Rome in 146 BC in the Punic wars and inscription in 1979.",
            ADD.format(g="UNESCO World Heritage Centre and Britannica", n="Carthage", s="")),
    new_src("UNESCO on Chaco Culture", U + "353/", "Chaco Culture",
            "Chaco Canyon as a major centre of ancestral Pueblo culture between 850 and 1250, and inscription in 1987.",
            ADD.format(g="UNESCO World Heritage Centre", n="Chaco Canyon and North America", s="s")),
    new_src("UNESCO on Gobekli Tepe", U + "1572/", "Gobekli Tepe", "Göbekli Tepe's T-shaped limestone pillars up to 5.50 m tall and inscription in 2018.",
            ADD.format(g="UNESCO World Heritage Centre", n="Göbekli Tepe, Neolithic and Levant and Anatolia", s="s") + "The page does not give 9500-9000 BCE for the earliest structures or Klaus Schmidt's 1995 excavations."),
    new_src("UNESCO on Machu Picchu", U + "274/", "Historic Sanctuary of Machu Picchu",
            "Machu Picchu at 2,430 m above sea level, made known to the outside world in 1911, and inscribed in 1983.",
            ADD.format(g="UNESCO World Heritage Centre", n="Machu Picchu and Andes", s="s") + "The page does not give about 1450 or Pachacuti, or name Bingham."),
    new_src("UNESCO on Mohenjo-daro", U + "138/", "Archaeological Ruins at Moenjodaro", "Inscription of Mohenjo-daro in 1980.",
            ADD.format(g="UNESCO World Heritage Centre", n="Mohenjo-daro", s="")),
    new_src("UNESCO on Timbuktu", U + "119/", "Timbuktu", "Inscription of Timbuktu in 1988.",
            ADD.format(g="UNESCO World Heritage Centre", n="Timbuktu and Sub-Saharan Africa", s="s") + "The page does not give a figure of about 700,000 manuscripts."),
    new_src("UNESCO on Catalhoyuk", U + "1405/", "Neolithic Site of Catalhoyuk", "Inscription of Çatalhöyük in 2012.",
            ADD.format(g="UNESCO World Heritage Centre", n="Çatalhöyük, Neolithic and Levant and Anatolia", s="s")),
    new_src("UNESCO on Cahokia Mounds", U + "198/", "Cahokia Mounds State Historic Site",
            "Cahokia's possible peak population of 10-20,000 between 1050 and 1150, Monks Mound (30 m high, the largest prehistoric earthwork in the Americas) and inscription in 1982.",
            ADD.format(g="UNESCO World Heritage Centre", n="Cahokia and North America", s="s") + "The generic UNESCO note's url pointed at this page."),
    new_src("UNESCO on Chinchorro Settlement and Artificial Mummification", U + "1634/", "Chinchorro Culture's Settlement and Artificial Mummification of the Arica and Parinacota Region",
            "The Chinchorro culture (approximately 5450 BCE to 890 BCE) on the northern coast of the Atacama Desert and inscription in 2021.",
            ADD.format(g="UNESCO World Heritage Centre", n="Chinchorro Culture", s="") + "The page does not give the start of mummification (about 5050 BCE) or its duration (about 3,000 years); Wikipedia on the Chinchorro Mummies does."),
    new_src("UNESCO on Poverty Point", U + "1435/", "Poverty Point",
            "Poverty Point built by hunter-fisher-gatherers between 3700 and 3100 BP, its five mounds and six concentric ridges, and inscription on 22 June 2014.",
            ADD.format(g="UNESCO World Heritage Centre", n="Poverty Point and North America", s="s") + "The page does not give a height of about 22 m for Mound A."),
    new_src("UNESCO on the Taj Mahal", U + "252/", "Taj Mahal",
            "Construction beginning in 1632 and completed in 1648 with the outer buildings finished in 1653, Ustad Ahmad Lahori as the main architect, and inscription in 1983.",
            ADD.format(g="UNESCO World Heritage Centre", n="Taj Mahal", s="") + "The page does not give a figure of over 20,000 workers."),
    new_src("UNESCO on the Jomon Prehistoric Sites", U + "1632/", "Jomon Prehistoric Sites in Northern Japan", "Inscription of the Jomon Prehistoric Sites in Northern Japan in 2021 (27 July 2021).",
            ADD.format(g="the Jomon official site", n="Jomon Culture", s="") + "The page does not give the Jomon period's dates. (The list id first used for this page, 1361, is Historic Jeddah; the Jomon sites are 1632.)"),
    new_src("UNESCO on Al-Hijr Archaeological Site", U + "1293/", "Hegra Archaeological Site (al-Hijr / Mada'in Salih)",
            "Hegra (al-Hijr) as the largest conserved site of the Nabataean civilization south of Petra, and its inscription in 2008.",
            ADD.format(g="World History Encyclopedia", n="Nabataeans", s="")),
    # ---- Nobel Prize
    new_src("NobelPrize.org on the 1945 Nobel Prize in Physiology or Medicine", NOBEL + "medicine/1945/summary/", "The Nobel Prize in Physiology or Medicine 1945",
            "The 1945 prize awarded jointly to Sir Alexander Fleming, Ernst Boris Chain and Sir Howard Walter Florey for the discovery of penicillin.",
            ADD.format(g="NobelPrize.org home page", n="Antibiotics", s="")),
    new_src("NobelPrize.org on the 1903 Nobel Prize in Physics", NOBEL + "physics/1903/summary/", "The Nobel Prize in Physics 1903",
            "The 1903 prize divided between Antoine Henri Becquerel and, jointly, Pierre Curie and Marie Curie.",
            ADD.format(g="NobelPrize.org home page", n="Marie Curie", s="")),
    new_src("NobelPrize.org on the 1911 Nobel Prize in Chemistry", NOBEL + "chemistry/1911/summary/", "The Nobel Prize in Chemistry 1911",
            "The 1911 Chemistry prize awarded to Marie Curie for the discovery of radium and polonium.",
            ADD.format(g="NobelPrize.org home page", n="Marie Curie", s="")),
    # ---- NOAA
    new_src("NOAA GML Global Annual Mean CO2 Data", NOAA + "co2_annmean_gl.txt", "Global annual mean CO2 (marine surface sites)",
            "The global annual mean CO2 concentration: 422.79 ppm for 2024 and 419.35 ppm for 2023.",
            ADD.format(g="NOAA Trends page (its numbers were not in the text read)", n="Modern Climate Change", s="") + "A data file that NOAA revises, so the values may differ in later versions."),
    new_src("NOAA GML Global Annual Growth Rate of CO2", NOAA + "co2_gr_gl.txt", "Global annual mean CO2 growth rate",
            "The global annual CO2 growth rate: 3.76 ppm for 2024 and 2.69 ppm for 2023.",
            ADD.format(g="NOAA Trends page (its numbers were not in the text read)", n="Modern Climate Change", s="") + "The Modern Climate Change note's earlier figure of 3.75 ppm probably came from an earlier release of this file."),
    new_src("NOAA GML Mauna Loa Annual Mean CO2 Data", NOAA + "co2_annmean_mlo.txt", "Mauna Loa annual mean CO2",
            "The Mauna Loa annual mean CO2 concentration: 424.61 ppm for 2024.",
            ADD.format(g="NOAA Trends page (its numbers were not in the text read)", n="Modern Climate Change", s="") + "The note's earlier figure was 424.5 ppm."),
    # ---- Wikipedia
    new_src("Wikipedia on Mahatma Gandhi", WP + "Mahatma_Gandhi", "Mahatma Gandhi",
            "The Salt March from 12 March to 6 April 1930, British-granted independence in August 1947, and Gandhi's assassination on 30 January 1948.",
            ADD.format(g="Britannica and World History Encyclopedia", n="Mahatma Gandhi", s="")),
    new_src("Wikipedia on Zheng He", WP + "Zheng_He", "Zheng He",
            "Zheng He (1371-1433 or 1435) and the seven treasure voyages of 1405-1433.",
            ADD.format(g="Britannica and World History Encyclopedia", n="Zheng He", s="") + "The infobox gives the death year as 1433 or 1435; the note says 1433."),
    new_src("Wikipedia on the Hijrah", WP + "Hijrah", "Hijrah", "The Hijrah, Muhammad's journey from Mecca to Medina, in 622 CE (departure in May 622; the Islamic calendar epoch equates to 16 July 622).",
            ADD.format(g="Britannica and World History Encyclopedia", n="Arabian Peninsula and Rise of Islam", s="s")),
    new_src("Wikipedia on the Iroquois", WP + "Iroquois", "Iroquois",
            "The Haudenosaunee confederacy (the Great Law of Peace dated likely between 1142 and 1660, with little agreement), the Tuscarora accepted into the confederacy after 1722, and the Oneida and Tuscarora fighting with the Patriots in the American Revolution while the other nations allied with the British.",
            ADD.format(g="English Wikipedia and World History Encyclopedia", n="Haudenosaunee Confederacy, North America and American Revolution", s="s") + "The article does not give 1451-52 for the founding."),
    new_src("Wikipedia on the Phoenician Alphabet", WP + "Phoenician_alphabet", "Phoenician alphabet",
            "The Phoenician alphabet proper as an abjad of 22 consonant letters, and vowels added to the Phoenician letters in the early Greek alphabet.",
            ADD.format(g="World History Encyclopedia", n="Iron Age, Alphabet, Phoenicians and Levant and Anatolia", s="s") + "The article does not give about 1800 BCE for Proto-Sinaitic."),
    new_src("Wikipedia on the Urban Revolution", WP + "Urban_revolution", "Urban revolution",
            "V. Gordon Childe's introduction of the term 'urban revolution' in the 1930s and his 1950 article in Town Planning Review.",
            ADD.format(g="World History Encyclopedia", n="The Urban Revolution", s="")),
    new_src("Wikipedia on World Population", WP + "World_population", "World population", "The UN estimate that world population first reached one billion in 1804.",
            ADD.format(g="UN World Population Milestones", n="Industrial Age and Great Acceleration", s="s") + "The article does not give 2.5 billion for 1950."),
    new_src("Wikipedia on Cleisthenes", WP + "Cleisthenes", "Cleisthenes", "Cleisthenes as the lawgiver who set Athens on a democratic footing in 508 BC and is called the father of Athenian democracy.",
            ADD.format(g="Britannica and World History Encyclopedia", n="Mediterranean Basin, Ancient Greeks and Athens", s="s")),
    new_src("Wikipedia on the Parthenon", WP + "Parthenon", "Parthenon", "The Parthenon begun in 447 BC, completed in 438 BC, with decoration continuing until 432 BC.",
            ADD.format(g="Britannica and World History Encyclopedia", n="Athens", s="")),
    new_src("Wikipedia on the Code of Hammurabi", WP + "Code_of_Hammurabi", "Code of Hammurabi",
            "The stele of the code, now in the Louvre, rediscovered in 1901 at Susa, and Hammurabi's reign (around 1792 to around 1750 BC, middle chronology).",
            ADD.format(g="Britannica and World History Encyclopedia", n="Hammurabi", s="") + "The article does not give a date of about 1754 BCE for the code or say in so many words that it has 282 laws."),
    new_src("Wikipedia on Ibn Battuta", WP + "Ibn_Battuta", "Ibn Battuta",
            "Ibn Battuta's travels of around 117,000 km, his dictation of the account to Ibn Juzayy, and his caravan to Mali from February 1352 and departure for Sijilmasa in September 1353.",
            ADD.format(g="World History Encyclopedia", n="Ibn Battuta", s="") + "The generic World History Encyclopedia note's url is the World History Encyclopedia article on Ibn Battuta, which could not be read on 2026-11-19."),
    new_src("Wikipedia on Augustus", WP + "Augustus", "Augustus", "Augustus (born Gaius Octavius, 23 September 63 BC; died 19 August AD 14), first Roman emperor from 27 BC.",
            ADD.format(g="Britannica and World History Encyclopedia", n="Augustus", s="")),
    new_src("Wikipedia on Rachel Carson", WP + "Rachel_Carson", "Rachel Carson",
            "Carson's death on 14 April 1964 and the phase-out of DDT use in the United States secured by 1972.",
            ADD.format(g="Britannica", n="Rachel Carson", s="") + "The article says activist groups had secured a phase-out by 1972 rather than that DDT was banned in 1972."),
    new_src("Wikipedia on Great Zimbabwe", WP + "Great_Zimbabwe", "Great Zimbabwe", "The Great Enclosure with walls as high as 11 m extending approximately 250 m.",
            ADD.format(g="UNESCO World Heritage Centre and Britannica", n="Great Zimbabwe", s="")),
    new_src("Wikipedia on the Taj Mahal", WP + "Taj_Mahal", "Taj Mahal",
            "The Taj Mahal commissioned in 1631, begun in 1632, the mausoleum completed in 1648 and the complex in 1653, more than 20,000 workers and artisans under Ustad Ahmad Lahori, and UNESCO designation in 1983.",
            ADD.format(g="UNESCO World Heritage Centre", n="Taj Mahal", s="")),
    new_src("Wikipedia on Borobudur", WP + "Borobudur", "Borobudur", "Borobudur's 2,672 relief panels and originally 504 Buddha statues, the Sailendra dynasty, the 1814 attention from Raffles, and the 1991 World Heritage listing.",
            ADD.format(g="UNESCO", n="Borobudur", s="")),
    new_src("Wikipedia on the Battle of Kadesh", WP + "Battle_of_Kadesh", "Battle of Kadesh",
            "The battle of May 1274 BCE (low chronology), the inconclusive result, 5,000 to 6,000 chariots in total, and the inscriptions at Abydos, Luxor, Karnak, Abu Simbel and the Ramesseum.",
            ADD.format(g="World History Encyclopedia", n="Battle of Kadesh", s="")),
    new_src("Wikipedia on the Olmec Colossal Heads", WP + "Olmec_colossal_heads", "Olmec colossal heads",
            "The colossal heads ranging in height from 1.17 to 3.4 m, carved from basalt from the Sierra de los Tuxtlas.",
            ADD.format(g="World History Encyclopedia", n="Olmecs", s="") + "The article does not give the Nahuatl name 'rubber people'."),
    new_src("Wikipedia on the Sokoto Caliphate", WP + "Sokoto_Caliphate", "Sokoto Caliphate",
            "Usman dan Fodio's migration to Gudu in February 1804 and Sultan Yunfa's declaration of war on 21 February 1804, control of Hausaland by 1808, and a population of 10-20 million by 1837.",
            ADD.format(g="BlackPast", n="Sokoto Caliphate and Usman dan Fodio", s="s")),
    new_src("Wikipedia on Homo habilis", WP + "Homo_habilis", "Homo habilis", "Homo habilis described in 1964 by Leakey et al. from Olduvai Gorge, living from about 2.4 to 1.65 million years ago.",
            ADD.format(g="the Smithsonian Human Origins Program", n="Homo habilis", s="") + "The article gives 2.4 to 1.65 mya, where the note gives 2.3-1.5 (or 2.4-1.4) Ma."),
    new_src("Wikipedia on Homo erectus", WP + "Homo_erectus", "Homo erectus", "The Dmanisi hominins about 1.8 million years ago and the earliest dispersal of Homo erectus out of Africa.",
            ADD.format(g="the Smithsonian Human Origins Program", n="Homo erectus", s="") + "The article gives some populations an average brain volume of about 1000 cc and does not give 900 cc."),
    new_src("Wikipedia on Sahelanthropus", WP + "Sahelanthropus", "Sahelanthropus", "Sahelanthropus tchadensis (Toumai), discovered in 2001 in northern Chad and dated to about 7 to 6 million years ago.",
            ADD.format(g="the Smithsonian Human Origins Program", n="Sahelanthropus tchadensis", s="")),
    new_src("Wikipedia on the Jomon Period", WP + "J%C5%8Dmon_period", "Jomon period",
            "Jomon dogu figurines, and Yayoi-style pottery found at a Jomon site in northern Kyushu by 800 BC with Korean-type settlements in western Kyushu from about 900 BCE.",
            ADD.format(g="the Jomon official site", n="Jomon Culture", s="") + "The article does not give pottery about 16,000 years old."),
    new_src("Wikipedia on Sannai-Maruyama", WP + "Sannai-Maruyama_site", "Sannai-Maruyama site", "Sannai-Maruyama occupied from about 3900 to 2200 BCE as the largest Jomon settlement known.",
            ADD.format(g="the Jomon official site", n="Jomon Culture", s="")),
    new_src("Wikipedia on the Marajoara Culture", WP + "Marajoara_culture", "Marajoara culture",
            "Ceramic occupation of Marajo island from 400 to 1400 AD, mound building, and an abandonment date around AD 1300.",
            ADD.format(g="ORIAS", n="Marajoara Culture", s="") + "The article gives 400-1400 AD for the ceramics where the note gives 400-1300, and does not give mounds up to 20 m."),
    new_src("Wikipedia on the Chinchorro Mummies", WP + "Chinchorro_mummies", "Chinchorro mummies",
            "Deliberate mummification beginning by about 5050 BCE and a tradition continuing about 3,000 years, ending around 1800 BCE.",
            ADD.format(g="UNESCO World Heritage Centre", n="Chinchorro Culture", s="")),
]


# --------------------------------------------------------------------------------------------------- per-source extras
SRC = {
    "National Geographic on the Mauryan Empire": {
        "used": "The Maurya Empire (321-185 BCE, founded around 321 BCE), the first pan-Indian empire, and Chandragupta's minister Kautilya, known for writing the Arthashastra.",
        "extra": "The page dates the empire 321-185 BCE (the notes say 322), and does not name Pataliputra or give Ashoka's reign (268-232 BCE), although it discusses the Ashoka pillars.",
    },
    "EBSCO on the Neolithic Revolution": {
        "used": "The Neolithic Revolution occurring around 12,000 years ago, with notable early agricultural developments in the Fertile Crescent, and its later arrival in the New World, Europe, Asia and Africa.",
        "extra": "The page does not mention independent centers in China, Mesoamerica or South America, potatoes or the Andes.",
    },
    "Lazaridis et al. 2025 Indo-European Origins": {
        "used": "The Caucasus Lower Volga people, in what is now Russia about 6,500 years ago, as the source of the Yamnaya and of the ancient Indo-Anatolian speakers, and the family of 400-plus languages spoken by more than 40 percent of the world's population.",
        "extra": "The page is a Harvard Gazette report on the 2025 studies, not the papers themselves. It says about 6,500 years ago and does not give 4400-4000 BCE.",
    },
    "Kuitems et al. 2021 L'Anse aux Meadows Dating": {
        "used": "Tree-ring dating of Norse activity at L'Anse aux Meadows to 1021 CE, Viking travel from about 793 to 1066, the settlement of Iceland by 874, and about 500 years of Norse colonization of Greenland.",
        "extra": "The page is a Smithsonian Magazine report on the study. It does not give Greenland about 985, Lindisfarne on 7 June 793, or the Iceland settlement range 870-930.",
    },
    "Penn Museum on Herodotus and the Scythians": {
        "used": "Scythian identity, Herodotus's account, and the frozen burials of the Altai Mountains at Pazyryk.",
        "extra": "The page describes the Pazyryk burials (water froze in the mounds and stayed permanently frozen) but does not mention Arzhan, its 5,600 gold objects or the cloak of 2,500 gold panthers.",
    },
    "WHO Smallpox Eradication": {
        "used": "Eradication declared on 8 May 1980 by the 33rd World Health Assembly, and about 300 million deaths in the 20th century.",
        "extra": "The page does not mention Jenner or 1796.",
    },
    "CDC on the 1918 Influenza Pandemic": {
        "used": "One third of the world's population (about 500 million) infected in 1918-1919, and deaths of about 50 million, possibly as high as 100 million.",
        "extra": "The page does not give a lower estimate of 17.4 million and does not describe the reconstruction of the virus in 2005 (its reference list includes 2005 papers).",
    },
    "Office of the Historian on the Haitian Revolution": {
        "used": "A massive rebellion in the French colony beginning on 22 August 1791, and Haiti as the second independent country in the Americas after the United States.",
        "extra": "The page does not use the name Saint-Domingue for the colony in the text read.",
    },
    "Phys.org on Ancient DNA and the South Pacific": {
        "used": "The Austronesian expansion beginning around 5,500 years ago, likely in Taiwan, and carrying farming peoples as far west as Madagascar and east to Rapa Nui; the Lapita peoples reaching Vanuatu about 3,000 years ago; and ancient DNA from Vanuatu, Tonga, French Polynesia and the Solomon Islands.",
        "extra": "The page does not give 1500-1000 BCE for the Lapita spread, more than 1,200 languages, Madagascar in the first millennium CE, or 2,800 BP for the Vanuatu individuals.",
    },
    "WHO COVID-19 Mortality Data": {
        "used": "The WHO estimate of 14.9 million excess deaths (range 13.3-16.6 million) associated with the COVID-19 pandemic in 2020 and 2021.",
        "extra": "This is the WHO news release of 5 May 2022. It does not give cumulative reported deaths (about 7 million, or 7.1 million by mid-2026).",
    },
    "United Nations Membership": {
        "used": "51 founding members in 1945 and 193 members today.",
        "extra": "The page does not give Ghana's independence on 6 March 1957 or the 17 African states of 1960.",
    },
    "Web Origins Sources (ICANN, CERN)": {
        "used": "Berners-Lee's March 1989 proposal at CERN, a line-mode browser available at CERN by March 1991, the announcement of his WWW software on Internet newsgroups in August 1991, and the release of the software into the public domain on 30 April 1993.",
        "extra": "The page does not mention the first ARPANET message (29 October 1969) and does not give 6 August 1991.",
    },
    "Encyclopedia of the Enlightenment Works (Encyclopedie, Wealth of Nations)": {
        "used": "The Encyclopedie (main work 1751-1772, supplement 1776-1777) edited by Diderot and d'Alembert.",
        "extra": "The page is about the Encyclopedie and does not mention The Wealth of Nations, its date or Kant's essay.",
    },
    "Museums of History NSW on the First Fleet": {
        "used": "The arrival of the last of the eleven ships of the First Fleet at Botany Bay on 20 January 1788.",
        "extra": "The page does not mention the move to Sydney Cove, the 1789 smallpox epidemic or the Mabo decision.",
    },
    "History.com on the Indian Removal Act": {
        "used": "Andrew Jackson's signing of the Indian Removal Act on 28 May 1830, and more than 10,000 deaths (an estimated 4,000 Cherokee) in the Trail of Tears.",
        "extra": "The page does not name the Choctaw, Chickasaw, Creek or Seminole, Worcester v. Georgia, or a Cherokee population of 16,000.",
    },
    "UK National Archives on Hong Kong and the Opium Wars": {
        "used": "The Treaty of Nanking (the cession of Hong Kong Island to Britain in perpetuity), the Convention for the Extension of Hong Kong Territory (a 99-year lease of the territory above Kowloon), and the causes of the First Opium War.",
        "extra": "The page does not give the Convention of Beijing of 1860 or its terms (Kowloon, legations, legalized opium) or a count of five treaty ports.",
    },
    "World History Encyclopedia on Martin Luther": {
        "used": "The Ninety-five Theses in October 1517 (nailed to the church door on 31 October 1517 according to tradition, which modern scholarship challenges), the Diet of Worms (1521), and the complete German Bible of 1534.",
        "extra": "The page does not give 1522 for the New Testament, and does not say the Theses were sent to Albrecht of Mainz (it mentions Albrecht and the sale of indulgences in 1516).",
    },
    "Waitangi Tribunal on the Maori and English Texts": {
        "used": "Kawanatanga versus sovereignty and tino rangatiratanga versus possession in the two texts, and the Treaty of Waitangi Act 1975.",
        "extra": "The page does not mention the New Zealand Wars of 1845-1872.",
    },
    "UCMP on the Carboniferous": {
        "used": "Carboniferous swamp forests that produced the coal from which the period takes its name.",
        "extra": "The page gives no dates for the swamp forests (the note's 360-300 Ma).",
    },
    "Metropolitan Museum on the Achaemenid Persian Empire": {
        "used": "The formation of the empire in 550 BCE when Cyrus II defeated Astyages of Media, its stabilization under Darius with roads and satraps, the fall of Sardis, and the buildings at Susa and Persepolis.",
        "extra": "The page does not mention the Indus, about twenty satrapies or the Royal Road.",
    },
    "Canadian Encyclopedia on the Thule Culture": {
        "used": "Early Inuit (Thule) groups from northern Alaska moving into the Eastern North American Arctic (Canada and Greenland) around 800 years ago, and their distinctness from the Dorset and Pre-Dorset.",
        "extra": "The page says around 800 years ago and does not give about 900 CE for the emergence in Alaska or the 12th century for Greenland.",
    },
    "Jomon Prehistoric Sites in Northern Japan Official Website": {
        "used": "The Jomon period of approximately 10,000 years until the Yayoi period, when full-scale rice cultivation began about 2,400 years ago, and the Sannai Maruyama Site.",
        "extra": "The page does not give pottery about 16,000 years old, Sannai-Maruyama dates, dogu, the UNESCO listing date, or 900 BCE for the Yayoi transition (it gives about 2,400 years ago and rice cultivation in northern Kyushu).",
    },
    "Metropolitan Museum on the Kushan Empire": {
        "used": "Kujula Kadphises uniting the tribes in the first century B.C. (as the Met writes it), Kushan wealth and Buddhist thought and visual arts, Kujula's son's gold coins, and Kanishka's rule from Purushapura and Mathura.",
        "extra": "The page puts Kujula Kadphises in the first century B.C., where the note says around 30 CE, and does not mention the Sasanian conquests after 225 CE.",
    },
    "Te Ara on Maori Arrival and Settlement": {
        "used": "First arrivals from East Polynesia between 1250 and 1300 CE, and the moa hunted to extinction.",
        "extra": "The page does not give 'under 150 years' for the moa extinction or the Maori Language Act 1987.",
    },
    "ORIAS on Ancient Marajó": {
        "used": "Marajoara mound building between CE 300 and 1350, on mounds where the people lived and held ceremonies.",
        "extra": "The page gives CE 300 to 1350 and does not give 400-1300 for ceramics or mounds up to 20 m.",
    },
    "World History Encyclopedia on the Kingdom of Nabatea": {
        "used": "A wealthy community near Petra by 312 BCE, the kingdom dated from 168 BCE, and its annexation by Rome under Trajan in 106 CE.",
        "extra": "The page does not mention the UNESCO inscription of Hegra in 2008; UNESCO on Al-Hijr Archaeological Site confirms 2008.",
    },
    "World History Encyclopedia on the Olmec Colossal Heads": {
        "used": "Olmec culture 1200-400 BCE and heads carved from basalt boulders whose principal source was in the Tuxtla Mountains.",
        "extra": "The page does not give the heads' height range (1.17 to 3.4 m; Wikipedia on the Olmec Colossal Heads does) or the Nahuatl 'rubber people' name.",
    },
    "World History Encyclopedia on Carthage and Tyrian Purple": {
        "used": "The traditional founding of Carthage in 814 BCE by the legendary Phoenician queen Dido, and an influx of refugees from Tyre after Alexander's conquests of 332 BCE.",
        "extra": "The page does not mention Sidon, Byblos, the 22-letter alphabet or murex; the alphabet is confirmed by Wikipedia on the Phoenician Alphabet.",
    },
    "Smithsonian Magazine on the Taino": {
        "used": "Greater Antilles chiefdoms under caciques, English words derived from Taino (canoe, hammock, barbecue, hurricane), a possible loss of 85 percent of the Taino population by the early 1500s, and surviving mitochondrial ancestry in Puerto Rico.",
        "extra": "The page gives 85 percent, not 70-85 percent, and does not mention zemis.",
    },
    "Education About Asia on Han-Xiongnu Relations": {
        "used": "The formation of the Xiongnu confederacy in 209 BCE, the Han-Xiongnu clash of 200 BCE, and the heqin ('Peace and Family Relations') treaty system.",
        "extra": "The page does not give the Xiongnu split about 51 BCE or the defeat of the northern Xiongnu in 89-93 CE.",
    },
    "Minority Rights Group on the Sakha": {
        "used": "The 2010 census count of 478,085 Sakha and a major revolt against Russian occupation in 1642.",
        "extra": "The page does not mention yasak or its abolition in 1917.",
    },
    "SERC on the Jack Hills Zircons": {
        "used": "Jack Hills zircons as the oldest Earth materials (4.0-4.4 Ga, a single grain at 4.4 Ga) from a quartzite/metaconglomerate unit in Western Australia, and oxygen isotopes showing magma from recycled rock that had interacted with surface waters.",
        "extra": "The page does not give 4.404 Ga or name the Narryer Terrane.",
    },
    "Durham University on Jericho": {
        "used": "Kathleen Kenyon's excavations at Ancient Jericho (1952-58) and the Durham Oriental Museum's collections from them.",
        "extra": "The page text read does not mention plastered skulls, 1953 or a depth of 250 m below sea level.",
    },
    "Encyclopedia.com on Potosi": {
        "used": "Silver discovered at Cerro Rico in 1545, Toledo's adaptation of the mita in 1573, and amalgamation from the mid-1570s.",
        "extra": "The page does not give a population of about 160,000 by 1650.",
    },
    "Scientific American on Xingu Garden Cities": {
        "used": "The Xingu settlement network, extensive ditches, a possible population of 30,000 to 50,000, and the people molding forests and wetlands about 1,500 years ago or before.",
        "extra": "The page does not give 28 settlements, c. 1200-1600 CE, ditches about 3 m deep or plazas about 150 m.",
    },
    "Smithsonian Human Origins Program": {
        "used": "Summaries of the early human species accepted by most scientists, including Sahelanthropus tchadensis.",
        "extra": "The page text read does not give brain size, Dmanisi, Olduvai, 1964, 2001 or ages for Homo erectus, Homo habilis or Sahelanthropus; the specific figures now cite Wikipedia articles.",
    },
    "Natural History Museum on the Dresser Formation": {
        "used": "Structures in 3.48-billion-year-old Australian rocks (the Dresser Formation of Western Australia) as the oldest evidence of life on Earth.",
        "extra": "The page does not name the Pilbara.",
    },
    "Poverty Point Monumental Earthworks Sources": {
        "used": "Poverty Point as a system of monumental mounds and ridges built by hunter-fisher-gatherers in Louisiana's Lower Mississippi Valley.",
        "extra": "This State Department press page does not give 3,700-3,100 BP, the count of mounds and ridges, Mound A or the inscription date; UNESCO on Poverty Point gives all but Mound A.",
    },
    "Taj Mahal Official Site and History Sources": {
        "used": "Construction of the Taj complex beginning about 1631, and its buildings and gardens finished in 1653.",
        "extra": "The page does not give 1632, more than 20,000 workers, Ahmad Lahori or the UNESCO listing; UNESCO on the Taj Mahal and Wikipedia on the Taj Mahal do.",
    },
    "World History Encyclopedia on the Battle of Kadesh": {
        "used": "The battle of 1274 BCE, Hittite chariots (3,500) and infantry (37,000), and the indecisive outcome.",
        "extra": "The page does not give 5,000-6,000 chariots in total, the month of May, or Abu Simbel and Karnak; Wikipedia on the Battle of Kadesh does.",
    },
    "World History Encyclopedia on the Classic Maya Collapse": {
        "used": "Drought, warfare between city-states and overpopulation among the causes proposed for the Maya collapse, and the prosperity of some northern cities.",
        "extra": "The page does not give the last Long Count date at Tonina (909 CE) or the Yok Balum cave record, and does not name Tonina.",
    },
    "Britannica on Chauvet-Pont d'Arc": {
        "extra": "The page gives a majority of samples about 35,500 years old and a smaller group 30,000 to 31,000 years old; the note's phases (37,000-33,500 and 31,000-28,000) match neither this page nor LSCE.",
    },
    "LSCE on Chauvet Cave Radiocarbon Dating": {
        "used": "An early Aurignacian phase between 37,000 and 34,000 years ago and a more recent Gravettian phase between 34,000 and 25,000 years ago at the Chauvet Cave, and its UNESCO listing on 22 June 2014.",
        "extra": "The page gives 37-34 ka and 34-25 ka, not the note's 37,000-33,500 and 31,000-28,000.",
    },
    "EBSCO Research Starters on Cixi": {
        "used": "Cixi's life (1835-1908), her regency from 1861, backing of the Boxers and war declaration of 21 June 1900, the Boxer Protocol signed in September, constitutional reforms announced in 1908, and her legacy.",
        "extra": "The page does not use the term 'New Policies'; it describes reforms after the Boxer Rebellion and constitutional reforms announced in 1908.",
    },
    "BlackPast on the Sokoto Caliphate": {
        "used": "The Sultanate of Sokoto (1804-1903), its conquests ending by 1815 across most of northern Nigeria, and its status as the most populous empire in West Africa by 1837.",
        "extra": "The page does not give February 1804, 1808 or the 10-20 million population; Wikipedia on the Sokoto Caliphate does.",
    },
    "NOAA Global Monitoring Laboratory CO2 Trends": {
        "used": "The NOAA GML 'Trends in CO2' page and its growth-rate table of annual CO2 values.",
        "extra": "The numeric values in the table were not in the text read (the page fills them by script), so the figures of 424.5 and 422.8 ppm now cite three NOAA GML data files. The pre-industrial baseline of about 280 ppm is not on this page.",
    },
    "World History Encyclopedia on Siddhartha Gautama": {
        "used": "Traditional dates (c. 563-483 BCE), and the awakening near Bodh Gaya.",
        "extra": "The page does not give the later scholarly date of death between about 411 and 400 BCE that the note mentions.",
    },
    "UNESCO World Heritage Centre": {"skip": True},
    "World History Encyclopedia": {"skip": True},
}

GENERIC_UPDATES = [
    {"title": "World History Encyclopedia", "mark": "done",
     "set": {"access": "not-consulted", "verified": False,
             "access_route": "none: this title stands for the whole site; the url is the single Ibn Battuta article that was fetched under it"},
     "used": "Stands for World History Encyclopedia as a whole when a note cites it without naming an article. A check that cites only this note is not confirmed by any text read; wherever a Tier 5 fetch of the specific article succeeded, the check now cites that article's source note instead (see the source notes titled World History Encyclopedia on ...).",
     "caveats": ("The url is the Ibn Battuta article, the only page fetched under this title (read in full on 2026-09-27, 15,000 or so characters); it gives 1352-1355 for his travels and does not give 117,000 km or Ibn Juzayy. "
                 "The checks that cited this note for other subjects were unconfirmed; in Tier 5 they were re-pointed to the specific World History Encyclopedia articles where the article was fetched. "
                 "A tertiary, non-academic source for general readers.")},
    {"title": "UNESCO World Heritage Centre", "mark": "done",
     "set": {"access": "not-consulted", "verified": False,
             "access_route": "none: this title stands for the whole site; the url is the single Cahokia Mounds page that was fetched under it"},
     "used": "Stands for the UNESCO World Heritage Centre as a whole when a note cites it without naming a site. A check that cites only this note is not confirmed by any text read; wherever a Tier 5 fetch of the specific site page succeeded, the check now cites that page's source note instead (see the source notes titled UNESCO on ...).",
     "caveats": ("The url is the Cahokia Mounds page, the only page fetched under this title; it was re-fetched in Tier 5 as UNESCO on Cahokia Mounds. "
                 "The checks that cited this note for other sites were unconfirmed; in Tier 5 they were re-pointed to the specific UNESCO site pages that were fetched.")},
]

# ------------------------------------------------------------------------------------------------------ note patches
N = {}


def _n(name):
    return N.setdefault(name, {"note": name, "replace_checks": [], "drop_checks": [], "checks": [], "replace": [], "sources": []})


def _src(name, claim):
    m = re.search(r"\[([^\]]*)\]\s*$", claim)
    assert m, claim
    for s in [x.strip() for x in m.group(1).split(";")]:
        if s not in _n(name)["sources"]:
            _n(name)["sources"].append(s)


def rc(name, old, new):
    _n(name)["replace_checks"].append([old, new])
    _src(name, new)


def add(name, claim):
    _n(name)["checks"].append(claim)
    _src(name, claim)


def drop(name, old):
    _n(name)["drop_checks"].append(old)


WHE = "World History Encyclopedia on "
WPD = "Wikipedia on "
UN_ = "UNESCO on "

# --- eras
rc("Bronze Age", "Mesopotamian writing about 3400-3200",
   "Cuneiform, the first true writing system, was developed by the Sumerians of Mesopotamia circa 3600/3500 BCE and further developed at Uruk circa 3200 BCE; the Indus Valley Civilization's Mature Harappan phase ran c. 2600-1900 BCE "
   "[World History Encyclopedia on Cuneiform; World History Encyclopedia on the Indus Valley Civilization]")
rc("Bronze Age", "Sea Peoples attack recorded about 1177",
   "Scholars use 1177 BCE as a kind of shorthand for the beginning of the Late Bronze Age collapse, not as a definitive date [World History Encyclopedia on the Late Bronze Age Collapse]")
rc("Bronze Age Collapse", "Sea Peoples attack recorded in Ramesses",
   "Scholars use 1177 BCE as a kind of shorthand for the beginning of the Late Bronze Age collapse, not as a definitive date [World History Encyclopedia on the Late Bronze Age Collapse]")
rc("Iron Age", "Proto-Sinaitic about 1800",
   "The Phoenician alphabet proper is an abjad of 22 consonant letters [Wikipedia on the Phoenician Alphabet]")
rc("Alphabet", "Proto-Sinaitic about 1800",
   "The Phoenician alphabet proper uses 22 consonant letters, and in the early Greek alphabet vowels were added to the consonant-only Phoenician letters [Wikipedia on the Phoenician Alphabet]")
rc("Levant and Anatolia", "Phoenician 22-letter alphabet",
   "The Phoenician alphabet proper uses 22 consonant letters [Wikipedia on the Phoenician Alphabet]")
rc("Levant and Anatolia", "Gobekli Tepe earliest structures",
   "Göbekli Tepe's distinctive limestone T-shaped pillars are up to 5.50 m tall, and Çatalhöyük was inscribed on the World Heritage List in 2012 [UNESCO on Gobekli Tepe; UNESCO on Catalhoyuk]")
rc("Neolithic", "Gobekli Tepe earliest structures",
   "Göbekli Tepe's distinctive limestone T-shaped pillars are up to 5.50 m tall, and Çatalhöyük was inscribed on the World Heritage List in 2012 [UNESCO on Gobekli Tepe; UNESCO on Catalhoyuk]")
rc("Neolithic", "Neolithic Revolution began about 12,000 years ago in Southwest Asia",
   "The Neolithic Revolution occurred around 12,000 years ago, with notable early agricultural developments in the Fertile Crescent [EBSCO on the Neolithic Revolution]")
rc("The Agricultural Revolution", "Neolithic Revolution began about 12,000 years ago",
   "The Neolithic Revolution occurred around 12,000 years ago, with notable early agricultural developments in the Fertile Crescent [EBSCO on the Neolithic Revolution]")
drop("Andes", "Potato domesticated in the Andes")
rc("Andes", "Machu Picchu built about 1450",
   "Machu Picchu stands 2,430 m above sea level and was made known to the outside world in 1911 [UNESCO on Machu Picchu]")
rc("Machu Picchu", "Elevation 2,430 m",
   "Machu Picchu stands 2,430 m above sea level, was made known to the outside world in 1911, and was inscribed on the World Heritage List in 1983 [UNESCO on Machu Picchu]")
rc("Classical Antiquity", "Maurya Empire 322-185",
   "National Geographic dates the Maurya Empire, the first pan-Indian empire, to 321-185 BCE; the Achaemenid Persian Empire began in 550 BCE and ended in 330 BCE "
   "[National Geographic on the Mauryan Empire; Metropolitan Museum on the Achaemenid Persian Empire]")
rc("Industrial Age", "World population about 1 billion around 1804",
   "The UN estimated that the world population first reached one billion in 1804 [Wikipedia on World Population]")
drop("Information Age", "World population about 2.5 billion in 1950")
rc("Great Acceleration", "World population about 1 billion around 1804",
   "The UN estimated that the world population first reached one billion in 1804, and projected that it would reach 8 billion on 15 November 2022 [Wikipedia on World Population; UN World Population Milestones]")
rc("Medieval Period", "Umayyad 661-750 and Abbasid",
   "The Umayyad Dynasty ruled 661-750 CE; the Abbasids assumed the caliphate in 750 CE and their rule ended in 1258 CE when the Mongols destroyed Baghdad; the Sosso were defeated at Kirina in 1235, founding the Mali Empire "
   "[World History Encyclopedia on the Umayyad Dynasty; World History Encyclopedia on the Abbasid Caliphate; World History Encyclopedia on the Mali Empire]")
rc("Arabian Peninsula", "Hijra in 622",
   "Muhammad and his followers made the Hijrah from Mecca to Medina in 622 CE [Wikipedia on the Hijrah]")
rc("Central Asian Steppe", "Proto-Indo-Anatolian community in the Caucasus",
   "The Caucasus Lower Volga people appear to be the original source of the Yamnaya and of the ancient Indo-Anatolian speakers, and lived in what is now Russia about 6,500 years ago [Lazaridis et al. 2025 Indo-European Origins]")
rc("Europe", "Lindisfarne raid 793",
   "Viking travel is dated from about 793 to 1066; the Norse colonized Greenland for almost 500 years; Norse occupation of L'Anse aux Meadows is dated to 1021 CE [Kuitems et al. 2021 L'Anse aux Meadows Dating]")
rc("Norse", "Lindisfarne 7 June 793",
   "Viking travel is dated from about 793 to 1066; the Norse settled Iceland by 874 and colonized Greenland for almost 500 years; Norse occupation of L'Anse aux Meadows is dated to 1021 CE [Kuitems et al. 2021 L'Anse aux Meadows Dating]")
rc("Mediterranean Basin", "Athenian democracy about 508",
   "Cleisthenes set Athens on a democratic footing in 508 BC and is called the father of Athenian democracy [Wikipedia on Cleisthenes]")
rc("Mesopotamia", "Cuneiform about 3400-3200",
   "Cuneiform was first developed by the Sumerians of Mesopotamia circa 3600/3500 BCE and further developed at Uruk circa 3200 BCE; during the Uruk Period (4000-3100 BCE) cities began to develop across Mesopotamia and Uruk became the most influential "
   "[World History Encyclopedia on Cuneiform; World History Encyclopedia on Uruk]")
rc("North America", "Poverty Point occupied about 3,700",
   "Poverty Point was built by hunter-fisher-gatherers between 3700 and 3100 BP; Cahokia's society may have had a population of 10-20,000 at its peak between 1050 and 1150; Chaco Canyon was a major centre of ancestral Pueblo culture between 850 and 1250 "
   "[UNESCO on Poverty Point; UNESCO on Cahokia Mounds; UNESCO on Chaco Culture]")
rc("North America", "Tuscarora joined the Haudenosaunee",
   "After 1722 the Iroquoian-speaking Tuscarora were accepted into the confederacy, henceforth known as the Six Nations [Wikipedia on the Iroquois]")
rc("Oceania", "Aotearoa settled 1250-1300",
   "Current understanding is that the first arrivals in Aotearoa came from East Polynesia between 1250 and 1300 CE [Te Ara on Maori Arrival and Settlement]")
rc("Polynesian Settlement of the Pacific", "Aotearoa first settled 1250-1300",
   "The first arrivals in Aotearoa came from East Polynesia between 1250 and 1300 CE, and the Lapita people settled Remote Oceania between 1100 and 900 BCE, with Lapita settlements in the Bismarck Archipelago as early as 2000 BCE "
   "[Te Ara on Maori Arrival and Settlement; World History Encyclopedia on Polynesian Navigation]")
rc("South Asia", "Indus Valley mature phase 2600-1900",
   "The Indus Valley Civilization's Mature Harappan phase ran c. 2600-1900 BCE [World History Encyclopedia on the Indus Valley Civilization]")
rc("Indus Valley Civilization", "Mature Harappan phase 2600-1900",
   "The Indus Valley Civilization's Mature Harappan phase ran c. 2600-1900 BCE [World History Encyclopedia on the Indus Valley Civilization]")
rc("Southeast Asia", "Khmer Empire founded 802",
   "The Khmer Empire lasted from 802 CE to 1431 CE, and Angkor was inscribed on the World Heritage List in 1992 [World History Encyclopedia on the Khmer Empire; UNESCO on Angkor]")
rc("Siberia and the Arctic", "Scythian tombs at Arzhan and Pazyryk",
   "Burials in the Altai Mountains, Pazyryk and other sites, contained objects normally lost to archaeologists, because water froze in the mounds and remained permanently frozen [Penn Museum on Herodotus and the Scythians]")
rc("Sub-Saharan Africa", "Ezana converted about 333",
   "Ezana I of Axum officially adopted Christianity in the mid-4th century CE; the Great Enclosure at Great Zimbabwe has walls as high as 11 m; Timbuktu was inscribed on the World Heritage List in 1988; the Sosso were defeated at Kirina in 1235, founding the Mali Empire "
   "[World History Encyclopedia on Aksum; Wikipedia on Great Zimbabwe; UNESCO on Timbuktu; World History Encyclopedia on the Mali Empire]")
rc("Emergence of Symbolic Art", "Sulawesi warty pig at least 45.5",
   "Sulawesi warty pig painting at least 45.5 ka; narrative art 51.2 ka; Blombos engraved ochres 75-100 ka; most Chauvet samples about 35,500 years old; Lascaux about 17 ka "
   "[Brumm et al. 2021 Sulawesi Warty Pig Painting; Oktaviana et al. 2024 Sulawesi Narrative Cave Art; Henshilwood et al. 2009 Blombos Engraved Ochres; Britannica on Chauvet-Pont d'Arc]")
rc("Invention of Writing", "Mesopotamia about 3400-3200",
   "Cuneiform was first developed by the Sumerians circa 3600/3500 BCE and further developed at Uruk circa 3200 BCE; Egyptian writing was already in use before the Early Dynastic Period (circa 3150 BCE); Chinese writing developed from oracle-bone divination circa 1200 BCE; "
   "Mesoamerican writing arose independently, with some evidence as early as 500 BCE [World History Encyclopedia on Cuneiform; World History Encyclopedia on Writing]")
rc("Mongol Conquests", "Empire about 24 million km2",
   "Abbasid rule came to an end in 1258 CE after the Mongols destroyed Baghdad [World History Encyclopedia on the Abbasid Caliphate]")
rc("Rise of Islam", "Umayyad Caliphate 661-750",
   "The Umayyad Dynasty ruled 661-750 CE; Muslim conquest of Spain began in 711 CE and the Umayyads defeated the Chach dynasty in Sindh in 711-713; the Abbasids assumed the caliphate in 750 CE and their rule ended in 1258 CE; the Hijrah to Medina was in 622 CE "
   "[World History Encyclopedia on the Umayyad Dynasty; Wikipedia on the Arab Conquest of Sindh; World History Encyclopedia on the Abbasid Caliphate; Wikipedia on the Hijrah]")
rc("The Urban Revolution", "Uruk 40,000-80,000",
   "V. Gordon Childe introduced the term 'urban revolution' in the 1930s and brought the concept to a much larger audience in his 1950 article in Town Planning Review; the Uruk Period (4000-3100 BCE) saw cities begin to develop across Mesopotamia "
   "[Wikipedia on the Urban Revolution; World History Encyclopedia on Uruk]")
rc("Treaty of Waitangi", "English and Maori texts differ",
   "The English and Maori texts differ (sovereignty translated as kawanatanga; possession versus tino rangatiratanga); the Waitangi Tribunal was established in 1975 [Waitangi Tribunal on the Maori and English Texts]")

# --- events
rc("Age of Revolutions", "Slave uprising in northern Saint-Domingue",
   "A massive slave rebellion in the French colony began on 22 August 1791, and the Haitian Revolution created the second independent country in the Americas [Office of the Historian on the Haitian Revolution]")
rc("American Revolution", "Lexington and Concord 19 April 1775",
   "Lexington and Concord 19 April 1775; Declaration 4 July 1776; French alliance 6 February 1778; Yorktown 1781; Treaty of Paris 3 September 1783 [National Park Service Timeline of the American Revolution]")
add("American Revolution",
    "During the American Revolution the Oneida and Tuscarora fought alongside the Patriots while the other nations of the Iroquois confederacy allied with the British [Wikipedia on the Iroquois]")
rc("Austronesian Expansion", "Austronesian expansion began about 5,500 years ago",
   "The Austronesian expansion began around 5,500 years ago, likely in Taiwan, and carried farming peoples as far west as Madagascar and east to Rapa Nui; Austronesian-speaking Lapita groups expanded into Remote Oceania about 3,000 years ago [Phys.org on Ancient DNA and the South Pacific]")
rc("Lapita Culture", "Lapita culture spread across Melanesia",
   "Austronesian-speaking groups associated with the Lapita pottery culture expanded east into Remote Oceania (Vanuatu, New Caledonia, Fiji and western Polynesia) about 3,000 years ago, and ancient DNA from Lapita-era individuals in Vanuatu has been sequenced "
   "[Phys.org on Ancient DNA and the South Pacific; World History Encyclopedia on Polynesian Navigation]")
rc("Battle of Kadesh", "Battle in May 1274 BCE at Kadesh",
   "The battle took place at Kadesh on the Orontes in May 1274 BCE (low chronology); the outcome was inconclusive; some 5,000 to 6,000 chariots were involved in total; the events were recorded in temples including Abu Simbel and Karnak "
   "[World History Encyclopedia on the Battle of Kadesh; Wikipedia on the Battle of Kadesh]")
rc("Classic Maya Collapse", "Last Long Count date at Tonina",
   "Proposed causes of the Maya collapse include drought, warfare between city-states and overpopulation, and some northern Maya cities prospered in the period [World History Encyclopedia on the Classic Maya Collapse]")
rc("Colonization of Land", "Earliest land-plant cryptospores",
   "Cryptospores first appear around 470 million years ago; the Gilboa forest dates to about 385 million years ago in the Devonian; Carboniferous swamp forests produced coal; tetrapods evolved from lobe-finned fishes in the Devonian "
   "[Wikipedia on Cryptospores; ScienceDaily on the Gilboa Fossil Forest; UCMP on the Carboniferous; Wikipedia on the Evolution of Tetrapods]")
rc("COVID-19 Pandemic", "WHO estimate of 14.9 million",
   "The WHO estimated 14.9 million excess deaths (range 13.3 to 16.6 million) associated with the COVID-19 pandemic in 2020 and 2021 [WHO COVID-19 Mortality Data]")
rc("Decolonization", "UN founded with 51 members",
   "The UN's membership has grown from the original 51 Member States in 1945 to the current 193 [United Nations Membership]")
rc("Digital Revolution", "First ARPANET message",
   "Tim Berners-Lee proposed the World Wide Web at CERN in March 1989, a line-mode browser was available at CERN by March 1991, and in August 1991 he announced his WWW software on Internet newsgroups [Web Origins Sources (ICANN, CERN)]")
rc("Enlightenment", "Encyclopedie published 1751-1772",
   "The main work of the Encyclopedie appeared between 1751 and 1772, with a supplement published from 1776 to 1777 [Encyclopedia of the Enlightenment Works (Encyclopedie, Wealth of Nations)]")
rc("First Fleet and the Colonization of Australia", "Eleven ships reached Botany Bay",
   "The last of the eleven ships of the First Fleet arrived at Botany Bay on 20 January 1788 [Museums of History NSW on the First Fleet]")
rc("Holocaust", "About six million Jews murdered",
   "At the Wannsee conference on 20 January 1942 officials met to coordinate the Final Solution to the Jewish Question, with the Nuremberg Laws as a basis for determining who was a Jew, and the SS envisioned some 11 million Jews being eradicated "
   "[USHMM Holocaust Encyclopedia on the Wannsee Conference]")
rc("Indian Removal and the Trail of Tears", "Act signed 28 May 1830",
   "Andrew Jackson signed the Indian Removal Act on 28 May 1830; the mass migration resulted in more than 10,000 deaths (an estimated 4,000 Cherokee) and became known as the Trail of Tears [History.com on the Indian Removal Act]")
rc("Indo-European Language Spread", "Indo-European languages are the first language of roughly 40",
   "Over 3.4 billion people (42 percent of the global population) speak an Indo-European language as a first language, and the family of 400-plus languages is spoken by more than 40 percent of the world's population "
   "[Wikipedia on Indo-European Languages; Lazaridis et al. 2025 Indo-European Origins]")
rc("Indo-European Language Spread", "2025 Nature papers place",
   "The Caucasus Lower Volga people appear to be the original source of the Yamnaya and of the ancient Indo-Anatolian speakers, about 6,500 years ago [Lazaridis et al. 2025 Indo-European Origins]")
add("Indo-European Language Spread",
    "Recent ancient DNA data suggest that the Anatolian branch of Indo-European did not emerge from the Steppe but from further south, in or near the northern arc of the Fertile Crescent [Heggarty et al. 2023 Indo-European Language Trees]")
rc("Modern Climate Change", "About 1.1 C above 1850-1900",
   "Global surface temperature was around 1.1 C above 1850-1900 in 2011-2020, and the Mauna Loa annual mean CO2 concentration for 2024 was 424.61 ppm against a global marine surface mean of 422.79 ppm "
   "[IPCC AR6 Synthesis Report 2023; NOAA GML Mauna Loa Annual Mean CO2 Data; NOAA GML Global Annual Mean CO2 Data]")
rc("Modern Climate Change", "Global average atmospheric CO2 was 422.8",
   "The global annual mean atmospheric CO2 was 422.79 ppm in 2024 against 419.35 ppm in 2023, and the 2024 growth rate was 3.76 ppm [NOAA GML Global Annual Mean CO2 Data; NOAA GML Global Annual Growth Rate of CO2]")
rc("Opium Wars", "Treaty of Nanking: Hong Kong",
   "Under the Treaty of Nanking the Emperor of China ceded the island of Hong Kong to Britain in perpetuity, and a later lease granted Britain the territory above Kowloon (the New Territories) for 99 years [UK National Archives on Hong Kong and the Opium Wars]")
rc("Protestant Reformation", "Theses of 31 October 1517",
   "According to tradition Luther nailed his Theses to the Wittenberg church door on 31 October 1517, though modern scholarship challenges this; he refused to recant at the Diet of Worms in April 1521; he published the complete Bible in German in 1534 "
   "[World History Encyclopedia on Martin Luther]")

# --- people
rc("Akhenaten", "Reign about 1353-1336",
   "Akhenaten (1353-1336 BCE), a pharaoh of the 18th Dynasty, moved the capital of Egypt from Thebes to the city he founded, Akhetaten, which came to be known as Amarna [World History Encyclopedia on Akhenaten]")
rc("Alexander the Great", "Born 356 BCE; died 13 June",
   "Alexander was born on 21 July 356 BCE and died on 10 or 11 June 323 BCE in Babylon [World History Encyclopedia on Alexander the Great]")
rc("Alexander's Conquests", "Alexander born 356 BCE, died Babylon",
   "Alexander was born on 21 July 356 BCE and died on 10 or 11 June 323 BCE, after returning to Babylon; he defeated Darius III at Gaugamela in 331 BCE; his army mutinied in 326 BCE and refused to go further [World History Encyclopedia on Alexander the Great]")
rc("Augustus", "Born 23 September 63 BCE",
   "Augustus (born Gaius Octavius, 23 September 63 BC; died 19 August AD 14) was the first Roman emperor, from 27 BC until his death in AD 14 [Wikipedia on Augustus; World History Encyclopedia on Augustus]")
rc("Genghis Khan", "Proclaimed Great Khan 1206",
   "Genghis Khan founded the Mongol Empire, which he ruled from 1206 until his death in 1227; his body was taken back to Mongolia for burial but the location of his tomb was kept secret [World History Encyclopedia on Genghis Khan]")
rc("Hammurabi", "Reign 1792-1750 BCE",
   "Hammurabi reigned 1792-1750 BCE as the sixth king of the Amorite First Dynasty of Babylon; the stele of his law code, now in the Louvre, was rediscovered in 1901 at Susa "
   "[World History Encyclopedia on Hammurabi; Wikipedia on the Code of Hammurabi]")
rc("Ibn Battuta", "About 117,000 km",
   "Ibn Battuta travelled around 117,000 km; he dictated an account of his journeys in Arabic to Ibn Juzayy; he set out with a caravan in February 1352 and set off for Sijilmasa in September 1353 [Wikipedia on Ibn Battuta]")
rc("Mahatma Gandhi", "Salt March 12 March",
   "The Salt March ran from 12 March to 6 April 1930; Britain granted independence in August 1947; Gandhi was shot dead on 30 January 1948 [Wikipedia on Mahatma Gandhi]")
rc("Marie Curie", "Physics Nobel 1903",
   "The 1903 Nobel Prize in Physics was divided between Antoine Henri Becquerel and, jointly, Pierre Curie and Marie Curie; the 1911 Nobel Prize in Chemistry was awarded to Marie Curie "
   "[NobelPrize.org on the 1903 Nobel Prize in Physics; NobelPrize.org on the 1911 Nobel Prize in Chemistry]")
rc("Antibiotics", "Nobel Prize in Physiology or Medicine 1945",
   "The Nobel Prize in Physiology or Medicine 1945 was awarded jointly to Sir Alexander Fleming, Ernst Boris Chain and Sir Howard Walter Florey for the discovery of penicillin [NobelPrize.org on the 1945 Nobel Prize in Physiology or Medicine]")
rc("Pachacuti", "Sapa Inca 1438-1471/72",
   "Pachacuti Inca Yupanqui (1438-1471 CE) founded the Inca empire with conquests in the Cuzco Valley and beyond, and Tupac Inca Yupanqui took over as Sapa Inca and continued his father's imperial plans [World History Encyclopedia on Pachacuti]")
rc("Rachel Carson", "Silent Spring September 1962",
   "Silent Spring was published in 1962; the US EPA began in 1970; Carson died on 14 April 1964; by 1972 activist groups had secured a phase-out of DDT use in the United States [US EPA History; Wikipedia on Rachel Carson]")
rc("Siddhartha Gautama", "Traditional dates c. 563-483",
   "Traditional dates c. 563-483 BCE; after his asceticism he sat beneath a Bodhi tree at Bodh Gaya [World History Encyclopedia on Siddhartha Gautama]")
rc("Usman dan Fodio", "Jihad began February 1804",
   "Usman dan Fodio and his followers migrated to Gudu in February 1804, and Sultan Yunfa declared war on him on 21 February 1804; the Sultanate of Sokoto followed (1804-1903) [Wikipedia on the Sokoto Caliphate; BlackPast on the Sokoto Caliphate]")
rc("Zheng He", "Seven voyages 1405-1433",
   "Zheng He (born 1371, died 1433 or 1435) commanded seven treasure voyages between 1405 and 1433 [Wikipedia on Zheng He]")

# --- peoples and cultures
rc("Achaemenid Persians", "Empire 550-330 BCE from Anatolia",
   "The Achaemenid Persian Empire (550-330 BCE) began when Cyrus II defeated Astyages of Media; under Darius it was stabilized with roads and a system of governors (satraps), and the buildings at Susa and Persepolis were built "
   "[Metropolitan Museum on the Achaemenid Persian Empire]")
rc("Ancient Greeks", "Athenian democracy about 508",
   "Cleisthenes set Athens on a democratic footing in 508 BC; the Peloponnesian War was fought from 431 to 404 BCE [Wikipedia on Cleisthenes; World History Encyclopedia on the Peloponnesian War]")
rc("Aztec Empire", "Conquest by Spain 1519-1521",
   "Cortes overthrew the Aztec empire between 1519 and 1521, and the Aztecs, led by Cuauhtemoc, collapsed on 13 August 1521 [Britannica on Hernan Cortes; World History Encyclopedia on the Aztec Empire]")
rc("Chinchorro Culture", "Culture about 5450-890 BCE",
   "The Chinchorro culture lived on the northern Atacama coast from approximately 5450 BCE to 890 BCE, deliberate mummification began by about 5050 BCE and the tradition continued about 3,000 years, and the site was inscribed in 2021 "
   "[UNESCO on Chinchorro Settlement and Artificial Mummification; Wikipedia on the Chinchorro Mummies]")
rc("Haudenosaunee Confederacy", "Founding date debated",
   "The date of the Great Law of Peace is debated, likely between 1142 and 1660, and the Tuscarora were accepted into the confederacy after 1722 [Wikipedia on the Iroquois]")
rc("Inca Empire", "Conquest under Pachacuti from 1438",
   "After the defeat of the Chanca in 1438 the Incas under Pachacuti began to expand; the empire had some 10 million subjects speaking over 30 languages, and its span is dated between 1400 and 1533 CE, with a civil war between Waskar and Atahualpa as Europeans arrived "
   "[World History Encyclopedia on the Inca Empire; World History Encyclopedia on Pachacuti]")
rc("Inuit and the Thule Expansion", "Thule culture emerged about 900",
   "Early Inuit (Thule) groups from northern Alaska moved into the Eastern North American Arctic (Canada and Greenland) around 800 years ago, and the early Inuit are distinct from the Dorset and Pre-Dorset [Canadian Encyclopedia on the Thule Culture]")
rc("Jomon Culture", "Pottery about 16,000 years old",
   "The Jomon period lasted about 10,000 years until the Yayoi period, when full-scale rice cultivation began about 2,400 years ago; Sannai-Maruyama was occupied from 3900 to 2200 BCE; Jomon dogu figurines survive; Yayoi-style pottery was found at a Jomon site in northern Kyushu by 800 BC; "
   "the Jomon Prehistoric Sites were inscribed in 2021 [Jomon Prehistoric Sites in Northern Japan Official Website; Wikipedia on Sannai-Maruyama; Wikipedia on the Jomon Period; UNESCO on the Jomon Prehistoric Sites]")
rc("Kushan Empire", "Kujula Kadphises united the Yuezhi",
   "The Met writes that Kujula Kadphises united the disparate tribes in the first century B.C.; Kushan territory was marked by flourishing Buddhist thought and visual arts; Kujula's son was the first Indian ruler to strike gold coins in imitation of the Roman aureus; Kanishka's rule was administered from Purushapura and Mathura "
   "[Metropolitan Museum on the Kushan Empire]")
rc("Mali Empire", "Founded after Kirina",
   "The Sosso were defeated at Kirina in 1235, and Mansa Musa I reigned 1312-1337 [World History Encyclopedia on the Mali Empire]")
rc("Maori", "Settlement about 1250-1300",
   "The first arrivals came from East Polynesia between 1250 and 1300 CE, and the moa were hunted to extinction [Te Ara on Maori Arrival and Settlement]")
rc("Marajoara Culture", "Ceramic tradition dated 400-1300",
   "Between CE 300 and 1350 Marajo island was home to a people who built huge mounds to live on and hold religious ceremonies; the ceramic occupation is dated 400 to 1400 AD, with abandonment around AD 1300 [ORIAS on Ancient Marajó; Wikipedia on the Marajoara Culture]")
rc("Maurya Empire", "Maurya Empire 322-185",
   "National Geographic dates the Maurya Empire to 321-185 BCE; Chandragupta's minister Kautilya is known for writing the Arthashastra [National Geographic on the Mauryan Empire]")
rc("Nabataeans", "First recorded in 312 BCE",
   "A wealthy community was thriving near Petra by 312 BCE; the kingdom was annexed by Rome under Trajan in 106 CE; Hegra was inscribed on the World Heritage List in 2008 [World History Encyclopedia on the Kingdom of Nabatea; UNESCO on Al-Hijr Archaeological Site]")
rc("Olmecs", "Olmec culture 1200-400 BCE",
   "Olmec colossal heads range in height from 1.17 to 3.4 m and were carved from basalt from the Sierra de los Tuxtlas; Olmec culture is dated 1200-400 BCE; whether the Olmecs were a mother culture is debated "
   "[World History Encyclopedia on the Olmec Colossal Heads; Wikipedia on the Olmec Colossal Heads]")
rc("Phoenicians", "Tyre, Sidon and Byblos",
   "Carthage was traditionally founded in 814 BCE by the Phoenician queen Dido and grew after an influx of refugees from Tyre; the Phoenician alphabet proper uses 22 consonant letters; Byblos was a Phoenician city [World History Encyclopedia on Carthage and Tyrian Purple; Wikipedia on the Phoenician Alphabet]")
rc("Scythians", "Arzhan 1 late 9th",
   "Burials in the Altai Mountains, Pazyryk and other sites, contained objects normally lost to archaeologists, because water froze in the mounds and remained permanently frozen [Penn Museum on Herodotus and the Scythians]")
rc("Sokoto Caliphate", "Jihad from 21 February 1804",
   "The Sokoto Caliphate was founded on 21 February 1804 (1804-1903); by 1808 it controlled Hausaland; by 1815 its conquests included most of northern Nigeria; by 1837 it had a population of 10-20 million [BlackPast on the Sokoto Caliphate; Wikipedia on the Sokoto Caliphate]")
rc("Swahili Coast City-States", "Ibn Battuta visited Kilwa 1331",
   "Ibn Battuta visited Kilwa in 1331 and called it one of the most beautiful towns in the world; the Portuguese built fortresses in East Africa, notably at Sofala in 1505 [World History Encyclopedia on the Swahili Coast]")
rc("Taino", "Greater Antilles chiefdoms",
   "Regional chieftaincies were headed by caciques; canoe, hammock, barbecue and hurricane are Taino words; possibly 85 percent of the Taino population had vanished by the early 1500s according to a controversial extrapolation from Spanish records; "
   "61 percent of surveyed Puerto Ricans carry Indigenous mitochondrial DNA [Smithsonian Magazine on the Taino]")
rc("Xiongnu", "Confederation under Modu 209 BCE",
   "The Xiongnu confederacy formed in 209 BCE, and the first major clash with Han came when Liu Bang led an army north in 200 BCE; the Han and Xiongnu agreed the heqin ('Peace and Family Relations') treaty system [Education About Asia on Han-Xiongnu Relations]")
rc("Yakut (Sakha)", "2010 census 478,085 Sakha",
   "The 2010 census counted 478,085 Sakha in the Russian Federation, and a major revolt against Russian occupation occurred in 1642 [Minority Rights Group on the Sakha]")

# --- places
rc("Angkor", "UNESCO inscription 14 December 1992", "Angkor was inscribed on the World Heritage List in 1992 [UNESCO on Angkor]")
rc("Athens", "Parthenon built 447-432",
   "Construction of the Parthenon started in 447 BC and it was completed in 438 BC, with decoration continuing until 432 BC; Cleisthenes set Athens on a democratic footing in 508 BC; the Peloponnesian War lasted 431-404 BCE "
   "[Wikipedia on the Parthenon; Wikipedia on Cleisthenes; World History Encyclopedia on the Peloponnesian War]")
rc("Borobudur", "Built in the 8th-9th centuries",
   "Borobudur was built during the rule of the Sailendra Dynasty and has 2,672 relief panels and originally 504 Buddha statues; it was rediscovered in 1814 and became a World Heritage Site in 1991 [World History Encyclopedia on Borobudur; Wikipedia on Borobudur]")
rc("Cahokia", "Peak population 10,000-20,000",
   "Cahokia's agricultural society may have had a population of 10-20,000 at its peak between 1050 and 1150; Monks Mound, the largest prehistoric earthwork in the Americas, stands 30 m high; the site was inscribed in 1982 [UNESCO on Cahokia Mounds]")
rc("Caral", "UNESCO inscription 2009", "The Sacred City of Caral-Supe was inscribed on the World Heritage List in 2009 [UNESCO on Caral-Supe]")
rc("Carthage", "Punic Wars 264-146",
   "The Punic Wars between Carthage and Rome were fought between 264 and 146 BCE; in the Second Punic War (218-201 BCE) Hannibal marched over the Alps into northern Italy; Rome destroyed Carthage in 146 BC; the Site of Carthage was inscribed in 1979 "
   "[World History Encyclopedia on the Punic Wars; UNESCO on the Site of Carthage]")
rc("Chaco Canyon", "UNESCO inscription 1987",
   "Chaco Culture was inscribed on the World Heritage List in 1987, and Chaco Canyon was a major centre of ancestral Pueblo culture between 850 and 1250 [UNESCO on Chaco Culture]")
rc("Great Zimbabwe", "Great Enclosure outer wall about 11 m",
   "The Great Enclosure has walls as high as 11 m, extending approximately 250 m [Wikipedia on Great Zimbabwe]")
rc("Göbekli Tepe", "Earliest structures 9500-9000",
   "Göbekli Tepe's distinctive limestone T-shaped pillars are up to 5.50 m tall, and the site was inscribed on the World Heritage List in 2018 [UNESCO on Gobekli Tepe]")
rc("Jack Hills Zircons", "Oldest Jack Hills zircon",
   "Jack Hills zircons in Western Australia are the oldest Earth materials, dating to 4.0-4.4 Ga with a single grain at 4.4 Ga; oxygen isotopes indicate magma from recycled rock that had interacted with surface waters [SERC on the Jack Hills Zircons]")
rc("Jericho", "Kenyon excavated Tell es-Sultan",
   "Kathleen Kenyon excavated Ancient Jericho (Tell es-Sultan) from 1952 to 1958 [Durham University on Jericho]")
rc("Mohenjo-daro", "UNESCO inscription 1980", "Mohenjo-daro was inscribed on the World Heritage List in 1980 [UNESCO on Mohenjo-daro]")
rc("Potosi", "Silver found at Cerro Rico",
   "Silver was discovered at Cerro Rico in 1545; in 1573 Viceroy Toledo adapted the Inca mita to supply forced labor for the mines; amalgamation was introduced from the mid-1570s [Encyclopedia.com on Potosi]")
rc("Poverty Point", "Occupied about 3,700-3,100 BP",
   "Poverty Point was built and used by hunter-fisher-gatherers between 3700 and 3100 BP; the complex comprises five mounds and six concentric semi-elliptical ridges around a central plaza; it was inscribed on 22 June 2014 [UNESCO on Poverty Point; Poverty Point Monumental Earthworks Sources]")
rc("Taj Mahal", "Mumtaz Mahal died 1631",
   "The Taj Mahal was commissioned in 1631, construction started in 1632, the mausoleum was completed in 1648 and the complex in 1653; more than 20,000 workers and artisans worked under a board of architects led by Ustad Ahmad Lahori; it was inscribed in 1983 "
   "[Taj Mahal Official Site and History Sources; UNESCO on the Taj Mahal; Wikipedia on the Taj Mahal]")
rc("Timbuktu", "UNESCO inscription 1988", "Timbuktu was inscribed on the World Heritage List in 1988 [UNESCO on Timbuktu]")
rc("Xingu Garden Cities", "About 28 settlements",
   "The Xingu garden cities were surrounded by extensive ditches; the region's population was many times larger than today, perhaps numbering 30,000 to 50,000; the people began molding the forests and wetlands about 1,500 years ago or before [Scientific American on Xingu Garden Cities]")
rc("Çatalhöyük", "UNESCO inscription 2012", "The Neolithic Site of Çatalhöyük was inscribed on the World Heritage List in 2012 [UNESCO on Catalhoyuk]")

# --- species and earth
rc("Homo erectus", "Average brain about 900",
   "The Dmanisi hominins date to about 1.8 million years ago [Wikipedia on Homo erectus]")
rc("Homo habilis", "Named 1964 from Olduvai",
   "Homo habilis was described in 1964 by Leakey et al. and lived from about 2.4 to 1.65 million years ago; its type material came from Olduvai Gorge [Wikipedia on Homo habilis]")
rc("Sahelanthropus tchadensis", "Fossils including the Toumai skull",
   "Sahelanthropus tchadensis, nicknamed Toumai, was discovered in the Djurab Desert of northern Chad in 2001 and is dated to about 7 to 6 million years ago [Wikipedia on Sahelanthropus]")
rc("Stromatolites", "Dresser Formation stromatolites of the Pilbara",
   "Structures in 3.48-billion-year-old rocks of Western Australia's Dresser Formation are the oldest evidence of life on Earth [Natural History Museum on the Dresser Formation]")
rc("Vaccination", "Jenner 1796",
   "Smallpox was declared eradicated on 8 May 1980 by the 33rd World Health Assembly, having killed about 300 million people in the 20th century [WHO Smallpox Eradication]")
rc("1918 Influenza Pandemic", "About one third of the world's population infected",
   "About one third of the world's population (about 500 million) was infected in 1918-1919, and deaths were estimated at about 50 million and possibly as high as 100 million [CDC on the 1918 Influenza Pandemic]")
rc("Chauvet Cave", "Discovered 18 December 1994",
   "The cave was discovered in 1994; radiocarbon dating of charcoal drawings shows an Aurignacian phase between 37,000 and 34,000 years ago and a Gravettian phase between 34,000 and 25,000 years ago (Britannica: a majority of samples about 35,500 years old and a smaller group 30,000-31,000); "
   "it was inscribed on the World Heritage List in 2014 [Britannica on Chauvet-Pont d'Arc; LSCE on Chauvet Cave Radiocarbon Dating]")
rc("Cixi", "Cixi lived 1835-1908",
   "Cixi lived 1835-1908, became co-regent in 1861, backed the Boxers and declared war on the foreigners on 21 June 1900, and after the Boxer Protocol was signed announced constitutional reforms in 1908; her legacy is debated [EBSCO Research Starters on Cixi]")


def notes_list():
    out = []
    for d in N.values():
        out.append({k: v for k, v in d.items() if v})
    return out


# ------------------------------------------------------------------------------------------------- discrepancies
def d(note_, source, was, says, action):
    return {"note": note_, "source": source, "was": was, "text_says": says, "action": action}


DISC = [
    d("Alexander the Great", "World History Encyclopedia on Alexander the Great", "died 13 June 323 BCE",
      "The page gives 10 or 11 June 323 BCE (born 21 July 356 BCE).", "Check corrected to 10 or 11 June 323 BCE; the note body gives no day."),
    d("Maurya Empire", "National Geographic on the Mauryan Empire", "Maurya Empire 322-185 BCE",
      "The page says the empire was founded around 321 BCE and was 321-185 BCE.", "Check narrowed to the page's 321-185 BCE; note text left at 322 (a common variant start date). Same for Classical Antiquity."),
    d("Invention of Writing", "World History Encyclopedia on Cuneiform", "Mesopotamia about 3400-3200 BCE (also in Bronze Age, Mesopotamia)",
      "The page gives circa 3600/3500 BCE for the first cuneiform and circa 3200 BCE for its development at Uruk.", "Checks state the page's dates; the notes' 3400-3200 BCE left as written (a common scholarly range), logged as unresolved."),
    d("Invention of Writing", "World History Encyclopedia on Writing", "Egypt about 3200 BCE (Abydos); Mesoamerica by 600 BCE",
      "Egyptian writing already in use before circa 3150 BCE; Mesoamerican writing with some evidence as early as 500 BCE.", "Checks state the page's dates; the note's figures left as written and logged as unresolved."),
    d("Kushan Empire", "Metropolitan Museum on the Kushan Empire", "Kujula Kadphises united the Yuezhi around 30 CE",
      "The Met writes that Kujula Kadphises united the disparate tribes in the first century B.C.", "Check states the Met's wording; the note's 30 CE left as written, logged as unresolved."),
    d("Modern Climate Change", "NOAA GML Mauna Loa Annual Mean CO2 Data; NOAA GML Global Annual Growth Rate of CO2", "CO2 about 424.5 ppm in 2024; up 3.75 ppm on 2023",
      "The Mauna Loa annual mean for 2024 is 424.61 ppm; the global mean is 422.79 ppm; the 2024 growth rate is 3.76 ppm in the current data file.", "Checks corrected to the data files' values; the note body (about 423, 422.8 in NOAA's record) is consistent."),
    d("Chauvet Cave", "LSCE on Chauvet Cave Radiocarbon Dating", "radiocarbon phases 37,000-33,500 and 31,000-28,000 years ago",
      "LSCE gives an Aurignacian phase of 37,000-34,000 and a Gravettian phase of 34,000-25,000 years ago; Britannica gives a majority about 35,500 and a smaller group 30,000-31,000.", "Check narrowed to the two pages' figures; the note's bands left as written and logged as unresolved."),
    d("Marajoara Culture", "Wikipedia on the Marajoara Culture", "ceramic tradition 400-1300 CE; mounds from about 300 CE; abandoned by about 1350",
      "ORIAS gives mound building CE 300-1350; Wikipedia gives ceramics 400-1400 AD and abandonment around AD 1300.", "Check states both pages' figures; note text left as written."),
    d("Homo habilis", "Wikipedia on Homo habilis", "lived about 2.3-1.5 (or 2.4-1.4) Ma", "The article gives about 2.4 to 1.65 mya.", "Check states the article's range; note text left as written."),
    d("Inuit and the Thule Expansion", "Canadian Encyclopedia on the Thule Culture", "Thule culture emerged about 900 CE in Alaska and reached Greenland by the 12th century",
      "The page says early Inuit groups moved from northern Alaska into Canada and Greenland around 800 years ago.", "Check narrowed to the page; note text left as written."),
    d("Zheng He", "Wikipedia on Zheng He", "died 1433", "The article gives 1371-1433 or 1435 for his lifespan.", "Check states both years; note text left as written."),
    d("Taj Mahal", "UNESCO on the Taj Mahal", "construction 1632-1653", "UNESCO and Wikipedia say construction began in 1632, the mausoleum was completed in 1648 and the surrounding buildings and garden in 1653.", "Check states all three dates; the note's 1632-1653 stands for the whole complex."),
    d("Haudenosaunee Confederacy", "Wikipedia on the Iroquois", "founding date debated (about 1142 vs about 1451-52)", "The article says likely between 1142 and 1660, with little agreement; its infobox says between 1142 and 1450.", "Check narrowed to the article; note text left as written."),
    d("Rachel Carson", "Wikipedia on Rachel Carson", "DDT banned 1972", "The article says that by 1972 activist groups had secured a phase-out of DDT use in the United States.", "Check says phase-out; note text left as written."),
    d("Pachacuti", "World History Encyclopedia on Pachacuti", "Sapa Inca 1438-1471/72", "The page gives 1438-1471.", "Check narrowed to 1438-1471; note text left as written."),
]

# ------------------------------------------------------------------------------------------------------ unresolved
UNRES = [
    ("Bronze Age; Mesopotamia; Invention of Writing", "Mesopotamian writing about 3400-3200 BCE (WHE gives 3600/3500 and 3200)", "World History Encyclopedia on Cuneiform"),
    ("Bronze Age; Bronze Age Collapse", "Sea Peoples attack recorded about 1177 BCE at Medinet Habu (Ramesses III year 8)", "World History Encyclopedia on the Late Bronze Age Collapse"),
    ("Iron Age; Alphabet", "Proto-Sinaitic about 1800 BCE", "Wikipedia on the Phoenician Alphabet"),
    ("Phoenicians", "Sidon and murex purple dye", "World History Encyclopedia on Carthage and Tyrian Purple"),
    ("Neolithic; The Agricultural Revolution", "Independent centers of agriculture in China, Mesoamerica and South America; the 'Southwest Asia' wording", "EBSCO on the Neolithic Revolution"),
    ("Andes", "Potato domesticated in the Andes between about 8000 and 5000 BCE (check dropped; no source read supports it)", "EBSCO on the Neolithic Revolution"),
    ("Andes; Machu Picchu", "Machu Picchu built about 1450 for Pachacuti; Bingham 1911 (the year is on the UNESCO page, Bingham is not)", "UNESCO on Machu Picchu"),
    ("Göbekli Tepe; Neolithic; Levant and Anatolia", "Earliest structures 9500-9000 BCE; Klaus Schmidt led excavations from 1995", "UNESCO on Gobekli Tepe"),
    ("Classical Antiquity; Maurya Empire", "Maurya Empire 322 BCE start; Pataliputra as capital; Ashoka reigned about 268-232 BCE", "National Geographic on the Mauryan Empire"),
    ("Information Age", "World population about 2.5 billion in 1950 (check dropped; the UN page and Wikipedia on World Population do not give it)", "UN World Population Milestones"),
    ("Central Asian Steppe; Indo-European Language Spread", "Proto-Indo-Anatolian community about 4400-4000 BCE (the Harvard Gazette page says about 6,500 years ago)", "Lazaridis et al. 2025 Indo-European Origins"),
    ("Indo-European Language Spread", "Roughly 40 to 46 percent of the world's population (Wikipedia says 42 percent, Lazaridis more than 40 percent)", "Wikipedia on Indo-European Languages"),
    ("Europe; Norse", "Lindisfarne raid on 7 June 793; Greenland settlement about 985; Iceland settlement 870-930", "Kuitems et al. 2021 L'Anse aux Meadows Dating"),
    ("Mediterranean Basin; Ancient Greeks; Athens", "Fully confirmed by Wikipedia on Cleisthenes (508 BC); nothing outstanding", "Wikipedia on Cleisthenes"),
    ("Mesopotamia; The Urban Revolution", "Uruk about 40,000-80,000 residents by about 2900-3100 BCE", "World History Encyclopedia on Uruk"),
    ("Sub-Saharan Africa", "Ezana converted about 333 CE (WHE: mid-4th century); Timbuktu about 700,000 manuscripts", "World History Encyclopedia on Aksum"),
    ("Scythians; Siberia and the Arctic", "Arzhan 1 (late 9th c. BCE) and Arzhan 2 (about 5,600 gold objects, cloak of about 2,500 gold panthers); the ice preservation of Arzhan", "Penn Museum on Herodotus and the Scythians"),
    ("Emergence of Symbolic Art", "Lascaux about 17 ka (not checked against a page read; verify in the re-run)", "Britannica on Chauvet-Pont d'Arc"),
    ("Invention of Writing", "Egypt about 3200 BCE (Abydos); Mesoamerica by 600 BCE", "World History Encyclopedia on Writing"),
    ("Mongol Conquests", "Empire about 24 million km2 at peak", "World History Encyclopedia on the Abbasid Caliphate"),
    ("Polynesian Settlement of the Pacific", "Lapita in Tonga about 2800 years ago", "World History Encyclopedia on Polynesian Navigation"),
    ("Rise of Islam", "Umayyad conquest of Sindh about 711-713 rests on the Tier 4 Wikipedia article; Iberia 711 on WHE Umayyad", "World History Encyclopedia on the Umayyad Dynasty"),
    ("Treaty of Waitangi", "New Zealand Wars 1845-1872", "Waitangi Tribunal on the Maori and English Texts"),
    ("Age of Revolutions", "Northern Saint-Domingue as the site of the 1791 uprising", "Office of the Historian on the Haitian Revolution"),
    ("Austronesian Expansion; Lapita Culture", "Lapita spread 1500-1000 BCE; more than 1,200 Austronesian languages; Madagascar settled in the first millennium CE; Vanuatu individuals 3,000-2,800 BP", "Phys.org on Ancient DNA and the South Pacific"),
    ("Classic Maya Collapse", "Last Long Count date at Tonina in 909 CE; drought 700-800 CE in the Yok Balum cave record; power shifted north", "World History Encyclopedia on the Classic Maya Collapse"),
    ("Colonization of Land", "Carboniferous swamp forests about 360-300 Ma", "UCMP on the Carboniferous"),
    ("COVID-19 Pandemic", "More than 7 million reported deaths (about 7.1 million by mid-2026)", "WHO COVID-19 Mortality Data"),
    ("Decolonization", "Ghana independent 6 March 1957; 17 African states in 1960", "United Nations Membership"),
    ("Digital Revolution", "First ARPANET message on 29 October 1969", "Web Origins Sources (ICANN, CERN)"),
    ("Enlightenment", "The Wealth of Nations published 1776", "Encyclopedia of the Enlightenment Works (Encyclopedie, Wealth of Nations)"),
    ("First Fleet and the Colonization of Australia", "The move to Sydney Cove; smallpox epidemic April 1789; Mabo decision 3 June 1992", "Museums of History NSW on the First Fleet"),
    ("Holocaust", "About six million Jews murdered; Roma, disabled people and others also killed; Nuremberg Laws 1935 (the page names the laws without the year)", "USHMM Holocaust Encyclopedia on the Wannsee Conference"),
    ("Indian Removal and the Trail of Tears", "The five nations named; Worcester v. Georgia 1832 not enforced; about 4,000 of 16,000 Cherokee in 1838-39", "History.com on the Indian Removal Act"),
    ("Modern Climate Change", "About 280 ppm before the Industrial Revolution (not in the IPCC report text read)", "IPCC AR6 Synthesis Report 2023"),
    ("Opium Wars", "Treaty of Nanking: five ports; Convention of Beijing 1860 (Kowloon, legations, opium legalized)", "UK National Archives on Hong Kong and the Opium Wars"),
    ("Protestant Reformation", "Theses sent to Albrecht of Mainz; New Testament in 1522", "World History Encyclopedia on Martin Luther"),
    ("Vaccination", "Jenner 1796", "WHO Smallpox Eradication"),
    ("1918 Influenza Pandemic", "Death estimates from 17.4 million; virus reconstructed in 2005", "CDC on the 1918 Influenza Pandemic"),
    ("Alexander's Conquests", "The mutiny at the Hyphasis (the page gives the mutiny in 326 BCE without the river)", "World History Encyclopedia on Alexander the Great"),
    ("Hammurabi", "Code of 282 laws about 1754 BCE", "World History Encyclopedia on Hammurabi"),
    ("Ibn Battuta", "73,000 miles (a conversion of 117,000 km)", "Wikipedia on Ibn Battuta"),
    ("Siddhartha Gautama", "Many scholars now place his death between about 411 and 400 BCE", "World History Encyclopedia on Siddhartha Gautama"),
    ("Achaemenid Persians", "Reach to the Indus; about twenty satrapies; Royal Road from Sardis to Susa", "Metropolitan Museum on the Achaemenid Persian Empire"),
    ("Aztec Empire", "Nothing outstanding beyond the check now split between Britannica on Hernan Cortes and WHE on the Aztec Empire", "Britannica on Hernan Cortes"),
    ("Inca Empire", "Atahualpa captured 1532; Cusco taken 1533; road network 30,000-40,000 km", "World History Encyclopedia on the Inca Empire"),
    ("Inuit and the Thule Expansion", "Thule emerging about 900 CE and reaching Greenland by the 12th century", "Canadian Encyclopedia on the Thule Culture"),
    ("Jomon Culture", "Pottery about 16,000 years old; UNESCO listing on 27 July 2021 (only the year 2021 was on the page)", "Jomon Prehistoric Sites in Northern Japan Official Website"),
    ("Kushan Empire", "Kujula Kadphises about 30 CE; Sasanians conquering western provinces after 225 CE", "Metropolitan Museum on the Kushan Empire"),
    ("Maori", "Moa extinct in under 150 years; Maori Language Act 1987", "Te Ara on Maori Arrival and Settlement"),
    ("Marajoara Culture", "Mounds up to 20 m", "ORIAS on Ancient Marajó"),
    ("Nabataeans", "Nothing outstanding; Hegra 2008 now confirmed by UNESCO on Al-Hijr", "UNESCO on Al-Hijr Archaeological Site"),
    ("Olmecs", "'Rubber people' as a later Nahuatl name", "World History Encyclopedia on the Olmec Colossal Heads"),
    ("Taino", "70 percent lower bound of the population loss", "Smithsonian Magazine on the Taino"),
    ("Xiongnu", "Split about 51 BCE; northern Xiongnu defeated 89-93 CE; the name Baideng", "Education About Asia on Han-Xiongnu Relations"),
    ("Yakut (Sakha)", "Yasak levied until 1917", "Minority Rights Group on the Sakha"),
    ("Angkor", "UNESCO inscription on 14 December 1992 (the page gives the year)", "UNESCO on Angkor"),
    ("Khmer Empire", "Angkor Wat under Suryavarman II reigning 1113-1150 (WHE: begun about 1122); 1431 abandonment is disputed (WHE: the empire lasted to 1431)", "World History Encyclopedia on the Khmer Empire"),
    ("Carthage", "Hannibal crossed the Alps in 218 BCE (WHE: the Second Punic War 218-201 BCE)", "World History Encyclopedia on the Punic Wars"),
    ("Chinchorro Culture", "Nothing outstanding after Wikipedia on the Chinchorro Mummies", "Wikipedia on the Chinchorro Mummies"),
    ("Chauvet Cave", "Discovery on 18 December 1994; radiocarbon phases 37,000-33,500 and 31,000-28,000; replica opened 2015", "Britannica on Chauvet-Pont d'Arc"),
    ("Jack Hills Zircons", "Oldest zircon 4.404 Ga in the Narryer Terrane", "SERC on the Jack Hills Zircons"),
    ("Jericho", "Plastered skulls from 1953; site about 250 m below sea level", "Durham University on Jericho"),
    ("Potosi", "Population about 160,000 by 1650", "Encyclopedia.com on Potosi"),
    ("Poverty Point", "Mound A about 22 m", "UNESCO on Poverty Point"),
    ("Xingu Garden Cities", "About 28 settlements; c. 1200-1600 CE; ditches about 3 m deep; plazas about 150 m", "Scientific American on Xingu Garden Cities"),
    ("Homo erectus", "Average brain about 900 cc (Wikipedia gives about 1000 cc for some populations)", "Wikipedia on Homo erectus"),
    ("Homo habilis", "Lived 2.3-1.5 (or 2.4-1.4) Ma (Wikipedia: 2.4 to 1.65 mya)", "Wikipedia on Homo habilis"),
    ("Stromatolites", "Location in the Pilbara", "Natural History Museum on the Dresser Formation"),
    ("Cixi", "The New Policies as a named programme", "EBSCO Research Starters on Cixi"),
    ("Rachel Carson", "Silent Spring published in September 1962; the EPA created on 2 December 1970 (only the year 1970 checked against the EPA text read)", "US EPA History"),
]


# ====================================================================================== the second pass, 2026-11-19
# The first pass (2026-09-27/28) read its pages on the owner's machine, and that cache was never in the repository. This pass
# re-fetched every page in a cloud sandbox. worldhistory.org answered HTTP 403, the Metropolitan Museum 429, several other
# hosts 403 or no answer, and the Wayback Machine could not be reached at all (every connection to web.archive.org was reset
# by the network path), so 43 of the 126 Tier 5 batch sources and all 19 new World History Encyclopedia articles were not read.
# Nothing written below rests on a page this pass did not read: a source that was not read gets a `blocked` entry; a check whose
# new wording cited such a page is narrowed to the sources that were read (NARROW) or, when none was read, not rewritten at
# all (DEFERRED: the existing check stays as it is, and the first pass's rewrite waits for a pass that can read the page).
PASS = "2026-11-19"
NEW = [x for x in NEW if x]
NEW.append(new_src("Wikipedia on Alexander the Great", WP + "Alexander_the_Great", "Alexander the Great",
                   "Alexander's life (20 or 21 July 356 BC to 10 or 11 June 323 BC, died in Babylon), his victory at Gaugamela in 331 BC and the overthrow of Darius III, and the mutiny of his army at the Hyphasis River (Beas).",
                   "Added in Tier 5 (2026-11-19) because World History Encyclopedia on Alexander the Great could not be read in this pass. "
                   "The article dates his death to 10 or 11 June 323 BC, not 13 June as the Alexander the Great note's earlier check had it."))
NEW = [x for x in NEW if x]

# Sources of the first pass's 120 that were already blocked then.
FIRST_PASS_BLOCKED = {"ICS International Chronostratigraphic Chart", "Library of Congress on the First Telegraph Message",
                      "Oxford Research Encyclopedia on Animal Domestication in Southwest Asia", "Slave Voyages Database",
                      "Smithsonian on the Sogdian Language", "Jinek et al. 2012 CRISPR-Cas9"}
# Tier 5 queue entries this pass leaves untouched. The first four were written by the fact-check sweep on 2026-09-27 from a
# WebFetch read, after the first pass built its queue, so the Tier 5 analysis never covered them; they keep their own access
# fields until a later pass reads them against their checks.
SKIP_NOW = {
    "Ancient Americas on the Oval Palace Tablet": "written by the fact-check sweep from a WebFetch read; not in the first pass's analysis",
    "Global Nonviolent Action Database on the Brazilian Rubber Tappers Campaign": "written by the fact-check sweep from a WebFetch read; not in the first pass's analysis",
    "National Park Service Theodore Roosevelt and Conservation": "written by the fact-check sweep from a WebFetch read; not in the first pass's analysis",
    "Why Now, Kandinsky masterpiece once seized by Nazis breaks record in London sale": "written by the fact-check sweep from a WebFetch read; not in the first pass's analysis",
    "USDA ERS on Genetically Engineered Crop Adoption": "created on 2026-11-19 by the vault-issues corrections (Soybean); not a Tier 5 source",
    "EBSCO Research Starters on Monte Alban": "already done in Tier 3 (full-text, 2026-09-26)",
    "ICS International Chronostratigraphic Chart": ("not readable in this pass (stratigraphy.org answered with a wall page, the Wayback Machine was unreachable), "
                                                    "but its Caveats say the chart PDF was read with the date left as a '%s' placeholder; the owner decides its access level"),
}


def _host(url):
    return urlparse(url).netloc.lower()


def _all_meta():
    out = []
    for mp in fs.CACHE.glob("*.meta.json"):
        try:
            out.append(json.loads(mp.read_text(encoding="utf-8")))
        except ValueError:
            pass
    return out


HOSTS_403 = {a["host"] for m in _all_meta() if m.get("retrieved") == PASS for a in m.get("attempts", []) if a.get("status") == 403}
WAYBACK = ("the Wayback Machine could not be reached from the sandbox that ran this pass (every connection to web.archive.org was "
           "reset)")


def why_blocked(meta, url):
    host = _host(url)
    att = [a for a in meta.get("attempts", []) if a.get("host") == host]
    st = [a.get("status") for a in att]
    if 403 in st:
        site = f"{host} answered HTTP 403 to automated requests"
    elif 429 in st:
        site = f"{host} answered HTTP 429 (too many requests) on every try"
    elif any(a.get("wall") for a in att):
        site = f"{host} answered with a page the fetcher recognised as a wall (a script, cookie or access check), not the text"
    elif st:
        site = f"{host} did not answer (the connection failed or timed out on every try)"
    elif host in HOSTS_403:
        site = f"{host} had answered HTTP 403 to automated requests earlier in the same run, so it was not asked again"
    else:
        site = f"{host} was not reached"
    return f"On {PASS} no readable copy could be obtained: {site}, and {WAYBACK}. The page was therefore not read in this pass, and the claims that cite it remain unverified."


q_ = fs.load_queue()
BLOCKED_NOW = {}
for t, e in q_.items():
    if e["tier"] != 5 or t in SKIP_NOW or t in ("World History Encyclopedia", "UNESCO World Heritage Centre"):
        continue
    mp = fs.cache_paths(fs.pick_slug(t))[1]
    m = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {"attempts": []}
    if not m.get("level"):
        BLOCKED_NOW[t] = why_blocked(m, e["url"]) + ("" if t in FIRST_PASS_BLOCKED else
            " The first Tier 5 pass (2026-09-27, on the owner's machine) did read this page, but its cached text is not in the repository, so nothing here rests on that read.")
for t in SKIP_NOW:
    SRC[t] = {"skip": True}
for t, why in BLOCKED_NOW.items():
    SRC[t] = {"blocked": why}
UNAVAILABLE = set(BLOCKED_NOW) | set(NOT_FETCHED) | {"World History Encyclopedia", "Britannica on Chauvet-Pont d'Arc", "Britannica on Hernan Cortes"}

# The generic World History Encyclopedia note: still set to not-consulted (the title stands for the whole site, like the generic
# Britannica and English Wikipedia notes), with Caveats that say only what is known without the first pass's cache.
GENERIC_UPDATES[0]["caveats"] = (
    "The url is the Ibn Battuta article. The first Tier 5 pass (2026-09-27, on the owner's machine) found that this title had been "
    "fetched from that one article only, so checks citing it for other subjects were unconfirmed. In the second pass (2026-11-19) "
    "worldhistory.org answered HTTP 403 and the Wayback Machine could not be reached, so no World History Encyclopedia page was read; "
    "checks that cite this note were re-pointed only where a Wikipedia or UNESCO page read in that pass carries the claim, and the others "
    "still cite it, unconfirmed. A tertiary, non-academic source for general readers.")
GENERIC_UPDATES[0]["used"] = (
    "Stands for World History Encyclopedia as a whole when a note cites it without naming an article. A check that cites only this note "
    "is not confirmed by any text read; wherever a page read in Tier 5 carries the claim, the check now cites that page's source note instead.")

# New wording for checks whose first-pass rewrite cited a page this pass could not read (or an earlier-tier page it could not
# re-read): each states only what the pages read in this pass say (probed against the cached text on 2026-11-19).
NARROW = {
    ("Classical Antiquity", "Maurya Empire 322-185"):
        "National Geographic dates the Maurya Empire, the first pan-Indian empire, to 321-185 BCE [National Geographic on the Mauryan Empire]",
    ("Southeast Asia", "Khmer Empire founded 802"):
        "Angkor was inscribed on the World Heritage List in 1992 [UNESCO on Angkor]",
    ("Sub-Saharan Africa", "Ezana converted about 333"):
        "The Great Enclosure at Great Zimbabwe has walls as high as 11 m, and Timbuktu was inscribed on the World Heritage List in 1988 [Wikipedia on Great Zimbabwe; UNESCO on Timbuktu]",
    ("Rise of Islam", "Umayyad Caliphate 661-750"):
        "Between 711 and 713 the Umayyad Caliphate defeated the Chach dynasty and incorporated Sindh as a province, and Muhammad and his followers made the Hijrah from Mecca to Medina in 622 CE "
        "[Wikipedia on the Arab Conquest of Sindh; Wikipedia on the Hijrah]",
    ("The Urban Revolution", "Uruk 40,000-80,000"):
        "V. Gordon Childe introduced the term 'urban revolution' in the 1930s and brought the concept to a much larger audience in his 1950 article in Town Planning Review [Wikipedia on the Urban Revolution]",
    ("Lapita Culture", "Lapita culture spread across Melanesia"):
        "Austronesian-speaking groups associated with the Lapita pottery culture expanded east into Remote Oceania (Vanuatu, New Caledonia, Fiji and the islands of western Polynesia) about 3,000 years ago, "
        "and an ancient DNA study of Lapita burial sites found that these earliest inhabitants of Vanuatu had East Asian ancestry [Phys.org on Ancient DNA and the South Pacific]",
    ("Battle of Kadesh", "Battle in May 1274 BCE at Kadesh"):
        "The battle took place at Kadesh on the Orontes in May 1274 BCE (low chronology); the outcome was inconclusive; some 5,000 to 6,000 chariots were involved in total; the events were recorded in temples including Abu Simbel and Karnak "
        "[Wikipedia on the Battle of Kadesh]",
    ("Modern Climate Change", "About 1.1 C above 1850-1900"):
        "The Mauna Loa annual mean CO2 concentration for 2024 was 424.61 ppm, against a global marine surface mean of 422.79 ppm [NOAA GML Mauna Loa Annual Mean CO2 Data; NOAA GML Global Annual Mean CO2 Data]",
    ("Augustus", "Born 23 September 63 BCE"):
        "Augustus (born Gaius Octavius, 23 September 63 BC; died 19 August AD 14) was the first Roman emperor, from 27 BC until his death in AD 14 [Wikipedia on Augustus]",
    ("Hammurabi", "Reign 1792-1750 BCE"):
        "Hammurabi, the sixth king of the Amorite First Dynasty of Babylon, ruled from around 1792 to around 1750 BC (middle chronology); the stele of his code, now in the Louvre, was rediscovered in 1901 at Susa "
        "[Wikipedia on the Code of Hammurabi]",
    ("Ancient Greeks", "Athenian democracy about 508"):
        "Cleisthenes set Athens on a democratic footing in 508 BC [Wikipedia on Cleisthenes]",
    ("Aztec Empire", "Conquest by Spain 1519-1521"): None,
    ("Nabataeans", "First recorded in 312 BCE"):
        "Hegra (al-Hijr), the largest conserved site of the Nabataean civilization south of Petra, was inscribed on the World Heritage List in 2008 [UNESCO on Al-Hijr Archaeological Site]",
    ("Olmecs", "Olmec culture 1200-400 BCE"):
        "Olmec colossal heads range in height from 1.17 to 3.4 m and were carved from basalt from the Sierra de los Tuxtlas [Wikipedia on the Olmec Colossal Heads]",
    ("Phoenicians", "Tyre, Sidon and Byblos"):
        "The Phoenician alphabet proper uses 22 consonant letters, and Byblos was a Phoenician city [Wikipedia on the Phoenician Alphabet]",
    ("Athens", "Parthenon built 447-432"):
        "Construction of the Parthenon started in 447 BC and it was completed in 438 BC, with decoration continuing until 432 BC; Cleisthenes set Athens on a democratic footing in 508 BC "
        "[Wikipedia on the Parthenon; Wikipedia on Cleisthenes]",
    ("Borobudur", "Built in the 8th-9th centuries"):
        "Borobudur was built during the reign of the Sailendra Dynasty and has 2,672 relief panels and originally 504 Buddha statues; worldwide knowledge of it was sparked in 1814 by Raffles; it became a World Heritage Site in 1991 "
        "[Wikipedia on Borobudur]",
    ("Carthage", "Punic Wars 264-146"):
        "Rome finally destroyed Carthage in 146 BC, and the Site of Carthage was inscribed on the World Heritage List in 1979 [UNESCO on the Site of Carthage]",
    ("Poverty Point", "Occupied about 3,700-3,100 BP"):
        "Poverty Point was built and used by hunter-fisher-gatherers between 3700 and 3100 BP; the complex comprises five mounds and six concentric semi-elliptical ridges around a central plaza; it was inscribed on 22 June 2014 "
        "[UNESCO on Poverty Point]",
    ("Alexander the Great", "Born 356 BCE; died 13 June"):
        "Alexander was born on 20 or 21 July 356 BC and died on 10 or 11 June 323 BC in Babylon [Wikipedia on Alexander the Great]",
    ("Alexander's Conquests", "Alexander born 356 BCE, died Babylon"):
        "Alexander was born on 20 or 21 July 356 BC and died on 10 or 11 June 323 BC in Babylon; he won at Gaugamela in 331 BC and overthrew Darius III; his army mutinied at the Hyphasis River and refused to march farther east "
        "[Wikipedia on Alexander the Great]",
    ("Emergence of Symbolic Art", "Sulawesi warty pig at least 45.5"):
        "Sulawesi warty pig painting at least 45.5 ka; narrative art 51.2 ka; Blombos engraved ochres 75-100 ka; the Chauvet Cave's early Aurignacian phase 37,000-34,000 years ago "
        "[Brumm et al. 2021 Sulawesi Warty Pig Painting; Oktaviana et al. 2024 Sulawesi Narrative Cave Art; Henshilwood et al. 2009 Blombos Engraved Ochres; LSCE on Chauvet Cave Radiocarbon Dating]",
    ("Chauvet Cave", "Discovered 18 December 1994"):
        "The cave was discovered on 18 December 1994; radiocarbon dating of its black charcoal drawings shows an early Aurignacian phase between 37,000 and 34,000 years ago and a more recent Gravettian phase between 34,000 and 25,000 years ago; "
        "it has been on the World Heritage List since 22 June 2014 [LSCE on Chauvet Cave Radiocarbon Dating]",
    # not blocked: the EPA page read in this pass gives the day, so the check can state it (the first pass had only the year)
    ("Rachel Carson", "Silent Spring September 1962"):
        "Silent Spring was published in 1962; the US EPA uses 2 December 1970, when its first administrator was confirmed, as the traditional date of its birth; Carson died on 14 April 1964; "
        "by 1972 activist groups had secured a phase-out of DDT use in the United States [US EPA History; Wikipedia on Rachel Carson]",
}


def _cites(claim):
    return [s.strip() for s in re.search(r"\[([^\]]*)\]\s*$", claim).group(1).split(";")]


DEFERRED = []   # (note, substring of the check left as it is, pages that could not be read)
_kept = {}
for name, dd in N.items():
    k = {"note": name, "replace_checks": [], "drop_checks": list(dd["drop_checks"]), "checks": [], "replace": list(dd["replace"]), "sources": []}
    for old, new in dd["replace_checks"]:
        if (name, old) in NARROW:
            first = new
            new = NARROW[(name, old)]
            if new is None:
                DEFERRED.append((name, old, [s for s in _cites(first) if s in UNAVAILABLE]))
                continue
        bad = [s for s in _cites(new) if s in UNAVAILABLE]
        if bad:
            DEFERRED.append((name, old, bad))
            continue
        k["replace_checks"].append([old, new])
    for c in dd["checks"]:
        if any(s in UNAVAILABLE for s in _cites(c)):
            DEFERRED.append((name, "(added check) " + c[:60], [s for s in _cites(c) if s in UNAVAILABLE]))
            continue
        k["checks"].append(c)
    for _, c in k["replace_checks"]:
        k["sources"] += [s for s in _cites(c) if s not in k["sources"]]
    for c in k["checks"]:
        k["sources"] += [s for s in _cites(c) if s not in k["sources"]]
    if k["replace_checks"] or k["checks"] or k["drop_checks"] or k["replace"]:
        _kept[name] = k
N = _kept
for t in [t for t in SRC if t in UNAVAILABLE and "blocked" not in SRC[t] and not SRC[t].get("skip")]:
    SRC[t] = {"skip": True}      # tier 3 pages named by the first pass (Britannica on Chauvet-Pont d'Arc) are not touched here

# Discrepancies: only those resting on pages read in this pass.
_DISC_FIX = {
    "Alexander the Great": d("Alexander the Great", "Wikipedia on Alexander the Great", "died 13 June 323 BCE",
                             "The article gives 20 or 21 July 356 BC to 10 or 11 June 323 BC.", "Check corrected to 10 or 11 June 323 BC and re-pointed to the article; the note body gives no day."),
    "Chauvet Cave": d("Chauvet Cave", "LSCE on Chauvet Cave Radiocarbon Dating", "radiocarbon phases 37,000-33,500 and 31,000-28,000 years ago",
                      "LSCE gives an early Aurignacian phase of 37,000-34,000 and a Gravettian phase of 34,000-25,000 years ago.",
                      "Check narrowed to the LSCE page (Britannica on Chauvet-Pont d'Arc could not be re-read in this pass and was dropped from the bracket); the note's bands left as written and logged as unresolved."),
}
DISC = [_DISC_FIX.get(x["note"], x) for x in DISC]
DISC = [x for x in DISC if not any(s.strip() in UNAVAILABLE for s in x["source"].split(";"))]

# Unresolved: drop entries whose page was not read in this pass (the DEFERRED list stands for them), adjust entries the pages
# read in this pass settle, and add the clauses the narrowed checks no longer state.
_UNRES_FIX = {
    "Jomon Culture": ("Jomon Culture", "Pottery about 16,000 years old", "Jomon Prehistoric Sites in Northern Japan Official Website"),
    "Chauvet Cave": ("Chauvet Cave", "Radiocarbon phases 37,000-33,500 and 31,000-28,000 (LSCE: 37,000-34,000 and 34,000-25,000); replica opened 2015", "LSCE on Chauvet Cave Radiocarbon Dating"),
    "Emergence of Symbolic Art": ("Emergence of Symbolic Art", "Lascaux about 17 ka and Chauvet about 36 ka (no page read in Tier 5 gives Lascaux)", "LSCE on Chauvet Cave Radiocarbon Dating"),
    "Rachel Carson": ("Rachel Carson", "Silent Spring published in September 1962 (the EPA page gives the year 1962 only)", "US EPA History"),
    "Hammurabi": ("Hammurabi", "Code of 282 laws about 1754 BCE (the article does not state 282 laws or 1754 BCE in so many words)", "Wikipedia on the Code of Hammurabi"),
    "Alexander's Conquests": ("Alexander's Conquests", "Nothing outstanding; the Hyphasis mutiny is in Wikipedia on Alexander the Great", "Wikipedia on Alexander the Great"),
    "Sub-Saharan Africa": ("Sub-Saharan Africa; Timbuktu", "Timbuktu about 700,000 manuscripts", "UNESCO on Timbuktu"),
    "Rise of Islam": ("Rise of Islam", "Umayyad Caliphate 661-750, the conquest of Iberia about 711 and the Abbasid Caliphate 750-1258 (World History Encyclopedia not readable in this pass)", "Wikipedia on the Arab Conquest of Sindh"),
}
UNRES = [_UNRES_FIX.get(n, (n, a, s)) for n, a, s in UNRES]
UNRES = [x for x in UNRES if x[2] not in UNAVAILABLE]
UNRES += [
    ("Classical Antiquity", "Achaemenid Empire 550-330 BCE (Metropolitan Museum on the Achaemenid Persian Empire not readable in this pass)", "National Geographic on the Mauryan Empire"),
    ("Southeast Asia", "Khmer Empire founded 802 (World History Encyclopedia on the Khmer Empire not readable in this pass)", "UNESCO on Angkor"),
    ("Sub-Saharan Africa", "Ezana converted about 333 CE; Mali founded about 1235 (World History Encyclopedia not readable in this pass)", "Wikipedia on Great Zimbabwe"),
    ("The Urban Revolution", "Uruk 40,000-80,000 people around 3100-2900 BCE", "Wikipedia on the Urban Revolution"),
    ("Modern Climate Change", "About 1.1 C above 1850-1900 in 2011-2020 (IPCC AR6 Synthesis Report not readable in this pass)", "NOAA GML Global Annual Mean CO2 Data"),
    ("Ancient Greeks; Athens", "Peloponnesian War 431-404 BCE (World History Encyclopedia on the Peloponnesian War not readable in this pass)", "Wikipedia on Cleisthenes"),
    ("Nabataeans", "First recorded in 312 BCE; Petra as capital; Trajan annexed the kingdom in 106 CE (World History Encyclopedia on the Kingdom of Nabatea not readable in this pass)", "UNESCO on Al-Hijr Archaeological Site"),
    ("Olmecs", "Olmec culture 1200-400 BCE; 'rubber people' as a later Nahuatl name; mother-culture status debated", "Wikipedia on the Olmec Colossal Heads"),
    ("Phoenicians", "Tyre and Sidon; Carthage traditionally founded 814 BCE; murex purple dye (World History Encyclopedia on Carthage and Tyrian Purple not readable in this pass)", "Wikipedia on the Phoenician Alphabet"),
    ("Borobudur", "Built in the 8th-9th centuries (the article says originally built in the 9th century)", "Wikipedia on Borobudur"),
    ("Carthage", "Punic Wars 264-146 BCE; Hannibal crossed the Alps 218 BCE (World History Encyclopedia on the Punic Wars not readable in this pass)", "UNESCO on the Site of Carthage"),
    ("Lapita Culture", "Lapita spread between 1500 and 1000 BCE; Vanuatu individuals 3,000-2,800 BP", "Phys.org on Ancient DNA and the South Pacific"),
]

# Second look (step 9, t3_usedfor.py 5 after the apply): the source notes' own used-for text still overclaimed for five fetched
# sources, and the NobelPrize.org home page (fetched in full, but it carries no prize details) was still the only cited page
# for three Nobel checks. As for Marie Curie and Antibiotics, the specific prize pages were read and the checks re-pointed.
# These items are applied as a separate small spec (tier5b.json, built by --second-look).
SECOND_LOOK_USED = {
    "NASA on the Dawn of the Space Age": "Sputnik 1 on 4 October 1957 and the continuous occupation of the ISS since 2 November 2000 (Gagarin is not on this page).",
    "The Conversation on Stone Tools and the Toba Eruption": "Jwalapuram stone tools above and below the Toba ash (the page gives no erupted volume).",
    "UN World Population Milestones": "The UN projection that world population would reach 8 billion on 15 November 2022 (the page does not give the one-billion milestone of 1804).",
    "USHMM Holocaust Encyclopedia on the Wannsee Conference": "The Wannsee Conference (20 January 1942), the Nuremberg Laws as the basis for determining who was a Jew, and the SS envisioning some 11 million Jews to be eradicated (the page does not give the year of the Nuremberg Laws).",
    "National Park Service Timeline of the American Revolution": "Lexington and Concord (19 April 1775), the Declaration (4 July 1776), the French alliance (6 February 1778), Yorktown (1781), the Treaty of Paris (3 September 1783), and the Treaty of Fort Stanwix imposing peace on the members of the Iroquois Confederacy that sided with the British.",
}
for _t, _u in SECOND_LOOK_USED.items():
    SRC.setdefault(_t, {})["used"] = _u
SECOND_LOOK_NEW = [
    new_src("NobelPrize.org on the 1944 Nobel Prize in Chemistry", NOBEL + "chemistry/1944/summary/", "The Nobel Prize in Chemistry 1944",
            "The 1944 Chemistry prize awarded to Otto Hahn for his discovery of the fission of heavy nuclei.",
            ADD.format(g="NobelPrize.org home page", n="Nuclear Fission", s="")),
    new_src("NobelPrize.org on the 1921 Nobel Prize in Physics", NOBEL + "physics/1921/summary/", "The Nobel Prize in Physics 1921",
            "The 1921 Physics prize awarded to Albert Einstein for his services to theoretical physics and especially his discovery of the law of the photoelectric effect.",
            ADD.format(g="NobelPrize.org home page", n="Albert Einstein", s="")),
    new_src("NobelPrize.org on the 1962 Nobel Prize in Physiology or Medicine", NOBEL + "medicine/1962/summary/", "The Nobel Prize in Physiology or Medicine 1962",
            "The 1962 prize awarded jointly to Francis Crick, James Watson and Maurice Wilkins for their discoveries concerning the molecular structure of nucleic acids.",
            ADD.format(g="NobelPrize.org home page", n="Rosalind Franklin", s="")),
]
SECOND_LOOK_NEW = [x for x in SECOND_LOOK_NEW if x]
NEW += SECOND_LOOK_NEW
SECOND_LOOK_GENERIC = {
    "title": "NobelPrize.org", "mark": "done",
    "set": {"access": "not-consulted", "verified": False,
            "access_route": "none: this title stands for the whole site; the url is the home page, which carries no prize details"},
    "used": "Stands for NobelPrize.org as a whole when a note cites it without naming a prize. The home page gives no prize years or laureates, so a check that cites only this note is not confirmed by any text read; the Nobel checks now cite the source notes titled NobelPrize.org on the ... Nobel Prize in ...",
    "caveats": "The url is the NobelPrize.org home page, which was read in full on 2026-11-19 (directly) and names no laureates or prize years. Set to not-consulted like the generic Britannica and English Wikipedia notes; the specific prize pages are separate source notes.",
}
GENERIC_UPDATES.append(SECOND_LOOK_GENERIC)
SRC["NobelPrize.org"] = {"skip": True}
SECOND_LOOK_NOTES = {
    "Nuclear Fission": ("Hahn alone received the 1944 Chemistry Nobel",
                        "The Nobel Prize in Chemistry 1944 was awarded to Otto Hahn for his discovery of the fission of heavy nuclei [NobelPrize.org on the 1944 Nobel Prize in Chemistry]"),
    "Albert Einstein": ("Nobel Prize in Physics 1921; letter to Roosevelt",
                        "The Nobel Prize in Physics 1921 was awarded to Albert Einstein for his services to theoretical physics, and especially for his discovery of the law of the photoelectric effect [NobelPrize.org on the 1921 Nobel Prize in Physics]"),
    "Rosalind Franklin": ("Nobel 1962 to Watson, Crick, Wilkins",
                          "The Nobel Prize in Physiology or Medicine 1962 was awarded jointly to Francis Crick, James Watson and Maurice Wilkins for their discoveries concerning the molecular structure of nucleic acids [NobelPrize.org on the 1962 Nobel Prize in Physiology or Medicine]"),
}
for _n, (_old, _new) in SECOND_LOOK_NOTES.items():
    N[_n] = {"note": _n, "replace_checks": [[_old, _new]], "drop_checks": [], "checks": [], "replace": [], "sources": _cites(_new)}
UNRES += [
    ("Nuclear Fission", "Fission discovered December 1938; Chicago Pile-1 on 2 December 1942 (the check now cites only the 1944 prize page)", "NobelPrize.org on the 1944 Nobel Prize in Chemistry"),
    ("Albert Einstein", "Letter to Roosevelt dated 2 August 1939", "NobelPrize.org on the 1921 Nobel Prize in Physics"),
    ("Rosalind Franklin", "Photo 51 taken 1952 with Gosling; died 16 April 1958 aged 37", "NobelPrize.org on the 1962 Nobel Prize in Physiology or Medicine"),
]


def write_unresolved(date):
    log = fs.CACHE / "unresolved.md"
    # The Tier 1-4 sections live in the copy on the owner's machine; a fresh cache starts a new file (merge the two by hand).
    text = log.read_text(encoding="utf-8") if log.exists() else (
        "# Unresolved claims\n\nClaims that stay in a note although the page cited for them does not contain them. "
        "This file was started fresh on 2026-11-19 in a cloud sandbox; the Tier 1-4 sections are in the copy on the owner's machine.\n")
    if f"## Tier 5 ({date})" in text:
        print("unresolved.md already has this Tier 5 section; not appended")
        return
    rows = "\n".join(f"- **{n}**: {a} [cited to {s}]" for n, a, s in UNRES if "Nothing outstanding" not in a and "Fully confirmed" not in a)
    dfr = "\n".join(f"- **{n}**: the check containing '{o}' was left as it is; its Tier 5 rewrite cites {', '.join(b)}, not readable on {PASS}"
                    for n, o, b in DEFERRED)
    log.write_text(text.rstrip("\n") + f"\n\n## Tier 5 ({date})\n{rows}\n\n### Tier 5 deferred: page not readable on {PASS}\n{dfr}\n",
                   encoding="utf-8", newline="\n")
    print("unresolved.md: Tier 5 entries written")


if __name__ == "__main__":
    (SP / "tier5_manual.json").write_text(json.dumps(SRC, indent=1, ensure_ascii=False), encoding="utf-8")
    (SP / "tier5_extra.json").write_text(json.dumps({"sources_new": NEW, "source_updates": GENERIC_UPDATES, "notes": notes_list(), "discrepancies": DISC},
                                                    indent=1, ensure_ascii=False), encoding="utf-8")
    (SP / "tier5_deferred.json").write_text(json.dumps({"deferred": DEFERRED, "blocked": BLOCKED_NOW, "new_not_fetched": sorted(NOT_FETCHED), "skipped": SKIP_NOW},
                                                       indent=1, ensure_ascii=False), encoding="utf-8")
    print(len(SRC), "source manual entries;", len(NEW), "new sources;", len(N), "notes patched;", len(DISC), "discrepancies;", len(UNRES), "unresolved;",
          len(DEFERRED), "deferred;", len(BLOCKED_NOW), "blocked;", len(NOT_FETCHED), "new pages not fetched")
    if "--unresolved" in sys.argv:
        write_unresolved(__import__("datetime").date.today().isoformat())
    if "--second-look" in sys.argv:
        # run after t2_build.py 5: the small follow-up spec, and its three unresolved entries appended to the Tier 5 section
        auto = json.loads((SP / "tier5_auto.json").read_text(encoding="utf-8"))
        spec_b = {"date": auto["date"], "sources_new": SECOND_LOOK_NEW,
                  "source_updates": [{"title": x, "used": u} for x, u in SECOND_LOOK_USED.items()] + [SECOND_LOOK_GENERIC],
                  "notes": [{k: v for k, v in N[n].items() if v} for n in SECOND_LOOK_NOTES], "discrepancies": []}
        (SP / "tier5b.json").write_text(json.dumps(spec_b, indent=1, ensure_ascii=False), encoding="utf-8")
        log = fs.CACHE / "unresolved.md"
        text = log.read_text(encoding="utf-8")
        add_rows = [f"- **{n}**: {a} [cited to {s}]" for n, a, s in UNRES[-3:]]
        if add_rows[0] not in text:
            head = "\n### Tier 5 deferred"
            text = text.replace(head, "\n".join(add_rows) + "\n" + head, 1)
            log.write_text(text, encoding="utf-8", newline="\n")
        print("tier5b.json:", len(spec_b["sources_new"]), "new sources,", len(spec_b["source_updates"]), "source updates,", len(spec_b["notes"]), "notes")
