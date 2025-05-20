# 標準庫導入
import time

# 第三方庫導入
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_openai import ChatOpenAI

# 本地模組導入
from . import aralia_tools
from . import node
from .state import BasicState
from config import exec_time

class AssistantGraph:
    def __init__(self):
        builder = StateGraph(BasicState)

        # add node
        builder.add_node("aralia_search_agent", node.aralia_search_agent)
        builder.add_node("analytics_planning_agent",
                         node.analytics_planning_agent)
        builder.add_node("filter_decision_agent",
                         node.filter_decision_agent)
        builder.add_node("analytics_execution_agent",
                         node.analytics_execution_agent)

        builder.set_entry_point("aralia_search_agent")

        # add edge
        builder.add_edge("aralia_search_agent", "analytics_planning_agent")
        builder.add_edge("analytics_planning_agent", "filter_decision_agent")
        builder.add_edge("filter_decision_agent",
                         "analytics_execution_agent")
        builder.add_edge("analytics_execution_agent", END)

        self.graph = builder.compile()

        # print(graph.get_graph().draw_mermaid()) # draw graph for debug

    def __call__(self, request):
        exec_time.append(time.perf_counter())
        request['llm'] = ChatGoogleGenerativeAI(
            api_key=request['llm'], model="gemini-2.0-flash", temperature=0)
        # request['llm'] = ChatOpenAI(
        #     api_key=request['llm'], model="gpt-4o", temperature=0)
        request['at'] = aralia_tools.AraliaTools(
            request['username'], request['password'])
        
        return self.graph.invoke(request)
