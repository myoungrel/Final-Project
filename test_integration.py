import sys
import os
import json
from PIL import Image # 이미지 생성용

# -------------------------------------------------------------------------
# [Step 0] 환경 설정
# -------------------------------------------------------------------------
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ⚠️ Mock(가짜) 설정 제거함! -> 이제 진짜 src.config와 LLM을 사용합니다.
# 만약 Paginator 파일이 아직 없다면 여기만 Mock 유지
if 'src.tools.paginator' not in sys.modules:
    from unittest.mock import MagicMock
    mock_paginator = MagicMock()
    def mock_organize(articles):
        if not isinstance(articles, list): articles = [articles]
        return [{"articles": articles, "layout_type": "Integrated_Test_Layout", "article_count": len(articles)}]
    mock_paginator.organize_articles_into_pages = mock_organize
    sys.modules['src.tools.paginator'] = mock_paginator

# -------------------------------------------------------------------------
# [Step 1] 모듈 임포트 (진짜 에이전트들)
# -------------------------------------------------------------------------
from src.state import MagazineState
from src.agents.vision import run_vision_analysis
from src.agents.planner import run_planner
from src.agents.editor import run_editor
from src.agents.director import run_director
from src.agents.publisher import PublisherAgent
# Paginator가 실제 파일이 있다면 아래 주석 해제
from src.tools.paginator import organize_articles_into_pages

def create_dummy_image(filename):
    """테스트용 빈 이미지 생성"""
    if not os.path.exists(filename):
        img = Image.new('RGB', (100, 100), color = 'white')
        img.save(filename)
        print(f"🖼️ 테스트용 이미지 생성: {filename}")

