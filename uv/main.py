"""
A FastMCP server that provides tools for searching related data to user's query.
"""
from graphs import AssistantGraph
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

assistant_graph = AssistantGraph()

mcp = FastMCP("data-search-server")


@mcp.tool()
def get_related_data(query: str) -> str:
    """
    Get the related data to user's query.

    Args:
        query (str): The user's query
    
    Returns:
        charts of realted data
    """
    return assistant_graph(
        {
            "question": query,
            "llm": os.environ['GOOGLE_API_KEY'],
            "username": os.environ["ARALIA_USERNAME"],
            "password": os.environ["ARALIA_PASSWORD"],
        }
    )['response']


if __name__ == "__main__":
    print("Starting MCP server...")
    mcp.run(transport='stdio')
