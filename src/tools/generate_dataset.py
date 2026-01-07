# src/tools/generate_dataset.py
import os
import json
import base64
import io
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv

# 1. 환경 설정 (API 키 로드)
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

# 2. 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__))) # Final-Project/
RAW_IMG_DIR = os.path.join(BASE_DIR, "dataset", "raw_images") # 스크린샷 넣어둘 곳
OUTPUT_FILE = os.path.join(BASE_DIR, "dataset", "training_data.json") # 결과 저장 파일

# 폴더 없으면 생성
os.makedirs(RAW_IMG_DIR, exist_ok=True)

def analyze_layout_with_gemini(image_path, filename):
    """
    Gemini에게 잡지 스크린샷을 주고 좌표를 따오라고 시키는 함수
    """
    model = genai.GenerativeModel('gemini-2.5-flash') 

    # [핵심] T5 학습 데이터 생성을 위한 특수 프롬프트
    prompt = """
    Analyze this magazine layout image and extract the bounding box coordinates for each element.
    The coordinates must be on a scale of 0 to 100 (percentage).

    **[Elements to Detect]**
    1. Hero Image (The main visual)
    2. Headline (The biggest text)
    3. Body Text (The main content block)

    **[Context Extraction]**
    1. Category: Classify the content into ONE of these: [Politics, Science, Beauty, Fashion, Society, Tech, Culture].
    2. Mood: Analyze the visual vibe (e.g., Serious, Modern, Elegant, Energetic, Minimalist).
    3. Subject Position: Where is the main subject located? Choose the MOST ACCURATE one:
       - Top_Left,    Top_Center,    Top_Right
       - Middle_Left, Center,        Middle_Right
       - Bottom_Left, Bottom_Center, Bottom_Right
       - Full_Page (if the subject fills the entire background)

    **[JSON Output Format]**
    {
        "category": "String",
        "mood": "String",
        "pos": "String",
        "layout": {
            "image": {"x": int, "y": int, "w": int, "h": int},
            "title": {"x": int, "y": int, "w": int, "h": int},
            "body":  {"x": int, "y": int, "w": int, "h": int}
        }
    }
    
    RETURN ONLY RAW JSON. NO MARKDOWN.
    """

    try:
        img = Image.open(image_path)
        response = model.generate_content([prompt, img])
        
        # JSON 파싱
        json_str = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(json_str)
        
        # 파일명 정보 추가 (디버깅용)
        data["source_image"] = filename
        return data

    except Exception as e:
        print(f"❌ Error analyzing {filename}: {e}")
        return None

def main():
    print(f"📂 '{RAW_IMG_DIR}' 폴더의 이미지를 분석합니다...")
    
    # 이미 분석된 데이터가 있으면 로드 (이어하기 기능)
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            dataset = json.load(f)
    else:
        dataset = []

    # 이미지 파일 스캔
    files = [f for f in os.listdir(RAW_IMG_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    print(f"🔍 총 {len(files)}장의 이미지 발견.")

    for i, filename in enumerate(files):
        # 중복 방지 (이미 한 건 패스)
        if any(d.get("source_image") == filename for d in dataset):
            print(f"⏭️ [Skip] {filename} (이미 분석됨)")
            continue

        print(f"[{i+1}/{len(files)}] 📸 분석 중: {filename}...")
        file_path = os.path.join(RAW_IMG_DIR, filename)
        
        result = analyze_layout_with_gemini(file_path, filename)
        
        if result:
            dataset.append(result)
            # 중간중간 저장 (혹시 꺼질까봐)
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(dataset, f, indent=4, ensure_ascii=False)
            print("  ✅ 저장 완료")

    print(f"\n🎉 모든 작업 완료! 총 {len(dataset)}개의 학습 데이터가 생성되었습니다.")
    print(f"파일 위치: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()