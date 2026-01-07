# server.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse # FileResponse 추가
from fastapi.staticfiles import StaticFiles # StaticFiles 추가
from fastapi.middleware.cors import CORSMiddleware # CORS 추가
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os

# 기존 로직 import
from src.main import app_graph

app = FastAPI(title="AI Magazine Generator API")

# --- [CORS 설정: 프론트엔드 연동 필수] ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 출처 허용 (보안상 운영 시에는 특정 도메인만 허용 권장)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- [정적 파일 마운트] ---
# /static 경로로 들어오면 static 폴더의 파일을 보여줌
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- [데이터 모델 정의] ---
class ArticleRequest(BaseModel):
    id: str
    title: str
    request: str
    style: str
    is_generated: bool
    image_base64: Optional[str] = None

class MagazineRequest(BaseModel):
    articles: List[ArticleRequest]

# --- [API 엔드포인트] ---

# 1. 메인 페이지 (index.html) 반환
@app.get("/", response_class=FileResponse)
async def read_index():
    # static/index.html 파일을 읽어서 반환
    return FileResponse("static/index.html")

# 2. 생성 API (기존 로직 유지)
@app.post("/generate", response_class=HTMLResponse)
def generate_magazine(payload: MagazineRequest):
    print(f"📩 요청 수신: 기사 {len(payload.articles)}개")
    try:
        user_inputs = []
        image_data_map = {}
        for art in payload.articles:
            user_inputs.append({
                "id": art.id,
                "title": art.title,
                "request": art.request,
                "style": art.style,
                "is_generated": art.is_generated
            })
            if art.image_base64:
                b64_str = art.image_base64
                if "," in b64_str:
                    b64_str = b64_str.split(",")[1]
                image_data_map[art.id] = b64_str

        initial_state = {
            "user_input": user_inputs,
            "image_data": image_data_map,
            "logs": []
        }

        final_state = app_graph.invoke(initial_state)
        html_output = final_state.get("final_output", "")
        
        if not html_output:
            raise HTTPException(status_code=500, detail="HTML 생성 실패")

        return HTMLResponse(content=html_output)

    except Exception as e:
        print(f"❌ 서버 에러: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)