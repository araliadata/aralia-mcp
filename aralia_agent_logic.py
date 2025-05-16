# Save this as aralia_agent_logic.py
import os
import sys
import pandas as pd 
import json 

# Attempt to import actual Aralia components
try:
    from aralia_openrag import aralia_tools, node
    from aralia_openrag.aralia_tools import AraliaTools
    ARALIA_LIBRARY_AVAILABLE = True
    print("INFO: Successfully imported aralia_openrag library.", file=sys.stderr)
except ImportError:
    ARALIA_LIBRARY_AVAILABLE = False
    print("WARNING: aralia_openrag library not found. Using mock objects for Aralia components.", file=sys.stderr)
    
    # --- Mock Objects (if aralia_openrag is not available) ---
    class AraliaTools:
        def __init__(self, username, password, url):
            print(f"Mock AraliaTools initialized for {url} (username: {username})", file=sys.stderr)
        def search_tool(self, query, **kwargs):
            print(f"Mock search_tool called with query: {query}", file=sys.stderr)
            return {"mock_ds_1": {"id": "mock_ds_1", "name": "Mock Dataset 1: GDP Data", "description": "Mock GDP data for various regions.", 
                                  "columns_metadata": [{"columnID": "col1", "name": "Year", "type": "date"}, {"columnID": "col2", "name": "Region", "type": "nominal"}, {"columnID": "col3", "name": "GDP_Growth_Rate", "type": "float"}]}}
        
        def column_metadata_tool(self, datasets_list_from_search_agent_response: list, **kwargs):
            print(f"Mock column_metadata_tool called with {len(datasets_list_from_search_agent_response)} dataset(s)", file=sys.stderr)
            processed_datasets_metadata = {}
            if isinstance(datasets_list_from_search_agent_response, list) and datasets_list_from_search_agent_response:
                 for ds_info in datasets_list_from_search_agent_response: 
                    ds_id = ds_info['id']
                    processed_datasets_metadata[ds_id] = { 
                        "id": ds_id, "name": ds_info.get('name', 'Mock Name'), "description": ds_info.get('description', 'Mock Desc'),
                        "sourceURL": "mock_url", 
                        "columns": { 
                            "col1": {"columnID": "col1", "name": "Year", "type": "date", "displayName":"Year"}, 
                            "col2": {"columnID": "col2", "name": "Region", "type": "nominal", "displayName":"Region"}, 
                            "col3": {"columnID": "col3", "name": "GDP_Growth_Rate", "type": "float", "displayName":"GDP Growth Rate (%)"}
                        }
                    }
            return processed_datasets_metadata

        def filter_option_tool(self, chart_spec_list: list, **kwargs):
            print(f"Mock filter_option_tool called with {len(chart_spec_list)} chart_spec(s)", file=sys.stderr)
            for spec in chart_spec_list:
                if "filter" in spec and isinstance(spec["filter"], list):
                    for f_col in spec["filter"]:
                        f_col['values'] = ["MockOption1", "MockOption2"]
            return 

        def explore_tool(self, charts_list: list, **kwargs): 
            print(f"Mock AraliaTools.explore_tool called with {len(charts_list)} chart_spec(s)", file=sys.stderr)
            for chart_spec in charts_list: 
                dataset_name = chart_spec.get("name", "Mock Dataset")
                mock_df_data_dict = {
                    "Year": [2019, 2019, 2020], "Region": ["RegionA", "RegionB", "RegionA"],
                    "GDP_Growth_Rate": [2.5, 3.0, 1.0]
                }
                mock_df = pd.DataFrame(mock_df_data_dict)
                chart_spec["json_data"] = mock_df.head(400).to_json(force_ascii=False, orient='records')
                print(f"  Added mock 'json_data' to chart_spec: {dataset_name}", file=sys.stderr)
            return 

    class MockNodeModule:
        def aralia_search_agent(self, state):
            print("Mock node.aralia_search_agent called", file=sys.stderr)
            at = state.get("at")
            datasets_dict = at.search_tool(state["question"])
            filtered_datasets_list = list(datasets_dict.values()) if datasets_dict else []
            return {"response": filtered_datasets_list}

        def analytics_planning_agent(self, state):
            print("Mock node.analytics_planning_agent called", file=sys.stderr)
            candidate_datasets_list = state.get("response", []) 
            if not candidate_datasets_list: return {"response": []}
            at = state.get("at")
            enriched_datasets_metadata_dict = at.column_metadata_tool(candidate_datasets_list)
            if not enriched_datasets_metadata_dict: return {"response": []}
            first_dataset_id = list(enriched_datasets_metadata_dict.keys())[0]
            first_dataset_info = enriched_datasets_metadata_dict[first_dataset_id]
            mock_chart_spec = {
                "id": first_dataset_id, "name": first_dataset_info['name'], "description": first_dataset_info['description'],
                "sourceURL": first_dataset_info['sourceURL'], 
                "x": [{"columnID": "col1", "name": "Year", "type":"date", "format": "year", "displayName":"Year"}],
                "y": [{"columnID": "col3", "name": "GDP_Growth_Rate", "type":"float", "calculation": "avg", "displayName":"GDP Growth Rate (%)"}],
                "filter":[{"columnID": "col2", "name": "Region", "type":"nominal", "format": "", "operator":"in", "value": ["RegionA", "RegionB"], "displayName":"Region"}]
            }
            return {"response": [mock_chart_spec]} 

        def filter_decision_agent(self, state):
            print("Mock node.filter_decision_agent called", file=sys.stderr)
            chart_specs_list = state.get("response", [])
            state.get("at").filter_option_tool(chart_specs_list) 
            return {"response": chart_specs_list} 

        def analytics_execution_agent(self, state):
            print("Mock node.analytics_execution_agent called", file=sys.stderr)
            chart_specs_list = state.get("response", []) 
            state.get("at").explore_tool(chart_specs_list) 
            return {"search_results": [chart_specs_list]}
    
    if not ARALIA_LIBRARY_AVAILABLE:
        node = MockNodeModule() # Assign the mock if the real 'node' couldn't be imported

