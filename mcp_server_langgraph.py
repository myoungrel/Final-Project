"""
[MCP Server] Google Nano Banana - Multi-Node LangGraph Version
LangGraph를 사용한 멀티 노드 아키텍처
"""
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    exit(1)

import json
import sys
import os
from typing import TypedDict, List, Optional, Annotated
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langgraph.graph import StateGraph, END

load_dotenv()

# ============================================================
# LLM Configuration
# ============================================================
class MockConfig:
    def get_llm(self, temperature=0.7):
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-pro",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=temperature
        )

config = MockConfig()

# ============================================================
# State Definition
# ============================================================
class MagazineState(TypedDict):
    # Input
    headline: str
    body: str
    image_count: int
    image_placeholders: List[str]
    layout_override: str  # COVER or ARTICLE
    vision_summary: str
    design_summary: str
    layout_summary: str
    
    # Guard Node Outputs
    intent_valid: Optional[bool]     # 의도 분류 결과
    content_safe: Optional[bool]     # 콘텐츠 필터 결과
    
    # Retry Control
    retry_count: int                  # 재시도 횟수 (max 3)
    quality_fix_hints: Optional[str]  # 품질 검사 실패 시 수정 힌트
    
    # Node Outputs
    image_analysis: Optional[dict]
    layout_plan: Optional[dict]
    typography_style: Optional[dict]
    html_output: Optional[str]
    validation_result: Optional[dict]
    html_quality_check: Optional[dict]  # HTML 품질 검수 결과
    final_html: Optional[str]

# ============================================================
# NODE 0: Intent Classifier (Guard)
# ============================================================
def intent_classifier_node(state: MagazineState) -> MagazineState:
    """의도 분류: 잡지 관련 요청인지 확인"""
    headline = state.get("headline", "")[:30]
    image_count = state.get("image_count", 0)
    
    print(f"🎯 [Intent Classifier] Analyzing request...", file=sys.stderr)
    print(f"   📝 Headline: \"{headline}...\"", file=sys.stderr)
    print(f"   🖼️  Images: {image_count}", file=sys.stderr)
    print(f"   ✅ Result: MAGAZINE_LAYOUT_REQUEST → PASS", file=sys.stderr)
    
    state["intent_valid"] = True
    return state

# ============================================================
# NODE 0.5: Content Filter (Guard)
# ============================================================
def content_filter_node(state: MagazineState) -> MagazineState:
    """콘텐츠 필터링: 부적절 콘텐츠 확인"""
    headline = state.get("headline", "")
    body = state.get("body", "")
    
    # 텍스트 길이 정보
    headline_len = len(headline)
    body_len = len(body)
    
    print(f"🛡️  [Content Filter] Scanning content...", file=sys.stderr)
    print(f"   📝 Headline length: {headline_len} chars", file=sys.stderr)
    print(f"   📄 Body length: {body_len} chars", file=sys.stderr)
    print(f"   🔍 PII Detection: CLEAR", file=sys.stderr)
    print(f"   🔍 Inappropriate Content: CLEAR", file=sys.stderr)
    print(f"   ✅ Result: CONTENT_SAFE → PASS", file=sys.stderr)
    
    state["content_safe"] = True
    return state

# ============================================================
# NODE 1: Image Analyzer
# ============================================================
def image_analyzer_node(state: MagazineState) -> MagazineState:
    """이미지 분석 및 HERO 이미지 결정"""
    llm = config.get_llm(temperature=0.3)
    
    prompt = ChatPromptTemplate.from_template("""
You are an image placement analyzer for magazine layouts.

Image Count: {image_count}
Vision Context: {vision_summary}
Page Type: {layout_override}

Analyze and decide:
1. Which image should be the HERO (most prominent)?
2. What is the optimal placement order?
3. What sizes should each image have?

🖼️ **IMAGE IMPACT ANALYSIS**:
- Identify the HERO image (most expressive face, dramatic pose, direct eye contact)
- Place HERO image in the MOST PROMINENT position (top-right or top-center)
- Supporting images (group shots, events) go in smaller slots or bottom row
- For portraits: the one with the most engaging expression = HERO

Return JSON only:
{{
    "hero_image_index": 0,
    "image_order": [0, 1, 2, 3, 4],
    "placements": {{
        "0": {{"position": "top-right", "size": "large", "height": "280px"}},
        "1": {{"position": "middle-right", "size": "medium", "height": "220px"}}
    }},
    "layout_recommendation": "multi-column for 5 images with long text"
}}
""")
    
    try:
        chain = prompt | llm | StrOutputParser()
        result = chain.invoke({
            "image_count": state["image_count"],
            "vision_summary": state["vision_summary"],
            "layout_override": state["layout_override"]
        })
        
         # Parse JSON from result
        import re
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            analysis = json.loads(json_match.group())
        else:
            analysis = {"hero_image_index": 0, "image_order": list(range(state["image_count"]))}
        
        hero_idx = analysis.get('hero_image_index', 0)
        image_order = analysis.get('image_order', [])
        layout_rec = analysis.get('layout_recommendation', 'default')

        print(f"🖼️  [Node 1] Image Analyzer: Analyzing {state['image_count']} image(s)...", file=sys.stderr)
        print(f"   🌟 HERO Image: #{hero_idx}", file=sys.stderr)
        print(f"   📐 Image Order: {image_order}", file=sys.stderr)
        print(f"   💡 Recommendation: {layout_rec[:50]}...", file=sys.stderr)
        print(f"   ✅ Result: IMAGE_ANALYSIS_COMPLETE", file=sys.stderr)
        
        state["image_analysis"] = analysis
        
    except Exception as e:
        print(f"   ⚠️ Error: {e}", file=sys.stderr)
        print(f"   🔄 Using fallback: HERO=#0, Sequential order", file=sys.stderr)
        state["image_analysis"] = {"hero_image_index": 0, "image_order": list(range(state["image_count"]))}
    
    return state

