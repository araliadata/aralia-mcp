# Save this as aralia_mcp_server.py
import os
import sys
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Any, List, Dict, Optional

# Attempt to load .env file if not in Colab
if "COLAB_GPU" not in os.environ:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("INFO: .env file loaded.", file=sys.stderr)
    except ImportError:
        print("INFO: python-dotenv not found, relying on system environment variables.", file=sys.stderr)

# Import from your utility and logic files
try:
    from mcp_anthropic_utils import format_aralia_data_for_mcp
    from aralia_agent_logic import fetch_aralia_evidence_for_mcp, initialize_global_instances, ARALIA_LIBRARY_AVAILABLE
except ImportError as e:
    print(f"ERROR: Failed to import helper modules: {e}. Ensure they are in the same directory or Python path.", file=sys.stderr)
    # Define fallback for format_aralia_data_for_mcp if import fails
    def format_aralia_data_for_mcp(data_wrapper: list) -> str:
        return "<document_set status=\"error_mcp_utils_missing_in_server\"></document_set>"
    def fetch_aralia_evidence_for_mcp(user_question: str, verbose: bool = False) -> list:
        return [{"error": "aralia_agent_logic.py not found or failed to import."}]
    def initialize_global_instances():
        print("ERROR: aralia_agent_logic.py not found, cannot initialize.", file=sys.stderr)
        return False
    ARALIA_LIBRARY_AVAILABLE = False


# --- FastAPI App Setup ---
app = FastAPI(
    title="Aralia Data MCP Server",
    description="Provides Aralia data context to Claude via Model Context Protocol.",
    version="0.1.0"
)

# --- Pydantic Models for MCP ---
class MCPContent(BaseModel):
    type: str
    text: Optional[str] = None
    xml: Optional[str] = None
    # Add other content types as needed by MCP spec

class MCPModelContext(BaseModel):
    instructions: Optional[str] = None
    contents: List[MCPContent] = Field(default_factory=list)

class MCPRequest(BaseModel):
    context: str # This will be the user's question/prompt
    model_context: Optional[MCPModelContext] = None # Previous context from Claude or other tools

class MCPResponse(BaseModel):
    model_context: MCPModelContext


# --- Server State ---
SERVER_INITIALIZED_SUCCESSFULLY = False

@app.on_event("startup")
async def startup_event():
    """Initializes global instances needed by the agent logic on server startup."""
    global SERVER_INITIALIZED_SUCCESSFULLY
    print("INFO: Server starting up. Initializing Aralia tools and LLM...", file=sys.stderr)
    if not ARALIA_LIBRARY_AVAILABLE:
         print("WARNING: Running with mock Aralia components because aralia_openrag library was not found.", file=sys.stderr)
    
    SERVER_INITIALIZED_SUCCESSFULLY = initialize_global_instances()
    if SERVER_INITIALIZED_SUCCESSFULLY:
        print("INFO: Server initialized successfully.", file=sys.stderr)
    else:
        print("ERROR: Server failed to initialize critical components. Check logs and environment variables (ARALIA_USERNAME, ARALIA_PASSWORD, GEMINI_API_KEY).", file=sys.stderr)

# --- MCP Endpoint ---
@app.post("/mcp", response_model=MCPResponse)
async def mcp_endpoint(request: MCPRequest):
    """
    MCP endpoint that receives a user question, fetches data from Aralia,
    formats it as MCP-compliant XML, and returns it.
    """
    user_question = request.context
    print(f"INFO: Received MCP request. User question: {user_question}", file=sys.stderr)

    if not SERVER_INITIALIZED_SUCCESSFULLY:
        print("ERROR: Server not initialized. Returning error context.", file=sys.stderr)
        error_xml = "<document_set status=\"server_initialization_error\"><error_details>Aralia tools or LLM failed to initialize. Check server logs.</error_details></document_set>"
        error_content = MCPContent(type="xml", xml=error_xml)
        return MCPResponse(model_context=MCPModelContext(contents=[error_content]))

    try:
        # Fetch Aralia data using the agent logic.
        # This function now returns the wrapper list: [[spec_with_data1, ...]]
        # or a list with an error dict: [{"error": "message"}]
        aralia_data_wrapper = fetch_aralia_evidence_for_mcp(user_question, verbose=True)

        if isinstance(aralia_data_wrapper, list) and len(aralia_data_wrapper) > 0 and \
           isinstance(aralia_data_wrapper[0], dict) and "error" in aralia_data_wrapper[0]:
            error_message = aralia_data_wrapper[0]["error"]
            print(f"ERROR: Error from agent logic: {error_message}", file=sys.stderr)
            error_xml_content = f"<document_set status=\"aralia_agent_error\"><error_details><![CDATA[{error_message}]]></error_details></document_set>"
            mcp_contents = [MCPContent(type="xml", xml=error_xml_content)]
        else:
            # Format the successfully retrieved data into MCP XML
            xml_evidence = format_aralia_data_for_mcp(aralia_data_wrapper)
            mcp_contents = [MCPContent(type="xml", xml=xml_evidence)]
            print("INFO: Successfully processed Aralia data and formatted as XML for MCP.", file=sys.stderr)

        # Construct the MCP response
        # The 'instructions' field in MCPModelContext can guide Claude on how to use the XML.
        # For this demo, we're keeping instructions minimal here, assuming the main prompt
        # to Claude (from the desktop app) will handle the primary tasking.
        response_model_context = MCPModelContext(
            instructions="The following XML document set contains data snippets from Aralia relevant to the user's query. Please use this information to formulate your response, citing document names and indices.",
            contents=mcp_contents
        )
        return MCPResponse(model_context=response_model_context)

    except Exception as e:
        print(f"ERROR: Unhandled exception in /mcp endpoint: {e}", file=sys.stderr)
        # Return a structured error within the MCP response
        error_xml = f"<document_set status=\"unhandled_server_exception\"><error_details><![CDATA[{str(e)}]]></error_details></document_set>"
        error_content = MCPContent(type="xml", xml=error_xml)
        return MCPResponse(model_context=MCPModelContext(contents=[error_content]))

if __name__ == "__main__":
    import uvicorn
    # Ensure API keys are loaded for the main execution context if .env is used
    if "COLAB_GPU" not in os.environ and 'dotenv' not in sys.modules:
        try:
            from dotenv import load_dotenv
            load_dotenv() 
        except ImportError:
            pass 

    # Check essential env vars for server startup
    required_vars = ["ARALIA_USERNAME", "ARALIA_PASSWORD", "GEMINI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"ERROR: Missing critical environment variables for server startup: {', '.join(missing_vars)}", file=sys.stderr)
        print("INFO: The server might not function correctly if these are needed by Aralia tools.", file=sys.stderr)
        # Allow startup for mock testing, but real functionality will be impaired.
    
    print("INFO: Starting Aralia MCP Server with Uvicorn on http://127.0.0.1:8000", file=sys.stderr)
    uvicorn.run(app, host="127.0.0.1", port=8000)

