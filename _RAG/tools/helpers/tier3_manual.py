"""Hand-written parts of the Tier 3 patch (44 Britannica sources read from Wayback Machine snapshots, 2026-09-26).

Policy A (agreed with the user): fix every contradiction in note text and checks; narrow each check to what the page read
supports; leave true-but-unconfirmed details in the note and log them in source_cache/unresolved.md so Tiers 4-6 can
re-attribute them.

Writes specs/tier3_manual.json (per-source extras for t2_build.py) and specs/tier3_extra.json (new sources, note patches,
discrepancies, generic-note update). `python tier3_manual.py --unresolved` also appends the unresolved list.
"""
import json
import sys
from pathlib import Path

import _paths
import fetch_source as fs

SP = _paths.WORK
SP.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------------------------------------ per-source manual entries
SRC = {
    "Britannica on Abd al-Malik": {
        "extra": "The page says the Dome of the Rock was built during his reign but gives no completion date; the 691 in the notes is not on this page.",
    },
    "Britannica on Al-Andalus": {
        "extra": "The page dates the battle in which Roderick was killed to 23 July 711 and gives only the year 1492 for the fall of Granada; the months April 711 and January 1492 in the notes are not on this page.",
    },
    "Britannica on Angiosperm Paleobotany and Evolution": {
        "used": "The age of the oldest angiosperm pollen (Hauterivian and Barremian ages of the Early Cretaceous, about 132.9 to 125 million years ago) and the 2013 report of angiosperm-like pollen of Middle Triassic age (about 247.2 to 242 million years ago) from Switzerland, which suggests an earlier origin.",
        "extra": "The page does not give 134 million years, the figure the Flowering Plants note used for the oldest pollen; the note now follows the page.",
    },
    "Britannica on Beringia": {
        "used": "Beringia as an intermittent Pleistocene land connection between northeastern Asia and northwestern North America: the most recent one began to appear about 38,000 years ago, was at its greatest extent about 20,000 years ago when sea level was lowered by as much as about 120 m, ran some 1,600 km north to south, and was largely dry and unglaciated with tundra vegetation; it is also called at least one route by which humans reached the Americas.",
        "extra": "The page does not mention mammoths or bison, the Beringian standstill hypothesis, or a flooding date of about 11,000 years ago; it says only that the Bering Strait opened at the end of the Pleistocene (about 11,700 years ago). Those details in the Beringia note are not confirmed here.",
    },
    "Britannica on Chauvet-Pont d'Arc": {
        "used": "Discovery in 1994 (Jean Clottes visited the cave on 29 December 1994), radiocarbon ages (a majority of samples about 35,500 years old and a smaller group 30,000 to 31,000 years old), UNESCO listing in 2014 and the replica opened in 2015.",
        "extra": "The page gives about 35,500 years for most samples, not the 37,000 to 33,500 year phase in the Chauvet Cave note, and does not give the day of discovery (18 December 1994); the Chauvet Cave check also cites LSCE on Chauvet Cave Radiocarbon Dating (Tier 5), so it is left unchanged until that page is read.",
    },
    "Britannica on Chichen Itza": {
        "citation": "Encyclopaedia Britannica. 'Chichen Itza.'",
        "cut_note": "EBSCO Research Starters, 'Monte Alban.'",
        "used": "El Castillo's 365 steps (91 on each of four stairways plus the top platform), the equinox serpent shadow, the largest ball court in the Americas (545 feet, about 166 m, long) and Chichen Itza's 1988 UNESCO listing.",
        "extra": "The used-for text credited this page with Monte Alban facts (founded about 500 BCE, Zapotec capital, Danzantes, UNESCO 1987), none of which are here; they are now checked against EBSCO Research Starters on Monte Alban. The page gives the ball court as 545 feet (166 m), not 168 m.",
    },
    "Britannica on Continental Drift": {
        "citation": "Encyclopaedia Britannica. 'Continental drift.'",
        "cut_note": "the Britannica 'Alfred Wegener' entry.",
        "used": "Wegener's detailed theory of continental drift proposed in 1912, and the later support from seafloor spreading (Harry Hess, early 1960s) and plate tectonic theory (formulated by the late 1960s).",
        "extra": "The page does not give 1915 for Wegener's book.",
    },
    "Britannica on Emperor Meiji": {
        "used": "Birth on 3 November 1852 at Kyoto, accession to the throne in 1867 after his father's death, the coronation ceremony and Charter Oath of Five Principles in 1868, the 1889 Meiji Constitution, and death on 30 July 1912 aged 59.",
        "extra": "The page gives death on 30 July 1912, not 29 July; it gives no day for the accession (the earlier text said 30 January 1867 at age 14) or for the Charter Oath (6 April 1868).",
    },
    "Britannica on Ferdinand de Lesseps and the Suez Canal": {
        "used": "The building of the Suez Canal (1859-69) under Ferdinand de Lesseps, its official inauguration on 17 November 1869, and the British government's 1875 purchase of the khedive's canal shares.",
        "extra": "The page does not give a length of 193 km, conscripted Egyptian labour, or the 1882 invasion; those details in the Suez Canal note are not confirmed here.",
    },
    "Britannica on Filippo Brunelleschi": {
        "used": "Brunelleschi's rediscovery of linear perspective (about 1410 to 1415), Alberti's codification of it in 1435, the dome of Florence Cathedral (1420-36), and the patronage of the Medici bank.",
        "extra": "The page dates the perspective experiments c. 1410-15, not about 1415 alone. It does not give Burckhardt's 1860 book or the lifespans of Leonardo, Michelangelo and Raphael; those details in the Renaissance note are not confirmed here.",
    },
    "Britannica on Hunayn ibn Ishaq": {
        "used": "Hunayn ibn Ishaq (808-873), an Arab scholar whose translations of Plato, Aristotle, Galen and Hippocrates made Greek thought available to Arab scholars, transmitted in Arabic and, more often, Syriac versions.",
        "extra": "The page gives 808 for his birth, not 809. It does not mention the 12th-century Toledo translations into Latin or the debate over the House of Wisdom as an institution; those details are not confirmed here.",
    },
    "Britannica on Menilek II": {
        "citation": "Encyclopaedia Britannica. 'Menilek II.'",
        "cut_note": "Britannica, 'Battle of Adwa' (now the separate source note Britannica on the Battle of Adwa).",
        "used": "Birth on 17 August 1844 at Ankober, kingship of Shewa (1865-89) and imperial reign 1889-1913, imported firearms, expansion of the empire almost to its present borders, the victory over Italy at Adwa on 1 March 1896, and death on 12 December 1913 at Addis Ababa.",
        "extra": "The page dates the battle to 1 March 1896 (the earlier text said 1-2 March) and says he imported firearms; it does not use the word rifles.",
    },
    "Britannica on Sakoku": {
        "used": "The Edo (Tokugawa) period of 1603 to 1867 and its sakoku policy of self-isolation: Spain expelled in 1624, Portuguese ships forbidden in 1639, the Dutch and Chinese confined to Dejima Island at Nagasaki, Perry's arrival in 1853, and the collapse of the Tokugawa shogunate in 1867 followed by the Meiji Restoration.",
        "extra": "The page does not say that Ieyasu became shogun in 1603 or that Edo exceeded one million people, and it dates the collapse of the shogunate to 1867, not 1868.",
    },
    "Britannica on Vasco da Gama": {
        "used": "Departure from Lisbon on 8 July 1497, arrival at Santa Helena Bay on 7 November, the rounding of the Cape of Good Hope on 22 November, and arrival at Calicut on 20 May 1498.",
        "extra": "The page does not mention the Portuguese capture of Goa in 1510 or the end of Zheng He's voyages in 1433.",
    },
    "Britannica on the Chola Dynasty": {
        "used": "Vijayalaya's initiation of the conquest of Pallava territory (reigned about 850 to 870), Rajaraja I (reigned 985 to 1014) and the Brihadishvara Temple at Tanjore (Thanjavur), and the end of the dynasty in 1279.",
        "extra": "The page does not say that Vijayalaya captured Thanjavur, that the temple was completed in 1010, or anything about UNESCO's Great Living Chola Temples; those details in the notes are not confirmed here.",
    },
    "Britannica on the Columbian Exchange": {
        "used": "Crosby's 1972 book dividing the exchange into diseases, animals and plants, the fall of the population of the Americas by 50 to 95 percent by 1650, and the crops and animals exchanged (maize, potatoes, cassava, wheat, rice, horses, cattle).",
        "extra": "The page gives 50 to 95 percent, not 80 to 95 percent. It says Crosby's 1972 book divided the exchange into three categories but does not say that he coined the term.",
    },
    "Britannica on the Coronation of Charlemagne": {
        "used": "Pope Leo III's crowning of Charlemagne as emperor on 25 December 800, two days after Leo cleared himself of the charges against him.",
        "extra": "The page does not mention Charlemagne's sole rule of the Franks from 771.",
    },
    "Britannica on the Dutch East India Company": {
        "used": "The company's foundation in the Dutch Republic in 1602, its trade monopoly between the Cape of Good Hope and the Straits of Magellan, the renaming of Jacatra as Batavia in 1619, and the takeover of its debts and possessions when its charter was revoked in 1799.",
        "extra": "The page does not give the charter date of 20 March 1602, the trading of shares in Amsterdam, or Coen's 1621 invasion of the Banda Islands.",
    },
    "Britannica on the Ediacaran Period": {
        "citation": "Encyclopaedia Britannica. 'Ediacaran Period.'",
        "cut_note": "the Britannica 'Ediacara fauna' entry.",
        "used": "The Ediacara fauna, named after the Ediacara Hills of South Australia, and an assemblage in the Avalon Zone of Newfoundland dated to 565 million years.",
        "extra": "The page does not name Mistaken Point, give a 575 Ma age, or mention Namibia or the White Sea, and it gives the period as about 635 to 541 million years ago (the vault's note uses the current ICS end of 538.8).",
    },
    "Britannica on the Fall of Constantinople": {
        "used": "The 55-day siege ending on 29 May 1453 under Mehmed II, the artillery barrage from 6 April, the Hungarian gunsmith Urban's cannon, and the death of Constantine XI in battle.",
        "extra": "The page spells the gunsmith Urban; the Fall of Constantinople note uses the variant Orban.",
    },
    "Britannica on the Green Revolution": {
        "used": "Norman Borlaug's wheat program in the Mexican Agricultural Program (from 1943), the development of the IR8 rice strain at the International Rice Research Institute in the Philippines, India's 1966 import of Mexican wheat seeds, and the later spread to countries such as Brazil, China, Pakistan and the Philippines.",
        "extra": "The page does not call Borlaug's wheat semi-dwarf and does not give a release year for IR8; those details in the Green Revolution note are not confirmed here.",
    },
    "Britannica on the Haitian Revolution": {
        "used": "The revolution of 1791 to 1804, independence declared on 1 January 1804, and France's 1825 recognition of Haiti in return for an indemnity of nearly 100 million francs payable annually until 1887.",
        "extra": "The page gives the indemnity as nearly 100 million francs, not 150 million (the sum first demanded in 1825 is not stated there). It dates the revolution 1791-1804 but does not give an August 1791 uprising.",
    },
    "Britannica on the Maya": {
        "used": "The Classic Period (about 250 to 900 CE), the cities of Tikal and Calakmul, hieroglyphic writing, the Long Count calendar with its zero date in 3113 BCE, positional notation and the use of zero, and more than five million speakers of some 30 Mayan languages in the early 21st century.",
        "extra": "The page does not give 357 CE for the earliest Maya zero, does not call the script logosyllabic, and says more than five million, not about six million, speakers.",
    },
    "Britannica on the Mongol Empire": {
        "used": "The founding of the Mongol empire in 1206, when Temujin was elected Genghis Khan, and its greatest extent of some 9 million square miles (about 23 million km2), making it the largest contiguous land empire in history.",
        "extra": "The page gives the extent in square miles; the earlier text of about 23 to 24 million km2 is a conversion.",
    },
    "Britannica on the Napoleonic Wars": {
        "citation": "Encyclopaedia Britannica. 'Napoleonic Wars.'",
        "cut_note": "World History Encyclopedia, 'Napoleon's Invasion of Russia' and 'Napoleonic Code.' (the Battle of Austerlitz page is now the separate source note Britannica on the Battle of Austerlitz).",
        "access_override": {"url": "https://www.britannica.com/event/Napoleonic-Wars"},
        "used": "The Napoleonic Wars as a series of wars between Napoleonic France and other European powers that, with the French Revolutionary wars, made up a 23-year period of recurrent conflict ending with the Battle of Waterloo on 18 June 1815.",
        "extra": "The URL of this note previously pointed to the Battle of Austerlitz article, so the earlier text and cache were of that page; the URL now points to the Napoleonic Wars article. The article does not give the proclamation of the Empire on 18 May 1804, the 1812 Russian campaign figures of about 612,000 and about 112,000, or the Napoleonic Code.",
    },
    "Britannica on the Parsis": {
        "used": "The Parsis as descendants of Persian Zoroastrians who emigrated to India to escape persecution by Muslims, arriving in the 8th century (the migration may have been as late as the 10th), settling first at Diu and then in Gujarat.",
        "extra": "The page gives the 8th century, possibly as late as the 10th, not a date of about 936.",
    },
    "Britannica on the Qing Dynasty": {
        "citation": "Encyclopaedia Britannica. 'Qing dynasty.'",
        "cut_note": "the Britannica 'China: The Qing empire' entry.",
        "used": "Qing rule from 1644 to 1911/12, the extension of the empire to include Outer Mongolia, Tibet, Dzungaria, Turkistan and Nepal, and the growth of the population from some 150 million to 450 million.",
        "extra": "The page does not use the name Xinjiang and gives no population figures for 1762 or 1830; it says the population grew from some 150 million to 450 million.",
    },
    "Britannica on the Rigveda": {
        "used": "The Rigveda as the oldest of the sacred books of Hinduism, composed in an ancient form of Sanskrit about 1500 BCE in the Punjab region and preserved orally until it was written down about 300 BCE.",
        "extra": "The page gives no end date of 1000 BCE, does not name the language Vedic Sanskrit, and does not describe the fidelity of the oral transmission.",
    },
    "Britannica on the Russian Revolution": {
        "used": "The two revolutions of 1917 (February, March New Style, and October, November), Nicholas II's abdication on 15 March 1917, and the Bolshevik seizure of power leading to the creation of the Soviet Union.",
        "extra": "The page has a section heading on the Treaty of Brest-Litovsk but no 3 March 1918 date, and no 30 December 1922 date for the formation of the USSR.",
    },
    "Britannica on the Stockton and Darlington Railway": {
        "used": "The opening run of the Stockton and Darlington Railway on 27 September 1825 (Darlington to Stockton at about 15 miles per hour), described as the first railway in the world to operate freight and passenger service with steam traction.",
        "extra": "The page does not mention the Rainhill Trials, Promontory Summit, London railway time in 1840 or North American standard time in 1883.",
    },
    "Britannica on the Sugar Revolution": {
        "used": "The statement that the Sugar Revolution in Barbados had momentous social, economic and political consequences, the island's elite choosing large sugarcane plantations cultivated by oppressed labourers.",
        "extra": "The page is a short stub (a search-result style excerpt from the Barbados article). It gives no date and says nothing about Madeira, Sao Tome, Brazil or Saint-Domingue.",
    },
    "Britannica on the Thirty Years' War": {
        "used": "The war of 1618 to 1648, conventionally dated from the revolt of the Protestant nobles of Bohemia and Austria against Ferdinand II in 1618, and its end with the Treaty of Westphalia (negotiated from 1644 at Munster and Osnabruck, the Spanish-Dutch treaty signed on 30 January 1648 and the treaty of 24 October 1648).",
        "extra": "The page gives no death toll, does not describe the Defenestration of Prague in its article text (only in a link title), and does not say that Spain recognized the Dutch Republic.",
    },
    "Britannica on the Trans-Siberian Railroad": {
        "used": "The start of construction in 1891 under Sergei Witte, the completion in 1916 of a route wholly within Russian territory, the line's passage through Khabarovsk on the Amur River to Vladivostok, and its status as the longest single rail system in the world.",
        "extra": "The page does not give 31 May 1891 or a ceremony at Vladivostok.",
    },
    "Britannica on the Tunguska Event": {
        "used": "The 30 June 1908 explosion (7:14 am, an airburst at 5 to 10 km altitude with no crater), an energy of as much as 15 megatons, trees felled radially for 15 to 30 km over some 2,000 square km, and Kulik's expeditions of 1927 to 1930.",
        "extra": "The page does not give a count of about 80 million trees felled.",
    },
    "Encyclopaedia Britannica": {"skip": True},
}


