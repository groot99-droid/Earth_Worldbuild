# Art-Talk

An illustrated timeline of 53 artists from around the world, from Murasaki Shikibu (born c. 973) to
Alice Guy-Blaché (died 1968), spanning painting, sculpture, architecture, design, film and
literature. Each artist has:

- **a Markdown profile** (`artists/<slug>.md`) with an overview, life, style and technique, legacy and
  sources;
- **at least five key works**, each with a picture downloaded from Wikimedia Commons, a short
  description, and a credit line;
- **entries in the RAG knowledge base** (`rag/`), ready to load into a retrieval system or an
  assistant's knowledge files.

By discipline: Painting (33) · Architecture (7) · Design (5) · Film (5) · Literature (5) · Sculpture
(1, alongside painting and architecture). Several figures work across more than one discipline, so
these totals add up to more than 53.

| Start here | What it is |
|---|---|
| [`TIMELINE.md`](TIMELINE.md) | Chronological index grouped by century, with a lifespan chart |
| [`index.html`](index.html) | Interactive timeline page: filters, search, artist panels, image lightbox |
| [`artists/`](artists) | One Markdown file per artist |
| [`rag/art-talk.jsonl`](rag/art-talk.jsonl) | Retrieval chunks, one JSON object per line |
| [`rag/art-talk.md`](rag/art-talk.md) | Every artist in a single Markdown file |

## The artists

### Painting & sculpture

**Europe:** Giotto, Jan van Eyck, Hieronymus Bosch, Leonardo da Vinci, Albrecht Dürer, Michelangelo
(also Sculpture and Architecture), Pieter Bruegel the Elder, Sofonisba Anguissola, Caravaggio,
Artemisia Gentileschi, Diego Velázquez, Rembrandt, Johannes Vermeer, Francisco Goya, J. M. W. Turner,
Claude Monet, Vincent van Gogh, Gustav Klimt, Hilma af Klint, Edvard Munch, Wassily Kandinsky.
**West & Central Asia:** Kamāl ud-Dīn Behzād.
**South Asia:** Basawan, Raja Ravi Varma, Amrita Sher-Gil.
**East Asia:** Sesshū Tōyō, Shen Zhou, Jeong Seon, Katsushika Hokusai, Utagawa Hiroshige.
**Americas:** José María Velasco, Mary Cassatt, Henry Ossawa Tanner.

### Architecture

**West & Central Asia:** Mimar Sinan.
**Europe:** Andrea Palladio, Christopher Wren, Antoni Gaudí, Charles Rennie Mackintosh (also Design).
**Americas:** Frank Lloyd Wright.

### Design

**Europe:** William Morris, Christopher Dresser, Alphonse Mucha, Charles Rennie Mackintosh (also
Architecture).
**Americas:** Louis Comfort Tiffany.

### Film

**Europe:** Georges Méliès, the Lumière Brothers, Alice Guy-Blaché, Sergei Eisenstein.
**Americas:** Buster Keaton.

### Literature

**East Asia:** Murasaki Shikibu.
**South Asia:** Amir Khusrau.
**West & Central Asia:** Rumi.
**Europe:** Jane Austen, Leo Tolstoy.

Every image had to be freely licensed on Wikimedia Commons. For that reason, figures whose work is
still in copyright (Picasso, Frida Kahlo, Diego Rivera, Georgia O'Keeffe and others among painters;
20th-century architects, designers, filmmakers and writers more generally) are not included yet.
That constraint is also why the architecture, design, film and literature selections skew toward
historical, public-domain-era figures: a building can usually be freely photographed regardless of
the architect's own copyright status, but a modern film poster or book cover typically cannot. New
figures can be added later as text-only profiles that link to images elsewhere.

## Viewing the timeline

Open `index.html` in a browser. It is a single self-contained page that loads the images from
`images/`, so it works straight from a clone.

To publish it, enable **GitHub Pages** for the repository: *Settings → Pages → Deploy from a branch*,
then choose `main` and `/ (root)`. The page will be served at
`https://<user>.github.io/Art-Talk/`. The `.nojekyll` file makes Pages serve the files as they are.

## Using the RAG files

`rag/art-talk.jsonl` contains 370 or so chunks of four types:

| `type` | One per | Contents |
|---|---|---|
| `profile` | artist | Summary, region and list of key works |
| `section` | artist section | Overview, Life, Style & Technique, or Legacy |
| `artwork` | work | Title, date, medium, location, description, image path and license |
| `century` | century | Which artists in the collection were alive in that century |

