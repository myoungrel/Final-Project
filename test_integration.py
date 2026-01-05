# test_integration.py
import os
import sys
from jinja2 import Template
from dotenv import load_dotenv

# 모듈 경로 설정
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.state import MagazineState
from src.agents.editor import run_editor
from src.agents.director import run_director

load_dotenv()

# --- [Step 1] 입력 데이터 설정 (여기에 네가 원하는 걸 넣는 거야!) ---

# 1. 글 전체 (User Input): 절대 바뀌면 안 되는 '팩트'와 '내용'
user_full_text = """
The defining trend of this season is undeniably 'Quiet Luxury.'
Large, flashy logos on t-shirts or bags are now considered outdated.
Instead, the focus has shifted to the intrinsic quality of materials, such as cashmere, silk, and high-grade wool.
True wealth is not about ostentatious display, but rather stems from the subtle fit and texture of the garment.
Invest in classic items that will remain in your wardrobe for years to come. That is the essence of true sustainability.
"""

# 2. 메타데이터 (Planner): 추상적 요구사항 (분위기/톤)
# Planner가 이미지를 보고 "이건 우아한(Elegant) 느낌으로 가야 해"라고 결정했다고 가정.
planner_abstract_intent = {
    "intent": "Fashion Trend Report",
    "target_tone": "Elegant & Lyrical" # 👉 Editor가 이 톤으로 '번역'을 수행함
}

# 3. 이미지 정보 (Vision): 시각적 분석 결과
vision_analysis = {
    "mood": "Chic and Minimalist",
    "description": "A model wearing a high-quality beige trench coat, walking confidently. Soft natural lighting.",
    "dominant_colors": ["#F5F5DC", "#4A4A4A"], # 베이지, 차콜
    "safe_areas": "Right"
}

print("🚀 [System] 매거진 생성 시작 (Full Pipeline Test)...")

initial_state: MagazineState = {
    "user_input": user_full_text,
    "vision_result": vision_analysis,
    "planner_result": planner_abstract_intent,
    "manuscript": {},
    "design_spec": {},
    "logs": []
}

# --- [Step 2] 에이전트 실행 ---

# 1. Editor (Style Transfer)
# 역할: "조용한 럭셔리" 텍스트를 -> "Elegant"한 영어 문체로 변환 (내용 보존)
print("\n📝 [Editor] 원문을 'Elegant' 톤으로 윤문(Rewriting) 중...")
editor_output = run_editor(initial_state)
initial_state.update(editor_output)

# 2. Director (SDUI Design)
# 역할: Vision 색상 + Elegant 톤 + Content Box(가독성) 설계
print("\n🎨 [Director] 디자인 입히는 중 (Content Box 포함)...")
director_output = run_director(initial_state)
initial_state.update(director_output)


# --- [Step 3] HTML 조립 (Publisher 역할) ---
print("\n🏗️  HTML 생성 중...")

html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ manuscript.headline }}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;700&family=Lato:wght@300;400;700&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
    <style>
        body { font-family: '{{ design.theme.fonts.body }}'; }
        h1, h2, h3 { font-family: '{{ design.theme.fonts.title }}'; }
        .hero-bg {
            background-image: url('{{ image_url }}');
            background-position: center center;
            background-size: cover;
        }
    </style>
</head>
<body style="background-color: {{ design.theme.colors.primary }};">
    
    <div class="max-w-screen-lg mx-auto min-h-screen shadow-2xl overflow-hidden relative hero-bg">
        
        <div class="absolute inset-0 bg-black" style="opacity: {{ design.layout_config.overlay_opacity }};"></div>

        <div class="relative z-10 h-full min-h-screen flex flex-col justify-center p-6 md:p-12 {{ design.layout_config.text_position_x }}">
            
            <div class="max-w-lg {{ design.components_style.content_box.bg_color }} {{ design.components_style.content_box.padding }} {{ design.components_style.content_box.border_radius }} {{ design.components_style.content_box.shadow }} {{ design.components_style.content_box.backdrop_blur }}">
                
                <h2 class="{{ design.components_style.subhead.size }} {{ design.components_style.subhead.weight }} tracking-widest mb-4 opacity-80" 
                    style="border-bottom: 1px solid currentColor; display: inline-block; padding-bottom: 4px; color: inherit;">
                    {{ manuscript.subhead }}
                </h2>

                <h1 class="{{ design.components_style.headline.size }} {{ design.components_style.headline.weight }} leading-tight italic mb-6"
                    style="color: inherit;">
                    {{ manuscript.headline }}
                </h1>

                <div class="{{ design.components_style.body.size }} {{ design.components_style.body.leading }} whitespace-pre-line mb-8 font-light opacity-90"
                     style="color: inherit;">
                    {{ manuscript.body }}
                </div>

                <div class="flex flex-wrap gap-2">
                    {% for tag in manuscript.tags %}
                    <span class="px-3 py-1 text-[10px] uppercase tracking-widest border border-current bg-transparent opacity-70"
                          style="color: inherit;">
                        {{ tag }}
                    </span>
                    {% endfor %}
                </div>

            </div>
            
            <div class="absolute bottom-6 left-0 right-0 px-12 text-center">
                 <p class="{{ design.components_style.caption.size }} {{ design.components_style.caption.style }} bg-black/40 text-white inline-block px-4 py-1 rounded-full backdrop-blur-md">
                    ▲ {{ manuscript.caption }}
                 </p>
            </div>

        </div>
    </div>
</body>
</html>
"""

# 렌더링
template = Template(html_template)
final_html = template.render(
    manuscript=initial_state['manuscript'],
    design=initial_state['design_spec'],
    image_url="https://images.unsplash.com/photo-1549419163-95240292728b?q=80&w=1000&auto=format&fit=crop" # 베이지 코트 이미지
)

# 저장
output_filename = "output_final_test.html"
with open(output_filename, "w", encoding="utf-8") as f:
    f.write(final_html)

print(f"\n✨ 테스트 완료! '{output_filename}' 파일을 열어보세요.")
print("👉 체크포인트:")
print("1. 글상자(Box)가 생겨서 글씨가 잘 보이는가?")
print("2. 본문 내용이 '조용한 럭셔리' 이야기를 담고 있는가?")
print("3. 말투가 'Elegant(우아한)' 영어로 바뀌었는가?")