"""
OPTIMUS API - OpenWebUI Compatible Version
FastAPI server with OpenAI-compatible endpoints for OpenWebUI integration
Supports images, file uploads, and MCP database queries
"""

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal, Union
import json
import logging
import sys
from datetime import datetime
import httpx
import os
from enum import Enum
import base64
import uuid
import mimetypes

# LLM imports
import openai
import ollama

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('optimus_api.log')
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="OPTIMUS API - OpenWebUI Compatible",
    description="Vibgyor Company AI Assistant with OpenAI-compatible API",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# OpenAI-Compatible Models
# ============================================================================

class Message(BaseModel):
    role: str
    content: Union[str, List[Dict[str, Any]]]  # Support text and multimodal content
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0
    frequency_penalty: Optional[float] = 0
    user: Optional[str] = None


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str = "optimus"


class ModelsResponse(BaseModel):
    object: str = "list"
    data: List[ModelInfo]


# ============================================================================
# MCP Tools Configuration
# ============================================================================

MCP_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_tables",
            "description": (
                "Search for tables or views in the database by keyword. "
                "Use this FIRST to find the correct table name. "
                "After you get results, you MUST immediately call query_table or execute_query to fetch the actual data rows."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "search_term": {
                        "type": "string",
                        "description": "Keyword to search for in table/view names (e.g. 'customer', 'employee', 'project')"
                    }
                },
                "required": ["search_term"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_table",
            "description": (
                "Fetch actual data rows from a table. Use this after you know the table name. "
                "This is the main tool for retrieving data."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Exact name of the table to query"
                    },
                    "columns": {
                        "type": "string",
                        "description": "Comma-separated column names, or '*' for all columns",
                        "default": "*"
                    },
                    "where_clause": {
                        "type": "string",
                        "description": "Filter condition without the WHERE keyword. Example: CustomerID = 1",
                        "default": ""
                    },
                    "order_by": {
                        "type": "string",
                        "description": "Order clause without ORDER BY keyword. Example: CreatedDate DESC",
                        "default": ""
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of rows to return. Default 100, max 5000.",
                        "default": 100
                    }
                },
                "required": ["table_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_query",
            "description": (
                "Run a custom SQL query. Use this for JOINs, aggregations, or anything query_table cannot handle. "
                "Write the full SQL SELECT statement."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Full SQL SELECT statement to execute"
                    },
                    "max_rows": {
                        "type": "integer",
                        "description": "Max rows to return. Default 1000.",
                        "default": 1000
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_table_columns",
            "description": "Get the column names and types for a specific table.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Name of the table"
                    }
                },
                "required": ["table_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "switch_database",
            "description": "Switch to a different database. Available: BoltAtom, HRMS_Dev.",
            "parameters": {
                "type": "object",
                "properties": {
                    "database_name": {
                        "type": "string",
                        "description": "Name of the database"
                    }
                },
                "required": ["database_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_tables",
            "description": "List ALL tables in the current database.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


# ============================================================================
# MCP Client Implementation
# ============================================================================

class MCPClient:
    """Client for interacting with MCP server using direct JSON-RPC 2.0 calls"""

    def __init__(self, base_url: str = "http://localhost:8001/mcp"):
        self.base_url = base_url
        self.session_id = None
        self.request_id = 0
        self.client = httpx.AsyncClient(timeout=60.0)

    async def _call_jsonrpc(self, method: str, params: dict = None):
        self.request_id += 1
        payload = {"jsonrpc": "2.0", "id": self.request_id, "method": method}
        if params is not None:
            payload["params"] = params

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id

        response = await self.client.post(self.base_url, json=payload, headers=headers)
        response.raise_for_status()

        new_session_id = response.headers.get("Mcp-Session-Id")
        if new_session_id:
            self.session_id = new_session_id

        content = response.text
        lines = content.split("\r\n")
        for line in lines:
            if line.startswith("data: "):
                return json.loads(line[6:])
        return json.loads(content)

    async def initialize(self):
        logger.info("Initializing MCP session...")
        result = await self._call_jsonrpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "optimus-api", "version": "2.0.0"}
            }
        )
        logger.info(f"MCP session initialized. Session ID: {self.session_id}")
        return result

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        if not self.session_id:
            await self.initialize()

        logger.info(f"MCP Tool Call: {tool_name}")
        logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")

        try:
            result = await self._call_jsonrpc("tools/call", {"name": tool_name, "arguments": arguments})
            if "result" in result and "content" in result["result"]:
                content = result["result"]["content"]
                if isinstance(content, list) and len(content) > 0:
                    text_content = content[0].get("text", "")
                    logger.info(f"MCP Tool Response: {tool_name}")
                    logger.info(f"Result preview: {text_content[:200]}...")
                    return text_content
            return json.dumps(result)
        except Exception as e:
            error_msg = f"MCP tool call failed: {str(e)}"
            logger.error(error_msg)
            return json.dumps({"status": "error", "message": error_msg})

    async def close(self):
        await self.client.aclose()


