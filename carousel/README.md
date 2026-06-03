# LinkedIn carousel — "977 papers cite one 2024 paper"

A 6-slide PDF carousel sized for LinkedIn (1080×1350, 4:5 portrait).

## Contents

| File | What it is |
|---|---|
| `linkedin_carousel.pdf` | The thing to upload as a Document post |
| `slide1_hero.png` … `slide6_cta.png` | Individual slide PNGs (for previews, screenshots, fallback) |
| `LINKEDIN_POST.md` | Three drafts of the post copy + a pre-publish checklist |

## How it was built

`build_carousel.py` reads `../docs/data.json` (the full 977-paper graph) and renders each slide with matplotlib (Inter font, navy/coral design system). Re-run to regenerate:

```bash
backend/.venv/bin/python /tmp/build_carousel.py
```

(Script lives at `/tmp/build_carousel.py` while iterating; move into the repo when stable.)

## Design system

- Background: `#0B1437` deep navy
- Coral `#FF5A4E` — reserved for: the seed/root paper, the headline 977, the headline 96%, citation counts on Slide 5, the d3 crest emphasis on Slide 4, and the link arrow on Slide 6
- Light blue `#6BA4FF` — secondary accent (quotable lines, blue link text)
- Off-white `#E6EDF3` body, muted `#94A3B8` captions
- Depth palette = sequential single-hue blue ramp (`#E0F2FE` → `#075985`); coral reserved for the root
- Typography: Inter / Inter Display

## Story arc

1. **Hero** — radial tree of 977 papers with "977" overlay (the thumbnail; works at 200×250)
2. **The reframe** — "96% of these papers didn't exist when I published the seed paper" + year-distribution chart
3. **The tree shape** — top-down tidy tree showing 8 depth bands and the biggest sub-tree (Bassner et al.'s Iris)
4. **The wavefront** — per-depth bar chart, depth 3 highlighted as the "crest" of citation velocity
5. **Where the citations concentrated** — top 5 cited descendants with concentration stat (27% of citation mass)
6. **CTA** — link to the interactive site (via first comment, since PDF URLs aren't tappable on LinkedIn)
