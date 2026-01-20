# 🛠️ Project Troubleshooting History

이 문서는 프로젝트 개발 과정에서 발생한 주요 기술적 이슈와 해결 과정을 정리한 트러블슈팅 로그입니다. 발표 자료의 핵심 근거자료로 활용할 수 있도록 문제 해결 흐름을 체계적으로 기록했습니다.

---

## 1. 템플릿 렌더링 시 이미지/텍스트 누락 (Silent Data Binding Failure)

### 1. 이슈 요약 (Issue Summary)
HTML 생성 시 에러 로그 없이 이미지와 텍스트가 화면에 렌더링되지 않는 'Silent Failure' 현상 발생

### 2. 발생 상황 & 에러 로그 (Context & Logs)
- **상황**: `template_renderer.py`를 통해 데이터를 주입했으나, 생성된 HTML 파일에서 이미지가 엑박(Broken Icon)으로 뜨고 텍스트 슬롯이 비어있음.
- **로그**: Python 런타임 에러는 없으나 브라우저 콘솔에서 리소스 로드 에 실패함.
  ```html
  <!-- 렌더링 결과 (Before) -->
  <img src="iVBORw0KGgoAAA..." /> <!-- 브라우저가 인식 불가 -->
  <div id="headline"></div> <!-- 데이터 바인딩 실패 -->
  ```

### 3. 원인 분석 (Root Cause)
1. **Base64 Prefix 누락**: HTML `<img>` 태그는 Base64 데이터 앞에 `data:image/png;base64,` 헤더가 있어야 인식하지만, 원본 데이터에는 이 부분이 빠져 있었음.
2. **Slot Key 불일치**: 템플릿 엔진(Jinja2)에서 기대하는 변수명(`headline`)과 실제 넘겨준 딕셔너리 키(`title`)가 일치하지 않아 매핑이 실패함.

### 4. 해결 과정 & 변경점 (Solution & Changes)
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

### 5. 배운 점 (Insight)
- **Silent Error의 위험성**: 에러가 안 난다고 정상 작동하는 것이 아님. 프론트엔드 결과물까지 End-to-End로 검증하는 습관이 중요함.
- **Data Protocol 준수**: Base64 이미지 처리 시 표준 스키마(URI Scheme) 준수 여부를 항상 체크해야 함.

---

## 2. Tailwind CSS 스타일 미적용 문제

### 1. 이슈 요약 (Issue Summary)
생성된 HTML 파일을 브라우저로 열었을 때 Tailwind 클래스가 적용되지 않아 레이아웃이 깨지는 현상

### 2. 발생 상황 & 에러 로그 (Context & Logs)
- **상황**: 로컬 파일로 HTML을 열었을 때 기본 브라우저 스타일(Times New Roman, 파란색 링크 등)만 적용됨.
- **로그**: 브라우저 콘솔 경고
  ```
  Refused to execute script from '...' because its MIME type ('text/html') is not executable...
  ```
  혹은 스타일이 전혀 먹히지 않는 상태.

### 3. 원인 분석 (Root Cause)
- **CDN 설정 미비**: 정적 HTML 파일에서 Tailwind CDN(`cdn.tailwindcss.com`)을 사용할 때, 커스텀 설정(Config) 스크립트가 올바르게 로드되지 않거나 네트워크 환경에 따라 차단됨.
- **Arbitrary Value 인식 불가**: JIT(Just-In-Time) 모드가 필요한 `h-[500px]` 같은 임의 값 문법이 CDN 버전에서 기본적으로 활성화되지 않았음.

### 4. 해결 과정 & 변경점 (Solution & Changes)
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

### 5. 배운 점 (Insight)
- **Standalone HTML의 제약**: 빌드 도구(Webpack/Vite) 없이 단일 HTML로 배포할 때는 CDN 의존성을 명확히 관리해야 함.

---

## 3. 텍스트 잘림(Truncation) 및 레이아웃 깨짐

### 1. 이슈 요약 (Issue Summary)
긴 텍스트가 들어왔을 때 레이아웃 영역을 벗어나거나 이미지를 침범하는 UI 버그 발생

### 2. 발생 상황 & 에러 로그 (Context & Logs)
- **상황**: `feature_split.html` 레이아웃에서 뉴스 헤드라인이 3줄을 넘어갈 때 하단 이미지 영역을 덮어버림.
- **코드 스니펫**:
  ```html
  <div class="h-20 overflow-hidden"> <!-- 단순히 높이만 고정 -->
      {{ huge_text_content }}
  </div>
  ```

