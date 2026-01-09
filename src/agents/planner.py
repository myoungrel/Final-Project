# src/agents/planner.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from src.state import MagazineState
from src.config import config

def run_planner(state: MagazineState) -> dict:
    """
    [Unified Structure Refactor]
    Vision 결과를 바탕으로 기사 레이아웃 및 컨셉을 기획합니다.
    state['articles'][id]['plan'] 에 결과를 저장합니다.
    """
    print("--- [Planner] 매거진 컨셉 기획 중... (Unified) ---")

    articles = state.get("articles", {})
    llm = config.get_llm()
    parser = JsonOutputParser()
    
    # 기획 프롬프트
    prompt = ChatPromptTemplate.from_template(
        """
        You are the Editor-in-Chief of a high-end Fashion Magazine.
        Decide the specific 'Layout Type' based on the Vision Strategy and Image Mood.

        [INPUTS]
        - Vision Strategy: {strategy} (If 'Overlay', place text ON image. If 'Separated', place text BESIDE image.)
        - Image Mood: {img_mood}
        - Title: {title}
        - User Request: {user_request}
        - Style Preference: {user_style}
        - Subject Position: {subject_pos}

        [LAYOUT MENU - Choose ONE based on Strategy]
        
        <CASE A: Strategy is 'Overlay'>
        1. "TYPE_FASHION_COVER": Classic magazine cover. Big bold title at the top or center. Elegant and impactful.
        2. "TYPE_STREET_VIBE": Hip, trendy, and free-spirited. Text can be scattered or in corners. Good for street snaps.

        <CASE B: Strategy is 'Separated'>
        3. "TYPE_EDITORIAL_SPLIT": Standard article layout. Image on one side, text column on the other. Professional and readable.
        4. "TYPE_LUXURY_PRODUCT": Minimalist layout for products (watches, bags). Clean background, small elegant text.

        [TASK]
        1. Analyze the inputs and select the best Type from the menu above.
        2. If 'Separated', choose a background color that matches the image mood.
        3. Respect the [Style Preference] if provided by the user.

        Return JSON:
        {{
            "selected_type": "String (One of the types above)",
            "concept_rationale": "Why you chose this type...",
            "layout_guide": {{ 
                "text_position": "{subject_pos}", 
                "font_theme": "Serif (Luxury) or Sans-serif (Modern)",
                "background_color": "#HexCode (Only for Separated types, otherwise null)"
            }}
        }}
        """
    )

    chain = prompt | llm | parser

    for a_id, article in articles.items():
        # [Strict Dependency Check]
        vision_analysis = article.get("vision_analysis")
        if not vision_analysis:
            # Vision 결과가 없으면 에러를 발생시키거나 로그를 남기고 건너뜀 (여기선 안전하게 기본값 처리)
            print(f"⚠️ [Planner] 기사 ID {a_id}: Vision 분석 데이터가 누락되었습니다.")
            vision_analysis = {}

        # 데이터 추출
        title_text = article.get("title", "Untitled")
        request_text = article.get("request", "")
        style_pref = article.get("style", "Modern")
        
        # Vision 데이터 파싱
        strategy = vision_analysis.get("layout_strategy", {}).get("recommendation", "Separated")
        metadata = vision_analysis.get("metadata", {})
        img_mood = metadata.get("mood", "General")
        subject_pos = metadata.get("dominant_position", "Center")

        print(f"🧠 기획 중... ID:{a_id} | 전략:{strategy} | 스타일:{style_pref}")

        try:
            plan = chain.invoke({
                "title": title_text,
                "user_request": request_text,
                "user_style": style_pref,
                "img_mood": img_mood,
                "strategy": strategy,
                "subject_pos": subject_pos 
            })
            
            # ✅ 결과 저장 (Unified Schema)
            article["plan"] = plan
            
        except Exception as e:
            print(f"❌ Planner Error (ID: {a_id}): {e}")
            # Fallback
            article["plan"] = {
                "selected_type": "TYPE_EDITORIAL_SPLIT",
                "concept_rationale": "Error Recovery",
                "layout_guide": {"font_theme": "Sans-serif"}
            }

    return {"articles": articles}