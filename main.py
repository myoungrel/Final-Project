
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

def image_to_base64(image: Image.Image) -> str:
    buffered = io.BytesIO()
    # Save as PNG to preserve quality/transparency
    image.save(buffered, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

@app.post("/analyze")
async def analyze_pages(
    files: List[UploadFile] = File(default=None),
    pages_data: str = Form(...) 
):
    """
    Handle multi-page analysis and layout generation.
    """
    try:
        pages_info = json.loads(pages_data)
        if not pages_info:
            raise HTTPException(status_code=400, detail="Pages data cannot be empty list")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in pages_data")

    # Read all images into PIL objects
    loaded_images = []
    if files:
        for file in files:
            content = await file.read()
            image = Image.open(io.BytesIO(content))
            loaded_images.append(image)

    results = []
    
    for page in pages_info:
        # Extract specific images for this page
        page_images = []
        page_images_b64 = []
        
        if 'image_indices' in page:
            for idx in page['image_indices']:
                if 0 <= idx < len(loaded_images):
                    img = loaded_images[idx]
                    page_images.append(img)
                    page_images_b64.append(image_to_base64(img))
        
        # 1. Gemini Analysis
        print(f"Analyzing Page: {page.get('id')} - {page.get('title', 'Untitled')}")
        try:
            analysis = rag_modules.analyzer.analyze_page(
                page_images, 
                page.get('title', ''), 
                page.get('body', '')
            )
        except Exception as e:
            print(f"Analysis Error: {e}")
            analysis = {"mood": "General", "category": "General", "type": "Balanced", "description": "Error in analysis"}

        # 2. Formulate Hybrid Search Query
        visual_tags = " ".join(analysis.get('visual_keywords', []))
        query_parts = [
            analysis.get('mood', ''),
            visual_tags, # Add visual keywords to query
            analysis.get('category', ''),
            analysis.get('type', ''),
            analysis.get('description', '')
        ]
        query = " ".join([p for p in query_parts if p])
        
        # 3. Retrieve Layouts (with Structural Filtering + Fallback)
        layout_type = page.get('layout_type', 'cover')
        db_type = 'Cover' if layout_type == 'cover' else 'Article'
        print(f"📌 Layout Type: {layout_type} -> DB filter: {db_type}")
        
        # Build filters
        full_filters = {'type': db_type}
        if page_images:
            full_filters['image_count'] = len(page_images)
            w, h = page_images[0].size
            if w > h * 1.1:
                full_filters['layout_ratio'] = "Horizontal"
            elif h > w * 1.1:
                full_filters['layout_ratio'] = "Vertical"
            else:
                full_filters['layout_ratio'] = "Square"
        
        # Try with all filters first, then fallback progressively
        recommendations = []
        filter_attempts = [
            full_filters,                          # 1st: All filters
            {'type': db_type, 'image_count': full_filters.get('image_count', 1)},  # 2nd: type + image_count
            {'type': db_type},                     # 3rd: type only
            {}                                     # 4th: no filters (last resort)
        ]
        
        for attempt_filters in filter_attempts:
            try:
                print(f"Trying filters: {attempt_filters}")
                recommendations = rag_modules.retriever.search(query, filters=attempt_filters, top_k=3)
                if recommendations:
                    print(f"✅ Found {len(recommendations)} layouts with filters: {attempt_filters}")
                    break
            except Exception as e:
                print(f"Retrieval Error: {e}")
                continue
        
        # 4. Render HTML for Top 1 Layout
        rendered_html = ""
        
        if not recommendations:
             print(f"⚠️ [Main] No recommendations found for page {page.get('id')}")
             rendered_html = "<div class='flex items-center justify-center h-full text-gray-500'>No matching layouts found. Try different content.</div>"
        
        if recommendations:
            top_rec = recommendations[0]
            try:
                # Retrieve raw layout data using the newly added get_layout method
                layout_data = rag_modules.retriever.get_layout(top_rec['image_id'])
                
                if layout_data:
                    user_content_for_render = {
                        "title": page.get('title', ''),
                        "body": page.get('body', ''),
                        "images": page_images_b64,
                        "analysis": analysis,
                        "layout_type": layout_type  # Pass cover/article to MCP
                    }
                    # Use AURA MCP for superior layout generation
                    rendered_html = await rag_modules.analyzer.aura_render(layout_data, user_content_for_render)
                    
                    if not rendered_html:
                         # No fallback - log error
                         print("⚠️ [Main] AURA returned empty HTML")
                         rendered_html = "<div style='padding:20px;color:red;'>Layout generation failed. Please try again.</div>"
            except Exception as e:
                print(f"Rendering Error: {e}")
                rendered_html = "<!-- Error generated HTML -->"

        results.append({
            "page_id": page.get('id'),
            "analysis": analysis,
            "recommendations": recommendations,
            "rendered_html": rendered_html
        })

    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
