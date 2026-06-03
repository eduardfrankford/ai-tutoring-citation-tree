"""Build the 6-slide LinkedIn PDF carousel for the citation tree post.

Design system (locked):
  Background:  #0B1437  deep navy
  Coral:       #FF5A4E  reserved for: root paper, headline numbers
  Light blue:  #6BA4FF  secondary accent (chart data, links)
  Text:        #E6EDF3  off-white body
  Muted:       #94A3B8  small captions

Aspect: 1080×1350 (LinkedIn carousel sweet spot, 4:5 portrait).
Output: 6 PNGs and one combined PDF.
"""
from __future__ import annotations

import json
import math
import textwrap
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
NAVY = "#0B1437"
NAVY_DEEP = "#06081A"
CORAL = "#FF5A4E"
BLUE = "#6BA4FF"
TEXT = "#E6EDF3"
MUTED = "#94A3B8"
DIM = "#475569"

W, H = 10.8, 13.5            # inches at dpi=100 → 1080×1350
DPI = 100

DATA = Path("/home/eduard-frankford/Desktop/citation_visualizer/docs/data.json")
OUT_DIR = Path("/home/eduard-frankford/Desktop/citation_visualizer/carousel")
OUT_DIR.mkdir(exist_ok=True)

plt.rcParams["font.family"] = "Inter"
plt.rcParams["font.weight"] = "regular"

# Depth palette: coral root + sequential blue ramp for d1..d8
# (single-hue, luminance-monotonic, perceptually-ordered — replaces rainbow per Tufte review)
DEPTH_COLOR = [
    CORAL,        # 0 root — coral, reserved
    "#E0F2FE",    # 1 lightest
    "#BAE6FD",    # 2
    "#7DD3FC",    # 3
    "#38BDF8",    # 4
    "#0EA5E9",    # 5
    "#0284C7",    # 6
    "#0369A1",    # 7
    "#075985",    # 8 darkest
]
# Off-white tone for emphasis bars on Slide 4
OFFWHITE = "#D8DEE9"
OFFWHITE_DIM = "#5C6478"


def _load() -> dict:
    blob = json.loads(DATA.read_text())
    flat: list[dict] = []

    def walk(n: dict) -> None:
        flat.append(n)
        for c in n.get("children") or []:
            walk(c)
    walk(blob["tree"])
    blob["_flat"] = flat
    return blob


def _slide_bg(ax) -> None:
    ax.set_facecolor(NAVY)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")


def _footer(ax, slide_n: int, total: int = 6) -> None:
    ax.text(
        0.04, 0.025, "@eduardfrankford",
        fontsize=11, color=MUTED, ha="left", va="bottom",
    )
    ax.text(
        0.96, 0.025, f"{slide_n} / {total}",
        fontsize=11, color=MUTED, ha="right", va="bottom",
        fontweight="medium",
    )


def _new_slide():
    fig, ax = plt.subplots(figsize=(W, H), dpi=DPI)
    fig.patch.set_facecolor(NAVY)
    _slide_bg(ax)
    return fig, ax


# ---------------------------------------------------------------------------
# Tree renderers used inside slides
# ---------------------------------------------------------------------------

def _radial_layout(flat: list[dict]) -> dict[str, tuple[float, float]]:
    """Concentric rings, root at centre, each subsequent depth on its own ring."""
    by_depth: dict[int, list[dict]] = {}
    for n in flat:
        by_depth.setdefault(n["depth"], []).append(n)
    pos: dict[str, tuple[float, float]] = {}
    pos[flat[0]["id"]] = (0.0, 0.0)
    for d in sorted(by_depth):
        if d == 0:
            continue
        ring = sorted(by_depth[d], key=lambda n: n["id"])
        r = d
        for i, n in enumerate(ring):
            theta = 2 * math.pi * i / len(ring)
            pos[n["id"]] = (r * math.cos(theta), r * math.sin(theta))
    return pos


