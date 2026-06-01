/* Citation tree — zoomable D3 visualisation. */
(async function () {
  const DEPTH_COLOR = [
    '#fde047', '#fbbf24', '#f97316', '#ef4444',
    '#a855f7', '#3b82f6', '#06b6d4', '#10b981', '#84cc16',
  ];

  const svg = d3.select('#canvas');
  const detailEl = document.getElementById('detail');
  const detailBody = document.getElementById('detailBody');
  const searchInput = document.getElementById('search');
  const resultCount = document.getElementById('resultCount');

  const data = await fetch('data.json').then((r) => r.json());
  const stats = data.stats;
  const root = d3.hierarchy(data.tree);

  // ── Stats badges ───────────────────────────────────────────────────────
  const statsHost = document.getElementById('stats');
  const renderStats = () => {
    const items = [
      { label: 'papers', value: stats.nodes.toLocaleString() },
      { label: 'edges', value: stats.edges.toLocaleString() },
      { label: 'max depth', value: stats.max_depth },
      { label: 'leaves', value: stats.leaves.toLocaleString() },
    ];
    statsHost.innerHTML = items.map((s) => `
      <div class="stat">
        <span class="stat-value">${s.value}</span>
        <span class="stat-label">${s.label}</span>
      </div>
    `).join('');
  };
  renderStats();

  // ── Legend ────────────────────────────────────────────────────────────
  const legend = document.getElementById('legend');
  const renderLegend = () => {
    const perDepth = stats.per_depth || {};
    const rows = Object.keys(perDepth)
      .map(Number)
      .sort((a, b) => a - b)
      .map((d) => `
        <div class="legend-row">
          <span class="legend-dot" style="background:${DEPTH_COLOR[d] || '#94a3b8'}"></span>
          <span>depth ${d}</span>
          <span style="color:var(--text-dim); margin-left:auto">${perDepth[d]} papers</span>
        </div>
      `).join('');
    legend.innerHTML = `<h3>Depth</h3>${rows}`;
  };
  renderLegend();

  // ── Tree layout — vertical tidy tree (root top, leaves bottom) ────────
  // Persist collapse state across renders.
  let nodeCounter = 0;
  root.each((d) => { d._id = nodeCounter++; });

  // Collapse all beyond depth 2 by default to keep the initial view legible.
  const collapseBeyond = (node, depth) => {
    if (node.depth >= depth && node.children) {
      node._children = node.children;
      node.children = null;
    }
    (node.children || node._children || []).forEach((c) =>
      collapseBeyond(c, depth)
    );
  };
  collapseBeyond(root, 1);

  const gMain = svg.append('g');
  const gLinks = gMain.append('g').attr('class', 'links');
  const gNodes = gMain.append('g').attr('class', 'nodes');

  const treeLayout = d3.tree();

  const NODE_X_SPACING = 16;
  const NODE_Y_SPACING = 110;
  const NODE_RADIUS = (d) => (d.depth === 0 ? 12 : Math.max(3, 9 - d.depth));

  let selectedNode = null;
  let searchHits = new Set();

  // ── Zoom / pan ────────────────────────────────────────────────────────
  const zoom = d3.zoom()
    .scaleExtent([0.05, 8])
    .on('zoom', (event) => {
      gMain.attr('transform', event.transform);
    });
  svg.call(zoom);

  document.getElementById('zoomIn').addEventListener('click', () => {
    svg.transition().duration(220).call(zoom.scaleBy, 1.4);
  });
  document.getElementById('zoomOut').addEventListener('click', () => {
    svg.transition().duration(220).call(zoom.scaleBy, 1 / 1.4);
  });
  document.getElementById('resetView').addEventListener('click', () => fitToView());

  function fitToView() {
    const visible = root.descendants().filter((d) => isVisible(d));
    if (!visible.length) return;
    const xs = visible.map((d) => d.x);
    const ys = visible.map((d) => d.y);
    const xMin = d3.min(xs), xMax = d3.max(xs);
    const yMin = d3.min(ys), yMax = d3.max(ys);
    const w = svg.node().clientWidth;
    const h = svg.node().clientHeight;
    const pad = 40;
    const scaleX = (w - pad * 2) / Math.max(1, xMax - xMin);
    const scaleY = (h - pad * 2) / Math.max(1, yMax - yMin);
    const scale = Math.min(scaleX, scaleY, 1.4);
    const tx = w / 2 - ((xMin + xMax) / 2) * scale;
    const ty = h / 2 - ((yMin + yMax) / 2) * scale;
    svg.transition().duration(600).call(
      zoom.transform,
      d3.zoomIdentity.translate(tx, ty).scale(scale)
    );
  }

  function isVisible(node) {
    let cur = node;
    while (cur.parent) {
      if (!cur.parent.children) return false;
      cur = cur.parent;
    }
    return true;
  }

  // ── Render pipeline ────────────────────────────────────────────────────
  function update() {
    // Compute counts for layout sizing.
    const visibleLeaves = root.copy().count().value || 1;
    const widthForLeaves = visibleLeaves * NODE_X_SPACING;
    treeLayout.nodeSize([NODE_X_SPACING, NODE_Y_SPACING]);
    treeLayout(root);

    const visible = root.descendants().filter((d) => isVisible(d));
    const links = root.links().filter((l) => isVisible(l.target) && isVisible(l.source));

    const linkSel = gLinks.selectAll('path.link')
      .data(links, (d) => d.target._id);
    linkSel.exit().remove();
    linkSel.enter().append('path')
      .attr('class', 'link')
      .merge(linkSel)
      .attr('d', d3.linkVertical().x((d) => d.x).y((d) => d.y));

    const nodeSel = gNodes.selectAll('g.node')
      .data(visible, (d) => d._id);
    nodeSel.exit().remove();
    const nodeEnter = nodeSel.enter().append('g')
      .attr('class', (d) => 'node' + (d.depth === 0 ? ' root' : ''))
      .on('click', (event, d) => { event.stopPropagation(); selectNode(d); })
      .on('dblclick', (event, d) => { event.stopPropagation(); toggleCollapse(d); update(); });

    nodeEnter.append('circle');
    nodeEnter.append('title');
    nodeEnter.append('text');

    const merged = nodeEnter.merge(nodeSel);
    merged
      .attr('transform', (d) => `translate(${d.x},${d.y})`)
      .classed('collapsed', (d) => !!d._children)
      .classed('selected', (d) => selectedNode && selectedNode._id === d._id)
      .classed('search-hit', (d) => searchHits.has(d._id))
      .classed('dimmed', (d) =>
        searchHits.size > 0 && !searchHits.has(d._id) && !isAncestorOfHit(d)
      );

    merged.select('circle')
      .attr('r', NODE_RADIUS)
      .attr('fill', (d) => DEPTH_COLOR[d.depth] || '#94a3b8');

    merged.select('title').text((d) => {
      const dat = d.data;
      const a = (dat.authors || []).slice(0, 3).join(', ');
      const more = (dat.authors || []).length > 3 ? '…' : '';
      return [
        dat.title,
        a + more,
        dat.year ? `Year: ${dat.year}` : null,
        dat.citedByCount != null ? `Own citations: ${dat.citedByCount}` : null,
        `Depth: ${dat.depth}`,
      ].filter(Boolean).join('\n');
    });

    merged.select('text')
      .attr('text-anchor', 'middle')
      .attr('y', (d) => -NODE_RADIUS(d) - 3)
      .text((d) => {
        if (d.depth === 0) return '';
        if (d.depth === 1 || (selectedNode && selectedNode === d)) {
          const a = (d.data.authors && d.data.authors[0]) || '';
          const last = a.split(' ').pop() || '';
          return `${last}${d.data.year ? ' ' + d.data.year : ''}`;
        }
        return '';
      });
  }

  function isAncestorOfHit(node) {
    if (searchHits.has(node._id)) return true;
    return node.descendants().some((d) => searchHits.has(d._id));
  }

  function toggleCollapse(d) {
    if (d.children) {
      d._children = d.children;
      d.children = null;
    } else if (d._children) {
      d.children = d._children;
      d._children = null;
    }
  }

  // ── Selection / detail panel ───────────────────────────────────────────
  function selectNode(d) {
    selectedNode = d;
    update();
    renderDetail(d);
    detailEl.setAttribute('aria-hidden', 'false');
  }
  function renderDetail(d) {
    const dat = d.data;
    const depthColor = DEPTH_COLOR[dat.depth] || '#94a3b8';
    const oaLink = dat.openalexId
      ? `<a href="${dat.openalexId.startsWith('http') ? dat.openalexId : 'https://openalex.org/' + dat.openalexId}" target="_blank" rel="noopener">View on OpenAlex ↗</a>`
      : '';
    const scholarLink = dat.scholarN != null
      ? `<a href="https://scholar.google.com/scholar?cites=17763308536187984722" target="_blank" rel="noopener">Position #${dat.scholarN} in Scholar's depth-1 list ↗</a>`
      : '';
    const authors = (dat.authors || []).join(', ') || '(unknown)';
    const childCount = (d.children || d._children || []).length;
    const directCiterText = childCount === 0
      ? 'No further citing papers found in this crawl (leaf).'
      : `${childCount} direct citing paper${childCount === 1 ? '' : 's'} in this tree.`;

    detailBody.innerHTML = `
      <h2>${escapeHtml(dat.title)}</h2>
      <div class="detail-row">
        <span class="detail-label">Authors</span>
        <span class="detail-value">${escapeHtml(authors)}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">Year</span>
        <span class="detail-value">${dat.year || '—'}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">Depth</span>
        <span class="detail-value">
          <span class="depth-badge" style="background:${depthColor}">depth ${dat.depth}</span>
        </span>
      </div>
      <div class="detail-row">
        <span class="detail-label">Own citations</span>
        <span class="detail-value">${dat.citedByCount != null ? dat.citedByCount : '—'}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">In this tree</span>
        <span class="detail-value">${directCiterText}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">Source</span>
        <span class="detail-value mono">${escapeHtml(dat.source || '—')}</span>
      </div>
      <div class="detail-links">
        ${oaLink}
        ${scholarLink}
      </div>
    `;
  }

  document.getElementById('detailClose').addEventListener('click', () => {
    detailEl.setAttribute('aria-hidden', 'true');
    selectedNode = null;
    update();
  });

  // ── Expand / collapse all ──────────────────────────────────────────────
  document.getElementById('expandAll').addEventListener('click', () => {
    root.each((d) => {
      if (d._children) {
        d.children = d._children;
        d._children = null;
      }
    });
    update();
    fitToView();
  });
  document.getElementById('collapseAll').addEventListener('click', () => {
    root.each((d) => {
      if (d.depth >= 1 && d.children) {
        d._children = d.children;
        d.children = null;
      }
    });
    update();
    fitToView();
  });

  // ── Search ────────────────────────────────────────────────────────────
  let searchTimer = null;
  searchInput.addEventListener('input', (e) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => runSearch(e.target.value), 120);
  });
  function runSearch(q) {
    searchHits = new Set();
    q = (q || '').trim().toLowerCase();
    if (!q) {
      resultCount.textContent = '';
      update();
      return;
    }
    let count = 0;
    root.each((d) => {
      const dat = d.data;
      const hay = [
        dat.title,
        ...(dat.authors || []),
        String(dat.year || ''),
      ].join(' ').toLowerCase();
      if (hay.includes(q)) {
        searchHits.add(d._id);
        count++;
        // Auto-expand ancestors so the hit is visible.
        let cur = d.parent;
        while (cur) {
          if (cur._children) {
            cur.children = cur._children;
            cur._children = null;
          }
          cur = cur.parent;
        }
      }
    });
    resultCount.textContent = `${count} match${count === 1 ? '' : 'es'}`;
    update();
    if (count > 0) fitToView();
  }

  // ── Utility ────────────────────────────────────────────────────────────
  function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
  }

  // ── Initial render + fit ───────────────────────────────────────────────
  function resizeCanvas() {
    const wrap = document.querySelector('.canvas-wrap');
    const rect = wrap.getBoundingClientRect();
    svg.attr('width', rect.width).attr('height', rect.height);
  }
  resizeCanvas();
  window.addEventListener('resize', () => { resizeCanvas(); fitToView(); });
  update();
  fitToView();
})();
