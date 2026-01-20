# 📊 임베딩 모델 및 유사도 측정 방식 가이드

> **목적**: RAG 시스템에서 사용할 수 있는 임베딩 모델과 유사도 측정 방식 정리  
> **대상 데이터**: Magazine Layout JSON (mood, category, description 등 짧은 구조화 텍스트)

---

## 📋 요약 비교표

| 모델 | 차원 | 비용 | 한국어 | 추천 유사도 | 특징 |
|:---|:---:|:---:|:---:|:---|:---|
| **BGE-M3** | 1024 | 무료 | ⭕ | Hybrid (Dense+Sparse) | 현재 사용 중, 다국어 지원 |
| **Voyage-3** | 1024 | 유료 | ⭕ | Cosine | Fashion/E-commerce 특화 |
| **Cohere embed-v3** | 1024 | 유료 | ⭕ | Input-type Aware | Query/Doc 분리 임베딩 |
| **Jina v3** | 1024 | 무료 | ⭕ | MaxSim (ColBERT) | 토큰 단위 Late-interaction |
| **OpenAI embed-3-large** | 3072 | 유료 | ⭕ | Cosine + MRL | 차원 축소 가능 (Matryoshka) |

---

## 1️⃣ BGE-M3 (현재 사용 중)

### 모델 정보
- **모델명**: `BAAI/bge-m3`
- **차원**: 1024
- **비용**: 무료 (로컬 실행)
- **특징**: Dense + Sparse + ColBERT 동시 지원

### 임베딩 코드
```python
from FlagEmbedding import BGEM3FlagModel

model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)

# Dense + Sparse 동시 추출
output = model.encode(
    ["Luxurious fashion editorial with serif fonts"],
    return_dense=True,
    return_sparse=True,
    return_colbert_vecs=False
)

dense_embedding = output['dense_vecs'][0]      # shape: (1024,)
sparse_weights = output['lexical_weights'][0]  # dict: {token_id: weight}
```

### 유사도 측정
```python
# Dense: Cosine Similarity
from numpy import dot
from numpy.linalg import norm

def cosine_similarity(a, b):
    return dot(a, b) / (norm(a) * norm(b))

# Sparse: Lexical Matching Score
sparse_score = model.compute_lexical_matching_score(doc_sparse, query_sparse)

# Hybrid: RRF Fusion
def compute_rrf(dense_results, sparse_results, k=60):
    scores = defaultdict(float)
    for rank, doc_id in enumerate(dense_results):
        scores[doc_id] += 1 / (k + rank + 1)
    for rank, doc_id in enumerate(sparse_results):
        scores[doc_id] += 1 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

---

## 2️⃣ Voyage AI voyage-3

### 모델 정보
- **모델명**: `voyage-3`
- **차원**: 1024
- **비용**: $0.06 / 1M tokens
- **특징**: Fashion, E-commerce 도메인 MTEB 1위

### 임베딩 코드
```python
import voyageai

client = voyageai.Client(api_key="your-api-key")

# 문서 임베딩
doc_result = client.embed(
    ["Luxurious fashion editorial with serif fonts"],
    model="voyage-3",
    input_type="document"
)
doc_embedding = doc_result.embeddings[0]  # shape: (1024,)

# 쿼리 임베딩
query_result = client.embed(
    ["minimalist beauty layout"],
    model="voyage-3",
    input_type="query"
)
query_embedding = query_result.embeddings[0]
```

### 유사도 측정
```python
# Cosine Similarity (기본)
import numpy as np

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

similarity = cosine_similarity(query_embedding, doc_embedding)

# 또는 Voyage API 내장 유사도
# (별도 계산 불필요, API에서 정렬된 결과 반환 가능)
```

---

## 3️⃣ Cohere embed-v3

### 모델 정보
- **모델명**: `embed-multilingual-v3.0`
- **차원**: 1024
- **비용**: 유료 (무료 티어 있음)
- **특징**: input_type으로 Document/Query 구분 → 검색 정확도 향상

### 임베딩 코드
```python
import cohere

co = cohere.Client("your-api-key")

# 문서 임베딩 (indexing용)
doc_response = co.embed(
    texts=["Luxurious fashion editorial with serif fonts"],
    model="embed-multilingual-v3.0",
    input_type="search_document",  # ⭐ 문서용
    embedding_types=["float"]
)
doc_embedding = doc_response.embeddings.float[0]

# 쿼리 임베딩 (검색용)
query_response = co.embed(
    texts=["minimalist beauty layout"],
    model="embed-multilingual-v3.0",
    input_type="search_query",  # ⭐ 쿼리용
    embedding_types=["float"]
)
query_embedding = query_response.embeddings.float[0]
```

### 유사도 측정
```python
# Dot Product (Cohere 권장)
import numpy as np

