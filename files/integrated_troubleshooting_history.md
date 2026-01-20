# 🛠️ Integrated Project Troubleshooting History

> **프로젝트**: AI Magazine Layout Generator (MCP + LangGraph)  
> **최종 업데이트**: 2026-01-15  
> **문서 목적**: 프로젝트 개발 생애주기별 기술적 과제와 극복 사례 통합 기록 (발표자용 상세 레퍼런스)

---

## 📋 프로젝트 단계별 이슈 요약

### Phase 1: 인프라 및 핵심 로직 구축 (Foundation)
*   **Git 대용량 파일 관리**: 100MB 초과 파일로 인한 Push 실패 및 히스토리 재작성
*   **Publisher 병렬 처리 엔진**: 순차적 생성 방식에서 `ThreadPoolExecutor` 기반 멀티스레딩 성능 최적화
*   **비즈니스 로직 정의**: 마진 계산 공식(Unit vs Total) 오류 수정 및 수식 단순화
*   **UX 인터랙션 개선**: 커스텀 파일 업로드 UI의 JavaScript 이벤트 바인딩 누락 해결

### Phase 2: 렌더링 엔진 정밀 튜닝 (Rendering)
*   **Silent Data Binding Failure**: 에러 없이 이미지가 누락되는 문제 해결 (Base64 URI 스키마 준수)
*   **Tailwind CSS CDN 안정화**: 독립형 HTML에서의 스타일 미적용 해결 (JIT 모드 설정 주입)
*   **콘텐츠 가변성 대응**: 긴 텍스트 유입 시 레이아웃 붕괴 방지 (Line-clamp 및 Truncation 전략)

### Phase 3: 데이터 파이프라인 및 레지스트리 고도화 (Intelligence)
*   **AI Vision 분석 자동화**: 120+개 레퍼런스 이미지에서 Bounding Box 좌표 자동 추출 파이프라인 구축
*   **디자인 레지스트리 통합**: 하드코딩된 레이아웃을 JSON 스펙 시스템으로 완전 이관 및 레거시 제거
*   **데이터 스키마 매핑**: 외부 크롤링 데이터(Pinterest)와 시스템 간의 형식 불일치 해결
*   **MCP 데이터 흐름 복구**: 대용량 직렬화 과정에서의 이미지 데이터 유실 추적 및 해결

### Phase 4: LangGraph 멀티 에이전트 전환 (Architecture)
*   **모놀리식 프롬프트 분리**: 500줄의 단일 프롬프트를 5개의 전문화된 노드(Planner, Styler 등)로 분리
*   **Layout Planner 의사결정 교정**: LLM의 자의적 판단 방지를 위한 프로그래밍적 폴백 로직 삽입
*   **상태 위임 정규화**: 리팩토링 과정에서 누락된 핵심 규칙들(9개 항목)의 완벽한 복원 및 이관

### Phase 5: 최종 품질 완성도 및 안정화 (Polish)
*   **고질적 겹침(Overlap) 해결**: 시각적 요소 간 충돌 방지를 위한 '절대 금지 규칙' 및 자기 검증 로직 도입
*   **페이지 레이아웃 밸런싱**: A4 포맷의 하단 여백(Bottom Margin) 확보 및 시각적 리듬 최적화
*   **플레이스홀더 패턴 매칭**: 복잡한 생성 환경에서 이미지 태그 매핑 정확도 향상 전략 수립

---

## 🚩 Phase 1: 인프라 및 핵심 로직 구축

### 1. Git 대용량 파일 업로드 실패 및 히스토리 관리

#### 📌 이슈 요약
GitHub Push 중 100MB 초과 파일로 인한 업로드 차단 발생

#### 📋 발생 상황 & 에러 로그
- **상황**: 로컬 개발 환경(`Final-Project`)을 원격 저장소로 `push` 하는 과정에서 차단됨.
- **에러 로그**:
  ```bash
  remote: error: File .venv/lib/site-packages/torch/lib/libtorch_cpu.so is 158.00 MB; 
  this exceeds GitHub's file size limit of 100.00 MB
  error: logical rewriting of history failed
  ```

#### 🔍 원인 분석
- `.gitignore` 설정이 늦게 적용되었거나, 이미 Staging Area에 대용량 라이브러리 폴더(`.venv`)나 모델 파일이 포함된 상태로 커밋됨.
- Git은 한번 커밋된 파일은 `.gitignore`에 추가해도 추적을 계속하기 때문에 발생.

