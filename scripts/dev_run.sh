#!/bin/bash
# Development runner script for Unix/Mac
echo "Starting 10K Insight Agent API..."
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