mcp_client = MCPClient(base_url="http://localhost:8001/mcp")


# ============================================================================
# System Prompt
# ============================================================================

SYSTEM_PROMPT = """You are OPTIMUS, a database assistant for Vibgyor (an interior design and home automation company). You help users query a SQL Server database.

You have these tools: search_tables, query_table, execute_query, get_table_columns, switch_database, list_tables.

RULE: When a user asks for data, always do TWO steps:
Step 1: Call search_tables with a keyword to find the right table name.
Step 2: Call query_table (or execute_query) with that table name to get the actual rows.

Never stop after step 1. The user wants data rows, not table names.

Common table locations:
- Customers → search "customer" → table ScCustomer (in BoltAtom)
- Projects → search "project" → table ScProject (in BoltAtom)
- Quotations → search "quotation" → table ScQuotation or ScQuotationData (in BoltAtom)
- Employees → search "employee" → table Employee (in HRMS_Dev, switch database first)

Default database is BoltAtom. If looking for employee or HR data, call switch_database("HRMS_Dev") first.

If the user provides an image, analyze it and help them with any database-related questions about it.

If you do not find any data in the tables, try to find the data in other related tables by looking at the tables names.

Present data as a clean markdown table. Do not show SQL queries to the user."""


# ============================================================================
# Model Capabilities Detection
# ============================================================================

# Models known to support multimodal input (images)
VISION_MODELS = {
    "ministral-3", "ministral-3:8b", "ministral-3:latest",
    "llava", "llava:latest", "llava:13b", "llava:7b",
    "bakllava", "bakllava:latest",
    "llava-llama3", "llava-llama3:latest",
    "llava-phi3", "llava-phi3:latest",
    "moondream", "moondream:latest"
}


def is_vision_model(model_name: str) -> bool:
    """Check if a model supports vision/multimodal input"""
    model_base = model_name.split(":")[0].lower()
    return any(vision_model in model_base for vision_model in VISION_MODELS)


# ============================================================================
# LLM Service
# ============================================================================

class LLMService:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if self.openai_api_key:
            openai.api_key = self.openai_api_key

    async def chat_completion_ollama(
        self, messages: List[Dict], model: str = "ministral-3:8b",
        temperature: float = 0.7, tools: Optional[List[Dict]] = None
    ):
        """
        Send chat completion request to Ollama.
        Handles both text-only and multimodal messages properly.
        """
        kwargs = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature}
        }
        if tools:
            kwargs["tools"] = tools

        try:
            client = ollama.AsyncClient(host='http://localhost:11434')
            response = await client.chat(**kwargs)
            logger.debug(f"Ollama full response: {response}")
            yield response
        except Exception as e:
            logger.error(f"Ollama error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Ollama error: {str(e)}")


llm_service = LLMService()


# ============================================================================
# Tool Execution
# ============================================================================

VALID_TOOL_NAMES = {
    "search_tables", "query_table", "execute_query",
    "get_table_columns", "switch_database", "list_tables", "list_databases",
    "load_database", "search_sql", "get_table_schema",
    "get_procedure_info", "list_objects", "find_dependencies", "get_statistics"
}


async def execute_tool_calls(tool_calls: List[Dict]) -> List[Dict]:
    results = []
    for tool_call in tool_calls:
        if isinstance(tool_call, dict):
            tool_name = tool_call.get("function", {}).get("name", "")
            arguments = tool_call.get("function", {}).get("arguments", {})
            tool_call_id = tool_call.get("id", f"call_{len(results)}")
        else:
            tool_name = getattr(getattr(tool_call, "function", None), "name", "")
            arguments = getattr(getattr(tool_call, "function", None), "arguments", {})
            tool_call_id = getattr(tool_call, "id", f"call_{len(results)}")

        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}

        if tool_name not in VALID_TOOL_NAMES:
            logger.warning(f"Invalid tool: '{tool_name}'")
            results.append({
                "tool_call_id": tool_call_id,
                "role": "tool",
                "name": tool_name,
                "content": json.dumps({"status": "error", "message": f"Tool '{tool_name}' does not exist"})
            })
            continue

        logger.info(f"Executing: {tool_name} with {arguments}")
        result = await mcp_client.call_tool(tool_name, arguments)
        results.append({
            "tool_call_id": tool_call_id,
            "role": "tool",
            "name": tool_name,
            "content": result
        })

    return results


