import os
import json
import base64
import glob
from jinja2 import Template
from src.state import MagazineState
from src.agents.planner import run_planner

# ==========================================
# 0. [설정] 이미지 폴더 경로 (WSL 내부 경로)
# ==========================================
# 사용자가 알려준 경로: \\wsl.localhost\Ubuntu-22.04\home\sauser\ysksean\Final-Project\tests\패션잡지
# 이를 리눅스 경로로 바꾸면 아래와 같습니다.
BASE_IMG_PATH = "/home/sauser/ysksean/Final-Project/tests/패션잡지"

def get_local_image_path(filename_no_ext):
    """
    확장자(.jpg, .png 등)를 모르므로 폴더에서 파일을 찾아서 반환합니다.
    """
    # 1, 2, 3 등으로 시작하는 파일 찾기
    search_pattern = os.path.join(BASE_IMG_PATH, f"{filename_no_ext}.*")
    files = glob.glob(search_pattern)
    
    if not files:
        print(f"⚠️ [경고] 이미지를 찾을 수 없습니다: {search_pattern}")
        return "https://placehold.co/1024x1024?text=No+Image"
    
    # 첫 번째로 발견된 파일 반환 (예: 1.jpg)
    return files[0]

def encode_image_to_base64(image_path):
    """
    로컬 이미지 파일을 읽어서 HTML에 넣을 수 있는 Base64 문자열로 변환
    """
    if image_path.startswith("http"):
        return image_path
        
    try:
        with open(image_path, "rb") as img_file:
            encoded_string = base64.b64encode(img_file.read()).decode("utf-8")
            # 확장자 추출 (jpg, png 등)
            ext = image_path.split('.')[-1].lower()
            mime_type = "jpeg" if ext == "jpg" else ext
            return f"data:image/{mime_type};base64,{encoded_string}"
    except Exception as e:
        print(f"❌ 이미지 변환 실패 ({image_path}): {e}")
        return "https://placehold.co/1024x1024?text=Error"

# ==========================================
# 1. 테스트 데이터 (대본 + 로컬 이미지 경로)
# ==========================================

# Case 1: Golden Goose (폴더 내 '1.*' 파일)
input_golden_goose = {
    "title": "GOLDEN GOOSE’S GRIT AND GLAMOUR",
    "subtitle": "The Italian brand may be best known for its sneakers...",
    "body": "Over the past 25 years, Venice-based Golden Goose has grown from a small, artisanal operation to a global retail phenomenon. That’s based largely on the brand’s iconic weathered sneakers... You couldn’t call them street—they’re more elevated than that—but there’s a gently dilapidated vintage vibe about them...",
    "image": get_local_image_path("1") 
}

# Case 2: Omega (폴더 내 '2.*' 파일)
input_omega = {
    "title": "DEPTH OF FEELING",
    "subtitle": "Omega’s much-loved technical diver, the Planet Ocean, just got a major refresh",
    "body": "When Omega introduced the Planet Ocean, the goal was to go deeper—both figuratively and literally... It’s slimmed down, gained a ceramic bezel, been done up in gold... The first thing fans will notice is that Omega has ditched the helium-escape valve.",
    "image": get_local_image_path("2")
}

# Case 3: Prada (폴더 내 '3.*' 파일)
input_prada = {
    "title": "BIRTH OF THE COOL",
    "subtitle": "Nowadays, it's a no-brainer that box-office stars make unbeatable ambassadors...",
    "body": "In the mid-1990s... Prada wasn't playing. Instead of shouting for attention, the Milanese brand quietly nudged its way into men's fashion... But Malkovich gave Prada's clothes a different kind of sex appeal. Shot in black-and-white against a stark white background...",
    "image": get_local_image_path("3")
}

