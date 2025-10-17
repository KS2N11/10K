Project tree
10k-insight-agent/
├─ src/
│  ├─ main.py                       # FastAPI entrypoint
│  ├─ api/
│  │  └─ routes.py                  # /analyze endpoint
│  ├─ graph/
│  │  ├─ __init__.py
│  │  └─ dag.py                     # LangGraph DAG (resolver → fetcher → embedder → solution_matcher)
│  ├─ nodes/
│  │  ├─ __init__.py
│  │  ├─ company_resolver.py        # extracts/disambiguates company
│  │  ├─ sec_fetcher.py             # pulls latest 10-K via SEC, saves locally
│  │  ├─ embedder.py                # chunk + embed filing (Chroma or pgvector)
│  │  ├─ solution_matcher/
│  │  │  ├─ __init__.py
│  │  │  ├─ subgraph.py             # agentic subgraph (ProblemMiner, ProductRetriever, FitScorer, Referee, etc.)
│  │  │  ├─ problem_miner.py
│  │  │  ├─ product_retriever.py
│  │  │  ├─ fit_scorer.py
│  │  │  ├─ objection_handler.py
│  │  │  └─ pitch_writer.py
│  ├─ utils/
│  │  ├─ sec_api.py                 # low-level SEC helpers (CIK lookup, latest filing URL)
│  │  ├─ text_utils.py              # html->text, section tagging, chunking
│  │  ├─ embeddings.py              # embedding client factory
│  │  └─ logging.py                 # structured logging + trace helpers
│  ├─ stores/
│  │  ├─ vector/                    # local Chroma persistence (POC)
│  │  └─ catalog/                   # embeddings/index for your product catalog
│  ├─ knowledge/
│  │  ├─ products.json              # your product catalog (capabilities, ICP rules, proof points)
│  │  └─ prompts/
│  │     ├─ extract_pains.txt
│  │     ├─ match_solutions.txt
│  │     └─ generate_pitch.txt
│  └─ configs/
│     ├─ settings.example.yaml      # sample config
│     └─ settings.yaml              # local config (gitignored)
├─ data/
│  └─ filings/                      # downloaded raw 10-K HTML/TXT
├─ tests/
│  ├─ test_company_resolver.py
│  ├─ test_sec_fetcher.py
│  ├─ test_embedder.py
│  └─ test_solution_matcher.py
├─ scripts/
│  ├─ dev_run.sh                    # uvicorn launcher
│  └─ reset_store.sh                # wipe vector stores (POC)
├─ .env.example                     # OPENAI_API_KEY, SEC_USER_AGENT, etc.
├─ .gitignore
├─ requirements.txt                 # pinned deps for POC
├─ README.md
└─ ARCHITECTURE.md

ARCHITECTURE.md
# 10K Insight Agent — Architecture

## Goal
Given a user query (e.g., “What are Microsoft’s key risks and which of our products fit?”), run a simple, fast, and explainable pipeline:

1) Resolve company → 2) Fetch latest 10-K → 3) Embed filing → 4) Agentic solution matcher (uses your catalog KB) → 5) Tailored pitch with citations.

We use **FastAPI** for the API, **LangGraph** to orchestrate the DAG, and a local **Chroma** vector store for the POC.

---

## High-level Flow (DAG)



user_query
↓
Company Resolver (nodes/company_resolver.py)
↓
SEC Fetcher (nodes/sec_fetcher.py)
↓
Embedder (nodes/embedder.py)
↓
Solution Matcher Subgraph (nodes/solution_matcher/subgraph.py)
├─ ProblemMiner
├─ ProductRetriever
├─ FitScorer
├─ ObjectionHandler
├─ PitchWriter
└─ Referee (guard/feedback)
↓
Response (insights + draft pitch + trace)


**Entry point**: `src/main.py` exposes `/analyze?query=...` (see `api/routes.py`).  
**Graph definition**: `graph/dag.py` compiles and runs the nodes.

---

## Components

