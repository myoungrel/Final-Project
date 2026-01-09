# src/agents/director.py
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from src.state import MagazineState
from src.config import config

def run_director(state: MagazineState) -> dict:
    """
    [Unified Structure Refactor]
    레이아웃 및 비주얼 분석 결과를 통합하여 최종 디자인 스펙을 생성합니다.
    state['articles'][id]['design_spec'] 에 결과를 저장합니다.
    """
    print("--- [5] Art Director: Generating SDUI Design Spec (Unified) ---")
    
    articles = state.get("articles", {})
    llm = config.get_llm()
    parser = JsonOutputParser()

    prompt = ChatPromptTemplate.from_template(
        """
        You are a World-Class Art Director & UI/UX Designer.
        Create a **JSON Design Specification (SDUI)** based on the inputs.
        
        [Input Data]
        - Layout Mode: {layout_mode}
        - Strategy Type: {target_tone}
        - Extracted Colors: {extracted_colors}
        - Safe Areas: {safe_areas}
        - Font Vibe: {font_vibe}

        [Output JSON format]
        {{
            "layout_strategy": "hero_overlay_smart",
            "theme": {{
                "mood": "{target_tone}",
                "colors": {{ "primary": "Hex", "text_main": "Hex" }},
                "fonts": {{ "title": "...", "body": "..." }}
            }},
            "layout_config": {{
                "text_alignment": "left/right/center",
                "overlay_opacity": "0.5"
            }},
            "components_style": {{
                "content_box": {{ "bg_color": "...", "padding": "..." }},
                "headline": {{ "size": "text-6xl" }}
            }}
        }}
        """
    )
    
    chain = prompt | llm | parser

    for a_id, article in articles.items():
        # [Strict Dependency Check]
        plan = article.get("plan")
        vision = article.get("vision_analysis")
        
        if not plan or not vision:
            print(f"⚠️ [Director] 기사 ID {a_id}: 필수 데이터(Planner/Vision) 누락.")
            # Fallback spec
            article["design_spec"] = {
                "layout_strategy": "Separated",
                "theme": {"mood": "Fallback"}, 
                "components_style": {}
            }
            continue

        # 데이터 매핑
        target_tone = plan.get("selected_type", "Elegant")
        layout_guide = plan.get("layout_guide", {})
        
        strategy_data = vision.get("layout_strategy", {})
        layout_mode = strategy_data.get("recommendation", "Overlay")
        metadata = vision.get("metadata", {})
        
        extracted_colors = metadata.get("dominant_colors", ["#000000"])
        safe_areas = vision.get("safe_areas", [])
        font_vibe = layout_guide.get("font_theme", "Sans-serif")

        print(f"🎨 디자인 중... ID:{a_id} | 모드:{layout_mode}")

        try:
            spec = chain.invoke({
                "layout_mode": layout_mode,
                "target_tone": target_tone,
                "extracted_colors": str(extracted_colors),
                "safe_areas": str(safe_areas),
                "font_vibe": font_vibe
            })
            
            # ✅ 결과 저장
            article["design_spec"] = spec
            
        except Exception as e:
            print(f"❌ Director Error (ID: {a_id}): {e}")
            article["design_spec"] = {"theme": {"mood": "Error"}}

    return {"articles": articles}