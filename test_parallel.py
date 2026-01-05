# test_parallel.py
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from src.state import MagazineState
from src.agents.editor import run_editor
from src.agents.director import run_director

load_dotenv()

# --- [Fashion Mock Data] ---

# 1. Vision: 시크하고 모던한 모델 사진이라고 가정
mock_vision_result = {
    "mood": "Chic and Minimalist",
    "description": "A high-fashion model wearing a beige trench coat, standing against a concrete wall. Soft shadows.",
    "safe_areas": "Right",  # 모델이 왼쪽에 있어서 텍스트는 오른쪽이 안전
    "dominant_colors": ["#1A1A1A", "#F5F5DC", "#8B4513"] # 블랙, 베이지, 브라운
}

# 2. Planner: '우아함'을 전략으로 선택
mock_planner_result = {
    "intent": "Fashion Trend Report",
    "target_tone": "Elegant & Lyrical" # 👉 Type A (Vogue Style) 발동!
}

mock_state: MagazineState = {
    "user_input": "이번 가을 트렌드는 '조용한 럭셔리(Quiet Luxury)'야. 로고 플레이 없이 고급스러운 소재와 절제된 핏이 핵심이지. 우아하고 시적인 느낌으로 써줘.",
    "vision_result": mock_vision_result,
    "planner_result": mock_planner_result,
    "manuscript": None,
    "design_spec": None,
    "logs": []
}

print("🧪 [테스트 시작] Fashion Magazine Scenario\n")

# Editor 테스트
print("👠 1. Editor (Fashion Tone) 실행...")
editor_output = run_editor(mock_state)
manuscript = editor_output['manuscript']
print(f"   👉 Headline: {manuscript.get('headline')}")
print(f"   👉 Tone: {manuscript.get('tone_applied')}")
print(f"   👉 Caption: {manuscript.get('caption')}")

# Director 테스트
print("\n🎨 2. Director (Elegant Design) 실행...")
director_output = run_director(mock_state)
design_spec = director_output['design_spec']
print(f"   👉 Font(Title): {design_spec.get('theme', {}).get('fonts', {}).get('title')}")
print(f"   👉 Colors: {design_spec.get('theme', {}).get('colors')}")

print("\n✅ 패션 매거진 시나리오 테스트 완료!")