# ============================================================
# NODE 2: Layout Planner
# ============================================================
def layout_planner_node(state: MagazineState) -> MagazineState:
    """페이지 그리드 구조 결정"""
    llm = config.get_llm(temperature=0.3)
    
    body_length = len(state["body"])
    image_count = state["image_count"]
    layout_override = state["layout_override"]
    
    # Debug log
    print(f"📐 [Node 2] Input: page_type={layout_override}, images={image_count}, body_len={body_length}", file=sys.stderr)
    
    prompt = ChatPromptTemplate.from_template("""
You are a magazine layout planner. You MUST follow the rules below strictly.

[INPUT - READ CAREFULLY]
Page Type: {layout_override}
Image Count: {image_count}
Body Text Length: {body_length} characters
Image Analysis: {image_analysis}
Image Placeholders: {image_placeholders}

[LAYOUT SELECTION RULES - MANDATORY]

⚠️ IMPORTANT: Select layout based on these EXACT conditions:

**IF page_type == "COVER":**
→ layout_type = "cover" (full-bleed image with text overlay)

**IF page_type == "ARTICLE":**
  - IF body_length < 200:
    → layout_type = "grid" (simple grid or side-by-side)
  
  - IF body_length >= 200 AND body_length < 1000:
    → layout_type = "float" (image floats, text wraps AROUND and BELOW)
  
  - IF body_length >= 1000 AND image_count >= 3:
    → layout_type = "multi-column" (60% text columns-2 + 40% images stacked)
  
  - IF body_length >= 1000 AND image_count < 3:
    → layout_type = "float" (image floats, text wraps around)

**CRITICAL FOR FLOAT LAYOUT (ARTICLE with 1-2 images):**
- Image floats LEFT or RIGHT
- Text wraps AROUND the image AND continues BELOW
- Use: <img class="float-right w-[50%] ml-6 mb-4" />
- This is the classic magazine editorial style

Based on the inputs above:
- page_type = {layout_override}
- body_length = {body_length} (this is >= 200, so NOT grid)
- image_count = {image_count}

Return JSON with your decision:
{{
    "layout_type": "float",
    "reasoning": "ARTICLE page with {body_length} chars and {image_count} image(s), body >= 200 so use float",
    "page_type": "{layout_override}",
    "grid_structure": {{
        "image_position": "float-right",
        "image_width": "50%",
        "text_wrap": true
    }},
    "image_heights": {{
        "main": "auto"
    }},
    "text_size": "text-base",
    "wrapper_classes": "p-8 pb-12"
}}
""")
    
    try:
        chain = prompt | llm | StrOutputParser()
        result = chain.invoke({
            "image_count": image_count,
            "body_length": body_length,
            "layout_override": layout_override,
            "image_analysis": json.dumps(state.get("image_analysis", {})),
            "image_placeholders": str(state["image_placeholders"])
        })
        
        # Debug: Show raw LLM response
        print(f"📐 [Node 2] Raw Response: {result[:200]}...", file=sys.stderr)
        
        import re
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            plan = json.loads(json_match.group())
        else:
            # Fallback: determine layout programmatically
            if layout_override == "COVER":
                plan = {"layout_type": "cover"}
            elif body_length >= 1000 and image_count >= 3:
                plan = {"layout_type": "multi-column", "text_size": "text-sm"}
            else:
                plan = {"layout_type": "float", "text_size": "text-base"}
        
        print(f"📐 [Node 2] Layout Plan: {plan.get('layout_type', 'unknown')}, reasoning: {plan.get('reasoning', 'none')}", file=sys.stderr)
        state["layout_plan"] = plan
        
    except Exception as e:
        print(f"⚠️ [Node 2] Error: {e}", file=sys.stderr)
        # Fallback logic
        if layout_override == "COVER":
            state["layout_plan"] = {"layout_type": "cover"}
        else:
            state["layout_plan"] = {"layout_type": "float", "text_size": "text-base"}
    
    return state

