import json
import os
import base64  # [추가]
import io      # [추가]
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv

# 1. 환경 변수 및 경로 설정
current_file_path = os.path.abspath(__file__)
tests_dir = os.path.dirname(current_file_path)
# .env 파일 위치는 프로젝트 구조에 맞게 조정하세요 (예: 상위 폴더 등)
env_path = os.path.join(tests_dir, "..", "..", ".env") 
load_dotenv(dotenv_path=env_path)

# 2. API 키 설정
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ [Vision] 에러: GOOGLE_API_KEY를 찾을 수 없습니다. .env 파일을 확인하세요.")
else:
    genai.configure(api_key=api_key)

def run_vision(state):
    print("--- [Vision Agent] 이미지 정밀 분석 시작 (Gemini) ---")
    
    # [New Code] 다중 이미지 처리 로직
    image_map = state.get("image_data", {}) # Dict[id, base64]
    user_inputs = state.get("user_input", []) # List[Dict]

    vision_results = {} # 결과를 담을 Dict {id: result}

    # 모델 설정 (Gemini 1.5 Flash 권장, 없으면 Pro 사용)
    # user_text에 언급된 2.5 모델은 아직 정식 사용이 어려울 수 있어 1.5로 설정합니다.
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
    except:
        model = genai.GenerativeModel('gemini-2.5-flash')

    # 이미지가 없으면 빈 결과 반환
    if not image_map:
        print("⚠️ 분석할 이미지가 없습니다.")
        return {"vision_result": {}}

    # 각 이미지 별로 반복 분석
    for article_id, b64_data in image_map.items():
        print(f"📸 이미지 분석 중... (ID: {article_id})")
        
        # 해당 ID에 맞는 사용자 텍스트 찾기 (프롬프트 반영용)
        # user_inputs 리스트에서 id가 일치하는 항목 찾기
        relevant_text = ""

        for item in user_inputs:
            if str(item.get("id")) == str(article_id):
                # request가 있으면 쓰고 없으면 title이라도 사용
                relevant_text = item.get("request") or item.get("title", "")
                break

        # 👇 [수정됨] 요청하신 프롬프트를 영어로 번역하여 적용했습니다.
        prompt = f"""
            You are the 'Chief Art Director'. 
            Request: "{relevant_text}"

            **[TASK: Step-by-Step Layout Decision]**
            Follow this exact order of thinking to decide "Overlay" vs "Separated".

            **STEP 1: Identify the 'HERO SUBJECT' (The Star)**
            - Find the Main Subject (Person, Watch, Bag).
            - **IGNORE** the background cleanliness for a moment. Focus ONLY on the Hero.

            **STEP 2: Analyze Hero's Dominance (The FATAL Check)**
            - **Is it a Person?** If yes, does the person occupy the **Center** of the image? -> If YES, STOP. Choose **'SEPARATED'**. (Never overlay text on a central portrait).
            - **Is it a Product?** Is it a "Macro Shot" (zoomed in extremely close)? -> If YES, STOP. Choose **'SEPARATED'**.
            - **Size Check:** Does the Hero Subject take up more than 50% of the image width/height? -> If YES, mostly **'SEPARATED'**.

            **STEP 3: Evaluate Background/Props (Only if Step 2 didn't stop you)**
            - Now look at the background.
            - **Case A (Prop as Canvas):** Is the Hero small, sitting on a huge uniform object (like a watch on a big white shell)? -> Choose **'OVERLAY'**.
            - **Case B (Clean Space):** Is the Hero off-center (Left/Right), leaving a huge empty sky/wall? -> Choose **'OVERLAY'**.

            **[Decision Logic Summary]**
            1. **Portrait/Central Human** = **SEPARATED** (Priority 1)
            2. **Zoomed-in Product** = **SEPARATED** (Priority 2)
            3. **Small Hero + Big Uniform Prop** = **OVERLAY** (Priority 3)
            4. **Small Hero + Clean Sky/Wall** = **OVERLAY** (Priority 4)

            **[JSON Data Structure]**
            1. thought_process: [Step-by-step reasoning based on the tasks above]
            2. layout_strategy:
                - recommendation: "Overlay" or "Separated"
                - reason: "Detailed reason for the choice"
            3. metadata: 
                - mood: "Visual mood keywords"
                - dominant_colors: ["#Hex1", "#Hex2", "#Hex3"]
                - lighting: "Lighting description"
                - dominant_position: "Left", "Right", or "Center"
                - design_guide: {{ "text_contrast": "Dark/Light", "font_recommendation": "Serif/Sans-serif" }}
                - composition_analysis: {{ "visual_weight": "...", "gaze_direction": "..." }}
                - texture_context: {{ "dominant_texture": "...", "seasonal_vibe": "..." }}
            4. safe_areas: [[ymin, xmin, ymax, xmax], ...] (Return [] if 'Separated')

            RETURN ONLY RAW JSON. NO MARKDOWN.

            **[JSON Response Example]**
            {{
                "thought_process": [
                    "Step 1: Hero is 'Watch'.",
                    "Step 2: Watch is on the right side, not central. Not a macro shot.",
                    "Step 3: Background is a large white seashell on the left.",
                    "Step 4: The seashell provides a clean, uniform 'canvas' for text.",
                    "Step 5: Decision 'Overlay' to utilize the negative space on the seashell."
                ],
                "layout_strategy": {{
                    "recommendation": "Overlay",
                    "reason": "The subject is off-center, and the uniform texture of the prop on the left provides an ideal surface for text overlay."
                }},
                "metadata": {{
                    "mood": "Oceanic, Luxury",
                    "dominant_colors": ["#F5F5F5", "#003366", "#111111"],
                    "lighting": "Soft studio light",
                    "dominant_position": "Right",
                    "design_guide": {{
                        "text_contrast": "Dark",
                        "font_recommendation": "Sans-serif"
                    }},
                    "composition_analysis": {{
                        "visual_weight": "Right-heavy (Watch)",
                        "gaze_direction": "Left"
                    }},
                    "texture_context": {{
                        "dominant_texture": "Smooth Shell Surface",
                        "seasonal_vibe": "Summer"
                    }}
                }},
                "safe_areas": [[100, 50, 800, 500]]
            }}

            RETURN ONLY RAW JSON. DO NOT USE MARKDOWN.
            """
        
        try:
            # [New Code]
            image_bytes = base64.b64decode(b64_data)
            # 2. Bytes를 메모리 파일(IO)로 변환 후 PIL로 열기
            img = Image.open(io.BytesIO(image_bytes))
            
            # 3. Gemini에게 전송
            response = model.generate_content([prompt, img])
            
            # JSON 정제
            json_res = response.text.replace("```json", "").replace("```", "").strip()

            # [New Code]
            vision_results[article_id] = json.loads(json_res)

        except Exception as e:
            print(f"❌ Vision Error (ID: {article_id}): {e}")
            # 실패 시 기본값 저장
            vision_results[article_id] = {
                "layout_strategy": {"recommendation": "Separated"},
                "metadata": {"mood": "General"},
                "safe_areas": [],
                "dominant_colors": ["#FFFFFF", "#000000"]
            }

    return {"vision_result": vision_results}