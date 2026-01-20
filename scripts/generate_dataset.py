#!/usr/bin/env python3
"""
Fashion Magazine Image Dataset Generator
Processes images from image_data/ and generates datas/dataset_new.json
Uses Gemini 2.5 Flash Vision for layout analysis
"""

import os
import json
import time
from PIL import Image
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Configuration
SOURCE_DIR = "./image_data"
OUTPUT_DIR = "./image_data/processed"
OUTPUT_JSON = "./datas/dataset_new.json"
DOUBLE_PAGE_THRESHOLD = 1.2
BATCH_SIZE = 10
BATCH_DELAY = 2.0  # seconds

def load_images(source_dir: str) -> list:
    """Step 1: Load images and extract basic info"""
    images = []
    for filename in sorted(os.listdir(source_dir)):
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue
        
        path = os.path.join(source_dir, filename)
        try:
            with Image.open(path) as img:
                width, height = img.size
                aspect_ratio = width / height
                
                images.append({
                    "filename": filename,
                    "path": os.path.abspath(path),
                    "width": width,
                    "height": height,
                    "aspect_ratio": aspect_ratio
                })
        except Exception as e:
            print(f"⚠️ Error loading {filename}: {e}")
    
    return images

def save_split_image(img: Image.Image, original_filename: str, side: str) -> str:
    """Save a split page image"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    base_name = os.path.splitext(original_filename)[0]
    new_filename = f"{base_name}_{side}.jpg"
    new_path = os.path.join(OUTPUT_DIR, new_filename)
    img.save(new_path, "JPEG", quality=95)
    return os.path.abspath(new_path)

def classify_and_split(image_info: dict) -> list:
    """Step 2: Classify as Single/Double and split if needed"""
    ratio = image_info["aspect_ratio"]
    
    # Single Page: return as-is
    if ratio <= DOUBLE_PAGE_THRESHOLD:
        return [{
            **image_info,
            "split_type": "single",
            "page_index": 0
        }]
    
    # Double Page: split at center
    print(f"  ✂️ Splitting double page: {image_info['filename']}")
    with Image.open(image_info["path"]) as img:
        width, height = img.size
        mid = width // 2
        
        # Left page
        left_page = img.crop((0, 0, mid, height))
        left_path = save_split_image(left_page, image_info["filename"], "left")
        
        # Right page
        right_page = img.crop((mid, 0, width, height))
        right_path = save_split_image(right_page, image_info["filename"], "right")
        
        return [
            {
                "filename": f"{os.path.splitext(image_info['filename'])[0]}_left.jpg",
                "original_filename": image_info["filename"],
                "path": left_path,
                "split_type": "left",
                "page_index": 0,
                "width": mid,
                "height": height,
                "aspect_ratio": mid / height
            },
            {
                "filename": f"{os.path.splitext(image_info['filename'])[0]}_right.jpg",
                "original_filename": image_info["filename"],
                "path": right_path,
                "split_type": "right",
                "page_index": 1,
                "width": width - mid,
                "height": height,
                "aspect_ratio": (width - mid) / height
            }
        ]

def analyze_layout(image_path: str) -> dict:
    """Step 3: Analyze layout using Gemini 2.5 Flash Vision"""
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    # Load image
    img = Image.open(image_path)
    width, height = img.size
    
    prompt = f"""
    Analyze this magazine page layout and extract all visual elements with PRECISE bounding box coordinates.
    Image dimensions: {width}x{height}px
    
    For EACH visual element you can identify, provide:
    1. type: "title", "plain text", "figure", or "abandon"
       - "title": Headlines, section headers, large text
       - "plain text": Body text, captions, descriptions
       - "figure": Images, photos, illustrations
       - "abandon": Logos, page numbers, decorative elements
    2. coordinates: bounding box as x1, y1 (top-left) and x2, y2 (bottom-right) in pixels
    3. confidence: your confidence score (0.0 to 1.0)
    4. text: extracted text (for title and plain text only)
    5. ocr_confidence: confidence of text extraction (0.0 to 1.0, only for text elements)
    
    Also analyze the overall layout:
    - mood: Minimalist, Vibrant, Elegant, Emotional, Luxurious, Trendy, etc.
    - description: Brief description of the layout composition
    - type: Image-Heavy, Text-Heavy, Balanced, Collage, Celebrity_Lifestyle, Advertisement
    
    Return ONLY valid JSON (no markdown, no explanation):
    {{
      "elements": [
        {{"id": 0, "type": "title", "coordinates": {{"x1": 50, "y1": 30, "x2": 400, "y2": 80}}, "confidence": 0.95, "text": "HEADLINE TEXT", "ocr_confidence": 0.92}},
        {{"id": 1, "type": "figure", "coordinates": {{"x1": 50, "y1": 100, "x2": 700, "y2": 600}}, "confidence": 0.90}},
        {{"id": 2, "type": "plain text", "coordinates": {{"x1": 50, "y1": 620, "x2": 400, "y2": 750}}, "confidence": 0.85, "text": "Body text content...", "ocr_confidence": 0.88}}
      ],
      "mood": "Elegant",
      "description": "Magazine spread with hero image and minimal text",
      "type": "Image-Heavy"
    }}
    """
    
    response = model.generate_content([prompt, img])
    
    # Parse JSON
    result_text = response.text.strip()
    
    # Extract JSON block if wrapped
    if "```json" in result_text:
        result_text = result_text.split("```json")[1].split("```")[0]
    elif "```" in result_text:
        result_text = result_text.split("```")[1].split("```")[0]
    
    result = json.loads(result_text.strip())
    result["total_elements"] = len(result.get("elements", []))
    
    return result

def generate_id(page_info: dict) -> str:
    """Generate unique ID for the page"""
    base_name = os.path.splitext(page_info["filename"])[0]
    return base_name

def main():
    print("=" * 60)
    print("🖼️  Fashion Magazine Dataset Generator")
    print("=" * 60)
    
    # Step 1: Load images
    print("\n📁 Step 1: Loading images...")
    images = load_images(SOURCE_DIR)
    print(f"   Found {len(images)} images")
    
    # Step 2: Classify and split
    print("\n✂️ Step 2: Classifying and splitting...")
    processed = []
    single_count = 0
    double_count = 0
    for img in images:
        pages = classify_and_split(img)
        if len(pages) == 1:
            single_count += 1
        else:
            double_count += 1
        processed.extend(pages)
    print(f"   Single pages: {single_count}")
    print(f"   Double pages split: {double_count} → {double_count * 2} pages")
    print(f"   Total pages to analyze: {len(processed)}")
    
    # Step 3: Analyze layouts
    print("\n🔍 Step 3: Analyzing layouts with Gemini Vision...")
    dataset = []
    errors = []
    
    for i, page in enumerate(processed):
        print(f"   [{i+1}/{len(processed)}] {page['filename']}...", end=" ")
        
        try:
            layout = analyze_layout(page["path"])
            
            entry = {
                "image_id": generate_id(page),
                "image_path": page["path"],
                "total_elements": layout.get("total_elements", 0),
                "elements": layout.get("elements", []),
                "mood": layout.get("mood", "Modern"),
                "description": layout.get("description", f"Layout from {page['filename']}"),
                "category": "fashion",
                "type": layout.get("type", "Balanced")
            }
            dataset.append(entry)
            print(f"✅ {entry['total_elements']} elements")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            errors.append({"filename": page["filename"], "error": str(e)})
            # Add placeholder entry
            dataset.append({
                "image_id": generate_id(page),
                "image_path": page["path"],
                "total_elements": 0,
                "elements": [],
                "mood": "Unknown",
                "description": f"Failed to analyze: {e}",
                "category": "fashion",
                "type": "Unknown"
            })
        
        # Rate limit handling
        if (i + 1) % BATCH_SIZE == 0 and i + 1 < len(processed):
            print(f"   ⏸️ Pausing {BATCH_DELAY}s for rate limit...")
            time.sleep(BATCH_DELAY)
    
    # Step 4: Save
    print("\n💾 Step 4: Saving dataset...")
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ DONE!")
    print("=" * 60)
    print(f"   Total entries: {len(dataset)}")
    print(f"   Successful: {len(dataset) - len(errors)}")
    print(f"   Errors: {len(errors)}")
    print(f"   Output: {OUTPUT_JSON}")
    
    if errors:
        print("\n⚠️ Errors:")
        for err in errors[:5]:  # Show first 5 errors
            print(f"   - {err['filename']}: {err['error']}")
        if len(errors) > 5:
            print(f"   ... and {len(errors) - 5} more")

if __name__ == "__main__":
    main()