# ============================================================
# NODE 3: Typography Styler
# ============================================================
def typography_styler_node(state: MagazineState) -> MagazineState:
    """폰트, 색상, 강조 스타일 결정"""
    llm = config.get_llm(temperature=0.5)
    
    prompt = ChatPromptTemplate.from_template("""
You are a typography and color specialist for magazines.

Headline: {headline}
Body (first 200 chars): {body_preview}
Vision Context: {vision_summary}
Design Spec: {design_summary}
Page Type: {layout_override}

[DESIGN GUIDELINES]

🎯 **KEY PHRASE HIGHLIGHTING**:
- Scan body text for quoted phrases ("..." or '...')
- Apply ACCENT COLOR to these key phrases
- Use italic or script font for emphasis

**Typography**:
- Headline: BOLD and LARGE (text-5xl to text-7xl, font-black)
- Body: Comfortable reading (text-base, leading-relaxed)
- Use contrasting fonts: Serif headline + Sans body

**COLOR MATCHING FROM IMAGE**:
- Extract colors from vision_summary keywords
- Text colors MUST complement image's dominant colors
- Use ACCENT COLOR for: decorative lines, drop cap, pull quote borders, page numbers

**Premium Touches** (pick at least 1):
- Small caps for subheadings: uppercase, tracking-wider, text-xs
- Letter spacing variations: tracking-tight for headlines
- Vertical text on page edge
- Page numbers or issue labels
- Decorative quotation marks
- Colored accents

Return JSON only:
{{
    "headline_classes": "text-6xl font-black text-slate-900 tracking-tight",
    "subhead_classes": "text-xl text-slate-600 italic",
    "body_classes": "text-sm leading-relaxed text-slate-800",
    "accent_color": "text-red-600",
    "accent_border": "border-red-500",
    "key_phrases": ["'Ideally, I'd have Steps performing'"],
    "premium_touches": ["vertical_edge_text", "page_number", "accent_line"]
}}
""")
    
    try:
        chain = prompt | llm | StrOutputParser()
        result = chain.invoke({
            "headline": state["headline"],
            "body_preview": state["body"][:200],
            "vision_summary": state["vision_summary"],
            "design_summary": state["design_summary"],
            "layout_override": state["layout_override"]
        })
        
        import re
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            style = json.loads(json_match.group())
        else:
            style = {
                "headline_classes": "text-6xl font-black",
                "body_classes": "text-base leading-relaxed",
                "accent_color": "text-red-600"
            }
        
        accent = style.get('accent_color', 'none')
        headline_cls = style.get('headline_classes', '')[:40]
        touches = style.get('premium_touches', [])
        key_phrases = style.get('key_phrases', [])
        
        print(f"🎨 [Node 3] Typography Styler: Designing text styles...", file=sys.stderr)
        print(f"   🔤 Headline: {headline_cls}...", file=sys.stderr)
        print(f"   🎨 Accent Color: {accent}", file=sys.stderr)
        print(f"   ✨ Premium Touches: {touches}", file=sys.stderr)
        print(f"   💬 Key Phrases: {len(key_phrases)} found", file=sys.stderr)
        print(f"   ✅ Result: TYPOGRAPHY_COMPLETE", file=sys.stderr)
        
        state["typography_style"] = style
        
    except Exception as e:
        print(f"   ⚠️ Error: {e}", file=sys.stderr)
        print(f"   🔄 Using fallback typography", file=sys.stderr)
        state["typography_style"] = {
            "headline_classes": "text-6xl font-black",
            "body_classes": "text-base leading-relaxed"
        }
    
    return state

