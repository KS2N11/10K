@echo off
REM Quick setup script for 10K Insight Agent (Windows)
echo ========================================
echo 10K Insight Agent - Quick Setup
echo ========================================
echo.

REM Check if uv is installed
where uv >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] uv package manager not found!
    echo Please install uv first:
    echo   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    pause
    exit /b 1
)

echo [1/5] Installing dependencies...
uv sync
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [2/5] Setting up configuration files...

if not exist .env (
    echo Creating .env from template...
    copy .env.example .env
    echo IMPORTANT: Please edit .env and add your OPENAI_API_KEY and SEC_USER_AGENT
) else (
    echo .env already exists, skipping...
)

if not exist src\configs\settings.yaml (
    echo Creating settings.yaml from template...
    copy src\configs\settings.example.yaml src\configs\settings.yaml
    echo IMPORTANT: Please edit src\configs\settings.yaml with your configuration
) else (
    echo settings.yaml already exists, skipping...
)

echo.
echo [3/5] Creating required directories...
if not exist data\filings mkdir data\filings
if not exist src\stores\vector mkdir src\stores\vector
if not exist src\stores\catalog mkdir src\stores\catalog

echo.
echo [4/5] Running health check...
echo Starting API server for test...
start /B uv run uvicorn src.main:app --port 8000
timeout /t 5 /nobreak >nul

REM Try to check health
curl -s http://localhost:8000/ >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] API server is responding!
) else (
    echo [WARNING] Could not verify API server
)

REM Stop the test server
taskkill /F /FI "WINDOWTITLE eq uvicorn*" >nul 2>nul

echo.
echo [5/5] Setup complete!
echo.
echo ========================================
echo Next Steps:
echo ========================================
echo 1. Edit .env and add your OPENAI_API_KEY
echo 2. Edit .env and add your SEC_USER_AGENT (email required)
echo 3. Edit src\configs\settings.yaml with your preferences
echo 4. Run the API: scripts\dev_run.bat
echo 5. Run the UI: uv run streamlit run streamlit_app.py
echo.
echo For detailed instructions, see SETUP_GUIDE.md
echo ========================================
echo.
pause
