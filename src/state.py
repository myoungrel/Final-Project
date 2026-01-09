# src/state.py
from typing import TypedDict, List, Annotated, Optional, Dict, Any
import operator

# ------------------------------------------------------------------
# [Reducer] Parallel Merge Logic
# ------------------------------------------------------------------
def merge_articles(old_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    [Parallel Update Reducer]
    Editor와 Director가 병렬로 실행될 때 발생하는 'InvalidConcurrentGraphUpdateError'를 방지합니다.
    기존 articles 딕셔너리를 덮어쓰지 않고, Article ID별로 내부 필드를 병합(update)합니다.
    """
    if not old_data:
        old_data = {}
        
    merged = old_data.copy()
    
    for article_id, new_content in new_data.items():
        if article_id in merged:
            # Case 1: 이미 존재하는 기사 -> 필드만 업데이트 (Merge)
            # 예: 기존 { "id": "1", "plan": {...} } + 신규 { "manuscript": {...} }
            # 결과 -> { "id": "1", "plan": {...}, "manuscript": {...} }
            merged[article_id].update(new_content)
        else:
            # Case 2: 새로운 기사 -> 추가
            merged[article_id] = new_content
            
    return merged

# ------------------------------------------------------------------
# [Schema] Unified Architecture
# ------------------------------------------------------------------
class ArticleState(TypedDict, total=False):
    """
    [Unified Schema]
    단일 기사(Article)의 전체 수명 주기 데이터를 담는 스키마입니다.
    분절된 키(vision_result, planner_result 등)를 사용하지 않고,
    이 객체 하나에 모든 메타데이터를 통합 관리합니다.
    """
    # === [1. Input Data] ===
    id: str                    # 필수: 기사 ID
    title: str                 # 사용자 입력 제목
    request: str               # 사용자 요청 내용
    style: str                 # 스타일 (Elegant, Bold 등)
    is_generated: bool         # AI 생성 여부 (False면 사용자 글 보존)
    image_path: Optional[str]  # 이미지 경로 (또는 base64)

    # === [2. Analysis (Vision)] ===
    vision_analysis: Dict[str, Any]
    # {
    #   "layout_strategy": {"recommendation": "...", "reason": "..."},
    #   "metadata": {"mood": "...", "dominant_colors": [...], "safe_areas": [...]},
    #   ...
    # }

    # === [3. Planning (Planner)] ===
    plan: Dict[str, Any]
    # {
    #   "selected_type": "TYPE_...",
    #   "concept_rationale": "...",
    #   "layout_guide": {...}
    # }

    # === [4. Content (Editor)] ===
    manuscript: Dict[str, Any]
    # {
    #   "headline": "...", "body": "...", "caption": "...", "tags": [...]
    # }

    # === [5. Design (Director)] ===
    design_spec: Dict[str, Any]
    # {
    #   "theme": {...}, "layout_config": {...}, "components_style": {...}
    # }


class MagazineState(TypedDict):
    """
    [Global State]
    전체 매거진 생성 워크플로우의 상태를 관리합니다.
    기존의 분산된 리스트/딕셔너리 대신 'articles' 딕셔너리에 통합됩니다.
    """
    # === [Core Data] ===
    # Key: article_id, Value: ArticleState
    # ✨ Annotated + merge_articles 적용: 병렬 실행 시 데이터 병합 지원
    articles: Annotated[Dict[str, ArticleState], merge_articles]

    # === [Legacy Input Fields (for compatibility / initialization)] ===
    user_input: List[Dict[str, Any]]  # 초기 입력 보관용
    image_data: Optional[Dict[str, str]] # 초기 이미지 데이터 보관용
    
    # === [Workflow State] ===
    intent: Optional[str]      # Router 결정 (General/Special)
    safety_check: Optional[str]
    safety_detail: Optional[Dict[str, Any]]
    
    # === [Output Data] ===
    pages: Optional[List[Any]]       # Paginator 결과 (List of Page objects)
    html_code: Optional[str]         # 최종 HTML
    final_output: Optional[str]      # Formatter가 반환하는 최종 결과
    
    # === [Feedback Loop] ===
    critique: Optional[str]
    critique_decision: Optional[str] # APPROVE / RETRY_*
    
    # === [Logging] ===
    logs: Annotated[List[str], operator.add]