# --- Global Instances ---
default_llm_instance = None
aralia_tools_instance_global = None
INITIALIZATION_ATTEMPTED = False
INITIALIZATION_SUCCESSFUL = False

def initialize_global_instances():
    global default_llm_instance, aralia_tools_instance_global, INITIALIZATION_ATTEMPTED, INITIALIZATION_SUCCESSFUL

    if INITIALIZATION_ATTEMPTED: # Avoid re-initializing if already attempted
        return INITIALIZATION_SUCCESSFUL
    INITIALIZATION_ATTEMPTED = True

    ARALIA_USERNAME = os.getenv("ARALIA_USERNAME")
    ARALIA_PASSWORD = os.getenv("ARALIA_PASSWORD")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    PLANET_URL = os.getenv("ARALIA_PLANET_URL", "https://tw-air.araliadata.io/api")

    if not (ARALIA_USERNAME and ARALIA_PASSWORD and GEMINI_API_KEY):
        print("ERROR: Aralia/Gemini credentials not fully configured in environment variables.", file=sys.stderr)
        INITIALIZATION_SUCCESSFUL = False
        return False

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        default_llm_instance = ChatGoogleGenerativeAI(
            google_api_key=GEMINI_API_KEY, model="gemini-1.5-flash", temperature=0
        )
        if ARALIA_LIBRARY_AVAILABLE:
            aralia_tools_instance_global = AraliaTools(
                username=ARALIA_USERNAME, password=ARALIA_PASSWORD, url=PLANET_URL
            )
        else: # Use mock if library not found
             aralia_tools_instance_global = AraliaTools( # Using the defined mock AraliaTools
                username=ARALIA_USERNAME, password=ARALIA_PASSWORD, url=PLANET_URL
            )
        print("INFO: Global instances initialized successfully.", file=sys.stderr)
        INITIALIZATION_SUCCESSFUL = True
        return True
    except Exception as e:
        print(f"ERROR: Failed to initialize global instances for agent logic: {e}", file=sys.stderr)
        INITIALIZATION_SUCCESSFUL = False
        return False

def fetch_aralia_evidence_for_mcp(user_question: str, verbose: bool = False) -> list:
    if not INITIALIZATION_SUCCESSFUL:
        print("ERROR: Agent logic dependencies not initialized. Call initialize_global_instances() first or check env vars.", file=sys.stderr)
        return [{"error": "Agent logic dependencies not initialized."}]

    current_state = {
        "question": user_question, "ai": default_llm_instance, "at": aralia_tools_instance_global,
        "url": os.getenv("ARALIA_PLANET_URL", "https://tw-air.araliadata.io/api"), 
        "verbose": verbose, "username": os.getenv("ARALIA_USERNAME"),
        "password": os.getenv("ARALIA_PASSWORD"), "search_results": [], "response": None,
    }

    try:
        if verbose: print("AgentLogic: Running Aralia Search Agent...", file=sys.stderr)
        search_output = node.aralia_search_agent(current_state)
        current_state.update(search_output)
        if not current_state.get("response") or not isinstance(current_state.get("response"), list) or not current_state.get("response"):
            return [{"error": "No datasets found by search agent"}]

        if verbose: print("AgentLogic: Running Analytics Planning Agent...", file=sys.stderr)
        planning_output = node.analytics_planning_agent(current_state)
        current_state.update(planning_output)
        planned_charts_specs = current_state.get("response")
        if not planned_charts_specs or not isinstance(planned_charts_specs, list) or \
           not (len(planned_charts_specs) > 0 and isinstance(planned_charts_specs[0], dict) and planned_charts_specs[0].get("id")):
            return [{"error": "No analysis plan generated"}]

        if verbose: print("AgentLogic: Running Filter Decision Agent...", file=sys.stderr)
        filter_output = node.filter_decision_agent(current_state)
        current_state.update(filter_output)
        
        if verbose: print("AgentLogic: Running Analytics Execution Agent...", file=sys.stderr)
        execution_output = node.analytics_execution_agent(current_state)
        current_state.update(execution_output)
        
        processed_data_wrapper = current_state.get("search_results", [])
        if not processed_data_wrapper or not isinstance(processed_data_wrapper, list) or \
           len(processed_data_wrapper) == 0 or not isinstance(processed_data_wrapper[0], list) or \
           not (len(processed_data_wrapper[0]) > 0 and isinstance(processed_data_wrapper[0][0], dict) and \
                processed_data_wrapper[0][0].get("json_data") is not None):
            if verbose: print(f"AgentLogic: No json_data found. Structure: {processed_data_wrapper}", file=sys.stderr)
            return [{"error": "No data snippets retrieved or unexpected format from analytics_execution_agent"}]
        
        return processed_data_wrapper

    except Exception as e:
        if verbose: print(f"AgentLogic: Error during Aralia pipeline: {e}", file=sys.stderr)
        return [{"error": f"Error in Aralia pipeline: {str(e)}"}]
