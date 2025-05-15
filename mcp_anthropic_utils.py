# Save this as mcp_anthropic_utils.py

def format_aralia_data_for_mcp(search_results: list) -> str:
    """
    Formats the search results from Aralia into an MCP-compliant XML string
    for Claude.

    Args:
        search_results: A list of dictionaries, where each dictionary
                        represents a dataset and should contain 'name'
                        and 'data' (as a CSV string or similar textual format).
                        It might also contain 'description' or 'id'.
    Returns:
        An XML string representing the formatted data.
    """
    if not search_results:
        return "<document_set status=\"empty\"></document_set>"

    xml_parts = ["<document_set>"]
    for i, result in enumerate(search_results):
        dataset_name = result.get("name", f"Dataset {i+1}")
        # Assuming 'data' contains the CSV string.
        dataset_data = result.get("data", "No data available for this dataset.")
        if not isinstance(dataset_data, str):
            # Fallback if data is not a string
            dataset_data = str(dataset_data)

        dataset_id = result.get("id", f"dataset_{i+1}")
        description = result.get("description", "No description available.")

        xml_parts.append(f"  <document index=\"{i+1}\" source_id=\"{dataset_id}\" name=\"{dataset_name}\">")
        xml_parts.append(f"    <description><![CDATA[{description}]]></description>")
        xml_parts.append(f"    <content format=\"csv\"><![CDATA[\n{dataset_data}\n]]></content>")
        xml_parts.append("  </document>")
    xml_parts.append("</document_set>")
    return "\n".join(xml_parts)

def create_mcp_claude_prompt(user_question: str, xml_formatted_aralia_data: str, custom_instructions: str = None) -> str:
    """
    Creates an MCP-compliant prompt for Claude, incorporating the user question
    and the XML-formatted Aralia data.

    Args:
        user_question: The user's question.
        xml_formatted_aralia_data: Aralia data formatted as an XML string.
        custom_instructions: Optional custom instructions for Claude.

    Returns:
        A string representing the full prompt for Claude.
    """

    instructions = custom_instructions if custom_instructions else \
    """You are an AI assistant specialized in analyzing data and providing evidence-based answers.
Please answer the following question based *only* on the provided documents.
Clearly cite the document index and name (e.g., "[evidence from document 1: Dataset XYZ Name]") for any claims or data points you use from the documents.
If the documents do not contain enough information to answer the question, please state that clearly.
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

class AraliaDataset:
    """
    A simple class to hold dataset information, especially if data is pandas DataFrame.
    This class is not strictly used in the current demo script's MCP formatting
    if 'data' is already a CSV string, but can be useful for preparing the data.
    """
    def __init__(self, id, name, description, data_df):
        self.id = id
        self.name = name
        self.description = description
        self.data_df = data_df # Expects a pandas DataFrame

    def to_dict_for_mcp(self):
        """Converts dataset to dict with data as CSV string for MCP formatting."""
        import pandas as pd
        csv_data = "No data available or dataset is empty."
        if self.data_df is not None and not self.data_df.empty:
            if isinstance(self.data_df, pd.DataFrame):
                csv_data = self.data_df.to_csv(index=False)
            else: # if data_df is already a CSV string by mistake
                csv_data = str(self.data_df)
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "data": csv_data
        }