# Citation Visualizer

Visualize the recursive citation tree of a paper. You give it a root paper
(URL, DOI, ArXiv ID, title, or even a Google Scholar `?cites=` URL) and it
crawls *papers that cite it* using **Claude (Anthropic API) with the
`web_search` tool**, then renders the result as an interactive force-directed
graph.

> ⚠️  **Cost & latency.** Each "find citations of this paper" call is one
> Claude turn that runs 2–4 web searches. Roughly **5–20 seconds and
> $0.05–$0.20 per paper** at the Opus 4.8 default. A depth-2 crawl with
> max-per-node = 5 = ~25 calls ≈ 5–10 min and a few dollars. Switch to
> `claude-sonnet-4-6` (env var `ANTHROPIC_MODEL`) for ~5× lower cost.

## Architecture

```
┌──────────────┐    /api/tree/stream (SSE)    ┌─────────────────────┐
│  Angular 17  │ ─────────────────────────▶  │   FastAPI backend   │
│  + D3 v7     │ ◀──── node events ─────────  │  Anthropic API +    │
└──────────────┘                              │  web_search tool    │
                                              └─────────────────────┘
```

- **backend/** – FastAPI + the official `anthropic` SDK. Resolves the input
  with one Claude+web-search call, then BFS-crawls citations one Claude call
  per node. Structured outputs (`output_config.format`) guarantee a JSON
  shape; prompt caching keeps the system prompt cheap across calls.
- **frontend/** – Angular 17 standalone app. D3 force-directed graph with
  zoom/pan/drag, depth-coloured nodes, and a side panel for paper details.

## Run it (Docker, recommended)

```bash
# REQUIRED: an Anthropic API key.  https://console.anthropic.com/settings/keys
export ANTHROPIC_API_KEY=sk-ant-...

# Optional: use Sonnet 4.6 instead of Opus 4.8 (~5× cheaper).
# export ANTHROPIC_MODEL=claude-sonnet-4-6

# Optional: cap web searches per Claude turn (each ~$0.01).
# export ANTHROPIC_MAX_WEB_SEARCHES=4

docker compose up --build -d
```

Then open <http://localhost:8090>. The frontend container (nginx) serves the
Angular bundle and reverse-proxies `/api` to the backend container.

- Frontend: <http://localhost:8090>
- Backend API (also exposed for direct use): <http://localhost:8765/api/health>

Stop with `docker compose down`. Logs: `docker compose logs -f`.

## Run it (without Docker)

### 1. Start the backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8765 --reload
```

### 2. Start the frontend

```bash
cd frontend
npm install
npm start          # serves on http://localhost:4200 and proxies /api → :8765
```

Open <http://localhost:4200>, paste a paper reference, and click **Visualize**.

## Inputs accepted

| Input               | Example                                                       |
|---------------------|---------------------------------------------------------------|
| ArXiv ID            | `1706.03762`                                                  |
| ArXiv URL           | `https://arxiv.org/abs/1706.03762`                            |
| DOI                 | `10.1145/3292500.3330701`                                     |
| DOI URL             | `https://doi.org/10.1145/3292500.3330701`                     |
| Paper title         | `Attention is all you need`                                   |
| Google Scholar URL  | `https://scholar.google.com/scholar?cites=17763308536187984722` |

Claude is asked to identify the paper from whatever you paste. For Google
Scholar URLs with `?cites=<cluster_id>`, it understands the cluster ID
identifies the *source* paper and tries to resolve it.

## Controls

- **Max depth** – how many levels of "X cites Y cites Z" to expand. `0` = root only.
  Defaults to **1** (Claude calls scale exponentially, so depth 3 is rarely worth the cost).
- **Max children per node** – how many citing papers to keep per node.
  Defaults to **5**.
- **Max total nodes** – hard cap to keep visualizations interactive.

## API

- `GET  /api/health` – liveness probe.
- `POST /api/resolve` – `{query}` → resolved paper metadata.
- `POST /api/tree` – non-streaming, returns the full tree as JSON.
- `GET  /api/tree/stream?query=…&max_depth=…&max_per_node=…&max_total_nodes=…` –
  SSE stream of `resolved`, `root`, `node`, `edge`, `done` events.

## Caveats

- **Quality varies.** Claude is asked to find citing papers via web search.
  Famous papers (Attention is All You Need, BERT) work great. Obscure or very
  recent papers may produce empty results or, worse, hallucinated bibliography
  entries. The system prompt instructs Claude to return empty results rather
  than fabricate, but verify anything important.
- **Costs add up fast.** A depth-2 crawl with default per-node=5 is roughly 25
  Claude turns. At Opus 4.8 that is a few dollars per query; at Sonnet 4.6 it
  is closer to $0.50.
- **No deduplication across sessions.** Each query starts fresh — no caching of
  citation lookups across runs. Prompt caching does keep the per-call system
  prompt cheap.