def dot_product(a, b):
    return np.dot(a, b)

similarity = dot_product(query_embedding, doc_embedding)

# 참고: Cohere는 정규화된 벡터를 반환하므로
# Dot Product ≈ Cosine Similarity
```

---

## 4️⃣ Jina jina-embeddings-v3

### 모델 정보
- **모델명**: `jinaai/jina-embeddings-v3`
- **차원**: 1024 (또는 Late-interaction 시 토큰별 벡터)
- **비용**: 무료 (로컬) / API 유료
- **특징**: ColBERT-style Late-interaction 지원

### 임베딩 코드
```python
from transformers import AutoModel, AutoTokenizer
import torch

model = AutoModel.from_pretrained("jinaai/jina-embeddings-v3", trust_remote_code=True)
tokenizer = AutoTokenizer.from_pretrained("jinaai/jina-embeddings-v3")

# 단일 벡터 (Mean Pooling)
def get_embedding(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    # Mean pooling
    embeddings = outputs.last_hidden_state.mean(dim=1)
    return embeddings[0].numpy()

doc_embedding = get_embedding("Luxurious fashion editorial")

# Late-Interaction (토큰별 벡터)
def get_token_embeddings(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True)
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.last_hidden_state[0].numpy()  # shape: (seq_len, 1024)

doc_tokens = get_token_embeddings("Luxurious fashion editorial")
query_tokens = get_token_embeddings("luxury style")
```

### 유사도 측정: MaxSim (ColBERT-style)
```python
import numpy as np

def maxsim_score(query_tokens, doc_tokens):
    """
    각 쿼리 토큰에 대해 가장 유사한 문서 토큰의 유사도를 합산
    """
    # query_tokens: (q_len, dim), doc_tokens: (d_len, dim)
    similarity_matrix = np.dot(query_tokens, doc_tokens.T)  # (q_len, d_len)
    
    # 각 쿼리 토큰의 최대 유사도
    max_similarities = similarity_matrix.max(axis=1)  # (q_len,)
    
    return max_similarities.sum()

score = maxsim_score(query_tokens, doc_tokens)
```

---

## 5️⃣ OpenAI text-embedding-3-large

### 모델 정보
- **모델명**: `text-embedding-3-large`
- **차원**: 3072 (기본) → **512, 1024 등으로 축소 가능**
- **비용**: $0.13 / 1M tokens
- **특징**: Matryoshka Representation Learning (MRL) - 앞쪽 차원만 사용해도 성능 유지

### 임베딩 코드
```python
from openai import OpenAI

client = OpenAI(api_key="your-api-key")

# 기본 3072 차원
response = client.embeddings.create(
    model="text-embedding-3-large",
    input=["Luxurious fashion editorial with serif fonts"]
)
full_embedding = response.data[0].embedding  # len: 3072

# ⭐ 차원 축소 (Matryoshka)
response_512 = client.embeddings.create(
    model="text-embedding-3-large",
    input=["Luxurious fashion editorial with serif fonts"],
    dimensions=512  # 512, 1024, 1536 등 선택 가능
)
small_embedding = response_512.data[0].embedding  # len: 512
```

### 유사도 측정
```python
# Cosine Similarity
import numpy as np

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# OpenAI는 정규화된 벡터를 반환하므로 Dot Product도 동일
similarity = cosine_similarity(query_embedding, doc_embedding)
```

---

## 📐 유사도 측정 방식 비교

| 방식 | 수식 | 특징 | 추천 모델 |
|:---|:---|:---|:---|
| **Cosine Similarity** | `dot(a,b) / (‖a‖ × ‖b‖)` | 방향 기반, 크기 무시 | 모든 모델 |
| **Dot Product** | `dot(a,b)` | 크기도 반영, 정규화된 벡터면 Cosine과 동일 | Cohere, OpenAI |
| **MaxSim (ColBERT)** | `Σ max(q_i · D)` | 토큰 단위 매칭, 긴 문서에 유리 | Jina, BGE-M3 |
| **RRF Fusion** | `1/(k+rank)` | Dense+Sparse 결합 | BGE-M3 (Hybrid) |

---

## 🎯 우리 데이터셋에 추천

| 우선순위 | 조합 | 이유 |
|:---:|:---|:---|
| 1 | **BGE-M3 + Dense Only** | 무료, 현재 코드 최소 수정, 짧은 텍스트에 적합 |
| 2 | **Voyage-3 + Cosine** | Fashion/Beauty 도메인 특화, 높은 정확도 |
| 3 | **OpenAI + 512차원** | 저장 비용 절감, 안정적인 품질 |

---

*문서 생성: 2026-01-15*
