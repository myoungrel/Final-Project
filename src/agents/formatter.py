from src.state import MagazineState

def run_formatter(state: MagazineState) -> dict:
    print("--- [8] UX Formatter: 최종 결과물 패키징... ---")
    
    # 최종 HTML 가져오기 (없으면 에러 메시지 사용)
    final_html = state.get("html_code", "")
    
    if not final_html:
        final_html = "<h1>⚠️ HTML generation failed (Formatter found empty html_code)</h1>"

    return {
        "final_output": final_html,
        "html_code": final_html, # 안전하게 둘 다 채움
        "logs": ["Formatter: 최종 렌더링 준비 완료"]
    }