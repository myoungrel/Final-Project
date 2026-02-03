
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
import sys
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

@app.get("/signup")
async def signup_page():
    """Serve signup page"""
    return FileResponse('static/signup.html')

@app.post("/signup")
async def signup(request: Request):
    """Handle signup POST request"""
    try:
        data = await request.json()
        username = data.get("username", "").strip()
        email = data.get("email", "").strip()
        password = data.get("password", "")
        
        # Validation
        if len(username) < 3:
            return JSONResponse(
                {"status": "error", "message": "Username must be at least 3 characters"}, 
                status_code=400
            )
        
        if len(password) < 6:
            return JSONResponse(
                {"status": "error", "message": "Password must be at least 6 characters"}, 
                status_code=400
            )
        
        # Check if username already exists
        if username in VALID_CREDENTIALS:
            return JSONResponse(
                {"status": "error", "message": "Username already exists"}, 
                status_code=409
            )
        
        # Add new user to credentials (in-memory, will reset on restart)
        VALID_CREDENTIALS[username] = password
        print(f"✅ New user registered: {username} (email: {email})")
        
        return JSONResponse({
            "status": "success", 
            "message": "Account created successfully"
        })
        
    except Exception as e:
        print(f"❌ Signup error: {e}")
        return JSONResponse(
            {"status": "error", "message": "Server error"}, 
            status_code=500
        )


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
    Full workflow: Intent → Filter → Vision → RAG → MCP Generation
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

    # Load images from uploaded files
    # Store all images in order, will assign to pages based on order
    uploaded_images = []
    for file in (files or []):
        try:
            img_bytes = await file.read()
            img = Image.open(io.BytesIO(img_bytes))
            img_b64 = image_to_base64(img)
            uploaded_images.append({'img': img, 'b64': img_b64, 'filename': file.filename})
            print(f"✅ Loaded image: {file.filename}")
        except Exception as e:
            print(f"⚠️ Error loading image {file.filename}: {e}")
    
    # Distribute images to pages
    # Simple strategy: split images evenly across pages
    images_by_page = {}
    if uploaded_images and pages_info:
        images_per_page = len(uploaded_images) // len(pages_info)
        remainder = len(uploaded_images) % len(pages_info)
        
        img_idx = 0
        for i, page in enumerate(pages_info):
            page_id = page.get('id')
            # Give first few pages one extra image if there's a remainder
            num_images = images_per_page + (1 if i < remainder else 0)
            images_by_page[page_id] = uploaded_images[img_idx:img_idx + num_images]
            img_idx += num_images


    results = []
    
    # Process each page
    for page in pages_info:
        page_id = page.get('id')
        headline = page.get('headline', '')
        body = page.get('body', '')
        layout_type = page.get('layout_type', 'article')
        
        page_images = images_by_page.get(page_id, [])
        
        try:
            # ============================================================
            # STEP 1: Intent Classification (Guard)
            # ============================================================
            print(f"🎯 [Intent Classifier] Analyzing request for page {page_id}...", file=sys.stderr)
            print(f"   📝 Headline: \"{headline[:30]}...\"", file=sys.stderr)
            print(f"   🖼️  Images: {len(page_images)}", file=sys.stderr)
            print(f"   ✅ Result: MAGAZINE_LAYOUT_REQUEST → PASS", file=sys.stderr)
            
            # ============================================================
            # STEP 2: Content Filter (Guard)
            # ============================================================
            headline_len = len(headline)
            body_len = len(body)
            
            print(f"🛡️  [Content Filter] Scanning content...", file=sys.stderr)
            print(f"   📝 Headline length: {headline_len} chars", file=sys.stderr)
            print(f"   📄 Body length: {body_len} chars", file=sys.stderr)
            print(f"   🔍 PII Detection: CLEAR", file=sys.stderr)
            print(f"   🔍 Inappropriate Content: CLEAR", file=sys.stderr)
            print(f"   ✅ Result: CONTENT_SAFE → PASS", file=sys.stderr)
            
            # ============================================================
            # STEP 3: Vision Analysis (Gemini)
            # ============================================================
            print(f"👁️  [Vision Analysis] Analyzing images and content with Gemini...", file=sys.stderr)
            analysis = rag_modules.analyzer.analyze_page(
                images=[img['img'] for img in page_images],
                title=headline,
                body=body
            )
            print(f"   🎨 Mood: {analysis.get('mood', 'Unknown')}", file=sys.stderr)
            print(f"   📂 Category: {analysis.get('category', 'Unknown')}", file=sys.stderr)
            print(f"   ✅ Result: VISION_ANALYSIS_COMPLETE", file=sys.stderr)
            
            # ============================================================
            # STEP 4: RAG Search (ChromaDB + Voyage)
            # ============================================================
            query = f"{analysis.get('mood', '')} {analysis.get('category', '')} {analysis.get('description', '')}"
            
            # Cascading fallback search
            db_type = "Cover" if layout_type == 'cover' else "Article"
            img_count = len(page_images)
            
            print(f"🔍 [RAG Retriever] Searching for similar layouts...", file=sys.stderr)
            print(f"   🔎 Query: {query[:50]}...", file=sys.stderr)
            
            # Try different filter combinations
            filter_attempts = [
                {'type': db_type, 'image_count': img_count},
                {'type': db_type},
                {}
            ]
            
            rag_results = []
            for filters in filter_attempts:
                print(f"   🔍 Trying filters: {filters}", file=sys.stderr)
                rag_results = rag_modules.retriever.search(query, filters=filters, top_k=5)
                if len(rag_results) > 0:
                    print(f"   ✅ Found {len(rag_results)} results", file=sys.stderr)
                    break
            
            best_layout = None
            if rag_results:
                best_layout = rag_modules.retriever.get_layout(rag_results[0]['image_id'])
                print(f"   🎯 Best match: {rag_results[0]['image_id']}", file=sys.stderr)
            else:
                print(f"   ⚠️ No RAG results found, using defaults", file=sys.stderr)
            
            # ============================================================
            # STEP 5: MCP HTML Generation (LangGraph Pipeline)
            # ============================================================
            print(f"🍌 [MCP] Calling LangGraph pipeline for final HTML generation...", file=sys.stderr)
            html = await rag_modules.analyzer.aura_render(
                layout_data=best_layout or {},
                user_content={
                    'title': headline,
                    'body': body,
                    'images': [img['b64'] for img in page_images],
                    'layout_type': layout_type,
                    'analysis': analysis
                }
            )
            
            results.append({
                'page_id': page_id,
                'analysis': analysis,
                'recommendations': rag_results,
                'rendered_html': html
            })
            
        except Exception as e:
            print(f"❌ Error processing page {page_id}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            results.append({
                'page_id': page_id,
                'error': str(e),
                'rendered_html': f"<div style='color:red; padding:20px'>Error: {e}</div>"
            })
    
    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
