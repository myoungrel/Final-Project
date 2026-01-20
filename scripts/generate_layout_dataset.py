"""
Image Layout Analyzer Script
============================
Gemini 2.5 Flash를 사용하여 image_data/ 폴더의 이미지를 분석하고
dataset.json과 동일한 형식의 JSON 데이터를 생성합니다.

Usage:
    python scripts/generate_layout_dataset.py

Output:
    datas/dataset_new.json
"""

import os
import json
import time
import base64
from pathlib import Path
from typing import List, Dict, Any
from PIL import Image
import io
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
IMAGE_DIR = "./image_data"
OUTPUT_PATH = "./datas/dataset_final.json"
MODEL_NAME = "gemini-2.5-flash"

# Rate limit settings
BATCH_SIZE = 10  # Process 10 images then pause
DELAY_BETWEEN_BATCHES = 5  # seconds


def setup_gemini():
    """Initialize Gemini API."""
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not found in .env file")
    genai.configure(api_key=GOOGLE_API_KEY)
    return genai.GenerativeModel(MODEL_NAME)


def load_image_as_pil(image_path: str) -> Image.Image:
    """Load image and return PIL Image."""
    return Image.open(image_path)


def analyze_layout_with_gemini(model, image: Image.Image, image_id: str) -> Dict[str, Any]:
    """
    Analyze magazine layout image using Gemini Vision.
    Returns data in dataset.json format.
    """
    prompt = """
You are an expert magazine layout analyzer. Analyze this magazine page layout image and extract the following information.

Return a JSON object with this exact structure:
{
    "total_elements": <number of distinct elements>,
    "elements": [
        {
            "id": <0-based index>,
            "type": "<one of: title, plain text, figure, abandon>",
            "coordinates": {
                "x1": <left boundary in pixels>,
                "y1": <top boundary in pixels>,
                "x2": <right boundary in pixels>,
                "y2": <bottom boundary in pixels>
            },
            "confidence": <0.0 to 1.0>,
            "text": "<extracted text if type is title or plain text, otherwise omit>",
            "ocr_confidence": <0.0 to 1.0, only if text is present>
        }
    ],
    "mood": "<one of: Minimalist, Energetic, Luxurious, Emotional, Professional, Trendy, Innovative, Elegant, Clean, Vibrant>",
    "description": "<2-3 sentence description of the layout style and content>",
    "category": "<one of: fashion, beauty, lifestyle, travel, food, tech, business>",
    "type": "<one of: Cover, Article, Advertisement, Editorial, Product_Showcase, Celebrity_Lifestyle, Real_Life_Story>"
}

Element types:
- "title": Headlines, subheadlines, section titles
- "plain text": Body text, captions, descriptions
- "figure": Images, photos, illustrations
- "abandon": Decorative elements, page numbers, logos to ignore

Estimate coordinates based on the image dimensions. Be accurate with bounding boxes.
Only return valid JSON, no markdown formatting or extra text.
"""

    try:
        response = model.generate_content([prompt, image])
        text = response.text.strip()
        
        # Clean up response
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        result = json.loads(text)
        
        # Add image metadata
        result["image_id"] = image_id
        result["image_path"] = os.path.abspath(os.path.join(IMAGE_DIR, image_id))
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"  ⚠️ JSON parse error for {image_id}: {e}")
        print(f"  Raw response: {text[:200]}...")
        return create_fallback_entry(image_id)
    except Exception as e:
        print(f"  ❌ Error analyzing {image_id}: {e}")
        return create_fallback_entry(image_id)


def create_fallback_entry(image_id: str) -> Dict[str, Any]:
    """Create a fallback entry when analysis fails."""
    return {
        "image_id": image_id,
        "image_path": os.path.abspath(os.path.join(IMAGE_DIR, image_id)),
        "total_elements": 1,
        "elements": [
            {
                "id": 0,
                "type": "figure",
                "coordinates": {"x1": 0, "y1": 0, "x2": 800, "y2": 1000},
                "confidence": 0.5
            }
        ],
        "mood": "General",
        "description": "Layout analysis failed. Manual review required.",
        "category": "lifestyle",
        "type": "Article"
    }


def get_image_files(directory: str) -> List[str]:
    """Get all image files from directory."""
    valid_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    files = []
    
    for filename in sorted(os.listdir(directory)):
        ext = Path(filename).suffix.lower()
        if ext in valid_extensions:
            files.append(filename)
    
    return files


def main():
    print("=" * 60)
    print("📸 Magazine Layout Dataset Generator")
    print("=" * 60)
    print(f"Model: {MODEL_NAME}")
    print(f"Input: {IMAGE_DIR}")
    print(f"Output: {OUTPUT_PATH}")
    print()
    
    # Setup
    model = setup_gemini()
    print("✅ Gemini model initialized")
    
    # Get images
    image_files = get_image_files(IMAGE_DIR)
    total_images = len(image_files)
    print(f"📁 Found {total_images} images to process")
    print()
    
    if total_images == 0:
        print("No images found. Exiting.")
        return
    
    # Process images
    dataset = []
    success_count = 0
    error_count = 0
    
    for i, filename in enumerate(image_files):
        image_path = os.path.join(IMAGE_DIR, filename)
        
        print(f"[{i+1}/{total_images}] Analyzing: {filename}")
        
        try:
            image = load_image_as_pil(image_path)
            result = analyze_layout_with_gemini(model, image, filename)
            dataset.append(result)
            success_count += 1
            print(f"  ✅ Success - {result.get('total_elements', 0)} elements, {result.get('mood', 'Unknown')} mood")
            
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            dataset.append(create_fallback_entry(filename))
            error_count += 1
        
        # Rate limiting
        if (i + 1) % BATCH_SIZE == 0 and (i + 1) < total_images:
            print(f"\n⏳ Batch complete. Waiting {DELAY_BETWEEN_BATCHES}s...\n")
            time.sleep(DELAY_BETWEEN_BATCHES)
    
    # Save results
    print()
    print("=" * 60)
    print("💾 Saving dataset...")
    
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved to: {OUTPUT_PATH}")
    print()
    print("📊 Summary:")
    print(f"   Total images: {total_images}")
    print(f"   Success: {success_count}")
    print(f"   Errors: {error_count}")
    print()
    
    # Show sample
    if dataset:
        print("📋 Sample entry:")
        sample = dataset[0]
        print(f"   ID: {sample.get('image_id')}")
        print(f"   Elements: {sample.get('total_elements')}")
        print(f"   Mood: {sample.get('mood')}")
        print(f"   Category: {sample.get('category')}")
        print(f"   Type: {sample.get('type')}")


if __name__ == "__main__":
    main()
