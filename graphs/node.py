import json
import time
from config import setting, exec_time
from . import prompts
from .state import BasicState
from . import schema
import re


def aralia_search_agent(state: BasicState):
    # search multi dataset
    exec_time.append(time.perf_counter())
    datasets = state["at"].search_tool(state["question"])
    exec_time.append(time.perf_counter())
    extract_prompt = prompts.simple_datasets_extract_template.invoke(
        {"question": state["question"], "datasets": datasets}
    )

    structured_llm = state["llm"].with_structured_output(schema.datasets_extract_output)

    for _ in range(5):
        try:
            # extract datasets
            response = structured_llm.invoke(extract_prompt).dict()

            filtered_datasets = [datasets[item] for item in response["dataset_key"]]
            break
        except Exception as e:
            if setting["debug"]:
                print(f"發生錯誤: {e}")
            continue
    else:
        raise RuntimeError("無法找到可能回答問題的資料集，程式終止")

    if setting["debug"]:
        print("# aralia_search_agent:\n")
        print([item["name"] for item in datasets.values()], end="\n\n")
        print([item["name"] for item in filtered_datasets], end="\n\n")

    return {"response": filtered_datasets}


def analytics_planning_agent(state: BasicState):
    exec_time.append(time.perf_counter())
    datasets = state["at"].column_metadata_tool(state["response"])
    exec_time.append(time.perf_counter())

    if not datasets:
        raise RuntimeError("無法跟搜尋到的星球要資料，程式終止")

    plot_chart_prompt = prompts.chart_ploting_template.invoke(  # extract column
        {
            "question": state["question"],
            "datasets": datasets,
            "admin_level": prompts.admin_level,
        }
    )

    for _ in range(5):
        try:
            response = state["llm"].invoke(plot_chart_prompt)

            if setting["debug"]:
                print(response.content, end="\n\n")

            response_json = json.loads(
                list(re.finditer(r"```json(.*?)```", response.content, re.DOTALL))[
                    -1
                ].group(1)
            )

            filtered_datasets = [
                {
                    **{
                        k: v for k, v in datasets[chart["id"]].items() if k != "columns"
                    },
                    "x": [
                        {
                            **datasets[chart["id"]]["columns"][x["columnID"]],
                            "format": x["format"]
                            if x["type"] not in ["date", "datetime", "space"]
                            else x["format"]
                            if (
                                (
                                    x["type"] in ["date", "datetime"]
                                    and (
                                        x["format"] in prompts.format["date"]
                                        or (_ := None)
                                    )
                                )
                                or (
                                    x["type"] == "space"
                                    and (
                                        x["format"] in prompts.format["space"]
                                        or (_ := None)
                                    )
                                )
                            )
                            else x["format"],
                        }
                        for x in chart["x"]
                    ],
                    "y": [
                        {
                            **datasets[chart["id"]]["columns"][y["columnID"]],
                            "calculation": y["calculation"],
                        }
                        for y in chart["y"]
                        if y["type"] in ["integer", "float"]
                        and (
                            y["calculation"] in prompts.format["calculation"]
                            or (_ := None)  # 檢查計算方法
                        )
                    ],
                    "filter": [
                        {
                            **datasets[chart["id"]]["columns"][f["columnID"]],
                            "format": f["format"]
                            if f["type"] not in ["date", "datetime", "space"]
                            else f["format"]
                            if (
                                (
                                    f["type"] in ["date", "datetime"]
                                    and (
                                        f["format"] in prompts.format["date"]
                                        or (_ := None)
                                    )
                                )
                                or (
                                    f["type"] == "space"
                                    and (
                                        f["format"] in prompts.format["space"]
                                        or (_ := None)
                                    )
                                )
                            )
                            else f["format"],
                        }
                        for f in chart["filter"]
                    ],
                }
                for chart in response_json["charts"]
            ]
            break
        except Exception as e:
            if setting["debug"]:
                print(f"發生錯誤: {e}")
            continue
    else:
        raise RuntimeError("AI模型無法產出準確的api調用")

    if setting["debug"]:
        print("# analytics_planning_agent:\n")
        print(json.dumps(filtered_datasets, ensure_ascii=False, indent=2), end="\n\n")

    return {"response": filtered_datasets}


def filter_decision_agent(state: BasicState):
    exec_time.append(time.perf_counter())
    state["at"].filter_option_tool(state["response"])
    exec_time.append(time.perf_counter())

    prompt = prompts.query_generate_template.invoke(
        {
            "question": state["question"],
            "response": state["response"],
        }
    )

    structured_llm = state["llm"].with_structured_output(schema.query_list)

    for _ in range(5):
        try:
            response = structured_llm.invoke(prompt).dict()["querys"]
            for chart in response:
                for x in chart["x"]:
                    if x["type"] not in {"date", "datetime", "space"}:
                        x.pop("format")
                for filter in chart["filter"]:
                    if filter["type"] not in {"date", "datetime", "space"}:
                        filter.pop("format")
                chart["filter"] = [chart["filter"]]
            break
        except Exception as e:
            if setting["debug"]:
                print(f"發生錯誤: {e}")
            continue
    else:
        raise RuntimeError("AI模型無法選擇準確的filter value")

    if setting["debug"]:
        print("# filter_decision_agent\n")
        print(json.dumps(response, ensure_ascii=False, indent=2), end="\n\n")

    return {"response": response}


def analytics_execution_agent(state: BasicState):
    if setting["debug"]:
        print("# analytics_execution_agent:\n")

    exec_time.append(time.perf_counter())
    state["at"].explore_tool(state["response"])

    return {
        "response": [state["response"]],
    }


def interpretation_agent(state: BasicState):
    exec_time.append(time.perf_counter())
    messages = [
        {
            "role": "system",
            "content": "You are a Senior Data Analyst with expertise in analyzing statistical data. You excel at uncovering insights from the data and identifying relationships between different datasets.",
        },
        {
            "role": "user",
            "content": f"""
                Question: ***{state["question"]}***
                Information: {state["response"]}

                I have already gathered relevant charts based on the user's question.
                Please analyze the charts above in detail, then provide a detailed answer to the question, and give a conclusion within 300 words.
                Please provide with the question's language.
            """,
        },
    ]

    response = state["llm"].invoke(messages)

    exec_time.append(time.perf_counter())
    if setting["debug"]:
        print("# interpretation_agent:\n")
        print(response.content, end="\n\n")

    return {"final_response": response.content}


def print_exec_time():
    """
    打印每個步驟的執行時間，從第二個步驟開始計算
    """

    for i, times in enumerate(exec_time):
        if i > 0:  # 從第二個開始計算
            print(f"Time taken for {i}th step: {times - exec_time[i - 1]} seconds")
