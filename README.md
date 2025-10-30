# 10K Insight Agent v3.0 - Autonomous Intelligence System

**AI-powered platform that autonomously analyzes companies' 10-K filings and matches pain points to your product catalog.**

## 🆕 What's New in v3.0: Autonomous Scheduler

The system now runs **completely autonomously** with:
- 🤖 **LLM-Powered Decision Making** - AI agent decides which companies to analyze
- 🧠 **Intelligent Memory** - Remembers past analyses, avoids duplicates, learns patterns
- ⏰ **Cron-Based Scheduling** - Runs automatically (e.g., daily at 2 AM)
- 🎯 **Smart Prioritization** - Focuses on SMALL → MID → LARGE → MEGA caps
- 📊 **Self-Learning** - Gets smarter over time based on results

**See [AUTONOMOUS_SCHEDULER.md](AUTONOMOUS_SCHEDULER.md) for full documentation.**

---

## Complete Solution

- 🎯 **React + TypeScript Frontend** - Modern UI with real-time progress tracking
- ⚡ **FastAPI Backend** - Async API with background job processing
- 🤖 **LangGraph AI Workflow** - Agentic analysis with citations and guardrails
- 🤖 **Autonomous Scheduler** - NEW! Self-operating intelligence system
- 📊 **PostgreSQL Database** - Reliable data persistence with memory system
- 💾 **Smart Caching** - Avoid re-analyzing companies unnecessarily

---

## Features

### ✨ Analysis Capabilities
- **Company Resolution**: Automatic company name lookup via SEC EDGAR
- **10-K Fetching**: Downloads and processes latest SEC filings
- **Pain Point Mining**: AI extracts business challenges with quotes and confidence scores
- **Product Matching**: Maps pain points to your product catalog with fit scores
- **Pitch Generation**: Creates persona-aware sales pitches with evidence
- **Citation Tracking**: Every insight includes source references (Item 1A, page X, etc.)
- **Autonomous Operation**: NEW! Scheduler runs 24/7, intelligently selecting companies to analyze

### 🚀 Modern UI (React)
- **Dashboard**: Real-time metrics and quick actions
- **Analysis Queue**: Batch processing with live progress (updates every 2 seconds)
- **Filter Search**: Find companies by market cap, industry, sector (105+ companies mapped)
- **SEC Preview**: Review companies before analyzing
- **Company Insights**: Detailed analysis results with pain points and matches
- **Top Pitches**: Best product-company matches across entire database
- **Metrics Dashboard**: Token usage, processing time, cache hit rates

### 💡 Recent Improvements (October 2025)
- ✅ **Autonomous Scheduler** (v3.0): LLM-powered continuous operation with memory
- ✅ **Smart Prioritization**: SMALL caps first, then MID, LARGE, MEGA
- ✅ **Intelligent Memory**: Remembers analyses, learns patterns, optimizes decisions
- ✅ **Cron Scheduling**: Configurable schedules (daily, weekly, custom)
- ✅ **Live Progress Tracking**: Real-time updates without manual refresh
- ✅ **Metrics Tracking**: Time and token usage for every analysis
- ✅ **Smart Caching**: Skip already-analyzed companies (60-80% efficiency gain)
- ✅ **Force Re-analyze**: Option to override cache when needed
- ✅ **ETA Display**: Estimated time remaining for active jobs

---

## Quick Start