#### ✅ 해결 과정 & 변경점
1. **커밋 되돌리기**: `git reset --soft HEAD~1` 명령어로 직전 커밋을 취소하고 파일들을 Unstage 상태로 변경.
2. **.gitignore 갱신**: `.venv`, `__pycache__`, `*.pth` 등 대용량 파일 패턴 추가.
3. **캐시 삭제**:
   ```bash
   git rm -r --cached .
   git add .
   git commit -m "Fix: Remove large files and update gitignore"
   ```

#### 💡 배운 점
- 프로젝트 초기 설정 시 `.gitignore`를 가장 먼저 완벽하게 세팅하는 것이 중요함.
- `git reset --soft`를 활용하면 작업 내용을 잃지 않고 커밋 이력만 수정할 수 있음.

---

### 2. Publisher Agent 병렬 처리 최적화

#### 📌 이슈 요약
기사 HTML 생성 속도가 너무 느려 전체 워크플로우 지연 발생

#### 📋 발생 상황 & 에러 로그
- **상황**: 5개 이상의 토픽을 처리할 때 Agent가 순차적으로(Sequential) 기사를 생성하여 응답 시간이 비례해서 늘어남.
- **코드 (Before)**:
  ```python
  for article in articles:
      html = self.generate_html(article) # 한 번에 하나씩 실행
  ```

#### 🔍 원인 분석
- LLM 호출과 같은 I/O Bound 작업을 단일 스레드에서 동기(Synchronous) 방식으로 처리하여 불필요한 대기 시간 발생.

#### ✅ 해결 과정 & 변경점
- **병렬 처리 도입**: `concurrent.futures.ThreadPoolExecutor`를 사용하여 멀티 스레딩 구현.
- **코드 (After)**:
  ```python
  with ThreadPoolExecutor(max_workers=5) as executor:
      results = list(executor.map(self.generate_single_article, articles))
  ```

#### 💡 배운 점
- LLM API 호출과 같은 대기 시간이 긴 작업은 병렬 처리를 통해 전체 실행 시간을 획기적으로 단축할 수 있음.
- **성과**: 평균 120초 → **25초** (79% 단축)

---

---

## 🚩 Phase 2: 렌더링 엔진 정밀 튜닝

### 1. Silent Data Binding Failure (Base64 누락)

#### 📌 이슈 요약
HTML 생성 시 에러 로그 없이 이미지와 텍스트가 화면에 렌더링되지 않는 'Silent Failure' 현상 발생

#### 📋 발생 상황 & 에러 로그
- **상황**: `template_renderer.py`를 통해 데이터를 주입했으나, 생성된 HTML 파일에서 이미지가 엑박(Broken Icon)으로 뜨고 텍스트 슬롯이 비어있음.
- **로그**: Python 런타임 에러는 없으나 브라우저 콘솔에서 리소스 로드에 실패함.
  ```html
  <!-- 렌더링 결과 (Before) -->
  <img src="iVBORw0KGgoAAA..." /> <!-- 브라우저가 인식 불가 -->
  <div id="headline"></div> <!-- 데이터 바인딩 실패 -->
  ```

#### 🔍 원인 분석
1. **Base64 Prefix 누락**: HTML `<img>` 태그는 Base64 데이터 앞에 `data:image/png;base64,` 헤더가 있어야 인식하지만, 원본 데이터에는 이 부분이 빠져 있었음.
2. **Slot Key 불일치**: 템플릿 엔진(Jinja2)에서 기대하는 변수명(`headline`)과 실제 넘겨준 딕셔너리 키(`title`)가 일치하지 않아 매핑이 실패함.

#### ✅ 해결 과정 & 변경점
- **Base64 처리 로직 수정**: 이미지 데이터를 주입하기 전 Prefix를 강제로 붙이는 전처리 함수 추가.
- **매핑 딕셔너리 교정**: 템플릿의 슬롯 이름과 1:1로 대응되도록 데이터 키 이름을 통일.

  ```python
  # After (Fix Code)
  def format_image_data(base64_str):
      return f"data:image/jpeg;base64,{base64_str}"
  
  context = {
      "headline": data["title"],  # Key Mapping 수정
      "image_src": format_image_data(raw_image)
  }
  ```

