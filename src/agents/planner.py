# 파일 위치: src/agents/planner.py

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from src.state import MagazineState
from src.config import config

def run_planner(state: MagazineState) -> dict:
    print("--- [Planner] 매거진 컨셉 기획 중... ---")
    
    user_input = state.get("user_input")
    user_script = state.get("user_script", {}) # 딕셔너리 (Dict)
    
    # 제목 결정 로직: 
    # 입력(user_input)이 있으면 그걸 제목으로 쓰고(String), 
    # 없으면 user_script 딕셔너리에서 title을 꺼내 쓴다.
    if user_input and isinstance(user_input, str):
        final_title = user_input
    else:
        final_title = user_script.get("title", "Untitled Project")

    vision_result = state.get("vision_result") or {}
    # 1. Vision 데이터 검증 및 기본값 설정
    if not vision_result:
        print("❌ [Critical] Vision 데이터 누락. 기본값으로 진행합니다.")
        vision_result = {
            "layout_strategy": {"recommendation": "Overlay"}, # 기본은 덮어쓰기
            "img_mood": "Modern",
            "safe_zone": "center"
        }
    
    # Vision이 제안한 전략 (Overlay vs Separated) 가져오기
    strategy = vision_result.get("layout_strategy", {}).get("recommendation", "Overlay")
    print(f"✅ Vision 제안 전략: {strategy}")

    llm = config.get_llm()
    parser = JsonOutputParser()

    # 2. 기획 프롬프트 (메뉴판 제공)
    prompt = ChatPromptTemplate.from_template(
        """
        You are the Editor-in-Chief of a high-end Fashion Magazine.
        Decide the specific 'Layout Type' based on the Vision Strategy and Image Mood.

        [INPUTS]
        - Vision Strategy: {strategy} (If 'Overlay', place text ON image. If 'Separated', place text BESIDE image.)
        - Image Mood: {img_mood}
        - Title: {title}
        - Safe Zone: {safe_zone}

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

        Return JSON:
        {{
            "selected_type": "String (One of the types above)",
            "concept_rationale": "Why you chose this type...",
            "layout_guide": {{ 
                "text_position": "{safe_zone}", 
                "font_theme": "Serif (Luxury) or Sans-serif (Modern)",
                "background_color": "#HexCode (Only for Separated types, otherwise null)"
            }}
        }}
        """
    )

    chain = prompt | llm | parser

    try:
        plan = chain.invoke({
            "title": final_title,
            "img_mood": vision_result.get("img_mood"),
            "strategy": strategy,
            "safe_zone": vision_result.get("safe_zone")
        })
        
        print(f"🧠 기획 확정: {plan.get('selected_type')} (전략: {strategy})")
        
        return {
            "planner_result": plan,
            "intent": plan.get("selected_type"),
            "vision_result": vision_result,
            "logs": [f"Planner: {plan.get('selected_type')} 선정"]
        }

    except Exception as e:
        print(f"❌ Planner Error: {e}")
        # 에러 시 안전한 기본값 반환
        fallback_type = "TYPE_EDITORIAL_SPLIT" if strategy == "Separated" else "TYPE_FASHION_COVER"
        return {"plan": {"selected_type": fallback_type}, "logs": ["Error"]}