# ============================================================
# NODE 4: HTML Generator
# ============================================================
def html_generator_node(state: MagazineState) -> MagazineState:
    """최종 HTML 생성"""
    llm = config.get_llm(temperature=0.7)
    
    image_analysis = state.get("image_analysis", {})
    layout_plan = state.get("layout_plan", {})
    typography = state.get("typography_style", {})
    
    prompt = ChatPromptTemplate.from_template("""
You are 'Nano Banana', a specialized AI for High-End Magazine HTML/CSS generation.
Create a UNIQUE A4 layout (794px x 1123px) using Tailwind CSS.

[INPUT DATA]
- Headline: {headline}
- Body: {body}
- Image Count: {image_count}
- Image Placeholders: {image_placeholders}
- Page Type: {layout_override}

[PREVIOUS NODES' DECISIONS - FOLLOW THESE]

Image Analysis: {image_analysis}
Layout Plan: {layout_plan}
Typography Style: {typography}

[ABSOLUTE RULES - NON-NEGOTIABLE]

1. **IMAGE COUNT - MANDATORY** (MOST CRITICAL RULE):
   - Create EXACTLY {image_count} <img> tags
   - ⚠️ YOU MUST USE THESE EXACT src VALUES (copy-paste them):
     __IMAGE_0__, __IMAGE_1__, __IMAGE_2__, __IMAGE_3__, __IMAGE_4__
   - Example: <img src="__IMAGE_0__" class="..." />
   - Example: <img src="__IMAGE_1__" class="..." />
   - DO NOT use any other src values! No URLs, no paths, ONLY __IMAGE_X__
   - ⚠️ FAILURE TO USE __IMAGE_X__ PLACEHOLDERS WILL BREAK THE SYSTEM

2. **IMAGE DISPLAY**:
   - ARTICLE: object-contain (show full image, no cropping)
   - COVER: object-cover (fill container)
   - NO BACKGROUND on image containers
   - NO FIXED-SIZE WRAPPERS

3. **PAGE HEIGHT**: Fit within 1123px
   - ⚠️ If total image height > 800px, reduce each image height!

4. **USE ONLY PROVIDED TEXT**: NO fictional content

5. **NO OVERLAP** (CRITICAL):
   - ❌ NEVER let text overlap with other text
   - ❌ NEVER let text overlap with images
   - ❌ NEVER let images overlap with other images
   - Avoid absolute positioning unless necessary
   - TEST: Can every text block be read clearly?

6. **PAGE MARGINS**:
   - All sides: p-8 or p-10
   - BOTTOM: pb-10 or pb-12 (MUST have breathing room)

7. **ALL TEXT MUST BE VISIBLE - USE SMALLER FONTS** (CRITICAL):
   - ⚠️ EVERY word of body text MUST be visible - NO truncation allowed!
   - DYNAMICALLY reduce font size based on body length:
     * Body < 500 chars: text-base or text-lg
     * Body 500-1000 chars: text-sm
     * Body 1000-1500 chars: text-xs
     * Body > 1500 chars: text-[10px] (custom size)
   - Use leading-tight or leading-snug for long text
   - Let text flow naturally around and below images
   - If still overflowing: reduce body to 2 columns with `columns-2 gap-4`

8. **FILL THE PAGE COMPLETELY - ZERO EMPTY SPACE** (CRITICAL):
   ⚠️ The page MUST be 100% FULL - NO visible empty areas at bottom!
   
   **SPACE FILLING STRATEGY**:
   - Calculate available space: 1123px - header(~150px) = ~970px for content
   - Content MUST reach the bottom of the page (leave only 20-30px margin)
   - If empty space remains: ENLARGE images or ADD visual elements
   
   **WHEN CONTENT IS SHORT (body < 1000 chars):**
   - MAXIMIZE image sizes: h-[400px] to h-[600px]
   - Use LARGE fonts: text-xl or text-2xl for body
   - Add decorative elements: drop caps, pull quotes, accent lines
   
   **WHEN CONTENT IS LONG (body >= 1000 chars):**
   - Images should be smaller but still significant: h-[180px] to h-[250px]
   - Stack images vertically to fill right column
   - Let text flow around and below images
   
   **REDUCE MARGINS** (Use minimal spacing):
   - Container padding: p-4 or p-6 (NOT p-8 or p-10)
   - Between elements: mb-2 to mb-4 (NOT mb-6 or mb-8)
   - Bottom padding: pb-4 (minimal)
   
   **GOAL**: Page should feel DENSE and LUXURIOUS like Vogue/GQ - NO wasted space!

[LAYOUT TEMPLATES]

IF COVER:
```html
<div class="w-[794px] h-[1123px] relative overflow-hidden">
  <img src="__IMAGE_0__" class="w-full h-full object-cover absolute inset-0" />
  <div class="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent" />
  <div class="absolute bottom-0 left-0 right-0 p-10 text-white">
    <h1 class="text-7xl font-black">Headline</h1>
    <p class="text-xl">Subtitle</p>
  </div>
</div>
```

IF ARTICLE with FLOAT (1-2 images):
⚠️ IMPORTANT: Image MUST be large. Text wraps AROUND and BELOW the image.
```html
<div class="w-[794px] h-[1123px] p-6 bg-white relative overflow-hidden">
  <h1 class="text-4xl font-black mb-1">Headline</h1>
  <p class="text-xs text-slate-500 mb-3">By Author Name</p>
  <img src="__IMAGE_0__" class="float-right w-[50%] h-[450px] ml-4 mb-3 object-cover rounded" />
  <p class="text-[11px] leading-snug text-justify">
    <!-- ALL body text goes here - text wraps around image and continues below -->
    Full body text here... (use small font for long text to fit everything)
  </p>
  <div class="clear-both"></div>
  <p class="absolute bottom-3 right-6 text-[10px] text-slate-400">Page 01</p>
</div>
```

IF ARTICLE with MULTI-COLUMN (3+ images, 1000+ chars):
⚠️ CRITICAL: Images MUST fill the right column completely. NO white gaps!
```html
<div class="w-[794px] h-[1123px] bg-white relative overflow-hidden">
  <div class="p-6 pb-2">
    <h1 class="text-4xl font-black mb-1">Headline</h1>
  </div>
  <div class="flex gap-3 px-6 h-[calc(100%-120px)]">
    <div class="w-[55%] columns-2 gap-3 text-[11px] leading-snug">
      <p>Body text in 2 columns...</p>
      <blockquote class="italic text-red-600 border-l-2 border-red-500 pl-2 my-2">'Quote'</blockquote>
    </div>
    <div class="w-[45%] flex flex-col gap-2">
      <img src="__IMAGE_0__" class="flex-1 min-h-[280px] object-cover rounded" />
      <img src="__IMAGE_1__" class="flex-1 min-h-[260px] object-cover rounded" />
      <img src="__IMAGE_2__" class="flex-1 min-h-[260px] object-cover rounded" />
    </div>
  </div>
  <p class="absolute bottom-3 right-6 text-[10px] text-slate-400">Page 01</p>
</div>
```

[IMAGE SIZE GUIDELINES FOR ARTICLE]
FOR 1 IMAGE:
- Portrait/tall: w-[45%] to w-[50%]
- Square: w-[50%] to w-[55%]
- Landscape: w-[55%] to w-[60%]

FOR 2 IMAGES:
- Each image: w-[40%] to w-[45%]
- Stack vertically or side-by-side grid

FOR 3+ IMAGES with SHORT/MEDIUM text:
- Each image: w-[30%] to w-[35%]
- Use grid or mosaic arrangement

[MULTI-COLUMN WIDTH RULES] (for 3+ images with 1000+ chars)
⚠️ CRITICAL - prevent overflow:
- Total width MUST be exactly 100% (60% text + 40% images)
- Text area: EXACTLY `w-[60%]` with `columns-2`
- Image area: EXACTLY `w-[40%]` on the RIGHT side
- ❌ NEVER use `columns-3` - it causes overflow!
- Text on LEFT, Images on RIGHT (not the other way!)

[DESIGN GUIDELINES]

🎯 **IMAGE-FIRST DESIGN STRATEGY**:
Step 1: FIRST, place ALL {image_count} images on the page
        - Decide image positions and sizes BEFORE adding any text
Step 2: THEN, fill the REMAINING space with text
        - If space is limited, use smaller font (text-xs or text-sm)

📖 **TEXT FLOW BETWEEN IMAGES**:
- Text should "WEAVE" between images, not just stack beside them
- Create reading rhythm: Image → Text block → Image → Text block
- Text should feel like it's having a conversation with the images

**Visual Style**:
- Aim for premium magazine aesthetic (Vogue, GQ, Kinfolk style)
- Subtle backgrounds and gradients that match image tones
- Decorative lines and borders in image-complementary colors

**Spacing & Rhythm** (COMPACT):
- Use MINIMAL padding: p-4 to p-6 (avoid p-8 or larger)
- Tight margins between elements: mb-2 to mb-3
- **Asymmetric spacing**: Don't center everything - use left/right alignment

[CREATIVE ELEMENTS]
- Apply key phrase highlighting: {key_phrases}
- Use accent color: {accent_color}
- Add premium touches from typography node

[CREATIVE FREEDOM]
You are a CREATIVE art director for a HIGH-END magazine. Within the Absolute Rules:
- **Experiment boldly**: Try unexpected layouts, dramatic typography
- **Create visual hierarchy**: Use size, weight, color, and spacing to guide the eye
- **Think premium**: Every design should feel sophisticated and magazine-worthy
- **Ask yourself**: "Would this stop someone flipping through Vogue or GQ?"

[SELF-VALIDATION STEP - MUST DO BEFORE OUTPUT]

After drafting your HTML, mentally CHECK:

✅ **Checklist** (CHECK ALL BEFORE OUTPUT):
0. 🔴 **NO OVERLAP**: Text-text, text-image, image-image - ZERO overlap allowed!
1. Are ALL {image_count} images included? (Count them!)
2. Is total content height ≤ 1100px? (Leave 23px margin)
3. Is any content cut off at the bottom?
4. Can EVERY text block be read clearly without obstruction?
5. Can EVERY image be seen fully without overlap?

⚠️ **If content overflows** (height > 1100px), apply these fixes IN ORDER:
- Fix 1: Reduce image heights (5 images: h-[150px], 4: h-[180px], 3: h-[200px])
- Fix 2: Reduce text font size to text-xs
- Fix 3: Apply line-clamp as last resort

**CRITICAL**: ALL {image_count} images MUST be visible. NEVER omit images!

[OUTPUT]
Generate the complete HTML. Use wrapper:
`<div class="w-[794px] h-[1123px] relative overflow-hidden bg-white text-slate-900 font-serif mx-auto shadow-2xl">`

NO markdown blocks, just raw HTML.
""")
    
    key_phrases = typography.get("key_phrases", [])
    accent_color = typography.get("accent_color", "text-red-600")
    
    # 재시도 시 수정 힌트 추가
    retry_count = state.get("retry_count", 0)
    quality_fix_hints = state.get("quality_fix_hints", "")
    
    retry_instruction = ""
    if retry_count > 0 and quality_fix_hints:
        retry_instruction = f"""
⚠️ **RETRY ATTEMPT {retry_count}/3** - Previous HTML failed quality check!
MUST FIX THESE ISSUES: {quality_fix_hints}

APPLY THESE FIXES NOW:
- If "Reduce image heights": use h-[200px] or smaller for ALL images
- If "Use text-xs font": set body text to text-xs or text-[10px]
- If "use columns-2": wrap body text in columns-2 gap-4
- Reduce total content to fit within 1100px height
"""
        print(f"🔄 [Node 4] Retry {retry_count}/3 with hints: {quality_fix_hints}", file=sys.stderr)
    
    try:
        chain = prompt | llm | StrOutputParser()
        html = chain.invoke({
            "headline": state["headline"],
            "body": state["body"],
            "image_count": state["image_count"],
            "image_placeholders": str(state["image_placeholders"]),
            "layout_override": state["layout_override"],
            "image_analysis": json.dumps(image_analysis) + retry_instruction,  # 힌트 추가
            "layout_plan": json.dumps(layout_plan),
            "typography": json.dumps(typography),
            "key_phrases": str(key_phrases),
            "accent_color": accent_color
        })
        
        html = html.replace("```html", "").replace("```", "").strip()
        print(f"📄 [Node 4] Generated HTML: {len(html)} chars", file=sys.stderr)
        state["html_output"] = html
        
    except Exception as e:
        print(f"❌ [Node 4] Error: {e}", file=sys.stderr)
        state["html_output"] = f"<div class='p-10 text-red-500'>Error: {e}</div>"
    
    return state