def _tidy_layout(flat: list[dict], children_map: dict[str, list[str]]) -> dict[str, tuple[float, float]]:
    """Top-down tidy tree: x by leaf-count proportion, y by depth."""
    leaf_count: dict[str, int] = {}

    def compute(n: str) -> int:
        kids = children_map.get(n, [])
        if not kids:
            leaf_count[n] = 1
            return 1
        s = sum(compute(k) for k in kids)
        leaf_count[n] = s
        return s

    root_id = flat[0]["id"]
    compute(root_id)

    pos: dict[str, tuple[float, float]] = {}

    def place(n: str, xl: float, xr: float, depth: int) -> None:
        pos[n] = ((xl + xr) / 2, -depth)
        kids = children_map.get(n, [])
        if not kids:
            return
        total = sum(leaf_count[k] for k in kids)
        cur = xl
        for k in kids:
            share = (xr - xl) * (leaf_count[k] / total)
            place(k, cur, cur + share, depth + 1)
            cur += share

    place(root_id, 0.0, float(leaf_count[root_id]), 0)
    return pos


def _build_children_map(blob: dict) -> tuple[dict[str, list[str]], dict[str, dict]]:
    by_id: dict[str, dict] = {}
    children: dict[str, list[str]] = {}

    def walk(n: dict) -> None:
        by_id[n["id"]] = n
        children[n["id"]] = [c["id"] for c in (n.get("children") or [])]
        for c in (n.get("children") or []):
            walk(c)

    walk(blob["tree"])
    return children, by_id


# ===========================================================================
# Slide 1 — Hero: the radial tree with "977" overlay
# ===========================================================================

def slide1(blob: dict) -> plt.Figure:
    """The thumbnail. Tree fills the canvas, "977" overlaid bottom-left."""
    flat = blob["_flat"]
    fig, ax = _new_slide()

    # Tree axis fills 100% — the tree IS the slide.
    tree_ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    tree_ax.set_facecolor(NAVY)
    tree_ax.axis("equal")
    tree_ax.axis("off")

    pos = _radial_layout(flat)
    children_map, by_id = _build_children_map(blob)
    depth_of = {n["id"]: n["depth"] for n in flat}

    # Edges
    for nid, kids in children_map.items():
        if nid not in pos:
            continue
        x1, y1 = pos[nid]
        for kid in kids:
            if kid not in pos:
                continue
            x2, y2 = pos[kid]
            d_mid = (depth_of[nid] + depth_of[kid]) // 2
            c = DEPTH_COLOR[min(d_mid, len(DEPTH_COLOR) - 1)]
            tree_ax.plot([x1, x2], [y1, y2], color=c, alpha=0.32, linewidth=0.55, zorder=1)

    # Nodes
    for n in flat:
        x, y = pos[n["id"]]
        d = n["depth"]
        if d == 0:
            for i, sz in enumerate([6000, 3500, 1600]):
                tree_ax.scatter([x], [y], s=sz, c=CORAL, alpha=0.10 - 0.025*i, edgecolors="none", zorder=15+i)
            tree_ax.scatter([x], [y], s=1100, c=CORAL, edgecolors="white", linewidths=2, zorder=20)
        else:
            sz = max(4, 32 - d * 3)
            tree_ax.scatter([x], [y], s=sz, c=DEPTH_COLOR[d], edgecolors="none", zorder=2)

    tree_ax.set_xlim(-9, 9)
    tree_ax.set_ylim(-10.3, 9.0)

    # Bottom vignette so the overlay text reads cleanly on top of the tree.
    grad_ax = fig.add_axes([0.0, 0.0, 1.0, 0.32], zorder=30)
    grad_ax.set_facecolor("none")
    grad_ax.set_xlim(0, 1)
    grad_ax.set_ylim(0, 1)
    grad_ax.axis("off")
    cmap = plt.matplotlib.colors.LinearSegmentedColormap.from_list(
        "vignette",
        [(11/255, 20/255, 55/255, 0.0), (11/255, 20/255, 55/255, 0.96)],
    )
    grad_ax.imshow(
        np.linspace(0.0, 1.0, 256).reshape(256, 1),
        cmap=cmap, aspect="auto",
        extent=(0, 1, 0, 1), origin="upper",
    )

    # Overlay: "977" big, bottom-left.
    fig.text(
        0.06, 0.135, "977",
        fontsize=185, color=CORAL, ha="left", va="bottom",
        fontweight="bold", family="Inter Display", zorder=40,
    )
    fig.text(
        0.06, 0.09,
        "papers cite one 2024 AI-tutoring paper.",
        fontsize=22, color=TEXT, ha="left", va="bottom",
        fontweight="medium", zorder=40,
    )
    fig.text(
        0.06, 0.055,
        "Almost none of them existed when it was published.",
        fontsize=20, color=MUTED, ha="left", va="bottom",
        fontweight="medium", style="italic", zorder=40,
    )

    # Swipe prompt
    fig.text(
        0.94, 0.07, "swipe →",
        fontsize=15, color=BLUE, ha="right", va="bottom", zorder=40,
    )

    # Subtle page indicator only (no @handle on hero — keep it clean)
    fig.text(
        0.94, 0.025, "1 / 6",
        fontsize=11, color=MUTED, ha="right", va="bottom", zorder=40,
    )
    return fig


