"""
RAG Module with Voyage AI voyage-3.5 Embedding
==============================================
Original: rag_modules.py (BGE-M3 + Hybrid Search)
Changed: Voyage-3.5 + Dense Only (Dot Product / Inner Product)
"""

import os
import json
import chromadb
import google.generativeai as genai
from typing import List, Dict, Any, Tuple
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
    VOYAGE_API_KEY = os.getenv("VOY_API_KEY")  # Voyage API Key
    CHROMA_DB_PATH = "./chroma_db_voyage"  # Separate DB for Voyage embeddings
    COLLECTION_NAME = "magazine_layouts_voyage"
    DATASET_PATH = "./datas/final_final_dataset.json"
    VOYAGE_MODEL = "voyage-3.5"  # Model selection
    VOYAGE_DIMENSIONS = 512  # Dimension (256, 512, 1024, 2048 available)

    @staticmethod
    def validate():
        if not Config.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not found in .env file")
        if not Config.VOYAGE_API_KEY:
            raise ValueError("VOY_API_KEY not found in .env file")


class GeminiAnalyzer:
    """Same as original - Uses Gemini for content analysis"""
    def __init__(self):
        Config.validate()
        genai.configure(api_key=Config.GOOGLE_API_KEY)
        self.model_name = 'gemini-2.5-flash'
        self.model = genai.GenerativeModel(self.model_name)

    def analyze_page(self, images: List[Any], title: str, body: str) -> Dict[str, str]:
        """Analyze a single page's content (Images + Text) to extract metadata."""
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

    async def aura_render(self, layout_data: Dict[str, Any], user_content: Dict[str, Any]) -> str:
        """
        Integration with AURA MCP Service for high-quality layout generation.
        """
        from tool.mcp_client import mcp_client
        from image_validator import image_validator
        
        headline = user_content.get('title', 'Untitled')
        body = user_content.get('body', '')
        analysis = user_content.get('analysis', {})
        
        # 🖼️ Image validation and processing
        raw_images = user_content.get('images', [])
        user_images = []
        
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
                from PIL import Image
                import io
                import base64 as b64
                
                if img_b64.startswith("data:"):
                    base64_data = img_b64.split(",")[1]
                else:
                    base64_data = img_b64
                image_bytes = b64.b64decode(base64_data)
                temp_img = Image.open(io.BytesIO(image_bytes))
                orig_width, orig_height = temp_img.size
                
                aspect_ratio = orig_width / orig_height
                slot_height = max_height
                slot_width = int(slot_height * aspect_ratio)
                
                max_width = 400
                if slot_width > max_width:
                    slot_width = max_width
                    slot_height = int(slot_width / aspect_ratio)
                
                print(f"  📐 [Image {i}] Original: {orig_width}x{orig_height}, Slot: {slot_width}x{slot_height}")
                
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
                    print(f"  ⚠️ [Image {i}] Validation failed, using original")
            except Exception as e:
                user_images.append(img_b64)
                print(f"  ⚠️ [Image {i}] Error during validation: {e}")
        
        placeholders = [f"__IMAGE_{i}__" for i in range(len(user_images))]
        
        vision_context = {
            "keywords": analysis.get('visual_keywords', []),
            "description": analysis.get('description', ''),
            "dominant_colors": "Analyze from keywords",
            "visual_style": analysis.get('mood', 'Modern')
        }
        
        page_layout_type = user_content.get('layout_type', 'article')
        design_spec = {
            "mood": analysis.get('mood', 'Modern'),
            "category": analysis.get('category', 'Magazine'),
            "layout_type": analysis.get('type', 'Balanced'),
            "page_type": page_layout_type,
            "visual_keywords": analysis.get('visual_keywords', []),
            "typography_style": self._suggest_typography(analysis.get('category', 'Magazine')),
            "color_scheme": self._suggest_color_scheme(analysis.get('mood', 'Modern'))
        }
        
        image_count = len(user_images)
        if image_count > 2:
            layout_strategy = "Mosaic or Grid"
        elif image_count == 2:
            layout_strategy = "Split or Collage"
        else:
            layout_strategy = "Hero Image"
        
        elements = layout_data.get('elements', [])
        plan_json = {
            "reference_id": layout_data.get('image_id'),
            "elements": elements,
            "spatial_summary": self._summarize_layout(elements),
            "suggested_strategy": layout_strategy
        }
        
        try:
            print(f"🍌 [AURA] Calling MCP for: {headline[:30]}")
            print(f"   Strategy: {layout_strategy}, Mood: {design_spec['mood']}")
            
            html = await mcp_client.generate_layout(
                headline=headline,
                body=body,
                image_data=placeholders,
                layout_override=page_layout_type.upper(),
                vision_json=json.dumps(vision_context),
                design_json=json.dumps(design_spec),
                plan_json=json.dumps(plan_json)
            )
            
            # Image Placeholder Injection
            for i, img_b64 in enumerate(user_images):
                injected = False
                
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
                
                if not injected:
                    url_pattern = f"url({patterns[0]})"
                    if url_pattern in html:
                        html = html.replace(url_pattern, f"url({img_b64})")
                        print(f"  ✅ [Image {i}] Injected via url() pattern")
                        injected = True
                
                if not injected:
                    print(f"  ⚠️ [Image {i}] No placeholder found! Forcing injection...")
                    img_tag = f'<img src="{img_b64}" class="w-[30%] h-[120px] object-cover inline-block mx-2 my-2" alt="Image {i}" />'
                    
                    if '</div>' in html:
                        last_div_pos = html.rfind('</div>')
                        html = html[:last_div_pos] + img_tag + html[last_div_pos:]
                    else:
                        html = html + img_tag
            
            # Tailwind CSS Script Injection
            tailwind_script = '<script src="https://cdn.tailwindcss.com"></script>\n'
            if "<head>" in html:
                html = html.replace("<head>", f"<head>\n{tailwind_script}")
            elif "<html>" in html:
                html = html.replace("<html>", f"<html>\n<head>{tailwind_script}</head>")
            else:
                html = tailwind_script + html

            return html
        except Exception as e:
            print(f"❌ [AURA] Integration Error: {e}")
            return ""
    
    def _suggest_typography(self, category: str) -> str:
        typography_map = {
            "Fashion": "Elegant serif, high contrast",
            "Tech": "Modern sans-serif, clean",
            "Travel": "Adventurous, mixed fonts",
            "Food": "Warm, inviting serif",
            "Business": "Professional sans-serif"
        }
        return typography_map.get(category, "Balanced, readable")
    
    def _suggest_color_scheme(self, mood: str) -> str:
        color_map = {
            "Minimalist": "Monochrome with accent",
            "Energetic": "Vibrant, high saturation",
            "Luxurious": "Gold, deep colors",
            "Emotional": "Warm tones",
            "Professional": "Navy, gray, white"
        }
        return color_map.get(mood, "Balanced palette")
    
    def _summarize_layout(self, elements: List[Dict]) -> str:
        if not elements:
            return "Flexible layout"
        
        image_count = sum(1 for e in elements if e.get('type') == 'figure')
        text_count = sum(1 for e in elements if e.get('type') in ['title', 'plain text'])
        
        top_heavy = sum(1 for e in elements if e.get('coordinates', {}).get('y1', 0) < 400)
        bottom_heavy = len(elements) - top_heavy
        
        layout_desc = f"{image_count} images, {text_count} text blocks. "
        if top_heavy > bottom_heavy:
            layout_desc += "Top-heavy composition."
        else:
            layout_desc += "Bottom-heavy composition."
        
        return layout_desc


