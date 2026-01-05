import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

class Config:
    # 1. 현재 파일(config.py)의 절대 경로를 구합니다.
    # 예: /home/sauser/ysksean/Final-Project/src/config.py
    current_file_path = os.path.abspath(__file__)
    
    # 2. 부모 폴더 (src)
    # 예: /home/sauser/ysksean/Final-Project/src
    src_dir = os.path.dirname(current_file_path)
    
    # 3. 조부모 폴더 (Final-Project) -> 여기가 프로젝트 루트!
    # 예: /home/sauser/ysksean/Final-Project
    project_root = os.path.dirname(src_dir)
    
    # 4. .env 경로 합치기
    env_path = os.path.join(project_root, '.env')

    # --- [디버깅용 출력] 실행하면 이 경로가 맞는지 눈으로 확인하세요 ---
    print(f"📍 Config가 보고 있는 프로젝트 루트: {project_root}")
    print(f"📂 .env 파일 예상 경로: {env_path}")
    
    if os.path.exists(env_path):
        print("✅ .env 파일을 찾았습니다! 로드합니다.")
        load_dotenv(dotenv_path=env_path)
    else:
        print("❌ [경고] .env 파일이 해당 경로에 없습니다. 파일명을 확인하세요!")
    # ---------------------------------------------------------

    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    MODEL_NAME = "gemini-2.5-pro"

    @staticmethod
    def get_llm():
        if not Config.GOOGLE_API_KEY:
            print("💀 [Critical] .env는 찾았는데 파일 안에 GOOGLE_API_KEY 내용이 비어있습니다!")
            
        return ChatGoogleGenerativeAI(
            model=Config.MODEL_NAME,
            google_api_key=Config.GOOGLE_API_KEY,
            temperature=0.7
        )

config = Config()