import os
if "COLAB_GPU" not in os.environ:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("python-dotenv library not found. Please install it with 'pip install python-dotenv' if you are using a .env file for API keys.")

import pandas as pd
import json # For mock json_data

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
            # search_tool returns a DICT of datasets keyed by ID
            return {"mock_ds_1": {"id": "mock_ds_1", "name": "Mock Dataset 1: GDP Data", "description": "Mock GDP data for various regions.", 
                                  "columns_metadata": [{"columnID": "col1", "name": "Year", "type": "date"}, {"columnID": "col2", "name": "Region", "type": "nominal"}, {"columnID": "col3", "name": "GDP_Growth_Rate", "type": "float"}]}}
        
        def column_metadata_tool(self, datasets_list_from_search_agent_response: list, **kwargs):
            # Input is a list of dataset dicts (the *value* part of aralia_search_agent's output after filtering)
            print(f"Mock column_metadata_tool called with {len(datasets_list_from_search_agent_response)} dataset(s)")
            processed_datasets_metadata = {}
            if isinstance(datasets_list_from_search_agent_response, list) and datasets_list_from_search_agent_response:
                 for ds_info in datasets_list_from_search_agent_response: 
                    ds_id = ds_info['id']
                    processed_datasets_metadata[ds_id] = { # Returns a DICT keyed by dataset_id
                        "id": ds_id, "name": ds_info.get('name', 'Mock Name'), "description": ds_info.get('description', 'Mock Desc'),
                        "sourceURL": "mock_url", # Needed by explore_tool
                        "columns": { 
                            "col1": {"columnID": "col1", "name": "Year", "type": "date", "displayName":"Year"}, 
                            "col2": {"columnID": "col2", "name": "Region", "type": "nominal", "displayName":"Region"}, 
                            "col3": {"columnID": "col3", "name": "GDP_Growth_Rate", "type": "float", "displayName":"GDP Growth Rate (%)"}
                        }
                    }
            return processed_datasets_metadata

        def filter_option_tool(self, chart_spec_list: list, **kwargs):
            print(f"Mock filter_option_tool called with {len(chart_spec_list)} chart_spec(s)")
            # This tool modifies the chart_spec_list in-place by adding 'values' to filters
            for spec in chart_spec_list:
                if "filter" in spec and isinstance(spec["filter"], list):
                    for f_col in spec["filter"]:
                        f_col['values'] = ["MockOption1", "MockOption2"] # Add mock filter options
            return # Returns None, modifies in place

        def explore_tool(self, charts_list: list, **kwargs): # AraliaTools.explore_tool takes a list of specs
            print(f"Mock AraliaTools.explore_tool called with {len(charts_list)} chart_spec(s)")
            for chart_spec in charts_list: # It iterates and MODIFIES IN PLACE
                dataset_id = chart_spec.get("id", "mock_ds_1")
                dataset_name = chart_spec.get("name", "Mock Dataset")
                mock_df_data_dict = { # Using dict for to_json()
                    "Year": [2019, 2019, 2020],
                    "Region": ["RegionA", "RegionB", "RegionA"],
                    "GDP_Growth_Rate": [2.5, 3.0, 1.0]
                }
                mock_df = pd.DataFrame(mock_df_data_dict)
                chart_spec["json_data"] = mock_df.head(400).to_json(force_ascii=False, orient='records') # Use common JSON orientation
                print(f"  Added mock 'json_data' to chart_spec: {dataset_name}")
            return # explore_tool returns None, modifies list in-place

    class MockNodeModule:
        def aralia_search_agent(self, state):
            print("Mock aralia_search_agent called")
            at = state.get("at")
            datasets_dict = at.search_tool(state["question"]) # Gets a dict
            # The actual agent uses LLM to filter keys from datasets_dict
            # For mock, assume we use all datasets found (if any)
            filtered_datasets_list = list(datasets_dict.values()) if datasets_dict else []
            return {"response": filtered_datasets_list}

        def analytics_planning_agent(self, state):
            print("Mock analytics_planning_agent called")
            candidate_datasets_list = state.get("response", []) 
            if not candidate_datasets_list: return {"response": []}
            
            at = state.get("at")
            # The planning agent calls column_metadata_tool with the list of dataset dicts
            enriched_datasets_metadata_dict = at.column_metadata_tool(candidate_datasets_list)
            
            # The actual agent uses LLM to generate chart_specs. Mocking one.
            # It should use IDs from enriched_datasets_metadata_dict if it needs to reference them.
            if not enriched_datasets_metadata_dict: return {"response": []}
            
            # Use the first dataset ID from the enriched metadata for the mock spec
            first_dataset_id = list(enriched_datasets_metadata_dict.keys())[0]
            first_dataset_name = enriched_datasets_metadata_dict[first_dataset_id]['name']
            first_dataset_description = enriched_datasets_metadata_dict[first_dataset_id]['description']

            mock_chart_spec = {
                "id": first_dataset_id, "name": first_dataset_name, "description": first_dataset_description,
                "sourceURL": enriched_datasets_metadata_dict[first_dataset_id]['sourceURL'], # important for explore_tool
                "x": [{"columnID": "col1", "name": "Year", "type":"date", "format": "year", "displayName":"Year"}],
                "y": [{"columnID": "col3", "name": "GDP_Growth_Rate", "type":"float", "calculation": "avg", "displayName":"GDP Growth Rate (%)"}],
                "filter":[{"columnID": "col2", "name": "Region", "type":"nominal", "format": "", "operator":"in", "value": ["RegionA", "RegionB"], "displayName":"Region"}]
            }
            return {"response": [mock_chart_spec]} 

        def filter_decision_agent(self, state):
            print("Mock filter_decision_agent called")
            chart_specs_list = state.get("response", [])
            at = state.get("at")
            at.filter_option_tool(chart_specs_list) # Modifies in-place
            # The actual agent would use LLM to decide on filter values based on question and options
            # For mock, we just pass through the (potentially modified by filter_option_tool) list
            return {"response": chart_specs_list} 

        def analytics_execution_agent(self, state):
            print("Mock node.analytics_execution_agent called")
            chart_specs_list = state.get("response", []) 
            at = state.get("at")
            at.explore_tool(chart_specs_list) # Modifies chart_specs_list in-place, adding 'json_data'
            return {"search_results": [chart_specs_list]} # Returns list containing the list of modified specs

    node = MockNodeModule(); schema = None; prompts = None


