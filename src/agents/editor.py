# src/agents/editor.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from src.state import MagazineState
from src.config import config

def run_editor(state: MagazineState) -> dict:
    """
    [Unified Structure Refactor]
    Planner의 전략에 따라 기사 원고를 작성합니다.
    state['articles'][id]['manuscript'] 에 결과를 저장합니다.
    """
    print("--- [4] Editor Agent: English Article Generation (Unified) ---")
    
    articles = state.get("articles", {})
    llm = config.get_llm()
    parser = JsonOutputParser()

    # 프롬프트 정의
    prompt = ChatPromptTemplate.from_template(
        """
        You are a Professional Editor for a High-End English Magazine.
        
        {mode_instruction}

        !!! CRITICAL RULE: ENGLISH OUTPUT ONLY !!!
        - The final output must be in **ENGLISH**.
        - Do NOT invent new fictional stories. Keep the facts intact.

        [Input Data]
        - Usre Request: {user_request}
        - Planner Strategy: {target_tone}
        - Image Context: {image_desc} (Use for Caption)
        - Layout Type: {layout_type}

        [Output JSON format]
        {{
            "headline": "English Title",
            "subhead": "Subtitle",
            "body": "English content...",
            "pull_quote": "Key quote",
            "caption": "Connection between image and text",
            "tags": ["Tag1", "Tag2"]
        }}
        """
    )
    
    chain = prompt | llm | parser

    for a_id, article in articles.items():
        # [Dependency Check]
        plan = article.get("plan")
        if not plan:
            print(f"⚠️ [Editor] 기사 ID {a_id}: Planner가 실행되지 않았습니다.")
            plan = {}

        # 데이터 로드
        req_text = article.get("request", "")
        title_text = article.get("title", "Untitled")
        is_gen = article.get("is_generated", True)
        
        # Planner & Vision 데이터
        target_tone = plan.get("selected_type") or article.get("style", "Elegant")
        vision = article.get("vision_analysis", {})
        image_desc = vision.get("metadata", {}).get("description", "Visual")
        
        # --- [Case 1: 사용자 직접 입력 보존] ---
        if not is_gen:
            print(f"   -> 👤 사용자 본문 유지 (ID: {a_id})")
            article["manuscript"] = {
                "headline": title_text,
                "subhead": "Original Draft",
                "body": req_text,
                "pull_quote": "",
                "caption": f"Visual context for {title_text}",
                "tags": [target_tone]
            }
            continue

        # --- [Case 2: AI 자동 생성] ---
        # 모드 결정 (긴 텍스트: 교정 / 짧은 텍스트: 생성)
        is_polish_mode = len(req_text.strip()) > 50
        
        if is_polish_mode:
            mode_instruction = "MODE: Proofreading & Minor Fixes. Improve grammar/flow."
        else:
            mode_instruction = "MODE: Creative Writing. Generate full article from keywords."

        print(f"✍️ Editor 작성 중... ID:{a_id} | 모드:{'Polish' if is_polish_mode else 'Create'}")

        try:
            generated = chain.invoke({
                "mode_instruction": mode_instruction,
                "user_request": req_text,
                "target_tone": target_tone,
                "image_desc": image_desc,
                "layout_type": plan.get("selected_type", "Standard")
            })

            # ID 및 제목 보정
            if title_text and title_text != "Untitled":
                generated["headline"] = title_text
            
            # ✅ 결과 저장
            article["manuscript"] = generated

        except Exception as e:
            print(f"❌ Editor Error (ID: {a_id}): {e}")
            article["manuscript"] = {
                "headline": title_text,
                "subhead": "Error",
                "body": f"generation failed: {req_text}",
                "caption": "Error",
                "tags": ["Error"]
            }

    return {"articles": articles}