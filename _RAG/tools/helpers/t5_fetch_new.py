"""Fetch the specific pages that Tier 5 checks need instead of the generic World History Encyclopedia / UNESCO
World Heritage Centre notes (each of which was fetched from a single unrelated page). Slug = slugify(title) so
fetch_source.pick_slug finds the cache later. Run in the background: python -u t5_fetch_new.py > log.

Usage: python t5_fetch_new.py [--only substring]
"""
import subprocess
import sys

import _paths
import fetch_source as fs

WHE = "https://www.worldhistory.org/"
UN = "https://whc.unesco.org/en/list/"

NEW = [
    ("World History Encyclopedia on Akhenaten", WHE + "Akhenaten/"),
    ("World History Encyclopedia on Alexander the Great", WHE + "Alexander_the_Great/"),
    ("World History Encyclopedia on Augustus", WHE + "Augustus/"),
    ("World History Encyclopedia on Genghis Khan", WHE + "Genghis_Khan/"),
    ("World History Encyclopedia on Hammurabi", WHE + "Hammurabi/"),
    ("World History Encyclopedia on Mahatma Gandhi", WHE + "Mahatma_Gandhi/"),
    ("World History Encyclopedia on Pachacuti", WHE + "Pachacuti/"),
    ("World History Encyclopedia on Zheng He", WHE + "Zheng_He/"),
    ("World History Encyclopedia on Athens", WHE + "athens/"),
    ("World History Encyclopedia on Ancient Greece", WHE + "greece/"),
    ("World History Encyclopedia on the Aztec Empire", WHE + "Aztec_Civilization/"),
    ("World History Encyclopedia on the Iroquois Confederacy", WHE + "Iroquois_Confederacy/"),
    ("World History Encyclopedia on the Inca Empire", WHE + "Inca_Civilization/"),
    ("World History Encyclopedia on the Khmer Empire", WHE + "Khmer_Empire/"),
    ("World History Encyclopedia on the Mali Empire", WHE + "Mali_Empire/"),
    ("World History Encyclopedia on the Indus Valley Civilization", WHE + "Indus_Valley_Civilization/"),
    ("World History Encyclopedia on Cuneiform", WHE + "Cuneiform/"),
    ("World History Encyclopedia on Writing", WHE + "writing/"),
    ("World History Encyclopedia on the Phoenician Alphabet", WHE + "Phoenician_Alphabet/"),
    ("World History Encyclopedia on the Sea Peoples", WHE + "Sea_Peoples/"),
    ("World History Encyclopedia on the Late Bronze Age Collapse", WHE + "Bronze_Age_Collapse/"),
    ("World History Encyclopedia on the Mongol Empire", WHE + "Mongol_Empire/"),
    ("World History Encyclopedia on Uruk", WHE + "uruk/"),
    ("World History Encyclopedia on the Abbasid Caliphate", WHE + "Abbasid_Caliphate/"),
    ("World History Encyclopedia on the Peloponnesian War", WHE + "Peloponnesian_War/"),
    ("World History Encyclopedia on the Punic Wars", WHE + "Punic_Wars/"),
    ("World History Encyclopedia on Muhammad", WHE + "Muhammad/"),
    ("World History Encyclopedia on Athenian Democracy", WHE + "Athenian_Democracy/"),
    ("World History Encyclopedia on the Ghana Empire", WHE + "Ghana_Empire/"),
    ("World History Encyclopedia on Aksum", WHE + "Kingdom_of_Axum/"),
    ("UNESCO on Angkor", UN + "668/"),
    ("UNESCO on Caral-Supe", UN + "1269/"),
    ("UNESCO on the Site of Carthage", UN + "37/"),
    ("UNESCO on Chaco Culture", UN + "353/"),
    ("UNESCO on Great Zimbabwe", UN + "364/"),
    ("UNESCO on Gobekli Tepe", UN + "1572/"),
    ("UNESCO on Machu Picchu", UN + "274/"),
    ("UNESCO on Mohenjo-daro", UN + "138/"),
    ("UNESCO on Timbuktu", UN + "119/"),
    ("UNESCO on Catalhoyuk", UN + "1405/"),
    ("UNESCO on Cahokia Mounds", UN + "198/"),
    ("UNESCO on Chinchorro Settlement and Artificial Mummification", UN + "1634/"),
    ("UNESCO on Poverty Point", UN + "1435/"),
    ("UNESCO on the Taj Mahal", UN + "252/"),
    ("UNESCO on Borobudur", UN + "592/"),
    ("UNESCO on the Jomon Prehistoric Sites", UN + "1361/"),
]

