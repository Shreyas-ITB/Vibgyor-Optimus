@echo off
REM ============================================================================
REM OPTIMUS AI Assistant - Quick Start Script (Windows)
REM ============================================================================

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║        OPTIMUS AI Assistant - Quick Start                ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo [STEP 1] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        echo Please ensure Python 3.10+ is installed
        pause
        exit /b 1
    )
)

echo [STEP 2] Activating virtual environment...
call venv\Scripts\activate.bat

echo [STEP 3] Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║                Prerequisites Check                        ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

echo Checking SQL Server connection...
python -c "import pyodbc; print('✓ pyodbc installed')" 2>nul || (
    echo ✗ pyodbc not working properly
    echo Please ensure ODBC Driver 18 for SQL Server is installed
)

echo Checking Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo ✗ Ollama not running
    echo Please start Ollama first: ollama serve
) else (
    echo ✓ Ollama is running
)

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║              Starting Services                            ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

echo Starting MCP Server on port 8001...
start "MCP Server" cmd /k "venv\Scripts\activate.bat && python server.py"

timeout /t 3 >nul

echo Starting OPTIMUS API on port 8000...
start "OPTIMUS API" cmd /k "venv\Scripts\activate.bat && python optimus_api.py"

timeout /t 3 >nul

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║              Services Started!                            ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
echo MCP Server:    http://localhost:8001
echo OPTIMUS API:   http://localhost:8000
echo.
echo Next steps:
echo 1. Start OpenWebUI with Docker:
echo    docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui ghcr.io/open-webui/open-webui:main
echo.
echo 2. Open OpenWebUI: http://localhost:3000
echo.
echo 3. Configure connection in OpenWebUI:
echo    Settings → Admin Panel → Connections → OpenAI
echo    Base URL: http://host.docker.internal:8000/v1
echo    API Key: sk-dummy
echo.
pause
