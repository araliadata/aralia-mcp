# Save this as aralia_mcp_server_sdk.py
import os
import sys
import uvicorn # For running the server if not using 'mcp run'
from modelcontext import MCPApplication, MCPContext, MCPContent, MCPModelContext

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
    def format_aralia_data_for_mcp(data_wrapper: list) -> str:
        return "<document_set status=\"error_mcp_utils_missing_in_server\"></document_set>"
    def fetch_aralia_evidence_for_mcp(user_question: str, verbose: bool = False) -> list:
        return [{"error": "aralia_agent_logic.py not found or failed to import."}]
    def initialize_global_instances():
        print("ERROR: aralia_agent_logic.py not found, cannot initialize.", file=sys.stderr)
        return False
    ARALIA_LIBRARY_AVAILABLE = False


# --- MCP Application Setup ---
app = MCPApplication(
    name="Aralia Data Evidence Provider",
    version="0.1.0",
    description="Fetches and formats data from Aralia Data Planet for use with Claude."
)

# --- Server State & Initialization ---
SERVER_INITIALIZED_SUCCESSFULLY = initialize_global_instances()
if not SERVER_INITIALIZED_SUCCESSFULLY:
    print("CRITICAL ERROR: Server failed to initialize Aralia tools or LLM. Check environment variables (ARALIA_USERNAME, ARALIA_PASSWORD, GEMINI_API_KEY) and logs.", file=sys.stderr)
if not ARALIA_LIBRARY_AVAILABLE: # This check is now inside initialize_global_instances, but a top-level warning is also good.
    print("WARNING: Running with MOCK Aralia components because aralia_openrag library was not found.", file=sys.stderr)


# --- MCP Provider Definition ---
@app.provider("aralia_data_retriever")
async def aralia_data_provider(context: MCPContext) -> MCPModelContext:
    """
    MCP provider that receives a user question from context.context_str,
    fetches data from Aralia, formats it as MCP-compliant XML, and returns it.
    """
    user_question = context.context_str 
    print(f"INFO: MCP Provider 'aralia_data_retriever' called. User question: '{user_question}'", file=sys.stderr)

    if not SERVER_INITIALIZED_SUCCESSFULLY:
        print("ERROR: Server (Aralia tools/LLM) not initialized. Returning error context.", file=sys.stderr)
        error_xml = "<document_set status=\"server_initialization_error\"><error_details>Aralia tools or LLM failed to initialize. Check server logs.</error_details></document_set>"
        return MCPModelContext(contents=[MCPContent(type="xml", xml=error_xml)])

    try:
        aralia_data_wrapper = fetch_aralia_evidence_for_mcp(user_question, verbose=True)

        if isinstance(aralia_data_wrapper, list) and len(aralia_data_wrapper) > 0 and \
           isinstance(aralia_data_wrapper[0], dict) and "error" in aralia_data_wrapper[0]:
            error_message = aralia_data_wrapper[0]["error"]
            print(f"ERROR: Error from agent logic: {error_message}", file=sys.stderr)
            error_xml_content = f"<document_set status=\"aralia_agent_error\"><error_details><![CDATA[{error_message}]]></error_details></document_set>"
            mcp_contents = [MCPContent(type="xml", xml=error_xml_content)]
        else:
            xml_evidence = format_aralia_data_for_mcp(aralia_data_wrapper)
            mcp_contents = [MCPContent(type="xml", xml=xml_evidence)]
            print("INFO: Successfully processed Aralia data and formatted as XML for MCP.", file=sys.stderr)

        return MCPModelContext(
            instructions="The following XML document set contains data snippets from Aralia relevant to the user's query. Please use this information to formulate your response, citing document names and indices as specified in the content.",
            contents=mcp_contents
        )

    except Exception as e:
        print(f"ERROR: Unhandled exception in aralia_data_provider: {e}", file=sys.stderr)
        error_xml = f"<document_set status=\"unhandled_provider_exception\"><error_details><![CDATA[{str(e)}]]></error_details></document_set>"
        return MCPModelContext(contents=[MCPContent(type="xml", xml=error_xml)])

# --- Running the Server ---
# This block allows running the server directly with `python aralia_mcp_server_sdk.py` for testing.
# To use with the MCP CLI, you would typically run: `mcp run aralia_mcp_server_sdk:app`
if __name__ == "__main__":
    if "COLAB_GPU" not in os.environ and 'dotenv' not in sys.modules:
        try:
            from dotenv import load_dotenv
            load_dotenv() 
            if not SERVER_INITIALIZED_SUCCESSFULLY: # Attempt re-init if .env was just loaded
                print("INFO: Attempting re-initialization after .env load for main execution...", file=sys.stderr)
                SERVER_INITIALIZED_SUCCESSFULLY = initialize_global_instances()
        except ImportError:
            pass 

    if not SERVER_INITIALIZED_SUCCESSFULLY:
        print("CRITICAL: Cannot start server due to initialization failure. Please check logs and environment variables.", file=sys.stderr)
    else:
        print("INFO: Starting Aralia MCP Server with Uvicorn on http://127.0.0.1:8000", file=sys.stderr)
        print("INFO: To run with MCP CLI: mcp run aralia_mcp_server_sdk:app", file=sys.stderr)
        print("INFO: Registered provider: aralia_data_retriever", file=sys.stderr)
        uvicorn.run(app, host="127.0.0.1", port=8000)

