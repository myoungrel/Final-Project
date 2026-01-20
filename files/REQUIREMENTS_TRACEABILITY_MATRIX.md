# 요구사항 추적 매트릭스

---

## 문서 정보

| 항목 | 내용 |
|:---|:---|
| **프로젝트 명** | AI Magazine Layout Generator |
| **문서 업데이트** | 2026.01.15 |
| **작성자** | 유신, 규리, 명래, 승민 |

---

## 매트릭스

| ID | 요구사항명 | 설계 항목 | 구현 항목(모듈) | 테스트 항목 |
|:---:|:---|:---|:---|:---|
| RU01 | 프로젝트 개요 | 시스템 개요 문서 | 요구사항 정의서, 시스템 아키텍처 다이어그램 작성 | - |
| RU02 | 시스템 개요 | 시스템 아키텍처 설계, 흐름도, 역할 정의 | LangGraph 멀티 에이전트 구성, Intent→Safety→Vision→Planner→Editor/Director→Publisher→Critique | - |
| RU03 | 사용자 입력 기능 | 프론트엔드 UI 설계 | `index.html`, `main.py` /analyze 엔드포인트, 이미지 업로드, 텍스트 입력 | 단위 테스트, 입력 검증 테스트 |
| RU04 | Safety Agent | 콘텐츠 필터링 아키텍처 | `safety.py`, Hybrid Detection (Regex+LLM), Pydantic 정형화 | 필터링 정확도 테스트, 오탐 방지 테스트 |
| RU05 | Vision Agent | 이미지 분석 로직 설계 | `vision.py`, Maximal Empty Rectangle, Primary Color 추출, 피사체 추적 | 이미지 분석 테스트, 좌표 검증 테스트 |
| RU06 | RAG 시스템 | RAG 아키텍처 설계 | `rag_voyage.py`, Voyage 3.5 임베딩, ChromaDB, 4-Stage Fallback | 검색 정확도 테스트, Fallback 테스트 |
| RU07 | MCP Server | 렌더링 마이크로서비스 설계 | `mcp_server_langgraph.py`, 6노드 파이프라인, Multimodal Prompting | HTML 생성 테스트, 품질 점수 검증 |
| RU08 | HTML 생성 | HTML/CSS 템플릿 설계 | `publisher.py`, Jinja2 템플릿, Tailwind CSS, Google Fonts | 렌더링 테스트, 크로스 브라우저 테스트 |
| RU09 | 성능 최적화 | 성능 아키텍처 설계 | Placeholder 치환, asyncio 병렬 처리, ThreadPoolExecutor | 응답 속도 테스트, 부하 테스트 |
| RU10 | 검색 성능 | 검색 최적화 설계 | Index Caching, Dense Only 검색, Cascading Fallback | 검색 속도 테스트, 캐시 HIT 테스트 |
| RU11 | 품질 검수 | Critique Agent 설계 | `mcp_server_langgraph.py` quality_check_router, Self-Validation | 품질 점수 테스트, 재시도 로직 테스트 |
| RU12 | 이미지 품질 | 이미지 처리 설계 | `image_validator.py`, object-fit, 조건부 크롭, 용량 최적화 | 이미지 잘림 테스트, 용량 테스트 |
| RU13 | 레이아웃 DB | 데이터셋 구축 설계 | `datas/final_final_dataset.json`, 122개 레이아웃, 감성 태깅 | 데이터 무결성 테스트, 스키마 검증 |
| RU14 | Template Registry | 템플릿 관리 설계 | Template Registry, find_best_match 알고리즘 | 템플릿 매칭 테스트 |
| RU15 | 서버 환경 | 서버 인프라 설계 | FastAPI, Python 3.11+, asyncio, Gemini 2.5 Flash/Pro | 서버 구동 테스트, API 연동 테스트 |
| RU16 | 외부 API | API 연동 설계 | Gemini API, Voyage API, ChromaDB, MCP Protocol | API 응답 테스트, 타임아웃 테스트 |

---

## 요구사항-모듈 매핑 상세

### RU03. 사용자 입력 기능

| 설계 | 구현 모듈 | 테스트 |
|:---|:---|:---|
| 입력 폼 UI | `static/index.html` | UI 렌더링 테스트 |
| 이미지 업로드 | `main.py` /analyze | 파일 형식 검증 |
| 텍스트 입력 | `main.py` /analyze | 필수 필드 검증 |
| 타입/Mood 선택 | `main.py` /analyze | Enum 검증 |

