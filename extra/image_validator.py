"""
[Image Validator Module]
이미지가 레이아웃에서 잘리지 않도록 검수하고 처리하는 모듈입니다.

주요 기능:
1. 이미지 비율 검사 및 조정
2. 레이아웃 슬롯에 맞게 이미지 리사이징/크롭
3. 이미지 품질 검증
"""

from PIL import Image
import io
import base64
from typing import Tuple, Optional, Dict, Any, List, Union

class ImageValidator:
    """
    이미지 검수 및 처리 클래스
    레이아웃에 맞게 이미지를 조정하여 잘림 현상을 방지합니다.
    """
    
    # 매거진 레이아웃용 표준 비율 정의
    ASPECT_RATIOS = {
        "portrait": (2, 3),      # 세로형 (잡지 전면)
        "landscape": (16, 9),    # 가로형
        "square": (1, 1),        # 정사각형
        "wide": (21, 9),         # 와이드
        "magazine_full": (210, 297),  # A4 비율 (잡지 전체 페이지)
        "magazine_half": (210, 148),  # A4 절반
    }
    
    # 최소/최대 해상도 기준
    MIN_WIDTH = 400
    MIN_HEIGHT = 400
    MAX_WIDTH = 4000
    MAX_HEIGHT = 4000
    
    def __init__(self, default_quality: int = 95):
        """
        Args:
            default_quality: JPEG 저장 시 기본 품질 (1-100)
        """
        self.default_quality = default_quality
    
    def validate_image(self, image: Image.Image) -> Dict[str, Any]:
        """
        이미지 유효성 검사
        
        Args:
            image: PIL Image 객체
            
        Returns:
            검증 결과 딕셔너리
        """
        width, height = image.size
        
        result = {
            "is_valid": True,
            "width": width,
            "height": height,
            "aspect_ratio": round(width / height, 2),
            "orientation": self._get_orientation(width, height),
            "warnings": [],
            "errors": []
        }
        
        # 최소 해상도 체크
        if width < self.MIN_WIDTH or height < self.MIN_HEIGHT:
            result["warnings"].append(
                f"이미지 해상도가 낮습니다 ({width}x{height}). "
                f"최소 권장: {self.MIN_WIDTH}x{self.MIN_HEIGHT}"
            )
        
        # 최대 해상도 체크
        if width > self.MAX_WIDTH or height > self.MAX_HEIGHT:
            result["warnings"].append(
                f"이미지가 매우 큽니다 ({width}x{height}). 리사이징을 권장합니다."
            )
        
        # 극단적인 비율 체크
        aspect = width / height
        if aspect < 0.3 or aspect > 3.0:
            result["warnings"].append(
                f"이미지 비율이 극단적입니다 ({result['aspect_ratio']}:1). "
                "레이아웃에서 잘릴 수 있습니다."
            )
        
        return result
    
    def _get_orientation(self, width: int, height: int) -> str:
        """이미지 방향 감지"""
        if width > height * 1.1:
            return "landscape"
        elif height > width * 1.1:
            return "portrait"
        else:
            return "square"
    
    def fit_to_slot(
        self, 
        image: Image.Image, 
        slot_width: int, 
        slot_height: int,
        mode: str = "contain"
    ) -> Image.Image:
        """
        이미지를 슬롯 크기에 맞게 조정 (잘림 방지)
        
        Args:
            image: 원본 PIL Image
            slot_width: 슬롯 너비
            slot_height: 슬롯 높이
            mode: 
                - "contain": 이미지 전체가 보이도록 축소 (여백 가능)
                - "cover": 슬롯을 채우도록 확대 (일부 잘림 가능)
                - "smart_crop": 중요 부분 유지하며 크롭
                
        Returns:
            조정된 PIL Image
        """
        orig_width, orig_height = image.size
        
        if mode == "contain":
            return self._contain_fit(image, slot_width, slot_height)
        elif mode == "cover":
            return self._cover_fit(image, slot_width, slot_height)
        elif mode == "smart_crop":
            return self._smart_crop(image, slot_width, slot_height)
        else:
            return self._contain_fit(image, slot_width, slot_height)
    
    def _contain_fit(
        self, 
        image: Image.Image, 
        target_width: int, 
        target_height: int
    ) -> Image.Image:
        """
        이미지 전체가 보이도록 비율 유지하며 리사이징
        이미지가 절대 잘리지 않음을 보장
        """
        orig_width, orig_height = image.size
        
        # 비율 계산
        width_ratio = target_width / orig_width
        height_ratio = target_height / orig_height
        
        # 더 작은 비율 사용 (이미지 전체가 들어오도록)
        ratio = min(width_ratio, height_ratio)
        
        new_width = int(orig_width * ratio)
        new_height = int(orig_height * ratio)
        
        # 고품질 리사이징
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return resized
    
    def _cover_fit(
        self, 
        image: Image.Image, 
        target_width: int, 
        target_height: int
    ) -> Image.Image:
        """
        슬롯을 완전히 채우도록 리사이징 후 중앙 크롭
        """
        orig_width, orig_height = image.size
        
        # 비율 계산
        width_ratio = target_width / orig_width
        height_ratio = target_height / orig_height
        
        # 더 큰 비율 사용 (슬롯을 완전히 채우도록)
        ratio = max(width_ratio, height_ratio)
        
        new_width = int(orig_width * ratio)
        new_height = int(orig_height * ratio)
        
        # 리사이징
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 중앙 크롭
        left = (new_width - target_width) // 2
        top = (new_height - target_height) // 2
        right = left + target_width
        bottom = top + target_height
        
        cropped = resized.crop((left, top, right, bottom))
        
        return cropped
    
    def _smart_crop(
        self, 
        image: Image.Image, 
        target_width: int, 
        target_height: int
    ) -> Image.Image:
        """
        스마트 크롭: 이미지의 중요한 부분을 유지하면서 크롭
        - 인물 사진: 얼굴/상체 중심
        - 풍경 사진: 중앙 중심
        - 세로 이미지: 상단 1/3 지점 중심 (황금비)
        """
        orig_width, orig_height = image.size
        
        # 비율 계산
        width_ratio = target_width / orig_width
        height_ratio = target_height / orig_height
        
        ratio = max(width_ratio, height_ratio)
        
        new_width = int(orig_width * ratio)
        new_height = int(orig_height * ratio)
        
        # 리사이징
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 스마트 크롭 위치 계산
        # 세로 이미지의 경우 상단 1/3 지점 중심 (인물 사진 대비)
        if new_height > new_width:
            # 세로 이미지: 상단 1/3 지점 중심
            center_y = new_height // 3
            top = max(0, center_y - target_height // 2)
            top = min(top, new_height - target_height)
        else:
            # 가로 이미지: 중앙 중심
            top = (new_height - target_height) // 2
        
        left = (new_width - target_width) // 2
        right = left + target_width
        bottom = top + target_height
        
        cropped = resized.crop((left, top, right, bottom))
        
        return cropped
    
    def prepare_for_layout(
        self, 
        image: Union[Image.Image, str, bytes],
        layout_type: str = "magazine_full",
        slot_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        레이아웃용 이미지 준비 (메인 API)
        
        Args:
            image: PIL Image, Base64 문자열, 또는 bytes
            layout_type: 레이아웃 타입 (portrait, landscape, square, magazine_full 등)
            slot_info: 슬롯 정보 딕셔너리 {"width": px, "height": px, "position": str}
            
        Returns:
            {
                "success": bool,
                "processed_image": PIL Image,
                "base64": str (data URI),
                "validation": dict,
                "adjustments": list of str
            }
        """
        result = {
            "success": False,
            "processed_image": None,
            "base64": None,
            "validation": None,
            "adjustments": []
        }
        
        try:
            # 이미지 로드
            if isinstance(image, str):
                # Base64 문자열인 경우
                if image.startswith("data:"):
                    # data URI에서 base64 부분 추출
                    base64_data = image.split(",")[1]
                else:
                    base64_data = image
                image_bytes = base64.b64decode(base64_data)
                img = Image.open(io.BytesIO(image_bytes))
            elif isinstance(image, bytes):
                img = Image.open(io.BytesIO(image))
            else:
                img = image
            
            # RGB 모드 변환 (RGBA인 경우)
            if img.mode == 'RGBA':
                # 흰색 배경에 합성
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
                result["adjustments"].append("RGBA를 RGB로 변환")
            elif img.mode != 'RGB':
                img = img.convert('RGB')
                result["adjustments"].append(f"{img.mode}를 RGB로 변환")
            
            # 유효성 검사
            validation = self.validate_image(img)
            result["validation"] = validation
            
            # 슬롯 정보가 있는 경우 해당 크기에 맞게 조정
            if slot_info:
                slot_width = slot_info.get("width", 800)
                slot_height = slot_info.get("height", 600)
                fit_mode = slot_info.get("fit_mode", "contain")
                
                processed = self.fit_to_slot(img, slot_width, slot_height, mode=fit_mode)
                result["adjustments"].append(
                    f"슬롯에 맞게 조정: {img.size} -> {processed.size} ({fit_mode})"
                )
            else:
                # 레이아웃 타입에 따른 기본 처리
                if layout_type in self.ASPECT_RATIOS:
                    target_ratio = self.ASPECT_RATIOS[layout_type]
                    target_w, target_h = target_ratio
                    
                    # 기본 매거진 크기 (A4 기준)
                    if layout_type == "magazine_full":
                        slot_width, slot_height = 794, 1123  # A4 at 96dpi
                    elif layout_type == "magazine_half":
                        slot_width, slot_height = 794, 561
                    else:
                        # 비율에 맞게 800px 기준으로 계산
                        slot_width = 800
                        slot_height = int(800 * target_h / target_w)
                    
                    processed = self.fit_to_slot(img, slot_width, slot_height, mode="contain")
                    result["adjustments"].append(
                        f"{layout_type} 비율로 조정: {img.size} -> {processed.size}"
                    )
                else:
                    processed = img
            
            result["processed_image"] = processed
            result["success"] = True
            
            # Base64 변환
            buffered = io.BytesIO()
            processed.save(buffered, format="PNG", quality=self.default_quality)
            base64_str = base64.b64encode(buffered.getvalue()).decode()
            result["base64"] = f"data:image/png;base64,{base64_str}"
            
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
        
        return result
    
    def batch_prepare(
        self, 
        images: List[Union[Image.Image, str, bytes]],
        layout_type: str = "magazine_full",
        slot_infos: Optional[List[Dict]] = None
    ) -> List[Dict[str, Any]]:
        """
        여러 이미지 일괄 처리
        
        Args:
            images: 이미지 리스트
            layout_type: 레이아웃 타입
            slot_infos: 각 이미지별 슬롯 정보 (None이면 동일 적용)
            
        Returns:
            처리 결과 리스트
        """
        results = []
        
        for i, img in enumerate(images):
            slot_info = slot_infos[i] if slot_infos and i < len(slot_infos) else None
            result = self.prepare_for_layout(img, layout_type, slot_info)
            results.append(result)
        
        return results
    
    def get_optimal_css(
        self, 
        image: Image.Image, 
        container_width: int, 
        container_height: int
    ) -> Dict[str, str]:
        """
        이미지가 잘리지 않도록 최적의 CSS 속성 반환
        
        Args:
            image: PIL Image
            container_width: 컨테이너 너비
            container_height: 컨테이너 높이
            
        Returns:
            CSS 속성 딕셔너리
        """
        img_width, img_height = image.size
        img_ratio = img_width / img_height
        container_ratio = container_width / container_height
        
        css = {
            "object-fit": "contain",
            "width": "100%",
            "height": "100%"
        }
        
        # 이미지 비율이 컨테이너보다 넓은 경우
        if img_ratio > container_ratio:
            css["object-fit"] = "contain"
            css["width"] = "100%"
            css["height"] = "auto"
        # 이미지 비율이 컨테이너보다 좁은 경우
        else:
            css["object-fit"] = "contain"
            css["width"] = "auto"
            css["height"] = "100%"
        
        return css


# 전역 인스턴스
image_validator = ImageValidator()


def validate_and_prepare_image(
    image_data: Union[str, bytes, Image.Image],
    slot_width: Optional[int] = None,
    slot_height: Optional[int] = None,
    fit_mode: str = "contain"
) -> Dict[str, Any]:
    """
    편의 함수: 이미지 검수 및 준비
    
    Args:
        image_data: 이미지 데이터 (Base64, bytes, 또는 PIL Image)
        slot_width: 슬롯 너비 (px)
        slot_height: 슬롯 높이 (px)
        fit_mode: "contain" (잘림 없음) 또는 "cover" (공백 없음)
        
    Returns:
        처리된 이미지 정보 딕셔너리
    """
    slot_info = None
    if slot_width and slot_height:
        slot_info = {
            "width": slot_width,
            "height": slot_height,
            "fit_mode": fit_mode
        }
    
    return image_validator.prepare_for_layout(
        image_data, 
        layout_type="magazine_full",
        slot_info=slot_info
    )


# 테스트 코드
if __name__ == "__main__":
    print("=" * 50)
    print("Image Validator 테스트")
    print("=" * 50)
    
    # 테스트 이미지 생성
    test_img = Image.new('RGB', (1600, 2400), color='lightblue')
    
    validator = ImageValidator()
    
    # 1. 유효성 검사
    print("\n[1] 유효성 검사:")
    validation = validator.validate_image(test_img)
    print(f"  크기: {validation['width']}x{validation['height']}")
    print(f"  비율: {validation['aspect_ratio']}")
    print(f"  방향: {validation['orientation']}")
    
    # 2. 슬롯 맞춤 테스트
    print("\n[2] 슬롯 맞춤 테스트:")
    
    # Contain 모드
    contained = validator.fit_to_slot(test_img, 800, 600, mode="contain")
    print(f"  Contain: {test_img.size} -> {contained.size}")
    
    # Cover 모드
    covered = validator.fit_to_slot(test_img, 800, 600, mode="cover")
    print(f"  Cover: {test_img.size} -> {covered.size}")
    
    # Smart Crop 모드
    smart = validator.fit_to_slot(test_img, 800, 600, mode="smart_crop")
    print(f"  Smart Crop: {test_img.size} -> {smart.size}")
    
    # 3. 레이아웃 준비
    print("\n[3] 레이아웃 준비:")
    result = validator.prepare_for_layout(test_img, layout_type="magazine_full")
    print(f"  성공: {result['success']}")
    print(f"  조정사항: {result['adjustments']}")
    if result['base64']:
        print(f"  Base64 길이: {len(result['base64'])} chars")
    
    print("\n" + "=" * 50)
    print("테스트 완료!")
