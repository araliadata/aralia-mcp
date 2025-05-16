# Save this as aralia_mcp_server_sdk.py
import os
import sys
import uvicorn 

# Correct imports based on the modelcontextprotocol/python-sdk
try:
    from mcp.server.fastmcp import FastMCP
    # Note: The tool function itself doesn't directly take/return MCPContext/ModelContext/Content
    # The FastMCP framework handles the wrapping.
    SDK_AVAILABLE = True
    print("INFO: Successfully imported FastMCP from mcp.server.fastmcp.", file=sys.stderr)
except ImportError as e:
    print(f"ERROR: Failed to import FastMCP from mcp.server.fastmcp: {e}", file=sys.stderr)
    print("Please ensure 'mcp[cli]' is installed correctly (e.g., pip install \"mcp[cli]\").", file=sys.stderr)
    SDK_AVAILABLE = False
    # Define a dummy FastMCP if SDK is not available
    class FastMCP: # type: ignore
        def __init__(self, name: str): 
            self.name = name
            print(f"Mock FastMCP initialized with name: {name}", file=sys.stderr)
        def tool(self, *args, **kwargs): 
            def decorator(func):
                return func
            return decorator
        def run(self, *args, **kwargs): # Add dummy run for the __main__ block
             print("Mock FastMCP.run() called. If SDK was available, server would start.", file=sys.stderr)


# Attempt to load .env file for local development
try:
    from dotenv import load_dotenv
    if load_dotenv(): 
        print("INFO: .env file loaded.", file=sys.stderr)
    else:
        print("INFO: .env file not found or empty, relying on system environment variables.", file=sys.stderr)
except ImportError:
    print("INFO: python-dotenv not found, relying on system environment variables.", file=sys.stderr)

# Import from your utility and logic files
try:
    from mcp_anthropic_utils import format_aralia_data_for_mcp
    from aralia_agent_logic import fetch_aralia_evidence_for_mcp, initialize_global_instances, ARALIA_LIBRARY_AVAILABLE
except ImportError as e:
    print(f"ERROR: Failed to import helper modules (mcp_anthropic_utils.py or aralia_agent_logic.py): {e}. Ensure they are in the same directory or Python path.", file=sys.stderr)
    def format_aralia_data_for_mcp(data_wrapper: list) -> str:
        return "<document_set status=\"error_mcp_utils_missing_in_server\"></document_set>"
    def fetch_aralia_evidence_for_mcp(user_question: str, verbose: bool = False) -> list:
        return [{"error": "aralia_agent_logic.py not found or failed to import."}]
    def initialize_global_instances():
        print("ERROR: aralia_agent_logic.py not found, cannot initialize.", file=sys.stderr)
        return False
    ARALIA_LIBRARY_AVAILABLE = False


# --- MCP Application Setup ---
# Initialize FastMCP with a name for your tool service, as per the weather example
mcp_app = FastMCP("aralia_data_tools")

# --- Server State & Initialization ---
SERVER_INITIALIZED_SUCCESSFULLY = initialize_global_instances()
if not SERVER_INITIALIZED_SUCCESSFULLY:
    print("CRITICAL ERROR: Server failed to initialize Aralia tools or LLM. Check environment variables (ARALIA_USERNAME, ARALIA_PASSWORD, GEMINI_API_KEY) and logs.", file=sys.stderr)
if not ARALIA_LIBRARY_AVAILABLE: 
    print("WARNING: Running with MOCK Aralia components because aralia_openrag library was not found.", file=sys.stderr)


