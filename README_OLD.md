---

# README.md

```markdown
# 10K Insight Agent (POC)

FastAPI + LangGraph microservice that:
1. Takes a user query (“Analyze Microsoft’s 10-K and map to our catalog”)
2. Resolves the company (with disambiguation if needed)
3. Fetches the latest 10-K from SEC EDGAR
4. Embeds it for RAG
5. Runs an **agentic solution matcher** that mines pains, maps to your products, handles objections, and drafts a pitch — all with citations and a visible agent trace.

---

## Quickstart

### 1) Clone & install
```bash
git clone <your-repo-url> 10k-insight-agent
cd 10k-insight-agent
python -m venv .venv && source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
2) Configure
Create src/configs/settings.yaml (or copy from settings.example.yaml) and .env (copy from .env.example):

yaml
Copy code
# src/configs/settings.yaml
openai_api_key: "sk-..."
embedding_model_name: "text-embedding-3-large"
sec_user_agent: "10KInsightAgent/0.1 (you@company.com)"
vector_store_dir: "src/stores/vector"
catalog_store_dir: "src/stores/catalog"
SEC requirement: A proper User-Agent is mandatory.

Put your product catalog in src/knowledge/products.json (simple schema is fine for POC):

json
Copy code
[
  {
    "product_id": "cloud-optimizer",
    "title": "Cloud Optimizer",
    "summary": "Reduce cloud spend with automated rightsizing and commitment planning.",
    "capabilities": ["cost optimization", "rightsizing", "forecasting"],
    "icp": {"industries": ["SaaS","Retail"], "min_emp": 200},
    "proof_points": ["Avg 18% savings in 90 days"]
  }
]
3) Run
bash
Copy code
bash scripts/dev_run.sh
# or
uvicorn src.main:app --reload --port 8000
Call the API:

perl
Copy code
GET http://localhost:8000/analyze?query=Summarize Apple’s latest 10-K risks and map to our FinOps product
Example response (trimmed):

json
Copy code
{
  "company": "Apple Inc",
  "filing_url": "https://www.sec.gov/Archives/…",
  "embedding_chunks": 713,
  "insights": {
    "pain_points": [...],
    "suggested_solutions": [...],
    "draft_pitch": "Hi <persona> ..."
  },
  "trace": [
    {"at":"2025-10-15T10:12:03Z","agent":"ProblemMiner","action":"extract_pains","summary":"Found 3 pains with citations"},
    {"at":"2025-10-15T10:12:05Z","agent":"ProductRetriever","action":"retrieve_products","summary":"Loaded 6 candidate products"},
    {"at":"2025-10-15T10:12:07Z","agent":"FitScorer","action":"score_fit","summary":"Top match: Cloud Optimizer (92/100)"}
  ]
}
Project Layout
src/main.py – FastAPI app startup

src/api/routes.py – /analyze endpoint to run the DAG

src/graph/dag.py – defines the orchestration graph

src/nodes/company_resolver.py – extracts/disambiguates company

src/nodes/sec_fetcher.py – fetches and saves latest 10-K

src/nodes/embedder.py – cleans, sections, chunks, embeds filing

src/nodes/solution_matcher/ – agentic subgraph:

problem_miner.py – mines pains/objectives with citations

product_retriever.py – pulls candidates from catalog store

fit_scorer.py – explains product–pain fit with scores & evidence

objection_handler.py – likely objections + grounded rebuttals

pitch_writer.py – persona-aware pitch referencing 10-K quotes

subgraph.py – wires the above plus a Referee guard and emits trace events

src/utils/ – helpers (SEC API, text parsing, embeddings, logging)

src/knowledge/ – product catalog + prompt templates

src/stores/ – vector store persistence (filings + catalog)

data/filings/ – raw downloaded filings

tests/ – minimal unit/e2e tests

scripts/ – dev runners

Running Notes
Disambiguation: if multiple companies match the query, the DAG short-circuits with

json
Copy code
{ "status": "disambiguation_required", "candidates": [...] }
Your UI should prompt the rep to pick one and re-call /analyze.

Citations: every pain/match/pitch includes citations such as "10K:Item 1A:page 14" or catalog doc refs.

Guardrails: the subgraph’s Referee rejects ungrounded claims and loops the relevant agent for revision (you’ll see this in the trace).

Storage: this POC writes vectors to disk (Chroma). Swap to pgvector/OpenSearch by adjusting utils/embeddings.py and the store calls.

Dependencies
See requirements.txt (example):

makefile
Copy code
fastapi==0.115.0
uvicorn[standard]==0.30.6
langgraph==0.2.31
langchain==0.3.4
langchain-community==0.3.3
chromadb==0.5.5
beautifulsoup4==4.12.3
aiohttp==3.10.5
aiofiles==24.1.0
python-dotenv==1.0.1
pydantic==2.9.2
pyyaml==6.0.2
Testing
bash
Copy code
pytest -q
tests/test_sec_fetcher.py — mocks SEC endpoints, asserts correct file saved.

tests/test_solution_matcher.py — uses a tiny fixture 10-K and a tiny catalog to validate scoring + citations present.