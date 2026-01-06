# src/agents/publisher.py
import os
import base64
import io
from PIL import Image
from jinja2 import Environment, FileSystemLoader

class PublisherAgent:
    def __init__(self, template_path="templates"):
        """
        Publisher 에이전트 초기화
        :param template_path: 템플릿 폴더명 (기본값: src/agents/templates)
        """
        # 1. 경로 설정 (절대 경로로 변환하여 에러 방지)
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.template_dir = os.path.join(self.current_dir, template_path)
        
        # 2. 템플릿 폴더/파일 자동 생성 (안전장치)
        if not os.path.exists(self.template_dir):
            os.makedirs(self.template_dir, exist_ok=True)
            print(f"📂 [Publisher] 템플릿 폴더 생성: {self.template_dir}")
        
        self.template_name = 'magazine_layout.html'
        template_file_path = os.path.join(self.template_dir, self.template_name)
        
        # 기본 템플릿이 없으면 생성 (렌더링 에러 방지용)
        if not os.path.exists(template_file_path):
            with open(template_file_path, "w", encoding="utf-8") as f:
                f.write("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>AI Magazine</title>
    <style>
        body { 
            background-color: {{ data.design_spec.theme.colors.primary if data.design_spec else '#ffffff' }}; 
            font-family: sans-serif; padding: 20px; 
        }
        .content { background: rgba(255,255,255,0.9); padding: 30px; border-radius: 10px; max-width: 800px; margin: 0 auto; }
        img { max-width: 100%; height: auto; border-radius: 5px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="content">
        {% if images and images.main_img %}
        <img src="{{ images.main_img }}" alt="Hero Image">
        {% endif %}

        {% if data.content and data.content.blocks %}
            <h1>{{ data.content.blocks[0].headline }}</h1>
            <h3>{{ data.content.blocks[0].subhead }}</h3>
            <p>{{ data.content.blocks[0].body }}</p>
        {% else %}
            <h1>No Content Generated</h1>
        {% endif %}
    </div>
    <div style="text-align:center; margin-top:20px; opacity:0.5; font-size:12px;">
        Designed by AI Director ({{ data.design_spec.theme.mood if data.design_spec else 'Default' }})
    </div>
</body>
</html>
                """)
            print(f"📄 [Publisher] 기본 템플릿 생성 완료: {template_file_path}")

        # Jinja2 환경 설정
        self.env = Environment(loader=FileSystemLoader(self.template_dir))

    def _optimize_image(self, image_data, max_width=1024):
        """
        [내부 메서드] 이미지 리사이징 및 압축
        """
        try:
            if not image_data: return None
            
            # 입력이 파일 경로인 경우와 Base64인 경우를 모두 처리
            if os.path.exists(image_data):
                img = Image.open(image_data)
            else:
                try:
                    img_bytes = base64.b64decode(image_data)
                    img = Image.open(io.BytesIO(img_bytes))
                except:
                    return image_data # 디코딩 실패 시 원본 반환

            if img.width > max_width:
                ratio = max_width / float(img.width)
                new_height = int(float(img.height) * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            img = img.convert("RGB")
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=75)
            # Base64로 다시 인코딩해서 HTML에 임베딩할 수 있게 함 (선택사항)
            # 여기서는 파일 경로를 유지하거나 Base64로 변환할 수 있음. 
            # 템플릿 호환성을 위해 Base64 문자열 반환
            return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode('utf-8')
        except Exception as e:
            print(f"⚠️ 이미지 최적화 실패: {e}")
            return image_data 

    def _human_in_the_loop(self, state):
        """
        [내부 메서드] 사용자 검수 단계 (HITL)
        """
        print("\n" + "="*50)
        print("🔍 [Publisher HITL] 최종 조립 전 검수를 시작합니다.")
        
        content = state.get('content', {})
        if 'blocks' in content and len(content['blocks']) > 0:
            current_headline = content['blocks'][0].get('headline', 'N/A')
            print(f"현재 표지 문구: {current_headline}")
            
            user_input = input("👉 수정할 문구를 입력하세요 (엔터 시 유지): ").strip()
            if user_input:
                state['content']['blocks'][0]['headline'] = user_input
                print(f"✅ 문구가 '{user_input}'(으)로 업데이트되었습니다.")
        
        print("="*50 + "\n")
        return state

    def run(self, state, enable_hitl=False):
        """
        에이전트 실행 메인 메서드
        """
        print("--- [Node 7] Publisher Agent 작동 시작 ---")

        # 1. 사용자 검수 (HITL)
        if enable_hitl:
            state = self._human_in_the_loop(state)

        # 2. 이미지 최적화 처리 (HTML에 임베딩하기 위해)
        # state['images'] 딕셔너리가 있다면 처리
        if state.get('images'):
            for key, val in state['images'].items():
                # 파일 경로인 경우 최적화 후 Base64로 변환
                if val and os.path.exists(val):
                    state['images'][key] = self._optimize_image(val)

        # 3. HTML 조립 (Rendering)
        try:
            # 🌟 [NEW] Planner의 의도에 따라 템플릿 교체!
            planner_intent = state.get("intent", "TYPE_FASHION_COVER")
            
            if "SPLIT" in planner_intent or "PRODUCT" in planner_intent:
                # 분할 레이아웃 (기사형)
                template_name = 'layout_split.html'
            else:
                # 덮어쓰기 레이아웃 (표지형) - 기본값
                template_name = 'layout_overlay.html' # 아까 만든 파일 이름도 이걸로 변경 추천!

            print(f"🖨️ Publisher: '{planner_intent}'에 맞춰 '{template_name}'을 사용합니다.")
            
            # 템플릿 로드
            template = self.env.get_template(template_name)
            
            html_output = template.render(
                data=state, 
                images=state.get('images', {})
            )
            
            # 4. 결과 저장
            state['final_html'] = html_output
            
            # 프로젝트 루트의 output 폴더 계산 (src/agents/publisher.py -> src/agents -> src -> root)
            root_dir = os.path.abspath(os.path.join(self.current_dir, "..", ".."))
            output_dir = os.path.join(root_dir, "output")
            os.makedirs(output_dir, exist_ok=True)
            
            output_path = os.path.join(output_dir, "final_magazine.html")
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_output)
            
            print(f"✅ 매거진 조립 완료! 결과 파일: {output_path}")
            return state

        except Exception as e:
            print(f"❌ Publisher 렌더링 에러: {e}")
            import traceback
            traceback.print_exc()
            return state

# ---------------------------------------------------------
# [Wrapper Function] Main.py에서 호출할 함수
# ---------------------------------------------------------
def run_publisher(state: dict) -> dict:
    # 클래스 인스턴스 생성 (여기서 __init__이 실행됨)
    agent = PublisherAgent(template_path="templates")
    
    # 자동화 모드이므로 HITL은 끔 (필요하면 True로 변경)
    return agent.run(state, enable_hitl=False)