# 파일 위치: src/agents/planner.py

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from src.state import MagazineState
from src.config import config

# 🚀 Vision 데이터 시뮬레이터 (Vision 개발 전까지 사용)
def simulate_vision_data(user_script: dict) -> dict:
    llm = config.get_llm()
    parser = JsonOutputParser()
    
    simulation_prompt = ChatPromptTemplate.from_template(
        """
        You are a 'Virtual Vision Simulator'.
        Infer the likely visual elements based on the article content.

        [Article Context]
        - Title: {title}
        - Body: {body_snippet}...

        Return JSON:
        {{
            "main_item": "String",
            "img_mood": "String",
            "colors": ["#Hex1", "#Hex2", "#Hex3"],
            "safe_zone": "String (one of: top, bottom, left, right, center)",
            "shot_type": "String"
        }}
        """
    )
    
    body_text = user_script.get("body", "")[:500]
    chain = simulation_prompt | llm | parser
    
    try:
        print(f"🔮 Vision 데이터 시뮬레이션 중... (주제: {user_script.get('title')})")
        return chain.invoke({
            "title": user_script.get("title", "No Title"),
            "body_snippet": body_text
        })
    except Exception as e:
        print(f"Simulator Error: {e}")
        return {
            "main_item": "Unknown", "img_mood": "Neutral", 
            "colors": ["#000000", "#FFFFFF", "#808080"], 
            "safe_zone": "center", "shot_type": "Product"
        }

# 🚀 Planner 메인 함수 (이게 꼭 있어야 합니다!)
def run_planner(state: MagazineState) -> dict:
    print("--- [Planner] 매거진 컨셉 기획 중... ---")
    
    user_script = state["user_script"]
    
    if state.get("vision_result"):
        vision_result = state["vision_result"]
        print("✅ 실제 Vision 데이터를 사용합니다.")
    else:
        vision_result = simulate_vision_data(user_script)
        
    llm = config.get_llm()
    parser = JsonOutputParser()

    prompt = ChatPromptTemplate.from_template(
        """
        You are the Editor-in-Chief. Determine the Concept.
        
        [INPUTS]
        - Title: {title}
        - Mood: {img_mood}
        - Item: {main_item}

        Return JSON:
        {{
            "selected_type": "TYPE_B_...",
            "concept_rationale": "Reason...",
            "layout_guide": {{ "text_position": "{safe_zone}", "font_theme": "String" }},
            "editor_guide": {{ "tone": "String", "emphasis": "String" }}
        }}
        """
    )

    chain = prompt | llm | parser

    try:
        plan = chain.invoke({
            "title": user_script.get("title"),
            "img_mood": vision_result.get("img_mood"),
            "main_item": vision_result.get("main_item"),
            "safe_zone": vision_result.get("safe_zone", "center")
        })
        
        print(f"🧠 기획 확정: {plan.get('selected_type')}")
        
        return {
            "plan": plan,
            "vision_result": vision_result,
            "logs": [f"Planner: {plan.get('selected_type')} 컨셉 확정"]
        }

    except Exception as e:
        print(f"❌ Planner Error: {e}")
        return {"plan": {"selected_type": "TYPE_B_1"}, "logs": ["Error"]}