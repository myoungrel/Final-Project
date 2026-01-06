# src/state.py
from typing import TypedDict, List, Annotated, Optional, Dict, Any
import operator

class MagazineState(TypedDict):
    # --- [1. 입력 데이터] ---
    user_input: str
    
    # [추가] Vision과 Publisher가 파일 경로를 참조할 때 사용
    image_path: Optional[str]  
    image_data: Optional[str]  # (기존 유지) Base64 등 데이터용
    
    # [추가] Planner가 'user_script'라는 키를 찾을 때 대비
    user_script: Optional[Dict[str, Any]]

    # --- [2. 분석 및 보안] ---
    intent: Optional[str]      
    safety_check: Optional[str]
    vision_result: Optional[Dict[str, Any]] 
    
    # [추가] Planner -> Editor/Director 연결용 (매우 중요! ⭐)
    planner_result: Optional[Dict[str, Any]] 
    plan: Optional[Dict[str, Any]] # (기존 유지 - 백업용)
    
    # --- [3. 생성 데이터 (병렬 구간)] ---
    manuscript: Optional[Dict[str, Any]]   
    design_spec: Optional[Dict[str, Any]]  
    
    # --- [4. 페이지네이션 & 퍼블리싱 (여기가 핵심!)] ---
    # [추가] Paginator가 나눈 페이지 리스트
    pages: Optional[List[Any]] 
    
    # [추가] Publisher가 읽어갈 최종 콘텐츠 구조 (blocks 포함)
    content: Optional[Dict[str, Any]] 
    
    # [추가] Publisher가 사용할 이미지 딕셔너리
    images: Optional[Dict[str, Any]]  

    # --- [5. 통합 및 검수] ---
    # [추가] Publisher가 생성한 최종 HTML 문자열
    final_html: Optional[str] 
    
    html_code: Optional[str] # (기존 유지)
    critique: Optional[str]
    final_output: Optional[str]
    
    # [추가] Critique 노드가 결정한 다음 단계 (RETRY 등)
    critique_decision: Optional[str] 
    
    # --- [6. 로그 (병렬 안전)] ---
    logs: Annotated[List[str], operator.add]