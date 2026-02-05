# 🔧 OPTIMUS AI Assistant - Troubleshooting Guide

## Table of Contents
- [Installation Issues](#installation-issues)
- [MCP Server Issues](#mcp-server-issues)
- [OPTIMUS API Issues](#optimus-api-issues)
- [OpenWebUI Issues](#openwebui-issues)
- [Database Connection Issues](#database-connection-issues)
- [Ollama Issues](#ollama-issues)
- [Common Error Messages](#common-error-messages)

---

## Installation Issues

### Python Package Installation Fails

**Error:**
```
ERROR: Could not find a version that satisfies the requirement...
```

**Solutions:**
1. Upgrade pip:
   ```bash
   python -m pip install --upgrade pip
   ```

2. Check Python version (must be 3.10+):
   ```bash
   python --version
   ```

3. Install packages one by one:
   ```bash
   pip install fastmcp
   pip install pyodbc
   pip install fastapi
   # etc.
   ```

### pyodbc Installation Fails on Windows

**Error:**
```
error: Microsoft Visual C++ 14.0 or greater is required
```

**Solutions:**
1. Install Microsoft C++ Build Tools:
   https://visualstudio.microsoft.com/visual-cpp-build-tools/

2. OR use pre-built wheels:
   ```bash
   pip install pyodbc --only-binary :all:
   ```

3. OR download from: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyodbc

---

## MCP Server Issues

### MCP Server Won't Start

**Error:**
```
pyodbc.Error: ('08001', '[08001] [Microsoft][ODBC Driver 18 for SQL Server]...')
```

**Diagnosis:**
```bash
# Test SQL Server connection
sqlcmd -S localhost\SQLEXPRESS -E -Q "SELECT @@VERSION"
```

**Solutions:**

1. **Check SQL Server is running:**
   ```
   Windows: services.msc → SQL Server (SQLEXPRESS)
   ```

2. **Verify ODBC Driver:**
   ```
   Windows: odbcad32 → Drivers → Look for "ODBC Driver 18 for SQL Server"
   ```

3. **Test connection in Python:**
   ```python
   import pyodbc
   conn_str = (
       "DRIVER={ODBC Driver 18 for SQL Server};"
       "SERVER=localhost\\SQLEXPRESS;"
       "Trusted_Connection=yes;"
       "Encrypt=optional;"
   )
   conn = pyodbc.connect(conn_str)
   print("✓ Connected!")
   ```

4. **Check server.py configuration:**
   - Verify SERVER name matches your instance
   - Try "localhost" instead of "localhost\\SQLEXPRESS"
   - Try IP address: "127.0.0.1\\SQLEXPRESS"

### Port 8001 Already in Use

**Error:**
```
ERROR: [Errno 48] Address already in use
```

**Solutions:**

1. **Find process using port 8001:**
   ```bash
   # Windows
   netstat -ano | findstr :8001
   taskkill /PID <PID> /F
   
   # Linux/Mac
   lsof -ti:8001 | xargs kill -9
   ```

2. **Change port in server.py:**
   ```python
   uvicorn.run(app, host="0.0.0.0", port=8002)  # Use different port
   ```

### Database Not Found

**Error:**
```
Cannot open database "BoltAtom" requested by the login
```

**Solutions:**
1. List available databases:
   ```sql
   SELECT name FROM sys.databases
   ```

2. Update server.py with correct database name

3. Create the database if missing:
   ```sql
   CREATE DATABASE BoltAtom
   ```

---

## OPTIMUS API Issues

### Can't Connect to MCP Server

**Error:**
```
httpx.ConnectError: All connection attempts failed
```

**Diagnosis:**
```bash
# Test MCP server
curl http://localhost:8001/health
```

**Solutions:**
1. Ensure MCP server is running (see MCP Server section)
2. Check firewall isn't blocking port 8001
3. Verify MCP_URL in optimus_api.py: `http://localhost:8001`

### Tool Calls Not Working

**Symptoms:**
- AI doesn't query database
- No tool execution logs
- Empty responses

**Solutions:**

1. **Check MCP server logs** for errors

2. **Test tool directly:**
   ```bash
   curl -X POST http://localhost:8001/call_tool \
     -H "Content-Type: application/json" \
     -d '{"name": "list_tables", "arguments": {}}'
   ```

3. **Verify tools are defined in optimus_api.py** (MCP_TOOLS array)

4. **Check model supports tool calling:**
   - ministral-3:8b ✓
   - llama3.1:latest ✓
   - Some older models ✗

### Streaming Not Working

**Symptoms:**
- Response appears all at once
- No real-time updates

**Solutions:**
1. Ensure `stream: true` in request
2. Check browser/client supports Server-Sent Events (SSE)
3. Verify no proxy is buffering responses

---

## OpenWebUI Issues

### Can't Access OpenWebUI (localhost:3000)

**Diagnosis:**
```bash
# Check if container is running
docker ps
```

**Solutions:**

1. **Container not running:**
   ```bash
   docker start open-webui
   ```

2. **Port conflict:**
   ```bash
   # Use different port
   docker run -d -p 3001:8080 ... ghcr.io/open-webui/open-webui:main
   ```

3. **Check Docker logs:**
   ```bash
   docker logs open-webui
   ```

### No Models Showing in OpenWebUI

**Symptoms:**
- Model dropdown is empty
- Can't select any model

**Solutions:**

1. **Verify API connection:**
   - Go to: Settings → Admin Panel → Connections → OpenAI
   - Base URL should be: `http://host.docker.internal:8000/v1`
   - Toggle to ON

2. **Test API endpoint:**
   ```bash
   curl http://localhost:8000/v1/models
   ```

3. **Check OPTIMUS API is running:**
   ```bash
   curl http://localhost:8000/health
   ```

4. **Restart OpenWebUI:**
   ```bash
   docker restart open-webui
   ```

### OpenWebUI Shows Connection Error

**Error:**
```
Failed to connect to OpenAI API
```

**Solutions:**

1. **Windows/Mac Docker Desktop Users:**
   - Use: `http://host.docker.internal:8000/v1`
   - NOT: `http://localhost:8000/v1`

2. **Linux Docker Users:**
   - Use: `http://172.17.0.1:8000/v1`
   - OR run with: `--network host`

3. **Check API is accessible from container:**
   ```bash
   docker exec open-webui curl http://host.docker.internal:8000/health
   ```

---

## Database Connection Issues

### Access Denied Error

**Error:**
```
Login failed for user 'DOMAIN\Username'
```

**Solutions:**

1. **Use SQL Server Authentication:**
   ```python
   conn_str = (
       "DRIVER={ODBC Driver 18 for SQL Server};"
       "SERVER=localhost\\SQLEXPRESS;"
       "DATABASE=BoltAtom;"
       "UID=sa;"
       "PWD=YourPassword;"
       "Encrypt=optional;"
   )
   ```

2. **Grant Windows user permissions:**
   ```sql
   CREATE LOGIN [DOMAIN\Username] FROM WINDOWS;
   USE BoltAtom;
   CREATE USER [DOMAIN\Username] FOR LOGIN [DOMAIN\Username];
   ALTER ROLE db_datareader ADD MEMBER [DOMAIN\Username];
   ```

### Timeout Errors

**Error:**
```
Query timeout expired
```

**Solutions:**

1. **Increase timeout in server.py:**
   ```python
   SQL_CONNECTION = pyodbc.connect(conn_str, timeout=60)
   ```

2. **Optimize query:**
   - Add WHERE clauses to limit rows
   - Add indexes to tables
   - Reduce LIMIT value

3. **Check server performance:**
   - High CPU usage?
   - Slow disk I/O?
   - Table locks?

### SSL/TLS Certificate Error

**Error:**
```
[SSL: CERTIFICATE_VERIFY_FAILED]
```

**Solutions:**

1. **Set Encrypt to optional:**
   ```python
   "Encrypt=optional;"
   ```

2. **Or disable encryption (not recommended for production):**
   ```python
   "Encrypt=no;"
   ```

3. **Or install valid certificate on SQL Server**

---

## Ollama Issues

### Ollama Not Running

**Diagnosis:**
```bash
curl http://localhost:11434/api/tags
```

**Solutions:**

1. **Start Ollama:**
   ```bash
   # Windows (as administrator)
   ollama serve
   
   # Linux/Mac
   ollama serve
   ```

2. **Check Ollama is in PATH:**
   ```bash
   ollama --version
   ```

3. **Reinstall Ollama if needed:**
   https://ollama.ai/download

### Model Not Found

**Error:**
```
model 'ministral-3:8b' not found
```

**Solutions:**

1. **Pull the model:**
   ```bash
   ollama pull ministral-3:8b
   ```

2. **List available models:**
   ```bash
   ollama list
   ```

3. **Use a different model:**
   ```bash
   # In optimus_api.py or OpenWebUI, use:
   llama3.1:latest
   ```

### Ollama Response Too Slow

**Solutions:**

1. **Use smaller model:**
   ```bash
   ollama pull llama3.2:3b  # Faster but less capable
   ```

2. **Increase VRAM allocation (if GPU):**
   - Check Ollama settings
   - Close other GPU-intensive apps

3. **Use GPU acceleration:**
   - Install CUDA (NVIDIA) or ROCm (AMD)
   - Verify: `ollama run ministral-3:8b "test" --verbose`

---

## Common Error Messages

### "No module named 'fastmcp'"

**Solution:**
```bash
pip install fastmcp
```

### "DLL load failed: The specified module could not be found"

**Solution (Windows):**
```bash
# Install Visual C++ Redistributable
# Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe
```

### "Port already in use"

**Solution:**
```bash
# Change port in server.py / optimus_api.py
# Or kill process using the port (see above)
```

### "Connection refused"

**Solutions:**
1. Check service is running
2. Verify port number
3. Check firewall settings
4. Try 127.0.0.1 instead of localhost

### "Tool execution failed"

**Solutions:**
1. Check MCP server logs
2. Verify database connection
3. Test tool manually via curl
4. Check tool arguments are correct

---

## Debug Mode

### Enable Detailed Logging

**server.py:**
```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_debug.log'),
        logging.StreamHandler()
    ]
)
```

**optimus_api.py:**
```python
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('api_debug.log'),
        logging.StreamHandler()
    ]
)
```

### View Real-time Logs

```bash
# Windows
type mcp_debug.log
type api_debug.log

# Linux/Mac
tail -f mcp_debug.log
tail -f api_debug.log
```

---

## Still Having Issues?

1. **Check all logs:**
   - MCP Server console output
   - OPTIMUS API console output
   - OpenWebUI: `docker logs open-webui`
   - SQL Server logs

2. **Verify all prerequisites:**
   - [ ] Python 3.10+ installed
   - [ ] SQL Server running
   - [ ] ODBC Driver 18 installed
   - [ ] Ollama running with models downloaded
   - [ ] Docker running (for OpenWebUI)

3. **Test each component separately:**
   - MCP Server: `curl http://localhost:8001/health`
   - OPTIMUS API: `curl http://localhost:8000/v1/models`
   - Ollama: `ollama list`
   - SQL Server: `sqlcmd -S localhost\SQLEXPRESS -E -Q "SELECT 1"`

4. **Create a minimal test:**
   ```python
   # test_mcp.py
   import httpx
   response = httpx.post(
       "http://localhost:8001/call_tool",
       json={"name": "list_databases", "arguments": {}}
   )
   print(response.json())
   ```

5. **Open an issue on GitHub** with:
   - Error messages
   - Log files
   - System information (OS, Python version, etc.)
   - Steps to reproduce

---

**Happy Troubleshooting! 🔧**
