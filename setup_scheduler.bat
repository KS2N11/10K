@echo off
echo ========================================
echo 10K Insight Agent v3.0 Setup
echo Autonomous Scheduler Installation
echo ========================================
echo.

echo Installing APScheduler dependency...
pip install apscheduler>=3.10.4

echo.
echo Running database migration...
python migrate_scheduler.py

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Start the application: start_react.bat
echo 2. Check scheduler status: http://localhost:8000/api/scheduler/status
echo 3. Read documentation: AUTONOMOUS_SCHEDULER.md
echo.
pause
