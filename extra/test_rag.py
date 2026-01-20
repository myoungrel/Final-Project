
import json
import os
import numpy as np
import chromadb
from typing import List, Dict, Any, Tuple
from FlagEmbedding import BGEM3FlagModel
from collections import defaultdict

# --- Configuration ---
MODEL_NAME = 'BAAI/bge-m3'
CHROMA_DB_PATH = "./chroma_db"
COLLECTION_NAME = "magazine_layouts"
DATASET_PATH = "./datas/dataset.json"  # Relative path assumption based on workspace

class ChromaHybridRetriever:
    def __init__(self, model_name: str = MODEL_NAME, db_path: str = CHROMA_DB_PATH):
        """
        Initialize the Hybrid Retriever with BGE-M3 model and ChromaDB client.
        """
        print(f"Loading Model: {model_name}...")
        self.model = BGEM3FlagModel(model_name, use_fp16=True)
        
        print(f"Connecting to ChromaDB at {db_path}...")
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name=COLLECTION_NAME)
        
        # In-memory storage for Sparse Vectors (Lexical Weights)
        # ChromaDB doesn't natively support BGE-M3's sparse weights efficiently yet for hybrid retrieval
        # so we keep them in memory for this implementation.
        self.sparse_index: Dict[str, Any] = {} 
        self.doc_ids: List[str] = []

    def _format_layout_text(self, item: Dict[str, Any]) -> str:
        """
        Format a dataset item into a single searchable text chunk.
        Combines metadata and textual elements.
        """
        # Metadata
        text_parts = [
            f"Category: {item.get('category', 'Unknown')}",
            f"Type: {item.get('type', 'Unknown')}",
            f"Mood: {item.get('mood', 'Unknown')}",
            f"Description: {item.get('description', '')}"
        ]
        
        # Extract text from elements (Title, Plain Text, etc.)
        content_texts = []
        if 'elements' in item:
            for elem in item['elements']:
                if 'text' in elem and elem['text']:
                    content_texts.append(elem['text'])
        
        if content_texts:
            text_parts.append("Content: " + " ".join(content_texts))
            
        return "\n".join(text_parts)

    def index_data(self, json_path: str):
        """
        Load JSON data, generate embeddings, and index into ChromaDB + Memory.
        """
        print(f"Loading dataset from {json_path}...")
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"Processing {len(data)} items...")
        
        doc_texts = []
        doc_metadatas = []
        self.doc_ids = []
        
        for item in data:
            doc_id = item['image_id']
            text_chunk = self._format_layout_text(item)
            
            self.doc_ids.append(doc_id)
            doc_texts.append(text_chunk)
            
            # Store essential metadata for retrieval result
            doc_metadatas.append({
                "image_id": doc_id,
                "category": item.get('category', ''),
                "type": item.get('type', ''),
                "mood": item.get('mood', '')
            })

        # Batch processing for embeddings (BGE-M3 handles batches well)
        print("Generating Embeddings (Dense + Sparse)...")
        output = self.model.encode(doc_texts, return_dense=True, return_sparse=True, return_colbert_vecs=False)
        
        dense_embeddings = output['dense_vecs']
        lexical_weights = output['lexical_weights'] # List of dicts

        # 1. Store Dense in ChromaDB
        print("Indexing Dense Vectors to ChromaDB...")
        # Check if already exists to avoid duplication errors or just upsert
        # Chroma Requires list format
        self.collection.upsert(
            ids=self.doc_ids,
            embeddings=[vec.tolist() for vec in dense_embeddings],
            metadatas=doc_metadatas,
            documents=doc_texts # Optional: Store raw text in Chroma too
        )

        # 2. Store Sparse in Memory
        print("Indexing Sparse Vectors to Memory...")
        for doc_id, sparse_vec in zip(self.doc_ids, lexical_weights):
            self.sparse_index[doc_id] = sparse_vec

        print("Indexing Complete!")

    def compute_rrf(self, dense_results: List[str], sparse_results: List[str], k: int = 60) -> List[Tuple[str, float]]:
        """
        Compute Reciprocal Rank Fusion (RRF) scores.
        """
        scores = defaultdict(float)
        
        # Dense Ranks
        for rank, doc_id in enumerate(dense_results):
            scores[doc_id] += 1 / (k + rank + 1)
            
        # Sparse Ranks
        for rank, doc_id in enumerate(sparse_results):
            scores[doc_id] += 1 / (k + rank + 1)
            
        # Sort by score desc
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Perform Hybrid Search:
        1. Dense Search (ChromaDB)
        2. Sparse Search (Lexical Match)
        3. RRF Fusion
        """
        print(f"Searching for: '{query}'")
        
        # Encode Query
        q_output = self.model.encode([query], return_dense=True, return_sparse=True)
        q_dense = q_output['dense_vecs'][0]
        q_sparse = q_output['lexical_weights'][0] # Dict[str, float]

        # 1. Dense Search via ChromaDB
        # We fetch more candidates than top_k for better fusion (e.g. top_k * 2 or fixed 20)
        candidate_k = min(20, len(self.doc_ids))
        
        dense_results = self.collection.query(
            query_embeddings=[q_dense.tolist()],
            n_results=candidate_k
        )
        # Chroma returns lists of lists
        dense_ids = dense_results['ids'][0]
        
        # 2. Sparse Search (Lexical Matching)
        # We calculate score for ALL docs in sparse_index (since dataset is small < 5000)
        # For larger datasets, we would use an Inverted Index here to only score docs sharing tokens.
        sparse_scores = []
        for doc_id, doc_sparse in self.sparse_index.items():
            score = self.model.compute_lexical_matching_score(doc_sparse, q_sparse)
            sparse_scores.append((doc_id, score))
        
        # Sort sparse results
        sparse_scores.sort(key=lambda x: x[1], reverse=True)
        sparse_ids = [x[0] for x in sparse_scores[:candidate_k]]

        # 3. RRF Fusion
        rrf_ranks = self.compute_rrf(dense_ids, sparse_ids, k=60)
        
        # Retrieve final Top-K
        final_results = []
        for doc_id, score in rrf_ranks[:top_k]:
            # Get metadata from Chroma (or memory cache)
            # Efficiently: we might have it from dense_results, but for sparse-only winners we need to fetch.
            # Simple get by id
            doc_data = self.collection.get(ids=[doc_id])
            if doc_data['metadatas']:
                meta = doc_data['metadatas'][0]
                final_results.append({
                    "image_id": doc_id,
                    "rrf_score": score,
                    "category": meta.get('category'),
                    "description": meta.get('mood') + " - " +  meta.get('type') # Simplified display
                })
                
        return final_results

# --- Main Execution ---
if __name__ == "__main__":
    retriever = ChromaHybridRetriever()
    
    # Check if data exists, if not index it (or just always index for this test)
    # in real prod, checking if collection count > 0 is better.
    if retriever.collection.count() == 0:
        retriever.index_data(DATASET_PATH)
    else:
        # Load sparse index from file or re-compute? 
        # For this script, we re-index to popuplate Memory Sparse Index (since we don't save it to disk in this simple script)
        print("Re-indexing to load in-memory Sparse Vectors...")
        retriever.index_data(DATASET_PATH)

    # Test Query
    # Simulating a user input: "A luxury fashion advertisement for winter holidays"
    test_query = "Fashion Advertisement. Luxurious mood. Winter holiday season. Red dress."
    
    results = retriever.search(test_query, top_k=3)
    
    print("\n--- Search Results ---")
    for r in results:
        print(f"ID: {r['image_id']} | Score: {r['rrf_score']:.4f}")
        print(f"   Category: {r['category']}")
        print(f"   Info: {r['description']}")
