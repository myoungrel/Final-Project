# RAG 시스템 임베딩 모델 및 유사도 측정 방식 선정 기술 명세서

**문서 작성일**: 2026-01-15  
**작성자**: Antigravity (AI Assistant)  
**대상 독자**: 개발팀 및 기술 의사결정권자

---

## 1. Executive Summary

본 문서는 RAG(Retrieval-Augmented Generation) 시스템 고도화를 위해 채택된 **Voyage AI 3.5** 임베딩 모델과 **Dot Product(내적)** 기반 유사도 측정 방식의 기술적 선정 근거를 기술합니다.

**결론적으로**, 현재의 데이터 규모와 검색 요구사항(정확도 vs 지연 시간)을 고려할 때 **Voyage 3.5(512차원 MRL 적용)**와 **Cosine Similarity(Normalized Dot Product)**의 조합이 최적의 성능과 효율성을 보장합니다.

---

## 2. 임베딩 모델 선정: Voyage 3.5

### 2.1 선정 배경
기존 BGE-M3(Open Source) 모델은 범용성이 뛰어나나, 로컬 리소스 점유와 처리 속도 면에서 최적화가 필요했습니다. 이에 따라 API 기반의 고성능 모델인 OpenAI와 Voyage AI를 비교 검토하였으며, **Retrieval Quality(검색 품질)**와 **Efficiency(효율성)** 측면에서 Voyage 3.5를 최종 선정하였습니다.

### 2.2 기술적 근거

#### ① Matryoshka Representation Learning (MRL) 지원
Voyage 모델의 가장 결정적인 선정 사유는 **MRL(Matryoshka Representation Learning)** 기술의 지원입니다.
*   **개념**: 단일 모델이 여러 차원(256, 512, 1024, 2048 등)의 임베딩을 생성할 때, 앞쪽 차원(앞부분의 element들)에 중요 정보를 집중시켜 학습하는 기법입니다.
*   **이점**: 차원을 50% 이상 줄여도(1024 → 512) 성능 하락폭이 매우 미미(-0.8% 수준)합니다. 이를 통해 **벡터 DB 저장 공간을 50% 절약**하고, **검색 속도(Latency)를 획기적으로 개선**할 수 있습니다.
*   **적용**: 현재 프로젝트에서는 **512차원**을 사용하여 스토리지 효율과 검색 속도를 극대화했습니다.

#### ② Retrieval Task 특화 성능 (SOTA)
Voyage 모델은 범용 언어 모델이 아닌 **Embedding & Retrieval Task에 특화**되어 학습되었습니다.
*   **MTEB 벤치마크**: Voyage 3 계열은 MTEB(Massive Text Embedding Benchmark)의 Retrieval 부문에서 OpenAI `text-embedding-3-large`와 동등하거나 상회하는 성능을 지속적으로 보여줍니다.
*   **Context Window**: 긴 문맥 처리에 강점이 있어, 향후 데이터 필드가 확장되더라도 유연한 대응이 가능합니다.

#### ③ Cost-Performance (가성비)
*   **무료 티어**: 초기 200M 토큰 무료 제공은 프로젝트 초기 개발 및 테스트 단계에서 비용 장벽을 제거합니다.
*   **API 효율성**: `voyage-3.5`는 `large` 모델 대비 약 3배 빠르며, `lite` 모델보다 정교한 의미 파악이 가능한 **Balanced Model**입니다.

---

## 3. 유사도 측정 방식: Dot Product (Cosine Similarity)

### 3.1 선정 배경
벡터 검색에서 주로 사용되는 거리 척도는 Euclidean Distance(L2), Cosine Similarity, Dot Product가 있습니다. 본 프로젝트에서는 **Dot Product(내적)** 방식을 채택하였습니다.

### 3.2 기술적 근거

#### ① 학습 목적함수(Training Objective)와의 일치
현대의 덴스 리트리버(Dense Retriever) 모델들(Voyage, OpenAI, BGE 등)은 학습 시 **Contrastive Loss (InfoNCE)** 등을 사용하며, 이때 Positive/Negative 샘플 간의 유사도를 **Dot Product** 또는 **Cosine Similarity**로 계산하여 최적화합니다.
*   따라서, 학습된 모델의 성능을 온전히 활용하기 위해서는 **학습 때와 동일한 Metric**을 사용하는 것이 수학적으로 타당합니다.
*   Euclidean Distance(L2)는 벡터의 크기(Magnitude)에 영향을 받지만, 의미론적 유사성(Semantic Similarity)은 벡터의 **방향(Direction)**에 주로 존재합니다.

#### ② Normalized Vectors와 Dot Product의 등가성
Voyage AI의 임베딩 벡터는 기본적으로 **Unit Norm(단위 벡터)**으로 정규화(Normalization)되어 출력됩니다. (또는 사용 전 정규화 권장)

수학적으로 두 벡터 $\mathbf{A}, \mathbf{B}$가 정규화($||\mathbf{A}|| = ||\mathbf{B}|| = 1$)되어 있을 때:
$$ \text{Cosine Similarity}(\mathbf{A}, \mathbf{B}) = \frac{\mathbf{A} \cdot \mathbf{B}}{||\mathbf{A}|| ||\mathbf{B}||} = \mathbf{A} \cdot \mathbf{B} = \text{Dot Product} $$

*   **연산 효율성**: Cosine Similarity를 계산하기 위해 매번 분모(Norm의 곱)를 계산하고 나누는 것보다, 정규화된 벡터의 **Dot Product(단순 곱셈 합)**만 수행하는 것이 연산 비용(FLOPs) 측면에서 훨씬 효율적입니다.
*   대부분의 고성능 벡터 DB(ChromaDB, Pinecone, Milvus)는 Dot Product 연산에 대해 SIMD 가속 등 하드웨어 최적화가 잘 되어 있습니다.

#### ③ 구현상의 이점
현재 구현된 `ChromaDB` 컬렉션은 `metadata={"hnsw:space": "cosine"}`으로 설정되어 있습니다. ChromaDB 내부적으로 이는 정규화된 벡터 간의 내적 연산을 통해 거리를 계산합니다. 이는 Voyage 모델의 출력 특성(Normalized)과 완벽하게 부합합니다.

---

## 4. 결론 (Conclusion)

본 프로젝트는 **데이터 효율성**과 **검색 정확도**의 균형을 위해 다음과 같은 기술 스택을 확정합니다.

1.  **Model**: `voyage-3.5` (512 Dimensions via MRL)
    *   *Why?* SOTA급 검색 성능 + 차원 축소를 통한 인프라 비용 절감.
2.  **Metric**: `Dot Product` (via Cosine config)
    *   *Why?* 의미론적 유사성(방향) 탐지 최적화 + 연산 속도 향상.

이 구성은 현재의 데이터셋 규모(수백~수천 건)는 물론, 향후 대규모 확장 시에도 별도 아키텍처 변경 없이 성능을 유지할 수 있는 **Scalable한 선택**입니다.