### Prerequisites
- **Python** 3.9+
- **Node.js** 18+ and npm
- **PostgreSQL** (Docker or local)
- **Groq API Key** (free tier: https://console.groq.com/keys)

### Installation

```bash
# 1. Clone repository
git clone <your-repo-url> 10k-insight-agent
cd 10k-insight-agent

# 2. Install Python dependencies
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Install frontend dependencies
cd frontend
npm install
cd ..

# 4. Configure environment
# Copy settings.example.yaml to settings.yaml
cp src/configs/settings.example.yaml src/configs/settings.yaml

# Edit settings.yaml with your API key:
# groq_api_key: "your-groq-api-key-here"
# sec_user_agent: "YourName your@email.com"

# 5. Start PostgreSQL
scripts/start_postgres.bat  # Windows
# or
scripts/start_postgres.sh   # Linux/Mac

# 6. Initialize database
python init_db.py

# 6. Start application
start_react.bat  # Windows - starts both API and React
# or manually:
# Terminal 1: uvicorn src.main:app --reload --port 8000
# Terminal 2: cd frontend && npm run dev

# 7. (Optional) Enable Autonomous Scheduler
# Via API:
curl -X PUT http://localhost:8000/api/scheduler/config \
  -H "Content-Type: application/json" \
  -d '{"is_active": true, "cron_schedule": "0 2 * * *"}'
# Or manually: see AUTONOMOUS_SCHEDULER.md
```

### Access the Application

- **React UI**: http://localhost:3000
- **API Server**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

---

## Usage

### Analyze Specific Companies
1. Go to **Analysis Queue** → **Company List** tab
2. Enter company names (one per line): `Microsoft`, `Apple`, `Tesla`
3. Optional: Check "Force re-analyze" to bypass cache
4. Click **Start Analysis**
5. Watch live progress in **Active Jobs** tab

### Filter by Market Cap/Industry
1. Go to **Analysis Queue** → **Filter Search** tab
2. Select filters (e.g., MEGA cap + Technology)
3. Click **Preview Companies from SEC**
4. Review results, then **Analyze X Companies**

### View Results
- **Company Insights**: Search for a company, view pain points and matches
- **Top Pitches**: See best fits across all companies, filter by score/product
- **Metrics Dashboard**: Analyze token usage, processing time, trends

---

## Architecture

### Frontend (`frontend/`)
```
src/
├── pages/               # Route components
│   ├── Dashboard.tsx         # Metrics overview
│   ├── AnalysisQueue.tsx     # Job management + live progress
│   ├── CompanyInsights.tsx   # Detailed analysis view
│   ├── TopPitches.tsx        # Best matches
│   └── Metrics.tsx           # Charts and analytics
├── components/
│   ├── common/          # Reusable components (Loading, Error, etc.)
│   └── layout/          # Navigation sidebar
├── services/
│   └── api.ts           # API client with all endpoints
└── App.tsx              # Routes and layout
```

**Tech Stack**: React 18.3, TypeScript 5.2, Vite 5.3, Tailwind CSS 3.4, React Router 6.26

### Backend (`src/`)
```
src/
├── api/
│   └── routes_v2.py          # FastAPI endpoints
├── services/
│   └── batch_analysis.py     # Background job processing + caching
├── database/
│   ├── models.py             # SQLAlchemy models (Company, Analysis, etc.)
│   └── repository.py         # Database queries
├── graph/
│   └── dag.py                # LangGraph workflow orchestration
├── nodes/
│   ├── company_resolver.py   # Resolve company names
│   ├── sec_fetcher.py        # Download 10-K filings
│   ├── embedder.py           # Vector embeddings
│   └── solution_matcher/     # Agentic analysis subgraph
│       ├── problem_miner.py       # Extract pain points
│       ├── product_retriever.py   # Load product catalog
│       ├── fit_scorer.py          # Score product-pain fit
│       ├── objection_handler.py   # Generate objections/rebuttals
│       └── pitch_writer.py        # Create sales pitches
└── utils/
    ├── multi_llm.py          # Multi-provider LLM wrapper (Groq, OpenAI)
    ├── multi_embeddings.py   # Multi-provider embeddings
    ├── sec_api.py            # SEC EDGAR API client
    └── sec_filter.py         # Company filtering by market cap
```

**Tech Stack**: Python 3.9+, FastAPI, SQLAlchemy, PostgreSQL, LangGraph, LangChain, ChromaDB, Groq

### Data Flow

1. **User Submits Request** → React UI → FastAPI endpoint
2. **Job Created** → Background task started with unique job_id
3. **Company Resolution** → SEC EDGAR API lookup
4. **10-K Fetching** → Download and parse HTML filing
5. **Embedding** → Chunk text, create vector embeddings, store in ChromaDB
6. **AI Analysis** → LangGraph DAG runs:
   - Problem Miner: Extract pain points with citations
   - Product Retriever: Load product catalog
   - Fit Scorer: Match products to pains with scores
   - Objection Handler: Generate likely objections + rebuttals
   - Pitch Writer: Create persona-aware pitch
7. **Save to Database** → Store results in PostgreSQL
8. **Progress Updates** → Frontend polls every 2 seconds for status

---

## API Endpoints

### Analysis
- `POST /api/v2/analysis/batch` - Start batch analysis job
- `GET /api/v2/analysis/status/{job_id}` - Get job progress
- `GET /api/v2/analysis` - List all completed analyses
- `GET /api/v2/analysis/{id}` - Get single analysis details

### Companies
- `POST /api/v2/companies/search` - Search companies in database
- `POST /api/v2/companies/search-sec` - Search SEC EDGAR with filters

### Results
- `GET /api/v2/pain-points` - Get all pain points
- `GET /api/v2/pain-points/company/{company_id}` - Pain points for company
- `GET /api/v2/product-matches` - Get all product matches
- `GET /api/v2/product-matches/top` - Top matches with filters
- `GET /api/v2/pitches` - Get all pitches
- `GET /api/v2/pitches/top` - Top pitches with filters

Full API documentation: http://localhost:8000/docs

---

## Configuration

### Product Catalog (`src/knowledge/products.json`)
```json
[
  {
    "product_id": "cloud-optimizer",
    "name": "Cloud Optimizer Pro",
    "summary": "AI-powered cloud cost optimization platform",
    "capabilities": [
      "automated rightsizing",
      "commitment planning",
      "waste detection",
      "multi-cloud support"
    ],
    "target_personas": ["CTO", "VP Engineering", "FinOps Lead"],
    "icp": {
      "industries": ["SaaS", "E-commerce", "FinTech"],
      "company_size": "200-5000 employees",
      "tech_stack": ["AWS", "Azure", "GCP"]
    },
    "proof_points": [
      "Average 18% savings in first 90 days",
      "500+ companies optimized",
      "ROI positive in <30 days"
    ]
  }
]
```

### LLM Provider Configuration (Centralized)

**The system uses a centralized LLM factory** (`src/utils/llm_factory.py`) to manage all LLM and embedding connections. Configure your provider via environment variables or `settings.yaml`.

#### Provider Selection (.env)
```bash
# Select your primary LLM provider (no auto-detection)
PRIMARY_LLM_PROVIDER=groq  # Options: groq, openai, azure

# Select your primary embedding provider
PRIMARY_EMBEDDING_PROVIDER=sentence-transformers  # Options: sentence-transformers, openai, cohere

# API Keys (only provide keys for providers you want to use)
GROQ_API_KEY=your-groq-key-here
OPENAI_API_KEY=your-openai-key-here  # Optional
COHERE_API_KEY=your-cohere-key-here  # Optional
```

**Important**: The system will use the provider you explicitly configure in `PRIMARY_LLM_PROVIDER`. There is no automatic provider switching based on which API keys are present.

#### Advanced Configuration (settings.yaml)
```yaml
# LLM Configuration with fallback support
llm:
  primary_provider: "groq"
  fallback_providers: ["openai"]  # Optional fallbacks if primary fails
  groq:
    model_name: "moonshotai/kimi-k2-instruct-0905"
    temperature: 0.7
    max_tokens: 4096
  openai:
    model_name: "gpt-4o-mini"
    temperature: 0.7
    max_tokens: 4096

# Embedding Configuration
embedding:
  primary_provider: "sentence-transformers"
  fallback_providers: []
  sentence_transformers:
    model_name: "all-mpnet-base-v2"
    device: "cpu"
  openai:
    model_name: "text-embedding-3-large"

# SEC Configuration
sec_user_agent: "YourName your@email.com"  # REQUIRED by SEC

# Database (default Docker setup)
database_url: "postgresql://postgres:postgres@localhost:5432/tenk_insight"

# Storage
vector_store_dir: "src/stores/vector"
catalog_store_dir: "src/stores/catalog"
filings_dir: "data/filings"

# Processing
max_chunk_size: 1000
chunk_overlap: 200
top_k_chunks: 10
```

#### Why Centralized Configuration?

Previously, the system would auto-detect OpenAI API keys and switch providers automatically. This caused confusion:
- ❌ Hard to predict which provider would be used
- ❌ Configuration scattered across multiple files
- ❌ Difficult to test with specific providers

Now with the centralized factory:
- ✅ Single source of truth for all LLM configuration
- ✅ Explicit provider selection via configuration
- ✅ Easy to switch providers without code changes
- ✅ Consistent behavior across the application

---

## Development

### Project Setup
```bash
# Backend development
python -m uvicorn src.main:app --reload --port 8000

# Frontend development  
cd frontend
npm run dev

# Database management
scripts/start_postgres.bat       # Start PostgreSQL
scripts/stop_postgres.bat        # Stop PostgreSQL
python init_db.py                # Initialize/reset database

# Testing
pytest tests/                    # Run all tests
pytest tests/test_sec_fetcher.py # Run specific test
```

### Code Style
- **Backend**: Python 3.9+, Black formatter, type hints
- **Frontend**: TypeScript strict mode, ESLint, Prettier
- **Commits**: Conventional commits (feat:, fix:, docs:, etc.)

### Adding New Features

**Frontend (React)**:
1. Create component in `frontend/src/pages/` or `frontend/src/components/`
2. Add route in `frontend/src/App.tsx`
3. Update API client in `frontend/src/services/api.ts`
4. Test in browser with hot reload

**Backend (API)**:
1. Add model in `src/database/models.py`
2. Add repository method in `src/database/repository.py`
3. Add endpoint in `src/api/routes_v2.py`
4. Test with Swagger UI at http://localhost:8000/docs

**DAG Workflow**:
1. Create node in `src/nodes/your_node.py`
2. Add to DAG in `src/graph/dag.py`
3. Test with `python test_dag.py`

---

## Testing

### Manual Testing
1. **Analysis Flow**: Submit job → Monitor progress → View results
2. **Caching**: Analyze same company twice, verify second run is skipped
3. **Force Re-analyze**: Check checkbox, verify company is re-processed
4. **Metrics**: Complete analysis, check Metrics Dashboard for data

### Automated Testing
```bash
# Run all tests
pytest tests/

# Specific tests
pytest tests/test_company_resolver.py
pytest tests/test_sec_fetcher.py
pytest tests/test_solution_matcher.py
pytest tests/test_embedder.py
```

### API Testing with Postman
Import `10K-Insight-Agent-API.postman_collection.json` into Postman for:
- Pre-configured requests for all endpoints
- Environment variables for localhost
- Example request bodies
- Expected response formats

---

## Performance

### Benchmarks
- **Company Resolution**: ~1-2 seconds
- **10-K Download**: ~3-5 seconds (depends on filing size)
- **Embedding**: ~30-60 seconds (for ~700 chunks)
- **AI Analysis**: ~60-90 seconds (pain mining + matching + pitch)
- **Total per Company**: ~2-3 minutes

### Optimization Tips
1. **Use Caching**: Enable smart caching to skip re-analyzed companies
2. **Batch Processing**: Analyze multiple companies in one job
3. **Groq Free Tier**: Faster than OpenAI, no cost for basic usage
4. **Database Indexes**: Already optimized on company_id, status, filing_date
5. **Vector Store**: ChromaDB is fast for local development

### Scaling
- **Horizontal**: Deploy multiple API instances with shared PostgreSQL
- **Vertical**: Increase worker count, add more RAM for vector operations
- **Queue**: Use Celery/Redis for distributed job processing
- **Cache**: Add Redis for API response caching

---

## Troubleshooting

### Common Issues

**Frontend won't start:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

**API errors on startup:**
- Check `settings.yaml` exists with valid API keys
- Verify PostgreSQL is running: `docker ps`
- Check Python dependencies: `pip install -r requirements.txt`

**Jobs stuck at 0%:**
- Check API server logs for errors
- Verify Groq API key is valid
- Ensure database connection is working
- Look for Python exceptions in terminal

**No metrics showing:**
- Run at least one analysis to completion
- Check database: `SELECT * FROM analyses WHERE status = 'COMPLETED';`
- Verify `time_taken_seconds` and `total_tokens_used` are populated

**Companies being re-analyzed every time:**
- Check logs for "Skipping" messages
- Verify caching logic is enabled (no "Force re-analyze" checked)
- Check `catalog_hash` consistency in database

**ChromaDB Corruption Error** (PanicException, "range start index out of range"):
```bash
# Automatic recovery is built-in, but if issues persist:

# Option 1: Let the system auto-recover (recommended)
# The embedder will automatically detect and fix corruption

# Option 2: Manual reset using CLI tool
python reset_chromadb.py           # Reset all stores
python reset_chromadb.py --vector  # Reset only vector store

# Option 3: Manual reset using batch file
scripts\reset_store.bat  # Windows
scripts/reset_store.sh   # Linux/Mac

# After reset, embeddings will be recreated automatically on next analysis
```

**Note**: ChromaDB corruption usually happens from:
- Improper shutdown (closing terminal instead of Ctrl+C)
- Multiple instances running simultaneously
- Disk space issues during write operations

The system now includes automatic recovery, so most corruption errors will be fixed without manual intervention.

For more troubleshooting, see `QUICK_START.md`.

---

## Documentation

- **QUICK_START.md** - Quick reference guide (start here!)
- **IMPROVEMENTS_COMPLETE.md** - Live progress, metrics, caching features
- **REACT_MIGRATION.md** - Why we migrated from Streamlit
- **REACT_SETUP_GUIDE.md** - Detailed React installation
- **MARKET_CAP_FILTER_FIX.md** - Market cap filtering explanation
- **FILTER_SEARCH_EXPLAINED.md** - SEC integration details
- **API_REFERENCE.md** - Complete API documentation
- **USER_GUIDE.md** - End-user documentation
- **POSTMAN_TESTING_GUIDE.md** - API testing guide

---

## Tech Stack Summary

### Frontend
- **React** 18.3 - UI library
- **TypeScript** 5.2 - Type safety
- **Vite** 5.3 - Build tool & dev server
- **Tailwind CSS** 3.4 - Styling framework
- **React Router** 6.26 - Client-side routing
- **Axios** 1.7 - HTTP client
- **Recharts** 2.12 - Charts & visualizations
- **Lucide React** 0.400 - Icon library

### Backend
- **Python** 3.9+
- **FastAPI** - Web framework
- **SQLAlchemy** - ORM
- **PostgreSQL** - Database
- **LangGraph** - AI workflow orchestration
- **LangChain** - LLM integration
- **ChromaDB** - Vector database
- **Groq** - LLM provider (free tier)
- **BeautifulSoup** - HTML parsing
- **aiohttp** - Async HTTP client

---

## Roadmap

### Completed ✅
- [x] React frontend with 5 pages
- [x] Live progress tracking (2-second updates)
- [x] Metrics tracking (time + tokens)
- [x] Smart caching system
- [x] SEC filter search with preview
- [x] Market cap filtering (105+ companies)
- [x] Batch job processing
- [x] PostgreSQL database
- [x] Complete API with 15+ endpoints

### Planned 🚧
- [ ] WebSocket for true real-time updates
- [ ] User authentication & multi-tenancy
- [ ] Custom product catalog editor
- [ ] Export pitches to CRM (Salesforce, HubSpot)
- [ ] Historical trend analysis
- [ ] Email pitch templates
- [ ] Competitor analysis mode
- [ ] Advanced filtering (revenue, growth, etc.)

---

## Contributing

### Guidelines
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'feat: add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Code Standards
- Follow existing code style (Black for Python, ESLint for TypeScript)
- Add tests for new features
- Update documentation
- Keep commits atomic and well-described

---

## License

[Your License Here]

---

## Support

- **Issues**: GitHub Issues for bugs and feature requests
- **Documentation**: See docs listed above
- **API Docs**: http://localhost:8000/docs when server is running
- **Groq API**: https://console.groq.com/docs

---

## Acknowledgments

- **SEC EDGAR** for providing free access to 10-K filings
- **Groq** for free tier LLM access
- **LangChain/LangGraph** for AI workflow framework
- **React** and **FastAPI** communities

---

**Built with ❤️ for sales teams who want AI-powered insights**

🚀 **Get started now**: See `QUICK_START.md` for installation instructions!
