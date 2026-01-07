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
        - **Layout Mode**: {layout_mode} (FIXED)
        - **Design Strategy (Type)**: {target_tone}
        - **Extracted Colors (from Image)**: {extracted_colors}
        - **Safe Text Areas (from Image)**: {safe_areas}
        - Planner's Color Idea: {color_suggestion}
        - Planner's Font Idea: {font_vibe}

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

    # ------------------------------------------------------------------
    # 2. 실행 분기 (Strict Type Check)
    # ------------------------------------------------------------------
    user_input = state.get("user_input")

    # [Case A] 다중 입력 (List) -> 반복문 실행
    if isinstance(user_input, list):
        print(f"🔄 다중 처리 모드 감지: {len(user_input)}건 처리 시작")
        design_specs = {}
        
        # 다중 모드일 때는 plan과 vision_result가 ID를 키로 하는 Dict여야 함
        plans = state.get("planner_result", {})
        vision_results = state.get("vision_result", {})

        for item in user_input:
            a_id = str(item.get("id"))
            
            # 해당 ID의 데이터 로드
            plan_details = plans.get(a_id, {})
            vis_data = vision_results.get(a_id, {})
            metadata = vis_data.get("metadata", {})
            
            # --- 변수 매핑 (기존 Director 변수명 준수) ---
            target_tone = plan_details.get("selected_type", "Elegant Style")
            layout_mode = plan_details.get("layout_mode", "Overlay")
            
            # Planner의 layout_guide -> Director 변수
            layout_guide = plan_details.get("layout_guide", {})
            bg_color = layout_guide.get("background_color")
            color_suggestion = f"Match with {bg_color}" if bg_color else "Contrast"
            font_vibe = layout_guide.get("font_theme", "Clean Sans-serif")
            
            # Vision Data
            extracted_colors = (
                metadata.get("dominant_colors") 
                or vis_data.get("dominant_colors") 
                or ["#000000", "#FFFFFF"]
            )
            safe_areas = metadata.get("dominant_position") or vis_data.get("safe_areas") or "Center"

            print(f"🎨 [ID:{a_id}] Designing... Tone:{target_tone} | Mode:{layout_mode}")

            try:
                spec = chain.invoke({
                    "layout_mode": layout_mode,
                    "target_tone": target_tone,
                    "color_suggestion": color_suggestion,
                    "font_vibe": font_vibe,
                    "extracted_colors": str(extracted_colors),
                    "safe_areas": safe_areas
                })
                design_specs[a_id] = spec
            except Exception as e:
                print(f"❌ Error [ID:{a_id}]: {e}")
                design_specs[a_id] = {
                    "layout_strategy": str(layout_mode),
                    "theme": {"mood": "Error Fallback"}
                }

        return {
            "design_spec": design_specs, 
            "logs": [f"Director: Batch generated {len(design_specs)} specs"]
        }

    # [Case B] 단일 입력 (Dict) -> 단일 실행
    else:
        print("👤 단일 처리 모드 감지")
        
        # 단일 모드용 데이터 로드
        plan_details = state.get("planner_result", {})
        vision_data = state.get("vision_result", {})
        
        # --- 변수 매핑 (기존 Director 변수명 준수) ---
        target_tone = plan_details.get("selected_type", "Elegant Style")
        layout_mode = plan_details.get("layout_mode", "Overlay")
        
        layout_guide = plan_details.get("layout_guide", {})
        bg_color = layout_guide.get("background_color")
        color_suggestion = f"Match with {bg_color}" if bg_color else "Contrast"
        font_vibe = layout_guide.get("font_theme", "Clean Sans-serif")
        
        extracted_colors = (
            vision_data.get("dominant_colors")
            or vision_data.get("metadata", {}).get("dominant_colors")
            or ["#000000", "#FFFFFF"]
        )
        safe_areas = vision_data.get("safe_areas") or vision_data.get("space_analysis") or "Center"

        try:
            design_spec = chain.invoke({
                "layout_mode": layout_mode,
                "target_tone": target_tone,
                "color_suggestion": color_suggestion,
                "font_vibe": font_vibe,
                "extracted_colors": str(extracted_colors),
                "safe_areas": safe_areas
            })
            
            # 안전장치
            design_spec['is_overlay'] = (str(layout_mode).lower() == 'overlay')

        except Exception as e:
            print(f"❌ Director Error: {e}")
            design_spec = {
                "layout_strategy": str(layout_mode),
                "theme": {"mood": "Error Fallback"}
            }

        return {
            "design_spec": design_spec,
            "logs": [f"Director: Spec generated for {layout_mode}"]
        }