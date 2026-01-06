# app.py
import streamlit as st
import os
import shutil
from src.main import app_graph

# 페이지 기본 설정
st.set_page_config(page_title="AI Magazine Agent", layout="wide")
st.title("🤖 AI Magazine Generator")

# --- [1] 사이드바: 입력 및 설정 ---
with st.sidebar:
    st.header("Magazine Settings")
    user_input = st.text_area("요청사항 (Topic)", "이번 시즌 트렌드는 '조용한 럭셔리'입니다. 화려한 로고 대신 소재에 집중하세요.")
    
    # 이미지 업로드
    uploaded_file = st.file_uploader("메인 이미지 업로드", type=['png', 'jpg', 'jpeg'])
    
    start_btn = st.button("매거진 생성 시작! 🚀", use_container_width=True)

# --- [2] 메인 로직 ---
if start_btn:
    # A. 이미지 파일 임시 저장 (Backend 호환성 확보)
    image_path = None
    if uploaded_file:
        # temp 폴더 생성
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        
        # 파일 저장
        image_path = os.path.join(temp_dir, uploaded_file.name)
        with open(image_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.sidebar.success(f"이미지 처리 완료: {uploaded_file.name}")
    else:
        st.sidebar.warning("이미지 없이 텍스트로만 생성합니다.")

    # B. 초기 상태 설정 (State 키 매칭)
    initial_state = {
        "user_input": user_input,
        "image_path": image_path, # 파일 경로 전달 (중요!)
        "logs": []
    }

    # 결과 HTML을 담을 변수
    final_html_content = None

    # C. LangGraph 실행 및 스트리밍
    st.divider()
    with st.status("AI 에이전트 팀이 작업을 시작합니다...", expanded=True) as status:
        try:
            # app_graph.stream()을 통해 각 노드의 실행 결과를 실시간으로 받음
            for step in app_graph.stream(initial_state):
                for node_name, node_output in step.items():
                    
                    # 1. 노드 완료 로그
                    st.write(f"✅ **{node_name.upper()}** 단계 완료")
                    
                    # 2. Vision 결과 (이미지 분석)
                    if node_name == "vision" and "vision_result" in node_output:
                        with st.expander("📸 Vision: 이미지 분석 결과"):
                            st.json(node_output["vision_result"])

                    # 3. Planner 결과 (기획)
                    if node_name == "planner" and "planner_result" in node_output:
                         with st.expander("🧠 Planner: 기획안"):
                            st.write(f"**컨셉:** {node_output['planner_result'].get('selected_type')}")
                            st.write(f"**톤앤매너:** {node_output['planner_result'].get('target_tone')}")

                    # 4. Paginator 결과 (페이지 분할)
                    if node_name == "paginator":
                        pages = node_output.get("pages", [])
                        st.info(f"📄 Paginator: 총 {len(pages)}개의 페이지로 구성을 나눴습니다.")

                    # 5. Director 결과 (디자인 스펙)
                    if node_name == "director" and "design_spec" in node_output:
                        mood = node_output['design_spec'].get('theme', {}).get('mood', 'N/A')
                        st.success(f"🎨 Director: '{mood}' 스타일의 디자인 시스템 구축 완료")

                    # 6. Publisher 결과 (HTML 확보) - 여기가 핵심! ⭐
                    if "final_html" in node_output:
                        final_html_content = node_output["final_html"]
                        st.write("🖨️ Publisher: HTML 렌더링 완료!")

            status.update(label="모든 작업이 완료되었습니다!", state="complete", expanded=False)
            
        except Exception as e:
            st.error(f"❌ 에러 발생: {e}")
            # 디버깅을 위해 에러 상세 출력
            import traceback
            st.code(traceback.format_exc())

    # D. 결과 화면 출력
    if final_html_content:
        st.divider()
        st.subheader("✨ 완성된 매거진")
        
        # 1. HTML 미리보기 (iframe)
        # scrolling=True로 설정하여 긴 내용도 볼 수 있게 함
        st.components.v1.html(final_html_content, height=800, scrolling=True)
        
        # 2. 다운로드 버튼
        col1, col2 = st.columns([1, 4])
        with col1:
            st.download_button(
                label="📥 HTML 파일 다운로드",
                data=final_html_content,
                file_name="my_magazine.html",
                mime="text/html"
            )
        with col2:
            st.success("브라우저에서 열면 더 멋진 효과를 볼 수 있어요!")

    # (선택) 임시 파일 정리
    # if image_path and os.path.exists(image_path):
    #    os.remove(image_path)