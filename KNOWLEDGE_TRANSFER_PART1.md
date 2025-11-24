# 10K Insight Agent - Knowledge Transfer Document (Part 1)
## Technical Deep Dive & Architecture

**Prepared for:** Office Knowledge Transfer Session  
**Date:** November 12, 2025  
**Version:** 3.0 (Autonomous Scheduler)  
**Project:** AI-Powered SEC 10-K Analysis Platform

---

## Table of Contents - Part 1

1. [Executive Summary](#executive-summary)
2. [What Problem Does This Solve?](#what-problem-does-this-solve)
3. [System Architecture Overview](#system-architecture-overview)
4. [Technology Stack](#technology-stack)
5. [Database Schema & Data Models](#database-schema--data-models)
6. [Backend Architecture Deep Dive](#backend-architecture-deep-dive)
7. [Frontend Architecture Deep Dive](#frontend-architecture-deep-dive)
8. [AI/LLM Integration](#aillm-integration)

---

## Executive Summary

### What is the 10K Insight Agent?

The **10K Insight Agent** is an AI-powered platform that autonomously analyzes companies' SEC 10-K filings (annual reports) and intelligently matches their business pain points to your product catalog. It's designed to help sales and business development teams identify opportunities by understanding what challenges companies are facing.

### Key Capabilities

- ✅ **Autonomous Operation**: Runs 24/7 with AI-powered decision making on which companies to analyze
- ✅ **Pain Point Mining**: Extracts business challenges from 10-K filings with citations and confidence scores
- ✅ **Product Matching**: Maps pain points to your product catalog with fit scores (0-100)
- ✅ **Pitch Generation**: Creates persona-aware sales pitches with evidence from filings
- ✅ **Smart Caching**: Avoids re-analyzing companies unnecessarily (60-80% efficiency gain)
- ✅ **Real-time UI**: Modern React frontend with live progress tracking
- ✅ **Batch Processing**: Analyze multiple companies simultaneously

### Business Value

**For Sales Teams:**
- Identify which companies need your products based on their own disclosures
- Get ready-made pitches with evidence from official SEC filings
- Prioritize outreach based on fit scores

**For Business Development:**
- Discover market trends and common pain points across industries
- Understand competitive landscape through company disclosures
- Track changes in company strategies year-over-year

**ROI Metrics:**
- Reduces manual research time from 2-3 hours to 2-3 minutes per company
- Analyzes 50+ companies in a single batch job (~2 hours)
- Estimated time saved: 100+ hours of manual research per batch

---

## What Problem Does This Solve?

### The Manual Problem

**Traditional approach to sales research:**
1. Sales rep identifies target company
2. Manually reads 100+ page 10-K filing (2-3 hours)
3. Takes notes on business challenges
4. Searches product catalog for potential fits
5. Crafts personalized pitch
6. Total time: **4-6 hours per company**

### The Automated Solution

**With 10K Insight Agent:**
1. Add company name to queue (or let scheduler auto-select)
2. AI analyzes entire 10-K in 2-3 minutes
3. Extracts pain points with citations
4. Matches to product catalog with scores
5. Generates persona-targeted pitch
6. Total time: **2-3 minutes per company** (96% time savings) - 1 minutes

### Real-World Use Case

**Scenario:** You sell cloud optimization services and want to target companies struggling with infrastructure costs.

**Manual Process:**
- Read Apple's 10-K (140 pages)
- Find mentions of cloud costs, infrastructure scaling
- Map to your product capabilities
- Write pitch email

**Automated Process:**
- System extracts: "Apple mentions 'increased costs from cloud infrastructure and data center expansion' with 85% confidence"
- System matches: "Cloud Modernization & Management product has 92/100 fit score"
- System generates: Pitch targeted to CFO/CTO with specific quotes from 10-K

---

## System Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                   React + TypeScript Frontend                   │
│         (Dashboard, Analysis Queue, Company Insights)           │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/REST API
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND                            │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐ │
│  │   Routes     │   Services   │  Repository  │  Scheduler   │ │
│  │  (API Layer) │ (Business)   │  (Data)      │ (Autonomous) │ │
│  └──────────────┴──────────────┴──────────────┴──────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                ▼                         ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│   POSTGRESQL DATABASE    │  │   LANGGRAPH AI ENGINE    │
│                          │  │                          │
│  • Companies             │  │  ┌────────────────────┐  │
│  • Analyses              │  │  │ Company Resolver   │  │
│  • Pain Points           │  │  ├────────────────────┤  │
│  • Product Matches       │  │  │ SEC Fetcher        │  │
│  • Pitches               │  │  ├────────────────────┤  │
│  • Scheduler Memory      │  │  │ Embedder           │  │
│  • Jobs                  │  │  ├────────────────────┤  │
│                          │  │  │ Solution Matcher   │  │
└──────────────────────────┘  │  │  • Problem Miner   │  │
                              │  │  • Fit Scorer      │  │
                              │  │  • Pitch Writer    │  │
                              │  └────────────────────┘  │
                              └──────────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
          ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
          │   SEC EDGAR API  │ │  CHROMADB        │ │  LLM PROVIDERS   │
          │                  │ │  Vector Store    │ │  (Groq/OpenAI)   │
          │  • Company Data  │ │                  │ │                  │
          │  • 10-K Filings  │ │  • Embeddings    │ │  • Text Analysis │
          │  • Market Cap    │ │  • Semantic      │ │  • Extraction    │
          │                  │ │    Search        │ │  • Generation    │
          └──────────────────┘ └──────────────────┘ └──────────────────┘
```

### Data Flow (End-to-End)

**User-Initiated Analysis:**
```
1. User submits company list → React UI
2. POST /api/v2/analysis/batch → FastAPI endpoint
3. BatchAnalysisService creates job_id → PostgreSQL
4. Background task spawned → Async processing
5. For each company:
   a. Company Resolver → SEC EDGAR API → Get CIK/ticker
   b. SEC Fetcher → Download 10-K HTML → Local storage
   c. Embedder → Chunk text → ChromaDB vectors
   d. Solution Matcher (LangGraph):
      - Problem Miner → Extract pain points → LLM
      - Product Retriever → Load catalog
      - Fit Scorer → Match products → Scoring algorithm
      - Pitch Writer → Generate pitch → LLM
   e. Save results → PostgreSQL (Analysis, PainPoints, Matches, Pitches)
6. Frontend polls GET /api/v2/analysis/status/{job_id} every 2 seconds
7. User views results in Company Insights page
```

**Autonomous Scheduler Flow:**
```
1. Cron trigger (e.g, runs very 15 minutes) → APScheduler
2. SchedulerAgent queries:
   - Candidate companies from SEC
   - Memory (past analyses, priority scores)
   - Learned patterns - Not implemeted yet
3. LLM decides which companies to analyze with reasoning
4. Batch job created automatically
5. Same flow as user-initiated (steps 5-7 above)
6. Memory updated with results and patterns
```

---

## Technology Stack

### Frontend Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| **React** | 18.3 | UI library for component-based architecture |
| **TypeScript** | 5.2 | Type safety and better developer experience |
| **Vite** | 5.3 | Fast build tool and dev server |
| **Tailwind CSS** | 3.4 | Utility-first styling framework |
| **React Router** | 6.26 | Client-side routing |
| **Axios** | 1.7 | HTTP client for API calls |
| **Recharts** | 2.12 | Charts and data visualizations |
| **Lucide React** | 0.400 | Icon library |

**Why React?** Originally built with Streamlit (Python-based), migrated to React for:
- Better performance and UX
- Real-time updates
- Professional appearance
- Easier customization

### Backend Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.9+ | Primary programming language |
| **FastAPI** | Latest | Modern async web framework |
| **SQLAlchemy** | Latest | ORM for database operations |
| **PostgreSQL** | 14+ | Relational database |
| **LangGraph** | Latest | AI workflow orchestration |
| **LangChain** | Latest | LLM integration framework |
| **ChromaDB** | Latest | Vector database for embeddings |
| **APScheduler** | 3.10+ | Cron-based scheduling |
| **BeautifulSoup** | Latest | HTML parsing for 10-K files |
| **aiohttp** | Latest | Async HTTP client |

**Why FastAPI?** 
- Async/await support for concurrent processing
- Auto-generated OpenAPI docs
- Type hints and validation with Pydantic
- High performance

**Why PostgreSQL?**
- Reliable and proven for production
- Excellent JSON support for flexible data
- Strong indexing capabilities
- Easy backup and migration

### AI/ML Stack

| Component | Provider Options | Current Default |
|-----------|------------------|-----------------|
| **LLM** | Groq, OpenAI, Azure OpenAI | Gpt-4o (moonshotai/kimi-k2-instruct) |
| **Embeddings** | Sentence Transformers, OpenAI, Cohere | Sentence Transformers (all-mpnet-base-v2) &  OpenAi Embeddings (text-embedding-3-large)|
| **Vector Store** | ChromaDB | ChromaDB (local) |

---

## Database Schema & Data Models

### Core Tables

#### 1. `companies`
Stores company information from SEC.

```sql
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    cik VARCHAR(10) UNIQUE NOT NULL,     -- SEC Central Index Key
    ticker VARCHAR(10),
    industry VARCHAR(255),
    sector VARCHAR(100),
    market_cap VARCHAR(20),              -- SMALL, MID, LARGE, MEGA
    market_cap_value FLOAT,              -- Actual $ value
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_company_search ON companies(name, ticker, cik);
CREATE INDEX idx_company_filters ON companies(market_cap, industry, sector);
```

**Key Points:**
- CIK is unique identifier from SEC
- Market cap categories for filtering
- Industry/sector for segmentation

#### 2. `analyses`
Tracks each 10-K analysis run.

```sql
CREATE TABLE analyses (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    filing_date TIMESTAMP NOT NULL,
    accession_number VARCHAR(20),
    filing_url VARCHAR(500),
    filing_path VARCHAR(500),            -- Local file path
    status VARCHAR(20),                  -- queued, in_progress, completed, failed
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    time_taken_seconds FLOAT,
    total_tokens_used INTEGER DEFAULT 0,
    embedding_tokens INTEGER DEFAULT 0,
    llm_tokens INTEGER DEFAULT 0,
    used_cached_filing BOOLEAN DEFAULT FALSE,
    used_cached_embeddings BOOLEAN DEFAULT FALSE,
    catalog_hash VARCHAR(64),            -- SHA256 of products.json
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_analysis_company_date ON analyses(company_id, filing_date);
CREATE INDEX idx_analysis_status ON analyses(status, created_at);
```

**Key Points:**
- Tracks performance metrics (time, tokens)
- Cache flags for optimization
- Catalog hash detects product changes
- Status tracking for job management

#### 3. `pain_points`
Identified business challenges from 10-K.

```sql
CREATE TABLE pain_points (
    id SERIAL PRIMARY KEY,
    analysis_id INTEGER REFERENCES analyses(id) ON DELETE CASCADE,
    theme VARCHAR(255) NOT NULL,
    rationale TEXT NOT NULL,
    confidence FLOAT NOT NULL,           -- 0.0 to 1.0
    quotes JSONB,                        -- Array of supporting quotes
    category VARCHAR(100),               -- Financial, Operational, Regulatory
    severity VARCHAR(20),                -- High, Medium, Low
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_pain_category ON pain_points(category, confidence);
```

**Example Record:**
```json
{
    "theme": "Rising Cloud Infrastructure Costs",
    "rationale": "Company experiencing 35% YoY increase in data center expenses",
    "confidence": 0.87,
    "quotes": [
        "Our cloud infrastructure costs increased by $2.5B in fiscal year 2024",
        "We expect continued pressure on operating margins from cloud expenses"
    ],
    "category": "Financial",
    "severity": "High"
}
```

#### 4. `product_matches`
Product-to-pain mappings with scores.

```sql
CREATE TABLE product_matches (
    id SERIAL PRIMARY KEY,
    analysis_id INTEGER REFERENCES analyses(id) ON DELETE CASCADE,
    pain_point_id INTEGER REFERENCES pain_points(id) ON DELETE CASCADE,
    product_id VARCHAR(100) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    product_category VARCHAR(100),
    fit_score INTEGER NOT NULL,          -- 0-100
    why_fits TEXT NOT NULL,
    evidence JSONB,                      -- Array of evidence points
    potential_objections JSONB,          -- Array of objection objects
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_match_score ON product_matches(fit_score, created_at);
CREATE INDEX idx_match_product ON product_matches(product_id, fit_score);
```

**Example Record:**
```json
{
    "product_id": "cloud-modernization",
    "product_name": "Cloud Modernization & Management",
    "fit_score": 92,
    "why_fits": "Direct alignment with cost optimization needs. Our platform has achieved 35% cost reduction for similar enterprises.",
    "evidence": [
        "Customer has multi-cloud footprint mentioned in filing",
        "Recent infrastructure expansion creating optimization opportunity",
        "CFO prioritizing margin improvement per earnings call"
    ],
    "potential_objections": [
        {
            "objection": "We already have internal cloud team",
            "rebuttal": "Our platform augments existing teams with AI-powered automation they don't have time to build"
        }
    ]
}
```

#### 5. `pitches`
Generated sales pitches.

```sql
CREATE TABLE pitches (
    id SERIAL PRIMARY KEY,
    analysis_id INTEGER REFERENCES analyses(id) ON DELETE CASCADE,
    product_match_id INTEGER REFERENCES product_matches(id) ON DELETE CASCADE,
    persona VARCHAR(255) NOT NULL,       -- CTO, CFO, VP Engineering
    subject VARCHAR(500) NOT NULL,
    body TEXT NOT NULL,
    key_quotes JSONB,                    -- 10-K quotes used in pitch
    overall_score INTEGER NOT NULL,
    sent BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_pitch_score ON pitches(overall_score, created_at);
CREATE INDEX idx_pitch_persona ON pitches(persona, overall_score);
```

#### 6. `analysis_jobs`
Batch job tracking.

```sql
CREATE TABLE analysis_jobs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(36) UNIQUE NOT NULL,  -- UUID
    filters JSONB,
    company_names JSONB,
    total_companies INTEGER NOT NULL,
    completed_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    skipped_count INTEGER DEFAULT 0,
    current_company VARCHAR(255),
    current_step VARCHAR(100),
    estimated_time_remaining FLOAT,      -- seconds
    status VARCHAR(20),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    total_time_seconds FLOAT,
    total_tokens_used INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Scheduler Tables (v3.0 Autonomous Feature)

#### 7. `scheduler_config`
Scheduler settings.

```sql
CREATE TABLE scheduler_config (
    id SERIAL PRIMARY KEY,
    is_active BOOLEAN DEFAULT FALSE,
    cron_schedule VARCHAR(100),          -- e.g., "0 2 * * *"
    market_cap_priority JSONB,           -- ["SMALL", "MID", "LARGE", "MEGA"]
    batch_size INTEGER DEFAULT 50,
    use_llm_agent BOOLEAN DEFAULT TRUE,
    analysis_interval_days INTEGER DEFAULT 90,
    industry_filters JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### 8. `scheduler_runs`
History of autonomous runs.

```sql
CREATE TABLE scheduler_runs (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(36) UNIQUE NOT NULL,
    llm_reasoning TEXT,                  -- Why LLM selected these companies
    companies_selected INTEGER,
    companies_analyzed INTEGER,
    companies_skipped INTEGER,
    total_tokens_used INTEGER,
    total_time_seconds FLOAT,
    status VARCHAR(20),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 9. `company_priorities`
Memory for smart scheduling.

```sql
CREATE TABLE company_priorities (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    priority_score FLOAT DEFAULT 50.0,   -- 0-100
    last_analyzed_at TIMESTAMP,
    times_analyzed INTEGER DEFAULT 0,
    avg_product_match_score FLOAT,
    has_high_value_matches BOOLEAN DEFAULT FALSE,
    next_scheduled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Priority Score Calculation:**
```python
base_score = 50.0

# Boost for high-value matches
if avg_match_score > 75:
    base_score += 25

# Boost for many pain points
if total_pain_points > 10:
    base_score += 10

# Reduce for over-analysis
if times_analyzed > 3:
    base_score -= 10

# Market cap priority
if market_cap == "SMALL":
    base_score += 15
elif market_cap == "MID":
    base_score += 10
```

#### 10. `scheduler_memory`
Learned patterns and strategies.

```sql
CREATE TABLE scheduler_memory (
    id SERIAL PRIMARY KEY,
    memory_key VARCHAR(255) UNIQUE,
    memory_type VARCHAR(50),             -- learned_pattern, strategy, blacklist
    memory_value JSONB,
    confidence_score FLOAT,
    times_validated INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Example Memory:**
```json
{
    "memory_key": "tech_sector_pattern_2024",
    "memory_type": "learned_pattern",
    "memory_value": {
        "observation": "Technology sector small caps yield 82% avg match score",
        "recommendation": "Prioritize tech small caps in future runs",
        "data": {
            "avg_match_score": 82,
            "sample_size": 45,
            "top_pain_categories": ["Cloud Costs", "Scaling Challenges"]
        }
    },
    "confidence_score": 0.85
}
```

#### 11. `scheduler_decisions`
Every LLM decision logged.

```sql
CREATE TABLE scheduler_decisions (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(36) REFERENCES scheduler_runs(run_id),
    company_id INTEGER REFERENCES companies(id),
    decision VARCHAR(20),                -- selected, skipped
    reasoning TEXT,
    confidence_score FLOAT,
    context JSONB,                       -- Days since last, priority, etc.
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Relationships Diagram

```
companies (1) ──────< (N) analyses
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼
      pain_points   product_matches   pitches
            │              │
            └──────┬───────┘
                   │
                   ▼
            product_matches ──────< pitches
```

---

## Backend Architecture Deep Dive

### Project Structure

```
src/
├── api/                    # API layer
│   ├── routes.py          # Legacy v1 routes
│   ├── routes_v2.py       # Modern batch analysis routes
│   └── scheduler_routes.py # Autonomous scheduler routes
│
├── services/              # Business logic
│   ├── batch_analysis.py  # Batch processing service
│   ├── autonomous_scheduler.py
│   └── scheduler_agent.py # LLM-powered decision making
│
├── database/              # Data layer
│   ├── database.py        # Connection management
│   ├── models.py          # SQLAlchemy models
│   ├── repository.py      # Data access layer
│   └── scheduler_models.py # Scheduler tables
│
├── graph/                 # AI workflow
│   └── dag.py            # LangGraph orchestration
│
├── nodes/                 # DAG nodes
│   ├── company_resolver.py
│   ├── sec_fetcher.py
│   ├── embedder.py
│   └── solution_matcher/
│       ├── subgraph.py
│       ├── problem_miner.py
│       ├── product_retriever.py
│       ├── fit_scorer.py
│       ├── objection_handler.py
│       └── pitch_writer.py
│
├── utils/                 # Utilities
│   ├── llm_factory.py    # Centralized LLM creation
│   ├── multi_llm.py      # Multi-provider LLM
│   ├── multi_embeddings.py
│   ├── sec_api.py        # SEC EDGAR client
│   ├── sec_filter.py     # Market cap filtering - This needs review
│   ├── catalog.py        # Product catalog utils
│   └── logging.py
│
├── knowledge/             # Knowledge base
│   ├── products.json     # Product catalog
│   └── prompts/          # LLM prompts
│
└── stores/               # Storage
    ├── vector/           # ChromaDB data
    └── catalog/          # Catalog embeddings
```

### Key Components

#### 1. FastAPI Application (`main.py`)

```python
app = FastAPI(
    title="10K Insight Agent",
    version="3.0.0 - Autonomous Scheduler"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_methods=["*"],
    allow_headers=["*"]
)

# Routes
app.include_router(router, prefix="", tags=["analysis"])
app.include_router(router_v2, tags=["batch"])
app.include_router(scheduler_router, tags=["scheduler"])

# Startup
@app.on_event("startup")
async def startup_event():
    init_db()
    scheduler = await get_autonomous_scheduler(config)
```

#### 2. Batch Analysis Service

**File:** `src/services/batch_analysis.py`

**Key Method:** `start_batch_job()`

```python
async def start_batch_job(
    self,
    company_names: List[str] = None,
    filters: Dict = None,
    limit: int = 50,
    force_reanalyze: bool = False
) -> str:
    """
    Create job, spawn background task, return job_id immediately.
    """
    job_id = str(uuid.uuid4())
    
    # Get companies to process
    if company_names:
        companies = await get_companies_by_names(company_names)
    elif filters:
        companies = await sec_filter.search_companies(filters)
    
    # Create job record
    AnalysisJobRepository.create(db, job_id, ...)
    
    # Start async processing (don't await - run in background)
    asyncio.create_task(
        self._process_batch(job_id, companies, force_reanalyze)
    )
    
    return job_id
```

**Smart Caching Logic:**

```python
# In _process_batch, for each company:
if not force_reanalyze:
    latest_analysis = AnalysisRepository.get_latest_for_company(db, company.id)
    
    if latest_analysis and latest_analysis.status == "COMPLETED":
        # Check if catalog changed
        if latest_analysis.catalog_hash == current_catalog_hash:
            # Check if has actual data
            if pain_count > 0:
                logger.info("⏭️ Skipping - already analyzed")
                skipped += 1
                continue
```

#### 3. LangGraph DAG

**File:** `src/graph/dag.py`

**Workflow:**
```python
workflow = StateGraph(dict)

# Add nodes
workflow.add_node("company_resolver", company_resolver_node)
workflow.add_node("sec_fetcher", sec_fetcher_node)
workflow.add_node("embedder", embedder_node)
workflow.add_node("solution_matcher", solution_matcher_node)

# Entry point
workflow.set_entry_point("company_resolver")

# Conditional routing
workflow.add_conditional_edges(
    "company_resolver",
    should_continue_after_resolver,
    {
        "fetch": "sec_fetcher",
        "end": END
    }
)

# Linear flow
workflow.add_edge("sec_fetcher", "embedder")
workflow.add_edge("embedder", "solution_matcher")
workflow.add_edge("solution_matcher", END)

app = workflow.compile()
```

**State Structure:**
```python
{
    # Input
    "user_query": "Analyze Microsoft",
    "config": {...},
    
    # Company resolution
    "company": "Microsoft Corporation",
    "cik": "0000789019",
    "ticker": "MSFT",
    
    # Filing
    "filing_url": "https://...",
    "file_path": "data/filings/Microsoft_10K.html",
    "filing_date": "2024-07-31",
    
    # Embedding
    "vector_store": <ChromaDB instance>,
    "chunks": 750,
    
    # Analysis results
    "pains": [{...}, {...}],
    "matches": [{...}, {...}],
    "pitch": {...},
    "citations": [{...}]
}
```

#### 4. Node Details

**Company Resolver** (`company_resolver.py`)
- Queries SEC EDGAR API for company by name
- Returns CIK, ticker, official name
- Handles disambiguation if multiple matches

**SEC Fetcher** (`sec_fetcher.py`)
- Downloads latest 10-K filing
- Parses HTML to extract text
- Saves locally to `data/filings/`
- Extracts metadata (filing date, accession number)

**Embedder** (`embedder.py`)
- Chunks 10-K text (1000 chars, 200 overlap)
- Creates embeddings using Sentence Transformers
- Stores in ChromaDB with metadata (section, page)
- Handles caching (skip if already embedded)

**Solution Matcher** - Subgraph with 5 nodes:

1. **Problem Miner** (`problem_miner.py`)
   - Queries vector store for risk/challenge sections
   - LLM extracts structured pain points
   - Returns: `{theme, rationale, quotes, confidence}`

2. **Product Retriever** (`product_retriever.py`)
   - Loads `products.json`
   - Returns product catalog

3. **Fit Scorer** (`fit_scorer.py`)
   - For each pain + product combination
   - Scores fit (0-100) using:
     - Capability overlap
     - ICP alignment
     - Proof point relevance
   - Returns top matches (>60 score)

4. **Objection Handler** (`objection_handler.py`)
   - For each top match, generates objections
   - LLM creates rebuttals
   - Returns: `{objection, rebuttal}`

5. **Pitch Writer** (`pitch_writer.py`)
   - Selects top match
   - Determines persona (CTO, CFO, etc.)
   - LLM generates pitch with:
     - Subject line
     - Body with quotes
     - Call to action

#### 5. LLM Integration

**Centralized Factory** (`llm_factory.py`)

```python
class LLMFactory:
    def create_llm_manager(self) -> MultiProviderLLM:
        """Create LLM with configured provider."""
        config = load_config()
        return MultiProviderLLM(
            primary_provider=config["llm"]["primary_provider"],
            fallback_providers=config["llm"]["fallback_providers"],
            config=config
        )
    
    def create_embedder(self) -> MultiProviderEmbeddings:
        """Create embeddings with configured provider."""
        config = load_config()
        return MultiProviderEmbeddings(
            primary_provider=config["embedding"]["primary_provider"],
            config=config
        )
```

**Multi-Provider LLM** (`multi_llm.py`)

```python
class MultiProviderLLM:
    async def ainvoke(self, messages, **kwargs):
        """Try primary, fallback to others if it fails."""
        try:
            return await self.primary.ainvoke(messages, **kwargs)
        except Exception as e:
            for fallback in self.fallbacks:
                try:
                    return await fallback.ainvoke(messages, **kwargs)
                except:
                    continue
            raise e
```

---

## Frontend Architecture Deep Dive

### Project Structure

```
frontend/
├── src/
│   ├── App.tsx            # Main app with routing
│   ├── main.tsx          # Entry point
│   │
│   ├── pages/            # Route components
│   │   ├── Dashboard.tsx
│   │   ├── AnalysisQueue.tsx
│   │   ├── CompanyInsights.tsx
│   │   ├── TopPitches.tsx
│   │   ├── Metrics.tsx
│   │   └── CatalogManager.tsx
│   │
│   ├── components/
│   │   ├── common/       # Reusable
│   │   │   ├── Loading.tsx
│   │   │   ├── ErrorMessage.tsx
│   │   │   └── Card.tsx
│   │   └── layout/
│   │       └── Sidebar.tsx
│   │
│   ├── services/
│   │   └── api.ts        # API client
│   │
│   └── types/            # TypeScript types
│
├── public/
│   └── config.js         # Runtime configuration
│
└── package.json
```

### Key Pages

#### 1. Dashboard (`Dashboard.tsx`)

**Purpose:** Overview metrics and quick actions

**Features:**
- Total companies analyzed
- Recent analyses
- Quick start buttons
- System health

#### 2. Analysis Queue (`AnalysisQueue.tsx`)

**Purpose:** Create and monitor batch jobs

**Tabs:**
1. **Active Jobs** - Live progress with 2-second polling
2. **Company List** - Manual company name entry
3. **Filter Search** - Market cap/industry filters + SEC preview

**Real-time Updates:**
```typescript
useEffect(() => {
    const interval = setInterval(async () => {
        if (activeJobId) {
            const status = await apiClient.getJobStatus(activeJobId);
            setJobStatus(status);
        }
    }, 2000); // Poll every 2 seconds
    
    return () => clearInterval(interval);
}, [activeJobId]);
```

**Progress Display:**
```typescript
<div>
    <span>{completed}/{total} completed</span>
    <span>{failed} failed</span>
    <span>{skipped} skipped</span>
    <ProgressBar value={(completed / total) * 100} />
    <span>ETA: {formatTime(estimated_time_remaining)}</span>
</div>
```

#### 3. Company Insights (`CompanyInsights.tsx`)

**Purpose:** View analysis results for a company

**Features:**
- Search companies by name
- View pain points with confidence scores
- See product matches with fit scores
- Read generated pitches
- Citations with section references

#### 4. Top Pitches (`TopPitches.tsx`)

**Purpose:** Browse best matches across all companies

**Features:**
- Filter by minimum score (e.g., >80)
- Filter by product
- Sort by score/date
- Copy pitch to clipboard
- Export to CRM (future)

#### 5. Metrics (`Metrics.tsx`)

**Purpose:** Analytics and visualizations

**Features:**
- Charts: analyses over time, tokens used, avg time
- Top industries/sectors
- Success rates
- ROI metrics (time saved)

### API Client (`api.ts`)

**Singleton Pattern:**
```typescript
class ApiClient {
    private client: AxiosInstance;
    
    constructor() {
        this.client = axios.create({
            baseURL: API_BASE_URL,
            timeout: 300000, // 5 minutes
        });
    }
    
    async startBatchAnalysis(params) {
        const response = await this.client.post(
            '/api/v2/analysis/batch',
            params
        );
        return response.data;
    }
    
    async getJobStatus(jobId: string) {
        const response = await this.client.get(
            `/api/v2/analysis/status/${jobId}`
        );
        return response.data;
    }
}

export const apiClient = new ApiClient();
```

**Runtime Configuration:**
```typescript
// Supports environment variable override at runtime
const API_BASE_URL = 
    window.__RUNTIME_CONFIG__?.VITE_API_URL || 
    import.meta.env.VITE_API_URL || 
    'http://localhost:8000';
```

---

## AI/LLM Integration

### LLM Provider Configuration

**Environment Variables:**
```bash
PRIMARY_LLM_PROVIDER=groq
GROQ_API_KEY=your-key-here
```

**settings.yaml:**
```yaml
llm:
  primary_provider: "groq"
  fallback_providers: ["openai"]
  groq:
    model_name: "moonshotai/kimi-k2-instruct-0905"
    temperature: 0.7
    max_tokens: 4096
```

### Prompt Engineering

**Problem Mining Prompt:**
```python
extraction_prompt = """
You are an expert business analyst extracting pain points from SEC 10-K filings.

TASK: Identify business challenges, risks, and objectives.

REQUIREMENTS:
- Extract 5-10 pain points
- Each must have: theme, rationale, quotes, confidence (0-1)
- Focus on actionable business problems
- Cite specific sections

10-K Excerpts:
[Section: Item 1A - Risk Factors]
"We face intense competition from cloud providers with significantly larger 
market share and resources..."

[Section: MD&A]
"Operating expenses increased 42% due to data center expansion and 
infrastructure scaling challenges..."

Provide your analysis in valid JSON format:
{
    "pains": [
        {
            "theme": "Rising Infrastructure Costs",
            "rationale": "42% YoY increase in operating expenses driven by...",
            "quotes": ["Operating expenses increased 42%..."],
            "section": "MD&A",
            "confidence": 0.85
        }
    ]
}
"""
```

**Fit Scoring Algorithm:**
```python
def calculate_fit_score(pain, product):
    score = 0
    
    # Capability overlap (40 points)
    pain_keywords = extract_keywords(pain.theme + pain.rationale)
    product_keywords = extract_keywords(product.capabilities)
    overlap = len(pain_keywords & product_keywords)
    score += min(overlap * 10, 40)
    
    # ICP alignment (30 points)
    if company.industry in product.icp.industries:
        score += 15
    if company.employee_count >= product.icp.min_emp:
        score += 15
    
    # Confidence (20 points)
    score += pain.confidence * 20
    
    # Proof points relevance (10 points)
    if any(keyword in proof for proof in product.proof_points):
        score += 10
    
    return min(score, 100)
```

**Pitch Generation Prompt:**
```python
pitch_prompt = f"""
You are a sales expert crafting personalized pitches.

COMPANY: {company_name}
PERSONA: {target_persona}  # e.g., CFO
PAIN POINT: {pain_theme}
EVIDENCE: {quotes_from_10k}

PRODUCT: {product_name}
CAPABILITIES: {product_capabilities}
PROOF POINTS: {product_proof}

TASK: Write a compelling email pitch (150-250 words).

REQUIREMENTS:
- Subject line (under 60 characters)
- Hook with specific 10-K quote
- Connect pain to product capability
- Include proof point with metric
- Clear call-to-action
- Professional but conversational tone

Return JSON:
{{
    "subject": "...",
    "body": "...",
    "key_quotes": ["..."],
    "persona": "{target_persona}"
}}
"""
```

### Token Optimization

**Strategies:**
1. **Chunk Smartly:** Only top 8 most relevant chunks to LLM (not all 700+)
2. **Batch Processing:** One LLM call per company, not per pain point
3. **Caching:** Store embeddings, skip re-embedding unchanged filings
4. **Groq Free Tier:** Unlimited tokens for basic usage

**Average Token Usage per Company:**
- Company Resolution: ~500 tokens (SEC API, no LLM)
- Pain Mining: ~15,000 tokens (8 chunks + extraction)
- Fit Scoring: ~5,000 tokens (scoring logic)
- Pitch Writing: ~3,000 tokens (generation)
- **Total: ~23,000 tokens per company**

**Monthly Cost Estimate (if using OpenAI):**
- 50 companies/day × 30 days = 1,500 companies/month
- 1,500 × 23,000 = 34.5M tokens
- GPT-4o-mini: $0.15 per 1M input tokens
- **Monthly cost: ~$5-10**

**With Groq:** FREE (generous free tier)

---

**End of Part 1**

**Next:** Part 2 will cover:
- Deployment & DevOps
- Autonomous Scheduler Details
- API Reference
- Walkthrough Script with Talking Points
- Common Issues & Troubleshooting
- Future Roadmap