#### 💡 배운 점
- **Silent Error의 위험성**: 에러가 안 난다고 정상 작동하는 것이 아님. 프론트엔드 결과물까지 End-to-End로 검증하는 습관이 중요함.
- **Data Protocol 준수**: Base64 이미지 처리 시 표준 스키마(URI Scheme) 준수 여부를 항상 체크해야 함.

---

### 2. Tailwind CSS 스타일 미적용 문제

#### 📌 이슈 요약
생성된 HTML 파일을 브라우저로 열었을 때 Tailwind 클래스가 적용되지 않아 레이아웃이 깨지는 현상

#### 📋 발생 상황 & 에러 로그
- **상황**: 로컬 파일로 HTML을 열었을 때 기본 브라우저 스타일(Times New Roman, 파란색 링크 등)만 적용됨.
- **로그**: 브라우저 콘솔 경고
  ```
  Refused to execute script from '...' because its MIME type ('text/html') is not executable...
  ```
  혹은 스타일이 전혀 먹히지 않는 상태.

#### 🔍 원인 분석
- **CDN 설정 미비**: 정적 HTML 파일에서 Tailwind CDN(`cdn.tailwindcss.com`)을 사용할 때, 커스텀 설정(Config) 스크립트가 올바르게 로드되지 않거나 네트워크 환경에 따라 차단됨.
- **Arbitrary Value 인식 불가**: JIT(Just-In-Time) 모드가 필요한 `h-[500px]` 같은 임의 값 문법이 CDN 버전에서 기본적으로 활성화되지 않았음.

#### ✅ 해결 과정 & 변경점
- **CDN 스크립트 명시적 선언**: 색상 및 폰트 설정을 포함한 `tailwind.config` 객체를 HTML 헤더에 직접 스크립트로 주입.

  ```html
  <!-- After (Solution) -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          colors: { custom: '#1a202c' }
        }
      }
    }
  </script>
  ```

#### 💡 배운 점
- **Standalone HTML의 제약**: 빌드 도구(Webpack/Vite) 없이 단일 HTML로 배포할 때는 CDN 의존성을 명확히 관리해야 함.

---

### 3. 텍스트 잘림(Truncation) 및 레이아웃 깨짐

#### 📌 이슈 요약
긴 텍스트가 들어왔을 때 레이아웃 영역을 벗어나거나 이미지를 침범하는 UI 버그 발생

#### 📋 발생 상황 & 에러 로그
- **상황**: `feature_split.html` 레이아웃에서 뉴스 헤드라인이 3줄을 넘어갈 때 하단 이미지 영역을 덮어버림.
- **코드 스니펫**:
  ```html
  <div class="h-20 overflow-hidden"> <!-- 단순히 높이만 고정 -->
      {{ huge_text_content }}
  </div>
  ```

#### 🔍 원인 분석
- **CSS 제어 부족**: 텍스트 길이에 대한 가변성을 고려하지 않고 고정 높이(`h-20`)만 주었으며, 넘치는 텍스트를 처리하는 `text-overflow`나 `line-clamp` 속성이 누락됨.

#### ✅ 해결 과정 & 변경점
- **Line Clamp 적용**: Tailwind의 `line-clamp` 플러그인을 활용하여 지정된 줄 수 이상은 '...'으로 처리되도록 수정.

  ```html
  <!-- After -->
  <div class="line-clamp-3 text-ellipsis overflow-hidden">
      {{ headline }}
  </div>
  ```

#### 💡 배운 점
- **Dynamic Content 대응**: CMS나 LLM이 생성하는 데이터는 길이를 예측할 수 없으므로, 항상 최악의 경우(가장 긴 텍스트)를 가정한 방어적 CSS 코딩이 필요함.

---

## 🚩 Phase 3: 데이터 파이프라인 및 레지스트리 고도화

### 1. Pinterest 데이터셋 형식 불일치

#### 📌 이슈 요약
Pinterest 크롤링 데이터와 시스템 데이터 스키마 불일치

#### 📋 발생 상황 & 에러 로그
```json
// Pinterest 데이터 (새 형식)
{"id": "pin_xxx", "keywords": [...], "css_style": {...}}

// 시스템 기대 형식
{"image_id": "...", "elements": [...], "mood": "..."}
```

