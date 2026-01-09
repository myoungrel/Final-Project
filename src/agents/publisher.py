from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.config import config
import os
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

def generate_single_article(a_id, article, chain):
    """
    Process a single article to generate HTML (for parallel execution).
    Uses placeholder strategy and sanitizes HTML tags.
    """
    print(f"🎨 [Parallel] Generative Coding for Article {a_id}...")
    
    manuscript = article.get("manuscript", {})
    
    # 1. Image Setup (Placeholder Strategy)
    real_image_src = article.get("image_path")
    if not real_image_src or len(real_image_src) < 10:
        mood = article.get("vision_analysis", {}).get("metadata", {}).get("mood", "abstract")
        real_image_src = f"https://source.unsplash.com/random/1600x2400/?{mood}&sig={a_id}"
    elif not real_image_src.startswith("http") and not real_image_src.startswith("data:"):
        real_image_src = f"data:image/png;base64,{real_image_src}"

    # 2. Input Data
    input_data = {
        "headline": manuscript.get("headline", "Untitled"),
        "body": manuscript.get("body", ""),
        "image_data": "(Image inserted via placeholder)", 
        "vision_json": str(article.get("vision_analysis", {})),
        "design_json": str(article.get("design_spec", {})),
        "plan_json": str(article.get("plan", {}))
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 3. LLM Generation
            html_code = chain.invoke(input_data)
            
            # 4. CRITICAL: Sanitize HTML (Remove root tags)
            # This allows multiple pages to be rendered in one file
            remove_list = [
                "```html", "```", 
                "<!DOCTYPE html>", "<!doctype html>",
                "<html>", "</html>", 
                "<body>", "</body>", 
                "<head>", "</head>"
            ]
            for tag in remove_list:
                html_code = html_code.replace(tag, "")
            
            html_code = html_code.strip()
            
            # 5. Inject Real Image
            if "{{IMAGE_PLACEHOLDER}}" in html_code:
                html_code = html_code.replace("{{IMAGE_PLACEHOLDER}}", real_image_src)
            
            return html_code
            
        except Exception as e:
            print(f"⚠️ Attempt {attempt+1}/{max_retries} failed for Article {a_id}: {e}")
            
            # Retry on temporary errors (503, 429)
            if "503" in str(e) or "overloaded" in str(e) or "429" in str(e):
                if attempt < max_retries - 1:
                    wait_time = (2 ** (attempt + 1)) + random.uniform(0, 1) 
                    time.sleep(wait_time)
                    continue
            
            # Stop on non-retriable errors
            break

    return f"<div style='color:red'>Generation Failed for Article {a_id}</div>"

def run_publisher(state):
    print("--- [Publisher] Data-Driven HTML Generation (Sanitized) ---")
    
    llm = config.get_llm()
    
    # [Modify] 1. Paginator 결과(pages)가 있으면 우선 사용
    pages = state.get("pages")
    all_articles = state.get("articles", {})
    
    target_articles = {}
    
    if pages and len(pages) > 0:
        print(f"📚 Publisher: Paginator가 생성한 {len(pages)}개 페이지를 처리합니다.")
        for page in pages:
            for art in page['articles']:
                a_id = art['id']
                # [Inheritance Check]
                # Paginator가 나눈 기사(_part2)에 디자인이 없으면 부모(원본) 디자인을 복사
                if not art.get("design_spec"):
                    parent_id = a_id.split("_part")[0]
                    parent_art = all_articles.get(parent_id)
                    if parent_art and parent_art.get("design_spec"):
                        print(f"🧬 [Inherit] {a_id}는 {parent_id}의 디자인을 상속받습니다.")
                        art["design_spec"] = parent_art.get("design_spec")
                        art["vision_analysis"] = parent_art.get("vision_analysis")
                
                target_articles[a_id] = art
    else:
        # Paginator가 없는 경우 (Fallback)
        print("📚 Publisher: 기본 Articles 모드로 실행합니다.")
        target_articles = all_articles

    final_pages = []

    # Prompt with Sanitization & Auto-fit Instructions
    prompt = ChatPromptTemplate.from_template(
        """
        You are an expert Frontend Developer specializing in high-end magazine layouts.
        
        [TASK]
        Create a stunning A4 HTML Magazine Page.
        
        [Constraints]
        1. **Size**: Strictly A4 (210mm x 297mm). Overflow hidden. Margin 0.
        2. **Styling**: Follow [Design Spec] for fonts, colors, layout. Use Tailwind CSS classes.
        3. **Image Handling**: 
           - **CRITICAL**: Do NOT write the base64 string or actual image URL.
           - Instead, for the `<img>` tag `src` attribute, write EXACTLY: `{{{{IMAGE_PLACEHOLDER}}}}`
           - Example: `<img src="{{{{IMAGE_PLACEHOLDER}}}}" class="...">`
        4. **Output Structure**: 
           - **CRITICAL**: Do NOT write `<html>`, `<body>`, `<!DOCTYPE html>`, or `<head>` tags.
           - Start directly with a wrapper `<div>` that contains your layout.
           - The wrapper should be exactly 210mm x 297mm.
        5. **Auto-Fit Typography (CRITICAL)**:
           - **Priority 1**: Fit ALL content on ONE page.
           - If text is long (> 1000 chars):
             - Use smaller fonts: `text-sm` or `text-xs`.
             - Use tighter spacing: `leading-tight`, `tracking-tight`.
             - Reduce padding/margins appropriately.

        [Data]
        - Title: {headline}
        - Body: {body}
        - Image: {image_data}
        
        - **Vision Analysis**: {vision_json}
        - **Design Spec**: {design_json}
        - **Plan**: {plan_json}
        
        [LAYOUT STRATEGY RULES - CRITICAL]
            Check the 'layout_strategy' in [Design Spec] or [Vision Analysis].
        
        👉 **CASE 1: STRATEGY = 'Separated' (or 'Split')**
           - **Structure**: Use CSS Grid or Flexbox to PHYSICALLY SEPARATE image and text.
           - **Image**: Occupy top 50% OR left 50%. (Do NOT make it full background).
           - **Text**: Place in the remaining whitespace. Background MUST be solid (white/beige/black).
           - **Overlap**: ABSOLUTELY NO text overlapping the image.
        
        👉 **CASE 2: STRATEGY = 'Overlay' (or 'Cover')**
           - **Structure**: Image is `absolute inset-0` (Full Background).
           - **Text**: Use `z-10` to place text ON TOP of the image.
           - **Contrast**: Use gradients or glass-morphism boxes behind text.
        
        Generate HTML strictly following the detected strategy:
        """
    )

    chain = prompt | llm | StrOutputParser()

    # Parallel Execution using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_id = {
            executor.submit(generate_single_article, a_id, article, chain): a_id 
            for a_id, article in target_articles.items()
        }
        
        results_map = {}
        for future in as_completed(future_to_id):
            a_id = future_to_id[future]
            try:
                html = future.result()
                results_map[a_id] = html
                print(f"✅ Article {a_id} Generated & Sanitized.")
            except Exception as e:
                print(f"❌ Critical Error in thread for Article {a_id}: {e}")
                results_map[a_id] = f"<div>Error: {e}</div>"

    # Sort pages by ID to maintain order
    sorted_ids = sorted(results_map.keys())
    for a_id in sorted_ids:
        final_pages.append(results_map[a_id])

    # Viewer Wrapper with Proper A4 Sizing
    full_html = """<!DOCTYPE html>
<html class="bg-gray-200">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Magazine</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="flex flex-col items-center py-10 space-y-10">
""" + "\n".join([f"    <div class='shadow-2xl bg-white relative w-[210mm] h-[297mm] overflow-hidden'>{page}</div>" for page in final_pages]) + """
</body>
</html>"""
    
    return {
        "html_code": full_html,
        "logs": [f"Publisher: Generated {len(final_pages)} sanitized pages"]
    }