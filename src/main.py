# src/main.py
from typing import List, Dict, Any
from langgraph.graph import StateGraph, START, END
from src.state import MagazineState, ArticleState

# 양방향 참조 방지 및 에이전트 임포트
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
# [Node] Setup Node (Initialization)
# ---------------------------------------------------------
def run_setup(state: MagazineState) -> dict:
    """
    [Steps 0] Setup Node
    사용자 입력(List)을 Unified Architecture의 핵심 구조인
    'articles' 딕셔너리(Dict[id, ArticleState])로 변환하여 초기화합니다.
    """
    print("--- [Step 0] Setup: Initializing Articles State ---")
    
    user_inputs = state.get("user_input", [])
    raw_images = state.get("image_data") or {}
    
    # 만약 image_data가 리스트라면 딕셔너리로 변환 (안전장치)
    if isinstance(raw_images, list):
        print("⚠️ Warning: image_data is List, converting to Dict...")
        image_map = {}
        for idx, item in enumerate(raw_images):
            # user_input 순서와 매칭 가정 혹은 id 확인
            # 여기서는 편의상 user_inputs의 ID를 따라가거나 인덱스 매칭
            if idx < len(user_inputs):
                u_id = str(user_inputs[idx].get("id", str(idx+1)))
                image_map[u_id] = item
        raw_images = image_map

    articles: Dict[str, ArticleState] = {}
    
    for item in user_inputs:
        # ID가 없으면 'main' 또는 임의 생성
        article_id = str(item.get("id", "main"))
        
        # ArticleState 기본 구조 생성
        articles[article_id] = {
            # 1. Input Data
            "id": article_id,
            "title": item.get("title", "Untitled"),
            "request": item.get("request", ""),
            "style": item.get("style", "Elegant"),
            "is_generated": item.get("is_generated", True),
            "image_path": raw_images.get(article_id), # 매핑된 이미지
            
            # 2. Placeholders (빈 딕셔너리로 초기화)
            "vision_analysis": {},
            "plan": {},
            "manuscript": {},
            "design_spec": {}
        }
        print(f"   > Initialized Article ID: {article_id}")

    # State Update
    return {"articles": articles}


# ---------------------------------------------------------
# [Node] Paginator Node (Adapter)
# ---------------------------------------------------------
def run_paginator_node(state: MagazineState) -> dict:
    """
    [Unified Architecture]
    state['articles']에 있는 모든 ArticleState에서 원고(manuscript)를 추출하여
    Paginator 툴에 전달합니다.
    """
    print("--- [Step 4.5] Paginator: Organizing Articles (Unified) ---")
    
    articles = state.get("articles", {})
    if not articles:
        print("⚠️ [Paginator] 처리할 기사(Articles)가 없습니다.")
        return {"pages": []}

    # Extract manuscripts from ArticleState
    manuscript_list = []
    
    for a_id, article in articles.items():
        # Editor가 작성한 원고 추출
        m = article.get("manuscript")
        
        if m:
            # 원고에 ID가 누락됐을 경우를 대비해 안전하게 주입
            if "id" not in m:
                m["id"] = a_id
            manuscript_list.append(m)
        else:
            print(f"⚠️ [Paginator] 기사 ID {a_id}에 원고가 없습니다.")

    if not manuscript_list:
        return {"pages": []}

    # Tool Execution
    # organize_articles_into_pages expects List[Dict]
    pages = organize_articles_into_pages(manuscript_list)
    
    print(f"📄 Paginator Result: Split into {len(pages)} page(s).")
    
    return {"pages": pages}


# ---------------------------------------------------------
# [Graph] Graph Construction
# ---------------------------------------------------------
def build_graph():
    workflow = StateGraph(MagazineState)

    # 1. 노드 등록
    workflow.add_node("setup", run_setup) # ✨ New Entry Node
    
    workflow.add_node("router", run_router)
    workflow.add_node("safety", run_safety)
    workflow.add_node("vision", run_vision)
    workflow.add_node("planner", run_planner)
    
    workflow.add_node("editor", run_editor)
    workflow.add_node("paginator", run_paginator_node)
    workflow.add_node("director", run_director)
    
    workflow.add_node("publisher", run_publisher)
    workflow.add_node("critique", run_critique)
    workflow.add_node("formatter", run_formatter)

    # 2. 엣지 연결 (Setup을 시작점으로 설정)
    workflow.add_edge(START, "setup")      # Start -> Setup
    workflow.add_edge("setup", "router")   # Setup -> Router
    
    workflow.add_edge("router", "safety")

    # [Safety Check]
    def check_safety(state):
        return "vision" if state.get("safety_check") == "SAFE" else END
    
    workflow.add_conditional_edges("safety", check_safety, {"vision": "vision", END: END})

    workflow.add_edge("vision", "planner")
    
    # 🔥 [병렬 시작] Planner -> Editor / Director
    workflow.add_edge("planner", "editor")   
    workflow.add_edge("planner", "director") 

    # 📄 [루트 1] Editor -> Paginator
    workflow.add_edge("editor", "paginator")

    # 🔀 [병렬 합류] Paginator + Director -> Publisher
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