#!/bin/bash
# Quick setup script for 10K Insight Agent (Unix/Mac)

echo "========================================"
echo "10K Insight Agent - Quick Setup"
echo "========================================"
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "[ERROR] uv package manager not found!"
    echo "Please install uv first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "[1/5] Installing dependencies..."
uv sync
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies"
    exit 1
fi

echo ""
echo "[2/5] Setting up configuration files..."

if [ ! -f .env ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    echo "IMPORTANT: Please edit .env and add your OPENAI_API_KEY and SEC_USER_AGENT"
else
    echo ".env already exists, skipping..."
fi

if [ ! -f src/configs/settings.yaml ]; then
    echo "Creating settings.yaml from template..."
    cp src/configs/settings.example.yaml src/configs/settings.yaml
    echo "IMPORTANT: Please edit src/configs/settings.yaml with your configuration"
else
    echo "settings.yaml already exists, skipping..."
fi

echo ""
echo "[3/5] Creating required directories..."
mkdir -p data/filings
mkdir -p src/stores/vector
mkdir -p src/stores/catalog

echo ""
echo "[4/5] Running health check..."
echo "Starting API server for test..."
uv run uvicorn src.main:app --port 8000 &
API_PID=$!
sleep 5

# Try to check health
if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo "[SUCCESS] API server is responding!"
else
    echo "[WARNING] Could not verify API server"
fi

# Stop the test server
kill $API_PID > /dev/null 2>&1

echo ""
echo "[5/5] Setup complete!"
echo ""
echo "========================================"
echo "Next Steps:"
echo "========================================"
echo "1. Edit .env and add your OPENAI_API_KEY"
echo "2. Edit .env and add your SEC_USER_AGENT (email required)"
echo "3. Edit src/configs/settings.yaml with your preferences"
echo "4. Run the API: bash scripts/dev_run.sh"
echo "5. Run the UI: uv run streamlit run streamlit_app.py"
echo ""
echo "For detailed instructions, see SETUP_GUIDE.md"
echo "========================================"
echo ""
