from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from src.state import MagazineState
from src.config import config

def run_planner(state: MagazineState) -> dict:
    print("--- [Planner] 매거진 컨셉 기획 중... ---")
    
    # 1. user_input 데이터 안전하게 가져오기 (타입 체크 및 데이터 정제)
    raw_input = state["user_input"]
    
    # 기본값 설정
    title_text = "Untitled"
    request_text = ""

    # (A) 입력이 딕셔너리인 경우 (Streamlit 등에서 구조화해서 보냄)
    if isinstance(raw_input, dict):
        title_text = raw_input.get("title", "Untitled")
        # request 키가 없으면 전체를 문자열로 변환하거나 topic 사용
        request_text = raw_input.get("request", raw_input.get("topic", str(raw_input)))
        
    # (B) 입력이 문자열인 경우 (단순 텍스트 입력)
    elif isinstance(raw_input, str):
        title_text = "Untitled" # 문자열만 왔을 땐 제목을 알 수 없음
        request_text = raw_input
        
    # 2. Vision 데이터 검증 및 기본값 설정
    vision_result = state.get("vision_result")
    
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
        # [수정] 위에서 정제한 title_text와 request_text를 넘겨줍니다.
        # 이제 .get() 에러가 발생하지 않습니다.
        plan = chain.invoke({
            "title": title_text,
            "user_request": request_text,
            "img_mood": vision_result.get("img_mood"),
            "strategy": strategy,
            "safe_zone": vision_result.get("safe_zone")
        })
        
        print(f"🧠 기획 확정: {plan.get('selected_type')} (전략: {strategy})")
        
        return {
            "plan": plan,
            "vision_result": vision_result,
            "logs": [f"Planner: {plan.get('selected_type')} 선정"]
        }

    except Exception as e:
        print(f"❌ Planner Error: {e}")
        # 에러 시 안전한 기본값 반환
        fallback_type = "TYPE_EDITORIAL_SPLIT" if strategy == "Separated" else "TYPE_FASHION_COVER"
        return {"plan": {"selected_type": fallback_type}, "logs": ["Error"]}