# src/state.py
from typing import TypedDict, List, Annotated, Optional, Dict, Any
import operator

class MagazineState(TypedDict):
    # --- [1. 입력 데이터] ---
    user_input: List[Dict[str, Any]]
    image_data: Optional[str]  # 처음엔 없을 수 있으니 Optional 필수!
    
    # --- [2. 분석 및 보안] ---
    intent: Optional[str]      # Router 돌기 전엔 없음
    safety_check: Optional[str]
    safety_detail: Optional[Dict[str, Any]]
    vision_result: Optional[Dict[str, Any]] # Vision 결과는 JSON(Dict)임!
    planner_result: Optional[Dict[str, Any]]
    
    # --- [3. 생성 데이터 (병렬 구간)] ---
    manuscript: Optional[List[Dict[str, Any]]]   
    pages: Optional[List[Any]]
    design_spec: Optional[Dict[str, Any]]  
    
    # --- [4. 통합 및 검수] ---
    html_code: Optional[str]
    critique: Optional[str]
    final_output: Optional[str]
    
    # --- [5. 로그 (병렬 안전)] ---
    logs: Annotated[List[str], operator.add]