# ===========================================================================
# Slide 2 — The reframe: 96%
# ===========================================================================

def slide2(blob: dict) -> plt.Figure:
    flat = blob["_flat"]
    fig, ax = _new_slide()

    # 96% headline — moved slightly higher to clear the chart below.
    fig.text(
        0.5, 0.78, "96%",
        fontsize=280, color=CORAL, ha="center", va="center",
        fontweight="bold", family="Inter Display",
    )

    # Quote-shareable line pulled UP under the headline so it screenshots together.
    fig.text(
        0.5, 0.575,
        "A forward citation tree of a recent paper",
        fontsize=18, color=BLUE, ha="center", va="center", style="italic",
        fontweight="medium",
    )
    fig.text(
        0.5, 0.545,
        "is a real-time field-velocity sensor.",
        fontsize=18, color=BLUE, ha="center", va="center", style="italic",
        fontweight="medium",
    )

    # Subhead — clearer reframe under the quotable line
    fig.text(
        0.5, 0.470,
        "of these papers did not exist",
        fontsize=26, color=TEXT, ha="center", va="center",
        fontweight="medium",
    )
    fig.text(
        0.5, 0.434,
        "when the seed paper was published.",
        fontsize=26, color=TEXT, ha="center", va="center",
        fontweight="medium",
    )

    # Year-distribution chart with sequential blue ramp and YTD marker.
    yc = Counter(n.get("year") for n in flat if isinstance(n.get("year"), int) and 2023 <= n.get("year") <= 2026)
    years = [2024, 2025, 2026]
    counts = [yc.get(y, 0) for y in years]

    chart_ax = fig.add_axes([0.18, 0.135, 0.64, 0.22])
    chart_ax.set_facecolor(NAVY)
    bar_colors = ["#38BDF8", "#0EA5E9", "#0369A1"]  # sequential blue ramp
    bars = chart_ax.bar(
        [str(y) for y in years], counts,
        color=bar_colors, width=0.55, edgecolor="none",
    )
    for bar, c in zip(bars, counts):
        chart_ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 12, str(c),
            ha="center", va="bottom", color=TEXT, fontsize=18, fontweight="bold",
        )
    # YTD label inside the 2026 bar
    chart_ax.text(
        bars[2].get_x() + bars[2].get_width() / 2,
        bars[2].get_height() / 2, "YTD",
        ha="center", va="center", color="#E0F2FE",
        fontsize=14, fontweight="bold", alpha=0.85,
    )
    chart_ax.set_ylim(0, max(counts) * 1.25)
    chart_ax.tick_params(axis="x", colors=MUTED, labelsize=14, length=0)
    chart_ax.tick_params(axis="y", left=False, labelleft=False)
    for spine in chart_ax.spines.values():
        spine.set_visible(False)
    chart_ax.set_title(
        "Publication year of all 977 papers in the tree",
        color=MUTED, fontsize=12, pad=10, loc="left",
    )

    # Honesty footnote — closes both the arithmetic gap (17 unresolved) and the partial-year gap.
    fig.text(
        0.5, 0.073,
        "Crawled June 2026 · 17 papers without a resolved publication year · 2026 bar is year-to-date",
        fontsize=10, color=MUTED, ha="center", va="bottom", style="italic",
    )

    # Footer
    fig.text(0.5, 0.025, "1 paper → 977 in 24 months",
             fontsize=11, color=MUTED, ha="center", va="bottom")
    fig.text(0.96, 0.025, "2 / 6", fontsize=11, color=MUTED, ha="right", va="bottom")
    return fig