def parse_ollama_response(response) -> tuple[str, List[Dict]]:
    text = ""
    tool_calls = []

    if isinstance(response, dict):
        msg = response.get("message", {})
        text = msg.get("content", "") or ""
        raw_tools = msg.get("tool_calls", []) or []
    else:
        msg = getattr(response, "message", None)
        if msg:
            text = getattr(msg, "content", "") or ""
            raw_tools = getattr(msg, "tool_calls", []) or []
        else:
            raw_tools = []

    for i, tc in enumerate(raw_tools):
        if isinstance(tc, dict):
            fn = tc.get("function", {})
            tool_calls.append({
                "id": tc.get("id", f"call_{i}"),
                "type": "function",
                "function": {"name": fn.get("name", ""), "arguments": fn.get("arguments", {})}
            })
        else:
            fn = getattr(tc, "function", None)
            tool_calls.append({
                "id": getattr(tc, "id", f"call_{i}"),
                "type": "function",
                "function": {"name": getattr(fn, "name", ""), "arguments": getattr(fn, "arguments", {})}
            })

    return text, tool_calls


def build_forced_query_message(search_result_text: str) -> Optional[str]:
    try:
        data = json.loads(search_result_text)
        results = data.get("results", [])
        if results:
            for r in results:
                if r.get("type") == "Table":
                    return f"Now call query_table with table_name=\"{r['name']}\" to get the actual data rows."
            return f"Now call query_table with table_name=\"{results[0]['name']}\" to get the actual data rows."
    except (json.JSONDecodeError, KeyError):
        pass
    return None


# ============================================================================
# Message Content Processing (for images and files)
# ============================================================================

def process_message_content(content: Union[str, List[Dict]], model: str) -> tuple[str, List[str]]:
    """
    Process message content for Ollama.
    
    Returns: (text_content, images_array)
    
    OpenWebUI sends multimodal content as:
    [
        {"type": "text", "text": "What's in this image?"},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
    ]
    
    Ollama expects:
    {
        'role': 'user',
        'content': 'What is in this image?',  # TEXT as string
        'images': ['base64_data']  # IMAGES as separate array (base64 without prefix)
    }
    """
    # If it's already a string, return as-is with no images
    if isinstance(content, str):
        return content, []
    
    # Extract text and images separately
    text_parts = []
    images = []
    
    for item in content:
        if isinstance(item, dict):
            if item.get("type") == "text":
                text_parts.append(item.get("text", ""))
            elif item.get("type") == "image_url":
                image_url = item.get("image_url", {})
                url = image_url.get("url", "")
                
                if url.startswith("data:"):
                    # Extract just the base64 part (remove "data:image/jpeg;base64," prefix)
                    try:
                        # Split by comma to get the base64 part
                        base64_data = url.split(",", 1)[1] if "," in url else url
                        images.append(base64_data)
                    except Exception as e:
                        logger.error(f"Error processing image data: {e}")
        elif isinstance(item, str):
            text_parts.append(item)
    
    text_content = " ".join(text_parts) if text_parts else ""
    
    # For text-only models, ignore images
    supports_vision = is_vision_model(model)
    if not supports_vision and images:
        logger.warning(f"Model '{model}' does not support vision. {len(images)} image(s) will be ignored.")
        images = []
    
    return text_content, images


# ============================================================================
# OpenAI-Compatible Streaming Handler
# ============================================================================

