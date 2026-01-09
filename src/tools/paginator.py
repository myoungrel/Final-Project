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
    
    # 설정: 한 페이지가 감당할 수 있는 최대 무게
    MAX_PAGE_WEIGHT = 100 
    
    pages = []
    current_page_articles = []
    current_weight = 0

    for article in articles:
        # 1. 기사 무게 계산 (Weight Calculation)
        # - 이미지: 시각적 비중이 크므로 50점 (캡션만 있어도 이미지 공간 확보 필요)
        has_image = bool(article.get("image_path") or article.get("caption"))
        image_score = 50 if has_image else 0
        
        # - 텍스트: 20자당 1점 (예: 1000자 = 50점) -> 긴 글은 혼자 한 페이지 차지하게 유도
        text_len = len(article.get("body", ""))
        text_score = min(50, math.ceil(text_len / 20)) 
        
        item_weight = image_score + text_score
        
        # 기사가 하나인데 100점을 넘으면? -> 강제로 100점으로 보정 (한 페이지 꽉 채움)
        if item_weight > MAX_PAGE_WEIGHT:
            item_weight = MAX_PAGE_WEIGHT

        # 2. 페이지 배치 로직 (Bin Packing)
        # 현재 페이지에 담을 수 있으면 담고, 아니면 페이지 넘김
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