# 📁 프로젝트 폴더 구조

## 개요

이 프로젝트는 **AI 기반 매거진 레이아웃 자동 생성 시스템**입니다. 
Gemini AI와 RAG(Retrieval-Augmented Generation)를 활용하여 사용자가 업로드한 이미지와 텍스트를 분석하고, 자동으로 아름다운 매거진 스타일의 HTML 레이아웃을 생성합니다.

---

## 📂 루트 디렉토리 (`/home/sauser/final`)

```
final/
├── 📄 main.py               # FastAPI 메인 서버
├── 📄 mcp_server.py         # MCP 레이아웃 생성 서버
├── 📄 publisher.py          # HTML 생성 오케스트레이터
├── 📄 rag_modules.py        # RAG 핵심 모듈
├── 📄 image_validator.py    # 🆕 이미지 검수 모듈
├── 📄 test_rag.py           # RAG 테스트 파일
├── 📄 .env                  # 환경 변수 (API 키 등)
├── 📄 index_cache.pkl       # 인덱스 캐시 파일
│
├── 📁 datas/                # 데이터 저장소
├── 📁 static/               # 정적 파일 (HTML 등)
├── 📁 tool/                 # 유틸리티 도구
├── 📁 chroma_db/            # 벡터 데이터베이스
└── 📁 __pycache__/          # Python 캐시
```

---

## 📄 주요 파일 설명

### `main.py` - FastAPI 메인 서버
| 항목 | 설명 |
|------|------|
| **역할** | 웹 API 서버의 진입점 |
| **주요 기능** | 이미지 업로드 처리, 페이지 분석 요청 라우팅 |
| **엔드포인트** | `GET /` (메인 페이지), `POST /analyze` (페이지 분석) |
| **실행 방법** | `python main.py` (포트 8000) |

### `mcp_server.py` - MCP 레이아웃 생성 서버
| 항목 | 설명 |
|------|------|
| **역할** | Google Nano Banana - 동적 레이아웃 엔진 |
| **주요 기능** | LLM을 사용해 고품질 매거진 HTML 동적 생성 |
| **특징** | 다중 이미지 지원, 비전 컨텍스트 활용 |

### `publisher.py` - HTML 생성 오케스트레이터
| 항목 | 설명 |
|------|------|
| **역할** | 다중 아티클 HTML 생성 관리 |
| **주요 기능** | MCP 클라이언트를 통한 레이아웃 생성, 이미지 플레이스홀더 처리 |
| **특징** | 멀티스레딩으로 병렬 처리 (최대 5개 동시) |

### `rag_modules.py` - RAG 핵심 모듈
| 항목 | 설명 |
|------|------|
| **역할** | 검색 증강 생성(RAG) 시스템의 핵심 로직 |
| **주요 클래스** | `GeminiAnalyzer`, `ChromaHybridRetriever` |
| **기능** | 이미지/텍스트 분석, 하이브리드 검색, 레이아웃 추천 |

### `image_validator.py` - 🆕 이미지 검수 모듈
| 항목 | 설명 |
|------|------|
| **역할** | 이미지가 레이아웃에서 잘리지 않도록 검수 및 처리 |
| **주요 클래스** | `ImageValidator` |
| **지원 모드** | `contain` (잘림 방지), `cover` (채우기), `smart_crop` (스마트 크롭) |
| **주요 기능** | 이미지 비율 검사, 자동 리사이징, Base64 변환 |

---

## 📁 하위 디렉토리

### `datas/` - 데이터 저장소
```
datas/
└── 📄 dataset.json      # 레이아웃 데이터셋 (약 128KB)
```
- 매거진 레이아웃 템플릿 정보가 JSON 형태로 저장
- RAG 시스템의 검색 소스로 활용

### `static/` - 정적 파일
```
static/
└── 📄 index.html        # 웹 프론트엔드 UI
```
- 사용자 인터페이스 HTML 파일
- FastAPI의 정적 파일 서빙을 통해 제공

### `tool/` - 유틸리티 도구
```
tool/
├── 📄 mcp_client.py     # MCP 클라이언트 래퍼
└── 📁 __pycache__/
```
- **mcp_client.py**: MCP 서버와의 통신 담당
  - 다중 이미지 지원
  - 비동기 레이아웃 생성 요청

### `chroma_db/` - 벡터 데이터베이스
```
chroma_db/
├── 📄 chroma.sqlite3    # SQLite 데이터베이스 (약 8MB)
└── 📁 {collection-id}/  # 컬렉션 데이터
```
- ChromaDB 벡터 저장소
- BGE-M3 임베딩을 사용한 하이브리드 검색 지원

---

## 🔄 시스템 흐름도

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│   사용자    │───▶│   main.py    │───▶│  rag_modules.py │
│ (이미지+텍스트)   │    │ (FastAPI)    │    │ (분석 & 검색)   │
└─────────────┘    └──────────────┘    └─────────────────┘
                          │                      │
                          ▼                      ▼
                   ┌──────────────┐    ┌─────────────────┐
                   │ publisher.py │◀───│   chroma_db/    │
                   │  (오케스트레이터) │    │ (벡터 DB)       │
                   └──────────────┘    └─────────────────┘
                          │
                          ▼
                   ┌──────────────┐    ┌─────────────────┐
                   │ mcp_client   │───▶│  mcp_server.py  │
                   │    (tool/)   │    │  (LLM 레이아웃)   │
                   └──────────────┘    └─────────────────┘
                          │
                          ▼
                   ┌──────────────┐
                   │  최종 HTML   │
                   │   결과물     │
                   └──────────────┘
```

---

## 🛠️ 기술 스택

| 분류 | 기술 |
|------|------|
| **웹 프레임워크** | FastAPI |
| **AI/ML** | Google Gemini, BGE-M3 |
| **벡터 DB** | ChromaDB |
| **프로토콜** | MCP (Model Context Protocol) |
| **UI 스타일** | TailwindCSS |

---

## 📌 참고사항

- `.env` 파일에 `GOOGLE_API_KEY` 설정 필요
- 서버 실행: `python main.py`
- 기본 포트: 8000