# ==========================================
# 2. [내부 함수] HTML 생성기 (Base64 적용)
# ==========================================
def generate_html_locally(plan, user_script, image_path):
    layout = plan.get("layout_guide", {})
    text_pos = layout.get("text_position", "center")
    font_theme = layout.get("font_theme", "Serif")

    # [CSS 매핑]
    pos_map = {
        "top": "top-12 left-0 w-full text-center",
        "top_left": "top-12 left-12 text-left max-w-lg",
        "center": "top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center w-full",
        "bottom": "bottom-12 left-0 w-full text-center",
        "bottom_right": "bottom-12 right-12 text-right max-w-lg",
        "left": "top-1/2 left-12 transform -translate-y-1/2 text-left max-w-md",
        "right": "top-1/2 right-12 transform -translate-y-1/2 text-right max-w-md"
    }
    
    css_position = pos_map.get(text_pos, pos_map["center"])
    css_font = "font-serif" if "Serif" in font_theme else "font-sans"
    if "Bold" in font_theme: css_font += " font-bold"

    # 이미지 경로가 로컬 파일이면 -> Base64로 인코딩하여 HTML에 박제
    print(f"   🖼️ 이미지 변환 중: {image_path}")
    final_img_src = encode_image_to_base64(image_path)

    # HTML 템플릿
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Lato:wght@300;400;700&display=swap" rel="stylesheet">
        <style>
            .font-serif { font-family: 'Playfair Display', serif; }
            .font-sans { font-family: 'Lato', sans-serif; }
        </style>
    </head>
    <body class="bg-gray-200 flex items-center justify-center min-h-screen p-10">
        <div class="relative w-[800px] h-[1000px] bg-black shadow-2xl overflow-hidden group">
            <img src="{{ image_src }}" class="absolute inset-0 w-full h-full object-cover opacity-90 group-hover:scale-105 transition duration-700">
            <div class="absolute inset-0 bg-gradient-to-b from-black/30 via-transparent to-black/60"></div>
            
            <div class="absolute {{ css_position }} text-white drop-shadow-lg p-8">
                <h3 class="text-xs tracking-[0.5em] uppercase mb-4 opacity-80">{{ selected_type }}</h3>
                <h1 class="{{ css_font }} text-6xl leading-tight mb-4">{{ title }}</h1>
                <p class="{{ css_font }} text-xl opacity-90 italic mb-6">{{ subtitle }}</p>
                <div class="w-20 h-1 bg-white opacity-50 mb-6 mx-auto"></div>
                <p class="text-sm opacity-80 max-w-prose mx-auto leading-relaxed hidden md:block">{{ body[:200] }}...</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return Template(html_template).render(
        title=user_script.get("title", ""),
        subtitle=user_script.get("subtitle", ""),
        body=user_script.get("body", ""),
        image_src=final_img_src, # Base64 문자열이 들어감
        css_position=css_position,
        css_font=css_font,
        selected_type=plan.get("selected_type", "TYPE_B")
    )

# ==========================================
# 3. 메인 테스트 함수
# ==========================================
def test(case_name, script_data):
    print(f"\n================ [TEST: {case_name}] ================")
    
    # 1. State 생성 (Vision은 None -> Planner가 시뮬레이션 함)
    dummy_state = MagazineState(
        user_script=script_data,
        vision_result=None, 
        plan=None,
        logs=[]
    )
    
    # 2. Planner 실행
    result_state = run_planner(dummy_state)
    plan = result_state["plan"]
    
    # 3. 결과 출력 (JSON)
    print("\n[🧠 Planner Result JSON]")
    print(json.dumps(plan, indent=2, ensure_ascii=False))

    # 4. HTML 생성 (내부 함수 사용)
    print(f"\n[🎨 HTML 생성 중...]")
    final_html = generate_html_locally(plan, script_data, script_data.get("image"))
    
    # 5. 파일 저장
    filename = f"result_{case_name.lower().replace(' ', '_')}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(final_html)
        
    print(f"✅ 저장 완료: {filename}")

if __name__ == "__main__":
    try:
        import jinja2
    except ImportError:
        print("⚠️ [경고] jinja2가 설치되지 않았습니다. 'pip install jinja2'를 실행해주세요.")
        exit()

    # 테스트 실행
    test("Golden Goose", input_golden_goose)
    test("Omega Watch", input_omega)
    test("Prada", input_prada)