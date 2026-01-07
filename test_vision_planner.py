import streamlit as st
import os
import json
import base64
from jinja2 import Template
import streamlit.components.v1 as components

# 모듈 임포트
try:
    from src.agents.vision import run_vision_analysis
    from src.agents.planner import run_planner
except ImportError:
    st.error("❌ 'src' 폴더를 찾을 수 없습니다. 실행 위치가 'Final-Project' 최상위 폴더인지 확인하세요.")
    st.stop()

# ==========================================
# 1. [유틸리티] Vision 좌표 -> Planner 위치 변환
# ==========================================
def map_coordinates_to_zone(space_analysis):
    # Separated 전략일 경우 space_analysis가 비어있을 수 있음
    if not space_analysis: return "center"
    
    box = space_analysis[0]
    y_center, x_center = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    
    vertical = "center"
    if y_center < 333: vertical = "top"
    elif y_center > 666: vertical = "bottom"
    
    horizontal = "center"
    if x_center < 333: horizontal = "left"
    elif x_center > 666: horizontal = "right"
    
    if vertical == "center" and horizontal == "center": return "center"
    if vertical == "center": return horizontal
    if horizontal == "center": return vertical
    return f"{vertical}_{horizontal}"

# ==========================================
# 2. [Publisher] HTML 생성 함수 (동적 레이아웃)
# ==========================================
def generate_html(plan, script, img_base64, vision_data):
    # 1. Planner가 결정한 타입 가져오기
    layout_type = plan.get("selected_type", "TYPE_FASHION_COVER")
    
    # 2. 공통 데이터
    colors = vision_data.get("metadata", {}).get("hex_colors", ["#000000"])
    mood = vision_data.get("metadata", {}).get("mood", "N/A")
    
    # 폰트 설정
    layout_guide = plan.get("layout_guide", {})
    font_theme = layout_guide.get("font_theme", "Serif")
    font_class = "font-serif" if "Serif" in font_theme else "font-sans font-bold tracking-tight"

    # =========================================================
    # [CASE A] 분리형 레이아웃 (Separated / Editorial / Split)
    # =========================================================
    if any(keyword in layout_type for keyword in ["SPLIT", "EDITORIAL", "PRODUCT", "SEPARATED"]):
        
        # 배경색 결정 (Vision 추출 색상 활용 or Planner 추천)
        planner_bg = layout_guide.get("background_color")
        # Planner가 색을 안 줬으면 Vision의 첫 번째 색(보통 배경색) 사용, 없으면 흰색
        bg_color = planner_bg if planner_bg else (colors[0] if colors else "#ffffff")
        
        # 텍스트 색상 (배경이 어두우면 흰색, 밝으면 검은색 - 간단한 로직)
        # 여기서는 안전하게 흰 배경에 검은 글씨 or 다크모드 등 고정 스타일 사용 추천
        # (데모용으로는 깔끔한 Editorial 화이트 테마 적용)
        
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.tailwindcss.com"></script>
            <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Lato:wght@300;400;700&display=swap" rel="stylesheet">
            <style>
                .font-serif { font-family: 'Playfair Display', serif; } 
                .font-sans { font-family: 'Lato', sans-serif; }
                ::-webkit-scrollbar { display: none; }
            </style>
        </head>
        <body class="bg-white m-0 p-0 h-screen overflow-hidden flex flex-col md:flex-row">
            
            <div class="w-full md:w-[55%] h-[50%] md:h-full relative overflow-hidden bg-gray-100">
                <img src="{{ img }}" class="absolute inset-0 w-full h-full object-cover grayscale hover:grayscale-0 transition duration-700">
            </div>

            <div class="w-full md:w-[45%] h-[50%] md:h-full bg-white text-black p-10 md:p-14 flex flex-col justify-center overflow-y-auto">
                
                <div class="border-b-2 border-black mb-8 pb-2 flex justify-between items-end">
                    <span class="text-xs font-bold tracking-[0.2em] uppercase text-gray-400">{{ type }}</span>
                </div>

                <h1 class="{{ font }} text-5xl md:text-6xl leading-tight mb-4 text-black">
                    {{ title }}
                </h1>
                
                <p class="text-xl italic text-gray-500 mb-8 font-serif">
                    {{ sub }}
                </p>

                <div class="font-sans text-gray-800 leading-relaxed text-justify text-sm md:text-base">
                    <span class="text-4xl float-left mr-2 font-serif font-bold">"</span>
                    {{ body }}
                </div>
                
                <div class="mt-auto pt-10 border-t border-gray-100 flex justify-between items-end text-[10px] text-gray-400 uppercase tracking-widest">
                    <span>Vol. 2026</span>
                    <span>Mood: {{ mood }}</span>
                </div>
            </div>
        </body>
        </html>
        """
        
        return Template(template).render(
            img=img_base64, font=font_class, type=layout_type,
            title=script["title"], sub=script["subtitle"], body=script["body"],
            mood=mood
        )

    # =========================================================
    # [CASE B] 덮어쓰기 레이아웃 (Overlay / Cover)
    # =========================================================
    else:
        text_pos = layout_guide.get("text_position", "center")
        
        pos_style = {
            "top_left": "top-0 left-0 bg-gradient-to-b from-black/80 via-transparent to-transparent pt-12 pl-12 text-left items-start justify-start",
            "top_right": "top-0 right-0 bg-gradient-to-b from-black/80 via-transparent to-transparent pt-12 pr-12 text-right items-start justify-end",
            "bottom_left": "bottom-0 left-0 bg-gradient-to-t from-black/90 via-transparent to-transparent pb-12 pl-12 text-left items-end justify-start",
            "bottom_right": "bottom-0 right-0 bg-gradient-to-t from-black/90 via-transparent to-transparent pb-12 pr-12 text-right items-end justify-end",
            "center": "inset-0 bg-black/30 flex flex-col items-center justify-center text-center",
            "left": "inset-y-0 left-0 bg-gradient-to-r from-black/80 to-transparent flex flex-col justify-center pl-12 text-left",
            "right": "inset-y-0 right-0 bg-gradient-to-l from-black/80 to-transparent flex flex-col justify-center pr-12 text-right",
            "top": "top-0 inset-x-0 bg-gradient-to-b from-black/80 to-transparent pt-12 text-center",
            "bottom": "bottom-0 inset-x-0 bg-gradient-to-t from-black/90 to-transparent pb-12 text-center"
        }
        container_class = pos_style.get(text_pos, pos_style["center"])

        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.tailwindcss.com"></script>
            <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Lato:wght@300;400;700&display=swap" rel="stylesheet">
            <style>
                .font-serif { font-family: 'Playfair Display', serif; } 
                .font-sans { font-family: 'Lato', sans-serif; }
                ::-webkit-scrollbar { display: none; }
            </style>
        </head>
        <body class="bg-gray-100 m-0 p-0 flex justify-center items-center h-screen overflow-hidden">
            <div class="relative w-full h-full bg-black text-white overflow-hidden group">
                
                <img src="{{ img }}" class="absolute inset-0 w-full h-full object-cover">
                
                <div class="absolute {{ container_class }} w-full h-full flex flex-col p-8 transition-all duration-500 z-10">
                    
                    <div class="mb-4 flex items-center gap-3 opacity-70">
                        <span class="text-[10px] tracking-[0.3em] uppercase border border-white/40 px-2 py-1">
                            {{ type }}
                        </span>
                    </div>

                    <h1 class="{{ font }} text-6xl leading-[0.9] mb-4 drop-shadow-xl">
                        {{ title }}
                    </h1>

                    <p class="text-xl font-serif italic opacity-90 mb-6 font-light drop-shadow-md max-w-2xl">
                        {{ sub }}
                    </p>

                    <div class="w-16 h-[2px] bg-white/60 mb-6"></div>

                    <p class="text-sm font-sans opacity-85 max-w-md leading-relaxed drop-shadow-sm">
                        {{ body }}
                    </p>
                    
                    <div class="mt-auto pt-8 opacity-50 text-[10px]">
                        Analysis: {{ mood }}
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return Template(template).render(
            img=img_base64,
            container_class=container_class,
            font=font_class,
            type=layout_type,
            title=script["title"], sub=script["subtitle"], body=script["body"],
            mood=mood
        )

# ==========================================
# 3. [Streamlit] 메인 실행 로직
# ==========================================
def main():
    st.set_page_config(page_title="AI Magazine Generator", layout="wide")
    st.title("🎨 AI Magazine Creator")
    st.markdown("Vision(분석) -> Planner(기획) -> **Publisher(HTML)** 통합 테스트")

    with st.sidebar:
        st.header("1. Settings")
        uploaded_file = st.file_uploader("이미지 업로드", type=["jpg", "png", "jpeg"])
        
        st.subheader("2. Editor Script")
        title = st.text_input("제목", "THE NEW ERA")
        subtitle = st.text_input("부제목", "Minimalism & Luxury")
        body = st.text_area("본문", "This creates a sophisticated atmosphere combined with modern aesthetics. The design focuses on clarity and elegance.")
        
        run_btn = st.button("🚀 매거진 생성", type="primary")

    if run_btn and uploaded_file:
        # Base64 변환
        bytes_data = uploaded_file.getvalue()
        b64_str = base64.b64encode(bytes_data).decode()
        img_base64 = f"data:{uploaded_file.type};base64,{b64_str}"
        
        # 임시 파일 저장 (Vision 분석용)
        temp_dir = "temp_uploads"
        os.makedirs(temp_dir, exist_ok=True)
        img_path = os.path.join(temp_dir, uploaded_file.name)
        with open(img_path, "wb") as f:
            f.write(bytes_data)

        col1, col2 = st.columns([1, 1.5])

        with col1:
            st.subheader("🤖 AI Analysis Log")
            
            # Step A: Vision Analysis
            with st.status("📸 Vision Agent 분석 중...", expanded=True) as status:
                state = {"image_path": img_path, "user_input": f"Analyze layout for {title}"}
                vision_out = run_vision_analysis(state)
                raw_vision = vision_out.get("vision_result")
                
                if raw_vision:
                    # Vision의 전략(Strategy) 확인
                    strategy = raw_vision.get("layout_strategy", {}).get("recommendation", "Unknown")
                    status.update(label=f"✅ Vision 분석 완료: {strategy} 모드 추천", state="complete")
                    
                    st.success(f"추천 전략: **{strategy}**")
                    st.json(raw_vision.get("layout_strategy"))
                else:
                    status.update(label="❌ Vision 분석 실패", state="error")
                    st.stop()

            # Step B: Planner Planning
            with st.status("🧠 Planner Agent 기획 중...", expanded=True) as status:
                # 좌표 변환 (Overlay일 경우에만 유효)
                safe_zone = map_coordinates_to_zone(raw_vision.get("space_analysis"))
                
                # Vision 데이터를 Planner로 전달 (layout_strategy 포함)
                mapped_vision = raw_vision # 전체 데이터 전달
                mapped_vision["safe_zone"] = safe_zone # 변환된 좌표 추가
                
                planner_state = {
                    "user_script": {"title": title, "subtitle": subtitle, "body": body},
                    "vision_result": mapped_vision,
                    "plan": None 
                }
                
                planner_out = run_planner(planner_state)
                plan = planner_out.get("plan")
                
                if plan:
                    sel_type = plan.get("selected_type")
                    status.update(label=f"✅ 기획 확정: {sel_type}", state="complete")
                    st.info(f"확정 타입: **{sel_type}**")
                    st.write(f"배치 위치: {plan['layout_guide'].get('text_position')}")
                else:
                    status.update(label="❌ Planner 기획 실패", state="error")
                    st.stop()

        # [오른쪽] 최종 결과
        with col2:
            st.subheader("✨ Final Output")
            if plan:
                with st.spinner("🎨 HTML 렌더링 중..."):
                    final_html = generate_html(plan, planner_state["user_script"], img_base64, raw_vision)
                    components.html(final_html, height=800, scrolling=True)
                    
                    st.download_button(
                        label="📥 HTML 다운로드",
                        data=final_html,
                        file_name="magazine_cover.html",
                        mime="text/html"
                    )

    elif run_btn and not uploaded_file:
        st.warning("이미지를 업로드해주세요.")

if __name__ == "__main__":
    main()