NOBEL = "https://www.nobelprize.org/prizes/"
WP = "https://en.wikipedia.org/wiki/"
NEW2 = [
    ("Wikipedia on Mahatma Gandhi", WP + "Mahatma_Gandhi"),
    ("Wikipedia on Zheng He", WP + "Zheng_He"),
    ("Wikipedia on the Hijrah", WP + "Hijrah"),
    ("Wikipedia on the Iroquois", WP + "Iroquois"),
    ("Wikipedia on the Phoenician Alphabet", WP + "Phoenician_alphabet"),
    ("Wikipedia on the Urban Revolution", WP + "Urban_revolution"),
    ("NobelPrize.org on the 1945 Nobel Prize in Physiology or Medicine", NOBEL + "medicine/1945/summary/"),
    ("NobelPrize.org on the 1903 Nobel Prize in Physics", NOBEL + "physics/1903/summary/"),
    ("NobelPrize.org on the 1911 Nobel Prize in Chemistry", NOBEL + "chemistry/1911/summary/"),
]
NOAA = "https://gml.noaa.gov/webdata/ccgg/trends/co2/"
NEW3 = [
    ("Wikipedia on World Population", WP + "World_population"),
    ("Wikipedia on Cleisthenes", WP + "Cleisthenes"),
    ("Wikipedia on the Parthenon", WP + "Parthenon"),
    ("Wikipedia on the Code of Hammurabi", WP + "Code_of_Hammurabi"),
    ("Wikipedia on Ibn Battuta", WP + "Ibn_Battuta"),
    ("Wikipedia on Augustus", WP + "Augustus"),
    ("Wikipedia on Rachel Carson", WP + "Rachel_Carson"),
    ("Wikipedia on Great Zimbabwe", WP + "Great_Zimbabwe"),
    ("Wikipedia on the Taj Mahal", WP + "Taj_Mahal"),
    ("Wikipedia on Borobudur", WP + "Borobudur"),
    ("Wikipedia on the Battle of Kadesh", WP + "Battle_of_Kadesh"),
    ("Wikipedia on the Classic Maya Collapse", WP + "Classic_Maya_collapse"),
    ("Wikipedia on the Olmec Colossal Heads", WP + "Olmec_colossal_heads"),
    ("Wikipedia on the Sokoto Caliphate", WP + "Sokoto_Caliphate"),
    ("Wikipedia on the Timbuktu Manuscripts", WP + "Timbuktu_Manuscripts"),
    ("Wikipedia on Homo habilis", WP + "Homo_habilis"),
    ("Wikipedia on Homo erectus", WP + "Homo_erectus"),
    ("Wikipedia on Sahelanthropus", WP + "Sahelanthropus"),
    ("Wikipedia on the Jomon Period", WP + "J%C5%8Dmon_period"),
    ("Wikipedia on Sannai-Maruyama", WP + "Sannai-Maruyama_site"),
    ("Wikipedia on the Marajoara Culture", WP + "Marajoara_culture"),
    ("Wikipedia on the Chinchorro Mummies", WP + "Chinchorro_mummies"),
    ("Wikipedia on Potosi", WP + "Potos%C3%AD"),
    ("NOAA GML Global Annual Mean CO2 Data", NOAA + "co2_annmean_gl.txt"),
    ("NOAA GML Global Annual Growth Rate of CO2", NOAA + "co2_gr_gl.txt"),
    ("NOAA GML Mauna Loa Annual Mean CO2 Data", NOAA + "co2_annmean_mlo.txt"),
]
NEW4 = [("UNESCO on Al-Hijr Archaeological Site", UN + "1293/")]
if "--set4" in sys.argv:
    NEW = NEW4
if "--set2" in sys.argv:
    NEW = NEW2
if "--set3" in sys.argv:
    NEW = NEW3

only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
py = sys.executable
for title, url in NEW:
    if only and only.lower() not in title.lower():
        continue
    slug = fs.slugify(title)
    print(f"##### {title}  ->  {slug}", flush=True)
    r = subprocess.run([py, "-u", str(_paths.TOOLS / "fetch_source.py"), "fetch", "--url", url, "--slug", slug],
                       capture_output=True, text=True, encoding="utf-8")
    out = (r.stdout or "") + (r.stderr or "")
    print("\n".join(l for l in out.splitlines() if l.strip().startswith(("OK", "FAILED", "route", "trace", "text:", "non-200"))), flush=True)
print("ALLDONE", flush=True)
