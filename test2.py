"""
AI Magazine Publisher - Professional Multi-Page Magazine Layout Generator
실제 잡지와 같은 여러 페이지 레이아웃 자동 생성 시스템
"""

import streamlit as st
import base64
import io
import json
import re
from typing import TypedDict, List, Dict, Any, Annotated
from PIL import Image
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
import operator

# ============================================================================
# State Definition
# ============================================================================

class MagazineState(TypedDict):
    """LangGraph 워크플로우 상태 정의"""
    raw_text: str
    images: List[Any]
    category: str
    api_key: str  # API Key를 state에 포함
    safety_status: bool
    vision_results: Annotated[List[Dict], operator.add]
    structured_content: Dict
    design_plan: Dict
    final_html: str
    feedback: str
    retry_count: int

# ============================================================================
# Helper Functions
# ============================================================================

def get_image_base64(image: Image.Image) -> str:
    """PIL Image를 Base64 문자열로 변환"""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def get_aspect_ratio(image: Image.Image) -> str:
    """이미지 비율 판단"""
    w, h = image.size
    ratio = w / h
    if ratio > 1.2:
        return "landscape"
    elif ratio < 0.8:
        return "portrait"
    return "square"

def split_text_into_pages(paragraphs: List[str], chars_per_page: int = 2500) -> List[List[str]]:
    """텍스트를 페이지별로 분할"""
    if not paragraphs:
        return [["내용이 없습니다."]]
    
    # 빈 문단 제거
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    
    if not paragraphs:
        return [["내용이 없습니다."]]
    
    pages = []
    current_page = []
    current_length = 0
    
    for para in paragraphs:
        para_length = len(para)
        if current_length + para_length > chars_per_page and current_page:
            pages.append(current_page)
            current_page = [para]
            current_length = para_length
        else:
            current_page.append(para)
            current_length += para_length
    
    if current_page:
        pages.append(current_page)
    
    return pages if pages else [["내용이 없습니다."]]

# ============================================================================
# LangGraph Nodes
# ============================================================================

def safety_filter_node(state: MagazineState) -> Dict:
    """(1) Safety Filter"""
    unsafe_keywords = ["폭력", "혐오", "불법"]
    text = state["raw_text"].lower()
    is_safe = not any(keyword in text for keyword in unsafe_keywords)
    
    return {
        "safety_status": is_safe,
        "feedback": "⚠️ 콘텐츠가 안전 기준을 통과하지 못했습니다." if not is_safe else ""
    }

def vision_agent_node(state: MagazineState) -> Dict:
    """(2) Vision Agent"""
    # Streamlit context 없이 실행 가능하도록 state에서 직접 가져오기
    api_key = state.get("api_key", "")
    if not api_key or not state["images"]:
        return {"vision_results": []}
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        google_api_key=api_key,
        temperature=0.3
    )
    
    vision_results = []
    for idx, img in enumerate(state["images"]):
        aspect = get_aspect_ratio(img)
        try:
            img_base64 = get_image_base64(img)
            messages = [
                HumanMessage(content=[
                    {"type": "text", "text": "이 이미지의 주요 색상을 Hex code 형태로 하나만 반환하세요. 형식: #RRGGBB"},
                    {"type": "image_url", "image_url": f"data:image/png;base64,{img_base64}"}
                ])
            ]
            response = llm.invoke(messages)
            color_match = re.search(r'#[0-9A-Fa-f]{6}', response.content)
            primary_color = color_match.group(0) if color_match else "#2C3E50"
        except:
            primary_color = "#2C3E50"
        
        vision_results.append({
            "index": idx,
            "aspect_ratio": aspect,
            "primary_color": primary_color
        })
    
    return {"vision_results": vision_results}