# ------------------------------------------------------------------------------------------------- new source notes
def meta_of(slug):
    return json.loads((fs.CACHE / f"{slug}.meta.json").read_text(encoding="utf-8"))


def snap_date(s):
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}"


def new_britannica(title, slug, url, citation, used, extra=""):
    m = meta_of(slug)
    d = snap_date(m["snapshot"])
    cav = (f"Read in full on {m['retrieved']} as raw text from a Wayback Machine snapshot dated {d} of britannica.com; the snapshot may "
           f"differ from the current page ({m['chars']:,} characters). {extra}").strip()
    return {"title": title, "citation": citation, "url": url, "kind": "reference", "reliability": "medium",
            "access": "archived-copy", "access_route": f"Wayback Machine snapshot of {d}", "read_on": m["retrieved"],
            "used": used, "caveats": cav}


B = "https://www.britannica.com/"
NEW = [
    new_britannica("Britannica on the Battle of Adwa", "britannica-on-the-battle-of-adwa", B + "event/Battle-of-Adwa",
                   "Encyclopaedia Britannica. 'Battle of Adwa.'",
                   "The Battle of Adwa on 1 March 1896 near Adwa in north-central Ethiopia: the Italian force of 14,500 men against an Ethiopian army of approximately 100,000, more than 6,000 killed in the Italian army (slightly more than half Italians, the rest African askari), 3,000 to 4,000 prisoners, and the Treaty of Addis Ababa of 26 October 1896 abrogating the Treaty of Wichale.",
                   "Added in Tier 3 to replace the generic Encyclopaedia Britannica citation on the Battle of Adwa note. The page does not give a low estimate of 73,000 Ethiopians or an Italian strength of 17,800."),
    new_britannica("Britannica on the Cold War", "britannica-on-the-cold-war", B + "event/Cold-War",
                   "Encyclopaedia Britannica. 'Cold War.'",
                   "The formation of NATO and the first Soviet atomic test in 1949, the Warsaw Pact in 1955, a Berlin crisis in 1961, the 1962 installation of Soviet missiles in Cuba, and the collapse of the Soviet Union in 1991.",
                   "Added in Tier 3 to replace the generic Encyclopaedia Britannica citation on the Cold War note. The page does not give the months of NATO's founding (April) or of the Soviet collapse (December), the day of the Warsaw Pact (14 May 1955), or the building of the Berlin Wall in August 1961 (it names only a Berlin crisis of 1961), and dates the Cuban Missile Crisis only by a photograph caption of 25 October 1962."),
    new_britannica("Britannica on the Meiji Restoration", "britannica-on-the-meiji-restoration", B + "event/Meiji-Restoration",
                   "Encyclopaedia Britannica. 'Meiji Restoration.'",
                   "Perry's arrival in Edo Bay in 1853, the coup d'etat at Kyoto on 3 January 1868, the Charter Oath (April 1868), and the replacement of the domains by prefectures in 1871.",
                   "Added in Tier 3 to replace the generic Encyclopaedia Britannica citation on the Meiji Restoration note. The page does not mention the Convention of Kanagawa (1854) or the Iwakura Mission (1871-73)."),
    new_britannica("Britannica on Kublai Khan", "britannica-on-kublai-khan", B + "biography/Kublai-Khan",
                   "Encyclopaedia Britannica. 'Kublai Khan.'",
                   "Kublai Khan (reigned 1260-94) as the fifth emperor of the Yuan (Mongol) dynasty, who completed the conquest of China in 1279.",
                   "Added in Tier 3 to replace the generic Encyclopaedia Britannica citation on the Mongol Empire note. The page counts the Yuan dynasty from 1206 to 1368 and calls Kublai its fifth emperor; it does not give 1271 for the founding of the Yuan dynasty."),
    new_britannica("Britannica on the Scramble for Africa", "britannica-on-the-scramble-for-africa", B + "event/Scramble-for-Africa",
                   "Encyclopaedia Britannica. 'Scramble for Africa.'",
                   "The extent of European control of Africa (10 percent in the 1870s, about 90 percent by 1914, every present-day country except Ethiopia and Liberia) and the Berlin Conference (15 November 1884 to 26 February 1885).",
                   "Added in Tier 3 to replace the generic Encyclopaedia Britannica citation on the Scramble for Africa note. The page says the 1870s, not 1870."),
    new_britannica("Britannica on Simon Bolivar", "britannica-on-simon-bolivar", B + "biography/Simon-Bolivar",
                   "Encyclopaedia Britannica. 'Simon Bolivar.'",
                   "Bolivar as president of Gran Colombia (1819-30) and dictator of Peru (1823-26), his liberation of New Granada (1819), Venezuela (1821), Quito (1822) and, with the help of Jose de San Martin, Peru (1824) and Bolivia (1825), and his death on 17 December 1830.",
                   "Added in Tier 3 to replace the generic Encyclopaedia Britannica citation on the Simon Bolivar and Latin American Wars of Independence notes. The page does not mention the Guayaquil meeting of 1822 or the Battle of Ayacucho by name."),
    new_britannica("Britannica on the Song Dynasty", "britannica-on-the-song-dynasty", B + "topic/Song-dynasty",
                   "Encyclopaedia Britannica. 'Song dynasty.'",
                   "The Song dynasty (960-1279), the Northern Song founded by Zhao Kuangyin with its capital at Kaifeng, and the Southern Song capital at Lin'an (Hangzhou).",
                   "Added in Tier 3 to replace the generic Encyclopaedia Britannica citation on the Song Dynasty note."),
    new_britannica("Britannica on the Taiping Rebellion", "britannica-on-the-taiping-rebellion", B + "event/Taiping-Rebellion",
                   "Encyclopaedia Britannica. 'Taiping Rebellion.'",
                   "The Taiping Rebellion of 1850 to 1864, which ravaged 17 provinces and took an estimated 20 million lives, the capture of Nanjing in 1853 (renamed Tianjing), and Hong Xiuquan's suicide in June.",
                   "Added in Tier 3 to replace the generic Encyclopaedia Britannica citation on the Taiping Rebellion note. The page gives an estimate of 20 million deaths, not the range of 20 to 30 million in the note, and gives the month of Hong's death but not the day (1 June)."),
    new_britannica("Britannica on Hernan Cortes", "britannica-on-hernan-cortes", B + "biography/Hernan-Cortes",
                   "Encyclopaedia Britannica. 'Hernan Cortes.'",
                   "Hernan Cortes's overthrow of the Aztec empire from 1519 to 1521, with Tenochtitlan taken on 13 August 1521.",
                   "Added in Tier 3 to replace the generic Encyclopaedia Britannica citation on the Mesoamerica note. The saved page also contains a machine-generated 'Britannica AI' summary panel; only the wording that repeats the article text was relied on."),
    new_britannica("Britannica on the Battle of Austerlitz", "britannica-on-the-battle-of-austerlitz", B + "event/Battle-of-Austerlitz",
                   "Encyclopaedia Britannica. 'Battle of Austerlitz.'",
                   "The Battle of Austerlitz on 2 December 1805, the first engagement of the War of the Third Coalition, in which Napoleon's 68,000 troops defeated almost 90,000 Russians and Austrians.",
                   "The Britannica on the Napoleonic Wars note pointed at this page until Tier 3; that note now points at the Napoleonic Wars article and this page is its own source."),
]
_m = meta_of("ebsco-research-starters-on-monte-alban")
NEW.append({
    "title": "EBSCO Research Starters on Monte Alban", "citation": "EBSCO Research Starters. 'Monte Alban.'",
    "url": "https://www.ebsco.com/research-starters/history/monte-alban", "kind": "reference", "reliability": "medium",
    "access": "full-text", "access_route": "the EBSCO Research Starters page, fetched directly", "read_on": _m["retrieved"],
    "used": "Monte Alban established around 500 BCE as the capital of the Zapotec civilization on a hilltop above the Oaxaca Valley, the danzantes stone slabs with hieroglyphs, and UNESCO's 1987 World Heritage designation.",
    "caveats": (f"Read in full on {_m['retrieved']} from ebsco.com fetched directly ({_m['chars']:,} characters). Added in Tier 3 because the Monte Alban note's only check "
                "had been credited to Britannica on Chichen Itza, which does not mention the site. This is a summary article; it puts the site's apogee in period III (200-700 CE) and "
                "the fragmentation of the Zapotec state and eventual abandonment of the capital by about 700 CE, whereas the Monte Alban note says abandoned by about 800 CE."),
})


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