from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

try:
    from mcp_anthropic_utils import format_aralia_data_for_mcp, create_mcp_claude_prompt
except ImportError:
    print("Error: mcp_anthropic_utils.py not found. Please ensure it's in the same directory.")
    def format_aralia_data_for_mcp(search_results_wrapper: list) -> str:
        if not search_results_wrapper or not isinstance(search_results_wrapper, list) or \
        len(search_results_wrapper) == 0 or not isinstance(search_results_wrapper[0], list):
            return "<document_set status=\"empty_or_invalid_wrapper\"></document_set>"
        actual_specs_with_data_list = search_results_wrapper[0]
        if not actual_specs_with_data_list: return "<document_set status=\"empty_spec_list\"></document_set>"
        xml_parts = ["<document_set type=\"aralia_datasets_with_json_data_snippets\">"]
        for i, spec_with_data in enumerate(actual_specs_with_data_list):
            if not isinstance(spec_with_data, dict):
                xml_parts.append(f"<document index=\"{i+1}\" name=\"Invalid Spec\"><content>Error</content></document>")
                continue
            dataset_name = spec_with_data.get("name", f"Dataset {i+1}")
            dataset_id = spec_with_data.get("id", f"spec_{i+1}")
            description = spec_with_data.get("description", "N/A")
            dataset_data_json_str = spec_with_data.get("json_data", "\"No data\"")
            xml_parts.append(f"<document index=\"{i+1}\" source_id=\"{dataset_id}\" name=\"{dataset_name}\"><description><![CDATA[{description}]]></description><content format=\"json_string_dataframe_snippet\"><![CDATA[\n{dataset_data_json_str}\n]]></content></document>")
        xml_parts.append("</document_set>")
        return "\n".join(xml_parts)

    def create_mcp_claude_prompt(user_question: str, xml_formatted_aralia_data: str, custom_instructions: str = None) -> str:
        instructions = custom_instructions or "Answer based on provided documents, citing sources. Content is JSON string snippets."
        return f"Human: {instructions}\n\n<user_question>\n{user_question}\n</user_question>\n\n<documents>\n{xml_formatted_aralia_data}\n</documents>\n\nAssistant:"


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ARALIA_USERNAME = os.getenv("ARALIA_USERNAME")
ARALIA_PASSWORD = os.getenv("ARALIA_PASSWORD")

if not (ANTHROPIC_API_KEY and GEMINI_API_KEY and ARALIA_USERNAME and ARALIA_PASSWORD):
    print("Error: Required API keys or credentials are not set as environment variables.")
    exit()

PLANET_URL = "https://tw-air.araliadata.io/api" # official data
USER_QUESTION = "What is the average GDP growth rate of each state in Malaysia in 2019, citing specific data in Aralia datasets."
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
        print("Search Agent Output (candidate datasets in state['response']):")
        if isinstance(current_state.get("response"), list):
            for ds in current_state.get("response", []): print(f"  - ID: {ds.get('id')}, Name: {ds.get('name')}")
        else: print(current_state.get("response"))
