import operator
from typing import Annotated, TypedDict, Union, List
from langgraph.graph import StateGraph, END

# 1. 상태(State) 정의
class MagazineState(TypedDict):
    user_input: str
    is_safe: bool = True
    vision_result: str = ""
    editor_result: str = ""
    strategy: str = ""
    html_code: str = ""
    critique_score: int = 0
    retry_count: Annotated[int, operator.add] = 0 

# 2. 노드(Nodes) 정의
def intent_router(state: MagazineState):
    print("--- (1) 의도 파악 중 ---")
    if "만들어" in state["user_input"]:
        return {"user_input": state["user_input"]}
    return {"user_input": "chitchat"}

def safety_filter(state: MagazineState):
    print("--- (2) 유해성 검사 중 ---")
    is_safe = "나쁜말" not in state["user_input"]
    return {"is_safe": is_safe}

def vision_agent(state: MagazineState):
    print("--- (3) 사진 분석 중 (Parallel) ---")
    return {"vision_result": "파란색 배경의 모던한 사진 분석 완료"}

def editor_agent(state: MagazineState):
    print("--- (4) 원고 작성 중 (Parallel) ---")
    return {"editor_result": "이것은 잡지의 멋진 원고입니다."}

def art_director(state: MagazineState):
    print("--- (5) 전략 수립 중 ---")
    # 병렬 노드들이 끝난 후 실행됨
    return {"strategy": "모던 & 미니멀 레이아웃 결정"}

def publisher(state: MagazineState):
    print(f"--- (6) HTML 코딩 중 (시도 횟수: {state['retry_count'] + 1}) ---")
    return {"html_code": "<html>...</html>", "retry_count": 1}

def critique(state: MagazineState):
    print("--- (7) 품질 검수 중 ---")
    score = 100 if state["retry_count"] >= 2 else 40
    return {"critique_score": score}

def ux_formatter(state: MagazineState):
    print("--- (8) 최종 변환 중 ---")
    return {"html_code": "✨ 최종 최적화된 HTML ✨"}

def fallback(state: MagazineState):
    print("--- (9) 일반 대화 또는 거절 응답 ---")
    return {}

# 3. 그래프(Graph) 구성
workflow = StateGraph(MagazineState)

# 노드 추가
workflow.add_node("intent_router", intent_router)
workflow.add_node("safety_filter", safety_filter)
workflow.add_node("vision_agent", vision_agent)
workflow.add_node("editor_agent", editor_agent)
workflow.add_node("art_director", art_director)
workflow.add_node("publisher", publisher)
workflow.add_node("critique", critique)
workflow.add_node("ux_formatter", ux_formatter)
workflow.add_node("fallback", fallback)

# 엣지 연결
workflow.set_entry_point("intent_router")

# (1) Intent Router 조건부 분기
workflow.add_conditional_edges(
    "intent_router",
    lambda x: "create" if "만들어" in x["user_input"] else "fallback",
    {"create": "safety_filter", "fallback": "fallback"}
)

# [수정된 부분] (2) Safety Filter 조건부 분기 (병렬 처리 로직 변경)
# 딕셔너리 매핑 대신, 함수가 직접 실행할 노드 리스트를 반환하게 함
def route_after_safety(state):
    if state["is_safe"]:
        # 안전하면 병렬로 실행할 노드들의 리스트 반환
        return ["vision_agent", "editor_agent"]
    else:
        # 안전하지 않으면 단일 노드 반환 (리스트로 감싸도 되고 안 해도 됨)
        return "fallback"

workflow.add_conditional_edges(
    "safety_filter",
    route_after_safety
    # path_map(딕셔너리) 생략: 함수 리턴값이 실제 노드 이름과 일치하므로 필요 없음
)

# 병렬 처리된 결과를 합치기 (Fan-in)
# vision_agent와 editor_agent가 모두 끝나면 art_director가 실행됨
workflow.add_edge("vision_agent", "art_director")
workflow.add_edge("editor_agent", "art_director")

workflow.add_edge("art_director", "publisher")
workflow.add_edge("publisher", "critique")

# (7) Critique 루프 분기
workflow.add_conditional_edges(
    "critique",
    lambda x: "pass" if x["critique_score"] >= 80 else "fail",
    {"pass": "ux_formatter", "fail": "publisher"}
)

workflow.add_edge("ux_formatter", END)
workflow.add_edge("fallback", END)

# 앱 컴파일
app = workflow.compile()

# 정상 케이스 테스트
print("=== 테스트 시작 ===")
inputs = {"user_input": "멋진 잡지 하나 만들어줘!"}
for output in app.stream(inputs):
    # stream 출력은 각 노드의 수행 결과를 보여줌
    for key, value in output.items():
        print(f"✅ Node '{key}': {value}")
    print("-" * 20)