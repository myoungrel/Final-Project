# app.py
import streamlit as st
import base64
import io
from PIL import Image
from src.main import app_graph

# [이미지 최적화 함수 유지]
def optimize_image(uploaded_file, max_width=1024):
    try:
        image = Image.open(uploaded_file)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        if image.width > max_width:
            ratio = max_width / float(image.width)
            new_height = int(float(image.height) * ratio)
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        return buffer.getvalue()
    except Exception as e:
        st.error(f"이미지 오류: {e}")
        return uploaded_file.getvalue()

st.set_page_config(page_title="AI Magazine Agent", layout="wide")
st.title("📚 AI Magazine Generator (Multi-Page Ver.)")

# --- [Session State 초기화] ---
if "articles" not in st.session_state:
    st.session_state.articles = [] # 기사들을 담을 리스트

with st.sidebar:
    st.header("📝 기사 추가하기")
    
    # 1. 입력 폼
    temp_title = st.text_input("제목 (Title)", key="input_title")
    temp_style = st.selectbox("스타일", ["Modern", "Elegant", "Retro", "Bold"], key="input_style")
    temp_mode = st.radio("본문 방식", ["AI 생성", "직접 입력"], key="input_mode")
    
    if temp_mode == "AI 생성":
        temp_text = st.text_area("요청사항 (Prompt)", "이 사진의 분위기를 살려줘", key="input_text")
        is_gen = True
    else:
        temp_text = st.text_area("본문 내용", key="input_text_manual")
        is_gen = False
        
    temp_file = st.file_uploader("사진 추가", type=['jpg', 'png'], key="input_file")
    
    # 2. 추가 버튼 (장바구니 담기)
    if st.button("➕ 기사 목록에 추가"):
        if not temp_title or not temp_file:
            st.error("제목과 사진은 필수입니다!")
        else:
            # 이미지 처리
            img_bytes = optimize_image(temp_file)
            b64_img = base64.b64encode(img_bytes).decode('utf-8')
            
            # 리스트에 저장 (ID는 현재 리스트 길이 이용)
            article_id = str(len(st.session_state.articles))
            
            new_article = {
                "id": article_id,
                "title": temp_title,
                "text": temp_text,
                "style": temp_style,
                "is_generated": is_gen,
                "image_b64": b64_img, # 편의상 여기에 잠시 저장
                "filename": temp_file.name
            }
            st.session_state.articles.append(new_article)
            st.success(f"'{temp_title}' 기사가 추가되었습니다! (총 {len(st.session_state.articles)}개)")

    st.divider()
    
    # 3. 생성 버튼 (최종 전송)
    generate_btn = st.button("🚀 매거진 생성 시작", type="primary")

# --- [메인 화면: 담긴 기사 목록 보여주기] ---
if len(st.session_state.articles) > 0:
    st.subheader(f"📋 현재 담긴 기사 목록 ({len(st.session_state.articles)}개)")
    cols = st.columns(3)
    for idx, art in enumerate(st.session_state.articles):
        with cols[idx % 3]:
            st.info(f"[{idx+1}] {art['title']}")
            st.caption(f"스타일: {art['style']}")
else:
    st.info("👈 왼쪽 사이드바에서 기사를 추가해주세요.")

# --- [생성 로직] ---
if generate_btn and len(st.session_state.articles) > 0:
    # 1. State 구조 변환 (List[Article] + Dict[Image])
    user_inputs = []
    image_data_map = {}
    
    for art in st.session_state.articles:
        # 이미지는 별도 맵으로 분리 (토큰 절약 및 구조화)
        image_data_map[art['id']] = art['image_b64']
        
        # 텍스트 정보만 user_input 리스트에 담음
        user_inputs.append({
            "id": art['id'],
            "title": art['title'],
            "request": art['text'],
            "style": art['style'],
            "is_generated": art['is_generated']
        })

    # 2. 초기 상태 설정
    initial_state = {
        "user_input": user_inputs,    # 리스트
        "image_data": image_data_map, # 딕셔너리 {id: b64}
        "logs": []
    }
    
    final_html = None

    # 3. 그래프 실행
    with st.status("AI 편집팀이 매거진을 제작 중입니다...", expanded=True) as status:
        try:
            for step in app_graph.stream(initial_state):
                for node_name, node_output in step.items():
                    st.write(f"✅ **{node_name.upper()}** 완료")
                    if 'logs' in node_output:
                        st.code(node_output['logs'][-1])
                    if "final_output" in node_output:
                        final_html = node_output["final_output"]
            
            status.update(label="작업 완료!", state="complete", expanded=False)
        except Exception as e:
            st.error(f"프로세스 에러: {e}")

    # 4. 결과 출력
    if final_html:
        st.divider()
        st.subheader("✨ 완성된 매거진")
        st.components.v1.html(final_html, height=800, scrolling=True)
        st.download_button("HTML 다운로드", final_html, "my_magazine.html", "text/html")