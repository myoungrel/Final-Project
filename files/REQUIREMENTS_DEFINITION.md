# 요구사항 정의서

---

## 문서 정보

| 항목 | 내용 |
|:---|:---|
| **프로젝트 명** | AI Magazine Layout Generator |
| **문서 업데이트** | 2026.01.15 |
| **작성자** | 유신, 규리, 명래, 승민 |
| **버전** | v1.0 |

---

## 요구사항 목록

| No | 구분 | 요구사항 ID | 요구사항 명 | 요구사항 상세 설명 | 요청자 | 중요도 | 요청일자 | 수용여부 | 난이도 | 비고 |
|:---:|:---:|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|:---|
| 1 | 개요 | RU01 | 프로젝트 개요 | **프로젝트명**: AI Magazine Layout Generator<br>**개발 환경**: Python, LangGraph, FastAPI, Gemini API, ChromaDB<br>**프로젝트 목적**: 사용자가 입력한 이미지, 제목, 본문에 맞는 최적의 잡지 레이아웃을 AI가 자동으로 추천하고 생성하는 시스템<br>**핵심 해결 과제**: 기존 Rule-Based 방식의 한계(추상적 Mood 반영 불가, 확장성 부족)를 RAG 기반 의미 검색으로 해결 | USER | 상 | 2025-12-24 | 수행 | 상 | 전체 비교자료 참고자료로 발표 추가 |
| 2 | 개요 | RU02 | 시스템 개요 | 본 시스템은 **LangGraph 멀티 에이전트** 구조로 구성됨<br>- Intent Router → Safety → Vision → Planner → Editor/Director → Publisher → Critique → Formatter<br>- **RAG 시스템**: Voyage 3.5 임베딩 + ChromaDB 벡터 검색<br>- **MCP Server**: 실제 HTML 렌더링 담당 마이크로서비스<br>- 보안 및 확장성을 고려한 설계로 구성 | USER | 상 | 2025-12-24 | 수행 | 상 | |
| | | | | | | | | | | |
| 3 | 기능 | RU03 | 사용자 입력 기능 | **1. 콘텐츠 입력**<br>- 이미지 업로드 (다중 이미지 지원, 1~7장)<br>- 제목/소제목/본문 텍스트 입력<br>- 레이아웃 타입 선택 (Cover/Article)<br>- Mood 선택 (Elegant, Vibrant, Bold 등)<br><br>**2. 입력 검증**<br>- 이미지 형식 검증 (PNG, JPG, WEBP)<br>- 이미지 크기 최적화 (max_width=1024)<br>- 텍스트 길이 자동 판별 (50자 기준) | USER | 상 | 2025-12-31 | 수행 | 중 | |
| 4 | 기능 | RU04 | Safety Agent | **콘텐츠 필터링 시스템**<br>- 부적절한 콘텐츠 자동 필터링<br>- PII(개인정보) 탐지 및 차단<br>- **Hybrid Detection**: 정규표현식 + LLM 병합<br>- **Pydantic 출력 정형화**: JSON 포맷으로 구조화된 응답<br><br>**문맥 인식 프롬프트**<br>- 인터뷰이 이름, 브랜드명 ALLOW 리스트<br>- 예술적 묘사 허용 (수영복 화보 등)<br>- Sheriff → Editor 패러다임 전환 | USER | 상 | 2026-01-06 | 수행 | 중 | |
| 5 | 기능 | RU05 | Vision Agent | **이미지 분석 시스템**<br>- 공간 분석: Maximal Empty Rectangle 전략<br>- 피사체 추적: dominant_position → CSS object-position 매핑<br>- 색상 추출: Primary Color 자동 추출<br>- 5가지 카테고리 분류 및 레이아웃 추천점수 부여<br><br>**레이아웃 엔진**<br>- Anti-Gravity: 창의적 배치 로직<br>- 텍스트 오토핏: 본문 길이별 폰트 자동 조절 (11~15px)<br>- Vertical-text, Outline, 그라데이션 지원 | USER | 상 | 2026-01-05 | 수행 | 상 | |
| 6 | 기능 | RU06 | RAG 시스템 | **임베딩 및 검색**<br>- 임베딩 모델: Voyage 3.5 (512차원, MRL)<br>- 벡터 DB: ChromaDB<br>- Hybrid Scoring: Dense 0.7 + Sparse 0.3<br><br>**Fallback 전략**<br>- Stage 1 (Strict): 텍스트 길이 + 비율 + 이미지 개수 모두 일치<br>- Stage 2 (Relaxed): 조건 완화<br>- Stage 3 (Fallback): 이미지 개수만 유지<br>- 검색 성공률 100% 달성<br><br>**성능 최적화**<br>- Index Caching: 초기화 20배 향상 (10s → 0.5s)<br>- FP16 정밀도: 메모리 50% 절감 | USER | 상 | 2026-01-12 | 수행 | 상 | 데이터 효율 및 사용예시 추가 |
| 7 | 기능 | RU07 | MCP Server | **렌더링 마이크로서비스**<br>- LangGraph 6개 노드 멀티 에이전트 파이프라인<br>- Multimodal Prompting: 레퍼런스 이미지 구조 모방<br>- Smart Selection: 후보 3개 중 최적 레이아웃 선택<br><br>**품질 검수**<br>- Self-Validation 체크리스트<br>- Absolute Rules: 오버랩 금지, 이미지 개수 준수, 텍스트 보존<br>- 품질 점수 기반 동적 재시도 | USER | 상 | 2026-01-13 | 수행 | 상 | 구체성 부족함(수정예정) |
| 8 | 기능 | RU08 | HTML 생성 | **렌더링 엔진**<br>- HTML5 + Tailwind CSS + Google Fonts<br>- Jinja2 템플릿 기반 SDUI<br>- 이미지 최적화 (quality=75, max_width=1024)<br><br>**품질 보장**<br>- ANTI-LINE-CLAMP: 텍스트 자르기 지양<br>- CONDITIONAL Z-INDEX: 글 길이별 분기<br>- CONTENT-FIRST: 콘텐츠 분량이 레이아웃 결정 | USER | 상 | 2026-01-05 | 수행 | 중 | |
| | | | | | | | | | | |
| 9 | 성능 | RU09 | 성능 최적화 | **속도 최적화**<br>- Placeholder 치환: 데이터 전송량 90% 감소<br>- 병렬 처리 (asyncio.gather): 처리시간 50% 단축<br>- ThreadPoolExecutor: 생성 시간 79% 단축 (120초 → 25초)<br><br>**메모리 최적화**<br>- State에 이미지 대신 변수명만 저장<br>- 최종 단계에서만 실제 데이터 주입 | USER | 상 | 2026-01-09 | 수행 | 중 | |
| 10 | 성능 | RU10 | 검색 성능 | **검색 정확도**<br>- Dense + Sparse 하이브리드 검색<br>- 3-Stage Fallback으로 검색 성공률 100%<br>- 컨텐츠 타입 인식률 90% 이상<br><br>**검색 속도**<br>- Index Caching으로 초기화 20배 향상<br>- 512차원 MRL로 검색 속도 최적화 | USER | 중 | 2026-01-12 | 수행 | 중 | |
| | | | | | | | | | | |
| 11 | 품질 | RU11 | 품질 검수 | **Critique Agent**<br>- 시각적 QA 수행 순환 구조<br>- 겹침률 2% 미만 달성<br>- 품질 점수 기반 동적 재생성<br><br>**검수 항목**<br>- 오버플로우 확인<br>- 이미지 잘림/왜곡 확인<br>- 텍스트 가독성 확인<br>- 여백 균형 확인 | USER | 상 | 2026-01-05 | 수행 | 중 | |
| 12 | 품질 | RU12 | 이미지 품질 | **이미지 처리**<br>- object-fit: contain (피사체 잘림 방지)<br>- 조건부 크롭 (세로 인물 사진)<br>- NEVER UPSCALE: 작은 이미지 확대 금지<br>- Solid Background: 단색 배경 사용<br><br>**오버레이 가독성**<br>- .mag-text-overlay 클래스<br>- 그라데이션 + 그림자 효과 | USER | 중 | 2026-01-11 | 수행 | 중 | |
| | | | | | | | | | | |
| 13 | 데이터 | RU13 | 레이아웃 DB | **데이터셋 구축**<br>- 122개 레이아웃 데이터 자동 추출<br>- LayoutParser + OCR + Gemini Vision 파이프라인<br>- 감성 태깅 및 벡터화<br><br>**데이터 스키마**<br>- mood, category, type 메타데이터<br>- elements 좌표 정보<br>- 물리적 텍스트 수용량 계산 | USER | 상 | 2026-01-12 | 수행 | 상 | |
| 14 | 데이터 | RU14 | Template Registry | **템플릿 관리**<br>- 104개 테마 폴더 자동 스캔<br>- find_best_match 알고리즘<br>- 레시피 전용 레이아웃 (5가지 컴포넌트) | USER | 중 | 2026-01-11 | 수행 | 중 | |
| | | | | | | | | | | |
| 15 | 인프라 | RU15 | 서버 환경 | **백엔드**<br>- FastAPI 서버<br>- Python 3.11+<br>- asyncio 비동기 처리<br><br>**AI 모델**<br>- Gemini 2.5 Flash (분석)<br>- Gemini 2.5 Pro (생성)<br>- Voyage 3.5 (임베딩) | USER | 중 | 2025-12-31 | 수행 | 중 | |
| 16 | 인프라 | RU16 | 외부 API | **API 연동**<br>- Google Gemini API<br>- Voyage AI API<br>- Serper API (트렌드 검색)<br><br>**MCP Protocol**<br>- MCP Server 독립 마이크로서비스<br>- 에이전트-렌더러 분리 | USER | 중 | 2026-01-13 | 수행 | 중 | |

---

## 요구사항 구분 범례

| 구분 | 설명 |
|:---:|:---|
| **개요** | 프로젝트 및 시스템 개요 |
| **기능** | 핵심 기능 요구사항 |
| **성능** | 성능 최적화 요구사항 |
| **품질** | 품질 검수 요구사항 |
| **데이터** | 데이터 및 DB 요구사항 |
| **인프라** | 서버/환경 요구사항 |

---

## 중요도 기준

| 중요도 | 설명 |
|:---:|:---|
| **상** | 필수 기능, 시스템 핵심 요소 |
| **중** | 중요 기능, 품질 향상 요소 |
| **하** | 부가 기능, 선택적 요소 |

---

## 수용여부 기준

| 수용여부 | 설명 |
|:---:|:---|
| **수행** | 요구사항 수용 및 개발 완료 |
| **협의 필요** | 추가 논의 필요 |
| **협의 진행중** | 현재 논의 중 |
| **불가** | 기술적/일정적 사유로 불가 |

---

## 변경 이력

| 버전 | 일자 | 변경 내용 | 작성자 |
|:---:|:---:|:---|:---:|
| v1.0 | 2026-01-15 | 최초 작성 | 전원 |