---

### RU04. Safety Agent

| 설계 | 구현 모듈 | 테스트 |
|:---|:---|:---|
| Regex 탐지 | `safety.py` regex_patterns | 이메일/전화번호 탐지 |
| LLM 분석 | `safety.py` llm_analyze | 부적절 콘텐츠 탐지 |
| Pydantic 정형화 | `safety.py` SafetyResponse | JSON 출력 검증 |
| ALLOW 리스트 | `safety.py` allow_list | 오탐 방지 테스트 |

---

### RU05. Vision Agent

| 설계 | 구현 모듈 | 테스트 |
|:---|:---|:---|
| 공간 분석 | `vision.py` analyze_space | Bounding Box 검증 |
| 색상 추출 | `vision.py` extract_colors | Hex 코드 검증 |
| 피사체 추적 | `vision.py` track_subject | CSS 매핑 테스트 |
| 카테고리 분류 | `vision.py` classify_content | 5개 타입 검증 |

---

### RU06. RAG 시스템

| 설계 | 구현 모듈 | 테스트 |
|:---|:---|:---|
| Voyage 임베딩 | `rag_voyage.py` VoyageRetriever | 512차원 검증 |
| ChromaDB 검색 | `rag_voyage.py` search() | Dot Product 검증 |
| Index Caching | `rag_voyage.py` load_cache() | 캐시 HIT 테스트 |
| 4-Stage Fallback | `rag_voyage.py` cascading_search() | 단계별 검색 테스트 |

---

### RU07. MCP Server

| 설계 | 구현 모듈 | 테스트 |
|:---|:---|:---|
| Intent Classifier | `mcp_server_langgraph.py` intent_classifier_node | 의도 분류 테스트 |
| Image Analyzer | `mcp_server_langgraph.py` image_analyzer_node | 이미지 분석 테스트 |
| Layout Planner | `mcp_server_langgraph.py` layout_planner_node | 레이아웃 계획 테스트 |
| Typography Styler | `mcp_server_langgraph.py` typography_styler_node | 폰트 설정 테스트 |
| HTML Generator | `mcp_server_langgraph.py` html_generator_node | HTML 생성 테스트 |
| Quality Checker | `mcp_server_langgraph.py` html_quality_checker_node | 품질 점수 테스트 |

---

### RU09. 성능 최적화

| 설계 | 구현 모듈 | 테스트 |
|:---|:---|:---|
| Placeholder 치환 | `publisher.py` replace_placeholders() | 데이터 전송량 측정 |
| 병렬 처리 | `main.py` asyncio.gather() | 동시 실행 테스트 |
| 이미지 최적화 | `image_validator.py` optimize_image() | 용량 감소 측정 |

---

## 추적성 요약

| 요구사항 ID | 설계 완료 | 구현 완료 | 테스트 완료 | 상태 |
|:---:|:---:|:---:|:---:|:---:|
| RU01 | ✅ | ✅ | - | 완료 |
| RU02 | ✅ | ✅ | - | 완료 |
| RU03 | ✅ | ✅ | ✅ | 완료 |
| RU04 | ✅ | ✅ | ✅ | 완료 |
| RU05 | ✅ | ✅ | ✅ | 완료 |
| RU06 | ✅ | ✅ | ✅ | 완료 |
| RU07 | ✅ | ✅ | ✅ | 완료 |
| RU08 | ✅ | ✅ | ✅ | 완료 |
| RU09 | ✅ | ✅ | ✅ | 완료 |
| RU10 | ✅ | ✅ | ✅ | 완료 |
| RU11 | ✅ | ✅ | ✅ | 완료 |
| RU12 | ✅ | ✅ | ✅ | 완료 |
| RU13 | ✅ | ✅ | ✅ | 완료 |
| RU14 | ✅ | ✅ | ✅ | 완료 |
| RU15 | ✅ | ✅ | ✅ | 완료 |
| RU16 | ✅ | ✅ | ✅ | 완료 |

---

## 변경 이력

| 버전 | 일자 | 변경 내용 | 작성자 |
|:---:|:---:|:---|:---:|
| v1.0 | 2026-01-15 | 최초 작성 | 전원 |