class VoyageRetriever:
    """
    Voyage AI voyage-3.5 based retriever.
    Uses Dense Only search with Dot Product (Inner Product).
    """
    def __init__(self):
        import voyageai
        
        print(f"🚀 Initializing Voyage AI Retriever...")
        print(f"   Model: {Config.VOYAGE_MODEL}")
        print(f"   Dimensions: {Config.VOYAGE_DIMENSIONS}")
        
        # Initialize Voyage client
        self.client = voyageai.Client(api_key=Config.VOYAGE_API_KEY)
        
        # Initialize ChromaDB
        print(f"   Connecting to ChromaDB at {Config.CHROMA_DB_PATH}...")
        self.chroma_client = chromadb.PersistentClient(path=Config.CHROMA_DB_PATH)
        self.collection = self.chroma_client.get_or_create_collection(
            name=Config.COLLECTION_NAME,
            metadata={"hnsw:space": "ip"}  # Inner Product (Dot Product) similarity
        )
        
        self.doc_ids: List[str] = []
        self.doc_map: Dict[str, Any] = {}
        
        # Cache management
        self.cache_path = "./index_cache_voyage.pkl"
        
        import hashlib
        import inspect
        logic_source = inspect.getsource(self.index_data)
        logic_hash = hashlib.md5(logic_source.encode()).hexdigest()[:8]
        # Include distance metric in version to invalidate cache when it changes
        distance_metric = self.collection.metadata.get('hnsw:space', 'unknown')
        self.CACHE_VERSION = f"voyage-1.0-{distance_metric}-{logic_hash}"
        
        if self._load_from_cache():
            logger.info(f"✅ Loaded Voyage index from cache (v{self.CACHE_VERSION}).")
        else:
            logger.info("⚡ Voyage index not found. Re-indexing...")
            self.index_data()
            self._save_to_cache()

    def _save_to_cache(self):
        try:
            with open(self.cache_path, 'wb') as f:
                pickle.dump({
                    'version': self.CACHE_VERSION,
                    'doc_map': self.doc_map,
                    'doc_ids': self.doc_ids
                }, f)
            logger.info(f"Saved Voyage index to {self.cache_path}")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def _load_from_cache(self) -> bool:
        if not os.path.exists(self.cache_path):
            return False
        try:
            if os.path.exists(Config.DATASET_PATH):
                if os.path.getmtime(Config.DATASET_PATH) > os.path.getmtime(self.cache_path):
                    logger.info("Dataset modified. Invalidating cache.")
                    return False
            
            with open(self.cache_path, 'rb') as f:
                data = pickle.load(f)
                
                cached_version = data.get('version', '0.0.0')
                if cached_version != self.CACHE_VERSION:
                    logger.info(f"Cache version mismatch. Invalidate.")
                    return False
                
                self.doc_map = data['doc_map']
                self.doc_ids = data['doc_ids']
            return True
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            return False

    def _format_layout_text(self, item: Dict[str, Any]) -> str:
        """Format layout data into searchable text."""
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

    def _get_voyage_embeddings(self, texts: List[str], input_type: str = "document") -> List[List[float]]:
        """
        Get embeddings from Voyage AI API.
        
        Args:
            texts: List of texts to embed
            input_type: "document" for indexing, "query" for searching
        
        Returns:
            List of embedding vectors
        """
        # Voyage API has batch size limits, process in chunks
        batch_size = 128
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            
            result = self.client.embed(
                batch,
                model=Config.VOYAGE_MODEL,
                input_type=input_type,
                output_dimension=Config.VOYAGE_DIMENSIONS  # Matryoshka dimension
            )
            
            all_embeddings.extend(result.embeddings)
            
            if i + batch_size < len(texts):
                print(f"   Embedded {i + batch_size}/{len(texts)} documents...")
        
        return all_embeddings

    def index_data(self):
        """Load JSON, generate Voyage embeddings, and populate ChromaDB."""
        if not os.path.exists(Config.DATASET_PATH):
            print(f"Dataset not found at {Config.DATASET_PATH}")
            return

        print(f"📚 Indexing data with Voyage-3.5...")
        with open(Config.DATASET_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)

        doc_texts = []
        doc_metadatas = []
        self.doc_ids = []
        self.doc_map = {}
        
        for item in data:
            doc_id = item['image_id']
            text_chunk = self._format_layout_text(item)
            
            # Structural Analysis
            elements = item.get('elements', [])
            image_elements = [e for e in elements if e['type'] == 'figure']
            img_count = len(image_elements)
            
            layout_ratio = "Square"
            if image_elements:
                largest_img = max(image_elements, key=lambda x: 
                    (x['coordinates']['x2'] - x['coordinates']['x1']) * 
                    (x['coordinates']['y2'] - x['coordinates']['y1']))
                coords = largest_img['coordinates']
                w = coords['x2'] - coords['x1']
                h = coords['y2'] - coords['y1']
                if w > h * 1.1:
                    layout_ratio = "Horizontal"
                elif h > w * 1.1:
                    layout_ratio = "Vertical"
            
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

        # Generate Voyage embeddings
        print(f"🔄 Generating Voyage embeddings for {len(doc_texts)} documents...")
        embeddings = self._get_voyage_embeddings(doc_texts, input_type="document")
        
        # Verify embeddings are normalized for dot product (optional but recommended)
        # Voyage AI embeddings should be pre-normalized
        if embeddings:
            sample_norm = sum(x**2 for x in embeddings[0]) ** 0.5
            if abs(sample_norm - 1.0) > 0.01:
                logger.warning(f"⚠️ Embeddings may not be normalized (norm={sample_norm:.4f}). Dot product may not work as expected.")

        # Upsert to ChromaDB
        print("💾 Upserting to ChromaDB...")
        self.collection.upsert(
            ids=self.doc_ids,
            embeddings=embeddings,
            metadatas=doc_metadatas,
            documents=doc_texts
        )
        
        print(f"✅ Voyage indexing complete! {len(self.doc_ids)} documents indexed.")

    def get_layout(self, doc_id: str) -> Dict[str, Any]:
        """Retrieve raw layout data by ID."""
        return self.doc_map.get(doc_id)

    def search(self, query: str, filters: Dict[str, Any] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar layouts using Voyage embeddings.
        Uses Dense Only search with Dot Product (Inner Product).
        """
        print(f"🔍 [Voyage] Searching: {query}")
        if filters:
            print(f"   Filters: {filters}")
        
        # Get query embedding
        query_embedding = self._get_voyage_embeddings([query], input_type="query")[0]
        
        # Prepare ChromaDB where clause
        chroma_where = None
        if filters:
            conditions = []
            for k, v in filters.items():
                conditions.append({k: {"$eq": v}})
            
            if len(conditions) > 1:
                chroma_where = {"$and": conditions}
            elif len(conditions) == 1:
                chroma_where = conditions[0]
        
        # Query ChromaDB (Dot Product/Inner Product is configured at collection level)
        candidate_k = min(50, len(self.doc_ids)) if self.doc_ids else top_k
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=candidate_k,
            where=chroma_where
        )
        
        # Format results
        output = []
        if results['ids'] and results['ids'][0]:
            for i, doc_id in enumerate(results['ids'][0][:top_k]):
                doc_data = self.doc_map.get(doc_id)
                if doc_data:
                    # ChromaDB returns distances
                    # For inner product (dot product), the distance IS the similarity score
                    # Higher values = more similar (unlike cosine distance where lower is better)
                    distance = results['distances'][0][i] if results.get('distances') else 0
                    similarity = distance  # For inner product, distance = similarity
                    
                    output.append({
                        "image_id": doc_id,
                        "similarity_score": round(similarity, 4),
                        "category": doc_data.get('category'),
                        "mood": doc_data.get('mood'),
                        "type": doc_data.get('type')
                    })
        
        print(f"   Found {len(output)} results")
        return output


# Global instance placeholders
analyzer = None
retriever = None

def setup_rag():
    """Initialize RAG components with Voyage embeddings."""
    global analyzer, retriever
    analyzer = GeminiAnalyzer()
    retriever = VoyageRetriever()
    print("✅ Voyage RAG system initialized!")
