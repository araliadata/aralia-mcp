import os
# Only import dotenv if not in Colab and if the library is available
if "COLAB_GPU" not in os.environ:
    try:
        from dotenv import load_dotenv
        load_dotenv() # Load .env file for API keys
    except ImportError:
        print("python-dotenv library not found. Please install it with 'pip install python-dotenv' if you are using a .env file for API keys.")

import pandas as pd

try:
    from aralia_openrag import aralia_tools, node, schema, prompts
    from aralia_openrag.aralia_tools import AraliaTools
except ImportError:
    print("Please ensure the aralia_openrag library is installed and accessible.")
    print("Using mock objects for Aralia components as fallback.")
    class AraliaTools:
        def __init__(self, username, password, url):
            print(f"Mock AraliaTools initialized for {url} (username: {username})")
        def search_tool(self, query, **kwargs):
            print(f"Mock search_tool called with query: {query}")
            return [{"id": "mock_ds_1", "name": "Mock Dataset 1: GDP Data", "description": "Mock GDP data for various regions.", "columns_metadata": [{"columnID": "col1", "name": "Year", "type": "date"}, {"columnID": "col2", "name": "Region", "type": "nominal"}, {"columnID": "col3", "name": "GDP_Growth_Rate", "type": "float"}]}]
        def column_metadata_tool(self, dataset_id, **kwargs):
            print(f"Mock column_metadata_tool called for dataset: {dataset_id}")
            return [{"columnID": "col1", "name": "Year", "type": "date", "displayName":"Year"}, {"columnID": "col2", "name": "Region", "type": "nominal", "displayName":"Region"}, {"columnID": "col3", "name": "GDP_Growth_Rate", "type": "float", "displayName":"GDP Growth Rate (%)"}]
        def filter_option_tool(self, dataset_id, column_id, **kwargs):
            print(f"Mock filter_option_tool called for {dataset_id}, {column_id}")
            return ["2019", "2020"]
        def explore_tool(self, chart_spec, **kwargs):
            print(f"Mock explore_tool called with chart_spec: {chart_spec}")
            dataset_id = chart_spec.get("id", "mock_ds_1")
            if dataset_id == "mock_ds_1":
              return {"id": dataset_id, "name": "Mock Dataset 1: GDP Data", "description": "Mock GDP data for various regions.", "data": "Year,Region,GDP_Growth_Rate\n2019,RegionA,2.5\n2019,RegionB,3.0\n2020,RegionA,1.0"}
            return {"id": dataset_id, "name": "Unknown Mock Dataset", "description": "N/A", "data": ""}
    class MockNodeModule:
        def aralia_search_agent(self, state):
            print("Mock aralia_search_agent called")
            at = state.get("at")
            datasets = at.search_tool(state["question"])
            return {"response": datasets[:1] if datasets else []}
        def analytics_planning_agent(self, state):
            print("Mock analytics_planning_agent called")
            dataset_info = state.get("response", [])
            if not dataset_info: return {"response": []}
            first_dataset = dataset_info[0]; at = state.get("at"); columns = at.column_metadata_tool(first_dataset["id"])
            return {"response": {"charts": [{"id": first_dataset["id"], "name": first_dataset["name"], "description": first_dataset["description"], "x": [{"columnID": "col1", "name": "Year", "type":"date", "format": "year"}], "y": [{"columnID": "col3", "name": "GDP_Growth_Rate", "type":"float", "calculation": "avg"}], "filter":[{"columnID": "col2", "name": "Region", "type":"nominal", "format": "", "operator":"in", "value": ["RegionA", "RegionB"]}]}]}}
        def filter_decision_agent(self, state):
            print("Mock filter_decision_agent called"); return {"response": state.get("response")}
        def analytics_execution_agent(self, state):
            print("Mock analytics_execution_agent called")
            chart_specs = state.get("response", {}).get("charts", []); results = []; at = state.get("at")
            for spec in chart_specs:
                data = at.explore_tool(spec)
                results.append({"id": spec["id"], "name": spec["name"], "description": spec.get("description", ""), "data": data["data"]})
            return {"search_results": results}
    node = MockNodeModule(); schema = None; prompts = None

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

try:
    from mcp_anthropic_utils import format_aralia_data_for_mcp, create_mcp_claude_prompt
except ImportError:
    print("Error: mcp_anthropic_utils.py not found. Please ensure it's in the same directory.")
    def format_aralia_data_for_mcp(search_results: list) -> str:
        if not search_results: return "<document_set status=\"empty\"></document_set>"
        xml_parts = ["<document_set>"]
        for i, result in enumerate(search_results):
            xml_parts.append(f"  <document index=\"{i+1}\" source_id=\"{result.get('id', '')}\" name=\"{result.get('name', '')}\">")
            xml_parts.append(f"    <description><![CDATA[{result.get('description', '')}]]></description>")
            xml_parts.append(f"    <content format=\"csv\"><![CDATA[\n{result.get('data', '')}\n]]></content>")
            xml_parts.append("  </document>")
        xml_parts.append("</document_set>")
        return "\n".join(xml_parts)
    def create_mcp_claude_prompt(user_question: str, xml_formatted_aralia_data: str, custom_instructions: str = None) -> str:
        instructions = custom_instructions or "Answer based on provided documents, citing sources."
        return f"Human: {instructions}\n\n<user_question>\n{user_question}\n</user_question>\n\n<documents>\n{xml_formatted_aralia_data}\n</documents>\n\nAssistant:"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ARALIA_USERNAME = os.getenv("ARALIA_USERNAME")
ARALIA_PASSWORD = os.getenv("ARALIA_PASSWORD")