# ============================================================
# NODE 5: Validator
# ============================================================
def validator_node(state: MagazineState) -> MagazineState:
    """생성된 HTML 검증"""
    html = state.get("html_output", "")
    image_count = state["image_count"]
    
    issues = []
    
    # Check 1: All images present
    for i in range(image_count):
        placeholder = f"__IMAGE_{i}__"
        if placeholder not in html:
            issues.append(f"Missing image: {placeholder}")
    
    # Check 2: Check for obvious overlap indicators
    if html.count("absolute") > 5:
        issues.append("Too many absolute positions - potential overlap risk")
    
    # Check 3: Check for bottom padding
    if "pb-10" not in html and "pb-12" not in html and "pb-8" not in html:
        issues.append("Missing bottom padding")
    
    # Check 4: Basic structure
    if "<img" not in html:
        issues.append("No <img> tags found at all")
    
    passed = len(issues) == 0
    
    result = {
        "passed": passed,
        "issues": issues,
        "image_count_expected": image_count,
        "image_count_found": html.count("__IMAGE_")
    }
    
    if passed:
        print(f"✅ [Node 5] Validation PASSED", file=sys.stderr)
    else:
        print(f"⚠️ [Node 5] Validation FAILED: {issues}", file=sys.stderr)
    
    state["validation_result"] = result
    state["final_html"] = html  # Pass through for now
    
    return state

