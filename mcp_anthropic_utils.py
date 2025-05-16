# Save this as mcp_anthropic_utils.py
import json

def format_aralia_data_for_mcp(search_results_wrapper: list) -> str:
    """
    Formats the results from Aralia (expected to be a list containing a list of 
    chart_specs, where each spec has 'json_data') into an MCP-compliant XML string.

    Args:
        search_results_wrapper: Expected structure: 
                                [[{spec1_with_json_data}, {spec2_with_json_data}, ...]]
    Returns:
        An XML string representing the formatted data.
    """
    if not search_results_wrapper or not isinstance(search_results_wrapper, list) or \
       len(search_results_wrapper) == 0 or not isinstance(search_results_wrapper[0], list):
        return "<document_set status=\"empty_or_invalid_wrapper\"></document_set>"

    actual_specs_with_data_list = search_results_wrapper[0]
    
    if not actual_specs_with_data_list:
        return "<document_set status=\"empty_spec_list\"></document_set>"

    xml_parts = ["<document_set type=\"aralia_datasets_with_json_data_snippets\">"]
    for i, spec_with_data in enumerate(actual_specs_with_data_list):
        if not isinstance(spec_with_data, dict):
            xml_parts.append(f"  <document index=\"{i+1}\" source_id=\"unknown_spec_{i+1}\" name=\"Invalid Specification Object\">")
            xml_parts.append(f"    <description><![CDATA[Result object is not in the expected dictionary format.]]></description>")
            xml_parts.append(f"    <content format=\"error\"><![CDATA[Invalid structure: {type(spec_with_data)}]]></content>")
            xml_parts.append("  </document>")
            continue

        dataset_name = spec_with_data.get("name", f"Dataset from Spec {i+1}")
        dataset_id = spec_with_data.get("id", f"spec_{i+1}")
        # Use the description from the spec itself if available
        description = spec_with_data.get("description", f"Data snippet for analytics specification: {dataset_name}")
        
        dataset_data_json_str = spec_with_data.get("json_data", "\"No data available for this dataset specification.\"") # Ensure valid JSON string

        xml_parts.append(f"  <document index=\"{i+1}\" source_id=\"{dataset_id}\" name=\"{dataset_name}\">")
        xml_parts.append(f"    <description><![CDATA[{description}]]></description>")
        xml_parts.append(f"    <content format=\"json_string_dataframe_snippet\"><![CDATA[\n{dataset_data_json_str}\n]]></content>")
        xml_parts.append("  </document>")
    xml_parts.append("</document_set>")
    return "\n".join(xml_parts)

def create_mcp_claude_prompt(user_question: str, xml_formatted_aralia_data: str, custom_instructions: str = None) -> str:
    """
    Creates an MCP-compliant prompt for Claude.
    """
    instructions = custom_instructions if custom_instructions else \
    """You are an AI assistant specialized in analyzing data and providing evidence-based answers.
Please answer the following question based *only* on the provided documents.
The content of each document is a JSON string, which represents a snippet of a dataset (typically the first 400 rows of a pandas DataFrame).
Your answer should be comprehensive, directly addressing all parts of the question.
When you use information from a document, you MUST cite it using its index and name, for example: [evidence from document 1: Dataset XYZ Name].
Structure your response clearly. If comparing, use comparative language and structure.
If the documents do not contain sufficient information to answer a part of the question, explicitly state that.
Provide a concise and comprehensive answer.
"""
    prompt = f"""Human: {instructions}

<user_question>
{user_question}
</user_question>

<documents>
{xml_formatted_aralia_data}
</documents>

Assistant:
"""
    return prompt