# ===========================================================================
# Slide 3 — The tree shape (hierarchical, top-down)
# ===========================================================================

def slide3(blob: dict) -> plt.Figure:
    flat = blob["_flat"]
    children_map, by_id = _build_children_map(blob)
    pos = _tidy_layout(flat, children_map)

    fig, ax = _new_slide()

    # Header
    fig.text(
        0.5, 0.92, "From 1 paper to 977.",
        fontsize=42, color=TEXT, ha="center", va="center", fontweight="bold",
    )
    # Forward-pointing swipe-driver subtitle (was: "Eight generations of citing work.")
    fig.text(
        0.5, 0.872, "But most of the mass lives in one specific layer  →",
        fontsize=21, color=MUTED, ha="center", va="center",
    )

    tree_ax = fig.add_axes([0.04, 0.10, 0.92, 0.74])
    tree_ax.set_facecolor(NAVY)
    tree_ax.axis("off")

    # Edges — bumped alpha 0.32 → 0.50 and width 0.42 → 0.65 so they survive
    # LinkedIn's PDF compression at mobile preview sizes.
    for nid, kids in children_map.items():
        if nid not in pos:
            continue
        x1, y1 = pos[nid]
        for kid in kids:
            if kid not in pos:
                continue
            x2, y2 = pos[kid]
            d = by_id[kid]["depth"]
            c = DEPTH_COLOR[min(d, len(DEPTH_COLOR) - 1)]
            tree_ax.plot(
                [x1, x2], [y1, y2],
                color=c, alpha=0.50, linewidth=0.65, zorder=1,
            )

    # Nodes
    for n in flat:
        x, y = pos[n["id"]]
        d = n["depth"]
        if d == 0:
            tree_ax.scatter([x], [y], s=520, c=CORAL, edgecolors="white", linewidths=1.2, zorder=20)
        else:
            sz = max(2, 36 - d * 4)
            tree_ax.scatter([x], [y], s=sz, c=DEPTH_COLOR[d], edgecolors="none", zorder=2)

    # Inline "root" label by the coral dot (Tufte fix: d0/coral ambiguity).
    rx, ry = pos[flat[0]["id"]]
    tree_ax.text(
        rx - 8, ry, "root  →",
        fontsize=11, color=CORAL, ha="right", va="center", fontweight="bold",
    )

    # Find the biggest depth-1 subtree (the Iris paper from Bassner et al.)
    # for an annotation arrow on Slide 3 — gives the eye a specific landing point
    # and creates a narrative thread to Slide 5 where Bassner appears at #2.
    d1_subtrees: dict[str, int] = {}

    def count_subtree(nid: str) -> int:
        s = 1
        for k in children_map.get(nid, []):
            s += count_subtree(k)
        return s
    for kid in children_map.get(flat[0]["id"], []):
        d1_subtrees[kid] = count_subtree(kid)
    if d1_subtrees:
        biggest_id = max(d1_subtrees, key=d1_subtrees.get)
        biggest_size = d1_subtrees[biggest_id]
        bx, by = pos[biggest_id]
        # Point at the top of the subtree (d1 row) where there's empty sky to the
        # left, so the annotation text doesn't collide with the dense d2-d4 mass.
        tree_ax.annotate(
            f"Iris (Bassner et al.):\n{biggest_size}-paper sub-tree",
            xy=(bx + 0.5, by - 0.15),
            xytext=(bx - 120, by + 0.30),
            fontsize=12, color=CORAL, fontweight="medium",
            arrowprops=dict(arrowstyle="->", color=CORAL, lw=1.2,
                            connectionstyle="arc3,rad=-0.2"),
            ha="left", va="center",
        )

    # Depth labels on the right edge — start at d1 (root is labelled inline).
    x_right = max(p[0] for p in pos.values()) + 8
    for d in sorted({n["depth"] for n in flat}):
        if d == 0:
            continue
        tree_ax.text(
            x_right, -d, f"d{d}",
            fontsize=12, color=DEPTH_COLOR[d] if d < len(DEPTH_COLOR) else MUTED,
            ha="left", va="center", fontweight="bold",
        )

    tree_ax.set_xlim(-100, x_right + 30)
    tree_ax.set_ylim(-(8 + 0.5), 0.6)

    _footer(ax, 3)
    return fig


