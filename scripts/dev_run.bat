@echo off
REM Development runner script for Windows
echo Starting 10K Insight Agent API...

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Run uvicorn
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
