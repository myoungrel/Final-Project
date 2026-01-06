# /home/sauser/final/Final-Project/src/agents/publisher.py
import os
import base64
import io
from PIL import Image
from jinja2 import Environment, FileSystemLoader

class PublisherAgent:
    def __init__(self):
        """
        Publisher 에이전트 초기화
        """
        # 1. 경로 계산 (publisher.py 위치 기준)
        self.current_dir = os.path.dirname(os.path.abspath(__file__)) # .../src/agents
        
        # 2. 프로젝트 루트로 이동 (src/agents -> src -> ProjectRoot)
        self.project_root = os.path.dirname(os.path.dirname(self.current_dir))
        
        # 3. 템플릿 '폴더' 경로 설정 (파일명 제외!)
        # 예: .../Final-Project/templates
        self.template_dir = os.path.join(self.project_root, "templates")
        
        # 4. 템플릿 파일 이름 설정
        self.template_name = 'magazine_layout.html'
        
        # 디버깅용 출력
        print(f"📂 Publisher Template Dir: {self.template_dir}")
        
        # Jinja2 환경 설정 (폴더 경로만 전달)
        self.env = Environment(loader=FileSystemLoader(self.template_dir))

    def _optimize_image(self, image_data, max_width=1024):
        """
        [내부 메서드] 이미지 리사이징 및 압축 (과부하 방지)
        - image_data: Base64 문자열 또는 이미지 파일 경로
        """
        try:
            # 입력이 파일 경로인 경우와 Base64인 경우를 모두 처리
            if os.path.exists(image_data):
                img = Image.open(image_data)
            else:
                img_bytes = base64.b64decode(image_data)
                img = Image.open(io.BytesIO(img_bytes))

            if img.width > max_width:
                ratio = max_width / float(img.width)
                new_height = int(float(img.height) * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            img = img.convert("RGB")
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=75)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except Exception as e:
            # print(f"⚠️ 이미지 최적화 실패: {e}") # 로그가 너무 많으면 주석 처리
            return image_data # 실패 시 원본 반환

    def _human_in_the_loop(self, state):
        """
        [내부 메서드] 사용자 검수 단계 (HITL)
        """
        print("\n" + "="*50)
        print("🔍 [Publisher HITL] 최종 조립 전 검수를 시작합니다.")
        
        # 첫 번째 블록의 헤드라인을 검수 대상으로 지정
        if 'blocks' in state.get('content', {}) and len(state['content']['blocks']) > 0:
            current_headline = state['content']['blocks'][0].get('headline', 'N/A')
            print(f"현재 표지 문구: {current_headline}")
            
            user_input = input("👉 수정할 문구를 입력하세요 (엔터 시 유지): ").strip()
            if user_input:
                state['content']['blocks'][0]['headline'] = user_input
                print(f"✅ 문구가 '{user_input}'(으)로 업데이트되었습니다.")
        
        print("="*50 + "\n")
        return state

    def run_process(self, state, enable_hitl=True):
        """
        에이전트 실행 메인 메서드
        :param state: Director/Editor로부터 전달받은 상태 데이터 (dict)
        :param enable_hitl: 사용자 검수 활성화 여부
        """
        print("--- [Node 7] Publisher Agent 작동 시작 ---")

        # 1. 사용자 검수 (HITL)
        if enable_hitl:
            state = self._human_in_the_loop(state)

        # 2. 이미지 최적화 처리
        if 'images' in state:
            for img_id, img_data in state['images'].items():
                state['images'][img_id] = self._optimize_image(img_data)

        # 3. HTML 조립 (Rendering)
        try:
            # 여기서 템플릿 파일 이름을 사용합니다.
            template = self.env.get_template(self.template_name)
            html_output = template.render(data=state, images=state.get('images', {}))
            
            # [A4 규격 강제 적용 코드 추가]
            # 인쇄 및 PDF 변환 시 정확한 A4 사이즈(210mm x 297mm)를 유지하도록 CSS 주입
            a4_style = """
<style>
    @page { size: A4; margin: 0; }
    html, body { width: 210mm; height: 297mm; margin: 0; padding: 0; overflow: hidden; }
</style>
"""
            if "</head>" in html_output:
                html_output = html_output.replace("</head>", f"{a4_style}</head>")
            else:
                html_output = a4_style + html_output

            # 4. 결과 저장
            state['final_html'] = html_output
            
            # 테스트를 위해 파일로도 저장 (선택 사항)
            output_path = os.path.join(self.project_root, "output", "universal_result.html")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_output)
            
            print(f"✅ 매거진 조립 완료: {output_path}")
            return state

        except Exception as e:
            print(f"❌ 렌더링 에러: {e}")
            # 에러 발생 시에도 빈 문자열이라도 반환하여 다음 단계 진행
            state['final_html'] = f"<h3>Error: {e}</h3>"
            return state

# ---------------------------------------------------------
# [중요] 외부 파일(main.py)에서 import 할 수 있도록 함수 노출
# ---------------------------------------------------------
publisher_agent = PublisherAgent()

def run_publisher(state):
    # Streamlit(app.py) 실행 시 터미널 입력이 멈추는 것을 방지하기 위해 HITL은 끕니다.
    return publisher_agent.run_process(state, enable_hitl=False)