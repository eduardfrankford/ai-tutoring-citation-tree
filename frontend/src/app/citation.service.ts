import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, Subject } from 'rxjs';

export interface PaperNode {
  id: string;
  title: string;
  year: number | null;
  authors: string[];
  citationCount: number | null;
  externalIds: Record<string, string | null>;
  venue: string | null;
  depth: number;
  parent: string | null;
}

export interface Edge {
  source: string;
  target: string;
}

export interface TreeResult {
  root: string;
  nodes: PaperNode[];
  edges: Edge[];
  truncated: boolean;
  rateLimited: boolean;
  stats: { totalNodes: number; totalEdges: number; maxDepth: number; maxPerNode: number };
}

export interface StreamEvent {
  type: 'resolved' | 'root' | 'node' | 'edge' | 'done' | 'error';
  paper?: PaperNode;
  node?: PaperNode;
  edge?: Edge;
  stats?: TreeResult['stats'];
  truncated?: boolean;
  rateLimited?: boolean;
  message?: string;
}

export interface StreamOptions {
  query: string;
  maxDepth: number;
  maxPerNode: number;
  maxTotalNodes: number;
}

@Injectable({ providedIn: 'root' })
export class CitationService {
  constructor(private http: HttpClient) {}

  resolve(query: string): Observable<PaperNode> {
    return this.http.post<PaperNode>('/api/resolve', { query });
  }

  fetchTree(opts: StreamOptions): Observable<TreeResult> {
    return this.http.post<TreeResult>('/api/tree', {
      query: opts.query,
      max_depth: opts.maxDepth,
      max_per_node: opts.maxPerNode,
      max_total_nodes: opts.maxTotalNodes,
    });
  }

  /**
   * Streams citation tree events via Server-Sent Events. The returned object
   * exposes an observable of events and a `close()` to abort the stream.
   */
  streamTree(opts: StreamOptions): { events$: Observable<StreamEvent>; close: () => void } {
    const url = new URL('/api/tree/stream', window.location.origin);
    url.searchParams.set('query', opts.query);
    url.searchParams.set('max_depth', String(opts.maxDepth));
    url.searchParams.set('max_per_node', String(opts.maxPerNode));
    url.searchParams.set('max_total_nodes', String(opts.maxTotalNodes));

    const subject = new Subject<StreamEvent>();
    const es = new EventSource(url.toString());

    es.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data) as StreamEvent;
        subject.next(data);
        if (data.type === 'done') {
          subject.complete();
          es.close();
        }
      } catch (err) {
        subject.next({ type: 'error', message: 'Failed to parse server event' });
      }
    };

    es.onerror = () => {
      // EventSource auto-reconnects; for our use case we want to surface the error
      // and stop. If the server has already sent 'done' the stream closes cleanly.
      if (es.readyState === EventSource.CLOSED) {
        subject.complete();
      } else {
        subject.next({ type: 'error', message: 'Stream connection lost' });
        es.close();
        subject.complete();
      }
    };

    return {
      events$: subject.asObservable(),
      close: () => {
        es.close();
        subject.complete();
      },
    };
  }
}
