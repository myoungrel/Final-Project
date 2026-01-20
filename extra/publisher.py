import time
import random
import asyncio 
import json
from concurrent.futures import ThreadPoolExecutor
from tool.mcp_client import mcp_client

def generate_single_article(a_id, article):
    print(f"🍌 [NanoBanana] Outsourcing Article {a_id}...")
    
    manuscript = article.get("manuscript", {})
    headline = manuscript.get("headline", "Untitled")
    body = manuscript.get("body", "")
    
    # [Multi-Image Logic]
    # 실제 이미지 경로가 리스트인지 확인
    real_image_src = article.get("image_path")
    placeholder_list = []
    
    if isinstance(real_image_src, list):
        # 다수 이미지
        for i, src in enumerate(real_image_src):
            placeholder_list.append(f"{{{{IMAGE_PLACEHOLDER_{i}}}}}")
    else:
        # 단일 이미지 (혹은 없음)
        placeholder_list.append("{{IMAGE_PLACEHOLDER_0}}")
        if not real_image_src:
             real_image_src = "https://source.unsplash.com/random/1600x2400/?fashion"

    # Context Serialization
    vision_json = str(article.get("vision_analysis", {}))
    design_json = str(article.get("design_spec", {}))
    plan_json = str(article.get("plan", {}))
    layout_override = article.get("layout_override", "None")

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # MCP Call (리스트 전달)
            html_code = asyncio.run(
                mcp_client.generate_layout(
                    headline=headline,
                    body=body,
                    image_data=placeholder_list, # 리스트를 넘김
                    layout_override=layout_override,
                    vision_json=vision_json,
                    design_json=design_json,
                    plan_json=plan_json
                )
            )
            
            html_code = html_code.replace("```html", "").replace("```", "")
            
            # [Multi-Image Injection]
            if isinstance(real_image_src, list):
                for i, src in enumerate(real_image_src):
                    target = f"{{{{IMAGE_PLACEHOLDER_{i}}}}}"
                    if target in html_code:
                        # Base64 처리 필요 시 여기서 수행
                        final_src = src if src.startswith("data:") or src.startswith("http") else f"data:image/png;base64,{src}"
                        html_code = html_code.replace(target, final_src)
            else:
                # 단일 이미지
                target = "{{IMAGE_PLACEHOLDER_0}}"
                if target in html_code:
                     final_src = real_image_src if real_image_src.startswith("data:") or real_image_src.startswith("http") else f"data:image/png;base64,{real_image_src}"
                     html_code = html_code.replace(target, final_src)
            
            return html_code
            
        except Exception as e:
            print(f"⚠️ [NanoBanana] Attempt {attempt+1} failed: {e}")
            time.sleep(1)
            
    return f"<div>Generation Failed: {a_id}</div>"

def run_publisher(state):
    print("--- [Publisher] Orchestrating Multi-Image Generation ---")
    
    pages = state.get("pages")
    all_articles = state.get("articles", {})
    target_articles = {}
    
    if pages:
        for page in pages:
            for art in page['articles']:
                a_id = art['id']
                if not art.get("design_spec"):
                    parent_id = a_id.split("_part")[0]
                    parent_art = all_articles.get(parent_id)
                    if parent_art:
                        art["design_spec"] = parent_art.get("design_spec")
                        art["vision_analysis"] = parent_art.get("vision_analysis")
                        art["plan"] = parent_art.get("plan")
                target_articles[a_id] = art
    else:
        target_articles = all_articles

    final_pages = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_id = {
            executor.submit(generate_single_article, a_id, article): a_id 
            for a_id, article in target_articles.items()
        }
        
        results_map = {}
        # Wait for completion
        for future in future_to_id:
             pass # just wait or check results below

    for future, a_id in future_to_id.items():
        try:
            html = future.result()
            results_map[a_id] = html
        except Exception as e:
            results_map[a_id] = f"Error: {e}"

    sorted_ids = sorted(results_map.keys())
    for a_id in sorted_ids:
        final_pages.append(results_map[a_id])

    full_html = """<!DOCTYPE html>
<html class="bg-gray-200">
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Lato:wght@300;400;700&display=swap');</style>
</head>
<body class="flex flex-col items-center py-10 space-y-10">
""" + "\n".join([f"    <div class='shadow-2xl bg-white relative w-[210mm] h-[297mm] overflow-hidden' id='page-{i}'>{page}</div>" for i, page in enumerate(final_pages)]) + """
</body>
</html>"""
    
    return {"html_code": full_html, "logs": []}