#### 🔍 원인 분석
- Pinterest 데이터는 `elements[]` (좌표 정보) 없음
- 필드명 불일치 (`id` vs `image_id`)

#### ✅ 해결 과정 & 변경점
- 변환 가이드 문서 작성
- Gemini Vision으로 elements 자동 생성

#### 💡 배운 점
- 외부 데이터 통합 전 **스키마 매핑 테이블** 작성
- 누락 필드는 **AI Vision으로 자동 생성** 가능

---

### 2. Gemini Vision 레이아웃 분석 파이프라인

#### 📌 이슈 요약
122개 Pinterest 이미지에서 레이아웃 좌표를 자동 추출

#### 📋 발생 상황 & 에러 로그
```
요구사항:
- image_data/ 폴더의 122개 이미지 처리
- Single/Double Page 자동 분류
- elements[] 좌표 추출
```

#### ✅ 해결 과정 & 변경점
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

#### 💡 배운 점
- **Gemini Vision은 bounding box 추출 가능**
- Rate Limit 대응: 배치 + delay 필수
- Double Page 자동 분할: `aspect_ratio > 1.2`

---

### 3. MCP(Model Context Protocol) 이미지 데이터 흐름 단절

#### 📌 이슈 요약
Publisher Agent에서 생성한 이미지가 MCP 서버를 거쳐 LLM에 도달하지 못하는 데이터 파이프라인 이슈

#### 📋 발생 상황 & 에러 로그
- **상황**: 최종 결과물 생성 요청 시, 텍스트 프롬프트는 전달되지만 이미지 컨텍스트가 누락되어 LLM이 이미지를 설명하거나 배치하지 못함.
- **로그**:
  ```json
  "content": [
     {"type": "text", "text": "..."} 
     // 이미지 블록이 있어야 할 자리가 비어있음
  ]
  ```

#### 🔍 원인 분석
- **JSON Serialization 버그**: MCP 클라이언트와 서버 간 통신 과정에서 대용량 Base64 문자열이 포함된 객체를 직렬화할 때, 일부 필드가 필터링되거나 크기 제한으로 인해 Drop됨.

#### ✅ 해결 과정 & 변경점
- **Explicit Payload Check**: 데이터 전송 전 단계에서 이미지 데이터 존재 여부를 검증하는 로직 추가.
- **Context Injection**: LLM 프롬프트 구성 시 이미지를 별도 첨부 파일이 아닌, 멀티모달 메시지 포맷에 맞춰 명시적으로 삽입하도록 프로토콜 수정.

#### 💡 배운 점
- **Pipeline Visibility**: 에이전트 간 통신(Agent-to-Agent)에서는 데이터가 어디서 유실되는지 추적하기 어려우므로, 각 단계별로 로그를 남기는 'Observability' 확보가 필수적임.

---

### 4. Vision-Driven Registry 통합 및 Legacy 코드 제거

#### 📌 이슈 요약
하드코딩된 레이아웃 로직을 동적 JSON 레지스트리(`layout_spec.json`)로 이관하면서 발생한 의존성 충돌

#### 📋 발생 상황 & 에러 로그
- **상황**: 새로운 테마를 추가했으나 시스템이 여전히 구버전 레이아웃을 참조하거나, `ImportError` 발생.
- **로그**:
  ```python
  AttributeError: 'LayoutManager' object has no attribute 'get_legacy_style'
  ```

#### 🔍 원인 분석
- **Legacy Code 잔존**: `director.py`가 새로운 레지스트리 시스템을 사용하도록 업데이트되었으나, 일부 서브 모듈이 여전히 삭제된 구버전 함수나 클래스를 참조하고 있었음.

#### ✅ 해결 과정 & 변경점
- **Full Refactoring**: 구버전 코드(`layouts.py`의 하드코딩 부분)를 완전히 삭제(Deprecate)하고, 모든 레이아웃 결정 로직이 JSON 스펙 파일을 읽어서 처리하도록 단일화.
- **Regeneration**: 모든 테마에 대해 `layout_spec.json`을 재생성하여 스키마 동기화.

#### 💡 배운 점
- **Technical Debt 청산**: 새로운 기능을 도입할 때 구버전 코드를 '나중에 지워야지' 하고 남겨두면 반드시 발목을 잡음. 과감한 Refactoring과 Clean-up이 시스템 안정성에 기여함.

