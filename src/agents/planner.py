from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from src.state import MagazineState
from src.config import config

def run_planner(state: MagazineState) -> dict:
    print("--- [Planner] 매거진 컨셉 기획 중... ---")

    user_inputs = state.get("user_input", []) # List[Dict]
    vision_results = state.get("vision_result", {}) # Dict[id, result]
    
    llm = config.get_llm()
    parser = JsonOutputParser()
    
    # [New Code]
    # 결과를 담을 딕셔너리
    plans = {}

    # 3. 기획 프롬프트 (메뉴판 제공)
    # [수정] {title} 외에 {user_request}를 추가하여 문맥 파악 능력 향상
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
        - Safe Aareas / Subject Position: {safe_areas}

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
                "text_position": "{safe_areas}", 
                "font_theme": "Serif (Luxury) or Sans-serif (Modern)",
                "background_color": "#HexCode (Only for Separated types, otherwise null)"
            }}
        }}
        """
    )

    chain = prompt | llm | parser

    for item in user_inputs:
        a_id = str(item.get("id"))
        title_text = item.get("title", "Untitled")
        request_text = item.get("request", "")
        style_pref = item.get("style", "Modern")
        
        # 해당 ID의 Vision 결과 가져오기 (없으면 기본값)
        v_res = vision_results.get(a_id, {})
        
        # Vision 결과 파싱
        strategy = v_res.get("layout_strategy", {}).get("recommendation", "Separated")
        metadata = v_res.get("metadata", {})
        img_mood = metadata.get("mood", "General")
        safe_areas = metadata.get("dominant_position", "Center")

        print(f"🧠 기획 중... ID:{a_id} | 전략:{strategy} | 스타일:{style_pref} | 위치:{safe_areas}")

        try:
            # 👇 [수정됨] chain.invoke 안에 "safe_areas" 키 추가 (에러 해결)
            plan = chain.invoke({
                "title": title_text,
                "user_request": request_text,
                "user_style": style_pref,
                "img_mood": img_mood,
                "strategy": strategy,
                "safe_areas": safe_areas  # <--- [여기 추가 필수!] 이게 없어서 에러가 났습니다.
            })
            
            # ID별로 계획 저장
            plans[a_id] = plan
            
        except Exception as e:
            print(f"❌ Planner Error (ID: {a_id}): {e}")
            # 에러 시 안전한 기본값
            fallback_type = "TYPE_EDITORIAL_SPLIT" if strategy == "Separated" else "TYPE_FASHION_COVER"
            plans[a_id] = {
                "selected_type": fallback_type,
                "concept_rationale": "Error Fallback",
                "layout_guide": {"font_theme": "Sans-serif"}
            }

    return {
            "planner_result": plans, # Dict[id, plan_json]
            "logs": [f"Planner: {len(plans)}개 기사 기획 완료"]
        }