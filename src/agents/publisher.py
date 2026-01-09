from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.config import config
import os
import time
import random

def run_publisher(state):
    print("--- [Publisher] Generative HTML Coding Start ---")
    
    llm = config.get_llm()
    articles = state.get("articles", {})
    final_pages = []

    # 1. Define the HTML Generation Prompt
    # A4 Size: 210mm x 297mm
    prompt = ChatPromptTemplate.from_template(
        """
        You are an expert Frontend Developer specializing in high-end magazine layouts.
        
        [TASK]
        Write the full HTML/CSS code for a single magazine page (A4 size).
        Use **Tailwind CSS** (via CDN).
        
        [Constraints]
        1. **Size**: Strictly A4 (width: 210mm, height: 297mm). Overflow hidden. 
           - Set body/html to margin 0, padding 0.
           - Wrapper div should be strictly 210mm x 297mm.
        2. **Styling**: Use the provided [Design Spec] for fonts, colors, and layout.
        3. **Content**: Use the [Manuscript] for texts.
        4. **Image**: Use the provided [Image Data] (Base64). Ensure it fits the [Vision Strategy].
        5. **Output**: Return ONLY the raw HTML code. Do not use Markdown blocks (```html).
        6. **CDN**: Include <script src="https://cdn.tailwindcss.com"></script> at the top.

        [Data]
        - Title: {headline}
        - Body: {body}
        - Image Base64: {image_data} (If None/Empty, use a placeholder color or gradient)
        
        - **Vision Analysis**: {vision_json}
        - **Design Spec**: {design_json}
        - **Plan**: {plan_json}
        
        [Design Directive]
        - If strategy is 'Overlay', place text over the image with proper contrast (gradients/boxes).
        - If strategy is 'Separated', create a multi-column layout or grid.
        - Use the specific fonts and colors defined in [Design Spec].
        
        Generate the HTML now:
        """
    )

    # Output Parser returns string
    chain = prompt | llm | StrOutputParser()

    # 2. Iterate and Generate with Retry
    for a_id, article in articles.items():
        print(f"🎨 Coding HTML for Article {a_id}...")
        
        manuscript = article.get("manuscript", {})
        
        # NOTE: ArticleState uses 'image_path' for the image data/path
        image_val = article.get("image_path") or ""
        
        input_data = {
            "headline": manuscript.get("headline", "Untitled"),
            "body": manuscript.get("body", ""),
            "image_data": image_val,
            "vision_json": str(article.get("vision_analysis", {})),
            "design_json": str(article.get("design_spec", {})),
            "plan_json": str(article.get("plan", {}))
        }

        html_code = ""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Invoke LLM
                html_code = chain.invoke(input_data)
                
                # Success! Break the retry loop
                html_code = html_code.replace("```html", "").replace("```", "")
                break 
                
            except Exception as e:
                print(f"⚠️ Attempt {attempt+1}/{max_retries} failed for Article {a_id}: {e}")
                
                # Check if it's a 503 or overload error or 429
                if "503" in str(e) or "overloaded" in str(e) or "429" in str(e):
                    if attempt < max_retries - 1:
                        # Exponential backoff + jitter
                        # 0: 2s, 1: 4s, 2: stop
                        wait_time = (2 ** (attempt + 1)) + random.uniform(0, 1) 
                        print(f"⏳ Waiting {wait_time:.1f}s before retrying...")
                        time.sleep(wait_time)
                        continue
                
                # If it's not a temporary error, or we ran out of retries
                html_code = f"<div style='color:red; padding:20px;'><h1>Error Generating Page {a_id}</h1><p>{e}</p></div>"

        final_pages.append(html_code)

    # 3. Combine Pages
    full_html = "\n<div class='page-break'></div>\n".join(final_pages)
    
    return {
        "html_code": full_html,
        "logs": [f"Publisher: Generated {len(final_pages)} pages via LLM (with retry logic)"]
    }