# Earth Chronicle: design decisions

Sources: the `ui-design` plugin (`Pipelines/plugins/ui-design`, used read-only through `route.py`, `search.py` and `contrast.py`) and its rule set in `references/quick-reference.md`. Rule ids are cited in backticks.

## Catalog results
- **Router:** `route.py` ranked *Museum/Gallery* first and *Wiki / Encyclopedia* third for this product, and flagged the choice AMBIGUOUS. I read both rows: Museum/Gallery for imagery-led browsing, Wiki/Encyclopedia for search-first navigation. The site takes both: image-forward cards plus search-first navigation.
- **Design system query:** it returned *Minimalism & Swiss Style* with Inter/Playfair, near-black on off-white. I kept the existing warm palette and Fraunces/Inter, because the catalog's own checklist is about contrast, focus, motion and touch, not about hue. `check_contrast.py` enforces those numbers instead.
- **UX rows used:** Focus States, Focus Not Obscured, Lazy Loading, Image Optimization, Autocomplete, No Results, Compact Control Semantics.

## Tokens (styles.css)
- **Colour:** semantic custom properties for light and dark, designed together (`dark-mode-pairing`, `color-semantic`). The type colours were darkened in light mode to pass 4.5:1 (era, culture, species, region, source).
- **Type and spacing:** `--serif`/`--sans`, 16px body (`readable-font-size`), 72ch line length (`line-length`), tabular figures for dates (`number-tabular`), balanced headings (`heading-line-balance`), 4/8px spacing steps (`spacing-scale`).
- **Motion:** 160ms ease-out for cards, a 220ms slide-in for the panel, and one shared easing token (`motion-consistency`). All of it is disabled under `prefers-reduced-motion` (`reduced-motion`), including the graph simulation, which runs to completion off-screen and draws once.

## What was fixed, by rule id
| Rule | Change |
|---|---|
| `focus-states`, `focus-not-obscured` | One 3px focus ring on every control; `scroll-padding-top` follows the sticky header height. |
| `skip-links`, `focus-on-route-change` | Skip link; the note title takes focus when the panel opens, and focus returns to the opening card on close. |
| `keyboard-nav`, `focusable-elements`, `tooltip-keyboard` | Tabs use arrow keys; the search box is an ARIA combobox; era bars on the ruler are buttons; the graph canvas has arrow-key stepping plus a plain list view. |
| `touch-target-size`, `web-target-size` | Chips, tabs, selects and buttons are at least 44px high on phones (verified with a DOM measurement at 375px). |
| `content-priority`, `fixed-element-offset` | On phones the sticky header holds only the tabs and search; filters sit in a "Filters (n)" disclosure with an active-count badge. |
| `deep-linking`, `state-preservation`, `back-behavior` | View, filters, search text and graph focus live in the URL hash; reload and the back button restore them. |
| `progressive-loading`, `image-dimension`, `content-jumping` | Skeleton grid on load; every image sits in a reserved 16:10 box with a shimmer; thumbnails are 480px, originals 960px. |
| `empty-states`, `error-recovery`, `timeout-feedback` | "No notes match" offers one-click ways to loosen each active filter; data or note load failures show Retry. |
| `search-accessible` | Autocomplete with recent and suggested queries, typo correction ("Did you mean"), and "search for exactly what I typed". |
| `screen-reader-summary`, `data-table` | The ruler has a text summary; the era sections below it are the table alternative. |
| `contextual-live-badge-updates`, `toast-accessibility` | The result count and toasts use polite live regions and never steal focus. |
| `no-emoji-icons`, `aria-labels` | Glyph buttons are labelled SVG icons. |

## Images
Every image goes through one loader (`js/img.js`): retry once with a cache-buster, then try the note's next image, then a typed placeholder, so a broken-image icon never shows. `scripts/check_images.py` checks the files, and `?selftest=images` decodes every URL in the browser.

## AI-made material
Higgsfield concept art (Recraft V4.1): 26 illustrations for abstract notes and three deep-time eons, plus the header banner. Each is badged "AI illustration" and credited with model, prompt and job id. Gemini text extras (In brief, journey narration, quiz) are not generated yet; the UI slots exist and read `data/ai-text.json`. The note text itself (summary, facts, context, Observer's Reading, questions, extra sections, card blurbs) is shown as an AI rewrite in the voices of the creative-writing tool, chosen per note. The rewrite is an overlay, never an edit: the vault note stays the record, every rewritten note carries an "AI rewrite" badge naming its voice, and `_Rewrite/rewrite_layer.py` rejects any rewrite that drops or adds a number, name, link or hedge. The Observer's Reading keeps its "Interpretation" frame. See `_Rewrite/README.md`.

## Known limits
- **Not tested:** real screen readers (VoiceOver, NVDA), real touch devices, and Lighthouse or Core Web Vitals numbers.
- **Advisory contrast:** hairline borders are under 3:1 against the background (WCAG 1.4.11 advisory in the plugin). Every component with a border also has a fill, a heading or text that marks it.
- **Graph:** the canvas is a visual aid. The list view and the note panel's connection lists carry the same information as text.