# --- MCP Tool Definition ---
@mcp_app.tool()
async def retrieve_aralia_evidence(user_question: str) -> str:
    """
    MCP Tool that receives a user question, fetches data from Aralia,
    and returns it formatted as an MCP-compliant XML string.
    The LLM (Claude) will provide the 'user_question'.
    The tool returns a string (the XML data), which FastMCP wraps for the LLM.
    """
    print(f"INFO: MCP Tool 'retrieve_aralia_evidence' called. User question: '{user_question}'", file=sys.stderr)

    if not SERVER_INITIALIZED_SUCCESSFULLY:
        print("ERROR: Server (Aralia tools/LLM) not initialized. Returning error XML.", file=sys.stderr)
        return "<document_set status=\"server_initialization_error\"><error_details>Aralia tools or LLM failed to initialize. Check server logs.</error_details></document_set>"

    try:
        aralia_data_wrapper = fetch_aralia_evidence_for_mcp(user_question, verbose=True)

        if isinstance(aralia_data_wrapper, list) and len(aralia_data_wrapper) > 0 and \
           isinstance(aralia_data_wrapper[0], dict) and "error" in aralia_data_wrapper[0]:
            error_message = aralia_data_wrapper[0]["error"]
            print(f"ERROR: Error from agent logic: {error_message}", file=sys.stderr)
            return f"<document_set status=\"aralia_agent_error\"><error_details><![CDATA[{error_message}]]></error_details></document_set>"
        
        xml_evidence = format_aralia_data_for_mcp(aralia_data_wrapper)
        print("INFO: Successfully processed Aralia data and formatted as XML for MCP tool output.", file=sys.stderr)
        return xml_evidence # Return the XML string directly

    except Exception as e:
        print(f"ERROR: Unhandled exception in retrieve_aralia_evidence tool: {e}", file=sys.stderr)
        return f"<document_set status=\"unhandled_tool_exception\"><error_details><![CDATA[{str(e)}]]></error_details></document_set>"


# --- Running the Server ---
if __name__ == "__main__":
    if not SDK_AVAILABLE:
        print("CRITICAL: modelcontext SDK (mcp.server.fastmcp) not found. Cannot start server.", file=sys.stderr)
        sys.exit(1)
        
    try:
        if 'dotenv' in sys.modules and hasattr(sys.modules['dotenv'], 'load_dotenv'):
            if load_dotenv():
                print("INFO: .env file re-checked/loaded for main execution.", file=sys.stderr)
                if not SERVER_INITIALIZED_SUCCESSFULLY:
                    print("INFO: Attempting re-initialization after .env load for main execution...", file=sys.stderr)
                    SERVER_INITIALIZED_SUCCESSFULLY = initialize_global_instances()
    except NameError: 
        pass

    if not SERVER_INITIALIZED_SUCCESSFULLY:
        print("CRITICAL: Cannot start server due to initialization failure. Please check logs and environment variables.", file=sys.stderr)
    else:
        # The example `weather` app uses `mcp.run(transport='stdio')` for CLI tool interaction.
        # For an HTTP server that Claude Desktop App can call, you'd typically use `mcp run` CLI command
        # or uvicorn if FastMCP instance is a standard ASGI app.
        
        # Option 1: Running with MCP CLI (recommended for tool servers if Claude app expects HTTP)
        print("INFO: To run this MCP tool server, use the MCP CLI:", file=sys.stderr)
        print("INFO:   mcp run aralia_mcp_server_sdk:mcp_app --port 8000", file=sys.stderr)
        print("INFO: (Ensure 'mcp[cli]' is installed and this script is in your Python path or current directory)", file=sys.stderr)
        
        # Option 2: Direct Uvicorn run (if mcp_app is a standard ASGI app, for testing)
        # This makes it behave like a general ASGI app, which the MCP CLI also does for HTTP.
        print("\nINFO: Attempting to start with Uvicorn for direct testing on http://127.0.0.1:8000...", file=sys.stderr)
        print("INFO: Registered tool: retrieve_aralia_evidence", file=sys.stderr)
        try:
            uvicorn.run(mcp_app, host="127.0.0.1", port=8000)
        except TypeError as e:
            if "'FastMCP' object is not callable" in str(e):
                 print("\nERROR: Uvicorn cannot run FastMCP instance directly if it's not a raw ASGI app.", file=sys.stderr)
                 print("Please use 'mcp run aralia_mcp_server_sdk:mcp_app --port 8000' instead.", file=sys.stderr)
            else:
                raise e
        except Exception as e:
            print(f"ERROR running with Uvicorn: {e}", file=sys.stderr)
            print("Try: 'mcp run aralia_mcp_server_sdk:mcp_app --port 8000'", file=sys.stderr)


