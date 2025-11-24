# 10K Insight Agent - Knowledge Transfer Document (Part 2)
## Deployment, Operations & Presentation Guide

**Prepared for:** Office Knowledge Transfer Session  
**Date:** November 12, 2025  
**Version:** 3.0 (Autonomous Scheduler)

---

## Table of Contents - Part 2

1. [Autonomous Scheduler Deep Dive](#autonomous-scheduler-deep-dive)
2. [API Reference Guide](#api-reference-guide)
3. [Deployment & DevOps](#deployment--devops)
4. [Configuration & Setup](#configuration--setup)
5. [Monitoring & Troubleshooting](#monitoring--troubleshooting)
6. [Presentation Walkthrough Script](#presentation-walkthrough-script)
7. [Demo Flow](#demo-flow)
8. [Common Questions & Answers](#common-questions--answers)
9. [Future Roadmap](#future-roadmap)

---

## Autonomous Scheduler Deep Dive

### What Makes It "Autonomous"?

The v3.0 scheduler transforms the system from a **tool** into an **intelligent agent** that:
- ✅ Decides which companies to analyze (not just executes commands)
- ✅ Learns from past results to improve future decisions
- ✅ Prioritizes based on business value
- ✅ Avoids wasting resources on low-value work
- ✅ Runs continuously without human intervention

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│              AUTONOMOUS SCHEDULER                       │
│  ┌────────────────────────────────────────────────┐   │
│  │         APScheduler (Cron Engine)               │   │
│  │  "0 2 * * *" = Daily at 2 AM                   │   │
│  └─────────────────┬───────────────────────────────┘   │
│                    │ Trigger                            │
│                    ▼                                    │
│  ┌────────────────────────────────────────────────┐   │
│  │         Scheduler Agent (LLM Brain)             │   │
│  │                                                  │   │
│  │  1. Get candidate companies from SEC            │   │
│  │  2. Load memory (past analyses, patterns)       │   │
│  │  3. Build context for LLM                       │   │
│  │  4. Ask LLM to decide + explain reasoning       │   │
│  │  5. Parse LLM response                          │   │
│  └─────────────────┬───────────────────────────────┘   │
│                    │ Selected Companies                 │
│                    ▼                                    │
│  ┌────────────────────────────────────────────────┐   │
│  │      Batch Analysis Service                     │   │
│  │  (Same as user-initiated analysis)              │   │
│  └─────────────────┬───────────────────────────────┘   │
│                    │ Results                            │
│                    ▼                                    │
│  ┌────────────────────────────────────────────────┐   │
│  │         Memory Update                           │   │
│  │  • Update company priorities                    │   │
│  │  • Learn patterns (e.g., "Tech small caps = 82% │   │
│  │    avg match score")                            │   │
│  │  • Store LLM reasoning                          │   │
│  └────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### LLM Decision Making

**Input to LLM:**
```python
prompt = f"""
You are an intelligent scheduler deciding which companies to analyze.

GOAL: Maximize business value by selecting companies with highest potential 
for product matches.

PRIORITY: Focus on SMALL and MID cap companies first (they have more pain points).

CANDIDATES: {len(candidates)} companies available
{json.dumps(candidates[:10], indent=2)}  # Sample shown

MEMORY (Past Learnings):
- Tech sector small caps: 82% avg match score (45 companies analyzed)
- Healthcare mid caps: 75% avg score (30 companies)
- Retail mega caps: 58% avg score (12 companies)
- Companies analyzed >3 times: diminishing returns

CONSTRAINTS:
- Select up to 50 companies
- Avoid companies analyzed in last 90 days (unless high priority)
- Prioritize: SMALL → MID → LARGE → MEGA caps

TASK: Select companies and provide reasoning for each.

Return JSON:
{{
    "selected_companies": [
        {{
            "cik": "0001234567",
            "name": "Tech Startup Inc",
            "ticker": "TECH",
            "reasoning": "SMALL cap, never analyzed, Technology sector shows 82% avg match",
            "confidence": 0.85,
            "priority": "high"
        }}
    ],
    "strategy_summary": "Focusing on small cap tech and healthcare companies based on historical performance..."
}}
"""
```

**LLM Response Example:**
```json
{
    "selected_companies": [
        {
            "cik": "0001559865",
            "name": "Datadog Inc",
            "ticker": "DDOG",
            "reasoning": "SMALL cap monitoring company (never analyzed). Tech sector has 82% historical match rate. Recent IPO likely facing scaling challenges.",
            "confidence": 0.88,
            "priority": "high"
        },
        {
            "cik": "0001327811",
            "name": "Teladoc Health Inc",
            "ticker": "TDOC",
            "reasoning": "MID cap healthcare. Recent 10-K filed 45 days ago. Healthcare sector shows 75% match rate. Digital health expansion creates opportunities.",
            "confidence": 0.79,
            "priority": "medium"
        }
    ],
    "strategy_summary": "Selected 47 companies with 68% SMALL cap, 25% MID cap, 7% LARGE cap. Focused on Technology (40%), Healthcare (30%), SaaS (20%), and E-commerce (10%) sectors based on proven high match rates from past runs."
}
```

### Memory System

**Company Priorities Table:**
```python
# After each analysis, update priority
company_priority = {
    "company_id": 123,
    "priority_score": 75.0,  # Calculated based on:
    "last_analyzed_at": "2024-11-01",
    "times_analyzed": 2,
    "avg_product_match_score": 82.5,
    "has_high_value_matches": True,  # Any match >80
    "next_scheduled_at": "2025-02-01"  # 90 days later
}

# Priority score calculation
base = 50
if avg_match_score > 75: base += 25
if total_pain_points > 10: base += 10
if times_analyzed > 3: base -= 10
if market_cap == "SMALL": base += 15
```

**Learned Patterns:**
```python
scheduler_memory = {
    "memory_key": "tech_small_cap_pattern",
    "memory_type": "learned_pattern",
    "memory_value": {
        "observation": "Technology sector small cap companies yield 82% average product match score",
        "recommendation": "Prioritize tech small caps in future runs",
        "supporting_data": {
            "sample_size": 45,
            "avg_match_score": 82,
            "top_pain_categories": ["Cloud Costs", "Scaling Infrastructure", "Security"],
            "top_product_matches": ["cloud-modernization", "cybersecurity-and-compliance"]
        }
    },
    "confidence_score": 0.85,
    "times_validated": 5  # Incremented when pattern holds true
}
```

### Scheduler API Endpoints

```http
# Get current status
GET /api/scheduler/status
Response: {
    "is_active": true,
    "cron_schedule": "0 2 * * *",
    "next_run_at": "2024-11-13T02:00:00Z",
    "last_run_at": "2024-11-12T02:00:00Z",
    "total_runs": 30,
    "total_companies_analyzed": 1250
}

# Start scheduler
POST /api/scheduler/start
Response: {"message": "Scheduler started", "next_run": "..."}

# Stop scheduler
POST /api/scheduler/stop
Response: {"message": "Scheduler stopped"}

# Update configuration
PUT /api/scheduler/config
Body: {
    "is_active": true,
    "cron_schedule": "0 2 * * *",  # Daily at 2 AM
    "batch_size": 50,
    "market_cap_priority": ["SMALL", "MID", "LARGE", "MEGA"],
    "analysis_interval_days": 90
}

# Trigger immediate run (for testing)
POST /api/scheduler/trigger
Response: {"run_id": "uuid", "message": "Run triggered"}

# Get run history
GET /api/scheduler/runs?limit=10
Response: {
    "runs": [
        {
            "run_id": "uuid",
            "started_at": "2024-11-12T02:00:00Z",
            "companies_selected": 50,
            "companies_analyzed": 48,
            "companies_skipped": 2,
            "status": "completed",
            "llm_reasoning": "Focused on tech small caps..."
        }
    ]
}

# View LLM decisions
GET /api/scheduler/decisions?run_id=uuid
Response: {
    "decisions": [
        {
            "company_name": "Datadog Inc",
            "decision": "selected",
            "reasoning": "SMALL cap, never analyzed, tech sector 82% match",
            "confidence": 0.88
        }
    ]
}
```

---

## API Reference Guide

### Analysis Endpoints

#### Start Batch Analysis
```http
POST /api/v2/analysis/batch
Content-Type: application/json

{
    "company_names": ["Microsoft", "Apple", "Tesla"],
    "force_reanalyze": false
}

# OR filter-based

{
    "filters": {
        "market_cap": ["SMALL", "MID"],
        "industry": ["Technology", "SaaS"],
        "sector": ["Information Technology"]
    },
    "limit": 50
}

Response 200:
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "message": "Analysis job started",
    "total_companies": 3
}
```

#### Get Job Status
```http
GET /api/v2/analysis/status/{job_id}

Response 200:
{
    "job_id": "550e8400-...",
    "status": "in_progress",
    "total_companies": 50,
    "completed": 25,
    "failed": 1,
    "skipped": 10,
    "current_company": "Microsoft Corporation",
    "current_step": "Embedding",
    "estimated_time_remaining": 3600,  // seconds
    "total_tokens": 450000,
    "started_at": "2024-11-12T10:00:00Z",
    "errors": [
        {
            "company": "Failed Corp",
            "error": "10-K not found"
        }
    ]
}
```

### Company Endpoints

#### Search Companies in Database
```http
POST /api/v2/companies/search
Content-Type: application/json

{
    "query": "tech",  // Optional: search by name
    "market_cap": ["SMALL"],
    "industry": ["Technology"],
    "limit": 20,
    "offset": 0
}

Response 200:
{
    "companies": [
        {
            "id": 123,
            "cik": "0001234567",
            "name": "Tech Company Inc",
            "ticker": "TECH",
            "market_cap": "SMALL",
            "industry": "Technology",
            "sector": "Information Technology"
        }
    ],
    "count": 1
}
```

#### Search SEC EDGAR
```http
POST /api/v2/companies/search-sec
Content-Type: application/json

{
    "market_cap": ["SMALL", "MID"],
    "industry": ["Technology"],
    "limit": 50
}

Response 200:
{
    "companies": [...],
    "count": 50,
    "source": "sec_edgar",
    "lookup_method": "realtime"  // or "cached"
}
```

### Results Endpoints

#### Get Company Analysis
```http
GET /api/v2/companies/{company_id}/analysis

Response 200:
{
    "analysis": {
        "id": 456,
        "company_id": 123,
        "company_name": "Microsoft Corporation",
        "filing_date": "2024-07-31",
        "status": "completed",
        "time_taken_seconds": 145.5,
        "total_tokens_used": 23450
    },
    "pain_points": [
        {
            "id": 789,
            "theme": "Rising Cloud Infrastructure Costs",
            "rationale": "42% YoY increase in data center expenses...",
            "confidence": 0.87,
            "quotes": ["Operating expenses increased 42%..."],
            "category": "Financial"
        }
    ],
    "product_matches": [
        {
            "id": 101,
            "product_id": "cloud-modernization",
            "product_name": "Cloud Modernization & Management",
            "fit_score": 92,
            "why_fits": "Direct alignment with cost optimization...",
            "evidence": ["Multi-cloud footprint", "Recent expansion"]
        }
    ],
    "pitches": [
        {
            "id": 202,
            "persona": "CFO",
            "subject": "Reduce Your $2.5B Cloud Spend",
            "body": "Dear CFO,\n\nI noticed in Microsoft's latest 10-K...",
            "overall_score": 92
        }
    ]
}
```

#### Get Top Pitches
```http
GET /api/v2/pitches/top?min_score=80&limit=20

Response 200:
{
    "pitches": [
        {
            "id": 202,
            "company_name": "Microsoft Corporation",
            "company_ticker": "MSFT",
            "persona": "CFO",
            "subject": "...",
            "body": "...",
            "overall_score": 92,
            "product_name": "Cloud Modernization",
            "created_at": "2024-11-12T10:30:00Z"
        }
    ],
    "count": 15
}
```

#### Get Metrics
```http
GET /api/v2/metrics/summary

Response 200:
{
    "total_companies_analyzed": 250,
    "total_analyses_run": 275,
    "total_pain_points_found": 3250,
    "total_pitches_generated": 1800,
    "total_processing_time_seconds": 43200,
    "avg_time_per_analysis": 157.1,
    "total_tokens_used": 5875000,
    "success_rate": 0.94,
    "avg_pain_points_per_company": 13.0,
    "avg_matches_per_company": 7.2,
    "estimated_time_saved_hours": 500,
    "top_industries": [
        {"industry": "Technology", "count": 85},
        {"industry": "Healthcare", "count": 42}
    ],
    "top_sectors": [
        {"sector": "Information Technology", "count": 95}
    ]
}
```

### Catalog Endpoints

#### Get Current Catalog
```http
GET /api/v2/catalog/current

Response 200:
{
    "products": [
        {
            "product_id": "cloud-modernization",
            "title": "Cloud Modernization & Management",
            "summary": "...",
            "capabilities": ["cloud strategy", "migration", ...],
            "icp": {
                "industries": ["SaaS", "Technology"],
                "min_emp": 100
            },
            "proof_points": ["50+ migrations", "35% cost reduction"]
        }
    ]
}
```

#### Upload New Catalog
```http
POST /api/v2/catalog/upload
Content-Type: application/json

{
    "text_content": "Product: Cloud Optimizer\nCapabilities: cost reduction...",
    "company_name": "Atidan Technologies",
    "merge_with_existing": false
}

Response 200:
{
    "products_count": 6,
    "message": "Catalog uploaded successfully"
}
```

---

## Deployment & DevOps

### Local Development Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd 10k-insight-agent

# 2. Backend setup
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 3. Frontend setup
cd frontend
npm install
cd ..

# 4. PostgreSQL (Docker)
docker run -d \
  --name postgres-10k \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=tenk_insight \
  -p 5432:5432 \
  postgres:14

# 5. Initialize database
python init_db.py

# 6. Configure settings
cp src/configs/settings.example.yaml src/configs/settings.yaml
# Edit settings.yaml with API keys

# 7. Start backend
uvicorn src.main:app --reload --port 8000

# 8. Start frontend (new terminal)
cd frontend
npm run dev

# Access at:
# Frontend: http://localhost:3000
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Production Deployment (Azure Container Apps)

**Architecture:**
```
┌──────────────────────────────────────────────────┐
│         Azure Container Apps                     │
│  ┌────────────────┐      ┌──────────────────┐  │
│  │   Frontend     │      │    Backend       │  │
│  │   Container    │◄────►│    Container     │  │
│  │   (React)      │      │    (FastAPI)     │  │
│  │   Port: 80     │      │    Port: 8000    │  │
│  └────────────────┘      └──────────────────┘  │
└──────────────────────────────────────────────────┘
                              │
                              ▼
                   ┌──────────────────────┐
                   │  Azure Database for  │
                   │  PostgreSQL          │
                   │  (Flexible Server)   │
                   └──────────────────────┘
```

**Backend Container (Dockerfile):**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY data/ ./data/

# Environment variables (set at runtime)
ENV DATABASE_URL=""
ENV GROQ_API_KEY=""
ENV SEC_USER_AGENT=""
ENV CORS_ORIGINS="*"

# Expose port
EXPOSE 8000

# Start server
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend Container (Dockerfile):**
```dockerfile
FROM node:18-alpine as build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

# Build with placeholder (actual API URL set at runtime)
ENV VITE_API_URL=__VITE_API_URL__
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

# Runtime config injection script
COPY generate-config.sh /docker-entrypoint.d/
RUN chmod +x /docker-entrypoint.d/generate-config.sh

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**Runtime Config Injection:**
```bash
# generate-config.sh
#!/bin/sh
cat > /usr/share/nginx/html/config.js <<EOF
window.__RUNTIME_CONFIG__ = {
  VITE_API_URL: '${VITE_API_URL}'
};
EOF
```

**Azure Container Apps Deployment:**
```bash
# 1. Create resource group
az group create --name rg-10k-insight --location eastus

# 2. Create container registry
az acr create --resource-group rg-10k-insight \
  --name acr10kinsight --sku Basic

# 3. Build and push images
az acr build --registry acr10kinsight \
  --image 10k-backend:v1 \
  --file Dockerfile .

az acr build --registry acr10kinsight \
  --image 10k-frontend:v1 \
  --file frontend/Dockerfile \
  ./frontend

# 4. Create PostgreSQL
az postgres flexible-server create \
  --resource-group rg-10k-insight \
  --name psql-10k-insight \
  --location eastus \
  --admin-user adminuser \
  --admin-password <strong-password> \
  --sku-name Standard_B2s \
  --version 14

# 5. Create Container Apps Environment
az containerapp env create \
  --name env-10k-insight \
  --resource-group rg-10k-insight \
  --location eastus

# 6. Deploy backend
az containerapp create \
  --name backend-10k \
  --resource-group rg-10k-insight \
  --environment env-10k-insight \
  --image acr10kinsight.azurecr.io/10k-backend:v1 \
  --target-port 8000 \
  --ingress external \
  --env-vars \
    DATABASE_URL="postgresql://adminuser:<password>@psql-10k-insight.postgres.database.azure.com/tenk_insight" \
    GROQ_API_KEY="<your-key>" \
    SEC_USER_AGENT="YourCompany support@company.com" \
    CORS_ORIGINS="https://frontend-10k.azurecontainerapps.io"

# 7. Deploy frontend
az containerapp create \
  --name frontend-10k \
  --resource-group rg-10k-insight \
  --environment env-10k-insight \
  --image acr10kinsight.azurecr.io/10k-frontend:v1 \
  --target-port 80 \
  --ingress external \
  --env-vars \
    VITE_API_URL="https://backend-10k.azurecontainerapps.io"
```

**Environment Variables:**

Backend:
```env
DATABASE_URL=postgresql://user:pass@host:5432/dbname
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-...  # Optional
SEC_USER_AGENT=YourName your@email.com
CORS_ORIGINS=https://frontend.example.com
PRIMARY_LLM_PROVIDER=groq
PRIMARY_EMBEDDING_PROVIDER=sentence-transformers
```

Frontend:
```env
VITE_API_URL=https://backend.example.com
```

### Docker Compose (Alternative)

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: tenk_insight
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/tenk_insight
      GROQ_API_KEY: ${GROQ_API_KEY}
      SEC_USER_AGENT: ${SEC_USER_AGENT}
      CORS_ORIGINS: http://localhost:3000
    depends_on:
      - postgres
    volumes:
      - ./data:/app/data
      - ./src:/app/src

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    environment:
      VITE_API_URL: http://localhost:8000
    depends_on:
      - backend

volumes:
  postgres_data:
```

---

## Configuration & Setup

### settings.yaml (Complete Example)

```yaml
# LLM Configuration
llm:
  primary_provider: "groq"
  fallback_providers: ["openai"]
  
  groq:
    model_name: "moonshotai/kimi-k2-instruct-0905"
    temperature: 0.7
    max_tokens: 4096
    api_key_env: "GROQ_API_KEY"
  
  openai:
    model_name: "gpt-4o-mini"
    temperature: 0.7
    max_tokens: 4096
    api_key_env: "OPENAI_API_KEY"
  
  azure:
    api_version: "2024-02-15-preview"
    azure_endpoint: "https://your-resource.openai.azure.com/"
    deployment_name: "gpt-4"
    api_key_env: "AZURE_OPENAI_API_KEY"

# Embedding Configuration
embedding:
  primary_provider: "sentence-transformers"
  fallback_providers: []
  
  sentence_transformers:
    model_name: "all-mpnet-base-v2"
    device: "cpu"  # or "cuda"
  
  openai:
    model_name: "text-embedding-3-large"
    api_key_env: "OPENAI_API_KEY"
  
  cohere:
    model_name: "embed-english-v3.0"
    api_key_env: "COHERE_API_KEY"

# SEC Configuration
sec_user_agent: "YourName your@email.com"  # REQUIRED by SEC

# Database
database_url: "postgresql://postgres:postgres@localhost:5432/tenk_insight"

# Storage Paths
vector_store_dir: "src/stores/vector"
catalog_store_dir: "src/stores/catalog"
filings_dir: "data/filings"

# Processing Settings
max_chunk_size: 1000
chunk_overlap: 200
top_k_chunks: 10

# Autonomous Scheduler
scheduler:
  enabled: false  # Enable via API
  cron_schedule: "0 2 * * *"  # Daily at 2 AM
  batch_size: 50
  market_cap_priority: ["SMALL", "MID", "LARGE", "MEGA"]
  analysis_interval_days: 90
  use_llm_agent: true
```

### Product Catalog Format

**products.json Structure:**
```json
[
  {
    "product_id": "unique-id",
    "title": "Product Name",
    "summary": "One-line description",
    "capabilities": [
      "capability 1",
      "capability 2"
    ],
    "icp": {
      "industries": ["Industry 1", "Industry 2"],
      "min_emp": 100,
      "company_size": "100-5000 employees"
    },
    "proof_points": [
      "Delivered X for Y companies",
      "Achieved Z% improvement"
    ],
    "target_personas": ["CTO", "CFO", "VP Engineering"]
  }
]
```

**Tips for Good Product Definitions:**
- **Capabilities:** Use action verbs (e.g., "automated rightsizing", not "rightsizing")
- **ICP Industries:** Match SEC industry names for better filtering
- **Proof Points:** Include metrics (percentages, numbers, timeframes)
- **Personas:** Be specific (not just "Executive")

---

## Monitoring & Troubleshooting

### Health Checks

```bash
# API Health
curl http://localhost:8000/health

# Database Connection
python -c "from src.database.database import get_db; next(get_db()); print('✅ DB OK')"

# LLM Provider
python -c "from src.utils.llm_factory import get_factory; get_factory().create_llm_manager(); print('✅ LLM OK')"

# Vector Store
python -c "from src.stores.vector import get_vector_store; get_vector_store('test'); print('✅ ChromaDB OK')"
```

### Common Issues

#### 1. Frontend Can't Connect to API

**Symptom:** API calls fail with CORS error or network error

**Diagnosis:**
```bash
# Check API is running
curl http://localhost:8000/health

# Check CORS configuration
grep CORS_ORIGINS .env

# Check frontend config
cat frontend/public/config.js
```

**Fix:**
```bash
# Update CORS in backend
export CORS_ORIGINS=http://localhost:3000

# Rebuild frontend with correct API URL
cd frontend
export VITE_API_URL=http://localhost:8000
npm run build
```

#### 2. Jobs Stuck at 0%

**Symptom:** Analysis job shows "in_progress" but never advances

**Diagnosis:**
```bash
# Check backend logs
# Look for errors like:
# - "API key not found"
# - "Connection refused"
# - "ChromaDB error"

# Check database
psql tenk_insight -c "SELECT * FROM analysis_jobs WHERE status='in_progress';"
```

**Fix:**
```bash
# Verify API keys
python -c "import os; print(os.getenv('GROQ_API_KEY', 'NOT SET'))"

# Reset stuck jobs
psql tenk_insight -c "UPDATE analysis_jobs SET status='failed' WHERE status='in_progress' AND started_at < NOW() - INTERVAL '1 hour';"

# Restart backend
```

#### 3. ChromaDB Corruption

**Symptom:** "PanicException" or "range start index out of range"

**Fix:**
```bash
# Automatic recovery (built-in)
# The embedder detects corruption and recreates collection

# Manual reset if needed
python reset_chromadb.py --vector

# Or delete and recreate
rm -rf src/stores/vector/*
# Embeddings will be recreated on next analysis
```

#### 4. High Token Usage

**Symptom:** Unexpectedly high token consumption

**Diagnosis:**
```sql
-- Check token usage by analysis
SELECT 
    c.name,
    a.total_tokens_used,
    a.time_taken_seconds,
    COUNT(pp.id) as pain_points
FROM analyses a
JOIN companies c ON a.company_id = c.id
LEFT JOIN pain_points pp ON pp.analysis_id = a.id
WHERE a.status = 'COMPLETED'
GROUP BY c.name, a.total_tokens_used, a.time_taken_seconds
ORDER BY a.total_tokens_used DESC
LIMIT 10;
```

**Fix:**
- Reduce `top_k_chunks` in settings.yaml (default: 10)
- Use smaller LLM model (e.g., "llama-3.1-8b-instant" instead of Kimi)
- Implement stricter caching

#### 5. Scheduler Not Running

**Symptom:** Autonomous runs don't trigger

**Diagnosis:**
```bash
# Check scheduler status
curl http://localhost:8000/api/scheduler/status

# Check logs for scheduler errors
grep "scheduler" logs/app.log
```

**Fix:**
```bash
# Activate scheduler
curl -X PUT http://localhost:8000/api/scheduler/config \
  -H "Content-Type: application/json" \
  -d '{"is_active": true, "cron_schedule": "0 2 * * *"}'

# Trigger manual run for testing
curl -X POST http://localhost:8000/api/scheduler/trigger
```

### Logging

**Backend Logs:**
```python
# src/utils/logging.py configures logging

# Levels: DEBUG, INFO, WARNING, ERROR
# Default: INFO

# View logs
tail -f logs/app.log

# Filter for errors
grep ERROR logs/app.log

# Filter for specific company
grep "Microsoft" logs/app.log
```

**Database Queries for Debugging:**
```sql
-- Recent failures
SELECT c.name, a.error_message, a.created_at
FROM analyses a
JOIN companies c ON a.company_id = c.id
WHERE a.status = 'FAILED'
ORDER BY a.created_at DESC
LIMIT 10;

-- Top performers
SELECT 
    c.name,
    AVG(pm.fit_score) as avg_score,
    COUNT(pm.id) as match_count
FROM product_matches pm
JOIN analyses a ON pm.analysis_id = a.id
JOIN companies c ON a.company_id = c.id
GROUP BY c.name
HAVING AVG(pm.fit_score) > 80
ORDER BY avg_score DESC;

-- Scheduler insights
SELECT 
    sr.run_id,
    sr.companies_selected,
    sr.companies_analyzed,
    sr.total_tokens_used,
    sr.started_at
FROM scheduler_runs sr
ORDER BY sr.started_at DESC
LIMIT 5;
```

---

## Presentation Walkthrough Script

### Opening (2 minutes)

**"Good morning everyone! Today I'm going to walk you through the 10K Insight Agent - an AI-powered platform we've built to automate SEC filing analysis and sales opportunity discovery."**

**Key Points to Hit:**
- What it does in one sentence
- Why it matters (time savings)
- Who it's for (sales teams, BD)

**Show:** Dashboard page with metrics

---

### Problem Statement (3 minutes)

**"Let me paint a picture of the problem this solves..."**

**Traditional Process:**
1. Sales rep wants to understand if Microsoft needs our cloud optimization product
2. Downloads Microsoft's 10-K (140 pages)
3. Spends 2-3 hours reading through risk factors, MD&A
4. Takes notes on challenges
5. Manually maps to product capabilities
6. Crafts email pitch
7. **Total: 4-6 hours per company**

**Our Solution:**
1. Add "Microsoft" to the queue
2. AI analyzes entire 10-K in 2-3 minutes
3. View results: pain points, matches, ready-made pitch
4. **Total: 2-3 minutes** (96% time savings)

**Show:** Side-by-side comparison slide or demo

---

### Architecture Overview (5 minutes)

**"Let me show you how this works under the hood..."**

**Component Walkthrough:**

1. **Frontend (React + TypeScript)**
   - "Modern web UI, built with React"
   - "5 main pages: Dashboard, Analysis Queue, Company Insights, Top Pitches, Metrics"
   - "Real-time progress tracking with 2-second polling"
   
2. **Backend (FastAPI + Python)**
   - "Async API server handling batch jobs"
   - "PostgreSQL for data persistence"
   - "LangGraph for AI workflow orchestration"

3. **AI Engine (LangGraph DAG)**
   - "4-node workflow pipeline"
   - "Company Resolver → SEC Fetcher → Embedder → Solution Matcher"
   - "Uses Groq for free, fast LLM inference"

4. **Data Flow**
   - "User submits companies → Job created → Background processing"
   - "Each company: Download 10-K → Embed text → Extract pains → Match products → Generate pitch"
   - "Results saved to database → User views in UI"

**Show:** Architecture diagram (from Part 1)

---

### Live Demo (15 minutes)

#### Demo Flow

**1. Dashboard (1 min)**
```
"Here's the dashboard - shows high-level metrics."
- Point to: Total companies analyzed, recent analyses
- "We've analyzed 250 companies so far"
```

**2. Analysis Queue - Manual Submission (3 min)**
```
"Let me show you how to start a batch analysis..."

Click: Analysis Queue → Company List tab
Type in companies:
  Tesla
  Netflix
  Shopify

Check: "Force re-analyze" (explain caching)
Click: "Start Analysis"

"Notice we got a job ID immediately - this runs in the background"
Switch to: Active Jobs tab
"Here's the live progress - updates every 2 seconds"
- Point to: Progress bar, current company, ETA
- "Currently analyzing Tesla, extracting pain points"
```

**3. Analysis Queue - Filter Search (3 min)**
```
"You can also search by market cap and industry..."

Click: Filter Search tab
Select: 
  - Market Cap: SMALL, MID
  - Industry: Technology
  - Limit: 20

Click: "Preview Companies from SEC"
Wait ~10 seconds

"See, it found 20 tech companies from SEC's database"
"Notice the real-time market cap lookup - this is live data"

Click: "Analyze 20 Companies"
"This kicks off a batch job for all of them"
```

**4. Company Insights (4 min)**
```
Switch to: Company Insights page
Search: "Tesla"  (or use completed analysis from earlier)
Click: View button

"Here's the full analysis for Tesla..."

Pain Points section:
"The AI extracted 12 pain points with confidence scores"
- Point to a high-confidence pain (e.g., 0.87)
- Read the theme: "Manufacturing Scaling Challenges"
- Show quotes from 10-K
- "These are actual quotes from their risk factors section"

Product Matches section:
"Automatically matched to our products based on fit score"
- Point to top match (e.g., 92/100)
- "Cloud Modernization scores 92 because..."
- Read "why_fits" reasoning
- Show evidence points

Pitch section:
"Ready-made sales pitch targeted to the CFO"
- Read subject line
- Scan body (highlight quote from 10-K)
- "Notice it references their specific challenges with evidence"
```

**5. Top Pitches (2 min)**
```
Click: Top Pitches
"This shows best matches across ALL companies"

Filter: Minimum Score = 85
"Only show high-confidence opportunities"

Click on a pitch:
"Each pitch includes the company, persona, score, and full email"
"You could copy-paste this and send it today"
```

**6. Metrics Dashboard (2 min)**
```
Click: Metrics
"Analytics on the entire system"

Point to:
- Total companies analyzed: 250
- Total pain points: 3,250 (avg 13 per company)
- Time saved: 500 hours
- Token usage chart
- Success rate: 94%

"This is how we track ROI and performance"
```

---

### Autonomous Scheduler (5 minutes)

**"Now here's where it gets really cool - the autonomous scheduler..."**

**Explain the Concept:**
```
"In v3.0, we added an AI agent that decides which companies to analyze automatically."

"Instead of you manually selecting companies every day, 
the system runs on a schedule - say, every day at 2 AM - 
and an LLM decides which companies are worth analyzing based on:
- Market cap (prioritizes small caps)
- Past results (learns what works)
- Analysis history (avoids over-analyzing)
- Industry trends (focuses on high-match sectors)"
```

**Show the Flow:**
```
1. Cron trigger (2 AM daily)
2. LLM gets list of candidates from SEC
3. LLM reviews memory: "Tech small caps = 82% avg match score"
4. LLM selects 50 companies with reasoning for each
5. Batch job runs automatically
6. Results saved, memory updated
7. Rinse and repeat next day
```

**API Demo (if time):**
```bash
# Show current status
curl http://localhost:8000/api/scheduler/status

# Show a past run
curl http://localhost:8000/api/scheduler/runs?limit=1

# Show LLM reasoning
# Point to: "Focusing on tech small caps because historical data shows 82% match rate"
```

**Key Value:**
```
"This means the system works FOR you, not WITH you"
"It's continuously discovering opportunities while you sleep"
"By the time you get to the office, you have 50 new analysis waiting"
```

---

### Technical Deep Dive (5 minutes - for technical audience)

**Database Schema:**
```sql
-- Show key tables
companies          (CIK, ticker, industry, market_cap)
analyses           (filing_date, status, metrics)
pain_points        (theme, confidence, quotes)
product_matches    (fit_score, evidence)
pitches            (persona, subject, body)

-- Scheduler tables
scheduler_runs     (LLM reasoning, companies selected)
company_priorities (priority score, last analyzed)
scheduler_memory   (learned patterns)
```

**LangGraph Workflow:**
```python
# Show dag.py structure
StateGraph with 4 nodes:
1. company_resolver  (SEC API)
2. sec_fetcher       (Download 10-K)
3. embedder          (ChromaDB vectors)
4. solution_matcher  (5-node subgraph)
   - problem_miner
   - product_retriever
   - fit_scorer
   - objection_handler
   - pitch_writer
```

**LLM Integration:**
```python
# Centralized factory pattern
from src.utils.llm_factory import get_factory

factory = get_factory()
llm = factory.create_llm_manager()

# Multi-provider with fallbacks
primary: Groq (fast, free)
fallback: OpenAI (reliable)
```

**Caching Strategy:**
```python
# Check before analyzing
if not force_reanalyze:
    latest = get_latest_analysis(company_id)
    if latest.catalog_hash == current_hash:
        if pain_count > 0:
            skip()  # Already done
```

---

### Key Metrics & ROI (3 minutes)

**Time Savings:**
```
Manual: 4-6 hours per company
Automated: 2-3 minutes per company
Savings: 96% time reduction

Example batch (50 companies):
- Manual: 200-300 hours (5-7.5 weeks of work)
- Automated: 2 hours
- Time saved: 198-298 hours per batch
```

**Cost Analysis:**
```
LLM Costs (using Groq - FREE tier):
- Average: 23,000 tokens per company
- 50 companies = 1.15M tokens
- Cost: $0 (free tier)

Alternative with OpenAI:
- GPT-4o-mini: $0.15 per 1M input tokens
- 50 companies = $3.45
- Still very economical
```

**Accuracy:**
```
Success rate: 94% (235/250 companies)
Average pain points: 13 per company
Average match score: 78/100
High-value matches (>80): 62% of all matches
```

---

### Common Questions & Answers

**Q: How accurate is the AI extraction?**
```
A: "The AI has a 94% success rate. Each pain point includes:
- Confidence score (0-1)
- Actual quotes from the 10-K as evidence
- Section references

We've found confidence scores above 0.75 are highly reliable."
```

**Q: What if our product catalog changes?**
```
A: "We track catalog versions with a hash. When products.json changes:
- Companies are automatically flagged for re-analysis
- Or you can force re-analyze via the checkbox
- The system ensures matches are always based on current products"
```

**Q: Can we customize the AI prompts?**
```
A: "Yes! All prompts are in src/knowledge/prompts/
You can customize:
- Pain extraction criteria
- Fit scoring logic
- Pitch tone and style
Just edit the .txt files, no code changes needed"
```

**Q: How do we add more products?**
```
A: "Two ways:
1. Edit src/knowledge/products.json directly
2. Use the Catalog Manager page (upload via UI)

The AI will automatically match new products in the next analysis"
```

**Q: What about data privacy?**
```
A: "All 10-K filings are public SEC documents.
We don't store any proprietary data.
LLM calls go through Groq/OpenAI (GDPR compliant).
Database is local or your Azure instance - you control the data"
```

**Q: Can we analyze 10-Q (quarterly) filings instead?**
```
A: "Currently focused on 10-K (annual reports) because:
- More comprehensive (100-200 pages vs 30-50)
- Annual strategic overview
- More pain points disclosed

But the code is extensible - we could add 10-Q support in v4.0"
```

---

### Future Roadmap (2 minutes)

**Planned Features:**

**Q1 2025:**
- [ ] WebSocket for true real-time updates (no polling)
- [ ] User authentication & multi-tenancy
- [ ] Email pitch templates with SendGrid integration

**Q2 2025:**
- [ ] Export to CRM (Salesforce, HubSpot)
- [ ] Historical trend analysis (compare 10-Ks year-over-year)
- [ ] Competitor analysis mode

**Q3 2025:**
- [ ] 10-Q quarterly filing support
- [ ] Advanced filtering (revenue, growth rate, geographic presence)
- [ ] Custom AI models fine-tuned on your product catalog

**Ideas for Discussion:**
- Mobile app?
- Slack/Teams notifications?
- AI-powered email sending?
- Integration with your existing sales tools?

---

### Closing (2 minutes)

**"To summarize..."**

**What We Built:**
- AI-powered platform that analyzes SEC 10-K filings
- Extracts pain points, matches products, generates pitches
- 96% time savings vs manual research
- Autonomous operation with scheduler

**Why It Matters:**
- Sales teams get ready-made, evidence-based pitches
- BD teams discover opportunities at scale
- Everyone saves 100+ hours per month

**What's Next:**
- Start using it for target accounts
- Customize product catalog for your offerings
- Enable autonomous scheduler for continuous operation
- Provide feedback for v4.0 features

**Questions?**

---

## Demo Checklist

Before your presentation, ensure:

- [ ] Backend running (`uvicorn src.main:app --reload`)
- [ ] Frontend running (`npm run dev` in frontend/)
- [ ] Database has sample data (run a few analyses beforehand)
- [ ] At least one completed analysis to show results
- [ ] API docs available (`http://localhost:8000/docs`)
- [ ] Architecture diagram ready
- [ ] `products.json` is populated and relevant
- [ ] Prepare 2-3 company names for live demo
- [ ] Test filter search before presenting
- [ ] Have backup screenshots in case of technical issues

---

## Talking Points Summary (Cheat Sheet)

### Elevator Pitch (30 seconds)
"10K Insight Agent is an AI platform that automatically analyzes companies' SEC filings, extracts their business challenges, and matches them to your product catalog - generating ready-to-send sales pitches with evidence. It reduces 4-6 hours of manual research to 2-3 minutes per company."

### Key Differentiators
1. **Evidence-Based**: Every pain point has quotes from actual filings
2. **Autonomous**: Runs 24/7 with AI-powered company selection
3. **Smart Caching**: Avoids redundant work (60-80% efficiency)
4. **Production-Ready**: Built with modern stack (React, FastAPI, PostgreSQL)
5. **Free to Run**: Uses Groq's free tier for LLM inference

### Technical Highlights
- **LangGraph**: Orchestrates 4-node AI workflow pipeline
- **Multi-Provider LLM**: Groq primary, OpenAI fallback
- **Vector Search**: ChromaDB for semantic document search
- **Real-Time UI**: 2-second polling with progress bars
- **Scheduler Memory**: LLM learns patterns over time

### ROI Numbers to Remember
- **Time Savings**: 96% (4-6 hours → 2-3 minutes)
- **Batch Capacity**: 50 companies in 2 hours
- **Success Rate**: 94% completion rate
- **Cost**: $0 with Groq free tier
- **Pain Points**: Average 13 per company
- **Match Accuracy**: 78/100 average fit score

### Common Objections
**"Can't we just read the 10-Ks manually?"**
→ "Sure, but at 50 companies × 4 hours = 200 hours per batch. This does it in 2 hours."

**"What if the AI makes mistakes?"**
→ "Every extraction includes confidence scores and citations. You validate before sending."

**"Is this secure?"**
→ "All data is public SEC filings. No proprietary information. You control the database."

**"How much does it cost?"**
→ "Using Groq's free tier: $0. With OpenAI: ~$3-5 per 50 companies."

---

**End of Part 2**

**You now have:**
✅ Part 1: Technical architecture deep dive  
✅ Part 2: Deployment, operations, and presentation guide

**Ready to crush that KT session! 💪**