### 3. 원인 분석 (Root Cause)
- **CSS 제어 부족**: 텍스트 길이에 대한 가변성을 고려하지 않고 고정 높이(`h-20`)만 주었으며, 넘치는 텍스트를 처리하는 `text-overflow`나 `line-clamp` 속성이 누락됨.

### 4. 해결 과정 & 변경점 (Solution & Changes)
- **Line Clamp 적용**: Tailwind의 `line-clamp` 플러그인을 활용하여 지정된 줄 수 이상은 '...'으로 처리되도록 수정.

  ```html
  <!-- After -->
  <div class="line-clamp-3 text-ellipsis overflow-hidden">
      {{ headline }}
  </div>
  ```

### 5. 배운 점 (Insight)
- **Dynamic Content 대응**: CMS나 LLM이 생성하는 데이터는 길이를 예측할 수 없으므로, 항상 최악의 경우(가장 긴 텍스트)를 가정한 방어적 CSS 코딩이 필요함.

---

## 4. MCP(Model Context Protocol) 이미지 데이터 흐름 단절

### 1. 이슈 요약 (Issue Summary)
Publisher Agent에서 생성한 이미지가 MCP 서버를 거쳐 LLM에 도달하지 못하는 데이터 파이프라인 이슈

### 2. 발생 상황 & 에러 로그 (Context & Logs)
- **상황**: 최종 결과물 생성 요청 시, 텍스트 프롬프트는 전달되지만 이미지 컨텍스트가 누락되어 LLM이 이미지를 설명하거나 배치하지 못함.
- **로그**:
  ```json
  "content": [
     {"type": "text", "text": "..."} 
     // 이미지 블록이 있어야 할 자리가 비어있음
  ]
  ```

### 3. 원인 분석 (Root Cause)
- **JSON Serialization 버그**: MCP 클라이언트와 서버 간 통신 과정에서 대용량 Base64 문자열이 포함된 객체를 직렬화할 때, 일부 필드가 필터링되거나 크기 제한으로 인해 Drop됨.

### 4. 해결 과정 & 변경점 (Solution & Changes)
- **Explicit Payload Check**: 데이터 전송 전 단계에서 이미지 데이터 존재 여부를 검증하는 로직 추가.
- **Context Injection**: LLM 프롬프트 구성 시 이미지를 별도 첨부 파일이 아닌, 멀티모달 메시지 포맷에 맞춰 명시적으로 삽입하도록 프로토콜 수정.

### 5. 배운 점 (Insight)
- **Pipeline Visibility**: 에이전트 간 통신(Agent-to-Agent)에서는 데이터가 어디서 유실되는지 추적하기 어려우므로, 각 단계별로 로그를 남기는 'Observability' 확보가 필수적임.

---

## 5. Vision-Driven Registry 통합 및 Legacy 코드 제거

### 1. 이슈 요약 (Issue Summary)
하드코딩된 레이아웃 로직을 동적 JSON 레지스트리(`layout_spec.json`)로 이관하면서 발생한 의존성 충돌

### 2. 발생 상황 & 에러 로그 (Context & Logs)
- **상황**: 새로운 테마를 추가했으나 시스템이 여전히 구버전 레이아웃을 참조하거나, `ImportError` 발생.
- **로그**:
  ```python
  AttributeError: 'LayoutManager' object has no attribute 'get_legacy_style'
  ```

### 3. 원인 분석 (Root Cause)
- **Legacy Code 잔존**: `director.py`가 새로운 레지스트리 시스템을 사용하도록 업데이트되었으나, 일부 서브 모듈이 여전히 삭제된 구버전 함수나 클래스를 참조하고 있었음.

### 4. 해결 과정 & 변경점 (Solution & Changes)
- **Full Refactoring**: 구버전 코드(`layouts.py`의 하드코딩 부분)를 완전히 삭제(Deprecate)하고, 모든 레이아웃 결정 로직이 JSON 스펙 파일을 읽어서 처리하도록 단일화.
- **Regeneration**: 모든 테마에 대해 `layout_spec.json`을 재생성하여 스키마 동기화.

### 5. 배운 점 (Insight)
- **Technical Debt 청산**: 새로운 기능을 도입할 때 구버전 코드를 '나중에 지워야지' 하고 남겨두면 반드시 발목을 잡음. 과감한 Refactoring과 Clean-up이 시스템 안정성에 기여함.