def swap_source(old_title, new_title):
    return [f'"[[{old_title}]]"', f'"[[{new_title}]]"']


NOTES = [
    note("Al-Andalus", rc_=[rc("Conquest from April 711",
        "Roderick was killed in battle near Arcos de la Frontera on 23 July 711 and Muslim rule then spread over much of the Iberian Peninsula; after 756 Abd al-Rahman I established an independent Umayyad emirate at Cordoba; Abd al-Rahman III proclaimed himself caliph in 929; the Catholic Monarchs completed the conquest of Granada in 1492 [Britannica on Al-Andalus]")]),
    note("Beringia", rc_=[rc("Steppe-tundra with mammoths and bison",
        "Beringia was an intermittent Pleistocene land connection between northeastern Asia and northwestern North America; the most recent one began to appear about 38,000 years ago and was at its greatest extent about 20,000 years ago, when sea level was lowered by as much as about 120 m, running some 1,600 km north to south; much of it had a dry climate and was not glaciated, with cold-hardy tundra vegetation that let land mammals move into North America [Britannica on Beringia]")]),
    note("Breakup of Pangaea", rc_=[rc("Wegener presented continental drift in 1912",
        "Alfred Wegener proposed a detailed theory of continental drift in 1912, and the concepts of seafloor spreading (Harry Hess, early 1960s) and plate tectonics (formulated by the late 1960s) later supported it [Britannica on Continental Drift]")]),
    note("Charlemagne", rc_=[rc("Sole ruler of the Franks from 771",
        "Pope Leo III crowned Charlemagne emperor on 25 December 800, two days after Leo cleared himself of the charges against him [Britannica on the Coronation of Charlemagne]")]),
    note("Chichen Itza",
         rc_=[rc("El Castillo has 365 steps",
                 "El Castillo has 91 steps on each of four sides which, with the top platform, total 365; the ball court, the largest in the Americas, is 545 feet (166 m) long and 223 feet (68 m) wide; Chichen Itza was designated a UNESCO World Heritage site in 1988 [Britannica on Chichen Itza]")],
         rep=[rc("- The site has the largest known Mesoamerican ball court, about 168 meters long, and a sacred cenote used for offerings.",
                 "- The site has the largest ball court in the Americas, about 166 meters (545 feet) long, and a sacred cenote used for offerings.")]),
    note("Chola Dynasty", rc_=[rc("Vijayalaya took Thanjavur",
        "Vijayalaya (reigned about 850-870) initiated the conquest of the Pallava territory; Rajaraja I (reigned 985-1014) built the Brihadishvara Temple at Tanjore (Thanjavur); the Chola dynasty ended in 1279 [Britannica on the Chola Dynasty]")]),
    note("Columbian Exchange",
         rc_=[rc("Term coined by Alfred Crosby in 1972",
                 "Crosby's 1972 book divided the Columbian Exchange into three categories, diseases, animals and plants; across the Americas populations fell by 50 to 95 percent by 1650; maize (corn), potatoes and cassava spread from the Americas, and wheat, rice and horses to the Americas [Britannica on the Columbian Exchange]")],
         rep=[rc("estimates of the loss vary widely.", "estimates of the loss vary widely, from about 50 to 95 percent of the population by 1650.")]),
    note("Dutch East India Company", rc_=[rc("Chartered 20 March 1602",
        "The company was founded in the Dutch Republic in 1602 and granted a trade monopoly between the Cape of Good Hope and the Straits of Magellan; in 1619 it renamed Jacatra Batavia (now Jakarta); the Dutch government revoked its charter and took over its debts and possessions in 1799 [Britannica on the Dutch East India Company]")]),
    note("Early Modern Period", rc_=[rc("Term 'Columbian Exchange' coined by Crosby in 1972",
        "Crosby's 1972 book divided the Columbian Exchange into diseases, animals and plants; across the Americas populations fell by 50 to 95 percent by 1650 [Britannica on the Columbian Exchange]")]),
    note("Ediacaran Biota", rc_=[rc("Fossil localities include",
        "The Ediacara fauna is named after the Ediacara Hills of South Australia, and one of the oldest dated assemblages of Ediacaran organisms, in the Avalon Zone of Newfoundland, has an age of 565 million years [Britannica on the Ediacaran Period]")]),
    note("Emperor Meiji", rc_=[rc("Born 3 November 1852",
        "Meiji was born on 3 November 1852 at Kyoto and was raised to the throne in 1867 after his father's death; his coronation ceremony was carried out in 1868, when he took the Charter Oath of Five Principles; the Meiji Constitution was promulgated in 1889; he died on 30 July 1912 aged 59 [Britannica on Emperor Meiji]")]),
    note("Fall of Constantinople",
         rc_=[rc("Siege from 6 April to 29 May 1453",
                 "Sultan Mehmed II besieged Constantinople for 55 days and conquered it on 29 May 1453; the Ottoman artillery barrage began on 6 April; the Hungarian gunsmith Urban was tasked with building cannon powerful enough to bring down the walls; the last Byzantine emperor, Constantine XI, died in battle [Britannica on the Fall of Constantinople]")],
         rep=[rc("including those cast by the engineer Orban.", "including those cast by the Hungarian engineer Urban (also spelled Orban).")]),
    note("Flowering Plants",
         rc_=[rc("Oldest angiosperm pollen about 134 Ma",
                 "Fossil angiosperm pollen is found in the Hauterivian and Barremian ages, about 132.9 to 125 million years ago, though angiosperm-like pollen found in Switzerland in 2013 dates to the Middle Triassic (about 247.2 to 242 million years ago); Archaefructus from the Yixian Formation of China is dated to about 125 million years ago; molecular clocks give older origins [Britannica on Angiosperm Paleobotany and Evolution; Britannica on Archaefructus; Nature Communications 2025 Angiosperm Crown Age]")],
         rep=[rc("- The oldest widely accepted angiosperm pollen is about 134 million years old.",
                 "- The oldest widely accepted angiosperm pollen dates to the Hauterivian and Barremian ages of the Early Cretaceous, about 133 to 125 million years ago.")]),
    note("Green Revolution", rc_=[rc("Borlaug's semi-dwarf wheat in Mexico",
        "Norman Borlaug, who oversaw the wheat program of the Mexican Agricultural Program begun in 1943, developed wheat varieties that made up about 95 percent of Mexican wheat by the early 1960s; scientists at the International Rice Research Institute in the Philippines developed the IR8 rice strain; in 1966 India imported 18,000 tons of new Mexican wheat seeds [Britannica on the Green Revolution]")]),
    note("Haitian Revolution", rc_=[rc("Uprising in August 1791",
        "The Haitian Revolution was a series of conflicts during 1791-1804; on 1 January 1804 the entire island was declared independent under the name Haiti; France recognized Haitian independence in 1825 in return for a large indemnity (nearly 100 million francs) to be paid annually until 1887 [Britannica on the Haitian Revolution]")]),
    note("Maya", rc_=[rc("Classic Period about 250-900 CE",
        "The rise of the Maya began about 250 CE and the Classic Period lasted until about 900 CE, with major cities including Tikal and Calakmul; the Maya developed hieroglyphic writing and calendars including the Long Count, with a zero date in 3113 BCE, and used positional notation and the zero; in the early 21st century some 30 Mayan languages were spoken by more than five million people [Britannica on the Maya]")]),
    note("Menelik II", rc_=[rc("Born 17 August 1844",
        "Menilek II was born on 17 August 1844 at Ankober, was king of Shewa (1865-89) and emperor of Ethiopia (1889-1913), imported firearms to equip his armies, expanded the empire almost to its present-day borders, repelled an Italian invasion at the Battle of Adwa on 1 March 1896, and died on 12 December 1913 at Addis Ababa [Britannica on Menilek II]")]),
    note("Monte Alban", src=["EBSCO Research Starters on Monte Alban"],
         rc_=[rc("Founded about 500 BCE as the Zapotec capital",
                 "Monte Alban was established around 500 BCE as the capital of the Zapotec civilization on a hilltop above the Oaxaca Valley; it is known for the danzantes, stone slabs depicting human figures with hieroglyphs; UNESCO designated the site a World Heritage Site in 1987 [EBSCO Research Starters on Monte Alban]")],
         rep=[swap_source("Britannica on Chichen Itza", "EBSCO Research Starters on Monte Alban")]),
    note("Napoleonic Wars", src=["Britannica on the Battle of Austerlitz"],
         rc_=[rc("Empire proclaimed 18 May 1804",
                 "The Napoleonic Wars were a series of wars between Napoleonic France and other European powers that, with the French Revolutionary wars, made up a 23-year period of recurrent conflict ending with the Battle of Waterloo on 18 June 1815, fought by Wellington and Blucher [Britannica on the Napoleonic Wars]")],
         checks=["Napoleon's 68,000 troops defeated almost 90,000 Russians and Austrians at the Battle of Austerlitz on 2 December 1805, the first engagement of the War of the Third Coalition [Britannica on the Battle of Austerlitz]"]),
    note("Peace of Westphalia",
         rc_=[rc("Treaties signed at Osnabruck and Munster",
                 "The Thirty Years' War ended with the Treaty of Westphalia in 1648, negotiated from 1644 in the Westphalian towns of Munster and Osnabruck; the Spanish-Dutch treaty was signed on 30 January 1648, and the treaty of 24 October 1648 comprehended the Holy Roman emperor Ferdinand III, the other German princes, France and Sweden [Britannica on the Thirty Years' War]")],
         rep=[rc("- The treaties were signed in October 1648 in the Westphalian cities of Osnabruck and Munster.",
                 "- The peace was negotiated from 1644 in the Westphalian cities of Osnabruck and Munster; the Spanish-Dutch treaty was signed on 30 January 1648, and the treaty involving the Holy Roman emperor, the German princes, France, and Sweden on 24 October 1648.")]),
    note("Portuguese Sea Route to India", rc_=[rc("Da Gama left Lisbon on 8 July 1497",
        "Da Gama sailed from Lisbon on 8 July 1497, reached Santa Helena Bay on 7 November, rounded the Cape of Good Hope on 22 November, and reached Calicut on 20 May 1498 [Britannica on Vasco da Gama]")]),
    note("Qing Dynasty", rc_=[rc("Qing rule began in 1644",
        "The Qing dynasty ruled China from 1644 to 1911/12; the empire was extended to include Outer Mongolia, Tibet, Dzungaria, Turkistan and Nepal; the population grew from some 150 million to 450 million [Britannica on the Qing Dynasty]")]),
    note("Railways", rc_=[rc("Stockton and Darlington opened 27 September 1825",
        "The first engine of the Stockton and Darlington Railway ran from Darlington to Stockton on 27 September 1825 at about 15 miles per hour, and the line is described as the first railway in the world to operate freight and passenger service with steam traction [Britannica on the Stockton and Darlington Railway]")]),
    note("Renaissance",
         rc_=[rc("Brunelleschi devised linear perspective about 1415",
                 "Brunelleschi rediscovered the principles of linear perspective in about 1410-15 and built the dome of Florence Cathedral (1420-36); Alberti set the principles down in Della pittura in 1435; Giovanni di Bicci de' Medici, founder of the Medici bank, had commissioned Brunelleschi to design the sacristy of San Lorenzo by the early 1420s [Britannica on Filippo Brunelleschi]")],
         rep=[rc("in experiments of about 1415 to 1420", "in experiments of about 1410 to 1415")]),
    note("Russian Revolution", rc_=[rc("Nicholas II abdicated 15 March 1917",
        "Nicholas II abdicated on 15 March 1917; the two revolutions of 1917, in February (March, New Style) and October (November), overthrew the imperial government and placed the Bolsheviks in power, leading to the creation of the Soviet Union [Britannica on the Russian Revolution]")]),
    note("Suez Canal", rc_=[rc("Opened 17 November 1869",
        "The Suez Canal was built across the Isthmus of Suez in 1859-69 under Ferdinand de Lesseps and officially inaugurated on 17 November 1869 by the empress Eugenie; in 1875 the British government, on Disraeli's initiative, bought the khedive Ismail's Suez Canal shares and became the largest shareholder [Britannica on Ferdinand de Lesseps and the Suez Canal]")]),
    note("Sugar Plantation Complex", rc_=[rc("Barbados sugar revolution by the mid-1640s",
        "The Sugar Revolution in Barbados had momentous social, economic and political consequences: the island's elite chose the form of sugar production that yielded the greatest profit, large sugarcane plantations cultivated by oppressed labourers, at great social cost [Britannica on the Sugar Revolution]")]),
    note("Thirty Years' War", rc_=[rc("War began with the 1618 Defenestration of Prague",
        "The war is conventionally held to have begun in 1618, when Ferdinand II, as king of Bohemia, tried to impose Roman Catholic absolutism and the Protestant nobles of Bohemia and Austria rose in rebellion, and it ended with the Treaty of Westphalia in 1648 [Britannica on the Thirty Years' War]")]),
    note("Tokugawa Shogunate",
         rc_=[rc("Ieyasu became shogun in 1603",
                 "The Edo (Tokugawa) period ran from 1603 to 1867 and the Tokugawa shogunate enforced the sakoku policy of self-isolation; Spain had been expelled in 1624 and Portuguese ships were forbidden in 1639; the Dutch and Chinese were confined to Dejima Island at Nagasaki; the shogunate collapsed in 1867 and the Meiji Restoration followed [Britannica on Sakoku]")],
         rep=[rc("- The shogunate ended in 1868 with the [[Meiji Restoration]].",
                 "- The shogunate collapsed in 1867, and imperial rule was restored the following year in the [[Meiji Restoration]]."),
              rc("ruled Japan from 1603 to 1868", "ruled Japan from 1603 to 1867")]),
    note("Trans-Siberian Railway", rc_=[rc("Inaugurated 31 May 1891",
        "Construction of the Trans-Siberian Railroad began in 1891 under Sergei Witte, who convinced Alexander III to begin it; a route wholly within Russian territory was completed in 1916; it runs between Moscow and Vladivostok through Khabarovsk on the Amur River and is called the longest single rail system in the world [Britannica on the Trans-Siberian Railroad]")]),
    note("Translation Movement and the House of Wisdom", rc_=[rc("Hunayn ibn Ishaq (809-873)",
        "Hunayn ibn Ishaq (808-873) was an Arab scholar whose translations of Plato, Aristotle, Galen and Hippocrates made Greek thought accessible to Arab scholars; from his translators' school in Baghdad he and his students transmitted Arabic and, more frequently, Syriac versions of the classical Greek texts [Britannica on Hunayn ibn Ishaq]")]),
    note("Tunguska Event", rc_=[rc("Airburst on 30 June 1908",
        "The explosion occurred at 7:14 am on 30 June 1908 at an altitude of 5-10 km, with no impact crater, flattening some 2,000 square km of forest; its energy is estimated at as much as 15 megatons of TNT and it felled trees radially for 15-30 km; Leonid Kulik led expeditions to the site in 1927-30 [Britannica on the Tunguska Event]")]),
    note("Umayyad Caliphate", rc_=[rc("Abd al-Malik (685-705) completed the Dome of the Rock",
        "Abd al-Malik was the fifth Umayyad caliph (685-705); his reign saw a wave of Islamization and the construction of the Dome of the Rock in Jerusalem, and his administrative reforms included the adoption of Arabic as the imperial language and the issuance of coinage [Britannica on Abd al-Malik]")]),
    note("Vedic Period", rc_=[rc("Rigveda dated to about 1500-1000 BCE",
        "The Rigveda, the oldest of the sacred books of Hinduism, was composed in an ancient form of Sanskrit about 1500 BCE in what is now the Punjab region of India and Pakistan, and was preserved orally before it was written down about 300 BCE [Britannica on the Rigveda]")]),
    note("Zoroastrianism", rc_=[rc("Parsis migrated to Gujarat from about 936",
        "The Parsis are descended from Persian Zoroastrians who emigrated to India to avoid religious persecution by Muslims, arriving in the 8th century (the migration may have taken place as late as the 10th century), and settled first at Diu and then in Gujarat [Britannica on the Parsis]")]),
    # ---- the ten notes that cited only the generic Encyclopaedia Britannica homepage: re-pointed to a specific article
    note("Battle of Adwa", src=[],
         rc_=[rc("1 March 1896; forces of about 73,000-100,000",
                 "The Battle of Adwa took place on 1 March 1896 near Adwa in north-central Ethiopia; the Italians advanced with 14,500 men against an Ethiopian army of approximately 100,000; the number killed in the Italian army is estimated at more than 6,000, slightly more than half of them Italians and the rest African askari, and between 3,000 and 4,000 of those fighting under Italian command were taken prisoner; Italy signed the Treaty of Addis Ababa on 26 October 1896, abrogating the Treaty of Wichale and recognizing Ethiopia's sovereign independence [Britannica on the Battle of Adwa]")],
         rep=[swap_source("Encyclopaedia Britannica", "Britannica on the Battle of Adwa"),
              rc("- Ethiopian forces numbered roughly 73,000 to 100,000 against about 15,000 to 18,000 Italian and colonial troops.",
                 "- Ethiopian forces numbered roughly 73,000 to over 100,000 against about 14,500 to 18,000 Italian and colonial troops."),
              rc("- Italian casualties were around 6,000, with several thousand captured.",
                 "- More than 6,000 of the Italian army were killed, slightly more than half of them Italians and the rest African askari, and between 3,000 and 4,000 of those fighting under Italian command were taken prisoner.")]),
    note("Cold War", rc_=[rc("NATO April 1949",
        "The United States and its European allies formed NATO in 1949, and the Soviets exploded their first atomic warhead that year; the Warsaw Pact was formed in 1955; a Berlin crisis occurred in 1961; in 1962 the Soviet Union began to install missiles in Cuba; the Cold War ended with the collapse of the Soviet Union in 1991 [Britannica on the Cold War]")],
         rep=[swap_source("Encyclopaedia Britannica", "Britannica on the Cold War")]),
    note("Latin American Wars of Independence", rc_=[rc("Guayaquil meeting 26 July 1822",
        "Bolivar was president of Gran Colombia (1819-30) and freed New Granada (1819), Venezuela (1821), Quito (1822) and, with the help of Jose de San Martin, Peru (1824) [Britannica on Simon Bolivar]")],
         rep=[swap_source("Encyclopaedia Britannica", "Britannica on Simon Bolivar")]),
    note("Meiji Restoration", rc_=[rc("Perry 1853; Kanagawa 1854",
        "Commodore Matthew Perry arrived in Edo Bay in 1853 with a squadron of Black Ships; the restoration event itself was a coup d'etat at Kyoto on 3 January 1868; the Charter Oath (April 1868) committed the government to deliberative assemblies and a worldwide search for knowledge; the domains were abolished and replaced by prefectures in 1871 [Britannica on the Meiji Restoration]")],
         rep=[swap_source("Encyclopaedia Britannica", "Britannica on the Meiji Restoration")]),
    note("Mesoamerica", rc_=[rc("Spanish conquest of the Aztec Empire 1519-1521",
        "Hernan Cortes overthrew the Aztec empire from 1519 to 1521, and the Spanish took Tenochtitlan on 13 August 1521 [Britannica on Hernan Cortes]")],
         rep=[swap_source("Encyclopaedia Britannica", "Britannica on Hernan Cortes")]),
    note("Mongol Empire", rc_=[rc("Kublai Khan founded the Yuan dynasty in 1271",
        "Kublai Khan reigned 1260-94 as the fifth emperor of the Yuan (Mongol) dynasty and completed the conquest of China in 1279 [Britannica on Kublai Khan]")],
         rep=[swap_source("Encyclopaedia Britannica", "Britannica on Kublai Khan")]),
    note("Scramble for Africa", rc_=[rc("About 10 percent European-controlled in 1870",
        "In the 1870s only 10 percent of African territory was controlled by European countries, but by 1914 about 90 percent had been incorporated into a European empire, including every present-day country except Ethiopia and Liberia; the Berlin Conference ran from 15 November 1884 to 26 February 1885 [Britannica on the Scramble for Africa]")],
         rep=[swap_source("Encyclopaedia Britannica", "Britannica on the Scramble for Africa")]),
    note("Simón Bolívar", rc_=[rc("Guayaquil 1822; Ayacucho 1824",
        "Bolivar was president of Gran Colombia (1819-30) and dictator of Peru (1823-26), freed Quito (1822), Peru (1824) and Bolivia (1825), and died of tuberculosis on 17 December 1830 aged 47 [Britannica on Simon Bolivar]")],
         rep=[swap_source("Encyclopaedia Britannica", "Britannica on Simon Bolivar")]),
    note("Song Dynasty", rc_=[rc("960-1279",
        "The Song dynasty lasted from 960 to 1279; its Northern Song was founded by Zhao Kuangyin, with its capital at Kaifeng [Britannica on the Song Dynasty]")],
         rep=[swap_source("Encyclopaedia Britannica", "Britannica on the Song Dynasty")]),
    note("Taiping Rebellion", rc_=[rc("1850-1864; 17 provinces",
        "The Taiping Rebellion lasted from 1850 to 1864 and took an estimated 20 million lives, ravaging 17 provinces; the Taipings captured Nanjing in 1853, renaming it Tianjing, and Hong Xiuquan, ailing and refusing all requests to flee the city, committed suicide in June [Britannica on the Taiping Rebellion]")],
         rep=[swap_source("Encyclopaedia Britannica", "Britannica on the Taiping Rebellion")]),
]

