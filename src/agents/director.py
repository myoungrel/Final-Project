# src/agents/director.py
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from src.state import MagazineState
from src.config import config

def run_director(state: MagazineState) -> dict:
    print("--- [5] Art Director: Generating SDUI Design Spec (Planner & Vision Integrated) ---")
    llm = config.get_llm()
    parser = JsonOutputParser()
    
    # 1. Input Data Extraction (안전한 데이터 추출)
    
    # A. Planner Result (디자인 전략 & 타입)
    planner_data = state.get("planner_result", {})
    target_tone = planner_data.get("target_tone", "Elegant & Lyrical") # 예: Type A
    
    # B. Vision Result (색상 & 좌표)
    vision_data = state.get("vision_result", {})
    # Vision이 분석한 주조색 (없으면 기본값)
    extracted_colors = vision_data.get("dominant_colors", ["#000000", "#FFFFFF"]) 
    # Vision이 찾은 여백 좌표 (없으면 중앙 배치 가정)
    safe_areas = vision_data.get("safe_areas", "Center") 

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
            "extracted_colors": str(extracted_colors),
            "safe_areas": str(safe_areas)
        })
    except Exception as e:
        print(f"❌ Director Error: {e}")
        # Fail-Safe Default Design
        design_spec = {
            "layout_strategy": "hero_center",
            "theme": {
                "colors": {"primary": "#000000", "text_main": "#FFFFFF"},
                "fonts": {"title": "Sans-Serif", "body": "Sans-Serif"}
            },
            "layout_config": {"text_alignment": "center", "overlay_opacity": "0.5"},
            "components_style": {"headline": {"size": "text-5xl"}}
        }

    return {
        "design_spec": design_spec,
        "logs": [f"Director: Designed '{target_tone}' style with Smart Layout"]
    }