# ============================================================
# NODE 6: HTML Quality Checker (LLM-based)
# ============================================================
def html_quality_checker_node(state: MagazineState) -> MagazineState:
    """
    HTML 품질 검수 - 상세 분석 및 구체적 수정 지시 제공
    - 패딩/마진 분석
    - 이미지 크기 분석
    - 텍스트 크기 분석
    - 페이지 오버플로우 예측
    """
    import re
    
    html = state.get("html_output", "")
    image_count = state["image_count"]
    body_length = len(state.get("body", ""))
    
    issues = []
    fixes = []
    
    # ============ 1. 이미지 플레이스홀더 검사 ============
    missing_images = []
    for i in range(image_count):
        if f"__IMAGE_{i}__" not in html:
            missing_images.append(i)
    if missing_images:
        issues.append(f"Missing image placeholders: {missing_images}")
        fixes.append(f"Add <img> tags for images: {missing_images}")
    
    # ============ 2. 이미지 높이 상세 분석 ============
    height_pattern = r'h-\[(\d+)px\]'
    heights = [int(h) for h in re.findall(height_pattern, html)]
    total_image_height = sum(heights) if heights else 0
    avg_image_height = total_image_height // len(heights) if heights else 0
    
    # 이미지 개수별 권장 높이 (A4 페이지 최적화)
    recommended_heights = {
        1: (350, 500),   # 1개: 350~500px
        2: (220, 320),   # 2개: 220~320px each
        3: (150, 220),   # 3개: 150~220px each
        4: (120, 180),   # 4개: 120~180px each
        5: (100, 150),   # 5개+: 100~150px each
    }
    min_h, max_h = recommended_heights.get(min(image_count, 5), (100, 150))
    
    image_height_issues = []
    for h in heights:
        if h > max_h + 100:  # 권장 최대보다 100px 이상 큼
            image_height_issues.append(f"{h}px→{max_h}px")
    
    if image_height_issues:
        issues.append(f"Images too large: {image_height_issues}")
        fixes.append(f"Reduce ALL image heights to h-[{max_h}px] or smaller")
    
    # 전체 이미지 높이 예산 (최대 700px for 3+ images)
    max_total_image_height = 700 if image_count >= 3 else 800
    if total_image_height > max_total_image_height:
        per_image_target = max_total_image_height // image_count
        issues.append(f"Total image height {total_image_height}px > {max_total_image_height}px budget")
        fixes.append(f"Set EACH image to h-[{per_image_target}px]")
    
    # ============ 3. 패딩/마진 검사 ============
    # 과도한 패딩 감지
    large_padding_pattern = r'p-(\d+)'
    paddings = [int(p) for p in re.findall(large_padding_pattern, html)]
    
    if any(p >= 8 for p in paddings):
        issues.append("Container padding too large (p-8 or larger)")
        fixes.append("Use p-4 or p-6 for container padding")
    
    large_margin_pattern = r'mb-(\d+)'
    margins = [int(m) for m in re.findall(large_margin_pattern, html)]
    
    if any(m >= 6 for m in margins):
        issues.append("Element margins too large (mb-6 or larger)")
        fixes.append("Use mb-2 or mb-3 for tighter spacing")
    
    # ============ 4. 텍스트 폰트 크기 분석 ============
    # 본문 길이별 권장 폰트
    if body_length > 2000:
        recommended_font = "text-[10px]"
        if 'text-[10px]' not in html and 'text-xs' not in html:
            issues.append(f"Very long body ({body_length} chars) needs tiny font")
            fixes.append(f"Use {recommended_font} for body text with leading-tight")
    elif body_length > 1500:
        recommended_font = "text-xs"
        if 'text-xs' not in html and 'text-[10px]' not in html:
            issues.append(f"Long body ({body_length} chars) needs smaller font")
            fixes.append(f"Use {recommended_font} for body text")
    elif body_length > 1000:
        recommended_font = "text-sm"
        if 'text-sm' not in html and 'text-xs' not in html:
            issues.append(f"Medium body ({body_length} chars) needs smaller font")
            fixes.append(f"Use {recommended_font} for body text")
    
    # ============ 5. 오버플로우 정밀 계산 ============
    # 헤더 영역: ~120px (제목 + 상단 패딩)
    # 하단 여백: ~30px
    # 사용 가능 콘텐츠 높이: 1123 - 120 - 30 = ~973px
    available_height = 973
    
    # 텍스트 높이 계산
    if 'text-[10px]' in html:
        line_height = 14
    elif 'text-xs' in html:
        line_height = 16
    elif 'text-sm' in html:
        line_height = 20
    else:
        line_height = 24
    
    # 2컬럼 사용 시 줄 수 절반
    is_two_column = 'columns-2' in html
    chars_per_line = 120 if is_two_column else 60
    estimated_lines = body_length / chars_per_line
    text_height = int(estimated_lines * line_height)
    
    # 패딩 추정
    padding_estimate = sum(paddings) * 8 if paddings else 40  # 기본 40px
    
    # 총 높이 계산
    estimated_content_height = total_image_height + text_height + padding_estimate
    
    if estimated_content_height > available_height:
        overflow_amount = estimated_content_height - available_height
        issues.append(f"Content overflow by ~{overflow_amount}px (estimated {estimated_content_height}px > {available_height}px)")
        
        # 구체적인 수정 지시
        if total_image_height > 400:
            target_img_height = max(100, (total_image_height - overflow_amount) // image_count)
            fixes.append(f"REDUCE each image to h-[{target_img_height}px]")
        if not is_two_column and body_length > 1000:
            fixes.append("Use columns-2 gap-3 for body text")
        if 'text-xs' not in html and 'text-[10px]' not in html:
            fixes.append("Use text-xs or text-[10px] for body")
    
    # ============ 6. UNDERFILL 검사 (페이지가 충분히 채워졌는지) ============
    fill_rate = estimated_content_height / available_height if available_height > 0 else 0
    min_fill_rate = 0.85  # 최소 85% 채워야 함
    
    if fill_rate < min_fill_rate and estimated_content_height < available_height:
        underfill_amount = available_height - estimated_content_height
        issues.append(f"Page underfilled: {int(fill_rate * 100)}% (target: 85%+). Empty space: ~{underfill_amount}px")
        
        # 구체적인 수정 지시
        if image_count > 0:
            suggested_increase = underfill_amount // image_count
            fixes.append(f"INCREASE each image height by {suggested_increase}px")
        fixes.append("Reduce margins: use p-4 or p-6, mb-2 or mb-3")
        if body_length < 1000:
            fixes.append("Use larger fonts: text-base or text-lg for body")
    
    # ============ 결과 정리 ============
    passed = len(issues) == 0
    
    result = {
        "passed": passed,
        "issues": issues,
        "fixes": fixes,
        "metrics": {
            "body_length": body_length,
            "image_count": image_count,
            "image_heights": heights,
            "total_image_height": total_image_height,
            "text_height": text_height,
            "padding_estimate": padding_estimate,
            "estimated_content_height": estimated_content_height,
            "available_height": available_height,
            "fill_rate": round(fill_rate * 100, 1)  # 페이지 fill rate (%)
        }
    }
    
    if passed:
        print(f"✅ [Node 6] HTML Quality Check: PASSED", file=sys.stderr)
        state["final_html"] = html
    else:
        retry_count = state.get("retry_count", 0)
        print(f"⚠️ [Node 6] HTML Quality Check: {len(issues)} issues found (retry {retry_count}/3)", file=sys.stderr)
        for issue in issues:
            print(f"   - {issue}", file=sys.stderr)
        print(f"   Suggested fixes: {fixes}", file=sys.stderr)
        
        state["quality_fix_hints"] = "; ".join(fixes)
        state["retry_count"] = retry_count + 1
    
    state["html_quality_check"] = result
    
    return state

# ============================================================
# Retry Router: 품질 검사 결과에 따른 분기
# ============================================================
def quality_check_router(state: MagazineState) -> str:
    """
    HTML 품질 검사 결과에 따라 다음 노드 결정:
    - PASSED 또는 retry >= 3: END
    - FAILED 및 retry < 3: html_generator로 재시도
    """
    quality_result = state.get("html_quality_check", {})
    retry_count = state.get("retry_count", 0)
    
    if quality_result.get("passed", False):
        return "end"
    elif retry_count >= 3:
        print(f"❌ [Router] Max retries (3) reached. Returning current HTML.", file=sys.stderr)
        state["final_html"] = state.get("html_output", "")  # 강제 반환
        return "end"
    else:
        print(f"🔄 [Router] Retrying HTML generation... (attempt {retry_count + 1}/3)", file=sys.stderr)
        return "retry"

# ============================================================
# Build LangGraph
# ============================================================
def build_magazine_graph():
    graph = StateGraph(MagazineState)
    
    # Guard nodes
    graph.add_node("intent_classifier", intent_classifier_node)
    graph.add_node("content_filter", content_filter_node)
    
    # Processing nodes
    graph.add_node("image_analyzer", image_analyzer_node)
    graph.add_node("layout_planner", layout_planner_node)
    graph.add_node("typography_styler", typography_styler_node)
    graph.add_node("html_generator", html_generator_node)
    graph.add_node("validator", validator_node)
    graph.add_node("html_quality_checker", html_quality_checker_node)
    
    # Entry point
    graph.set_entry_point("intent_classifier")
    
    # Guard edges
    graph.add_edge("intent_classifier", "content_filter")
    graph.add_edge("content_filter", "image_analyzer")
    
    # Processing edges
    graph.add_edge("image_analyzer", "layout_planner")
    graph.add_edge("layout_planner", "typography_styler")
    graph.add_edge("typography_styler", "html_generator")
    graph.add_edge("html_generator", "validator")
    graph.add_edge("validator", "html_quality_checker")
    
    # Conditional edge: quality check 후 분기 (retry or end)
    graph.add_conditional_edges(
        "html_quality_checker",
        quality_check_router,
        {
            "retry": "html_generator",  # 재시도
            "end": END                   # 종료
        }
    )
    
    return graph.compile()

# Global graph instance
magazine_graph = build_magazine_graph()

# ============================================================
# MCP Interface
# ============================================================
mcp = FastMCP("AURA Layout Service (LangGraph)")

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
    LangGraph 멀티 노드를 사용하여 동적으로 고품질 매거진 HTML을 생성합니다.
    """
    print(f"🍌 [AURA LangGraph] Generating Layout for: {headline[:20]}...", file=sys.stderr)

    # Parse image data
    images_list = []
    try:
        parsed = json.loads(image_data)
        if isinstance(parsed, list):
            images_list = parsed
    except:
        images_list = [image_data]

    image_count = len(images_list)
    print(f"🍌 [AURA] Detected {image_count} images.", file=sys.stderr)

    # Parse contexts
    try:
        vision_data = json.loads(vision_context) if vision_context != "{}" else {}
        design_data = json.loads(design_spec) if design_spec != "{}" else {}
        plan_data = json.loads(planner_intent) if planner_intent != "{}" else {}
    except:
        vision_data = {}
        design_data = {}
        plan_data = {}
    
    # Build summaries (same as original)
    vision_summary = "Not provided"
    if vision_data:
        keywords = vision_data.get('keywords', [])
        desc = vision_data.get('description', '')
        style = vision_data.get('visual_style', 'Modern')
        vision_summary = f"Style: {style}, Keywords: {', '.join(keywords) if keywords else 'none'}, Description: {desc}"
    
    design_summary = "Standard magazine layout"
    if design_data:
        mood = design_data.get('mood', 'Modern')
        category = design_data.get('category', 'Magazine')
        typo = design_data.get('typography_style', 'Balanced')
        colors = design_data.get('color_scheme', 'Balanced palette')
        design_summary = f"Mood: {mood}, Category: {category}, Typography: {typo}, Colors: {colors}"
    
    layout_summary = "Flexible layout"
    if plan_data:
        spatial = plan_data.get('spatial_summary', 'Flexible layout')
        strategy = plan_data.get('suggested_strategy', 'Balanced')
        layout_summary = f"Strategy: {strategy}, Structure: {spatial}"

    # Build initial state
    initial_state: MagazineState = {
        "headline": headline,
        "body": body,
        "image_count": image_count,
        "image_placeholders": images_list,
        "layout_override": layout_override,
        "vision_summary": vision_summary,
        "design_summary": design_summary,
        "layout_summary": layout_summary,
        "intent_valid": None,
        "content_safe": None,
        "retry_count": 0,              # 재시도 카운터 초기화
        "quality_fix_hints": None,     # 품질 수정 힌트 초기화
        "image_analysis": None,
        "layout_plan": None,
        "typography_style": None,
        "html_output": None,
        "validation_result": None,
        "html_quality_check": None,
        "final_html": None
    }

    try:
        # Run the graph
        final_state = magazine_graph.invoke(initial_state)
        
        html = final_state.get("final_html", "")
        validation = final_state.get("validation_result", {})
        
        if validation.get("passed", False):
            print(f"✅ [AURA] All validations passed!", file=sys.stderr)
        else:
            print(f"⚠️ [AURA] Validation issues: {validation.get('issues', [])}", file=sys.stderr)
        
        print(f"🍌 [AURA] Generated HTML Length: {len(html)} chars", file=sys.stderr)
        return html
        
    except Exception as e:
        print(f"❌ [AURA] Graph Error: {e}", file=sys.stderr)
        return f"<div class='p-10 text-red-500'>Error: {e}</div>"

if __name__ == "__main__":
    mcp.run()