# ------------------------------------------------------------------------- the generic homepage note
GENERIC_UPDATE = {
    "title": "Encyclopaedia Britannica",
    "set": {"access": "not-consulted", "access_route": "none: the Britannica home page stands for the whole work; no article was read under this title"},
    "used": "Stands for Encyclopaedia Britannica as a whole when a note cites it without naming an article. No article was read under this title, so a check that cites only this note is not confirmed by any text read; wherever possible such checks have been re-pointed to a specific article (see the source notes titled Britannica on ...).",
    "caveats": "Only the home page was fetched (through a Wayback Machine snapshot dated 2026-09-24, 7,607 characters of navigation and headlines, no article content). Many checks still cite this note together with another source (Wikipedia, World History Encyclopedia, UNESCO); they are to be resolved in Tiers 4 and 5 when that other source is read. A tertiary source: check primary or scholarly sources for anything that matters.",
    "mark": "done",
}

# ------------------------------------------------------------------------------------------------- discrepancies
def d(note_, source, was, says, action):
    return {"note": note_, "source": source, "was": was, "text_says": says, "action": action}


DISC = [
    d("Columbian Exchange; Early Modern Period", "Britannica on the Columbian Exchange", "disease mortality estimates of 80-95 percent; term coined by Crosby in 1972",
      "Populations across the Americas fell by 50 to 95 percent by 1650; Crosby's 1972 book divided the exchange into diseases, animals and plants (the page does not say he coined the term).",
      "Checks rewritten; the Columbian Exchange bullet now gives the 50 to 95 percent range."),
    d("Haitian Revolution", "Britannica on the Haitian Revolution", "indemnity of 150 million francs in 1825; uprising in August 1791",
      "France recognized independence in 1825 for a large indemnity (nearly 100 million francs) payable annually until 1887; the revolution is dated 1791-1804 with no August 1791 uprising.",
      "Check narrowed to the page; the note text (which says only 'a large indemnity (1825)') is unchanged; the 150 million figure and August 1791 are in unresolved.md."),
    d("Translation Movement and the House of Wisdom", "Britannica on Hunayn ibn Ishaq", "Hunayn ibn Ishaq (809-873)", "Born 808, died 873.", "Check corrected to 808; Toledo and House of Wisdom details logged in unresolved.md."),
    d("Emperor Meiji", "Britannica on Emperor Meiji", "died 29 July 1912; became emperor on 30 January 1867 aged 14; Charter Oath 6 April 1868",
      "Died 30 July 1912 (aged 59); raised to the throne in 1867 after his father's death; coronation ceremony and Charter Oath in 1868; no accession day or Charter Oath day.",
      "Check corrected; the note text gives only the years, so it is unchanged. The accession date needs a second source (30 January 1867 may be the date of his father's death)."),
    d("Maya", "Britannica on the Maya", "about six million Maya speakers today; earliest Maya zero in 357 CE; logosyllabic script",
      "More than five million speakers of some 30 Mayan languages; the Long Count has a zero date in 3113 BCE; hieroglyphic writing; no 357 CE.",
      "Check rewritten to the page; the note text (millions of speakers, use of zero) is unchanged."),
    d("Qing Dynasty", "Britannica on the Qing Dynasty", "population from about 200 million (1762) to about 395 million (1830); Mongolia, Tibet and Xinjiang incorporated by the mid-18th century",
      "The population grew from some 150 million to 450 million; the empire was extended to include Outer Mongolia, Tibet, Dzungaria, Turkistan and Nepal; the name Xinjiang does not appear.",
      "Check rewritten to the page; the note text is unchanged (Xinjiang is the modern name for Dzungaria and Turkistan)."),
    d("Tokugawa Shogunate", "Britannica on Sakoku", "The shogunate ended in 1868 with the Meiji Restoration; ruled Japan from 1603 to 1868",
      "The Edo (Tokugawa) period is dated 1603-1867 and the shogunate is said to have collapsed in 1867, with the Meiji Restoration following.",
      "Summary and Facts bullet changed to 1867 (Restoration 1868); check rewritten. Other sources date the shogunate's end to 1868, so this may need a second source."),
    d("Zoroastrianism", "Britannica on the Parsis", "Parsis migrated to Gujarat from about 936", "Arrived in India in the 8th century; the migration may have been as late as the 10th century.", "Check rewritten; the note text gives no date for the migration."),
    d("Chichen Itza", "Britannica on Chichen Itza", "ball court is 168 m long, the largest known Mesoamerican ball court", "545 feet (166 m) long, the largest ball court in the Americas.", "Facts bullet and check changed to 166 m and the Americas."),
    d("Monte Alban", "Britannica on Chichen Itza", "Founded about 500 BCE as the Zapotec capital; Danzantes slabs; UNESCO 1987 (cited to Britannica on Chichen Itza)",
      "The Chichen Itza page does not mention Monte Alban; the claims come from EBSCO Research Starters on Monte Alban, which confirms all three.",
      "Added source note EBSCO Research Starters on Monte Alban and re-attributed the check; the wrong source link was replaced."),
    d("Napoleonic Wars", "Britannica on the Napoleonic Wars", "Empire proclaimed 18 May 1804; about 612,000 entered Russia in 1812 and about 112,000 returned; Napoleonic Code 1804 (cited to a source note whose URL was the Battle of Austerlitz article)",
      "The URL was the Austerlitz page, which supports only Austerlitz on 2 December 1805; the real Napoleonic Wars article supports the 23-year span and Waterloo on 18 June 1815 but not the other figures.",
      "Source URL corrected to the Napoleonic Wars article; Austerlitz became its own source note (Britannica on the Battle of Austerlitz); check split; the other figures are in unresolved.md."),
    d("Flowering Plants", "Britannica on Angiosperm Paleobotany and Evolution", "Oldest angiosperm pollen about 134 Ma",
      "Fossil pollen in the Hauterivian and Barremian ages, about 132.9 to 125 Ma; angiosperm-like pollen of 2013 from Switzerland dates to the Middle Triassic (about 247.2 to 242 Ma).",
      "Facts bullet changed to about 133 to 125 million years ago; check rewritten."),
    d("Peace of Westphalia", "Britannica on the Thirty Years' War", "Treaties signed at Osnabruck and Munster between May and October 1648 ended the Eighty Years' War; the treaties were signed in October 1648",
      "Negotiated from 1644 at Munster and Osnabruck; the Spanish-Dutch treaty was signed on 30 January 1648 and the treaty of 24 October 1648 included the emperor, the German princes, France and Sweden.",
      "Facts bullet and check rewritten to the two dates; Spain's recognition of the Dutch Republic is not on the page and is logged in unresolved.md."),
    d("Battle of Adwa", "Britannica on the Battle of Adwa", "forces of about 73,000-100,000 vs 14,500-17,800; about 6,000 Italian casualties",
      "The Italians had 14,500 men against about 100,000 Ethiopians; more than 6,000 of the Italian army were killed (slightly more than half Italians, the rest askari) and 3,000 to 4,000 were taken prisoner.",
      "Facts bullets and check rewritten; casualties now stated as killed."),
    d("Renaissance", "Britannica on Filippo Brunelleschi", "Brunelleschi's linear perspective in experiments of about 1415 to 1420", "c. 1410-15; the dome of Florence Cathedral is dated 1420-36.", "Facts bullet changed to about 1410 to 1415; check rewritten."),
    d("Mongol Empire", "Britannica on Kublai Khan", "Kublai Khan founded the Yuan dynasty in China in 1271",
      "Kublai reigned 1260-94 as the fifth emperor of the Yuan (Mongol) dynasty (counted 1206-1368 by Britannica) and completed the conquest of China in 1279; 1271 is not given.",
      "Check narrowed; the note text is unchanged (the 1271 proclamation of the Yuan name is commonly given) and 1271 is logged in unresolved.md."),
    d("Taiping Rebellion", "Britannica on the Taiping Rebellion", "20-30 million deaths (higher estimates exist); Hong died 1 June 1864",
      "An estimated 20 million lives; Hong Xiuquan committed suicide in June.", "Check narrowed to the page's figure; the note text keeps the wider range, logged in unresolved.md."),
    d("Menelik II", "Britannica on Menilek II", "won at Adwa on 1-2 March 1896 with modern rifles", "The Battle of Adwa was fought on 1 March 1896; he imported firearms.", "Check rewritten; the note text already says 1 March."),
    d("Fall of Constantinople", "Britannica on the Fall of Constantinople", "Orban's cannon", "The page names the Hungarian gunsmith Urban.", "Note bullet now says Urban (also spelled Orban); check rewritten."),
    d("Sugar Plantation Complex", "Britannica on the Sugar Revolution", "Barbados sugar revolution by the mid-1640s; Madeira and Sao Tome; Brazil largest producer by the mid-16th century; Saint-Domingue largest in the late 18th century",
      "The cached page is a stub that says only that the Sugar Revolution in Barbados had momentous social, economic and political consequences.",
      "Check reduced to that statement; every other atom is logged in unresolved.md."),
]