def editor_agent_node(state: MagazineState) -> Dict:
    """(3) Editor Agent - NO REWRITING"""
    # Streamlit context 없이 실행 가능하도록
    api_key = state.get("api_key", "")
    if not api_key:
        return {"structured_content": {}}
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        google_api_key=api_key,
        temperature=0.1
    )
    
    prompt = f"""당신은 잡지 에디터입니다. 아래 원고를 구조화하세요.

**절대 규칙: 원문을 수정하거나 다시 쓰지 마세요. 원문 그대로 사용하세요.**

원고:
{state["raw_text"]}

다음 JSON 형식으로만 응답하세요:
{{
  "section": "섹션명 (예: Science, Politics, Health)",
  "headline": "원문에서 추출한 제목",
  "subhead": "원문에서 추출한 부제",
  "byline": "저자명 (있다면)",
  "deck": "원문에서 추출한 리드 문단",
  "body": ["원문 문단1", "원문 문단2", ...],
  "pull_quote": "원문에서 인용할 만한 문장",
  "caption": "이미지 캡션 (원문에 있다면)"
}}

JSON만 출력하세요."""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            structured = json.loads(json_match.group(0))
        else:
            lines = [l for l in state["raw_text"].split('\n') if l.strip()]
            structured = {
                "section": state.get("category", "Article"),
                "headline": lines[0] if lines else "Untitled",
                "subhead": lines[1] if len(lines) > 1 else "",
                "byline": "",
                "deck": lines[2] if len(lines) > 2 else "",
                "body": lines[3:] if len(lines) > 3 else [],
                "pull_quote": "",
                "caption": ""
            }
        return {"structured_content": structured}
    except:
        lines = [l for l in state["raw_text"].split('\n') if l.strip()]
        return {
            "structured_content": {
                "section": state.get("category", "Article"),
                "headline": lines[0] if lines else "Untitled",
                "subhead": "",
                "byline": "",
                "deck": "",
                "body": lines[1:] if len(lines) > 1 else [],
                "pull_quote": "",
                "caption": ""
            }
        }

