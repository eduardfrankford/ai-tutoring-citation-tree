import { Component, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CitationGraphComponent } from './citation-graph.component';
import {
  CitationService,
  Edge,
  PaperNode,
  StreamEvent,
} from './citation.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, CitationGraphComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent {
  query =
    'https://scholar.google.com/scholar?oi=bibs&hl=de&cites=17763308536187984722&as_sdt=5';
  maxDepth = 2;
  maxPerNode = 10;
  maxTotalNodes = 300;

  status: 'idle' | 'loading' | 'done' | 'error' = 'idle';
  statusMessage = '';
  rootId: string | null = null;
  nodes: PaperNode[] = [];
  edges: Edge[] = [];
  selected: PaperNode | null = null;
  truncated = false;
  rateLimited = false;

  private currentStreamClose: (() => void) | null = null;

  @ViewChild(CitationGraphComponent) graph?: CitationGraphComponent;

  constructor(private api: CitationService) {}

  get nodeCount(): number { return this.nodes.length; }
  get edgeCount(): number { return this.edges.length; }

  start(): void {
    if (!this.query.trim()) return;
    this.cancel();

    this.nodes = [];
    this.edges = [];
    this.rootId = null;
    this.selected = null;
    this.truncated = false;
    this.rateLimited = false;
    this.status = 'loading';
    this.statusMessage = 'Resolving paper…';

    const stream = this.api.streamTree({
      query: this.query.trim(),
      maxDepth: this.maxDepth,
      maxPerNode: this.maxPerNode,
      maxTotalNodes: this.maxTotalNodes,
    });
    this.currentStreamClose = stream.close;

    stream.events$.subscribe({
      next: (ev) => this.handleEvent(ev),
      error: (err) => {
        this.status = 'error';
        this.statusMessage = err?.message || 'Stream failed';
      },
      complete: () => {
        if (this.status === 'loading') {
          this.status = 'done';
          this.statusMessage = `Loaded ${this.nodes.length} papers, ${this.edges.length} citation edges.`;
        }
      },
    });
  }

  cancel(): void {
    if (this.currentStreamClose) {
      this.currentStreamClose();
      this.currentStreamClose = null;
    }
  }

  resetView(): void {
    this.graph?.resetView();
  }

  selectNode(n: PaperNode): void {
    this.selected = n;
  }

  externalLink(n: PaperNode): string | null {
    const ids = n.externalIds || {};
    if (ids['DOI']) return `https://doi.org/${ids['DOI']}`;
    if (ids['ArXiv']) return `https://arxiv.org/abs/${ids['ArXiv']}`;
    if (n.id) return `https://www.semanticscholar.org/paper/${n.id}`;
    return null;
  }

  private handleEvent(ev: StreamEvent): void {
    switch (ev.type) {
      case 'resolved':
        if (ev.paper) {
          this.statusMessage = `Resolved: ${ev.paper.title}`;
        }
        break;
      case 'root':
        if (ev.node) {
          this.rootId = ev.node.id;
          this.nodes = [...this.nodes, ev.node];
          this.statusMessage = `Crawling citations of: ${ev.node.title}`;
        }
        break;
      case 'node':
        if (ev.node) this.nodes = [...this.nodes, ev.node];
        if (ev.edge) this.edges = [...this.edges, ev.edge];
        this.statusMessage = `Discovered ${this.nodes.length} papers…`;
        break;
      case 'edge':
        if (ev.edge) this.edges = [...this.edges, ev.edge];
        break;
      case 'done':
        this.truncated = !!ev.truncated;
        this.rateLimited = !!ev.rateLimited;
        this.status = 'done';
        let msg = `Done — ${this.nodes.length} papers, ${this.edges.length} citation edges.`;
        if (ev.truncated) msg += ' Hit node cap (raise “max total nodes” to see more).';
        if (ev.rateLimited) msg += ' Some requests were rate-limited; results may be partial.';
        this.statusMessage = msg;
        break;
      case 'error':
        this.status = 'error';
        this.statusMessage = ev.message || 'Unknown error';
        break;
    }
  }
}
