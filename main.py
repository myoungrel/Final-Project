
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
import json
from typing import List, Optional
import io
import base64
from PIL import Image
# import rag_modules
import rag_voyage as rag_modules

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load models on startup
    print("Startup: Initializing RAG Modules...")
    rag_modules.setup_rag()
    yield
    print("Shutdown: Cleaning up...")

app = FastAPI(lifespan=lifespan)

# Add session middleware (required for login)
app.add_middleware(SessionMiddleware, secret_key="aura-secret-key-change-in-production-2024")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Hardcoded credentials
VALID_CREDENTIALS = {
    'admin': 'admin123',
    'user': 'user123',
    'demo': 'demo123'
}

def image_to_base64(image: Image.Image) -> str:
    buffered = io.BytesIO()
    # Save as PNG to preserve quality/transparency
    image.save(buffered, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"

def is_authenticated(request: Request) -> bool:
    """Check if user is logged in"""
    return request.session.get("authenticated", False)

@app.get("/login")
async def login_page():
    """Serve login page"""
    return FileResponse('static/login.html')

@app.post("/login")
async def login(request: Request):
    """Handle login POST request"""
    try:
        data = await request.json()
        username = data.get("username", "").strip()
        password = data.get("password", "")
        
        # Validate credentials
        if username in VALID_CREDENTIALS and VALID_CREDENTIALS[username] == password:
            # Set session
            request.session["authenticated"] = True
            request.session["username"] = username
            print(f"✅ User '{username}' logged in successfully")
            return JSONResponse({"status": "success", "message": "Login successful"})
        else:
            print(f"❌ Failed login attempt for username: {username}")
            return JSONResponse(
                {"status": "error", "message": "Invalid credentials"}, 
                status_code=401
            )
    except Exception as e:
        print(f"❌ Login error: {e}")
        return JSONResponse(
            {"status": "error", "message": "Server error"}, 
            status_code=500
        )

@app.get("/logout")
async def logout(request: Request):
    """Handle logout"""
    username = request.session.get("username", "unknown")
    request.session.clear()
    print(f"👋 User '{username}' logged out")
    return RedirectResponse(url="/login", status_code=302)

@app.get("/")
async def read_index(request: Request):
    """Main page - requires authentication"""
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    return FileResponse('static/index.html')

@app.post("/analyze")
async def analyze_pages(
    request: Request,
    files: List[UploadFile] = File(default=None),
    pages_data: str = Form(...) 
):
    """
    Handle multi-page analysis and layout generation.
    Requires authentication.
    """
    # Check authentication
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized - Please login")
    
    try:
        pages_info = json.loads(pages_data)
        if not pages_info:
            raise HTTPException(status_code=400, detail="Pages data cannot be empty list")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in pages_data")

    # ============================================================
    # HARDCODED OVERRIDE LOGIC START
    # ============================================================
    import asyncio
    print("⏳ [Override] Sleeping for 30 seconds...")
    await asyncio.sleep(30)

    # Determine requested layout type
    # We need to load both potential files
    try:
        with open("datas/cover.html", "r", encoding="utf-8") as f:
            cover_html = f.read()
        with open("datas/article.html", "r", encoding="utf-8") as f:
            article_html = f.read()
    except Exception as e:
        print(f"❌ [Override] Error reading hardcoded files: {e}")
        return {"results": [{
            "rendered_html": f"<div style='color:red'>Error reading hardcoded files: {e}</div>"
        }]}

    results = []
    for page in pages_info:
        # Check specific layout for THIS page
        l_type = page.get('layout_type', 'cover')
        print(f"📄 Processing page {page.get('id')} -> Type: {l_type}")
        
        target_html = cover_html if l_type == 'cover' else article_html
        
        results.append({
            "page_id": page.get('id'),
            "analysis": {"mode": "HARDCODED_OVERRIDE"},
            "recommendations": [],
            "rendered_html": target_html
        })
        
    return {"results": results}
    # ============================================================
    # HARDCODED OVERRIDE LOGIC END
    # ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