# ------------------------------------------------------------------------------------------------ unresolved.md
U = [
    ("Al-Andalus", "Conquest from April 711; Granada surrendered in January 1492 (page: 23 July 711 for the battle that killed Roderick; 1492 only)", "Britannica on Al-Andalus"),
    ("Umayyad Caliphate", "Dome of the Rock completed in 691 (page: built during his reign, no date)", "Britannica on Abd al-Malik"),
    ("Flowering Plants", "Oldest angiosperm pollen about 134 Ma (page: Hauterivian-Barremian, 132.9 to 125 Ma); note now says about 133 to 125", "Britannica on Angiosperm Paleobotany and Evolution"),
    ("Beringia", "Steppe-tundra with mammoths, bison and horses; Beringian standstill hypothesis; flooding from about 11,000 years ago and full submergence 10,000 to 9,000 years ago (page: Bering Strait opened at the end of the Pleistocene, about 11,700 years ago)", "Britannica on Beringia"),
    ("Breakup of Pangaea", "Wegener published his book in 1915", "Britannica on Continental Drift"),
    ("Charlemagne", "Sole ruler of the Franks from 771", "Britannica on the Coronation of Charlemagne"),
    ("Chola Dynasty", "Vijayalaya took Thanjavur about 850; Brihadisvara Temple completed in 1010; UNESCO Great Living Chola Temples", "Britannica on the Chola Dynasty"),
    ("Columbian Exchange; Early Modern Period", "Term coined by Alfred Crosby in 1972 (page: Crosby's 1972 book divided the exchange into three categories)", "Britannica on the Columbian Exchange"),
    ("Dutch East India Company", "Chartered 20 March 1602; shares traded in Amsterdam; Banda Islands invaded 1621", "Britannica on the Dutch East India Company"),
    ("Ediacaran Biota", "Mistaken Point (Newfoundland, 565-575 Ma), Namibia and the White Sea as fossil localities; period end of 538.8 Ma (page: 541 Ma)", "Britannica on the Ediacaran Period"),
    ("Emperor Meiji", "Accession on 30 January 1867 at age 14; Charter Oath on 6 April 1868 (page: 1867 and 1868 only; the Meiji Restoration page gives April 1868)", "Britannica on Emperor Meiji"),
    ("Green Revolution", "Borlaug's semi-dwarf wheat; IR8 released in 1966", "Britannica on the Green Revolution"),
    ("Haitian Revolution", "Uprising in August 1791; the 150 million francs first demanded in 1825 (page: nearly 100 million francs until 1887)", "Britannica on the Haitian Revolution"),
    ("Maya", "Earliest Maya zero in 357 CE; script described as logosyllabic and largely deciphered", "Britannica on the Maya"),
    ("Peace of Westphalia", "Spain recognized the independence of the Dutch Republic", "Britannica on the Thirty Years' War"),
    ("Mongol Empire", "Kublai Khan founded the Yuan dynasty in 1271", "Britannica on Kublai Khan"),
    ("Portuguese Sea Route to India", "Goa captured 25 November 1510; Zheng He's voyages ended in 1433", "Britannica on Vasco da Gama"),
    ("Qing Dynasty", "Population about 200 million (1762) and about 395 million (1830); Xinjiang incorporated by the mid-18th century", "Britannica on the Qing Dynasty"),
    ("Railways", "Rainhill Trials 6-14 October 1829 won by Rocket; Promontory Summit 10 May 1869; Great Western Railway adopted London time in 1840; North American standard time 18 November 1883; the Liverpool and Manchester Railway of 1830", "Britannica on the Stockton and Darlington Railway"),
    ("Renaissance", "Burckhardt's 1860 book; Leonardo 1452-1519, Michelangelo 1475-1564, Raphael 1483-1520", "Britannica on Filippo Brunelleschi"),
    ("Russian Revolution", "Brest-Litovsk 3 March 1918; USSR formed 30 December 1922", "Britannica on the Russian Revolution"),
    ("Suez Canal", "About 193 km long; built with conscripted Egyptian labour; Britain invaded in 1882", "Britannica on Ferdinand de Lesseps and the Suez Canal"),
    ("Sugar Plantation Complex", "Barbados sugar revolution by the mid-1640s; Madeira and Sao Tome plantation model; Brazil largest producer by the mid-16th century; Saint-Domingue largest in the late 18th century", "Britannica on the Sugar Revolution"),
    ("Thirty Years' War", "Deaths estimated at 4.5 to 8 million; the Defenestration of Prague as the start", "Britannica on the Thirty Years' War"),
    ("Tokugawa Shogunate", "Ieyasu became shogun in 1603 and ruled from Edo; Edo above one million by the early 18th century", "Britannica on Sakoku"),
    ("Trans-Siberian Railway", "Inaugurated on 31 May 1891 at Vladivostok, with a ceremony attended by the future Nicholas II", "Britannica on the Trans-Siberian Railroad"),
    ("Translation Movement and the House of Wisdom", "Toledo translations into Latin in the 12th century; the House of Wisdom's institutional character is debated", "Britannica on Hunayn ibn Ishaq"),
    ("Tunguska Event", "About 80 million trees felled", "Britannica on the Tunguska Event"),
    ("Vedic Period", "Rigveda dated to 1500 to 1000 BCE; the language called Vedic Sanskrit; transmission with high fidelity", "Britannica on the Rigveda"),
    ("Battle of Adwa", "Low estimate of 73,000 Ethiopians and an Italian strength of 17,800 (page: about 100,000 against 14,500)", "Britannica on the Battle of Adwa"),
    ("Cold War", "NATO in April 1949; Warsaw Pact on 14 May 1955; Berlin Wall in August 1961; USSR dissolved in December 1991; Cuban Missile Crisis in October 1962 (page: years only, plus a photograph caption of 25 October 1962)", "Britannica on the Cold War"),
    ("Latin American Wars of Independence; Simon Bolivar", "Guayaquil meeting on 26 July 1822; Ayacucho on 9 December 1824; Gran Colombia dissolved within seven years (the Latin American note also cites Latin American Independence Dates (Search Summaries), a Tier 6 source)", "Britannica on Simon Bolivar"),
    ("Meiji Restoration", "Convention of Kanagawa 1854; Iwakura Mission 1871-73 (the note also cites Meiji Restoration Dates (Search Summaries), a Tier 6 source)", "Britannica on the Meiji Restoration"),
    ("Taiping Rebellion", "Deaths of 20 to 30 million (page: an estimated 20 million); Hong Xiuquan died on 1 June 1864 (page: June)", "Britannica on the Taiping Rebellion"),
    ("Chauvet Cave", "Discovery on 18 December 1994; radiocarbon phases 37,000-33,500 and 31,000-28,000 (page: majority about 35,500, smaller group 30,000 to 31,000); check left unchanged pending LSCE on Chauvet Cave Radiocarbon Dating (Tier 5)", "Britannica on Chauvet-Pont d'Arc"),
    ("Monte Alban", "Abandoned by about 800 CE (EBSCO: the Zapotec state fragmented and the capital was abandoned by about 700 CE)", "EBSCO Research Starters on Monte Alban"),
]