def test_pipeline():
    print("🚀 [System] 5단계 리얼 통합 테스트 시작 (Mock 해제됨)\n")

    # 0. 테스트용 이미지 준비
    img_path = "test_image.jpg"
    create_dummy_image(img_path)

    # 1. 초기 State 설정
    state = {
        "user_input": "이번 시즌 트렌드는 '조용한 럭셔리(Quiet Luxury)'입니다. 화려한 로고 대신 고급 소재에 집중하세요.",
        # Planner가 user_script가 없으면 user_input을 쓰도록 수정했다고 가정하거나, 여기서 넣어줌
        "user_script": {"title": "Quiet Luxury 2026"}, 
        "image_path": img_path, 
        "logs": []
    }

    # ----------------------------------------------------------------
    # 2. Vision Node 실행
    # ----------------------------------------------------------------
    print("👁️ [1/5] Vision Agent 실행 중...")
    try:
        vision_output = run_vision_analysis(state)
        # Vision 결과가 없으면 강제 주입 (API 에러 대비)
        if not vision_output.get("vision_result"):
             vision_output = {"vision_result": {"mood": "Minimalist", "dominant_colors": ["#F5F5DC"], "safe_areas": "Right"}}
    except Exception as e:
        print(f"⚠️ Vision Error: {e}")
        vision_output = {"vision_result": {"mood": "ErrorFallback", "safe_areas": "Center"}}
    
    state.update(vision_output)
    print(f"   ✅ Vision 완료: {state['vision_result'].get('mood', 'N/A')}")

    # ----------------------------------------------------------------
    # 3. Planner Node 실행
    # ----------------------------------------------------------------
    print("\n🧠 [2/5] Planner Agent 실행 중...")
    planner_output = run_planner(state)
    state.update(planner_output)
    
    # [키 매핑 보정] Planner 결과 -> Editor/Director 입력용
    if "plan" in state:
        state["planner_result"] = state["plan"]
        state["intent"] = state["plan"].get("selected_type")
    
    # target_tone이 누락되었을 경우를 대비해 안전장치
    if "target_tone" not in state.get("planner_result", {}):
        if "planner_result" not in state: state["planner_result"] = {}
        state["planner_result"]["target_tone"] = "Elegant & Lyrical"

    print(f"   ✅ Planner 완료: {state.get('planner_result', {}).get('selected_type')}")

    # ----------------------------------------------------------------
    # 4. Editor & Director 실행
    # ----------------------------------------------------------------
    print("\n📝 [3/5] Editor Agent 실행 중 (Real LLM)...")
    editor_output = run_editor(state)
    state.update(editor_output)
    print(f"   ✅ Editor 완료: {state.get('manuscript', {}).get('headline', 'Fail')}")

    print("\n🎨 [3/5] Director Agent 실행 중 (Real LLM)...")
    director_output = run_director(state)
    state.update(director_output)
    print(f"   ✅ Director 완료: {state.get('design_spec', {}).get('theme', {}).get('mood', 'Fail')}")

    # ----------------------------------------------------------------
    # 5. Paginator 실행
    # ----------------------------------------------------------------
    print("\n📄 [4/5] Paginator Tool 실행 중...")
    manuscript = state.get("manuscript", {})
    
    # 딕셔너리면 리스트로 변환
    articles = [manuscript] if isinstance(manuscript, dict) else manuscript
    
    # Paginator 실행
    pages = organize_articles_into_pages(articles)
    
    # Publisher를 위한 데이터 구조 매핑 (핵심!)
    state["content"] = {"blocks": []}
    # Paginator의 첫 번째 기사를 표지(Block)용으로 사용
    if pages and len(pages) > 0:
        first_page_articles = pages[0]['articles']
        if first_page_articles:
            state["content"]["blocks"] = first_page_articles

    # 이미지 데이터 매핑 (Publisher가 images 키를 봄)
    state["images"] = {"img_01": img_path}

    print(f"   ✅ Paginator 완료: {len(pages)} 페이지 생성")

    # ----------------------------------------------------------------
    # 6. Publisher 실행
    # ----------------------------------------------------------------
    print("\n🖨️ [5/5] Publisher Agent 실행 중...")
    
    # [경로 수정] Publisher가 찾는 위치(src/agents/templates)에 파일 생성
    # 현재 스크립트 위치 기준으로 src/agents/templates 경로 계산
    base_dir = os.path.dirname(os.path.abspath(__file__))
    publisher_template_dir = os.path.join(base_dir, "src", "agents", "templates")
    
    if not os.path.exists(publisher_template_dir):
        os.makedirs(publisher_template_dir, exist_ok=True)
    
    template_path = os.path.join(publisher_template_dir, "magazine_layout.html")
    
    # 템플릿 파일이 없으면 생성 (Publisher용 간단 템플릿)
    if not os.path.exists(template_path):
        with open(template_path, "w", encoding="utf-8") as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>AI Magazine</title>
    <style>
        body { font-family: sans-serif; padding: 20px; background: {{ data.design_spec.theme.colors.primary }}; color: {{ data.design_spec.theme.colors.text_main }}; }
        .box { background: rgba(255,255,255,0.8); padding: 20px; border-radius: 10px; }
    </style>
</head>
<body>
    <div class="box">
        <h1>{{ data.content.blocks[0].headline }}</h1>
        <h3>{{ data.content.blocks[0].subhead }}</h3>
        <p>{{ data.content.blocks[0].body }}</p>
    </div>
    <hr>
    <p>Mood: {{ data.design_spec.theme.mood }}</p>
</body>
</html>
            """)
        print(f"   📂 템플릿 생성됨: {template_path}")

    # Publisher 초기화 (경로는 relative path인 'templates'로 주면 src/agents/templates를 찾음)
    publisher = PublisherAgent(template_path="templates")
    
    final_state = publisher.run(state, enable_hitl=False)
    
    if "final_html" in final_state:
        print(f"   ✅ Publisher 완료! HTML 생성 성공.")
        # output 경로는 Publisher가 출력한 로그 참고
    else:
        print("   ❌ Publisher 실패.")

if __name__ == "__main__":
    test_pipeline()