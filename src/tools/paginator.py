# src/tools/paginator.py
import math
from typing import List, Dict

def organize_articles_into_pages(articles: List[Dict]) -> List[Dict]:
    """
    [Input Expectation]
    - articles: List[Dict] - Each dict must have 'body', 'caption', etc.
    - Note: Caller (main.py's run_paginator_node) should convert Dict[id, article] to List[article]
    
    [기능]
    여러 개의 기사(Article)를 입력받아, '페이지(Page)' 단위로 묶어줍니다.
    각 페이지에 어떤 레이아웃을 쓸지(layout_hint)도 결정합니다.

    [알고리즘: First Fit / Bin Packing]
    페이지 용량(100)이 찰 때까지 기사를 담고, 넘치면 새 페이지를 만듭니다.
    """
    
    # ✨ [New] 입력 타입 검증
    if not isinstance(articles, list):
        print(f"⚠️ Paginator expects List, got {type(articles)}")
        return []
        
    # [Pre-processing] 긴 기사 분할 (Smart Splitting)
    # A4 한 페이지에 이미지가 있을 때 안전한 글자 수는 약 800~1000자입니다.
    # 하지만 사용자는 '한 페이지 완결'을 선호하므로, 한계치(1100/2200)까지 꽉 채웁니다.
    SAFE_LIMIT_WITH_IMAGE = 1100 
    SAFE_LIMIT_TEXT_ONLY = 2200
    
    normalized_articles = []
    
    for art in articles:
        # [Fix 1] 데이터 추출 경로 수정
        manuscript = art.get("manuscript", {})
        body_text = manuscript.get("body") or art.get("body", "")
        
        # [Adaptive Layout] 2800자(A4 Safe)까지는 한 페이지 수용
        SAFE_LIMIT_WITH_IMAGE = 2800
        SAFE_LIMIT_TEXT_ONLY = 2800
        
        limit = SAFE_LIMIT_WITH_IMAGE
        text_len = len(body_text)
        
        if text_len <= limit:
            normalized_articles.append(art)
            continue
            
        print(f"✂️ Paginator: 기사 '{art.get('title')}' ({text_len}자) -> Balanced Splitting 적용")
        
        # [Balanced Splitting Logic]
        # 무조건 꽉 채우지 않고, N등분하여 균형 맞춤
        num_parts = math.ceil(text_len / limit)
        ideal_chunk_size = math.ceil(text_len / num_parts)
        
        chunks = []
        start = 0
        while start < text_len:
            end = min(start + ideal_chunk_size, text_len)
            
            # 문장 단위 끊기 (Tolerance 10% 허용)
            if end < text_len:
                search_end = min(text_len, end + 100) # 조금 더 뒤까지 봐서 마침표 찾기
                last_period = body_text.rfind('.', start, search_end)
                
                if last_period != -1 and last_period > start + (ideal_chunk_size * 0.7):
                    end = last_period + 1
            
            chunks.append(body_text[start:end].strip())
            start = end
            
        # 분할된 기사 객체 생성
        base_id = art.get("id", "unknown")
        base_title = art.get("title", "Untitled")
        base_headline = manuscript.get("headline", base_title)
        
        for i, chunk in enumerate(chunks):
            new_art = art.copy()
            new_art["body"] = chunk
            new_art["id"] = f"{base_id}_part{i+1}"
            
            # manuscript 업데이트
            new_manuscript = manuscript.copy()
            new_manuscript["body"] = chunk
            
            if i == 0:
                # 첫 페이지: 기존 스타일 유지
                pass
            else:
                # 두 번째 페이지부터: 텍스트 전용 + 헤더 제거
                new_art["image_path"] = None 
                new_art["vision_analysis"] = {} 
                new_art["layout_override"] = "editorial_text_only" # Publisher 힌트
                
                new_art["title"] = f"{base_title} (Continued)"
                new_manuscript["headline"] = "" # 헤더 삭제 (본문 확보)
                new_manuscript["subhead"] = ""  # 소제목 삭제
            
            new_art["manuscript"] = new_manuscript
            normalized_articles.append(new_art)

    # 설정: 한 페이지가 감당할 수 있는 최대 무게
    MAX_PAGE_WEIGHT = 100 
    
    pages = []
    current_page_articles = []
    current_weight = 0

    for article in normalized_articles:
        # 1. 기사 무게 계산 (Weight Calculation)
        # - 이미지: 시각적 비중이 크므로 50점
        has_image = bool(article.get("image_path") or article.get("caption"))
        image_score = 50 if has_image else 0
        
        # - 텍스트: 20자당 1점 (보수적으로 잡아서 페이지 넘김 유도)
        text_len = len(article.get("body", ""))
        text_score = min(80, math.ceil(text_len / 20)) # 상한선 높임
        
        item_weight = image_score + text_score
        
        # 기사가 하나인데 100점을 넘으면? -> 강제로 100점으로 보정
        if item_weight > MAX_PAGE_WEIGHT:
            item_weight = MAX_PAGE_WEIGHT

        # 2. 페이지 배치 로직 (Bin Packing)
        if current_weight + item_weight > MAX_PAGE_WEIGHT:
            # (A) 기존 페이지 마감 & 저장
            if current_page_articles:
                pages.append(_create_page_object(current_page_articles))
            
            # (B) 새 페이지 시작
            current_page_articles = [article]
            current_weight = item_weight
        else:
            # (C) 현재 페이지에 추가
            current_page_articles.append(article)
            current_weight += item_weight

    # 3. 마지막 남은 페이지 처리
    if current_page_articles:
        pages.append(_create_page_object(current_page_articles))

    return pages

def _create_page_object(articles: List[Dict]) -> Dict:
    """
    기사 목록을 받아서 '페이지 객체'와 '레이아웃 힌트'를 생성함.
    Director는 이 'layout_type'을 보고 디자인을 결정함.
    """
    count = len(articles)
    layout_type = "hero_single" # 기본값

    # 기사 개수에 따른 레이아웃 전략 결정
    if count == 1:
        layout_type = "hero_single"  # 기사 1개: 꽉 채운 디자인 (우리가 여태 했던 것)
    elif count == 2:
        layout_type = "split_half"   # 기사 2개: 좌우 또는 상하 분할
    elif count == 3:
        layout_type = "magazine_grid_3" # 기사 3개: 잡지식 그리드
    else:
        layout_type = "multi_column_list" # 4개 이상: 목록형 디자인

    return {
        "articles": articles,      # 이 페이지에 들어갈 기사들
        "article_count": count,    # 기사 개수
        "layout_type": layout_type # Director에게 주는 힌트
    }