### API
- `src/main.py` – creates the FastAPI app and mounts routes.
- `src/api/routes.py` – defines `/analyze` endpoint. It:
  - builds initial state `{ "user_query": <query> }`
  - invokes the compiled LangGraph workflow
  - returns JSON with optional disambiguation, citations, and agent trace.

### Orchestration (LangGraph)
- `src/graph/dag.py` – declares the DAG:
  - Nodes: `company_resolver` → `sec_fetcher` → `embedder` → `solution_matcher` → END.
  - Adds an internal branch for disambiguation (early return if multiple candidates).

### Nodes
- `nodes/company_resolver.py`  
  Extract/normalize company from the user query.
  - If exact match: set `state["company"]`.
  - If ambiguous: set `state["candidates"]` and short-circuit with `need_disambiguation`.

- `nodes/sec_fetcher.py`  
  Fetch the **latest 10-K** from SEC EDGAR.
  - Uses `utils/sec_api.py` to:
    - resolve CIK by company name,
    - read `submissions/CIK{cik}.json`,
    - locate the latest `10-K`, build the primary document URL,
    - download and save to `data/filings/<Company>_10K.html`.
  - Returns: `file_path`, `filing_url`.

- `nodes/embedder.py`  
  Convert HTML to text, section-tag (Item 1, 1A, 7/7A), chunk, and embed.
  - Uses `utils/text_utils.py` for cleaning/section tagging.
  - Uses `utils/embeddings.py` for an embedding client (OpenAI/Ollama).
  - Persists vectors to `stores/vector/` (Chroma POC).
  - Returns: `vector_index_dir`, `chunks`.

- `nodes/solution_matcher/subgraph.py`  
  A **subgraph** that makes the process agentic and explainable:
  - **ProblemMiner** — extracts top pains/objectives with citations from the 10-K retriever.
  - **ProductRetriever** — retrieves candidate products from your catalog vector index in `stores/catalog/`.
  - **FitScorer** — maps pains → products with an explainable score and cites evidence.
  - **ObjectionHandler** — predicts likely objections + grounded rebuttals (catalog citations).
  - **PitchWriter** — generates a persona-aware opener (+ follow-ups) that **quotes** at least one 10-K line.
  - **Referee** — enforces guardrails: grounding, citations, minimum confidence.
  - Each step appends a structured `TraceEvent` to `state["trace"]`.

---

## State Contract (simplified)
```ts
{
  user_query: string,
  company?: string,
  candidates?: Array<{ name: string, ticker?: string, cik?: string }>,
  file_path?: string,
  filing_url?: string,
  vector_index?: string,
  chunks?: number,

  // solution matcher
  citations?: Array<{source: "10K"|"CATALOG", id: string, section?: string, page?: number, quote?: string}>,
  pains?: Array<{theme: string, rationale: string, citations: string[], confidence: number}>,
  candidates_products?: Array<{product_id: string, title: string, summary: string}>,
  matches?: Array<{pain_theme: string, product_id: string, score: number, why: string, citations: string[]}>,
  objections?: Array<{objection: string, rebuttal: string, citations: string[]}>,
  pitch?: {subject: string, body: string, persona: string, citations: string[]},

  // trace for UI
  trace: Array<{
    at: string, agent: string, action: string, summary: string, artifacts?: any
  }>
}

Config & Secrets

configs/settings.yaml – local runtime config (gitignored). Keys:

openai_api_key (or model provider of choice)

embedding_model_name

sec_user_agent (REQUIRED by SEC: Name/Version (email) )

vector_store_dir

.env – optionally mirrors critical vars for libraries that read from env.

settings.example.yaml and .env.example provided as templates.

Persistence

Raw filings: data/filings/

Filing vectors: stores/vector/ (Chroma persist dir)

Catalog vectors: stores/catalog/ (built from knowledge/products.json)

Tests

Lightweight tests for each node and the end-to-end DAG using a small local fixture.

Extensibility

Replace Chroma with pgvector/OpenSearch by swapping utils/embeddings.py + the vector store calls.

Add tools (e.g., slide/pitch deck generator) as extra nodes after solution_matcher.

Stream traces via Server-Sent Events/WebSocket if you want a live UI.