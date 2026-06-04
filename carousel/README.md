# LinkedIn carousel — "100 → 977"

A 4-slide PDF carousel sized for LinkedIn (1080×1350, 4:5 portrait).

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

1. **Milestone** — `MILESTONE / 100 citations on the first paper of my PhD.` Seed paper card. `Time to see how far the impact actually went…`
2. **Discovery** — `So I followed every citation. Then their citations. Then theirs.` Full radial tree with "977" overlaid at the centre. `977 papers turned out to be built on mine. 8 generations deep.`
3. **The tree shape** — top-down tidy tree (`From 1 paper to 977.`) with the Iris follow-up annotation
4. **The takeaway** — `Pretty cool to see the work had some real impact in the AI tutoring space :)` + tappable-link-in-first-comment affordance + minimal seed paper attribution
