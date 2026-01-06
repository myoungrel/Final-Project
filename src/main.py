# src/main.py
from langgraph.graph import StateGraph, START, END
from src.state import MagazineState

# 에이전트들
from src.agents.router import run_router
from src.agents.safety import run_safety
from src.agents.vision import run_vision
from src.agents.planner import run_planner
from src.agents.editor import run_editor
from src.agents.director import run_director
from src.agents.publisher import run_publisher
from src.agents.critique import run_critique
from src.agents.formatter import run_formatter

from src.tools.paginator import organize_articles_into_pages

# ---------------------------------------------------------
# [New] Paginator 노드 함수를 여기서 바로 정의 (Inline)
# ---------------------------------------------------------
def run_paginator_node(state: MagazineState) -> dict:
    """
    Editor가 쓴 글을 받아서 src/tools/paginator.py의 로직을 돌려주는 함수
    """
    print("--- [Step 4.5] Paginator: Organizing Articles (Inline) ---")
    
    # 1. 원고 가져오기
    manuscript = state.get("manuscript", {})
    
    # [방어 코드] 원고가 없으면 빈 리스트 처리
    if not manuscript:
        print("⚠️ [Paginator] 원고(Manuscript)가 없습니다. 빈 페이지를 반환합니다.")
        return {"pages": []}

    # 리스트 변환 (안전장치)
    if isinstance(manuscript, dict):
        articles = [manuscript]
    else:
        articles = manuscript

    # 2. 도구 실행 (툴 폴더에 있는 함수 호출)
    pages = organize_articles_into_pages(articles)
    
    print(f"📄 Paginator Result: Split into {len(pages)} page(s).")
    
    # 3. 결과 반환
    return {"pages": pages}

def build_graph():
    workflow = StateGraph(MagazineState)

    # 1. 노드 등록
    workflow.add_node("router", run_router)
    workflow.add_node("safety", run_safety)
    workflow.add_node("vision", run_vision)
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