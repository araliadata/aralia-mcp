# Save this as mcp_anthropic_utils.py
import json

def format_aralia_data_for_mcp(processed_data_wrapper: list) -> str:
    """
    Formats the processed data from Aralia into an MCP-compliant XML string.
    The input is expected to be the 'search_results' from the analytics_execution_agent,
    which, based on the provided node code, is a list containing a single element:
    a list of chart specifications, where each specification now also holds its 'json_data'.

    Args:
        processed_data_wrapper: Expected structure from analytics_execution_agent:
                                [[{spec1_with_json_data}, {spec2_with_json_data}, ...]]
    Returns:
        An XML string representing the formatted data snippets.
    """
    if not processed_data_wrapper or not isinstance(processed_data_wrapper, list) or \
       len(processed_data_wrapper) == 0 or not isinstance(processed_data_wrapper[0], list):
        # If the structure is not as expected, return an error or empty set
        return "<document_set status=\"empty_or_invalid_data_wrapper\"><error_details>Input to format_aralia_data_for_mcp was not a list containing a list of specs.</error_details></document_set>"

    actual_specs_with_data_list = processed_data_wrapper[0]
    
    if not actual_specs_with_data_list:
        return "<document_set status=\"empty_spec_list\"></document_set>"

    xml_parts = ["<document_set type=\"aralia_datasets_with_json_data_snippets\">"]
    for i, spec_with_data in enumerate(actual_specs_with_data_list):
        if not isinstance(spec_with_data, dict):
            xml_parts.append(f"  <document index=\"{i+1}\" source_id=\"unknown_spec_{i+1}\" name=\"Invalid Specification Object\">")
            xml_parts.append(f"    <description><![CDATA[Result object is not in the expected dictionary format. Type was: {type(spec_with_data)}]]></description>")
            xml_parts.append(f"    <content format=\"error\"><![CDATA[Invalid structure]]></content>")
            xml_parts.append("  </document>")
            continue

        dataset_name = spec_with_data.get("name", f"Dataset from Spec {i+1}")
        dataset_id = spec_with_data.get("id", f"spec_{i+1}")
        # The description in the spec is about the dataset/analysis plan, not the data itself.
        # We are providing a snippet of data.
        description = spec_with_data.get("description", f"Data snippet related to analytics specification: {dataset_name}")
        
        # 'json_data' is added by AraliaTools.explore_tool to each spec
        dataset_data_json_str = spec_with_data.get("json_data", "\"No data snippet available for this specification.\"") 
        # Ensure it's a string, even if it's an error message or None
        if not isinstance(dataset_data_json_str, str):
            dataset_data_json_str = json.dumps({"error": "Data was not a JSON string.", "original_type": str(type(dataset_data_json_str))})


        xml_parts.append(f"  <document index=\"{i+1}\" source_id=\"{dataset_id}\" name=\"{dataset_name}\">")
        xml_parts.append(f"    <description><![CDATA[{description}]]></description>")
        # The content is a JSON string representing a pandas DataFrame snippet (first 400 rows)
        xml_parts.append(f"    <content format=\"json_string_dataframe_snippet\"><![CDATA[\n{dataset_data_json_str}\n]]></content>")
        xml_parts.append("  </document>")
    xml_parts.append("</document_set>")
    return "\n".join(xml_parts)

