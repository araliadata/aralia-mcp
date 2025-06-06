"""
A FastMCP server that provides tools for searching related data to user's query.
"""

from mcp import types
from graphs import AssistantGraph
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server import Server
import mcp.types as types
from mcp_src.aralia_tools import AraliaTools
from mcp_src.prompts import (
    datasets_extract_prompt,
    chart_ploting_prompt,
    query_generate_prompt,
    admin_level,
)

mcp = FastMCP("aralia-data-server")

load_dotenv()

aralia_tools = AraliaTools(
    os.environ["ARALIA_USERNAME"], os.environ["ARALIA_PASSWORD"])

data = dict()

question = "幫我用aralia回答'酒駕致死道路類別以哪種類型居多?'"
answer = "[{'sourceURL': 'https://tw-traffic.araliadata.io', 'id': 'Sp53HruAx6xZUAX5ERpKBz', 'name': '交 通事故紀錄表', 'x': [{'columnID': 'mEaKbXG9Y93uUVi9DSK9YJ', 'displayName': '道路類別', 'type': 'nominal'}], 'y': [{'columnID': 'ByGDZwjjqgQqSWvQ4iX9WF', 'displayName': '死亡人數', 'calculation': 'sum'}], 'filter': [[{'columnID': 'MqV9TaZnHWAoR2ZBNCSLyn', 'displayName': '當事者飲酒情形', 'type': 'nominal', 'operator': 'in', 'value': ['經呼氣檢測 0.16~0.25 mg/L或血液檢測 0.031%~0.05%', '經呼氣檢測 0.26~0.40 mg/L或血液檢測 0.051%~0.08%', '經呼氣檢測 0.41~0.55 mg/L或血液檢測 0.081%~0.11%', '經呼氣檢測 0.56~0.80 mg/L或血液檢測 0.111%~0.16%', '經呼氣檢測超過 0.80 mg/L或血液檢測超過 0.16%']}]], 'data': [{'x': [['市區道路']], 'values': [496]}, {'x': [['村里道路']], 'values': [169]}, {'x': [['省道']], 'values': [118]}, {'x': [['縣道']], 'values': [71]}, {'x': [['鄉道']], 'values': [47]}, {'x': [['國道']], 'values': [29]}, {'x': [['其他 ']], 'values': [25]}, {'x': [['專用道路']], 'values': [2]}]}]"


def debug(text: any):
    with open("debug.txt", "a", encoding='utf-8') as file:
        file.write(str(text))


@mcp.tool()
def search_aralia_data_first_step(question: str) -> list[str]:
    """
    First step to get related structured data to user's question from Aralia.

    Args:
        query (str): The user's question

    Returns:
        1. The related datasets to the user's question.
        2. Instruction and task to the next step's input.
    """
    data = aralia_tools.search_tool(question)

    return [
        data,
        datasets_extract_prompt,
    ]


@mcp.tool()
def search_aralia_data_second_step(datasets: list[dict]) -> list[str]:
    """
    Second step to get related structured data to user's question from Aralia.

    Args:
        datasets (list[dict]): The datasets that are related to the user's question

    Returns:
        1. The related datasets column metadata to the user's question.
        2. Instruction and task to the next step's input.
    """

    datasets_metadata = aralia_tools.column_metadata_tool(datasets)

    return [
        datasets_metadata,
        chart_ploting_prompt.format(admin_level=admin_level),
    ]


@mcp.tool()
def search_aralia_data_third_step(charts: list[dict]) -> list[str]:
    """
    Third step to get related structured data to user's question from Aralia.

    Args:
        charts (list[dict]): The charts that are related to the user's question

    Returns:
        1. aralia api request with candidate filter values
        2. Instruction and task to the next step's input.
    """

    aralia_tools.filter_option_tool(charts)

    return [
        charts,
        query_generate_prompt,
    ]


@mcp.tool()
def search_aralia_data_final_step(charts: list[dict]) -> list[dict]:
    """
    Final step to get related structured data to user's question from Aralia.
    
    Args:
        charts (list[dict]): The charts that are related to the user's question
    
    Returns:
        charts data related to the user's question
    """

    for chart in charts:
        for x in chart["x"]:
            if x["type"] not in {"date", "datetime", "space"}:
                x.pop("format")
        for filter in chart["filter"]:
            if filter["type"] not in {"date", "datetime", "space"}:
                filter.pop("format")
        chart["filter"] = [chart["filter"]]

    aralia_tools.explore_tool(charts)

    return charts

# search_aralia_data_final_step([
#     {
#       "id": "RV2dQLRtsAwuwVT3Z6Auso",
#       "name": "即時交通事故紀錄表",
#       "description": "此數據集收集了2018年~2023年和2025年的交通事故紀錄表，欄位包含了發生年度、月份、日期、時間以及事故發生時詳細內容。此數據集每7天更新A1類型和每15天更新A2類型。",
#       "siteName": "交通監控星球",
#       "sourceURL": "https://tw-traffic.araliadata.io",
#       "x": [
#         {
#           "columnID": "5KiFSVMi3YGu4wxaC2HvMm",
#           "displayName": "道路類別-第1當事者-名稱",
#           "type": "nominal",
#           "format": ""
#         }
#       ],
#       "y": [
#         {
#           "columnID": "BZwvmPvNRgDmGp4xMS3JBf",
#           "displayName": "死亡受傷人數",
#           "type": "nominal",
#           "calculation": "count"
#         }
#       ],
#       "filter": [
#         {
#           "columnID": "hzPv46vrxTgkdx5Sqxak3w",
#           "displayName": "事故類別名稱",
#           "calculation": "",
#           "type": "nominal",
#           "format": "",
#           "operator": "in",
#           "value": [
#             "A1"
#           ]
#         },
#         {
#           "columnID": "agzMY9g6GrfsPDfxvRPjGA",
#           "displayName": "肇因研判子類別名稱-主要",
#           "calculation": "",
#           "type": "nominal",
#           "format": "",
#           "operator": "in",
#           "value": [
#             "酒醉(後)駕駛",
#             "酒醉(後)駕駛失控"
#           ]
#         }
#       ]
#     }
#   ])

if __name__ == "__main__":
    mcp.run(transport="stdio")
