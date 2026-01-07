import os
import sys
import asyncio
import json
from jinja2 import Template
from dotenv import load_dotenv

# 1. 경로 설정 및 환경 변수 로드
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from src.agents.editor import run_editor
from src.agents.director import run_director
from src.tools.paginator import organize_articles_into_pages

# --- [더미 데이터 설정] Vision & Planner ---
MOCK_VISION = {
    "mood": "Minimalist & Sophisticated",
    "description": "High-end fashion photography with soft beige tones.",
    "dominant_colors": ["#F5F5DC", "#2C2C2C"],
    "safe_areas": "Right"
}

MOCK_PLANNER = {
    "intent": "Trend Analysis",
    "target_tone": "Elegant & Lyrical"
}

# --- [병렬 팀 A] Editor + Paginator ---
async def editor_paginator_task(user_input):
    print("📝 [Line A] Editor: AI가 원고를 작성 중입니다 (실제 LLM 호출)...")
    loop = asyncio.get_event_loop()
    
    # 더미 데이터와 유저 입력을 합친 상태 생성
    state = {
        "user_input": user_input,
        "vision_result": MOCK_VISION,
        "planner_result": MOCK_PLANNER,
        "logs": []
    }
    
    # 1. Editor 실행 (실제 AI)
    editor_output = await loop.run_in_executor(None, run_editor, state)
    manuscript = editor_output.get("manuscript", {})
    print(f"✅ [Line A] Editor 완료: '{manuscript.get('headline')}'")

    # 2. Paginator 작동 확인을 위해 기사 3개로 구성 (원본 + 파생 기사)
    # 실제 글이 길면 Paginator가 어떻게 반응하는지 보기 위해 원본을 그대로 넣고 짧은 기사를 추가해볼게.
    print("📄 [Line A] Paginator: 페이지 분할 로직 가동...")
    articles_batch = [
        {**manuscript, "image_path": "hero_fashion.jpg"}, # 원본 (무거움)
        {**manuscript, "headline": "Styling Tip", "body": "Less is more. Focus on the fit.", "image_path": None}, # 가벼움
        {**manuscript, "headline": "Material Check", "body": "Pure cashmere lasts forever.", "image_path": None} # 가벼움
    ]
    
    pages = organize_articles_into_pages(articles_batch)
    return pages

# --- [병렬 팀 B] Director ---
async def director_task():
    print("🎨 [Line B] Director: 디자인 가이드를 생성 중입니다 (실제 LLM 호출)...")
    loop = asyncio.get_event_loop()
    
    # Director는 원고 없이도 톤과 비전 정보를 보고 스타일을 정함
    state = {
        "vision_result": MOCK_VISION,
        "planner_result": MOCK_PLANNER,
        "manuscript": [] # 병렬 구조이므로 빈 값 전달
    }
    
    director_output = await loop.run_in_executor(None, run_director, state)
    return director_output.get("design_spec", {})

# --- [Publisher] HTML 렌더링 ---
def publish_html(pages, design):
    print("\n🏗️ [Publisher] HTML 파일 생성 시작...")
    
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Magazine Page {{ page_num }}</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { 
                font-family: '{{ design.theme.fonts.body }}', sans-serif; 
                background-color: {{ design.theme.colors.primary }};
                color: {{ design.theme.colors.secondary }};
            }
            h1 { font-family: '{{ design.theme.fonts.title }}', serif; }
            .content-box {
                background: {{ design.components_style.content_box.bg_color }};
                backdrop-filter: blur(8px);
                border-radius: {{ design.components_style.content_box.border_radius }};
            }
        </style>
    </head>
    <body class="p-8 min-h-screen">
        <div class="max-w-4xl mx-auto flex flex-col gap-8">
            <header class="text-[10px] uppercase tracking-[0.5em] opacity-40 text-center mb-10">
                — {{ design.theme.mood }} EDITION / PAGE {{ page_num }} —
            </header>

            {% for article in articles %}
            <div class="content-box p-10 shadow-2xl border border-white/5 relative overflow-hidden">
                <h2 class="text-xs uppercase tracking-widest mb-4 opacity-60">{{ article.subhead }}</h2>
                <h1 class="text-5xl font-bold mb-6 italic leading-tight">{{ article.headline }}</h1>
                <div class="text-lg leading-relaxed opacity-90 whitespace-pre-line mb-6">
                    {{ article.body }}
                </div>
                <div class="flex gap-3">
                    {% for tag in article.tags %}
                    <span class="text-[9px] border border-current px-2 py-0.5 rounded-full opacity-50 uppercase">{{ tag }}</span>
                    {% endfor %}
                </div>
            </div>
            {% endfor %}
            
            <footer class="mt-10 text-center text-[10px] opacity-30">
                LAYOUT HINT: {{ layout_type }}
            </div>
        </div>
    </body>
    </html>
    """
    
    template = Template(html_template)
    for i, page in enumerate(pages):
        html_result = template.render(
            page_num=i + 1,
            articles=page["articles"],
            design=design,
            layout_type=page["layout_type"]
        )
        file_name = f"magazine_page_{i+1}.html"
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(html_result)
        print(f"   ✅ '{file_name}' 저장 완료!")

# --- [메인 실행부] ---
async def run_test():
    # Paginator를 자극할 만큼 충분히 긴 원본 글
    long_input = """
    Quiet Luxury is more than just a fashion statement; it's a philosophy of living. 
    In 2026, the world has moved away from the loud branding of the past. 
    Today, true wealth is found in the texture of a high-grade cashmere sweater, 
    the subtle drape of a silk scarf, and the impeccable fit of a bespoke wool coat. 
    It is about sustainability—buying items that last a lifetime rather than a season. 
    The focus is on the 'if you know, you know' (IYKYK) culture, where quality speaks for itself.
    (Editor: Please expand this into a deep, poetic editorial piece about the soul of craftsmanship.)
    """

    print("🚀 [System] 통합 병렬 테스트 시작 (Editor, Director 실구동)\n")
    
    # 1. 병렬 실행 (Editor+Paginator vs Director)
    results = await asyncio.gather(
        editor_paginator_task(long_input),
        director_task()
    )

    pages = results[0]
    design = results[1]

    # 2. HTML 생성
    publish_html(pages, design)

    print("\n✨ 테스트 종료! 브라우저에서 생성된 HTML 파일들을 확인하세요.")

if __name__ == "__main__":
    asyncio.run(run_test())