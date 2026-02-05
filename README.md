# 🚀 OPTIMUS AI Assistant - Complete Setup Guide

A powerful AI assistant system with real-time SQL database querying capabilities, featuring MCP (Model Context Protocol) integration with Ollama/OpenAI and OpenWebUI interface.

## 📋 Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the System](#running-the-system)
- [OpenWebUI Setup](#openwebui-setup)
- [Usage Examples](#usage-examples)
- [API Documentation](#api-documentation)
- [Troubleshooting](#troubleshooting)
- [Advanced Configuration](#advanced-configuration)

---

## 🎯 Overview

This system consists of three main components:

1. **MCP Server** (`server.py`) - Provides real-time database query tools via FastMCP
2. **OPTIMUS API** (`optimus_api.py`) - OpenAI-compatible API that integrates MCP with Ollama/OpenAI
3. **OpenWebUI** - Web interface for interacting with the AI assistant

### Key Features

✅ **Real-time Database Querying** - Query SQL Server databases using natural language  
✅ **Multi-Database Support** - Switch between BoltAtom and HRMS_Dev databases  
✅ **File Indexing** - Index and search through SQL scripts and stored procedures  
✅ **Vision Model Support** - Process images with multimodal models  
✅ **Streaming Responses** - Real-time response streaming  
✅ **Tool Calling** - Automatic function execution for database operations  
✅ **OpenAI-Compatible** - Works with any OpenAI-compatible client  

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      OpenWebUI                          │
│                  (Web Interface)                        │
│                 http://localhost:3000                   │
└─────────────────────┬───────────────────────────────────┘
                      │
                      │ HTTP Requests
                      │
┌─────────────────────▼───────────────────────────────────┐
│                  OPTIMUS API                            │
│              (optimus_api.py)                           │
│            http://localhost:8000                        │
│                                                         │
│  • OpenAI-compatible endpoints                         │
│  • Image/file processing                               │
│  • Tool calling orchestration                          │
└─────────────┬──────────────────────┬────────────────────┘
              │                      │
              │                      │
        ┌─────▼──────┐         ┌────▼─────────┐
        │   Ollama   │         │  MCP Server  │
        │   Models   │         │  (server.py) │
        │   :11434   │         │    :8001     │
        └────────────┘         └────┬─────────┘
                                    │
                              ┌─────▼──────────┐
                              │  SQL Server    │
                              │  (MSSQL)       │
                              │  BoltAtom DB   │
                              │  HRMS_Dev DB   │
                              └────────────────┘
```

---

## 📦 Prerequisites

### Required Software

1. **Python 3.10+**
   - Download: https://www.python.org/downloads/

2. **SQL Server** (SQL Server 2019+ or SQL Server Express)
   - Download: https://www.microsoft.com/en-us/sql-server/sql-server-downloads
   - Must have `ODBC Driver 18 for SQL Server` installed

3. **Ollama** (for local LLM inference)
   - Download: https://ollama.ai/download
   - Required models:
     ```bash
     ollama pull ministral-3:8b    # Recommended multimodal model
     ollama pull llama3.1:latest   # Alternative text model
     ollama pull llava:latest      # Vision model
     ```

4. **Docker** (for OpenWebUI)
   - Download: https://www.docker.com/products/docker-desktop

### Optional Software

- **OpenAI API Key** (if using OpenAI instead of Ollama)
- **Git** (for cloning repositories)

---

## 🔧 Installation

### Step 1: Clone or Download the Project

```bash
git clone <your-repo-url>
cd optimus-ai-assistant
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Python Dependencies

Create a `requirements.txt` file:

```txt
# MCP Server Dependencies
fastmcp>=0.4.0
pyodbc>=5.0.0
uvicorn>=0.27.0

# API Dependencies
fastapi>=0.109.0
openai>=1.12.0
ollama>=0.1.6
httpx>=0.26.0
python-multipart>=0.0.9

# Shared Dependencies
pydantic>=2.6.0
```

Install:

```bash
pip install -r requirements.txt
```

### Step 4: Install ODBC Driver (Windows)

Download and install the **ODBC Driver 18 for SQL Server**:
https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

Verify installation:
```bash
# Windows Command Prompt
odbcad32
```

---

## ⚙️ Configuration

### 1. Configure SQL Server Connection

Edit `server.py` (lines 47-53):

```python
conn_str = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=localhost\\SQLEXPRESS;"      # Change to your SQL Server instance
    "DATABASE=BoltAtom;"                  # Your default database
    "Trusted_Connection=yes;"             # Use Windows Authentication
    "Encrypt=optional;"
)
```

**Connection Options:**

- **Windows Authentication** (recommended):
  ```python
  "Trusted_Connection=yes;"
  ```

- **SQL Server Authentication**:
  ```python
  "UID=your_username;"
  "PWD=your_password;"
  ```

- **Remote Server**:
  ```python
  "SERVER=192.168.1.100,1433;"  # IP and port
  ```

### 2. Configure Allowed Databases

Edit `server.py` (line 84):

```python
ALLOWED_DATABASES = {"BoltAtom", "HRMS_Dev", "YourOtherDB"}
```

### 3. Configure MCP Server Port

Edit `server.py` (line 819):

```python
uvicorn.run(
    app,
    host="0.0.0.0",
    port=8001,  # Change if needed
    log_level="info"
)
```

### 4. Configure OPTIMUS API

Edit `optimus_api.py` (line 235 for MCP endpoint):

```python
self.mcp_url = "http://localhost:8001"  # MCP server URL
```

Edit `optimus_api.py` (line 863 for API port):

```python
uvicorn.run(
    "optimus_api:app",
    host="0.0.0.0",
    port=8000,  # Change if needed
)
```

---

## 🚀 Running the System

### Step 1: Start Ollama

```bash
# Windows (run as administrator)
ollama serve

# Linux/Mac
ollama serve
```

Verify Ollama is running:
```bash
curl http://localhost:11434/api/tags
```

### Step 2: Start MCP Server

Open a **new terminal** (keep Ollama running):

```bash
cd path/to/project
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

python server.py
```

Expected output:
```
INFO - Starting Company SQL Database MCP Server...
INFO - Auto-connected to SQL Server (BoltAtom)

── Live SQL Server Tools ──
  - list_databases      : List all databases
  - switch_database     : Switch active database
  - list_tables         : List tables (with row counts)
  - get_table_columns   : Get columns / PKs / FKs
  - query_table         : Query a table (no raw SQL needed)
  - execute_query       : Run any raw SQL query
  
INFO - Application startup complete.
INFO - Uvicorn running on http://0.0.0.0:8001
```

**Verify MCP server:**
```bash
curl http://localhost:8001/health
```

### Step 3: Start OPTIMUS API

Open a **new terminal**:

```bash
cd path/to/project
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

python optimus_api.py
```

Expected output:
```
╔══════════════════════════════════════════════════════════╗
║        OPTIMUS API - OpenWebUI Compatible v2.0           ║
║         OpenAI-Compatible API with MCP Integration       ║
╚══════════════════════════════════════════════════════════╝

Features:
✓ OpenAI-Compatible API (/v1/chat/completions)
✓ Image Support (Vision Models)
✓ Tool Calling (Database Queries)
✓ Streaming Responses

API: http://localhost:8000

INFO - Uvicorn running on http://0.0.0.0:8000
```

**Verify API:**
```bash
curl http://localhost:8000/v1/models
```

### Step 4: Install and Start OpenWebUI

```bash
# Pull the Docker image
docker pull ghcr.io/open-webui/open-webui:main

# Run OpenWebUI
docker run -d \
  -p 3000:8080 \
  --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart always \
  ghcr.io/open-webui/open-webui:main
```

**Windows (PowerShell):**
```powershell
docker run -d `
  -p 3000:8080 `
  --add-host=host.docker.internal:host-gateway `
  -v open-webui:/app/backend/data `
  --name open-webui `
  --restart always `
  ghcr.io/open-webui/open-webui:main
```

Access OpenWebUI at: **http://localhost:3000**

---

## 🌐 OpenWebUI Setup

### Initial Setup

1. **Create Admin Account**
   - Open http://localhost:3000
   - Sign up with email and password
   - First user automatically becomes admin

2. **Configure OpenAI Connection**

   **Go to:** Settings (⚙️) → Admin Panel → Connections → OpenAI

   **Add the following:**
   - **Base URL:** `http://host.docker.internal:8000/v1`
   - **API Key:** `sk-dummy` (any value works, not validated)
   - **Enable:** Toggle ON

   Click **Save**

3. **Verify Models**

   Go to the chat interface and click the model dropdown. You should see:
   - `ministral-3:8b`
   - `llama3.1:latest`
   - `llava:latest`
   - (Any other Ollama models you've installed)

4. **Test the Connection**

   Select a model and send a test message:
   ```
   Hello! Can you help me query the database?
   ```

---

## 📖 Usage Examples

### Example 1: Simple Database Query

**User:**
```
Show me all tables in the database
```

**AI Response:**
The AI will:
1. Call `list_tables` tool
2. Return a formatted list of tables with row counts

---

### Example 2: Search and Query

**User:**
```
Find information about customers
```

**AI Response:**
The AI will:
1. Call `search_tables` with keyword "customer"
2. Find table(s) like "Customers" or "CustomerOrders"
3. Call `query_table` to fetch sample data
4. Present the results

---

### Example 3: Complex Query

**User:**
```
Show me all orders from the last 30 days with customer names and total amounts
```

**AI Response:**
The AI will:
1. Call `search_tables` to find Orders and Customers tables
2. Call `execute_query` with a JOIN query
3. Present the formatted results

---

### Example 4: Switch Database

**User:**
```
Switch to the HRMS_Dev database and show me employee count
```

**AI Response:**
The AI will:
1. Call `switch_database` with "HRMS_Dev"
2. Call `query_table` or `execute_query` to get employee count
3. Present the result

---

### Example 5: Image Analysis (Vision Models)

**User:**
Upload an image and ask:
```
What's in this image? Does it relate to any data in our database?
```

**Requirements:**
- Must use a vision-enabled model (ministral-3:8b, llava:latest)
- Image must be uploaded through OpenWebUI interface

---

## 📚 API Documentation

### MCP Server Endpoints (http://localhost:8001)

#### Database Query Tools

**`list_databases`**
- List all databases on the SQL Server
- No parameters required

**`switch_database`**
- Switch to a different database
- Parameters:
  - `database_name` (string): Database name

**`list_tables`**
- List all tables in current database
- Parameters:
  - `schema` (string, optional): Schema name (default: "dbo")

**`get_table_columns`**
- Get column details for a table
- Parameters:
  - `table_name` (string): Table name
  - `schema` (string, optional): Schema name

**`query_table`**
- Query a table with filters
- Parameters:
  - `table_name` (string): Table name
  - `columns` (string, optional): Columns to select (default: "*")
  - `where_clause` (string, optional): Filter condition
  - `order_by` (string, optional): Sort order
  - `limit` (int, optional): Max rows (default: 100)

**`execute_query`**
- Execute raw SQL query
- Parameters:
  - `query` (string): SQL SELECT statement
  - `max_rows` (int, optional): Max rows (default: 1000)

**`search_tables`**
- Search for tables/views by keyword
- Parameters:
  - `search_term` (string): Search keyword

#### File Indexer Tools

**`load_database`**
- Index SQL files from a directory
- Parameters:
  - `path` (string): Directory path

**`search_sql`**
- Search indexed SQL content
- Parameters:
  - `search_term` (string): Search term
  - `limit` (int, optional): Max results

**`get_sql_file`**
- Read a SQL file
- Parameters:
  - `file_path` (string): File path

---

### OPTIMUS API Endpoints (http://localhost:8000)

#### OpenAI-Compatible Endpoints

**`GET /v1/models`**
- List available models
- Returns: List of Ollama models

**`POST /v1/chat/completions`**
- Chat completion endpoint
- Request body:
  ```json
  {
    "model": "ministral-3:8b",
    "messages": [
      {"role": "user", "content": "Hello"}
    ],
    "stream": true,
    "temperature": 0.7
  }
  ```

**`GET /health`**
- Health check endpoint
- Returns: Server status

---

## 🐛 Troubleshooting

### Issue: MCP Server Won't Start

**Error:** `pyodbc.Error: ('08001', ...)`

**Solution:**
1. Check SQL Server is running:
   ```bash
   # Windows
   services.msc
   # Look for "SQL Server (SQLEXPRESS)"
   ```

2. Verify ODBC driver:
   ```bash
   odbcad32  # Should show ODBC Driver 18
   ```

3. Test connection string in Python:
   ```python
   import pyodbc
   conn = pyodbc.connect("DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost\\SQLEXPRESS;Trusted_Connection=yes;")
   print("Connected!")
   ```

---

### Issue: OPTIMUS API Can't Connect to MCP

**Error:** `Connection refused` or `MCP server error`

**Solution:**
1. Verify MCP server is running:
   ```bash
   curl http://localhost:8001/health
   ```

2. Check firewall settings
3. Verify port 8001 is not in use:
   ```bash
   # Windows
   netstat -ano | findstr :8001
   ```

---

### Issue: OpenWebUI Can't See Models

**Solution:**
1. Check OPTIMUS API is running:
   ```bash
   curl http://localhost:8000/v1/models
   ```

2. Verify OpenWebUI connection settings:
   - Base URL must be `http://host.docker.internal:8000/v1`
   - NOT `http://localhost:8000/v1` (Docker networking)

3. Restart OpenWebUI container:
   ```bash
   docker restart open-webui
   ```

---

### Issue: Ollama Models Not Responding

**Solution:**
1. Verify Ollama is running:
   ```bash
   ollama list
   ```

2. Test model directly:
   ```bash
   ollama run ministral-3:8b "Hello"
   ```

3. Check Ollama logs:
   ```bash
   # Check Docker logs if running in container
   docker logs ollama
   ```

---

### Issue: Database Query Returns Empty

**Solution:**
1. Check current database:
   - Ask AI: "What database am I connected to?"

2. Verify table exists:
   - Ask AI: "List all tables"

3. Check table has data:
   - Ask AI: "How many rows in [table_name]?"

---

## 🔐 Security Best Practices

### Production Deployment

1. **Enable Authentication**
   - Add API key validation in `optimus_api.py`
   - Use environment variables for credentials

2. **Use SQL Authentication Instead of Trusted Connection**
   ```python
   conn_str = (
       "DRIVER={ODBC Driver 18 for SQL Server};"
       "SERVER=your-server;"
       "DATABASE=YourDB;"
       "UID=readonly_user;"  # Limited permissions
       "PWD=secure_password;"
       "Encrypt=yes;"
   )
   ```

3. **Limit Database Permissions**
   - Create a read-only SQL user
   - Grant only SELECT permissions
   - Restrict to specific schemas

4. **Enable HTTPS**
   - Use reverse proxy (nginx/Apache)
   - Add SSL certificates

5. **Rate Limiting**
   - Add rate limiting to API endpoints
   - Prevent abuse

---

## 🚀 Advanced Configuration

### Using OpenAI Instead of Ollama

Edit `optimus_api.py` to switch LLM provider:

```python
# At the top of the file, set your OpenAI API key
openai.api_key = "sk-your-api-key"

# In the stream_openai_chat_response function (around line 450):
# Replace Ollama client initialization with OpenAI client
client = openai.AsyncOpenAI()

# Use OpenAI models
model = "gpt-4o"  # or "gpt-3.5-turbo"
```

### Adding Custom MCP Tools

Add new tools to `server.py`:

```python
@mcp.tool()
def my_custom_tool(parameter: str) -> str:
    """
    Description of what this tool does
    
    Args:
        parameter: Description of parameter
        
    Returns:
        JSON string with results
    """
    try:
        # Your logic here
        result = do_something(parameter)
        
        return json.dumps({
            "status": "success",
            "data": result
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        })
```

Then register it in `optimus_api.py` MCP_TOOLS array.

### Logging Configuration

Enable detailed logging:

```python
# In server.py and optimus_api.py
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('detailed.log'),
        logging.StreamHandler()
    ]
)
```

---

## 📊 System Requirements

### Minimum Requirements
- **CPU:** 4 cores
- **RAM:** 8GB
- **Disk:** 20GB free space
- **OS:** Windows 10/11, Linux, macOS

### Recommended for Production
- **CPU:** 8+ cores
- **RAM:** 16GB+
- **Disk:** SSD with 50GB+ free space
- **Network:** 100Mbps+

---

## 📝 License

MIT License - See LICENSE file for details

---

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

---

## 📞 Support

For issues and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review logs in `optimus_api.log`

---

## 🎉 Quick Start Checklist

- [ ] Install Python 3.10+
- [ ] Install SQL Server + ODBC Driver 18
- [ ] Install Ollama + download models
- [ ] Install Docker
- [ ] Clone repository
- [ ] Create virtual environment
- [ ] Install dependencies (`pip install -r requirements.txt`)
- [ ] Configure SQL Server connection in `server.py`
- [ ] Start Ollama (`ollama serve`)
- [ ] Start MCP Server (`python server.py`)
- [ ] Start OPTIMUS API (`python optimus_api.py`)
- [ ] Start OpenWebUI (Docker)
- [ ] Configure OpenWebUI connection settings
- [ ] Test with a simple query

---

**Made with ❤️ by the Vibgyor Team**

*Last Updated: February 2026*
