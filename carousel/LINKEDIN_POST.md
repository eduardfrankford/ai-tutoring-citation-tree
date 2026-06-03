# LinkedIn carousel — post copy

Three drafts at different lengths. Pick one.

## Use this checklist before posting

- [ ] Upload `linkedin_carousel.pdf` as a Document post (not as individual images)
- [ ] Post text in the body (do NOT put the URL in the body — LinkedIn deprioritizes posts with external links)
- [ ] **First comment immediately after publishing**: paste the URL `https://eduardfrankford.github.io/ai-tutoring-citation-tree/`. This is the standard LinkedIn-algorithm move.
- [ ] Add 3–5 hashtags at the end of the post body: `#AIinEducation #SoftwareEngineering #CitationAnalysis #AcademicResearch #DataVisualization`
- [ ] Reply to comments in the first hour — the algorithm watches early engagement

---

## Draft A — short and punchy (recommended for cold reach)

```
96% of the papers that cite my 2024 ICSE-SEET paper didn't exist when I published it.

I crawled the full forward citation tree, 8 generations deep — 977 papers, 1062 edges. None of which I'd have found through the paper's own "cited by" list.

A forward citation tree of a recent paper is basically a real-time field-velocity sensor.

Tappable link in the first comment 👇

#AIinEducation #SoftwareEngineering #CitationAnalysis
```

## Draft B — story angle (best for academic + EdTech network)

```
In 2024 my ICSE-SEET paper on AI tutoring had zero citations.

Today: 100 direct citers on Google Scholar.

So I asked the obvious follow-up: who cites the citers? Then I built a tool to crawl the full forward citation tree, all the way down to the leaves.

The result: 977 papers, 8 generations deep, 711 of which are leaves (papers that have no citers themselves yet).

The most surprising stat: 96% of those 977 papers were published AFTER I published mine. The tree is almost entirely 2025 and 2026 work. A forward citation tree of a recent paper isn't really a "citation graph" — it's a real-time field-velocity sensor.

Interactive viewer (zoom, search, click any paper for full details) — link in the first comment 👇

Built with the OpenAlex API, D3 v7, and GitHub Pages. Open source.

#AIinEducation #SoftwareEngineering #CitationAnalysis #AcademicResearch
```

## Draft C — technical angle (best for engineers / data folks)

```
What does the full forward citation tree of a single paper look like, all the way to the leaves?

I crawled mine: 977 papers, 1062 edges, max depth 8 generations, 711 leaves. 27% of the entire tree's citation mass concentrates in just 5 papers at depth 1.

But the headline finding: 96% of these 977 papers were published AFTER the seed paper. A forward citation tree of a recent paper is a real-time field-velocity sensor.

Stack:
→ Google Scholar gave the ground-truth 100 depth-1 citers
→ OpenAlex (free, well-indexed citation graph) handled the recursive BFS — finished in 27 seconds
→ D3 v7 for the visualization, GitHub Pages for hosting

Interactive zoomable tree — link in the first comment 👇

Open source on GitHub — comment with a DOI and I'll run yours.

#DataVisualization #CitationAnalysis #OpenScience #AIinEducation
```

---

## Why these specific moves

- **96% headline first** — the adversarial review flagged this as the only screenshot-bait stat in the deck. Don't bury it.
- **Link in first comment** — PDF carousels don't surface external URLs as clickable. LinkedIn also suppresses posts with external links in the body. Putting the URL in the first comment is the standard workaround.
- **No "humblebrag" framing** — "in 2024 my paper had zero citations → today X" works because it's about the field's velocity, not the author's vanity. Avoid "my impact" / "look how far my paper traveled".
- **"comment with a DOI and I'll run yours"** (Draft C) — turns the post into a service. Drives saves and replies, which the algorithm reads as quality engagement.
- **Hashtags at end, 3–5 max** — too many tanks reach; too few misses topical feeds.