def art_director_node(state: MagazineState) -> Dict:
    """(4) Art Director"""
    num_images = len(state["images"])
    text_length = len(state["raw_text"])
    vision_results = state.get("vision_results", [])
    
    # 레이아웃 결정
    if num_images >= 3:
        layout_id = "magazine_feature_story"  # Image 1 스타일
    elif num_images == 1:
        aspect = vision_results[0]["aspect_ratio"] if vision_results else "landscape"
        if aspect == "portrait":
            layout_id = "magazine_profile"  # Image 2 스타일 (세로 이미지)
        else:
            layout_id = "magazine_feature_story"  # 가로 이미지
    elif num_images >= 2:
        layout_id = "magazine_multi_topic"  # Image 3 스타일
    else:
        layout_id = "magazine_essay"
    
    # 카테고리별 컬러
    category_styles = {
        "SCIENCE": {"accent": "#0066CC", "secondary": "#E8F4F8"},
        "BEAUTY": {"accent": "#E63946", "secondary": "#FFE5E8"},
        "POLITICS": {"accent": "#1A1A1A", "secondary": "#F5F5F5"},
        "TECH": {"accent": "#00D9FF", "secondary": "#E0F7FF"},
        "FASHION": {"accent": "#FF006E", "secondary": "#FFE0F0"}
    }
    
    category = state.get("category", "SCIENCE")
    style = category_styles.get(category, category_styles["SCIENCE"])
    
    # 페이지 수 계산
    estimated_pages = max(1, (text_length // 2000) + (num_images // 2))
    
    return {
        "design_plan": {
            "layout_id": layout_id,
            "accent_color": style["accent"],
            "secondary_color": style["secondary"],
            "estimated_pages": estimated_pages,
            "column_count": 2 if text_length > 1000 else 1
        }
    }

def publisher_node(state: MagazineState) -> Dict:
    """(5) Publisher - Multi-Page Magazine Layout Generator"""
    
    # 데이터 준비
    plan = state.get("design_plan", {})
    content = state.get("structured_content", {})
    layout_id = plan.get("layout_id", "magazine_feature_story")
    
    # 디버깅: content 확인
    print(f"[DEBUG] Content: {content}")
    print(f"[DEBUG] Body paragraphs count: {len(content.get('body', []))}")
    
    # 이미지 Base64
    img_data = {}
    for idx, img in enumerate(state["images"]):
        img_data[f"img_{idx}"] = get_image_base64(img)
    
    # 텍스트 페이지 분할
    body_paragraphs = content.get("body", [])
    if not body_paragraphs:
        # body가 없으면 raw_text를 직접 사용
        body_paragraphs = [p.strip() for p in state["raw_text"].split('\n\n') if p.strip()]
    
    print(f"[DEBUG] Final body paragraphs: {body_paragraphs[:2]}")  # 첫 2개만 출력
    
    text_pages = split_text_into_pages(body_paragraphs, chars_per_page=2200)
    
    # 공통 스타일
    common_head = f"""
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=Inter:wght@300;400;500;600&display=swap');
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        .magazine-page {{
            width: 210mm;
            min-height: 297mm;
            margin: 0 auto;
            background: white;
            padding: 15mm;
            position: relative;
            page-break-after: always;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}
        
        @media print {{
            .magazine-page {{
                box-shadow: none;
                page-break-after: always;
            }}
        }}
        
        .section-header {{
            font-family: 'Inter', sans-serif;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            color: {plan.get('accent_color', '#000')};
            border-bottom: 2px solid {plan.get('accent_color', '#000')};
            padding-bottom: 8px;
            margin-bottom: 20px;
        }}
        
        .magazine-headline {{
            font-family: 'Playfair Display', serif;
            font-weight: 900;
            line-height: 1.1;
            margin-bottom: 16px;
            color: #1a1a1a;
        }}
        
        .magazine-deck {{
            font-family: 'Inter', sans-serif;
            font-size: 18px;
            line-height: 1.6;
            color: #4a4a4a;
            margin-bottom: 24px;
            font-weight: 400;
        }}
        
        .magazine-byline {{
            font-family: 'Inter', sans-serif;
            font-size: 13px;
            color: #666;
            margin-bottom: 24px;
            font-style: italic;
        }}
        
        .two-column {{
            column-count: 2;
            column-gap: 20mm;
            text-align: justify;
        }}
        
        .magazine-body {{
            font-family: 'Inter', sans-serif;
            font-size: 11pt;
            line-height: 1.7;
            color: #2c2c2c;
        }}
        
        .magazine-body p {{
            margin-bottom: 14px;
        }}
        
        .drop-cap::first-letter {{
            float: left;
            font-family: 'Playfair Display', serif;
            font-size: 72px;
            line-height: 60px;
            padding-right: 8px;
            margin-top: 4px;
            font-weight: 700;
            color: {plan.get('accent_color', '#000')};
        }}
        
        .pull-quote {{
            font-family: 'Playfair Display', serif;
            font-size: 24px;
            line-height: 1.4;
            font-weight: 700;
            color: {plan.get('accent_color', '#000')};
            border-left: 4px solid {plan.get('accent_color', '#000')};
            padding: 20px 0 20px 24px;
            margin: 30px 0;
            font-style: italic;
        }}
        
        .page-number {{
            position: absolute;
            bottom: 10mm;
            font-family: 'Inter', sans-serif;
            font-size: 10px;
            color: #999;
        }}
        
        .image-caption {{
            font-family: 'Inter', sans-serif;
            font-size: 9px;
            color: #666;
            margin-top: 8px;
            line-height: 1.4;
        }}
        
        .info-box {{
            background: {plan.get('secondary_color', '#f5f5f5')};
            padding: 20px;
            border-left: 3px solid {plan.get('accent_color', '#000')};
            margin: 24px 0;
            font-size: 10pt;
        }}
    </style>
"""
    
    # ========== 레이아웃 1: Feature Story (Image 1 스타일) ==========
    if layout_id == "magazine_feature_story":
        pages_html = []
        
        # 첫 페이지: 히어로 이미지 + 제목 + 첫 단락
        first_page = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <title>{content.get('headline', 'Article')}</title>
    {common_head}
</head>
<body style="background: #f8f8f8; padding: 20px 0;">
    <div class="magazine-page">
        <div class="section-header">{content.get('section', state.get('category', 'Article'))}</div>
        
        <!-- Hero Image -->
        <div style="margin: 0 -15mm 24px -15mm;">
            <img src="data:image/png;base64,{img_data.get('img_0', '')}" 
                 style="width: 100%; height: 180mm; object-fit: cover;">
            {f'<div class="image-caption" style="padding: 0 15mm;">{content.get("caption", "")}</div>' if content.get('caption') else ''}
        </div>
        
        <!-- Headline -->
        <h1 class="magazine-headline" style="font-size: 48px;">
            {content.get('headline', 'Untitled')}
        </h1>
        
        {f'<h2 class="magazine-headline" style="font-size: 24px; font-weight: 400; margin-top: -8px;">{content.get("subhead", "")}</h2>' if content.get('subhead') else ''}
        
        {f'<div class="magazine-byline">By {content.get("byline", "")}</div>' if content.get('byline') else ''}
        
        <!-- Deck -->
        {f'<div class="magazine-deck">{content.get("deck", "")}</div>' if content.get('deck') else ''}
        
        <!-- First paragraphs -->
        <div class="two-column magazine-body">
            <div class="drop-cap">
                {"".join([f"<p>{p}</p>" for p in (text_pages[0] if text_pages else ["내용이 없습니다."])])}
            </div>
        </div>
        
        <div class="page-number" style="right: 10mm;">52</div>
    </div>
"""
        
        # 추가 이미지들을 하단에 그리드로 배치 (Image 1의 Science Briefs 스타일)
        if len(state["images"]) > 1:
            briefs_html = '<div style="margin-top: 30px;"><div style="background: #DC2626; color: white; display: inline-block; padding: 6px 16px; font-family: Inter; font-size: 11px; font-weight: 700; margin-bottom: 16px;">Science Briefs</div><div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;">'
            
            for idx in range(1, min(5, len(state["images"]))):
                briefs_html += f"""
                <div>
                    <img src="data:image/png;base64,{img_data.get(f'img_{idx}', '')}" 
                         style="width: 100%; height: 80px; object-fit: cover; border-radius: 4px;">
                    <div style="font-family: Playfair Display; font-weight: 700; font-size: 14px; margin-top: 8px;">Topic {idx}</div>
                    <div style="font-family: Inter; font-size: 9px; line-height: 1.4; color: #666; margin-top: 4px;">Brief description of the topic.</div>
                </div>
                """
            
            briefs_html += '</div></div>'
            first_page += briefs_html
        
        first_page += "</body></html>"
        pages_html.append(first_page)
        
        # 후속 페이지들
        for page_idx, page_paras in enumerate(text_pages[1:], start=2):
            page_html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <title>{content.get('headline', 'Article')} - Page {page_idx}</title>
    {common_head}
</head>
<body style="background: #f8f8f8; padding: 20px 0;">
    <div class="magazine-page">
        <div class="section-header">{content.get('section', 'Continued')}</div>
        
        <div class="two-column magazine-body">
            {"".join([f"<p>{p}</p>" for p in page_paras])}
        </div>
        
        {f'<div class="pull-quote">"{content.get("pull_quote", "")}"</div>' if content.get('pull_quote') and page_idx == 2 else ''}
        
        <div class="page-number" style="right: 10mm;">{52 + page_idx - 1}</div>
    </div>
</body>
</html>
"""
            pages_html.append(page_html)
        
        final_html = "\n".join(pages_html)
    
    # ========== 레이아웃 2: Profile/Long-form (Image 2 스타일) ==========
    elif layout_id == "magazine_profile":
        pages_html = []
        
        first_page = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <title>{content.get('headline', 'Article')}</title>
    {common_head}
</head>
<body style="background: #f8f8f8; padding: 20px 0;">
    <div class="magazine-page">
        <div class="section-header">{content.get('section', state.get('category', 'Article'))}</div>
        
        <!-- Full Bleed Hero -->
        <div style="margin: 20px -15mm 32px -15mm;">
            <img src="data:image/png;base64,{img_data.get('img_0', '')}" 
                 style="width: 100%; height: 200mm; object-fit: cover;">
        </div>
        
        <div class="page-number" style="right: 10mm;">50</div>
    </div>
</body>
</html>
"""
        pages_html.append(first_page)
        
        # 두 번째 페이지: 제목 + 본문
        second_page = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <title>{content.get('headline', 'Article')} - Page 2</title>
    {common_head}
</head>
<body style="background: #f8f8f8; padding: 20px 0;">
    <div class="magazine-page">
        <div style="margin-bottom: 40px;">
            <div style="font-family: 'Inter', sans-serif; font-size: 11px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; color: #999; margin-bottom: 16px;">
                {content.get('section', 'PROFILE')}
            </div>
            <h1 class="magazine-headline" style="font-size: 52px; margin-bottom: 24px;">
                {content.get('headline', 'Untitled')}
            </h1>
        </div>
        
        <div class="magazine-body" style="column-count: 1;">
            <div class="drop-cap">
                {"".join([f"<p>{p}</p>" for p in text_pages[0][:4]])}
            </div>
        </div>
        
        <div class="page-number" style="right: 10mm;">51</div>
    </div>
</body>
</html>
"""
        pages_html.append(second_page)
        
        # 후속 페이지
        for page_idx, page_paras in enumerate(text_pages[1:], start=3):
            page_html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <title>{content.get('headline', 'Article')} - Page {page_idx}</title>
    {common_head}
</head>
<body style="background: #f8f8f8; padding: 20px 0;">
    <div class="magazine-page">
        <div class="magazine-body" style="column-count: 1;">
            {"".join([f"<p>{p}</p>" for p in page_paras])}
        </div>
        
        {f'<div class="pull-quote">"{content.get("pull_quote", "")}"</div>' if content.get('pull_quote') and page_idx == 3 else ''}
        
        <div class="page-number" style="right: 10mm;">{49 + page_idx}</div>
    </div>
</body>
</html>
"""
            pages_html.append(page_html)
        
        final_html = "\n".join(pages_html)
    
    # ========== 레이아웃 3: Multi-Topic (Image 3 스타일) ==========
    else:
        pages_html = []
        
        first_page = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <title>{content.get('headline', 'Article')}</title>
    {common_head}
</head>
<body style="background: #f8f8f8; padding: 20px 0;">
    <div class="magazine-page">
        <div class="section-header">{content.get('section', state.get('category', 'Article'))}</div>
        
        <!-- Two Column Layout with Sidebar -->
        <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 20mm;">
            <div>
                <h1 class="magazine-headline" style="font-size: 42px;">
                    {content.get('headline', 'Untitled')}
                </h1>
                
                {f'<div class="magazine-deck">{content.get("deck", "")}</div>' if content.get('deck') else ''}
                
                <div class="magazine-body drop-cap">
                    {"".join([f"<p>{p}</p>" for p in (text_pages[0][:3] if text_pages and len(text_pages[0]) >= 3 else text_pages[0] if text_pages else ["내용이 없습니다."])])}
                </div>
            </div>
            
            <div>
                <img src="data:image/png;base64,{img_data.get('img_0', '')}" 
                     style="width: 100%; height: 200px; object-fit: cover; border-radius: 4px;">
                {f'<div class="image-caption">{content.get("caption", "")}</div>' if content.get('caption') else ''}
                
                <div class="info-box" style="margin-top: 24px;">
                    <div style="font-weight: 600; margin-bottom: 12px;">Key Facts</div>
                    <div style="font-size: 9pt; line-height: 1.6;">
                        Additional context and related information.
                    </div>
                </div>
            </div>
        </div>
        
        <div class="page-number" style="right: 10mm;">51</div>
    </div>
</body>
</html>
"""
        pages_html.append(first_page)
        
        # 후속 페이지
        for page_idx, page_paras in enumerate(text_pages[1:], start=2):
            images_in_page = ""
            if page_idx == 2 and len(state["images"]) > 1:
                images_in_page = f"""
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 24px 0;">
                    <img src="data:image/png;base64,{img_data.get('img_1', '')}" 
                         style="width: 100%; height: 150px; object-fit: cover; border-radius: 4px;">
                    {f'<img src="data:image/png;base64,{img_data.get("img_2", "")}" style="width: 100%; height: 150px; object-fit: cover; border-radius: 4px;">' if len(state["images"]) > 2 else ''}
                </div>
                """
            
            page_html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <title>{content.get('headline', 'Article')} - Page {page_idx}</title>
    {common_head}
</head>
<body style="background: #f8f8f8; padding: 20px 0;">
    <div class="magazine-page">
        <div class="two-column magazine-body">
            {"".join([f"<p>{p}</p>" for p in page_paras])}
        </div>
        
        {images_in_page}
        
        <div class="page-number" style="right: 10mm;">{50 + page_idx}</div>
    </div>
</body>
</html>
"""
            pages_html.append(page_html)
        
        final_html = "\n".join(pages_html)
    
    return {"final_html": final_html}

def critique_node(state: MagazineState) -> Dict:
    """(6) Critique"""
    html = state.get("final_html", "")
    issues = []
    
    if "<h1" not in html:
        issues.append("제목 누락")
    
    expected_images = len(state["images"])
    actual_images = html.count("<img")
    
    if actual_images < expected_images:
        issues.append(f"이미지 누락 ({actual_images}/{expected_images})")
    
    if issues:
        return {
            "feedback": " | ".join(issues),
            "retry_count": state.get("retry_count", 0) + 1
        }
    return {"feedback": "✅ 검수 통과"}

# ============================================================================
# Conditional Edges
# ============================================================================

def should_continue_after_safety(state: MagazineState) -> str:
    if not state.get("safety_status", True):
        return "end"
    return "continue"

def should_retry_after_critique(state: MagazineState) -> str:
    if state.get("feedback") == "✅ 검수 통과":
        return "end"
    if state.get("retry_count", 0) >= 3:
        return "end"
    return "retry"

# ============================================================================
# Workflow
# ============================================================================

def create_magazine_workflow():
    workflow = StateGraph(MagazineState)
    
    workflow.add_node("safety_filter", safety_filter_node)
    workflow.add_node("vision_agent", vision_agent_node)
    workflow.add_node("editor_agent", editor_agent_node)
    workflow.add_node("art_director", art_director_node)
    workflow.add_node("publisher", publisher_node)
    workflow.add_node("critique", critique_node)
    
    workflow.set_entry_point("safety_filter")
    
    workflow.add_conditional_edges(
        "safety_filter",
        should_continue_after_safety,
        {"continue": "vision_agent", "end": END}
    )
    
    workflow.add_edge("safety_filter", "editor_agent")
    workflow.add_edge("vision_agent", "art_director")
    workflow.add_edge("editor_agent", "art_director")
    workflow.add_edge("art_director", "publisher")
    workflow.add_edge("publisher", "critique")
    
    workflow.add_conditional_edges(
        "critique",
        should_retry_after_critique,
        {"retry": "publisher", "end": END}
    )
    
    return workflow.compile()

# ============================================================================
# Streamlit UI
# ============================================================================

def main():
    st.set_page_config(
        page_title="AI Magazine Publisher",
        page_icon="📰",
        layout="wide"
    )
    
    st.title("📰 AI Magazine Publisher")
    st.markdown("**실제 잡지와 같은 프로페셔널 멀티-페이지 레이아웃 자동 생성**")
    
    with st.sidebar:
        st.header("⚙️ 설정")
        
        api_key = st.text_input(
            "Google API Key",
            type="password",
            help="Gemini API 키 입력"
        )
        st.session_state["api_key"] = api_key
        
        category = st.selectbox(
            "카테고리",
            ["SCIENCE", "BEAUTY", "POLITICS", "TECH", "FASHION"]
        )
        
        st.markdown("---")
        st.markdown("### 📐 레이아웃 스타일")
        st.markdown("""
        **자동 선택됨:**
        - Feature Story (히어로 + 2단)
        - Profile (풀 블리드 + 긴 텍스트)
        - Multi-Topic (그리드 레이아웃)
        """)
        
        st.markdown("---")
        st.info("💡 텍스트가 길면 자동으로 여러 페이지로 분할됩니다")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📄 원고 입력")
        raw_text = st.text_area(
            "완성된 원고를 입력하세요",
            height=350,
            placeholder="섹션: Science\n\n제목: Richard Thompson\n\n부제: A TIME 100 MOST INFLUENTIAL INNOVATOR\n\n본문: Marine biologist Richard Thompson..."
        )
        
        st.subheader("🖼️ 이미지 업로드")
        uploaded_files = st.file_uploader(
            "이미지를 업로드하세요 (1-5장)",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True
        )
        
        if uploaded_files:
            st.write(f"✅ {len(uploaded_files)}장 업로드됨")
            cols = st.columns(min(len(uploaded_files), 4))
            for idx, (col, file) in enumerate(zip(cols, uploaded_files[:4])):
                with col:
                    img = Image.open(file)
                    st.image(img, use_container_width=True)
    
    with col2:
        st.subheader("✨ 생성 결과")
        
        if st.button("🚀 매거진 생성", type="primary", use_container_width=True):
            if not api_key:
                st.error("API Key를 입력해주세요!")
                return
            
            if not raw_text:
                st.error("원고를 입력해주세요!")
                return
            
            images = [Image.open(f) for f in uploaded_files] if uploaded_files else []
            
            initial_state = {
                "raw_text": raw_text,
                "images": images,
                "category": category,
                "api_key": api_key,  # API Key를 state에 전달
                "safety_status": True,
                "vision_results": [],
                "structured_content": {},
                "design_plan": {},
                "final_html": "",
                "feedback": "",
                "retry_count": 0
            }
            
            with st.spinner("🔄 AI가 프로페셔널 매거진을 생성하고 있습니다..."):
                try:
                    workflow = create_magazine_workflow()
                    result = workflow.invoke(initial_state)
                    
                    if not result.get("safety_status", True):
                        st.error(result.get("feedback", "안전 검사 실패"))
                        return
                    
                    design_plan = result.get("design_plan", {})
                    st.success(f"✅ {design_plan.get('estimated_pages', 1)}페이지 매거진 생성 완료!")
                    
                    st.info(f"""
**레이아웃:** `{design_plan.get('layout_id', 'N/A')}`  
**컬럼:** {design_plan.get('column_count', 2)}단  
**페이지:** 약 {design_plan.get('estimated_pages', 1)}페이지
                    """)
                    
                    final_html = result.get("final_html", "")
                    if final_html:
                        with st.expander("🔍 매거진 미리보기", expanded=True):
                            st.components.v1.html(final_html, height=1200, scrolling=True)
                        
                        st.download_button(
                            label="📥 HTML 다운로드 (인쇄 가능)",
                            data=final_html,
                            file_name="magazine_multi_page.html",
                            mime="text/html",
                            use_container_width=True
                        )
                        
                        st.success("💡 다운로드 후 브라우저에서 열어 인쇄(Ctrl+P)하면 PDF로 저장 가능합니다!")
                    
                    with st.expander("🔧 디버그 정보"):
                        st.json({
                            "vision_results": result.get("vision_results", []),
                            "structured_content": result.get("structured_content", {}),
                            "design_plan": design_plan,
                            "feedback": result.get("feedback", "")
                        })
                
                except Exception as e:
                    st.error(f"오류 발생: {str(e)}")
                    st.exception(e)

if __name__ == "__main__":
    main()