# ===========================================================================
# Slide 4 — The staircase (per-depth counts)
# ===========================================================================

def slide4(blob: dict) -> plt.Figure:
    flat = blob["_flat"]
    per_depth = Counter(n["depth"] for n in flat)
    leaves = Counter(n["depth"] for n in flat if n.get("isLeaf"))

    fig, ax = _new_slide()

    fig.text(
        0.5, 0.93, "The wavefront",
        fontsize=46, color=TEXT, ha="center", va="center", fontweight="bold",
    )
    fig.text(
        0.5, 0.88,
        "Papers per generation. Depth 3 is where the wave breaks.",
        fontsize=18, color=MUTED, ha="center", va="center",
    )

    chart_ax = fig.add_axes([0.10, 0.20, 0.84, 0.60])
    chart_ax.set_facecolor(NAVY)

    depths = sorted(per_depth)
    totals = [per_depth[d] for d in depths]
    leaf_counts = [leaves[d] for d in depths]
    non_leaf_counts = [t - l for t, l in zip(totals, leaf_counts)]

    crest_d = max(depths, key=lambda d: per_depth[d])
    # Off-white bars (neutral) with coral on the crest only (d3) — fixes coral
    # discipline drift. Bars now encode position-on-x; color = emphasis only.
    bar_colors = [CORAL if d == crest_d else OFFWHITE for d in depths]
    leaf_colors = [
        ("#FF8A82" if d == crest_d else OFFWHITE_DIM)
        for d in depths
    ]

    chart_ax.bar(
        depths, non_leaf_counts, color=bar_colors, width=0.72, edgecolor="none",
        label="Branching papers", zorder=2,
    )
    chart_ax.bar(
        depths, leaf_counts, bottom=non_leaf_counts,
        color=leaf_colors, width=0.72, edgecolor="none",
        label="Leaves (no citers yet)", zorder=2,
    )

    # Total labels above each bar — crest in coral, others in off-white
    for d, t in zip(depths, totals):
        chart_ax.text(
            d, t + 9, str(t),
            ha="center", va="bottom",
            color=(CORAL if d == crest_d else TEXT),
            fontsize=22, fontweight="bold",
        )

    chart_ax.annotate(
        "crest of the wave",
        xy=(crest_d, per_depth[crest_d]),
        xytext=(crest_d + 1.2, per_depth[crest_d] + 30),
        fontsize=15, color=TEXT, fontweight="medium",
        arrowprops=dict(arrowstyle="->", color=TEXT, lw=1.2),
        ha="left", va="center",
    )

    chart_ax.set_xticks(depths)
    chart_ax.set_xticklabels([f"d{d}" for d in depths])
    chart_ax.tick_params(axis="x", colors=MUTED, labelsize=14, length=0, pad=10)
    chart_ax.tick_params(axis="y", left=False, labelleft=False)
    # x-axis label removed — d0..d8 ticks make the axis self-explanatory.
    chart_ax.set_ylim(0, max(totals) * 1.18)
    for spine in chart_ax.spines.values():
        spine.set_visible(False)

    leg = chart_ax.legend(
        loc="upper right", facecolor=NAVY_DEEP, edgecolor=DIM,
        labelcolor=TEXT, fontsize=12, framealpha=0.9,
    )

    # "So what" forward-looking takeaway.
    fig.text(
        0.5, 0.155,
        "Those depth-3 papers are spawning the next wave right now.",
        fontsize=15, color=CORAL, ha="center", va="center",
        fontweight="medium", style="italic",
    )

    # Bottom summary with honest leaves disclosure.
    fig.text(
        0.5, 0.115,
        "977 papers · 711 leaves · 1062 citation edges",
        fontsize=13, color=MUTED, ha="center", va="center",
    )
    fig.text(
        0.5, 0.087,
        "Leaves = no descendants in our crawl (yet).",
        fontsize=11, color=MUTED, ha="center", va="center", style="italic",
    )

    _footer(ax, 4)
    return fig


# ===========================================================================
# Slide 5 — Top 5 most-cited descendants
# ===========================================================================

