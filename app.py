# app.py
import streamlit as st
import base64
from src.main import app_graph

st.set_page_config(page_title="AI Magazine Agent", layout="wide")
st.title("🤖 AI Magazine Generator (In-Memory Ver.)")

with st.sidebar:
    user_input = st.text_area("요청사항", "이 사진에 어울리는 감성적인 에세이 써줘")
    uploaded_file = st.file_uploader("사진 업로드", type=['png', 'jpg', 'jpeg'])
    start_btn = st.button("매거진 생성 시작! 🚀")

if start_btn:
    # 1. 이미지 처리 (메모리 로드)
    if uploaded_file:
        bytes_data = uploaded_file.getvalue()
        base64_image = base64.b64encode(bytes_data).decode('utf-8')
        st.sidebar.success("이미지 메모리 로드 완료! (저장 X)")
    else:
        base64_image = None

    # 2. 초기 상태 설정
    initial_state = {
        "user_input": user_input,
        "image_data": base64_image,
        "logs": []
    }

    # 3. 결과물을 담을 변수 미리 준비! (중요 ✨)
    final_html = None

    # 4. 에이전트 실행
    with st.status("에이전트 팀이 협업 중입니다...", expanded=True) as status:
        try:
            for step in app_graph.stream(initial_state):
                for node_name, node_output in step.items():
                    st.write(f"✅ **{node_name.upper()}** 완료")
                    
                    # 로그 찍기
                    if 'logs' in node_output:
                        st.code(node_output['logs'][-1])
                    
                    # Vision 결과 확인
                    if node_name == "vision" and "vision_result" in node_output:
                        with st.expander("📸 Vision 분석 결과"):
                            st.info(node_output["vision_result"])
                    
                    # 👇 [핵심] 마지막 단계(formatter)에서 HTML 낚아채기!
                    if "final_output" in node_output:
                        final_html = node_output["final_output"]

            status.update(label="작업 완료!", state="complete", expanded=False)
            
        except Exception as e:
            st.error(f"에러 발생: {e}")

    # 5. 결과 화면 출력 (로딩 바 밖에서 실행)
    if final_html:
        st.divider()
        st.subheader("✨ 생성된 매거진 페이지")
        
        # HTML 렌더링 (높이 800px, 스크롤 가능)
        st.components.v1.html(final_html, height=800, scrolling=True)
        
        # 다운로드 버튼
        st.download_button(
            label="HTML 파일 다운로드",
            data=final_html,
            file_name="magazine_page.html",
            mime="text/html"
        )