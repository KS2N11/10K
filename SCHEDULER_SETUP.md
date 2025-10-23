# Quick Setup Guide - Autonomous Scheduler

## Prerequisites

✅ Existing 10K Insight Agent installation  
✅ Python 3.10+ with dependencies installed  
✅ PostgreSQL running  
✅ Groq API key configured  

---

## Installation Steps

### 1. Install New Dependency

```bash
pip install apscheduler>=3.10.4
```

Or update all dependencies:
```bash
pip install -e .
```

### 2. Run Database Migration

```bash
python migrate_scheduler.py
```

This creates:
- `scheduler_config` - Scheduler configuration
- `scheduler_runs` - History of all runs
- `company_priorities` - Memory of company analysis history
- `scheduler_memory` - Learned patterns and strategies
- `scheduler_decisions` - LLM reasoning for each decision

### 3. Start Application

```bash
uvicorn src.main:app --reload --port 8000
```

The scheduler starts **automatically** but in **PAUSED** mode by default.

### 4. Enable Scheduler

#### Option A: Via API (Recommended)

```bash
curl -X PUT http://localhost:8000/api/scheduler/config \
  -H "Content-Type: application/json" \
  -d '{
    "is_active": true,
    "cron_schedule": "0 2 * * *",
    "market_cap_priority": ["SMALL", "MID", "LARGE", "MEGA"],
    "batch_size": 10,
    "analysis_interval_days": 90,
    "max_companies_per_run": 50
  }'
```

#### Option B: Via Python

```python
import requests

response = requests.put(
    "http://localhost:8000/api/scheduler/config",
    json={
        "is_active": True,
        "cron_schedule": "0 2 * * *"  # Daily at 2 AM
    }
)
print(response.json())
```

### 5. Test with Manual Trigger

```bash
# Trigger immediate test run
curl -X POST http://localhost:8000/api/scheduler/trigger

# Check status
curl http://localhost:8000/api/scheduler/status
```

---

## Verify Installation

### Check Scheduler Status

```bash
curl http://localhost:8000/api/scheduler/status
```

Expected output:
```json
{
  "is_running": true,
  "is_active": true,
  "cron_schedule": "0 2 * * *",
  "next_run_at": "2025-10-24T02:00:00Z",
  "config": {
    "market_cap_priority": ["SMALL", "MID", "LARGE", "MEGA"],
    "use_llm_agent": true,
    "max_companies_per_run": 50
  }
}
```

### Check Recent Runs

```bash
curl http://localhost:8000/api/scheduler/runs?limit=5
```

### View Company Priorities

```bash
curl http://localhost:8000/api/scheduler/priorities?limit=10
```

---

## Configuration Options

### Cron Schedule Examples

```bash
# Daily at 2 AM
"0 2 * * *"

# Every 6 hours
"0 */6 * * *"

# Weekly on Sunday at midnight
"0 0 * * 0"

# Monthly on the 1st
"0 0 1 * *"

# Every 30 minutes (testing)
"*/30 * * * *"
```

### Market Cap Priority

Default order (RECOMMENDED):
```json
["SMALL", "MID", "LARGE", "MEGA"]
```

Focus on small caps only:
```json
["SMALL"]
```

Skip mega caps:
```json
["SMALL", "MID", "LARGE"]
```

### Industry Filters

Prioritize specific industries:
```json
{
  "prioritize_industries": ["Technology", "Healthcare", "Software"]
}
```

Exclude industries:
```json
{
  "exclude_industries": ["Real Estate", "Financial Services"]
}
```

---

## Common Use Cases

### Use Case 1: Focus on Small-Cap Tech Companies

```bash
curl -X PUT http://localhost:8000/api/scheduler/config \
  -H "Content-Type: application/json" \
  -d '{
    "is_active": true,
    "market_cap_priority": ["SMALL"],
    "prioritize_industries": ["Technology", "Software"],
    "analysis_interval_days": 60,
    "max_companies_per_run": 30
  }'
```

### Use Case 2: Daily Healthcare Analysis

```bash
curl -X PUT http://localhost:8000/api/scheduler/config \
  -H "Content-Type: application/json" \
  -d '{
    "is_active": true,
    "cron_schedule": "0 1 * * *",
    "prioritize_industries": ["Healthcare", "Biotechnology"],
    "market_cap_priority": ["SMALL", "MID"],
    "max_companies_per_run": 25
  }'
```

### Use Case 3: Weekly Full Scan

```bash
curl -X PUT http://localhost:8000/api/scheduler/config \
  -H "Content-Type: application/json" \
  -d '{
    "is_active": true,
    "cron_schedule": "0 0 * * 0",
    "market_cap_priority": ["SMALL", "MID", "LARGE", "MEGA"],
    "max_companies_per_run": 100,
    "analysis_interval_days": 180
  }'
```

---

## Monitoring

### Real-time Status

```bash
# Watch scheduler status
watch -n 5 'curl -s http://localhost:8000/api/scheduler/status | jq'
```

### View Logs

```bash
# Application logs
tail -f logs/app.log

# Filter for scheduler events
tail -f logs/app.log | grep "scheduler"
```

### Check LLM Decisions

```bash
# Recent decisions with reasoning
curl http://localhost:8000/api/scheduler/decisions?limit=20 | jq
```

---

## Troubleshooting

### Scheduler Not Running

```bash
# Check if FastAPI app is running
curl http://localhost:8000/docs

# Check scheduler status
curl http://localhost:8000/api/scheduler/status

# Restart scheduler
curl -X POST http://localhost:8000/api/scheduler/stop
curl -X POST http://localhost:8000/api/scheduler/start
```

### No Companies Selected

```bash
# Check company priorities
curl http://localhost:8000/api/scheduler/priorities

# Update priorities manually
curl -X POST http://localhost:8000/api/scheduler/priorities/update

# View available companies
curl -X POST http://localhost:8000/api/v2/companies/search-sec \
  -H "Content-Type: application/json" \
  -d '{"market_cap": ["SMALL"], "limit": 20}'
```

### LLM Not Working

```bash
# Disable LLM, use rule-based selection
curl -X PUT http://localhost:8000/api/scheduler/config \
  -H "Content-Type: application/json" \
  -d '{"use_llm_agent": false}'

# Check Groq API key in settings.yaml
cat src/configs/settings.yaml | grep groq_api_key
```

---

## Next Steps

1. ✅ **Monitor First Run**: Watch logs and check `/api/scheduler/runs`
2. ✅ **Review Decisions**: Check `/api/scheduler/decisions` for LLM reasoning
3. ✅ **Tune Configuration**: Adjust cron schedule, batch size, intervals
4. ✅ **Set Up Alerts**: Configure notifications for failures (future feature)
5. ✅ **Scale Up**: Increase `max_companies_per_run` once stable

---

## Support

📚 **Full Documentation**: [AUTONOMOUS_SCHEDULER.md](AUTONOMOUS_SCHEDULER.md)  
🔍 **API Reference**: http://localhost:8000/docs  
📊 **Scheduler Status**: http://localhost:8000/api/scheduler/status  

---

## Summary

You now have a **fully autonomous 10K analysis system** that:
- ✅ Runs continuously without manual intervention
- ✅ Intelligently selects companies based on business value
- ✅ Prioritizes SMALL → MID → LARGE → MEGA caps
- ✅ Remembers past analyses to avoid duplicates
- ✅ Learns and improves over time
- ✅ Provides full transparency with LLM reasoning

**The system is now working 24/7 for you!** 🚀
