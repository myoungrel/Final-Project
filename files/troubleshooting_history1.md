# 🛠️ Troubleshooting History Log

> **프로젝트**: AI Magazine Layout Generator (MCP + LangGraph)  
> **기간**: 2026-01-13 ~ 2026-01-14  
> **문서 목적**: PPT 발표 자료용 트러블슈팅 기록

---

## 📋 목차

| # | 이슈 | 심각도 | 상태 |
|---|------|--------|------|
| 1 | [콘텐츠 겹침 (Overlap) 문제](#issue-1-콘텐츠-겹침-overlap-문제) | 🔴 Critical | ✅ 해결 |
| 2 | [하단 여백 누락 및 텍스트 잘림](#issue-2-하단-여백-누락-및-텍스트-잘림) | 🟠 High | ✅ 해결 |
| 3 | [멀티노드 아키텍처 전환](#issue-3-멀티노드-langgraph-아키텍처-전환) | 🟡 Medium | ✅ 해결 |
| 4 | [Layout Planner 잘못된 레이아웃 선택](#issue-4-layout-planner-잘못된-레이아웃-선택) | 🟠 High | ✅ 해결 |
| 5 | [LangGraph 프롬프트 누락](#issue-5-langgraph-프롬프트-누락) | 🟠 High | ✅ 해결 |
| 6 | [Pinterest 데이터셋 형식 불일치](#issue-6-pinterest-데이터셋-형식-불일치) | 🟡 Medium | ✅ 해결 |
| 7 | [Gemini Vision 레이아웃 분석 파이프라인](#issue-7-gemini-vision-레이아웃-분석-파이프라인) | 🟡 Medium | ✅ 해결 |
| 8 | [이미지 Placeholder 누락](#issue-8-이미지-placeholder-누락) | 🔴 Critical | ✅ 해결 |

---

## Issue #1: 콘텐츠 겹침 (Overlap) 문제

### 📌 이슈 요약
생성된 레이아웃에서 텍스트-텍스트, 텍스트-이미지, 이미지-이미지 간 겹침이 발생하여 가독성 저하

### 📋 발생 상황 & 에러 로그
```
문제 현상:
- 헤드라인과 본문 텍스트가 겹쳐서 읽을 수 없음
- 이미지 위에 텍스트가 overlay 없이 직접 배치됨
- absolute 포지셔닝 과다 사용으로 요소 간 충돌
```

### 🔍 원인 분석
1. **프롬프트에 NO OVERLAP 규칙 부재**: LLM이 겹침 방지에 대한 명시적 지침 없이 자유롭게 배치
2. **absolute 포지셔닝 남용**: 상대 위치 계산 없이 절대 위치 사용
3. **자기 검증 단계 누락**: 생성 후 겹침 여부를 체크하는 로직 없음

### ✅ 해결 과정 & 변경점

**Before** (규칙 없음):
```
[DESIGN GUIDELINES]
- Typography...
- Visual Style...
```

**After** (ABSOLUTE RULE #5 추가):
```python
5. **NO OVERLAP - READABILITY IS #1 PRIORITY** (CRITICAL):
   - ❌ NEVER let text overlap with other text
   - ❌ NEVER let text overlap with images
   - ❌ NEVER let images overlap with other images
   - ⚠️ Avoid `absolute` positioning unless necessary
   - Use `relative` + `flex` or `grid` layouts
   - **TEST**: Can every text block be read clearly?
```

**SELF-VALIDATION 체크리스트 추가**:
```python
✅ Checklist:
0. 🔴 **NO OVERLAP**: Text-text, text-image, image-image - ZERO overlap!
1. Are ALL images included?
...
```

### 💡 배운 점
- LLM은 명시적으로 금지하지 않으면 시각적 겹침을 허용함
- **"하지 마라"를 명확히 말해야** LLM이 따름
- 자기 검증 단계를 프롬프트에 포함시키면 품질 향상

---

## Issue #2: 하단 여백 누락 및 텍스트 잘림

### 📌 이슈 요약
A4 레이아웃 하단에 여백이 없고, 본문 텍스트가 페이지 끝에서 잘림

### 📋 발생 상황 & 에러 로그
```
관찰된 문제:
- 좌/우/상단은 p-8 여백 있음
- 하단만 콘텐츠가 페이지 끝까지 차지
- overflow-hidden으로 텍스트 절단됨
```

### 🔍 원인 분석
1. **pb (padding-bottom) 누락**: 전체 여백(p-8) 설정 시 하단만 별도 처리 필요
2. **overflow-hidden 적용**: 콘텐츠가 넘쳐도 보이지 않도록 숨김 처리됨
3. **텍스트 길이 대비 폰트 크기 부적절**: 긴 텍스트에 text-base 사용

### ✅ 해결 과정 & 변경점

**ABSOLUTE RULE #6 추가**:
```python
6. **PAGE MARGINS - ALL SIDES MUST HAVE PADDING** (CRITICAL):
   - Top: pt-8 or pt-10
   - Left/Right: pl-8, pr-8
   - **BOTTOM: pb-10 or pb-12** - content must NOT touch bottom!
   - Leave at least 40px at bottom for breathing room
```

**ABSOLUTE RULE #7 추가 (LangGraph)**:
```python
7. **TEXT MUST NOT BE TRUNCATED**:
   - SHOW ALL body text - do NOT cut it off
   - If text is long (1000+ chars), use text-sm
   - NEVER use overflow-hidden that cuts content
```

### 💡 배운 점
- `overflow-hidden`은 레이아웃 보호용이지만 콘텐츠 손실 유발 가능
- **긴 텍스트는 폰트 크기 자동 조절**이 필요
- 하단 여백은 별도로 강조해야 LLM이 준수함

---

## Issue #3: 멀티노드 (LangGraph) 아키텍처 전환

### 📌 이슈 요약
단일 거대 프롬프트(~500줄)를 역할별 5개 노드로 분리하여 유지보수성 및 품질 향상

### 📋 발생 상황 & 에러 로그
```
기존 구조의 문제:
- 단일 프롬프트 ~500줄 → 수정/디버깅 어려움
- 모든 규칙이 한 곳에 → 역할 구분 불명확
- 토큰 사용량 비효율
```

### 🔍 원인 분석
- 모놀리식 프롬프트는 규모가 커지면 관리 불가능

### ✅ 해결 과정 & 변경점

**아키텍처 설계**:
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Node 1    │ →  │   Node 2    │ →  │   Node 3    │
│ Image       │    │ Layout      │    │ Typography  │
│ Analyzer    │    │ Planner     │    │ Styler      │
└─────────────┘    └─────────────┘    └─────────────┘
                          ↓
┌─────────────┐    ┌─────────────┐
│   Node 5    │ ←  │   Node 4    │
│ Validator   │    │ HTML Gen    │
└─────────────┘    └─────────────┘
```

**구현 파일**:
- `mcp_server_single_prompt_backup.py` - 원본 백업
- `mcp_server_langgraph.py` - 새 멀티노드 버전

**전환 스위치** (.env):
```bash
# LangGraph 사용
MCP_SERVER_SCRIPT=/home/sauser/final/mcp_server_langgraph.py

# 롤백 (단일 프롬프트)
# MCP_SERVER_SCRIPT=/home/sauser/final/mcp_server.py
```

### 💡 배운 점
- **LangGraph StateGraph**로 노드 간 상태 전달 용이
- 각 노드는 단일 책임 → 디버깅 쉬움
- 백업 + 환경변수 스위치로 **안전한 롤백** 가능

---

## Issue #4: Layout Planner 잘못된 레이아웃 선택

### 📌 이슈 요약
ARTICLE 페이지인데 Layout Planner가 `hero` 레이아웃 선택

### 📋 발생 상황 & 에러 로그
```
📐 [Node 2] Layout Plan: hero  ← 문제!

예상: ARTICLE + 긴 본문 → float 레이아웃
실제: hero 레이아웃 (이미지 상단 고정)
```

### 🔍 원인 분석
1. **본문 길이 조건 LLM 위임**: 프로그래밍적 판단 없이 LLM이 자의적 결정
2. **규칙 명확성 부족**: 조건문 형태로 명시하지 않음

### ✅ 해결 과정 & 변경점

**After** (명확한 조건문 + 디버깅 로그):
```python
# 디버깅 로그 추가
print(f"📐 [Node 2] Input: page_type={layout_override}, 
      images={image_count}, body_len={body_length}")

# 프롬프트 조건 명확화
**IF page_type == "ARTICLE":**
  - IF body_length >= 200 AND body_length < 1000:
    → layout_type = "float"
  - IF body_length >= 1000 AND image_count >= 3:
    → layout_type = "multi-column"

# 프로그래밍적 폴백
else:
    if body_length >= 1000 and image_count >= 3:
        plan = {"layout_type": "multi-column"}
    else:
        plan = {"layout_type": "float"}
```

### 💡 배운 점
- **LLM 결정을 믿지 말고 검증해라**: 프로그래밍적 폴백 필수
- **디버깅 로그는 필수**: 입력값, 원본 응답, 최종 결정 모두 출력

---

## Issue #5: LangGraph 프롬프트 누락

### 📌 이슈 요약
멀티노드 전환 시 원본 프롬프트의 9개 주요 규칙이 누락됨

### 📋 발생 상황 & 에러 로그
```
비교 검수 결과:
- 포함됨: 14개 항목
- ❌ 누락됨: 9개 항목

누락 목록:
1. IMAGE-FIRST DESIGN STRATEGY
2. TEXT FLOW BETWEEN IMAGES
3. IMAGE SIZE FOR ARTICLE
4. MULTI-COLUMN WIDTH RULES
5. Visual Style (Vogue/GQ/Kinfolk)
6. Visual Interest
7. Spacing & Rhythm
8. CREATIVE FREEDOM
9. SELF-VALIDATION 체크리스트
```

### 🔍 원인 분석
- 수동 분리 과정에서 일부 규칙 누락
- 원본과 새 버전 간 체계적 비교 미실시

### ✅ 해결 과정 & 변경점
Node 4 HTML Generator에 누락된 9개 항목 모두 추가

### 💡 배운 점
- 리팩토링 시 **원본과 새 버전 diff 비교 필수**
- **100% 기능 동등성** 확인 후 전환

---

## Issue #6: Pinterest 데이터셋 형식 불일치

### 📌 이슈 요약
Pinterest 크롤링 데이터와 시스템 데이터 스키마 불일치

### 📋 발생 상황 & 에러 로그
```json
// Pinterest 데이터 (새 형식)
{"id": "pin_xxx", "keywords": [...], "css_style": {...}}

// 시스템 기대 형식
{"image_id": "...", "elements": [...], "mood": "..."}
```

### 🔍 원인 분석
- Pinterest 데이터는 `elements[]` (좌표 정보) 없음
- 필드명 불일치 (`id` vs `image_id`)

### ✅ 해결 과정 & 변경점
- 변환 가이드 문서 작성
- Gemini Vision으로 elements 자동 생성

### 💡 배운 점
- 외부 데이터 통합 전 **스키마 매핑 테이블** 작성
- 누락 필드는 **AI Vision으로 자동 생성** 가능

---

## Issue #7: Gemini Vision 레이아웃 분석 파이프라인

### 📌 이슈 요약
122개 Pinterest 이미지에서 레이아웃 좌표를 자동 추출

### 📋 발생 상황 & 에러 로그
```
요구사항:
- image_data/ 폴더의 122개 이미지 처리
- Single/Double Page 자동 분류
- elements[] 좌표 추출
```

### ✅ 해결 과정 & 변경점
```python
# scripts/generate_dataset.py
def analyze_layout(image_path):
    model = genai.GenerativeModel("gemini-2.5-flash")
    # Vision API로 좌표 추출
    
# Rate Limit 처리
if (i + 1) % 10 == 0:
    time.sleep(2.0)
```

**실행 결과**: 148개 pages, 147 성공, 1 에러

### 💡 배운 점
- **Gemini Vision은 bounding box 추출 가능**
- Rate Limit 대응: 배치 + delay 필수
- Double Page 자동 분할: `aspect_ratio > 1.2`

---

## Issue #8: 이미지 Placeholder 누락

### 📌 이슈 요약
LangGraph HTML Generator가 `__IMAGE_X__` placeholder 대신 다른 src 값 사용

### 📋 발생 상황 & 에러 로그
```
⚠️ [Image 0] No placeholder found! Forcing injection...
⚠️ [Image 1] No placeholder found! Forcing injection...
```

### 🔍 원인 분석
- `{image_placeholders}` 리스트를 LLM이 src로 직접 사용 시도
- `__IMAGE_X__` 패턴 명시적 지정 없음

### ✅ 해결 과정 & 변경점

**Before**:
```python
- Use these EXACT placeholders: {image_placeholders}
```

**After**:
```python
1. **IMAGE COUNT - MANDATORY** (MOST CRITICAL RULE):
   - ⚠️ YOU MUST USE THESE EXACT src VALUES:
     __IMAGE_0__, __IMAGE_1__, __IMAGE_2__, __IMAGE_3__, __IMAGE_4__
   - Example: <img src="__IMAGE_0__" class="..." />
   - ⚠️ FAILURE TO USE __IMAGE_X__ WILL BREAK THE SYSTEM
```

### 💡 배운 점
- LLM은 **리스트를 그대로 사용하지 않음** → 명시적 나열 필요
- 중요한 패턴은 **예시와 함께 반복 강조**

---

## 📊 요약 통계

| 분류 | 이슈 수 |
|------|---------|
| 프롬프트 엔지니어링 | 5 |
| 아키텍처 설계 | 1 |
| 데이터 파이프라인 | 2 |
| **총합** | **8** |

---

## 🎯 핵심 교훈

1. **LLM은 명시적 지시가 필요하다**: "하지 마라"를 말하지 않으면 허용됨
2. **디버깅 로그는 기본**: 입력, 중간, 출력 모두 로깅
3. **프로그래밍적 폴백 필수**: LLM 결과를 100% 신뢰하지 말 것
4. **리팩토링 시 diff 비교**: 기능 동등성 검증 필수
5. **외부 데이터 통합 전 스키마 분석**: 매핑 테이블 작성

---

*문서 생성: 2026-01-14*
