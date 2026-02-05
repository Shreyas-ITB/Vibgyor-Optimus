#!/bin/bash
# ============================================================================
# OPTIMUS AI Assistant - Quick Start Script (Linux/Mac)
# ============================================================================

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║        OPTIMUS AI Assistant - Quick Start                ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "[STEP 1] Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment"
        echo "Please ensure Python 3.10+ is installed"
        exit 1
    fi
fi

echo "[STEP 2] Activating virtual environment..."
source venv/bin/activate

echo "[STEP 3] Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                Prerequisites Check                        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

echo "Checking SQL Server connection..."
python -c "import pyodbc; print('✓ pyodbc installed')" 2>/dev/null || {
    echo "✗ pyodbc not working properly"
    echo "Please ensure ODBC Driver 18 for SQL Server is installed"
}

echo "Checking Ollama..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✓ Ollama is running"
else
    echo "✗ Ollama not running"
    echo "Please start Ollama first: ollama serve"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              Starting Services                            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

echo "Starting MCP Server on port 8001..."
python server.py &
MCP_PID=$!

sleep 3

echo "Starting OPTIMUS API on port 8000..."
python optimus_api.py &
API_PID=$!

sleep 3

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              Services Started!                            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "MCP Server:    http://localhost:8001 (PID: $MCP_PID)"
echo "OPTIMUS API:   http://localhost:8000 (PID: $API_PID)"
echo ""
echo "Next steps:"
echo "1. Start OpenWebUI with Docker:"
echo "   docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui ghcr.io/open-webui/open-webui:main"
echo ""
echo "2. Open OpenWebUI: http://localhost:3000"
echo ""
echo "3. Configure connection in OpenWebUI:"
echo "   Settings → Admin Panel → Connections → OpenAI"
echo "   Base URL: http://host.docker.internal:8000/v1"
echo "   API Key: sk-dummy"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "kill $MCP_PID $API_PID; exit" INT
wait
