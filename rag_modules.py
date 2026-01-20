
import os
import json
import chromadb
import google.generativeai as genai
from typing import List, Dict, Any, Tuple
from FlagEmbedding import BGEM3FlagModel
from collections import defaultdict
from dotenv import load_dotenv
import numpy as np

# Load environment variables
load_dotenv()

# Configure Logging
import logging
import pickle
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Config:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    MODEL_NAME = 'BAAI/bge-m3'
    CHROMA_DB_PATH = "./chroma_db"
    COLLECTION_NAME = "magazine_layouts"
    DATASET_PATH = "./datas/dataset.json"

    @staticmethod
    def validate():
        if not Config.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not found in .env file")

class GeminiAnalyzer:
    def __init__(self):
        Config.validate()
        genai.configure(api_key=Config.GOOGLE_API_KEY)
        # Using valid model name. 'gemini-1.5-flash' sometimes requires specific versioning.
        # Fallback to 'gemini-2.5-flash' if needed.
        self.model_name = 'gemini-2.5-flash'
        self.model = genai.GenerativeModel(self.model_name)

    def analyze_page(self, images: List[Any], title: str, body: str) -> Dict[str, str]:
        """
        Analyze a single page's content (Images + Text) to extract metadata.
        """
        # ... (Existing analysis logic remains the same, assuming it's above)
        prompt = f"""
        You are an expert design assistant. Analyze these images and the provided text content for a magazine layout.
        
        Title: {title}
        Body Text: {body}
        
        Determine the following attributes:
        1. Mood (e.g., Minimalist, Energetic, Luxurious, Emotional, Professional)
        2. Category (e.g., Fashion, Travel, Food, Business, Tech)
        3. Type (e.g., Image-heavy, Text-heavy, Balanced, Collage)
        4. Description (A short visual description of the ideal layout style)
        5. Visual Keywords (List of 3-5 key visual elements/colors/objects found in the images)

        Return the result strictly in JSON format:
        {{
            "mood": "...",
            "category": "...",
            "type": "...",
            "description": "...",
            "visual_keywords": ["...", "..."]
        }}
        """
        
        try:
            inputs = [prompt]
            if images:
                inputs.extend(images)
                
            response = self.model.generate_content(inputs)
            text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except Exception as e:
            print(f"Gemini Analysis Error: {e}")
            return {
                "mood": "General",
                "category": "General",
                "type": "Balanced",
                "description": "Standard layout",
                "visual_keywords": []
            }

    async def nanobanana_render(self, layout_data: Dict[str, Any], user_content: Dict[str, Any]) -> str:
        """
        Integration with Nanobanana MCP Service for high-quality layout generation.
        Optimized to provide rich context for superior results.
        이미지 검수 모듈을 통해 이미지가 잘리지 않도록 처리합니다.
        """
        from tool.mcp_client import mcp_client
        from image_validator import image_validator
        
        headline = user_content.get('title', 'Untitled')
        body = user_content.get('body', '')
        analysis = user_content.get('analysis', {})
        
        # 🖼️ 이미지 검수 및 처리
        raw_images = user_content.get('images', [])
        user_images = []
        
        # Calculate max height based on image count (width is calculated per-image based on aspect ratio)
        image_count = len(raw_images)
        if image_count == 1:
            max_height = 600
        elif image_count == 2:
            max_height = 400
        elif image_count <= 4:
            max_height = 280
        else:
            max_height = 220
        
        print(f"  📐 Max height for {image_count} images: {max_height}px")
        
        for i, img_b64 in enumerate(raw_images):
            try:
                # First, get original image dimensions
                from PIL import Image
                import io
                import base64 as b64
                
                # Decode base64 to get image dimensions
                if img_b64.startswith("data:"):
                    base64_data = img_b64.split(",")[1]
                else:
                    base64_data = img_b64
                image_bytes = b64.b64decode(base64_data)
                temp_img = Image.open(io.BytesIO(image_bytes))
                orig_width, orig_height = temp_img.size
                
                # Calculate slot size based on image aspect ratio (no cropping, no padding)
                aspect_ratio = orig_width / orig_height
                slot_height = max_height
                slot_width = int(slot_height * aspect_ratio)
                
                # Limit max width to prevent too wide images
                max_width = 400
                if slot_width > max_width:
                    slot_width = max_width
                    slot_height = int(slot_width / aspect_ratio)
                
                print(f"  📐 [Image {i}] Original: {orig_width}x{orig_height}, Slot: {slot_width}x{slot_height} (ratio: {aspect_ratio:.2f})")
                
                # Now process with calculated slot size
                result = image_validator.prepare_for_layout(
                    img_b64,
                    layout_type="magazine_full",
                    slot_info={
                        "width": slot_width,
                        "height": slot_height,
                        "fit_mode": "contain"
                    }
                )
                
                if result["success"]:
                    user_images.append(result["base64"])
                else:
                    user_images.append(img_b64)
                    print(f"  ⚠️ [Image {i}] Validation failed, using original: {result.get('error')}")
            except Exception as e:
                user_images.append(img_b64)
                print(f"  ⚠️ [Image {i}] Error during validation: {e}")
        placeholders = [f"__IMAGE_{i}__" for i in range(len(user_images))]
        
        # Enhanced Vision Context (for color palette and mood)
        vision_context = {
            "keywords": analysis.get('visual_keywords', []),
            "description": analysis.get('description', ''),
            "dominant_colors": "Analyze from keywords",  # Hint for LLM
            "visual_style": analysis.get('mood', 'Modern')
        }
        
        # Enhanced Design Spec (with visual harmony)
        page_layout_type = user_content.get('layout_type', 'article')  # cover or article
        design_spec = {
            "mood": analysis.get('mood', 'Modern'),
            "category": analysis.get('category', 'Magazine'),
            "layout_type": analysis.get('type', 'Balanced'),
            "page_type": page_layout_type,  # cover or article
            "visual_keywords": analysis.get('visual_keywords', []),  # For color matching
            "typography_style": self._suggest_typography(analysis.get('category', 'Magazine')),
            "color_scheme": self._suggest_color_scheme(analysis.get('mood', 'Modern'))
        }
        
        # Layout Strategy Hint (based on image count and type)
        image_count = len(user_images)
        if image_count > 2:
            layout_strategy = "Mosaic or Grid"
        elif image_count == 2:
            layout_strategy = "Split or Collage"
        else:
            layout_strategy = "Hero Image"
        
        # Enhanced Plan JSON (RAG layout as structural reference)
        elements = layout_data.get('elements', [])
        plan_json = {
            "reference_id": layout_data.get('image_id'),
            "elements": elements,
            "spatial_summary": self._summarize_layout(elements),
            "suggested_strategy": layout_strategy
        }
        
        try:
            print(f"🍌 [NanoBanana] Calling MCP for: {headline[:30]}")
            print(f"   Strategy: {layout_strategy}, Mood: {design_spec['mood']}")
            
            html = await mcp_client.generate_layout(
                headline=headline,
                body=body,
                image_data=placeholders,
                layout_override=page_layout_type.upper(),  # COVER or ARTICLE
                vision_json=json.dumps(vision_context),
                design_json=json.dumps(design_spec),
                plan_json=json.dumps(plan_json)
            )
            
            # Image Placeholder Injection with enhanced pattern matching
            for i, img_b64 in enumerate(user_images):
                injected = False
                
                # Try multiple placeholder patterns
                patterns = [
                    f"__IMAGE_{i}__",
                    f"{{{{IMAGE_PLACEHOLDER_{i}}}}}",
                    f"[IMAGE_{i}]",
                    f"{{IMAGE_{i}}}",
                    f"$IMAGE_{i}$"
                ]
                
                for pattern in patterns:
                    if pattern in html:
                        html = html.replace(pattern, img_b64, 1)
                        print(f"  ✅ [Image {i}] Injected via pattern: {pattern}")
                        injected = True
                        break
                
                # Also check for url() pattern (used in background-image)
                if not injected:
                    url_pattern = f"url({patterns[0]})"
                    if url_pattern in html:
                        html = html.replace(url_pattern, f"url({img_b64})")
                        print(f"  ✅ [Image {i}] Injected via url() pattern")
                        injected = True
                
                # If no placeholder found, force inject image at end
                if not injected:
                    print(f"  ⚠️ [Image {i}] No placeholder found! Forcing injection...")
                    # Force inject with smaller size to fit page
                    img_tag = f'<img src="{img_b64}" class="w-[30%] h-[120px] object-cover inline-block mx-2 my-2" alt="Image {i}" />'
                    
                    # Try to inject before the last closing div
                    if '</div>' in html:
                        last_div_pos = html.rfind('</div>')
                        html = html[:last_div_pos] + img_tag + html[last_div_pos:]
                    else:
                        html = html + img_tag
            
            # 🎨 Tailwind CSS Script Injection
            tailwind_script = '<script src="https://cdn.tailwindcss.com"></script>\n'
            if "<head>" in html:
                html = html.replace("<head>", f"<head>\n{tailwind_script}")
            elif "<html>" in html:
                html = html.replace("<html>", f"<html>\n<head>{tailwind_script}</head>")
            else:
                html = tailwind_script + html

            return html
        except Exception as e:
            print(f"❌ [NanoBanana] Integration Error: {e}")
            return ""
    
    def _suggest_typography(self, category: str) -> str:
        """Suggest typography style based on category."""
        typography_map = {
            "Fashion": "Elegant serif, high contrast",
            "Tech": "Modern sans-serif, clean",
            "Travel": "Adventurous, mixed fonts",
            "Food": "Warm, inviting serif",
            "Business": "Professional sans-serif"
        }
        return typography_map.get(category, "Balanced, readable")
    
    def _suggest_color_scheme(self, mood: str) -> str:
        """Suggest color scheme based on mood."""
        color_map = {
            "Minimalist": "Monochrome with accent",
            "Energetic": "Vibrant, high saturation",
            "Luxurious": "Gold, deep colors",
            "Emotional": "Warm tones",
            "Professional": "Navy, gray, white"
        }
        return color_map.get(mood, "Balanced palette")
    
    def _summarize_layout(self, elements: List[Dict]) -> str:
        """Create a spatial summary of the layout for LLM understanding."""
        if not elements:
            return "Flexible layout"
        
        image_count = sum(1 for e in elements if e.get('type') == 'figure')
        text_count = sum(1 for e in elements if e.get('type') in ['title', 'plain text'])
        
        # Determine dominant region
        top_heavy = sum(1 for e in elements if e.get('coordinates', {}).get('y1', 0) < 400)
        bottom_heavy = len(elements) - top_heavy
        
        layout_desc = f"{image_count} images, {text_count} text blocks. "
        if top_heavy > bottom_heavy:
            layout_desc += "Top-heavy composition."
        else:
            layout_desc += "Bottom-heavy composition."
        
        return layout_desc