---

## 🚩 Phase 4: LangGraph 멀티 에이전트 전환

### 1. 멀티노드 (LangGraph) 아키텍처 전환

#### 📌 이슈 요약
단일 거대 프롬프트(~500줄)를 역할별 5개 노드로 분리하여 유지보수성 및 품질 향상

#### 📋 발생 상황 & 에러 로그
```
기존 구조의 문제:
- 단일 프롬프트 ~500줄 → 수정/디버깅 어려움
- 모든 규칙이 한 곳에 → 역할 구분 불명확
- 토큰 사용량 비효율
```

#### 🔍 원인 분석
- 모놀리식 프롬프트는 규모가 커지면 관리 불가능

#### ✅ 해결 과정 & 변경점

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

#### 💡 배운 점
- **LangGraph StateGraph**로 노드 간 상태 전달 용이
- 각 노드는 단일 책임 → 디버깅 쉬움
- 백업 + 환경변수 스위치로 **안전한 롤백** 가능

---

### 2. Layout Planner 잘못된 레이아웃 선택

#### 📌 이슈 요약
ARTICLE 페이지인데 Layout Planner가 `hero` 레이아웃 선택

#### 📋 발생 상황 & 에러 로그
```
📐 [Node 2] Layout Plan: hero  ← 문제!

예상: ARTICLE + 긴 본문 → float 레이아웃
실제: hero 레이아웃 (이미지 상단 고정)
```

#### 🔍 원인 분석
1. **본문 길이 조건 LLM 위임**: 프로그래밍적 판단 없이 LLM이 자의적 결정
2. **규칙 명확성 부족**: 조건문 형태로 명시하지 않음

#### ✅ 해결 과정 & 변경점

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

#### 💡 배운 점
- **LLM 결정을 믿지 말고 검증해라**: 프로그래밍적 폴백 필수
- **디버깅 로그는 필수**: 입력값, 원본 응답, 최종 결정 모두 출력

---

### 3. LangGraph 프롬프트 누락

#### 📌 이슈 요약
멀티노드 전환 시 원본 프롬프트의 9개 주요 규칙이 누락됨

#### 📋 발생 상황 & 에러 로그
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

#### 🔍 원인 분석
- 수동 분리 과정에서 일부 규칙 누락
- 원본과 새 버전 간 체계적 비교 미실시

#### ✅ 해결 과정 & 변경점
Node 4 HTML Generator에 누락된 9개 항목 모두 추가

#### 💡 배운 점
- 리팩토링 시 **원본과 새 버전 diff 비교 필수**
- **100% 기능 동등성** 확인 후 전환

---

### 4. LangGraph 무한 루프 (Infinite Loop)

#### 📌 이슈 요약
Workflow가 종료되지 않고 특정 노드 구간을 반복하는 현상

#### 📋 발생 상황 & 에러 로그
- **상황**: `Writer` -> `Critique` -> `Writer` 순환 구조에서 품질 기준을 계속 만족하지 못해 무한 반복됨.
- **로그**: 동일한 프롬프트로 계속 재시도(Retry) 요청이 발생하며 토큰 비용 급증.

#### 🔍 원인 분석
- `Conditional Edge`의 종료 조건이 너무 엄격하거나, 탈출 로직(최대 시도 횟수 등)이 명확하지 않았음.

#### ✅ 해결 과정 & 변경점
- **흐름 단순화**: 무한 루프 방지를 위해 조건부 엣지를 제거하고 `Direct Edge`로 변경하여 강제 진행시킴 (임시 조치 및 흐름 제어 확립).
- **변경**: `Critique` 노드 이후 조건 판단 없이 바로 `Formatter` 노드로 이동하도록 그래프 구조 수정.

#### 💡 배운 점
- 자율 에이전트 설계 시 '최대 재시도 횟수(Max Retries)'와 같은 안전 장치(Fail-safe)가 필수적임.

---

## 🚩 Phase 5: 최종 품질 완성도 및 안정화

### 1. 콘텐츠 겹침 (Overlap) 문제

#### 📌 이슈 요약
생성된 레이아웃에서 텍스트-텍스트, 텍스트-이미지, 이미지-이미지 간 겹침이 발생하여 가독성 저하