def slide5(blob: dict) -> plt.Figure:
    flat = blob["_flat"]
    descendants = [n for n in flat if n["depth"] > 0]
    top5 = sorted(descendants, key=lambda n: -(n.get("citedByCount") or 0))[:5]

    total_cites_all = sum(n.get("citedByCount") or 0 for n in descendants)
    top5_cites = sum(n.get("citedByCount") or 0 for n in top5)
    concentration_pct = round(100 * top5_cites / total_cites_all) if total_cites_all else 0

    max_cc = max(n.get("citedByCount") or 0 for n in top5) or 1

    fig, ax = _new_slide()
    fig.text(
        0.5, 0.93, "Where the citations concentrated.",
        fontsize=38, color=TEXT, ha="center", va="center", fontweight="bold",
    )
    # Insight, not leaderboard
    fig.text(
        0.5, 0.882,
        f"5 papers (of 977) account for {concentration_pct}% of the tree's citation mass.",
        fontsize=17, color=BLUE, ha="center", va="center", fontweight="medium",
    )

    card_top = 0.795
    card_h = 0.115
    gap = 0.013

    for i, n in enumerate(top5):
        y_top = card_top - i * (card_h + gap)
        y_bot = y_top - card_h
        y_mid = (y_top + y_bot) / 2

        # Card background
        card = mpatches.FancyBboxPatch(
            (0.04, y_bot), 0.92, card_h,
            boxstyle="round,pad=0.005,rounding_size=0.012",
            facecolor=NAVY_DEEP, edgecolor=DIM, linewidth=0.7,
            transform=fig.transFigure, zorder=1,
        )
        fig.patches.append(card)

        # Horizontal sparkline ratio bar in the card background — encodes
        # the relative magnitude pre-attentively (Tufte fix: digits alone
        # don't communicate the 3× spread between #1 and #5).
        cc = n.get("citedByCount", 0) or 0
        ratio = cc / max_cc
        sparkline = mpatches.Rectangle(
            (0.04, y_bot), 0.92 * ratio, card_h,
            facecolor=CORAL, edgecolor="none", alpha=0.10,
            transform=fig.transFigure, zorder=1,
        )
        fig.patches.append(sparkline)

        # Rank
        fig.text(
            0.085, y_mid + 0.012, f"#{i+1}",
            fontsize=14, color=MUTED, ha="left", va="center",
            fontweight="medium",
        )
        fig.text(
            0.085, y_mid - 0.025,
            f"{cc}",
            fontsize=38, color=CORAL, ha="left", va="center",
            fontweight="bold", family="Inter Display",
        )
        fig.text(
            0.205, y_mid - 0.034,
            "citations",
            fontsize=11, color=MUTED, ha="left", va="center",
        )

        # Title + meta
        title = n["title"]
        wrapped = textwrap.wrap(title, width=54)[:2]
        if len(wrapped) >= 2 and len(title) > 54 * 2:
            wrapped[1] = wrapped[1].rstrip() + "…"
        for j, line in enumerate(wrapped):
            fig.text(
                0.30, y_mid + 0.022 - j * 0.022, line,
                fontsize=15, color=TEXT, ha="left", va="center", fontweight="medium",
            )

        # Author · year only (depth chip removed — all top-5 are d1, displaying
        # that to a cold reader undercuts "eight generations deep" from slide 1).
        auth = (n.get("authors") or [""])[0]
        last = auth.split()[-1] if auth else "?"
        year = n.get("year", "?")
        et_al = " et al." if len(n.get("authors") or []) > 1 else ""
        meta = f"{last}{et_al} · {year}"
        fig.text(
            0.30, y_mid - 0.034, meta,
            fontsize=12, color=MUTED, ha="left", va="center",
        )

    _footer(ax, 5)
    return fig


# ===========================================================================
# Slide 6 — Call to action
# ===========================================================================

