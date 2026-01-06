# src/main.py
from langgraph.graph import StateGraph, START, END
from src.state import MagazineState

# 에이전트들
from src.agents.router import run_router
from src.agents.safety import run_safety
from src.agents.vision import run_vision_analysis
from src.agents.planner import run_planner
from src.agents.editor import run_editor
from src.agents.director import run_director
from src.agents.publisher import run_publisher
from src.agents.critique import run_critique
from src.agents.formatter import run_formatter

from src.tools.paginator import organize_articles_into_pages

# src/main.py (run_paginator_node 함수만 수정하면 됨)

def run_paginator_node(state: MagazineState) -> dict:
    print("--- [Step 4.5] Paginator: Organizing Articles ---")
    
    manuscript = state.get("manuscript", {})
    articles = [manuscript] if isinstance(manuscript, dict) else manuscript

    # 도구 실행
    pages = organize_articles_into_pages(articles)
    print(f"📄 Paginator Result: Split into {len(pages)} page(s).")
    
    # ---------------------------------------------------------
    # [데이터 브릿지] Publisher가 이해하는 형태로 변환
    # ---------------------------------------------------------
    publisher_content = {"blocks": []}
    
    # 첫 번째 페이지의 기사들을 Publisher의 메인 콘텐츠로 전달
    if pages and len(pages) > 0:
        publisher_content["blocks"] = pages[0]["articles"]
        
    # 이미지 경로도 Publisher에게 전달 (state에 있는 image_path 활용)
    publisher_images = {}
    if state.get("image_path"):
        publisher_images["main_img"] = state.get("image_path")

    return {
        "pages": pages,          # 나중을 위해 원본 보존
        "content": publisher_content, # Publisher용
        "images": publisher_images    # Publisher용
    }

def build_graph():
    workflow = StateGraph(MagazineState)

    # 1. 노드 등록
    workflow.add_node("router", run_router)
    workflow.add_node("safety", run_safety)
    workflow.add_node("vision", run_vision_analysis)
    workflow.add_node("planner", run_planner)
    
    workflow.add_node("editor", run_editor)
    workflow.add_node("paginator", run_paginator_node) # Editor 다음 타자
    workflow.add_node("director", run_director)
    
    workflow.add_node("publisher", run_publisher)
    workflow.add_node("critique", run_critique)
    workflow.add_node("formatter", run_formatter)

    # 2. 엣지 연결 (흐름 제어)
    workflow.add_edge(START, "router")
    workflow.add_edge("router", "safety")

    # [Safety Check]
    def check_safety(state):
        return "vision" if state.get("safety_check") == "SAFE" else END
    
    workflow.add_conditional_edges("safety", check_safety, {"vision": "vision", END: END})

    workflow.add_edge("vision", "planner")
    
    # 🔥 [병렬 시작] Planner에서 두 갈래로 나뉨!
    workflow.add_edge("planner", "editor")   # 루트 1: 글쓰기 팀
    workflow.add_edge("planner", "director") # 루트 2: 디자인 팀

    # 📄 [루트 1 상세] Editor -> Paginator
    # Editor가 글을 다 쓰면 Paginator가 받아서 페이지를 나눔
    workflow.add_edge("editor", "paginator")

    # 🔀 [병렬 합류] Paginator와 Director가 모두 끝나면 Publisher로 모임
    # LangGraph는 들어오는 엣지가 다 도착할 때까지 자동으로 기다려줌! (Wait for all)
    workflow.add_edge("paginator", "publisher") 
    workflow.add_edge("director", "publisher")

    # 이후 흐름
    workflow.add_edge("publisher", "critique")

    # [Critique Feedback Loop]
    def route_critique(state):
        decision = state.get("critique_decision", "APPROVE")
        if decision == "RETRY_EDITOR": return "editor"
        elif decision == "RETRY_DIRECTOR": return "director"
        elif decision == "RETRY_PLANNER": return "planner"
        elif decision == "RETRY_PUBLISHER": return "publisher"
        else: return "formatter"

    workflow.add_conditional_edges(
        "critique",
        route_critique,
        {
            "editor": "editor",
            "director": "director",
            "planner": "planner",
            "publisher": "publisher",
            "formatter": "formatter"
        }
    )
    
    workflow.add_edge("formatter", END)

    return workflow.compile()

app_graph = build_graph()