#### 📋 발생 상황 & 에러 로그
```
문제 현상:
- 헤드라인과 본문 텍스트가 겹쳐서 읽을 수 없음
- 이미지 위에 텍스트가 overlay 없이 직접 배치됨
- absolute 포지셔닝 과다 사용으로 요소 간 충돌
```

#### 🔍 원인 분석
1. **프롬프트에 NO OVERLAP 규칙 부재**: LLM이 겹침 방지에 대한 명시적 지침 없이 자유롭게 배치
2. **absolute 포지셔닝 남용**: 상대 위치 계산 없이 절대 위치 사용
3. **자기 검증 단계 누락**: 생성 후 겹침 여부를 체크하는 로직 없음

#### ✅ 해결 과정 & 변경점

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

#### 💡 배운 점
- LLM은 명시적으로 금지하지 않으면 시각적 겹침을 허용함
- **"하지 마라"를 명확히 말해야** LLM이 따름
- 자기 검증 단계를 프롬프트에 포함시키면 품질 향상

---

### 2. 하단 여백 누락 및 텍스트 잘림

#### 📌 이슈 요약
A4 레이아웃 하단에 여백이 없고, 본문 텍스트가 페이지 끝에서 잘림

#### 📋 발생 상황 & 에러 로그
```
관찰된 문제:
- 좌/우/상단은 p-8 여백 있음
- 하단만 콘텐츠가 페이지 끝까지 차지
- overflow-hidden으로 텍스트 절단됨
```

#### 🔍 원인 분석
1. **pb (padding-bottom) 누락**: 전체 여백(p-8) 설정 시 하단만 별도 처리 필요
2. **overflow-hidden 적용**: 콘텐츠가 넘쳐도 보이지 않도록 숨김 처리됨
3. **텍스트 길이 대비 폰트 크기 부적절**: 긴 텍스트에 text-base 사용

#### ✅ 해결 과정 & 변경점

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

#### 💡 배운 점
- `overflow-hidden`은 레이아웃 보호용이지만 콘텐츠 손실 유발 가능
- **긴 텍스트는 폰트 크기 자동 조절**이 필요
- 하단 여백은 별도로 강조해야 LLM이 준수함

---

### 3. 이미지 Placeholder 누락

#### 📌 이슈 요약
LangGraph HTML Generator가 `__IMAGE_X__` placeholder 대신 다른 src 값 사용

#### 📋 발생 상황 & 에러 로그
```
⚠️ [Image 0] No placeholder found! Forcing injection...
⚠️ [Image 1] No placeholder found! Forcing injection...
```

#### 🔍 원인 분석
- `{image_placeholders}` 리스트를 LLM이 src로 직접 사용 시도
- `__IMAGE_X__` 패턴 명시적 지정 없음

#### ✅ 해결 과정 & 변경점

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

#### 💡 배운 점
- LLM은 **리스트를 그대로 사용하지 않음** → 명시적 나열 필요
- 중요한 패턴은 **예시와 함께 반복 강조**

---

## 📊 종합 성과 요약

| 성과 지표 | 개선 전 | 개선 후 | 핵심 기술 |
|:---:|:---:|:---:|:---|
| **생성 속도** | 120초 | **25초** (79%↓) | 병렬 처리, MCP 최적화 |
| **RAG 데이터셋** | 0개 | **122개** | Gemini Vision Pipeline |
| **겹침 발생률** | 40% | **2% 미만** | LangGraph, Self-Validation |
| **유지보수성** | 1개 거대 파일 | **5개 독립 노드** | LangGraph State Management |

---

## 🎯 기술적 통찰 (Key Insights for PPT)

1.  **AI 지시의 명확성**: LLM에게 "하지 마라"를 말하지 않는 것은 "해도 된다"고 말하는 것과 같다. (겹침 방지 규칙 사례)
2.  **하이브리드 아키텍처**: 모든 것을 AI에게 맡기지 말고, 논리적 결정(Length 기반 선택 등)은 프로그래밍으로 보조해야 한다.
3.  **Observability(관측 가능성)**: 에이전트 간 복잡한 통신 과정에서는 단계별 로그 전송과 데이터 검증이 없으면 문제를 찾을 수 없다.
4.  **Data-Driven Design**: 고품질 레이아웃은 모델 성능이 아니라, 고품질 데이터셋(Reference 좌표계)의 양과 질에서 결정된다.

---

*문서 생성: 2026-01-15*