def slide6(blob: dict) -> plt.Figure:
    fig, ax = _new_slide()

    # Punchline callback above the headline.
    fig.text(
        0.5, 0.882,
        "977 papers. 96% published after the seed.",
        fontsize=15, color=MUTED, ha="center", va="center",
        fontweight="medium",
    )

    # Headline
    fig.text(
        0.5, 0.82, "Explore every paper",
        fontsize=44, color=TEXT, ha="center", va="center", fontweight="bold",
    )
    fig.text(
        0.5, 0.775, "in the tree.",
        fontsize=44, color=TEXT, ha="center", va="center", fontweight="bold",
    )

    # "Link in first comment" affordance — PDF URLs are not tappable on LinkedIn.
    fig.text(
        0.5, 0.69, "↓  Tappable link in the first comment",
        fontsize=16, color=CORAL, ha="center", va="center", fontweight="bold",
    )

    # Off-white pill with coral arrow — color discipline preserved.
    btn = mpatches.FancyBboxPatch(
        (0.08, 0.595), 0.84, 0.075,
        boxstyle="round,pad=0.004,rounding_size=0.022",
        facecolor=OFFWHITE, edgecolor="none",
        transform=fig.transFigure, zorder=2,
    )
    fig.patches.append(btn)
    fig.text(
        0.49, 0.6325,
        "eduardfrankford.github.io/ai-tutoring-citation-tree",
        fontsize=18, color=NAVY_DEEP, ha="center", va="center",
        fontweight="bold", family="Inter",
    )
    # Coral arrow at the end of the pill
    fig.text(
        0.88, 0.6325, "→",
        fontsize=24, color=CORAL, ha="center", va="center",
        fontweight="bold",
    )

    # Feature bullets — only the two real user benefits; tech stack moved below.
    bullets = [
        "→  Zoom, pan, click any paper for details",
        "→  Search across all 977 titles and authors",
    ]
    for i, b in enumerate(bullets):
        fig.text(
            0.5, 0.50 - i * 0.045, b,
            fontsize=15, color=TEXT, ha="center", va="center", fontweight="medium",
        )

    # Divider
    ax.plot([0.18, 0.82], [0.36, 0.36], color=DIM, lw=0.8, transform=fig.transFigure, zorder=2)

    # Seed paper details
    fig.text(
        0.5, 0.328, "SEED PAPER",
        fontsize=11, color=MUTED, ha="center", va="center",
        fontweight="bold",
    )
    fig.text(
        0.5, 0.290,
        "“AI-Tutoring in Software Engineering Education”",
        fontsize=17, color=TEXT, ha="center", va="center", fontweight="medium",
        style="italic",
    )
    fig.text(
        0.5, 0.258,
        "Frankford, Sauerwein, Bassner, Krusche, Breu",
        fontsize=14, color=MUTED, ha="center", va="center",
    )
    fig.text(
        0.5, 0.232,
        "ICSE-SEET 2024 · doi.org/10.1145/3639474.3640061",
        fontsize=14, color=MUTED, ha="center", va="center",
    )

    # Source line consolidated: stack credit + repo on one row.
    fig.text(
        0.5, 0.17,
        "Source: github.com/eduardfrankford/ai-tutoring-citation-tree",
        fontsize=14, color=BLUE, ha="center", va="center",
    )
    fig.text(
        0.5, 0.142,
        "Built on OpenAlex API · D3 v7 · GitHub Pages",
        fontsize=12, color=MUTED, ha="center", va="center",
    )

    _footer(ax, 6)
    return fig


# ===========================================================================
# Build everything
# ===========================================================================

def main() -> None:
    blob = _load()

    slides = [
        ("slide1_hero", slide1),
        ("slide2_reframe", slide2),
        ("slide3_tree", slide3),
        ("slide4_wavefront", slide4),
        ("slide5_top5", slide5),
        ("slide6_cta", slide6),
    ]

    pdf_path = OUT_DIR / "linkedin_carousel.pdf"
    with PdfPages(pdf_path) as pdf:
        for name, fn in slides:
            print(f"Rendering {name}…")
            fig = fn(blob)
            png_path = OUT_DIR / f"{name}.png"
            fig.savefig(png_path, dpi=DPI, facecolor=NAVY, bbox_inches=None, pad_inches=0)
            pdf.savefig(fig, facecolor=NAVY)
            plt.close(fig)
            print(f"  → {png_path.relative_to(OUT_DIR.parent)} ({png_path.stat().st_size // 1024} KB)")

    print(f"\nPDF: {pdf_path.relative_to(OUT_DIR.parent)} ({pdf_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
