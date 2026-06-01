import {
  AfterViewInit,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import * as d3 from 'd3';
import { Edge, PaperNode } from './citation.service';

interface SimNode extends d3.SimulationNodeDatum {
  id: string;
  data: PaperNode;
}

interface SimLink extends d3.SimulationLinkDatum<SimNode> {
  source: string | SimNode;
  target: string | SimNode;
}

@Component({
  selector: 'app-citation-graph',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="graph-wrap" #wrap>
      <svg #svg></svg>
      <div class="empty" *ngIf="!nodes?.length">
        Enter a paper above and press “Visualize” to see its citation tree.
      </div>
    </div>
  `,
  styles: [`
    .graph-wrap { position: relative; width: 100%; height: 100%; background: #0e1116; }
    svg { width: 100%; height: 100%; display: block; cursor: grab; }
    svg:active { cursor: grabbing; }
    .empty {
      position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
      color: #9aa4b2; font-style: italic; pointer-events: none;
    }
    :host ::ng-deep .node-circle { cursor: pointer; }
    :host ::ng-deep .node-label {
      font-family: ui-sans-serif, system-ui, sans-serif;
      font-size: 11px;
      fill: #e6edf3;
      pointer-events: none;
    }
    :host ::ng-deep .link {
      stroke: #4a5568;
      stroke-opacity: 0.55;
      fill: none;
    }
    :host ::ng-deep .link.cross { stroke-dasharray: 3 3; stroke-opacity: 0.3; }
    :host ::ng-deep .node-circle.root { stroke: #fbbf24; stroke-width: 2.5px; }
    :host ::ng-deep .node-circle.hover { stroke: #f0f6fc; stroke-width: 2.5px; }
  `],
})
export class CitationGraphComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input() nodes: PaperNode[] = [];
  @Input() edges: Edge[] = [];
  @Input() rootId: string | null = null;
  @Output() nodeSelected = new EventEmitter<PaperNode>();

  @ViewChild('svg', { static: true }) svgRef!: ElementRef<SVGSVGElement>;
  @ViewChild('wrap', { static: true }) wrapRef!: ElementRef<HTMLDivElement>;

  private simulation: d3.Simulation<SimNode, SimLink> | null = null;
  private svgSel: d3.Selection<SVGSVGElement, unknown, null, undefined> | null = null;
  private container: d3.Selection<SVGGElement, unknown, null, undefined> | null = null;
  private linkGroup: d3.Selection<SVGGElement, unknown, null, undefined> | null = null;
  private nodeGroup: d3.Selection<SVGGElement, unknown, null, undefined> | null = null;
  private zoomBehavior: d3.ZoomBehavior<SVGSVGElement, unknown> | null = null;
  private resizeObs?: ResizeObserver;

  private simNodes: SimNode[] = [];
  private simLinks: SimLink[] = [];

  ngAfterViewInit(): void {
    this.initSvg();
    this.update();
    this.resizeObs = new ResizeObserver(() => this.handleResize());
    this.resizeObs.observe(this.wrapRef.nativeElement);
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (this.svgSel) this.update();
  }

  ngOnDestroy(): void {
    this.simulation?.stop();
    this.resizeObs?.disconnect();
  }

  private initSvg(): void {
    const svg = d3.select(this.svgRef.nativeElement);
    this.svgSel = svg;
    svg.selectAll('*').remove();

    const defs = svg.append('defs');
    defs.append('marker')
      .attr('id', 'arrow')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 16)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#4a5568');

    this.container = svg.append('g');
    this.linkGroup = this.container.append('g').attr('class', 'links');
    this.nodeGroup = this.container.append('g').attr('class', 'nodes');

    this.zoomBehavior = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        this.container!.attr('transform', event.transform.toString());
      });
    svg.call(this.zoomBehavior);
  }

  private handleResize(): void {
    if (!this.simulation) return;
    const { width, height } = this.dimensions();
    this.simulation.force('center', d3.forceCenter(width / 2, height / 2));
    this.simulation.alpha(0.3).restart();
  }

  private dimensions(): { width: number; height: number } {
    const rect = this.wrapRef.nativeElement.getBoundingClientRect();
    return { width: rect.width || 800, height: rect.height || 600 };
  }

  private update(): void {
    if (!this.svgSel || !this.linkGroup || !this.nodeGroup) return;

    const nodeIds = new Set(this.nodes.map((n) => n.id));
    const existing = new Map(this.simNodes.map((n) => [n.id, n]));
    this.simNodes = this.nodes.map((p) => {
      const prev = existing.get(p.id);
      return prev ? { ...prev, data: p } : { id: p.id, data: p };
    });
    this.simLinks = this.edges
      .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
      .map((e) => ({ source: e.source, target: e.target }));

    const { width, height } = this.dimensions();

    // Color by depth.
    const depthMax = Math.max(1, ...this.simNodes.map((n) => n.data.depth));
    const color = d3.scaleSequential(d3.interpolateCool).domain([0, depthMax]);

    // Radius by citation count (log scale).
    const radius = (d: SimNode) => {
      const c = Math.max(1, d.data.citationCount || 1);
      return 4 + Math.min(18, Math.log10(c) * 4);
    };

    // Build "tree-like" parent edges (depth-1 connections) separate from cross edges.
    const parentEdges = new Set(
      this.simNodes
        .filter((n) => n.data.parent)
        .map((n) => `${n.data.parent}->${n.id}`),
    );

    if (!this.simulation) {
      this.simulation = d3
        .forceSimulation<SimNode, SimLink>(this.simNodes)
        .force(
          'link',
          d3
            .forceLink<SimNode, SimLink>(this.simLinks)
            .id((d) => d.id)
            .distance((l) => {
              const src = (l.source as SimNode).data;
              const tgt = (l.target as SimNode).data;
              return 60 + Math.abs((tgt?.depth || 0) - (src?.depth || 0)) * 20;
            })
            .strength(0.6),
        )
        .force('charge', d3.forceManyBody().strength(-220))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force(
          'collide',
          d3.forceCollide<SimNode>().radius((d) => radius(d) + 6),
        )
        .force(
          'radial',
          d3.forceRadial<SimNode>(
            (d) => 90 + d.data.depth * 130,
            width / 2,
            height / 2,
          ).strength(0.18),
        );
    } else {
      this.simulation.nodes(this.simNodes);
      (this.simulation.force('link') as d3.ForceLink<SimNode, SimLink>).links(this.simLinks);
      this.simulation.alpha(0.6).restart();
    }

    const link = this.linkGroup
      .selectAll<SVGLineElement, SimLink>('line.link')
      .data(this.simLinks, (d: any) => `${d.source.id || d.source}->${d.target.id || d.target}`);

    link.exit().remove();
    const linkEnter = link
      .enter()
      .append('line')
      .attr('class', (d) => {
        const key = `${(d.source as any).id ?? d.source}->${(d.target as any).id ?? d.target}`;
        return parentEdges.has(key) ? 'link parent' : 'link cross';
      })
      .attr('marker-end', 'url(#arrow)');

    const linkMerged = linkEnter.merge(link);

    const node = this.nodeGroup
      .selectAll<SVGGElement, SimNode>('g.node')
      .data(this.simNodes, (d: SimNode) => d.id);

    node.exit().remove();

    const nodeEnter = node
      .enter()
      .append('g')
      .attr('class', 'node')
      .call(
        d3
          .drag<SVGGElement, SimNode>()
          .on('start', (event, d) => {
            if (!event.active) this.simulation!.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on('drag', (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on('end', (event, d) => {
            if (!event.active) this.simulation!.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          }),
      )
      .on('click', (event, d) => {
        event.stopPropagation();
        this.nodeSelected.emit(d.data);
      })
      .on('mouseenter', (event, _d) => {
        d3.select(event.currentTarget as Element)
          .select('circle')
          .classed('hover', true);
      })
      .on('mouseleave', (event, _d) => {
        d3.select(event.currentTarget as Element)
          .select('circle')
          .classed('hover', false);
      });

    nodeEnter
      .append('circle')
      .attr('class', (d) => `node-circle ${d.id === this.rootId ? 'root' : ''}`)
      .attr('r', (d) => radius(d))
      .attr('fill', (d) => color(d.data.depth) as string)
      .attr('stroke', '#0b0f14')
      .attr('stroke-width', 1);

    nodeEnter.append('title').text((d) => this.tooltip(d.data));

    nodeEnter
      .append('text')
      .attr('class', 'node-label')
      .attr('x', (d) => radius(d) + 4)
      .attr('y', 4)
      .text((d) => this.truncate(d.data.title, 60));

    const nodeMerged = nodeEnter.merge(node);
    nodeMerged
      .select('circle')
      .attr('r', (d: any) => radius(d))
      .attr('fill', (d: any) => color(d.data.depth) as string)
      .classed('root', (d: any) => d.id === this.rootId);
    nodeMerged.select('text').text((d: any) => this.truncate(d.data.title, 60));
    nodeMerged.select('title').text((d: any) => this.tooltip(d.data));

    this.simulation.on('tick', () => {
      linkMerged
        .attr('x1', (d) => (d.source as SimNode).x ?? 0)
        .attr('y1', (d) => (d.source as SimNode).y ?? 0)
        .attr('x2', (d) => (d.target as SimNode).x ?? 0)
        .attr('y2', (d) => (d.target as SimNode).y ?? 0);
      nodeMerged.attr('transform', (d) => `translate(${d.x ?? 0},${d.y ?? 0})`);
    });
  }

  private tooltip(n: PaperNode): string {
    const authors = (n.authors || []).slice(0, 4).join(', ');
    const more = (n.authors?.length || 0) > 4 ? ` +${(n.authors?.length || 0) - 4} more` : '';
    return [
      n.title,
      authors ? `${authors}${more}` : null,
      n.year ? `Year: ${n.year}` : null,
      n.venue ? `Venue: ${n.venue}` : null,
      n.citationCount != null ? `Citations: ${n.citationCount}` : null,
      `Depth: ${n.depth}`,
    ]
      .filter(Boolean)
      .join('\n');
  }

  private truncate(s: string, n: number): string {
    if (!s) return '';
    return s.length > n ? s.slice(0, n - 1) + '…' : s;
  }

  resetView(): void {
    if (this.svgSel && this.zoomBehavior) {
      this.svgSel.transition().duration(400).call(this.zoomBehavior.transform, d3.zoomIdentity);
    }
  }
}
