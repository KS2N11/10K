# 10-Q Analysis Microservice

Standalone microservice for analyzing quarterly reports (10-Q filings) and generating sales insights.

## Features

- 📥 Fetches latest 10-Q filings from SEC EDGAR
- 🔍 Extracts business pain points using AI
- 🎯 Matches pain points with solutions catalog
- 💡 Generates actionable sales insights
- 🚀 Standalone FastAPI service (deployable separately)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file:

```bash
# SEC EDGAR Configuration (REQUIRED)
SEC_USER_AGENT=YourCompany/1.0 (your.email@example.com)

# Azure OpenAI (Primary LLM)
AZURE_OPENAI_API_KEY=your-azure-key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# Groq (Fallback LLM)
GROQ_API_KEY=your-groq-key

# Primary LLM Provider
PRIMARY_LLM_PROVIDER=azure
MODEL_STRATEGY=fallback
```

### 3. Run the Service

**As API Server:**
```bash
python -m uvicorn src.tenq.app:app --host 0.0.0.0 --port 8001
```

**As CLI Tool:**
```bash
python -m src.tenq.cli "Apple Inc"
```

## API Endpoints

### POST /analyze

Analyze a company's latest 10-Q filing.

**Request:**
```json
{
  "company_name": "Apple Inc"
}
```

**Response:**
```json
{
  "company_name": "Apple Inc",
  "cik": "0000320193",
  "filing_date": "2025-08-01",
  "reporting_date": "2025-06-28",
  "pain_points": [
    {
      "category": "revenue_decline",
      "description": "...",
      "severity": "high",
      "evidence": "...",
      "quarter": "2025-06-28"
    }
  ],
  "matched_solutions": [
    {
      "solution_name": "Cloud Migration & Optimization",
      "solution_category": "Infrastructure & Cloud",
      "value_proposition": "...",
      "relevance_score": 0.8,
      "matching_rationale": "..."
    }
  ],
  "insights": [
    {
      "company_name": "Apple Inc",
      "quarter": "2025-06-28",
      "pain_point_summary": "...",
      "recommended_solution": "Cloud Migration & Optimization",
      "value_proposition": "...",
      "engagement_strategy": "...",
      "priority": "high"
    }
  ]
}
```

### GET /health

Health check endpoint.

## Architecture

```
src/tenq/
├── __init__.py
├── app.py              # FastAPI application
├── cli.py              # Command-line interface
├── dag.py              # LangGraph workflow
├── nodes.py            # Pipeline nodes
├── schemas.py          # Data models
├── fetcher.py          # SEC filing fetcher
└── solutions_catalog.json  # Products/services catalog
```

## Pipeline Flow

1. **Fetch** → Retrieves 10-Q filing from SEC EDGAR
2. **Parse** → Extracts relevant sections
3. **Embed** → Creates vector embeddings
4. **Extract** → Identifies pain points using LLM
5. **Match** → Maps pain points to solutions
6. **Generate** → Creates sales insights

## Deployment

### Docker

```dockerfile
FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["uvicorn", "src.tenq.app:app", "--host", "0.0.0.0", "--port", "8001"]
```

### Environment Variables

- `SEC_USER_AGENT`: Required by SEC (must include email)
- `AZURE_OPENAI_API_KEY`: Azure OpenAI key
- `AZURE_OPENAI_ENDPOINT`: Azure endpoint URL
- `AZURE_OPENAI_DEPLOYMENT`: Model deployment name
- `PRIMARY_LLM_PROVIDER`: LLM provider (azure/groq/openai)
- `MODEL_STRATEGY`: Fallback strategy

## Solutions Catalog

Edit `src/tenq/solutions_catalog.json` to customize the products/services that get matched to pain points.

## License

Proprietary