def write_unresolved(date):
    log = fs.CACHE / "unresolved.md"
    head = ("# Unresolved atoms\n\nClaims that stay in a note although the page cited for them does not contain them. Each is probably correct but "
            "unconfirmed: a later tier should find the page that does (Wikipedia in Tier 4, other reference sites in Tier 5, search-summary and book "
            "sources in Tier 6) and re-attribute the check, or change the note if the page contradicts it.\n")
    text = log.read_text(encoding="utf-8") if log.exists() else head
    if f"## Tier 3 ({date})" in text:
        print("unresolved.md already has this Tier 3 section; not appended")
        return
    rows = "\n".join(f"- **{n}**: {a} [cited to {s}]" for n, a, s in U)
    log.write_text(text.rstrip("\n") + f"\n\n## Tier 3 ({date})\n{rows}\n", encoding="utf-8", newline="\n")
    print(f"unresolved.md: {len(U)} Tier 3 entries written")


if __name__ == "__main__":
    (SP / "tier3_manual.json").write_text(json.dumps(SRC, indent=1, ensure_ascii=False), encoding="utf-8")
    (SP / "tier3_extra.json").write_text(json.dumps({"sources_new": NEW, "source_updates": [GENERIC_UPDATE], "notes": NOTES, "discrepancies": DISC},
                                                    indent=1, ensure_ascii=False), encoding="utf-8")
    print(len(SRC), "source manual entries;", len(NEW), "new sources;", len(NOTES), "note patches;", len(DISC), "discrepancies;", len(U), "unresolved")
    if "--unresolved" in sys.argv:
        write_unresolved(__import__("datetime").date.today().isoformat())
