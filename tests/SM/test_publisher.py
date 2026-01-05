# /home/sauser/final/Final-Project/tests/SM/test_publisher.py
import os
import base64
import io  # 바이너리 데이터를 메모리에서 다루기 위한 모듈
from PIL import Image  # 이미지 리사이징 및 압축을 위한 라이브러리
from jinja2 import Environment, FileSystemLoader

# [신규 추가] 이미지 과부하 방지를 위한 최적화 함수
def optimize_image(image_path, max_width=1024):
    """
    원본 이미지를 잡지 레이아웃에 맞게 줄이고 압축하여 Base64로 변환합니다.
    - 용량이 크면 HTML 파일이 무거워져 렌더링 에러가 날 수 있기 때문입니다.
    """
    try:
        with Image.open(image_path) as img:
            # 1. 가로가 max_width보다 크면 비율을 유지하며 축소
            if img.width > max_width:
                ratio = max_width / float(img.width)
                new_height = int(float(img.height) * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            # 2. 색상 모드를 RGB로 통일 (PNG의 투명도 등을 JPEG 표준에 맞춤)
            img = img.convert("RGB")
            
            # 3. 메모리(Buffer)에 JPEG 형식으로 압축 저장 (품질 75% 설정)
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=75)
            
            # 4. 압축된 데이터의 Base64 문자열 반환
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"⚠️ 이미지 최적화 실패: {e}")
        return None

def run_universal_publisher_test():
    print("--- [Node 7] Publisher: 범용 조립 및 이미지 최적화 테스트 시작 ---")
    
    # [1단계: 경로 설정]
    # 현재 파일 위치: tests/SM/
    # 템플릿 위치: ../../templates (프로젝트 루트의 templates)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.normpath(os.path.join(current_dir, "../../templates"))
    
    # [2단계: SDUI 데이터 구조 설계]
    # 'items' 대신 'product_list'를 사용하여 Jinja2 기본 함수와의 이름 충돌을 피함
    magazine_state = {
        "style": {
            "primary_color": "#FF8A00",  # 포인트 컬러
            "font_family": "font-serif", # 명조체 스타일
            "bg_color": "#F8FAFC"        # 배경색 가이드
        },
        "content": {
            "title": "2026 SKINCARE SPECIAL",
            "page": 24,
            "blocks": [
                {
                    "type": "hero_cover",
                    "img_id": "사진4-1.png",
                    "headline": "HIGH-PERFORMANCE ITEMS"
                },
                {
                    "type": "product_list",
                    "subtitle": "YOU WANT 수분·탄력",
                    "product_list": ["유세린 에피셀린 세럼", "아벤느 히알루론 세럼", "오에라 프레스티지 크림"]
                },
                {
                    "type": "text_essay",
                    "text": "피부 고민별로 순하지만 강력한 필수템을 모았다. 자극 없이 속까지 채우는..."
                }
            ]
        },
        "meta": {"editor": "김지혜", "photographer": "이민섭"}
    }

    # [3단계: 이미지 최적화 및 인코딩]
    # tests/SM/ 폴더 안에 sample.png가 있다면 최적화하고, 없으면 더미 데이터 사용
    image_file_path = os.path.join(current_dir, "sample.png")
    
    if os.path.exists(image_file_path):
        real_base64 = optimize_image(image_file_path)
        print("📸 실제 이미지를 최적화하여 인코딩했습니다.")
    else:
        # 파일이 없을 때 사용하는 1x1 픽셀 더미 데이터
        real_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        print("⚠️ sample.png가 없어 더미 데이터를 사용합니다.")

    images_dict = {"사진4-1.png": real_base64}

    # [4단계: Jinja2 렌더링 (조립)]
    try:
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template('magazine_layout.html')
        
        # 데이터 주입
        html_output = template.render(data=magazine_state, images=images_dict)
        
        # [5단계: 결과물 저장]
        output_path = os.path.join(current_dir, "universal_result.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_output)
            
        print(f"✅ 성공: {output_path} 생성 완료!")
        
    except Exception as e:
        print(f"❌ 렌더링 에러 발생: {e}")

if __name__ == "__main__":
    run_universal_publisher_test()