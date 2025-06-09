from graphs import AssistantGraph
import os
from dotenv import load_dotenv
from graphs.node import print_exec_time

load_dotenv()

assistant_graph = AssistantGraph()

question = [
    # "Malaysia Hospital Beds by District",
    "哪個縣市經呼氣檢測 0.16~0.25 mg/L或血液檢0.031%~0.05%酒駕死亡人數最多?請依照各縣市進行排序。",
    # '酒駕致死道路類別以哪種類型居多?',
    # '經呼氣檢測超過 0.80 mg/L或血液檢測超過 0.16%酒駕事故者平均年齡?',
    # '請提供4月份台北區監理所「酒駕新制再犯」課程日期。',
    # "請列出六都中經呼氣檢測 0.56~0.80 mg/L或血液檢測 0.111%~0.16%酒駕死亡及受傷人數。",
    # '各縣市死亡車禍的熱點地圖',
    # 'What is the average GDP growth rate of each state in Malaysia in 2019?',
    # 'What is the average GDP growth rate of each state in Malaysia in 2019 compared to their Gini coefficient?',
    # '請提供4月份新北市監理所「酒駕新制再犯」課程日期。',
]

for item in question:
    response = assistant_graph(
        {
            "question": item,
            "llm": os.environ["GOOGLE_API_KEY"],
            "username": os.environ["ARALIA_USERNAME"],
            "password": os.environ["ARALIA_PASSWORD"],
        }
    )["response"]
    # print(response)

print_exec_time()
