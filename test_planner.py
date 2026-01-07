import os
import json
import base64
from jinja2 import Template
from src.state import MagazineState
from src.agents.planner import run_planner
from src.agents.vision import run_vision_analysis  # 👈 Vision Agent 임포트

# ==========================================
# 1. [Helper] Vision 좌표 -> Planner 위치 변환기
# ==========================================
def map_coordinates_to_zone(space_analysis):
    """
    Vision이 준 좌표([[y1,x1,y2,x2]])를 보고
    Planner가 이해하는 'top_left', 'center' 등의 문자열로 변환
    """
    if not space_analysis:
        return "center"
    
    # 첫 번째 박스 가져오기 (ymin, xmin, ymax, xmax) 0~1000 기준
    box = space_analysis[0]
    y_center = (box[0] + box[2]) / 2
    x_center = (box[1] + box[3]) / 2
    
    # 위치 판단 로직
    vertical = "center"
    horizontal = "center"
    
    if y_center < 333: vertical = "top"
    elif y_center > 666: vertical = "bottom"
    
    if x_center < 333: horizontal = "left"
    elif x_center > 666: horizontal = "right"
    
    if vertical == "center" and horizontal == "center":
        return "center"
    elif vertical == "center":
        return horizontal # left or right
    elif horizontal == "center":
        return vertical # top or bottom
    else:
        return f"{vertical}_{horizontal}" # top_left 등

# ==========================================
# 2. [Helper] Base64 변환 (HTML용)
# ==========================================
def encode_image_to_base64(image_path):
    if not os.path.exists(image_path):
        return "https://placehold.co/1024x1024?text=No+Image"
    with open(image_path, "rb") as img_file:
        encoded = base64.b64encode(img_file.read()).decode("utf-8")
        ext = image_path.split('.')[-1].lower()
        mime = "jpeg" if ext in ["jpg", "jpeg"] else ext
        return f"data:image/{mime};base64,{encoded}"

# ==========================================
# 3. 테스트 데이터 설정
# ==========================================
# [중요] 실제 존재하는 이미지 경로를 넣어주세요
TEST_DATA = [
    {
        "name": "Golden Goose",
        "image_path": "tests/패션잡지/1.png", 
        "script": {
            "title": "GOLDEN GOOSE",
            "subtitle": "Grit and Glamour",
            "body": "The Italian brand may be best known for its sneakers..."
        }
    },
    {
        "name": "Omega Watch",
        "image_path": "tests/패션잡지/2.png",
        "script": {
            "title": "DEPTH OF FEELING",
            "subtitle": "Omega’s much-loved technical diver",
            "body": "When Omega introduced the Planet Ocean..."
        }
    }
]

# ==========================================
# 4. HTML 생성기 (Publisher 역할)
# ==========================================
def generate_html(plan, script, img_path, vision_meta):
    # Vision에서 추출한 색상 사용 (없으면 기본값)
    colors = vision_meta.get("hex_colors", ["#000000"])
    bg_color = colors[0] if colors else "#000000"
    
    # Planner의 기획
    layout = plan.get("layout_guide", {})
    text_pos = layout.get("text_position", "center")
    font_theme = layout.get("font_theme", "Serif")
    
    # CSS 매핑
    pos_map = {
        "top": "top-10 left-0 w-full text-center",
        "bottom": "bottom-10 left-0 w-full text-center",
        "left": "top-1/2 left-10 transform -translate-y-1/2 text-left max-w-md",
        "right": "top-1/2 right-10 transform -translate-y-1/2 text-right max-w-md",
        "top_left": "top-10 left-10 text-left max-w-md",
        "top_right": "top-10 right-10 text-right max-w-md",
        "bottom_left": "bottom-10 left-10 text-left max-w-md",
        "bottom_right": "bottom-10 right-10 text-right max-w-md",
        "center": "top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center"
    }
    css_pos = pos_map.get(text_pos, pos_map["center"])
    css_font = "font-serif" if "Serif" in font_theme else "font-sans font-bold"

    img_b64 = encode_image_to_base64(img_path)

    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Lato:wght@400&display=swap" rel="stylesheet">
        <style>.font-serif { font-family: 'Playfair Display', serif; } .font-sans { font-family: 'Lato', sans-serif; }</style>
    </head>
    <body class="bg-gray-100 flex justify-center items-center min-h-screen">
        <div class="relative w-[800px] h-[1000px] bg-black shadow-2xl overflow-hidden group">
            <img src="{{ img }}" class="absolute inset-0 w-full h-full object-cover opacity-90 transition duration-700 group-hover:scale-105">
            <div class="absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/60"></div>
            
            <div class="absolute {{ pos }} text-white p-8 drop-shadow-lg">
                <h3 class="text-xs tracking-[0.4em] uppercase mb-4 border-b inline-block pb-1">{{ type }}</h3>
                <h1 class="{{ font }} text-6xl leading-tight mb-4">{{ title }}</h1>
                <p class="text-xl italic opacity-90 mb-6">{{ sub }}</p>
                <p class="text-sm opacity-80 max-w-prose leading-relaxed">{{ body }}...</p>
                
                <div class="mt-8 text-[10px] opacity-60 border border-white/30 p-2 inline-block rounded">
                    🎨 Mood: {{ mood }} <br> 💡 Light: {{ light }}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return Template(template).render(
        img=img_b64, pos=css_pos, font=css_font,
        type=plan.get("selected_type", "MAGAZINE"),
        title=script["title"], sub=script["subtitle"], body=script["body"][:150],
        mood=vision_meta.get("mood", "N/A"),
        light=vision_meta.get("lighting", "N/A")
    )

# ==========================================
# 5. 메인 실행 함수
# ==========================================
def run_test():
    for case in TEST_DATA:
        print(f"\n🚀 [Test Case] {case['name']} 시작...")

        # 1. State 초기화
        state = MagazineState(
            user_input=f"Make a magazine cover for {case['name']}",
            image_path=case['image_path'], # Vision을 위해 경로 저장
            user_script=case['script'],
            vision_result=None,
            plan=None,
            logs=[]
        )

        # 2. Vision Agent 실행 (실제 이미지 분석)
        vision_output = run_vision_analysis(state)
        
        if not vision_output["vision_result"]:
            print("❌ Vision 분석 실패. 다음 케이스로 넘어갑니다.")
            continue
            
        # Vision 결과 파싱
        raw_vision = vision_output["vision_result"]
        print(f"   👁️ Vision 분석 완료: {raw_vision['metadata']['mood']}")
        
        # 3. Vision 데이터 -> Planner 데이터로 매핑 (핵심!)
        mapped_vision_result = {
            "main_item": case['name'], # 간단히 이름 사용
            "img_mood": raw_vision["metadata"]["mood"],
            "colors": raw_vision["metadata"]["hex_colors"],
            "safe_zone": map_coordinates_to_zone(raw_vision.get("space_analysis")), # 좌표 -> 문자열 변환
            "shot_type": "Portrait" # 임시
        }
        
        # 매핑된 데이터를 State에 업데이트
        state["vision_result"] = mapped_vision_result
        
        # 4. Planner 실행
        planner_output = run_planner(state)
        plan = planner_output["plan"]
        print(f"   🧠 Planner 기획: {plan['selected_type']} (배치: {plan['layout_guide']['text_position']})")

        # 5. HTML 생성
        html = generate_html(plan, case['script'], case['image_path'], raw_vision['metadata'])
        
        # 저장
        filename = f"result_{case['name'].replace(' ', '_')}.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"   ✅ 저장 완료: {filename}")

if __name__ == "__main__":
    run_test()