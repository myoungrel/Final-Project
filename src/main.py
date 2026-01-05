# src/main.py
from langgraph.graph import StateGraph, START, END
from src.state import MagazineState

# 에이전트 파일들 불러오기
from src.agents.router import run_router
from src.agents.safety import run_safety
from src.agents.vision import run_vision
from src.agents.planner import run_planner
from src.agents.editor import run_editor
from src.agents.director import run_director
from src.agents.publisher import run_publisher
from src.agents.critique import run_critique
from src.agents.formatter import run_formatter

def build_graph():
    workflow = StateGraph(MagazineState)

    # 1. 노드 등록
    # (Editor와 Director를 연달아 등록하여 그래프 배치 최적화 시도)
    workflow.add_node("router", run_router)
    workflow.add_node("safety", run_safety)
    workflow.add_node("vision", run_vision)
    workflow.add_node("planner", run_planner)

    workflow.add_node("editor", run_editor)
    workflow.add_node("director", run_director)
    
    workflow.add_node("publisher", run_publisher)
    workflow.add_node("critique", run_critique)
    workflow.add_node("formatter", run_formatter)

    # 2. 엣지 연결
    workflow.add_edge(START, "router")
    workflow.add_edge("router", "safety")

    # [조건부 분기 1] 안전 검사 결과에 따른 분기
    def check_safety(state):
        return "vision" if state.get("safety_check") == "SAFE" else END
    
    workflow.add_conditional_edges(
        "safety",
        check_safety,
        {"vision": "vision", END: END}
    )

    # [3. 흐름 수정] Vision -> Planner -> (병렬 시작)
    workflow.add_edge("vision", "planner")
    workflow.add_edge("planner", "editor")
    workflow.add_edge("planner", "director")
    
    # 병렬 흐름 합류 (Editor & Director -> Publisher)
    workflow.add_edge("editor", "publisher")
    workflow.add_edge("director", "publisher")
    
    # Publisher -> Critique
    workflow.add_edge("publisher", "critique")

    # [조건부 분기 2] Critique 결과에 따른 라우팅 로직
    def route_critique(state):
        # State에 저장된 검수 결과(결정)를 가져옵니다.
        decision = state.get("critique_decision", "APPROVE")
        
        # 반환값은 아래 딕셔너리의 Key와 똑같아야 합니다!
        if decision == "RETRY_EDITOR" or decision == "RETRY_MOOD":
            return "editor"
        elif decision == "RETRY_DIRECTOR":
            return "director"
        elif decision == "RETRY_PLANNER": # 👈 [4. Planner로 돌아가는 경우 추가]
            return "planner"
        elif decision == "RETRY_PUBLISHER":
            return "publisher"
        else:
            return "formatter"

    # LangGraph에 갈림길 등록
    # ⚠️ 수정됨: 키(Key) 값을 위 함수의 반환값(영어)과 일치시켰습니다!
    workflow.add_conditional_edges(
        "critique",
        route_critique,
        {
            "editor": "editor",       # 글/Mood 문제
            "director": "director",   # 디자인 문제
            "planner": "planner",
            "publisher": "publisher", # 코드 문제
            "formatter": "formatter"  # 통과
        }
    )
    
    # 마지막 단계
    workflow.add_edge("formatter", END)

    return workflow.compile()

app_graph = build_graph()

# 👇 이미지 저장 코드 👇
if __name__ == "__main__":
    print("🚀 그래프 이미지 생성 중...")
    try:
        # 1. 그래프를 PNG 이진 데이터로 변환
        png_data = app_graph.get_graph().draw_mermaid_png()
        
        # 2. 파일로 저장
        output_file = "graph.png"
        with open(output_file, "wb") as f:
            f.write(png_data)
            
        print(f"✅ 그래프가 '{output_file}' 파일로 저장되었습니다! VS Code 탐색기에서 확인해보세요.")
        
    except Exception as e:
        print(f"❌ 그래프 이미지 생성 실패: {e}")
        print("💡 팁: Graphviz가 설치되어 있지 않다면 에러가 날 수 있습니다.")