async def stream_openai_chat_response(
    messages: List[Message],
    model: str,
    temperature: float
):
    """Stream chat responses in OpenAI format"""
    
    # Check if the selected model supports vision
    model_supports_vision = is_vision_model(model)
    
    # Process messages with appropriate formatting for the model
    processed_messages = []
    has_images = False
    
    for msg in messages:
        # Process content to extract text and images separately
        text_content, images_array = process_message_content(msg.content, model)
        
        # Check if we have images
        if images_array:
            has_images = True
        
        # Build message in Ollama's format
        message_dict = {
            "role": msg.role,
            "content": text_content
        }
        
        # Add images array only if we have images
        if images_array:
            message_dict["images"] = images_array
        
        processed_messages.append(message_dict)
    
    # Log if images detected but model doesn't support them
    if has_images and not model_supports_vision:
        logger.warning(f"Images detected but model '{model}' may not support vision. Images will be ignored.")
    
    # Add system prompt (always as text, no images)
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + processed_messages
    
    logger.info(f"Using model: {model} (vision support: {model_supports_vision})")
    if has_images:
        logger.info(f"Processing request with {sum(len(m.get('images', [])) for m in processed_messages)} image(s)")
    
    max_iterations = 20
    iteration = 0
    assistant_full_text = ""
    
    while iteration < max_iterations:
        iteration += 1
        logger.info(f"--- Iteration {iteration}/{max_iterations} ---")

        try:
            full_response = ""
            tool_calls = []

            async for response in llm_service.chat_completion_ollama(
                messages=full_messages,
                model=model,
                temperature=temperature,
                tools=MCP_TOOLS
            ):
                full_response, tool_calls = parse_ollama_response(response)
                logger.info(f"Ollama: text_len={len(full_response)}, tool_calls={len(tool_calls)}")

            if full_response:
                assistant_full_text += full_response
                # Stream in OpenAI format
                chunk_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
                chunk = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": int(datetime.now().timestamp()),
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": full_response},
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(chunk)}\n\n"

            if tool_calls:
                logger.info(f"Executing {len(tool_calls)} tool call(s)")
                
                assistant_msg: Dict[str, Any] = {
                    "role": "assistant",
                    "content": full_response or None,
                    "tool_calls": tool_calls
                }
                full_messages.append(assistant_msg)

                tool_results = await execute_tool_calls(tool_calls)
                for result in tool_results:
                    full_messages.append(result)
                    logger.info(f"Tool {result['name']} completed")

                called_names = [tc["function"]["name"] for tc in tool_calls]
                if called_names == ["search_tables"]:
                    for r in tool_results:
                        if r["name"] == "search_tables":
                            nudge = build_forced_query_message(r["content"])
                            if nudge:
                                logger.info(f"Injecting nudge: {nudge}")
                                full_messages.append({"role": "user", "content": nudge})
                            break
                continue
            else:
                # Send final chunk
                chunk_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
                final_chunk = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": int(datetime.now().timestamp()),
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }]
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"
                break

        except Exception as e:
            logger.error(f"Error in iteration {iteration}: {str(e)}", exc_info=True)
            error_chunk = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                "object": "chat.completion.chunk",
                "created": int(datetime.now().timestamp()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {"content": f"\n\nError: {str(e)}"},
                    "finish_reason": "stop"
                }]
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
            yield "data: [DONE]\n\n"
            break


# ============================================================================
# OpenAI-Compatible API Endpoints
# ============================================================================

@app.get("/v1/models")
@app.get("/models")
async def list_models():
    """List available models (OpenAI-compatible)"""

    try:
        client = ollama.AsyncClient(host="http://localhost:11434")
        ollama_models = await client.list()

        models_data = []

        for model in ollama_models.models:

            models_data.append(
                ModelInfo(
                    id=model.model,   # ✅ correct field
                    created=int(model.modified_at.timestamp()),
                    owned_by="ollama"
                )
            )

    except Exception as e:
        logger.error(f"Failed to get Ollama models: {e}")

        models_data = [
            ModelInfo(id="ministral-3:8b", created=int(datetime.now().timestamp())),
            ModelInfo(id="llama3.1:latest", created=int(datetime.now().timestamp())),
            ModelInfo(id="llava:latest", created=int(datetime.now().timestamp())),
        ]

    return ModelsResponse(data=models_data)


@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI-compatible chat completions endpoint.
    Supports streaming, images, and tool calling.
    """
    logger.info(f"Chat completion request - Model: {request.model}, Stream: {request.stream}")
    
    if request.stream:
        return StreamingResponse(
            stream_openai_chat_response(
                messages=request.messages,
                model=request.model,
                temperature=request.temperature
            ),
            media_type="text/event-stream"
        )
    else:
        # Non-streaming response
        full_response = ""
        async for chunk_str in stream_openai_chat_response(
            messages=request.messages,
            model=request.model,
            temperature=request.temperature
        ):
            if chunk_str.startswith("data: ") and not chunk_str.startswith("data: [DONE]"):
                chunk_data = json.loads(chunk_str[6:])
                if chunk_data["choices"][0]["delta"].get("content"):
                    full_response += chunk_data["choices"][0]["delta"]["content"]
        
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": request.model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": full_response
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }


# ============================================================================
# Health Check
# ============================================================================

@app.get("/")
@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "api_type": "openai-compatible",
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# Shutdown
# ============================================================================

@app.on_event("shutdown")
async def shutdown_event():
    await mcp_client.close()


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║        OPTIMUS API - OpenWebUI Compatible v2.0           ║
    ║         OpenAI-Compatible API with MCP Integration       ║
    ╚══════════════════════════════════════════════════════════╝
    
    Features:
    ✓ OpenAI-Compatible API (/v1/chat/completions)
    ✓ Image Support (Vision Models)
    ✓ File Upload Support
    ✓ Tool Calling (Database Queries)
    ✓ Streaming Responses
    
    Supported Vision Models:
    • ministral-3:8b (multimodal)
    • llava:latest
    • bakllava:latest
    • llava-llama3:latest
    
    API: http://localhost:8000
    OpenWebUI Setup:
      1. In OpenWebUI, go to Settings → Connections
      2. Add OpenAI API Connection:
         - Base URL: http://localhost:8000/v1
         - API Key: (not required, leave as 'sk-dummy' or any value)
      3. Select OPTIMUS models in the chat
    
    """)
    
    uvicorn.run(
        "optimus_api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )