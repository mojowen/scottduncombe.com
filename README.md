# scottduncombe.com — prototype v0

A local, no-build prototype of the recommended redesign direction:

**"Civic letterhead" chassis · field-guide spec cards · stat posters.**

Design ideation doc: `~/Projects/scottduncombe-redesign-ideation.md`
Content source: live WP site + `~/Projects/Scott-Theme` (mojowen/Scott-Theme).

## View it

    cd ~/Projects/scottduncombe-prototype
    python3 -m http.server 4173
    open http://localhost:4173

(or just open `index.html` — everything is relative and works from `file://` too, except the Google Fonts CDN)

## Pages

| File | What it demonstrates |
|---|---|
| `index.html` | Featured work (3 spec cards), stat posters, press strip |
| `work.html` | All 23 projects grouped into 3 habitats ("eras") |
| `project/pizza-to-the-polls.html` | Flagship detail page: specimen header, story, measurements, gallery, field notes, prev/next |
| `project/power-the-polls.html` | Second detail page |
| `project/moodmonitor.html` | Third detail page (drafted content from `Scott-Theme/projects/moodmonitor.md`, never published to WP) |
| `press.html` | All 16 verified clippings from `stuff/press.json`, grouped by era |
| `about.html` | **Draft copy** — dashed underline (`.todo` class) marks every fact needing Scott's confirmation |
| `writing.html` | "Dispatches" blog slot stub — feed-first framing |
| `404.html` | Pizza slice with googly eyes (pupils follow the cursor; disabled under reduced-motion) |

## Design system

- **Tokens** at the top of `assets/css/site.css`: `--plum #580035`, `--cream #fdfafc`, `--tomato #c8102e`, `--stamp #2b4a9b` — plum/cream carried over from the WP theme; tomato used *only* for stat posters.
- **Type**: Bitter (400/600/700/900 + italics) for display/serif; system sans body; `ui-monospace` for specimen metadata.
- **Whimsy mechanics included**: monogram "signature" animation on load (click the monogram to replay), hover photo-grow (kept from the WP theme), tilted cards/posters that straighten on hover, googly-eye 404, "powered by coffee & free pizza" footer.
- **Accessibility**: all motion disabled under `prefers-reduced-motion`; `:focus-visible` styles; alt text on gallery images.

## Images

`assets/img/thumb-*.jpg|png` + `ptp-gallery-*.png` scraped from the live site (one-time). `me.jpg` and `favicon.svg` copied from `Scott-Theme/stuff/`. `moodmonitor-tile.svg` is generated (original CDN is dead; archived logo was rate-limited).

## Not a real site yet — known gaps

1. **20 stub detail pages** — only 3 are typeset. In the real build each is a markdown file.
2. **About copy is a draft** — current-day framing (agent orchestration, current PTP role, contact address, marital trivia) needs Scott.
3. **Social URLs are placeholders** (GitHub verified; LinkedIn/Bluesky guessed).
4. **RSS/JSON feeds** don't exist yet — the writing page promises them.
5. **GA**: old `UA-15235777-1` footer snippet is *not* carried over; wire GA4 only if wanted.

## Migration path (when ready)

This prototype maps 1:1 to an **11ty** build:

- `work.html` era sections → `content/projects/*.md` with front matter (`era`, `firstObserved`, `with`, `diet`, `status`, `tags`, `sticker`)
- `press.html` → `press.json` rendered through a template (data unchanged, keeps `collect_press.py` workflow)
- `about.html`/`writing.html` → markdown pages + posts collection with RSS/JSON feed templates
- shared rail/nav → a single layout include
- deploy: GitHub Pages via Actions; then DNS cutover + 301s (`/project/<slug>/` shape is preserved), and the shared host keeps only whatever else it still serves (email?)

See the ideation doc's "Stack & migration notes" for the open questions to answer before cutting over.