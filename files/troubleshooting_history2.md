# Troubleshooting History Log

이 문서는 프로젝트 개발 중 발생한 주요 기술적 이슈와 해결 과정을 정리한 트러블슈팅 로그입니다. PPT 발표 자료의 핵심 근거로 사용될 수 있도록 핵심 내용을 요약했습니다.

---

## 1. Git 대용량 파일 업로드 실패 (Large File Error)

### **이슈 요약 (Issue Summary)**
GitHub Push 중 100MB 초과 파일로 인한 업로드 차단 발생

### **발생 상황 & 에러 로그 (Context & Logs)**
- **상황**: 로컬 개발 환경(`flask_web`)을 원격 저장소로 `push` 하는 과정에서 차단됨.
- **에러 로그**:
  ```bash
  remote: error: File .venv/lib/site-packages/torch/lib/libtorch_cpu.so is 158.00 MB; this exceeds GitHub's file size limit of 100.00 MB
  error: logical rewriting of history failed
  ```

### **원인 분석 (Root Cause)**
- `.gitignore` 설정이 늦게 적용되었거나, 이미 Staging Area에 대용량 라이브러리 폴더(`.venv`)나 모델 파일이 포함된 상태로 커밋됨.
- Git은 한번 커밋된 파일은 `.gitignore`에 추가해도 추적을 계속하기 때문에 발생.

### **해결 과정 & 변경점 (Solution & Changes)**
1. **커밋 되돌리기**: `git reset --soft HEAD~1` 명령어로 직전 커밋을 취소하고 파일들을 Unstage 상태로 변경.
2. **.gitignore 갱신**: `.venv`, `__pycache__`, `*.pth` 등 대용량 파일 패턴 추가.
3. **캐시 삭제**:
   ```bash
   git rm -r --cached .
   git add .
   git commit -m "Fix: Remove large files and update gitignore"
   ```

### **배운 점 (Insight)**
- 프로젝트 초기 설정 시 `.gitignore`를 가장 먼저 완벽하게 세팅하는 것이 중요함.
- `git reset --soft`를 활용하면 작업 내용을 잃지 않고 커밋 이력만 수정할 수 있음.

---

## 2. Publisher Agent 성능 저하 (Performance Bottleneck)

### **이슈 요약 (Issue Summary)**
기사 HTML 생성 속도가 너무 느려 전체 워크플로우 지연 발생

### **발생 상황 & 에러 로그 (Context & Logs)**
- **상황**: 5개 이상의 토픽을 처리할 때 Agent가 순차적으로(Sequential) 기사를 생성하여 응답 시간이 비례해서 늘어남.
- **코드 (Before)**:
  ```python
  for article in articles:
      html = self.generate_html(article) # 한 번에 하나씩 실행
  ```

### **원인 분석 (Root Cause)**
- LLM 호출과 같은 I/O Bound 작업을 단일 스레드에서 동기(Synchronous) 방식으로 처리하여 불필요한 대기 시간 발생.

### **해결 과정 & 변경점 (Solution & Changes)**
- **병렬 처리 도입**: `concurrent.futures.ThreadPoolExecutor`를 사용하여 멀티 스레딩 구현.
- **코드 (After)**:
  ```python
  with ThreadPoolExecutor(max_workers=5) as executor:
      results = list(executor.map(self.generate_single_article, articles))
  ```

### **배운 점 (Insight)**
- LLM API 호출과 같은 대기 시간이 긴 작업은 병렬 처리를 통해 전체 실행 시간을 획기적으로 단축할 수 있음.

---

## 3. LangGraph 무한 루프 (Infinite Loop)

### **이슈 요약 (Issue Summary)**
Workflow가 종료되지 않고 특정 노드 구간을 반복하는 현상

### **발생 상황 & 에러 로그 (Context & Logs)**
- **상황**: `Writer` -> `Critique` -> `Writer` 순환 구조에서 품질 기준을 계속 만족하지 못해 무한 반복됨.
- **로그**: 동일한 프롬프트로 계속 재시도(Retry) 요청이 발생하며 토큰 비용 급증.

### **원인 분석 (Root Cause)**
- `Conditional Edge`의 종료 조건이 너무 엄격하거나, 탈출 로직(최대 시도 횟수 등)이 명확하지 않았음.

### **해결 과정 & 변경점 (Solution & Changes)**
- **흐름 단순화**: 무한 루프 방지를 위해 조건부 엣지를 제거하고 `Direct Edge`로 변경하여 강제 진행시킴 (임시 조치 및 흐름 제어 확립).
- **변경**: `Critique` 노드 이후 조건 판단 없이 바로 `Formatter` 노드로 이동하도록 그래프 구조 수정.

### **배운 점 (Insight)**
- 자율 에이전트 설계 시 '최대 재시도 횟수(Max Retries)'와 같은 안전 장치(Fail-safe)가 필수적임.

---

## 4. Flask 파일 업로드 UI 반응 없음 (UX Bug)

### **이슈 요약 (Issue Summary)**
파일 선택 후 화면에 아무런 변화가 없어 사용자가 혼란을 겪음

### **발생 상황 & 에러 로그 (Context & Logs)**
- **상황**: `<input type="file">`을 통해 파일을 선택했으나, 옆에 파일명이 뜨지 않음.
- **원인**: 브라우저의 기본 파일 입력을 CSS로 숨기고 커스텀 버튼을 만들었으나, 파일명 업데이트 로직이 누락됨.

### **원인 분석 (Root Cause)**
- JavaScript에서 `change` 이벤트를 감지하여 DOM을 업데이트하는 핸들러가 없었음.

### **해결 과정 & 변경점 (Solution & Changes)**
- **이벤트 리스너 추가**:
  ```javascript
  document.getElementById('fileInput').addEventListener('change', function(e) {
      document.getElementById('fileNameDisplay').textContent = e.target.files[0].name;
  });
  ```

### **배운 점 (Insight)**
- 백엔드 기능 구현만큼이나 프론트엔드에서의 직관적인 사용자 피드백(Visual Feedback)이 중요함.

---

## 5. 마진 계산 로직 오류 (Business Logic Error)

### **이슈 요약 (Issue Summary)**
마진(Margin) 계산 방식이 사용자 의도(개당 마진)와 다르게 동작

### **발생 상황 & 에러 로그 (Context & Logs)**
- **상황**: 사용자는 "개당 1,000원 마진"을 기대하고 입력했으나, 시스템은 "총 마진 1,000원을 수량 n개로 나눔"으로 처리하거나 그 반대로 동작.
- **문제 식별**: 수량을 변경해도 단위 판매가가 변하는 기형적인 구조.

### **원인 분석 (Root Cause)**
- '마진'이라는 용어에 대한 기획 정의(Unit Margin vs Total Margin)가 코드에 명확히 반영되지 않음.

### **해결 과정 & 변경점 (Solution & Changes)**
- **공식 재정의**:
  - 기존: `Unit Price = (Total Cost + Total Margin) / Qty` (복잡/오류)
  - 변경: `Unit Price = Unit Cost + Unit Margin` (단순화)
  - `Line Total = Unit Price * Quantity`

### **배운 점 (Insight)**
- 개발 전 '비즈니스 로직'과 '수식'에 대한 명확한 정의가 선행되어야 코드 재작성을 방지할 수 있음.