if not (ANTHROPIC_API_KEY and GEMINI_API_KEY and ARALIA_USERNAME and ARALIA_PASSWORD):
    print("Error: Required API keys or credentials are not set as environment variables.")
    exit()

PLANET_URL = "https://tw-air.araliadata.io/api"
USER_QUESTION = "What is the average GDP growth rate of each state in Malaysia in 2019?, citing data from Aralia."
VERBOSE_OUTPUT = True

default_llm = ChatGoogleGenerativeAI(google_api_key=GEMINI_API_KEY, model="gemini-1.5-flash", temperature=0)
claude_llm = ChatAnthropic(anthropic_api_key=ANTHROPIC_API_KEY, model_name="claude-3-opus-20240229")
aralia_tools_instance = AraliaTools(username=ARALIA_USERNAME, password=ARALIA_PASSWORD, url=PLANET_URL)

print("--- Starting Demo 1: Optimized RAG with Aralia Data and Claude via MCP ---")
print(f"User Question: {USER_QUESTION}\n")

current_state = {
    "question": USER_QUESTION, "ai": default_llm, "at": aralia_tools_instance,
    "url": PLANET_URL, "verbose": VERBOSE_OUTPUT, "username": ARALIA_USERNAME,
    "password": ARALIA_PASSWORD, "search_results": [], "response": None,
    "final_response": None, "condition": None, "language": "english",
    "interpretation_prompt": None
}

print("\n--- Running Aralia Search Agent ---")
try:
    search_agent_output_state = node.aralia_search_agent(current_state)
    current_state.update(search_agent_output_state)
    if VERBOSE_OUTPUT:
        print("Search Agent Output (candidate datasets):")
        if isinstance(current_state.get("response"), list):
            for ds in current_state.get("response", []): print(f"  - ID: {ds.get('id')}, Name: {ds.get('name')}")
        else: print(current_state.get("response"))
except Exception as e: print(f"Error in Aralia Search Agent: {e}"); exit()
if not current_state.get("response"): print("\nNo datasets found. Exiting."); exit()

print("\n--- Running Analytics Planning Agent ---")
try:
    planning_agent_input_state = current_state.copy()
    planning_agent_output_state = node.analytics_planning_agent(planning_agent_input_state)
    current_state.update(planning_agent_output_state)
    if VERBOSE_OUTPUT: print("Planning Agent Output (chart specifications):"); print(current_state.get("response"))
except Exception as e: print(f"Error in Analytics Planning Agent: {e}"); exit()
if not current_state.get("response") or not current_state.get("response", {}).get("charts"): print("\nNo analysis plan. Exiting."); exit()

print("\n--- Running Filter Decision Agent ---")
try:
    filter_decision_input_state = current_state.copy()
    filter_decision_output_state = node.filter_decision_agent(filter_decision_input_state)
    current_state.update(filter_decision_output_state)
    if VERBOSE_OUTPUT: print("Filter Decision Agent Output:"); print(current_state.get("response"))
except Exception as e: print(f"Error in Filter Decision Agent: {e}"); exit()

print("\n--- Running Analytics Execution Agent ---")
try:
    analytics_execution_input_state = current_state.copy()
    analytics_execution_output_state = node.analytics_execution_agent(analytics_execution_input_state)
    current_state.update(analytics_execution_output_state)
    processed_datasets = current_state.get("search_results", [])
    if VERBOSE_OUTPUT:
        print(f"Analytics Execution Agent Output ({len(processed_datasets)} processed dataset(s)):")
        for i, ds_result in enumerate(processed_datasets):
            print(f"  Dataset {i+1}: Name: {ds_result.get('name')}")
            data_preview = ds_result.get('data', ''); print(f"    Data Preview (first 200 chars): {data_preview[:200]}..." if isinstance(data_preview, str) else f"    Data: (type: {type(data_preview)})")
except Exception as e: print(f"Error in Analytics Execution Agent: {e}"); exit()
if not current_state.get("search_results"): print("\nNo data retrieved. Exiting."); exit()

print("\n--- Preparing for MCP-Compliant Interpretation with Claude ---")
xml_formatted_data = format_aralia_data_for_mcp(current_state["search_results"])
if VERBOSE_OUTPUT: print("\nXML Formatted Aralia Data (for Claude via MCP):\n", xml_formatted_data)

claude_system_instructions = """You are an expert financial and policy analyst.
Please answer the user's question based *only* on the information contained within the provided XML documents.
Your answer should be comprehensive, directly addressing all parts of the question.
When you use information from a document, you MUST cite it using its index and name, for example: [evidence from document 1: Dataset XYZ Name].
Structure your response clearly. If comparing, use comparative language and structure.
If the documents do not contain sufficient information to answer a part of the question, explicitly state that.
Limit your response to approximately 300-500 words.
"""
mcp_prompt_for_claude = create_mcp_claude_prompt(USER_QUESTION, xml_formatted_data, custom_instructions=claude_system_instructions)
if VERBOSE_OUTPUT: print("\nMCP-Compliant Prompt for Claude:\n", mcp_prompt_for_claude)

print("\n--- Invoking Claude for Interpretation ---")
try:
    claude_response_message = claude_llm.invoke(mcp_prompt_for_claude)
    final_answer = claude_response_message.content if hasattr(claude_response_message, 'content') else str(claude_response_message)
    current_state["final_response"] = final_answer
    print("\n--- Claude's Interpretation (Evidence-Based Answer) ---")
    print(final_answer)
except Exception as e:
    print(f"Error during Claude interpretation: {e}")
    current_state["final_response"] = "Error: Could not get interpretation from Claude."

print("\n--- Demo 1 Finished ---")