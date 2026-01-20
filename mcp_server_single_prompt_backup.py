"""
[MCP Server] Google Nano Banana - Dynamic Layout Engine
다중 이미지 지원 및 프롬프트 최적화 버전
"""
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    exit(1)

import json
import sys
import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Load environment variables (for API Key)
load_dotenv()

# Mock Config or Real Config
class MockConfig:
    def get_llm(self):
        from langchain_google_genai import ChatGoogleGenerativeAI
        import os
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-pro",
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
config = MockConfig()

mcp = FastMCP("Nano Banana Layout Service")

@mcp.tool()
def generate_magazine_layout(
    headline: str, 
    body: str, 
    image_data: str, 
    layout_override: str = "None",
    vision_context: str = "{}",
    design_spec: str = "{}",
    planner_intent: str = "{}"
) -> str:
    """
    LLM을 사용하여 동적으로 고품질 매거진 HTML을 생성합니다.
    image_data는 단일 문자열(플레이스홀더)일 수도 있고, JSON 리스트 문자열일 수도 있습니다.
    """
    print(f"🍌 [NanoBanana] Generating Layout for: {headline[:20]}...", file=sys.stderr)

    # 이미지 데이터 파싱 (리스트 여부 확인)
    is_multi_image = False
    images_list = []
    try:
        parsed = json.loads(image_data)
        if isinstance(parsed, list):
            images_list = parsed
            is_multi_image = True
    except:
        images_list = [image_data]

    image_count = len(images_list)
    print(f"🍌 [NanoBanana] Detected {image_count} images.", file=sys.stderr)

    llm = config.get_llm()

    # 🔧 JSON 파싱 및 구조화 (LLM이 이해할 수 있도록)
    try:
        vision_data = json.loads(vision_context) if vision_context != "{}" else {}
        design_data = json.loads(design_spec) if design_spec != "{}" else {}
        plan_data = json.loads(planner_intent) if planner_intent != "{}" else {}
    except:
        vision_data = {}
        design_data = {}
        plan_data = {}
    
    # Vision Context를 읽기 쉬운 텍스트로 변환
    vision_summary = "Not provided"
    if vision_data:
        keywords = vision_data.get('keywords', [])
        desc = vision_data.get('description', '')
        style = vision_data.get('visual_style', 'Modern')
        vision_summary = f"Style: {style}, Keywords: {', '.join(keywords) if keywords else 'none'}, Description: {desc}"
    
    # Design Spec을 읽기 쉬운 텍스트로 변환
    design_summary = "Standard magazine layout"
    if design_data:
        mood = design_data.get('mood', 'Modern')
        category = design_data.get('category', 'Magazine')
        typo = design_data.get('typography_style', 'Balanced')
        colors = design_data.get('color_scheme', 'Balanced palette')
        design_summary = f"Mood: {mood}, Category: {category}, Typography: {typo}, Colors: {colors}"
    
    # Layout Plan을 읽기 쉬운 텍스트로 변환
    layout_summary = "Flexible layout"
    if plan_data:
        spatial = plan_data.get('spatial_summary', 'Flexible layout')
        strategy = plan_data.get('suggested_strategy', 'Balanced')
        ref_id = plan_data.get('reference_id', 'N/A')
        
        # 🟢 Coordinate Injection Logic
        elements = plan_data.get('elements', [])
        blueprint_lines = []
        if elements:
            # Constants for coordinate normalization (based on typical dataset dimensions)
            REFERENCE_WIDTH = 800
            REFERENCE_HEIGHT = 1200
            
            for idx, elem in enumerate(elements[:8]): # Limit to 8 to avoid context overload
                etype = elem.get('type', 'content')
                coords = elem.get('coordinates', {})
                if coords and 'x1' in coords:
                    # Convert to % for resolution independence
                    cx = (coords.get('x1', 0) + coords.get('x2', 0)) / 2
                    cy = (coords.get('y1', 0) + coords.get('y2', 0)) / 2
                    
                    # Normalize to simple 3x3 grid terms using percentages
                    h_pos = "Left" if cx < REFERENCE_WIDTH * 0.375 else ("Right" if cx > REFERENCE_WIDTH * 0.625 else "Center")
                    v_pos = "Top" if cy < REFERENCE_HEIGHT * 0.33 else ("Bottom" if cy > REFERENCE_HEIGHT * 0.67 else "Middle")
                    
                    blueprint_lines.append(f"- Element {idx} ({etype}): {v_pos}-{h_pos} Area")
                else:
                    blueprint_lines.append(f"- Element {idx} ({etype}): Position Unknown")
        
        blueprint_str = "\n".join(blueprint_lines) if blueprint_lines else "No specific coordinates"
        layout_summary = f"Reference: {ref_id}\nStrategy: {strategy}\nStructure: {spatial}\n\n[BLUEPRINT HINTS]\n{blueprint_str}"

    # 최적화된 프롬프트: RAG 레이아웃 + 비전 컨텍스트 활용
    prompt_text = """
    You are 'Nano Banana', a specialized AI for High-End Magazine HTML/CSS generation.
    Create a UNIQUE A4 layout (794px x 1123px, ~210mm x 297mm) using Tailwind CSS.
    
    [INPUT DATA]
    - Headline: {headline}
    - Body: {body}
    - Image Count: {image_count}
    - Image Placeholders: {image_placeholders} (Use these EXACT strings in <img src="...">)
    - Page Type: {layout_override}
    
    [PAGE TYPE INSTRUCTIONS]
    **{layout_override}** page style:
    
    IF COVER:
    - Create a MAGAZINE COVER layout (IGNORE float/text-wrap guidelines below)
    - Image should be FULL-BLEED (fills entire page, edge-to-edge)
    - For COVER: use `object-cover` to fill the page (exception to contain rule)
    - Text OVERLAYS on the image using absolute positioning
    - Add dark gradient overlay for text readability: `bg-gradient-to-t from-black/70 to-transparent`
    - Headline: dramatic, LARGE (text-6xl to text-8xl), white or light colored
    - Body text: minimal, use as subtitle/tagline only
    - Think: Vogue, GQ, National Geographic covers
    - DO NOT use float layout for COVER
    
    IF ARTICLE:
    - Create an EDITORIAL ARTICLE layout
    - Text and image are SEPARATE (not overlapping)
    - Use float to wrap text around image (follow float guidelines below)
    - For ARTICLE: use `object-contain` to show full image
    - Body text should be fully readable and prominent
    - Text wraps around or beside the image
    - Think: Inside pages of a magazine
    
    [VISUAL CONTEXT]
    {vision_summary}
    → Use these visual elements to inform your color palette and design mood
    
    [DESIGN SPECIFICATION]
    {design_summary}
    → Adapt typography, spacing, and color scheme to match this specification
    
    [REFERENCE LAYOUT STRUCTURE]
    {layout_summary}
    → Use this as a COMPOSITIONAL GUIDE (Spirit of the layout), not a rigid blueprint.
    
    ═══════════════════════════════════════════════════════════════
    [ABSOLUTE RULES - NON-NEGOTIABLE]
    ═══════════════════════════════════════════════════════════════
    
    1. **IMAGE COUNT - MANDATORY** (MOST IMPORTANT RULE):
       - You MUST create EXACTLY {image_count} <img> tags
       - You MUST use these EXACT placeholders in src attribute:
         {image_placeholders}
       - Example for 1 image: <img src="__IMAGE_0__" ... />
       - Example for 5 images: <img src="__IMAGE_0__" />, ..., <img src="__IMAGE_4__" />
       - ⚠️ FAILURE TO INCLUDE ALL IMAGES IS UNACCEPTABLE
       - Every image MUST be visible in the final layout
       
       🎯 **IMAGE-FIRST DESIGN STRATEGY** (CRITICAL):
       Step 1: FIRST, place ALL {image_count} images on the page
               - Decide image positions and sizes BEFORE adding any text
               - Calculate: {image_count} images × approximate height = required image space
       Step 2: THEN, fill the REMAINING space with text
               - If space is limited, use smaller font (text-xs or text-sm)
               - Truncate text if necessary - images are the priority!
    
    2. **IMAGE DISPLAY**:
       - For ARTICLE pages: use `object-fit: contain` (show full image, no cropping)
       - For COVER pages: use `object-fit: cover` (fill container, some cropping OK)
       - Always use `object-position: center` for proper centering
       - ARTICLE example: <img class="object-contain" />
       - COVER example: <img class="w-full h-full object-cover" />
       - ⚠️ **NO BACKGROUND on image containers** - do NOT use bg-gray, bg-slate, or any bg-*
       - ⚠️ **NO FIXED-SIZE WRAPPERS** - do NOT wrap <img> in a div with fixed w-[Xpx] h-[Ypx]
       - Let the image determine its container size: use `<img class="h-[220px] w-auto" />` directly
    
    3. **PAGE HEIGHT**: Fit within 1123px total - CALCULATE BEFORE PLACING!
       - Headline + padding: ~150px
       - Remaining content area: ~950px
       - For 5 images stacked: max h-[180px] each (180×3=540px + 120×2=240px = 780px OK)
       - For 3 images stacked: max h-[250px] each (250×3=750px OK)
       - ⚠️ If total image height > 800px, reduce each image height!
       - Use text-sm for long text, line-clamp only for 1500+ chars
    
    4. **USE ONLY PROVIDED TEXT**: DO NOT generate additional content
       - Use ONLY the headline and body text provided
       - DO NOT add fictional quotes, stories, or descriptions
    
    5. **NO OVERLAP - READABILITY IS #1 PRIORITY** (CRITICAL):
       - ❌ **NEVER let text overlap with other text** - each paragraph must be clearly separated
       - ❌ **NEVER let text overlap with images** - maintain clear boundaries
       - ❌ **NEVER let images overlap with other images** - use proper spacing
       - ⚠️ **Avoid `absolute` positioning** unless absolutely necessary - it causes overlap!
       - If using `absolute`, ensure elements have enough `top/left/right/bottom` offset to not collide
       - Use `relative` + `flex` or `grid` layouts for predictable, non-overlapping placement
       - **TEST**: Can every text block be read clearly? Can every image be seen fully?
    
    6. **PAGE MARGINS - ALL SIDES MUST HAVE PADDING** (CRITICAL):
       - Top: pt-8 or pt-10 (header space)
       - Left: pl-8 or pl-10
       - Right: pr-8 or pr-10
       - **BOTTOM: pb-10 or pb-12** - content must NOT touch bottom edge!
       - Use wrapper: `<div class="p-8 pb-12">` or similar
       - Leave at least 40px (pb-10) at bottom for breathing room
    
    ═══════════════════════════════════════════════════════════════
    [DESIGN GUIDELINES - STRONGLY RECOMMENDED]
    ═══════════════════════════════════════════════════════════════
    
    🎯 **KEY PHRASE HIGHLIGHTING** (IMPORTANT):
    - Scan body text for quoted phrases ("..." or '...')
    - Apply ACCENT COLOR to these key phrases
    - Use italic or script font for emphasis
    - Example: 'Ideally, I'd have Steps performing' → red italic script
    - This makes the layout feel more editorial and premium
    
    🖼️ **IMAGE IMPACT ANALYSIS** (before placing):
    - Identify the HERO image (most expressive face, dramatic pose, direct eye contact)
    - Place HERO image in the MOST PROMINENT position (top-right or top-center)
    - Supporting images (group shots, events) go in smaller slots or bottom row
    - For portraits: the one with the most engaging expression = HERO
    
    📖 **TEXT FLOW BETWEEN IMAGES**:
    - Text should "WEAVE" between images, not just stack beside them
    - Create reading rhythm: Image → Text block → Image → Text block
    - Use varying column widths for visual interest
    - Text should feel like it's having a conversation with the images
    
    **Visual Style**:
    - Adapt to MOOD: {design_summary}
    - Use Vision Context for color palette: {vision_summary}
    - Aim for premium magazine aesthetic (Vogue, GQ, Kinfolk style)
    
    **Layout Strategy** (FOR ARTICLE PAGES ONLY - COVER uses overlay style):
    
    FOR ARTICLE WITH LONG BODY TEXT:
    - Use CSS `float` to wrap text AROUND the image (not just beside it)
    - Image floats to one side, text flows around it INCLUDING BELOW the image
    - This creates a natural editorial/magazine reading flow
    
    CORRECT FLOAT IMPLEMENTATION:
    ```html
    <div class="p-8">
      <h1>Headline</h1>
      <img src="__IMAGE_0__" class="float-left w-[50%] mr-6 mb-4 object-contain" />
      <p class="text-base leading-relaxed">
        Body text here... text flows to the right of image AND continues 
        below the image when it runs out of space on the right.
      </p>
      <div class="clear-both"></div>
    </div>
    ```
    
    IMAGE SIZE FOR ARTICLE (DYNAMIC based on image count):
    
    FOR 1 IMAGE:
    - Portrait/tall: w-[45%] to w-[50%]
    - Square: w-[50%] to w-[55%]  
    - Landscape: w-[55%] to w-[60%]
    
    FOR 2 IMAGES:
    - Each image: w-[40%] to w-[45%]
    - Stack vertically or side-by-side grid
    
    FOR 3+ IMAGES with SHORT/MEDIUM text (use float layout):
    - Each image: w-[30%] to w-[35%]
    - Use grid or mosaic arrangement
    - This is for cases where text is NOT long enough for multi-column
    
    **NOTE**: For 3+ images WITH LONG text (1000+ chars), use MULTI-COLUMN layout below instead!
    
    KEY RULES FOR TEXT WRAP (for body text 200+ chars):
    - Image and text must be in the SAME container (NOT separate columns)
    - Use `float-left` or `float-right` on <img>
    - Text naturally wraps around AND below the floated image
    - Add `clear-both` at the end to prevent layout issues
    
    **MULTI-COLUMN LAYOUT** (for LONG body text 1000+ chars WITH 3+ images):
    
    ⚠️ **LAYOUT WIDTH RULES** (CRITICAL - prevent overflow):
    - Total width MUST be exactly 100% (60% text + 40% images)
    - Text area: EXACTLY `w-[60%]` with `columns-2` (TWO columns ONLY)
    - Image area: EXACTLY `w-[40%]` on the RIGHT side
    - ❌ NEVER use `columns-3` - it causes overflow!
    - ❌ NEVER exceed 100% total width
    
    - CSS for text: `columns-2 gap-4` (NOT columns-3!)
    
    CORRECT STRUCTURE (matches real magazine layout):
    ```html
    <div class="flex gap-4 p-6">
      <!-- LEFT: Text in 2 columns -->
      <div class="w-[60%] columns-2 gap-4 text-sm leading-relaxed">
        <p>Body text flows across 2 narrow columns on the left side...</p>
        <!-- Pull quote in the middle -->
        <blockquote class="text-lg italic text-blue-600 border-l-4 border-blue-500 pl-4 my-4">
          'Key quote from the article'
        </blockquote>
        <p>More text continues...</p>
      </div>
      
      <!-- RIGHT: Images stacked vertically - make them LARGE -->
      <div class="w-[40%] flex flex-col gap-3">
        <img src="__IMAGE_0__" class="w-full h-[280px] object-cover rounded" />
        <img src="__IMAGE_1__" class="w-full h-[280px] object-cover rounded" />
        <img src="__IMAGE_2__" class="w-full h-[280px] object-cover rounded" />
      </div>
    </div>
    
    <!-- BOTTOM: Additional small images in a row (if more than 3 images) -->
    <div class="flex gap-4 px-6 mt-4">
      <img src="__IMAGE_3__" class="w-[30%] h-[150px] object-cover" />
      <img src="__IMAGE_4__" class="w-[30%] h-[150px] object-cover" />
      <p class="text-xs italic">Image caption here</p>
    </div>
    ```
    
    KEY POINTS FOR MULTI-COLUMN:
    - Text on LEFT, Images on RIGHT (not the other way around!)
    - Images should be LARGE (h-[280px] each) - don't make them tiny!
    - Use object-cover for portrait images to fill the space
    - 2 text columns maximum to keep readability
    - Pull quote with colored border for visual interest
    
    ⚠️ **CRITICAL - USE ALL IMAGES** (applies to MULTI-COLUMN layout):
    - You MUST include ALL {image_count} images - check the image_count!
    - If image_count > 3: Put first 3 in right column, remaining in bottom row
    - NEVER skip any images - every __IMAGE_X__ placeholder must appear
    - Bottom images: Use smaller size (h-[120px]) with caption text
    
    **EXAMPLE FOR 5 IMAGES** (if image_count == 5):
    ```html
    <div class="flex gap-4 p-6">
      <!-- LEFT: Text 60% -->
      <div class="w-[60%] columns-2 gap-4 text-sm">
        <p>Body text...</p>
        <blockquote class="italic text-blue-600 border-l-4 pl-4">'Pull quote'</blockquote>
        <p>More text...</p>
      </div>
      <!-- RIGHT: 3 portraits stacked 40% -->
      <div class="w-[40%] flex flex-col gap-2">
        <img src="__IMAGE_0__" class="w-full h-[220px] object-cover" />
        <img src="__IMAGE_1__" class="w-full h-[220px] object-cover" />
        <img src="__IMAGE_2__" class="w-full h-[220px] object-cover" />
      </div>
    </div>
    <!-- BOTTOM: 2 smaller images + caption (MUST include for 5 images!) -->
    <div class="flex gap-3 px-6 items-end">
      <img src="__IMAGE_3__" class="w-[22%] h-[120px] object-cover" />
      <img src="__IMAGE_4__" class="w-[22%] h-[120px] object-cover" />
      <p class="text-xs italic flex-1">Caption for bottom images</p>
    </div>
    ```
    
    FOR SHORT BODY TEXT (under 200 chars):
    - Use CSS Grid for side-by-side layout
    - Or Hero/Cover style with text overlay on image
    
    **IMPORTANT - SHOW ALL TEXT**:
    - Display the COMPLETE body text - do not truncate unless 1500+ chars
    - Use text-sm for very long text to fit more content
    - Let text flow below the image rather than cutting it off
    
    **Typography** (Make it STAND OUT):
    - Headline: BOLD and LARGE (text-5xl to text-7xl, font-black)
    - Body: Comfortable reading (text-base, leading-relaxed)
    - Use contrasting fonts: Serif headline + Sans body
    
    **COLOR MATCHING FROM IMAGE** (CRITICAL - DO NOT USE RANDOM COLORS):
    - Extract colors from the vision_summary keywords (e.g., "Deep blue", "Dark background")
    - Text colors MUST complement the image's dominant colors
    - Use the image's ACCENT COLOR extensively:
      → Decorative lines under/beside headline
      → Drop cap first letter
      → Pull quote borders
      → Page numbers and labels
      → Divider lines between sections
    - Examples:
      → Blue watch image → Blue accent line under headline, blue page number
      → Dark/moody image → White or cream text with subtle accent
    - DO NOT use random colors like yellow on a blue image
    - For COVER: Always use white/light text with dark gradient overlay
    
    **Visual Interest**:
    - Subtle backgrounds and gradients that match image tones
    - Decorative lines and borders in image-complementary colors
    
    **Spacing & Rhythm**:
    - Use generous but balanced padding (p-8 to p-12)
    - **ALWAYS leave bottom padding**: pb-8 or pb-10 (content must NOT touch bottom edge)
    - Create visual breathing room with margins (mb-6, mt-8)
    - Align elements to invisible grid for harmony
    - **Asymmetric spacing**: Don't center everything - use left/right alignment for interest
    
    **Premium Touches** (USE AT LEAST 1):
    - **Small caps for subheadings**: uppercase, tracking-wider, text-xs, font-semibold
    - **Letter spacing variations**: tracking-tight for headlines, tracking-widest for labels
    - **Vertical text on page edge**: writing-mode: vertical-rl, text-xs, opacity-50, absolute positioning
    - **Page numbers or issue labels**: absolute positioning, bottom-right or top-left, text-xs
    - **Decorative quotation marks**: Oversized quotes (text-9xl, opacity-10, absolute)
    - **Colored accents**: Small colored rectangles or lines as visual punctuation
    - **Layered text**: Stack text at different opacities for depth
    
    ═══════════════════════════════════════════════════════════════
    [CREATIVE FREEDOM]
    ═══════════════════════════════════════════════════════════════
    
    You are a CREATIVE art director for a HIGH-END magazine. Within the Absolute Rules:
    - **Experiment boldly**: Try unexpected layouts, dramatic typography, striking color combinations
    - **Create visual hierarchy**: Use size, weight, color, and spacing to guide the eye
    - **Add visual drama**: Don't be afraid of large headlines, bold colors, or decorative elements
    - **Think premium**: Every design should feel sophisticated, intentional, and magazine-worthy
    - **Use the full toolkit**: Combine multiple premium touches for maximum impact
    - **Ask yourself**: "Would this stop someone flipping through Vogue or GQ?"
    
    ═══════════════════════════════════════════════════════════════
    [SELF-VALIDATION STEP - MUST DO BEFORE OUTPUT]
    ═══════════════════════════════════════════════════════════════
    
    After drafting your HTML, mentally CHECK:
    
    ✅ **Checklist** (CHECK ALL BEFORE OUTPUT):
    0. 🔴 **NO OVERLAP**: Text-text, text-image, image-image - ZERO overlap allowed!
    1. Are ALL {image_count} images included? (Count them!)
    2. Is total content height ≤ 1100px? (Leave 23px margin)
    3. Is any content cut off at the bottom?
    4. Can EVERY text block be read clearly without obstruction?
    5. Can EVERY image be seen fully without overlap?
    6. Is the HERO image in the most prominent position?
    
    ⚠️ **If content overflows** (height > 1100px), apply these fixes IN ORDER:
    
    **Fix 1: Reduce image heights**
    - 5 images: h-[150px] for stacked, h-[100px] for bottom row
    - 4 images: h-[180px] each
    - 3 images: h-[200px] each
    
    **Fix 2: Reduce text font size**
    - Body text: text-xs (12px) with leading-tight
    - Can go to text-[10px] if needed (minimum allowed)
    
    **Fix 3: Apply line-clamp**
    - Use line-clamp-[X] on body text as last resort
    - Calculate X based on available height
    
    **CRITICAL**: ALL {image_count} images MUST be visible on the page.
    If images don't fit, make them smaller - NEVER omit them!
    
    ═══════════════════════════════════════════════════════════════
    
    **Output Format**:
    - Raw HTML with Tailwind CSS
    - Wrapper: `<div class="w-[794px] h-[1123px] relative overflow-hidden bg-white text-slate-900 font-serif mx-auto shadow-2xl">`
    - NO markdown blocks
    """

    prompt = ChatPromptTemplate.from_template(prompt_text)
    chain = prompt | llm | StrOutputParser()

    try:
        html = chain.invoke({
            "headline": headline,
            "body": body,
            "image_count": image_count,
            "image_placeholders": str(images_list),
            "layout_override": layout_override,    # COVER or ARTICLE
            "vision_summary": vision_summary,      # 구조화된 텍스트
            "design_summary": design_summary,      # 구조화된 텍스트
            "layout_summary": layout_summary       # 구조화된 텍스트
        })
        
        print(f"🍌 [NanoBanana] Generated HTML Length: {len(html)} chars", file=sys.stderr)
        return html.replace("```html", "").replace("```", "").strip()
        
    except Exception as e:
        print(f"❌ [NanoBanana] Error: {e}", file=sys.stderr)
        return f"<div class='p-10 text-red-500'>Error: {e}</div>"

if __name__ == "__main__":
    mcp.run()
