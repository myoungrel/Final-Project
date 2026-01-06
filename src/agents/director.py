# src/agents/director.py
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from src.state import MagazineState
from src.config import config

def run_director(state: MagazineState) -> dict:
    print("--- [5] Art Director: Generating SDUI Design Spec ---")
    llm = config.get_llm()
    parser = JsonOutputParser()
    
    # 1. Input Data Extraction
    planner_data = state.get("planner_result", {}) or {}
    plan_details = planner_data.get("plan") if isinstance(planner_data, dict) else None
    plan_details = plan_details if isinstance(plan_details, dict) else planner_data

    # [중요] Planner가 결정한 큰 틀 가져오기
    # plan 딕셔너리 구조에 따라 접근 경로 주의 (planner_data['plan']['layout_mode'] 일 수도 있음)    
    target_tone = plan_details.get("selected_type", "Elegant Style")
    layout_mode = plan_details.get("layout_mode", "Overlay") # "Overlay" or "Separated"
    
    vision_data = state.get("vision_result", {})
    
    # Vision Data
    extracted_colors = (
        vision_data.get("dominant_colors")
        or vision_data.get("metadata", {}).get("hex_colors")
        or ["#000000", "#FFFFFF"]
        )
    safe_areas = vision_data.get("safe_areas") or vision_data.get("space_analysis") or "Center"

    # ------------------------------------------------------------------
    # [프롬프트 설계 의도]
    # 1. Type-Based Few-Shot: Planner의 Tone(A~H)에 따라 다른 폰트/레이아웃 규칙 적용.
    # 2. Dynamic Styling: Vision이 추출한 Hex Code를 Primary/Secondary 컬러로 배정.
    # 3. Smart Layout: Vision의 'Safe Area' 좌표를 보고 텍스트 정렬(Left/Right) 결정.
    # 4. SDUI Generation: 단순히 'Hero'라고 하는 게 아니라, margin, padding, font-family 등 구체적 Spec 생성.
    # ------------------------------------------------------------------

    prompt = ChatPromptTemplate.from_template(
        """
        You are a World-Class Art Director & UI/UX Designer.
        Your task is to create a **JSON Design Specification (SDUI Blueprint)** based on the Strategy and Visual Analysis.
        
        [Input Data]
        - **Layout Mode**: {layout_mode}
        - **Design Strategy (Type)**: {target_tone}
        - **Extracted Colors (from Image)**: {extracted_colors}
        - **Safe Text Areas (from Image)**: {safe_areas}
        
        [Design Rules by Type (Few-Shot Logic)]
        Apply the following rules strictly based on the [Design Strategy]:
        
        - **Type A (Elegant)**: Serif fonts (Playfair Display), High contrast, Minimalist, Overlay opacity 0.3.
        - **Type B (Bold)**: Sans-Serif fonts (Oswald), Neon/Vivid accent colors, Italic headlines, Overlay opacity 0.5.
        - **Type C (Analytical)**: Clean Sans-Serif (Roboto), Grid layout, Blue/Grey tones, High legibility.
        - **Type D (Friendly)**: Rounded Sans (Nunito), Warm pastel tones, Card layout.
        - **Type E (Witty)**: Retro Serif (Merriweather), Brutalist layout, Stark borders.
        - **Type F (Dramatic)**: Cinematic Serif (Cinzel), Dark mode, High fade gradients.
        - **Type G (Minimalist)**: Modern Sans (Inter), Huge whitespace, Small typography.
        - **Type H (Nostalgic)**: Retro font (Courier Prime), Sepia/Grainy filters, Polaroid style.

        [Directives]
        1. **Smart Layout**: Analyze the [Safe Text Areas].
           - If safe area is on the **Left**, set text alignment to 'left' and position to 'absolute-left'.
           - If safe area is on the **Right**, set text alignment to 'right' and position to 'absolute-right'.
           - If unsure, default to 'center'.
           
        2. **Dynamic Styling**: 
           - Pick the most vibrant color from [Extracted Colors] as the 'Accent Color'.
           - Pick a contrasting color (White/Black) for text based on background brightness.

        3. **SDUI Structure**:
           - Define 'container_style' (Background, Overlay).
           - Define 'typography' (Font Family, Size, Weight).
           - **NEW**: Define 'content_box' style.
             - To ensure readability, text MUST be inside a box.
             - Typical style: "bg-white bg-opacity-90 p-8 shadow-lg" (for Elegant/Clean)
             - Or: "bg-black bg-opacity-80 p-8 border border-white" (for Dark/Bold)
           - Define 'components' (Headline, Subhead, Body).

        Output JSON format ONLY (No markdown):
        {{
            "layout_strategy": "hero_overlay_smart",
            "theme": {{
                "mood": "{target_tone}",
                "colors": {{
                    "primary": "Hex from input",
                    "secondary": "Hex from input",
                    "text_main": "#FFFFFF or #000000",
                    "text_sub": "Hex with opacity"
                }},
                "fonts": {{
                    "title": "Font Name, serif",
                    "body": "Font Name, sans-serif"
                }}
            }},
            "layout_config": {{
                "text_alignment": "left" or "right" or "center",
                "text_position_x": "justify-start" or "justify-end" or "justify-center",
                "overlay_opacity": "0.1 to 0.9"
            }},
            "components_style": {{
                "content_box": {{
                    "bg_color": "bg-white/90 or bg-black/80", 
                    "padding": "p-8 md:p-12",
                    "border_radius": "rounded-none or rounded-xl",
                    "shadow": "shadow-2xl",
                    "backdrop_blur": "backdrop-blur-sm"
                }},
                "headline": {{ "size": "text-6xl", "weight": "font-bold", "letter_spacing": "tracking-tight" }},
                "subhead": {{ "size": "text-xl", "weight": "font-medium", "transform": "uppercase" }},
                "body": {{ "size": "text-base", "leading": "leading-relaxed" }},
                "caption": {{ "size": "text-xs", "style": "italic", "color": "text-gray-400" }}
            }}
        }}
        """
    )
    
    chain = prompt | llm | parser
        
    try:
        design_spec = chain.invoke({
            "target_tone": target_tone,
            "layout_mode": layout_mode,
            "extracted_colors": str(extracted_colors),
            "safe_areas": str(safe_areas)
        })
        
        # [안전장치] LLM이 실수할 수 있으니 강제로 동기화
        design_spec['is_overlay'] = (layout_mode.lower() == 'overlay')

    except Exception as e:
        print(f"❌ Director Error: {e}")
        # Fail-Safe
        is_overlay = (layout_mode.lower() == 'overlay')
        design_spec = {
            "is_overlay": is_overlay,
            "layout_config": {"container_bg": "#FFFFFF", "text_alignment": "center"},
            "theme": {"primary_color": "#000000"}
        }

    print(f"🎨 디자인 스펙 생성 완료 (Mode: {layout_mode})")
    
    return {
        "design_spec": design_spec,
        "logs": [f"Director: Spec generated for {layout_mode}"]
    }