class ChromaHybridRetriever:
    def __init__(self):
        """
        Initialize BGE-M3 model and ChromaDB client.
        """
        print(f"Loading Model: {Config.MODEL_NAME}...")
        self.model = BGEM3FlagModel(Config.MODEL_NAME, use_fp16=True)
        
        print(f"Connecting to ChromaDB at {Config.CHROMA_DB_PATH}...")
        self.client = chromadb.PersistentClient(path=Config.CHROMA_DB_PATH)
        self.collection = self.client.get_or_create_collection(name=Config.COLLECTION_NAME)
        
        self.sparse_index: Dict[str, Any] = {}
        self.doc_ids: List[str] = []
        self.doc_map: Dict[str, Any] = {} # Store raw layout data
        
        # Index Caching Logic with Auto-Versioning
        self.cache_path = "./index_cache.pkl"
        
        # Auto-generate version from index_data logic hash
        import hashlib
        import inspect
        logic_source = inspect.getsource(self.index_data)
        logic_hash = hashlib.md5(logic_source.encode()).hexdigest()[:8]
        self.CACHE_VERSION = f"1.0.1-{logic_hash}" # Auto-versioned
        
        if self._load_from_cache():
            logger.info(f"✅ Loaded index from cache (v{self.CACHE_VERSION}).")
        else:
            logger.info("⚡ Index not found, expired, or invalid. Re-indexing...")
            self.index_data() 
            self._save_to_cache()

    def _save_to_cache(self):
        try:
            with open(self.cache_path, 'wb') as f:
                pickle.dump({
                    'version': self.CACHE_VERSION, # Add versioning
                    'sparse_index': self.sparse_index,
                    'doc_map': self.doc_map,
                    'doc_ids': self.doc_ids
                }, f)
            logger.info(f"Saved index to {self.cache_path} (v{self.CACHE_VERSION})")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def _load_from_cache(self) -> bool:
        if not os.path.exists(self.cache_path):
            return False
        try:
            # check if dataset is newer than cache
            if os.path.exists(Config.DATASET_PATH):
                if os.path.getmtime(Config.DATASET_PATH) > os.path.getmtime(self.cache_path):
                    logger.info("Dataset modified. Invalidating cache.")
                    return False
            
            with open(self.cache_path, 'rb') as f:
                data = pickle.load(f)
                
                # Check version compatibility
                cached_version = data.get('version', '0.0.0')
                if cached_version != self.CACHE_VERSION:
                     logger.info(f"Cache version mismatch (Found: {cached_version}, Expected: {self.CACHE_VERSION}). Invalidate.")
                     return False
                     
                self.sparse_index = data['sparse_index']
                self.doc_map = data['doc_map']
                self.doc_ids = data['doc_ids']
            return True
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            return False 

    def _format_layout_text(self, item: Dict[str, Any]) -> str:
        text_parts = [
            f"Category: {item.get('category', 'Unknown')}",
            f"Type: {item.get('type', 'Unknown')}",
            f"Mood: {item.get('mood', 'Unknown')}",
            f"Description: {item.get('description', '')}"
        ]
        
        content_texts = []
        if 'elements' in item:
            for elem in item['elements']:
                if 'text' in elem and elem['text']:
                    content_texts.append(elem['text'])
        
        if content_texts:
            text_parts.append("Content: " + " ".join(content_texts))
            
        return "\n".join(text_parts)

    def index_data(self):
        """
        Load JSON, generate embeddings, and populate DB + Memory.
        """
        if not os.path.exists(Config.DATASET_PATH):
            print(f"Dataset not found at {Config.DATASET_PATH}")
            return

        print(f"Indexing data from {Config.DATASET_PATH}...")
        with open(Config.DATASET_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)

        doc_texts = []
        doc_metadatas = []
        self.doc_ids = []
        self.doc_map = {}
        
        for item in data:
            doc_id = item['image_id']
            text_chunk = self._format_layout_text(item)
            
            # --- Structural Analysis ---
            elements = item.get('elements', [])
            image_elements = [e for e in elements if e['type'] == 'figure']
            img_count = len(image_elements)
            
            # Determine dominant ratio (based on largest image)
            layout_ratio = "Square"
            if image_elements:
                largest_img = max(image_elements, key=lambda x: (x['coordinates']['x2'] - x['coordinates']['x1']) * (x['coordinates']['y2'] - x['coordinates']['y1']))
                coords = largest_img['coordinates']
                w = coords['x2'] - coords['x1']
                h = coords['y2'] - coords['y1']
                if w > h * 1.1:
                    layout_ratio = "Horizontal"
                elif h > w * 1.1:
                    layout_ratio = "Vertical"
            
            # Update raw item with these stats for easier access later
            item['image_count'] = img_count
            item['layout_ratio'] = layout_ratio
            
            self.doc_ids.append(doc_id)
            self.doc_map[doc_id] = item 
            doc_texts.append(text_chunk)
            
            doc_metadatas.append({
                "image_id": doc_id,
                "category": item.get('category', ''),
                "type": item.get('type', ''),
                "mood": item.get('mood', ''),
                "image_count": img_count,
                "layout_ratio": layout_ratio
            })

        print("Generating Embeddings...")
        output = self.model.encode(doc_texts, return_dense=True, return_sparse=True, return_colbert_vecs=False)
        
        dense_embeddings = output['dense_vecs']
        lexical_weights = output['lexical_weights']

        print("Upserting to ChromaDB...")
        self.collection.upsert(
            ids=self.doc_ids,
            embeddings=[vec.tolist() for vec in dense_embeddings],
            metadatas=doc_metadatas,
            documents=doc_texts
        )

        print("Updating Memory Sparse Index...")
        for doc_id, sparse_vec in zip(self.doc_ids, lexical_weights):
            self.sparse_index[doc_id] = sparse_vec
            
        print("Indexing Complete.")
        
    def get_layout(self, doc_id: str) -> Dict[str, Any]:
        """Retrieve raw layout data by ID."""
        return self.doc_map.get(doc_id)

    def compute_rrf(self, dense_results: List[str], sparse_results: List[str], k: int = 60) -> List[Tuple[str, float]]:
        scores = defaultdict(float)
        for rank, doc_id in enumerate(dense_results):
            scores[doc_id] += 1 / (k + rank + 1)
        for rank, doc_id in enumerate(sparse_results):
            scores[doc_id] += 1 / (k + rank + 1)
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    def search(self, query: str, filters: Dict[str, Any] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        print(f"Searching: {query} | Filters: {filters}")
        
        q_output = self.model.encode([query], return_dense=True, return_sparse=True)
        q_dense = q_output['dense_vecs'][0]
        q_sparse = q_output['lexical_weights'][0]

        # 1. Dense Search (with Chroma Filtering)
        if len(self.doc_ids) == 0:
             return []

        candidate_k = min(50, len(self.doc_ids))
        
        # Prepare Chroma Where clause
        chroma_where = {}
        if filters:
            # We only support exact match for now in this simple implementation
            # Chroma requires specific format. 
            # If multiple filters, use $and.
            conditions = []
            for k, v in filters.items():
                conditions.append({k: {"$eq": v}})
            
            if len(conditions) > 1:
                chroma_where = {"$and": conditions}
            elif len(conditions) == 1:
                chroma_where = conditions[0]

        dense_out = self.collection.query(
            query_embeddings=[q_dense.tolist()],
            n_results=candidate_k,
            where=chroma_where if chroma_where else None
        )
        dense_ids = dense_out['ids'][0] if dense_out['ids'] else []

        # 2. Sparse Search (Manual Filtering)
        sparse_scores = []
        for doc_id, doc_sparse in self.sparse_index.items():
            # Filter check
            if filters:
                item = self.doc_map.get(doc_id)
                if not item: continue
                match = True
                for k, v in filters.items():
                    if item.get(k) != v:
                        match = False
                        break
                if not match:
                    continue
            
            score = self.model.compute_lexical_matching_score(doc_sparse, q_sparse)
            sparse_scores.append((doc_id, score))
        
        sparse_scores.sort(key=lambda x: x[1], reverse=True)
        sparse_ids = [x[0] for x in sparse_scores[:candidate_k]]

        # 3. RRF
        rrf_ranks = self.compute_rrf(dense_ids, sparse_ids)
        
        results = []
        for doc_id, score in rrf_ranks[:top_k]:
            doc_data = self.doc_map.get(doc_id)
            if doc_data:
                results.append({
                    "image_id": doc_id,
                    "rrf_score": score,
                    "category": doc_data.get('category'),
                    "mood": doc_data.get('mood'),
                    "type": doc_data.get('type')
                })
        return results



# Global instance placeholders
analyzer = None
retriever = None

def setup_rag():
    global analyzer, retriever
    analyzer = GeminiAnalyzer()
    retriever = ChromaHybridRetriever()