except Exception as e: print(f"Error in Aralia Search Agent: {e}"); exit()

if not current_state.get("response") or not isinstance(current_state.get("response"), list) or len(current_state.get("response")) == 0:
    print("\nNo datasets found by the search agent. Exiting.")
    exit()

print("\n--- Running Analytics Planning Agent ---")
try:
    planning_agent_input_state = current_state.copy()
    planning_agent_output_state = node.analytics_planning_agent(planning_agent_input_state)
    current_state.update(planning_agent_output_state)
    if VERBOSE_OUTPUT:
        print("Planning Agent Output (chart specifications in state['response']):")
        print(current_state.get("response"))
except Exception as e:
    print(f"Error in Analytics Planning Agent: {e}")
    exit()

planned_charts_specs = current_state.get("response")
if not planned_charts_specs or not isinstance(planned_charts_specs, list) or \
   not (len(planned_charts_specs) > 0 and isinstance(planned_charts_specs[0], dict) and planned_charts_specs[0].get("id")):
    print("\nNo valid analysis plan (list of chart_specs) generated by the planning agent. Exiting.")
    exit()

print("\n--- Running Filter Decision Agent ---")
try:
    filter_decision_input_state = current_state.copy()
    filter_decision_output_state = node.filter_decision_agent(filter_decision_input_state)
    current_state.update(filter_decision_output_state)
    if VERBOSE_OUTPUT:
        print("Filter Decision Agent Output (updated chart/filter specifications in state['response']):")
        print(current_state.get("response"))
except Exception as e:
    print(f"Error in Filter Decision Agent: {e}")
    exit()

print("\n--- Running Analytics Execution Agent ---")
try:
    analytics_execution_input_state = current_state.copy()
    analytics_execution_output_state = node.analytics_execution_agent(analytics_execution_input_state)
    current_state.update(analytics_execution_output_state) 
    
    processed_data_wrapper = current_state.get("search_results", [])
    if VERBOSE_OUTPUT:
        print(f"Analytics Execution Agent Output (in state['search_results']):")
        print(processed_data_wrapper) # This will be [[spec_with_data1, ...]]
        if processed_data_wrapper and isinstance(processed_data_wrapper, list) and len(processed_data_wrapper) > 0 and isinstance(processed_data_wrapper[0], list):
            print(f"  Contains {len(processed_data_wrapper[0])} processed chart_spec(s) with data.")
            for i, spec_with_data in enumerate(processed_data_wrapper[0]):
                 print(f"  Spec {i+1}: Name: {spec_with_data.get('name')}")
                 json_data_preview = spec_with_data.get('json_data', '')
                 print(f"    json_data Preview (first 200 chars): {json_data_preview[:200]}..." if isinstance(json_data_preview, str) else f"    json_data: (type: {type(json_data_preview)})")
except Exception as e:
    print(f"Error in Analytics Execution Agent: {e}")
    exit()

# Updated check for analytics_execution_agent output
processed_data_wrapper = current_state.get("search_results", [])
if not processed_data_wrapper or not isinstance(processed_data_wrapper, list) or \
   len(processed_data_wrapper) == 0 or not isinstance(processed_data_wrapper[0], list) or \
   not (len(processed_data_wrapper[0]) > 0 and isinstance(processed_data_wrapper[0][0], dict) and \
        processed_data_wrapper[0][0].get("json_data") is not None):
    print("\nNo data (or incorrect data format with 'json_data') in search_results after analytics_execution_agent. Exiting.")
    print("Current structure of search_results:", current_state.get("search_results"))
    exit()


print("\n--- Preparing for MCP-Compliant Interpretation with Claude ---")
xml_formatted_data = format_aralia_data_for_mcp(current_state["search_results"])
if VERBOSE_OUTPUT:
    print("\nXML Formatted Aralia Data (for Claude via MCP):\n", xml_formatted_data)

claude_system_instructions = """You are an expert financial and policy analyst.
Please answer the user's question based *only* on the information contained within the provided XML documents.
The content of each document is a JSON string, which represents a snippet of a dataset (typically the first 400 rows of a pandas DataFrame, in JSON records format).
Your answer should be comprehensive, directly addressing all parts of the question.
When you use information from a document, you MUST cite it using its index and name, for example: [evidence from document 1: Dataset XYZ Name].
Structure your response clearly. If comparing, use comparative language and structure.
If the documents do not contain sufficient information to answer a part of the question, explicitly state that.
Limit your response to approximately 300-500 words.
"""
mcp_prompt_for_claude = create_mcp_claude_prompt(USER_QUESTION, xml_formatted_data, custom_instructions=claude_system_instructions)
if VERBOSE_OUTPUT:
    print("\nMCP-Compliant Prompt for Claude:\n", mcp_prompt_for_claude)

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