Every chunk has an `id`, `text` and metadata fields for filtering (`artist`, `slug`, `lifespan`,
`born`, `died`, `dates_approximate`, `region`, `country`, `movements`, `discipline`, `section`,
`source_file`, `url`). Each `text` begins with its context, for example "Katsushika Hokusai (1760–1849, Japan,
Ukiyo-e): Life: ...", so a chunk still makes sense when it is retrieved on its own. `born` and
`died` are sort years; when `dates_approximate` is true, use the `lifespan` string instead.

```python
import json

chunks = [json.loads(line) for line in open("rag/art-talk.jsonl", encoding="utf-8")]
works = [c for c in chunks if c["type"] == "artwork" and c["region"] == "East Asia"]
# embed c["text"] with your model of choice and store the rest as metadata
```

`rag/art-talk.md` contains the same material as a single document. Use it where you can upload
files but not a vector store, such as a Claude Project or another assistant's knowledge files.

## Adding or editing an artist

The files in `artists/` are the source of truth, and everything else is generated from them.

1. Create `artists/<slug>.md` by copying an existing profile. The front matter holds the metadata
   and the list of works:

   ```yaml
   ---
   name: Katsushika Hokusai
   short_name: Hokusai          # optional, used in the lifespan chart
   slug: hokusai                # must match the file name
   born: 1760                   # sort year (use the best estimate if unknown)
   died: 1849
   lifespan: "1760–1849"        # display text, e.g. "c. 1450–1516" or "active c. 1560–1600"
   year_label: fl. 1560         # optional label on the timeline page (defaults to born)
   region: East Asia            # Europe | West & Central Asia | South Asia | East Asia | Americas
   country: Japan
   movements: [Ukiyo-e]
   discipline: [Painting]       # Painting | Sculpture | Architecture | Design | Film | Literature
                                 # a list, so a polymath can carry more than one, e.g. [Painting, Sculpture, Architecture]
   wikipedia: https://en.wikipedia.org/wiki/Hokusai
   cover: great-wave            # work shown on the timeline card
   works:                       # at least 5
     - id: great-wave           # becomes images/<slug>/<id>.jpg
       title: The Great Wave off Kanagawa
       year: c. 1831
       medium: Woodblock print, ink and colour on paper
       location: Metropolitan Museum of Art, New York
       commons_file: "Tsunami by hokusai 19th century.jpg"   # or `wiki: <article title>` to use its lead image
       description: >-
         A towering wave ...
   ---
   ```

2. Below the front matter, write `# Name (lifespan)`, a one-line `> summary`, and the sections
   `## Overview`, `## Life`, `## Style & Technique`, `## Legacy`, `## Key Works` (leave it empty)
   and `## Sources`.
3. Download the images, then rebuild:

   ```sh
   pip install -r requirements.txt
   python scripts/fetch_images.py --only hokusai   # or no --only for everything
   python scripts/build.py
   python scripts/build.py --check                 # validate; non-zero exit on problems
   ```

`build.py` fills in the `## Key Works` section of each profile, between the `<!-- works:start -->`
and `<!-- works:end -->` markers. Edit the works in the front matter, not in that block.

For disciplines beyond painting, `medium` and `location` are reused with a looser sense: for
architecture and design, a photo of the building or object, its materials, and where it stands or is
held; for film, a still or poster, the format, and the production company in place of a museum; for
literature, a period title page, manuscript page or illustration, the form (novel, poem, play), and
the original publisher or collection in place of a museum.

### About the image downloads

`fetch_images.py` uses the Wikipedia API to look up each file. It accepts only files hosted on
Wikimedia Commons that are public domain, CC0, CC BY or CC BY-SA, and rejects non-free files. It then
downloads a standard-size thumbnail, resizes it to at most 1280 px, and records the author, license
and source page in `data/image-credits.json`. Wikimedia rate-limits image downloads. The script waits
when asked to, falls back to smaller cached sizes, and skips a file that is still blocked. Re-run it
to fill any gaps; images already downloaded are kept.

## Licensing

- **Images** are public domain or freely licensed. The author, license and Commons source of every
  image are recorded in `data/image-credits.json` and printed under each work in the artist profiles.
  Images under CC BY or CC BY-SA, mostly photographs of sculptures, buildings and exhibited works,
  must keep that attribution when reused.
- **Text** in the artist profiles was written for this project and fact-checked against the linked
  sources. It is not copied from Wikipedia.
