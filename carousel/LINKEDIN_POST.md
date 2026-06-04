# LinkedIn carousel — post copy

Three drafts at different lengths, all in your voice (based on how you actually told me the story).

## Pre-publish checklist

- [ ] Upload `linkedin_carousel.pdf` as a **Document post** (not as individual images)
- [ ] **Document title** (LinkedIn asks for this on upload — screen readers will read it as the post's accessible name in the feed):
  > **From 100 citations to a 977-paper tree — the forward citation graph of my first PhD paper on AI tutoring**
- [ ] Paste the post text in the body (do NOT put the URL in the body — LinkedIn deprioritizes posts with external links)
- [ ] **First comment immediately after publishing**: paste `https://eduardfrankford.github.io/ai-tutoring-citation-tree/`. This is the standard LinkedIn-algorithm move so the link is tappable without the post being penalized.
- [ ] Add 3–5 hashtags at the end: `#AIinEducation #PhD #SoftwareEngineering #AITutoring #AcademicResearch`
- [ ] Reply to comments in the first hour — the algorithm watches early engagement

## Accessibility

The PDF has descriptive metadata embedded (Title, Subject, Keywords, Author) — verifiable with `pdfinfo linkedin_carousel.pdf`. Screen readers (NVDA, VoiceOver, JAWS) announce the Title when the document opens.

If LinkedIn offers per-slide alt text on upload, use these descriptions:

- **Slide 1 (Milestone):** *A celebration slide on a dark navy background. A large coral "MILESTONE" eyebrow at top, the number "100" in giant coral type filling the upper half, then the words "citations on the first paper of my PhD." Below, a citation card for the seed paper: "AI-Tutoring in Software Engineering Education" by Frankford, Sauerwein, Bassner, Krusche, and Breu, ICSE-SEET 2024. Closing prompt: "Time to see how far the impact actually went…" with a "swipe" arrow.*

- **Slide 2 (Discovery):** *A dense radial citation tree centred on a glowing coral dot — the seed paper — surrounded by eight concentric rings of light-blue dots, each ring representing one generation of citing papers, all the way out to 977 papers total. The number "977" is overlaid at the centre in large coral text. Header: "So I followed every citation. Then their citations. Then theirs." Caption below: "977 papers turned out to be built on mine. 8 generations deep."*

- **Slide 3 (Tree shape):** *A top-down hierarchical tree visualization. The seed paper sits at the top centre as a coral dot labelled "root", with light-blue branches fanning down through 8 generational rows labelled d1 through d8 along the right edge. Hundreds of small light-blue dots form the descendant papers, with the densest concentration in rows d2 to d4. A coral annotation calls out the Iris paper: "Iris — follow-up paper with TUM (413 papers branch off it)." Title: "From 1 paper to 977." Subtitle: "Each layer = one generation away from my paper."*

- **Slide 4 (Takeaway):** *A clean closing slide on dark navy. A coral "THE TAKEAWAY" eyebrow at top, then three lines of large bold text: "Pretty cool to see the work / had some real impact / in the AI tutoring space :)" with the third line in coral. Below: "Want to see the full tree? Every paper is in there, zoomable and searchable." A coral "↓ Tappable link in the first comment" prompt and an off-white pill with the URL "eduardfrankford.github.io/ai-tutoring-citation-tree" and a coral arrow.*

> **Honest caveat:** matplotlib produces *untagged* PDFs (no semantic structure, no per-element alt text). The Title/Subject metadata above gives screen reader users a content summary at the document level, which is the most important fix. Per-slide alt text and tagged-PDF structure would require a different toolchain (ReportLab, or post-processing with pikepdf) — happy to do that if you need WCAG 2.1 AA conformance.

---

## Draft A — short and personal (recommended)

```
My first PhD paper just hit 100 citations on Google Scholar 🎉

I was curious where the impact actually went, so I followed those 100 papers
to see who cites them. Then who cites those. And so on, until I hit the leaves.

977 papers turned out to be built on mine — 8 generations deep.

Really cool to see the work had some real impact in the AI tutoring space :)

Tappable link to the interactive tree in the first comment 👇

#AIinEducation #PhD #SoftwareEngineering
```

## Draft B — medium, with the build story

```
My first PhD paper just hit 100 citations on Google Scholar 🎉

For fun I wanted to see the actual ripple effect — not just who cites my paper,
but who cites THOSE papers, and so on, all the way down.

So I built a little tool to crawl the citation graph and visualize it.

Turns out 977 papers are built on mine — 8 generations deep.

The first generation (the 100 direct citers) is just the start. Generation 3
is actually the biggest with 244 papers. So my paper's "reach" is mostly
indirect — people building on people building on the work, not directly on it.

Really cool to see the research had some real impact in the AI tutoring space :)

Interactive tree where you can zoom into any of the 977 papers — link in the
first comment 👇

#AIinEducation #PhD #SoftwareEngineering #DataVisualization
```

## Draft C — with the methodology

```
My first PhD paper just hit 100 citations on Google Scholar 🎉

I wanted to see the actual downstream impact, so I built a small tool that
follows citations recursively — papers cite my paper, then I follow each of
those to see who cites them, then again, all the way to the leaves.

The result: 977 papers, 8 generations deep, with depth 3 being the biggest
generation (244 papers).

What surprised me: 96% of those 977 papers were written AFTER mine, in
just 2 years. AI in education is moving really fast.

Really cool to see the work had some real impact in the AI tutoring scene :)

Interactive zoomable tree (search, click any paper for full details) — link
in the first comment 👇

Built with Google Scholar (for the depth-1 ground truth), the OpenAlex API
(for the recursive crawl), and D3 for the viz. Open source.

#AIinEducation #PhD #SoftwareEngineering #DataVisualization #AcademicResearch
```

---

## What changed from the previous version

The earlier drafts I gave you leaned on strategist framing — "field-velocity
sensor", "screenshot-worthy stats", calling 977 a "vanity number to reframe".
That's not how you actually talk. These drafts use your own phrasing:
"first PhD paper", "really cool to see", "AI tutoring space", the smile emoji
at the end. Pick whichever length feels right — A for cold reach, B for
your network, C for the data/methods crowd.
