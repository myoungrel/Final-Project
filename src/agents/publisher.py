# /home/sauser/final/Final-Project/src/agents/publisher.py
import os
import base64
import io
from PIL import Image
from jinja2 import Environment, FileSystemLoader

class PublisherAgent:
    def __init__(self):
        """
        Publisher 에이전트 초기화 (경로 수정 + 루트 경로 유지 버전)
        """
        # 1. 현재 파일(publisher.py)의 위치 기준 (src/agents)
        self.current_dir = os.path.dirname(os.path.abspath(__file__)) 
        
        # 2. [중요] 프로젝트 루트 경로 계산 (저장할 때 필요해서 유지해야 함!)
        # src/agents -> src -> ProjectRoot
        self.project_root = os.path.dirname(os.path.dirname(self.current_dir))
        
        # 3. 템플릿 폴더는 바로 옆 'templates' 폴더로 설정
        # (기존: project_root/templates -> 수정: src/agents/templates)
        self.template_dir = os.path.join(self.current_dir, "templates")
        
        # 디버깅: 실제 경로 확인
        print(f"📂 Publisher Template Dir: {self.template_dir}")
        if not os.path.exists(self.template_dir):
            print("❌ [CRITICAL] 템플릿 폴더가 없습니다! 경로를 확인하세요.")
        
        # Jinja2 환경 설정
        self.env = Environment(loader=FileSystemLoader(self.template_dir))

    def _looks_like_path(self, s: str) -> bool:
        if not isinstance(s, str):
            return False
        s = s.strip()
        if len(s) == 0 or len(s) > 260:   # 윈도/리눅스 공통으로 보수적
            return False
        if s.startswith(("data:image", "http://", "https://")):
            return False
        # 확장자 기반 + 경로구분자
        has_sep = ("/" in s) or ("\\" in s)
        has_ext = os.path.splitext(s)[1].lower() in {".jpg", ".jpeg", ".png", ".webp"}
        return has_sep and has_ext


    def _optimize_image(self, image_data, max_width=1024):
        """
        image_data: data URI / base64 payload / file path
        return: base64 payload (JPEG) or None
        """
        try:
            if not image_data:
                return None            

            # 2) 파일 경로면 파일 열기
            if self._looks_like_path(image_data) and os.path.exists(image_data):
                img = Image.open(image_data)
            else:
                # 3) base64 payload로 간주하고 decode
                img_bytes = base64.b64decode(image_data)
                img = Image.open(io.BytesIO(img_bytes))

            # 4) 리사이즈
            if img.width > max_width:
                ratio = max_width / float(img.width)
                new_height = int(float(img.height) * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

            # 5) JPEG로 압축
            img = img.convert("RGB")
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=75)

            # ✅ base64 payload만 반환
            return base64.b64encode(buffer.getvalue()).decode("utf-8")

        except Exception:
            # ✅ 실패 시 원본을 그대로 반환하지 말고 None
            return None


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
        if "images" in state and isinstance(state["images"], dict):
            for img_id, img_data in list(state["images"].items()):
                if not img_data:
                    continue

                # 원본이 data URI면 payload만 분리해서 최적화 입력으로 사용
                payload = img_data
                if isinstance(payload, str) and payload.startswith("data:image"):
                    payload = payload.split(",", 1)[-1]

                optimized = self._optimize_image(payload)

                if optimized:
                    # 성공: jpeg data uri로 저장
                    state["images"][img_id] = f"data:image/jpeg;base64,{optimized}"
                else:
                    # 실패: ✅ 원본 유지 (원본이 data URI면 그대로 두는게 가장 안전)
                    # 만약 원본이 파일경로라면, 템플릿에서 로컬 파일 접근이 막힐 수 있으니
                    # 여기서는 '원본이 data URI인 경우만 유지'하도록 더 엄격하게 할 수도 있음.
                    state["images"][img_id] = img_data


        # 3. 템플릿 자동 선택 & HTML 조립 (핵심 수정!)
        try:
            # A. 의도(Intent) 파악 - Planner 또는 State에서 가져오기
            planner_data = state.get("planner_result", {})
            intent = state.get("intent") or planner_data.get("selected_type", "TYPE_FASHION_COVER")
            intent_str = str(intent) if intent else ""

            # B. 템플릿 파일 결정 ('Separated' 등 키워드 체크)
            if ("SPLIT" in intent_str) or ("PRODUCT" in intent_str) or ("Separated" in intent_str):
                current_template_name = 'layout_split.html'
            else:
                current_template_name = 'layout_overlay.html'

            print(f"🖨️ Publisher: Intent='{intent_str}' -> Template='{current_template_name}' 선택됨")

            # ✅ manuscript -> content.blocks 호환 레이어
            if "manuscript" in state and isinstance(state["manuscript"], dict):
                state.setdefault("content", {})
                state["content"].setdefault("blocks", [])

                # blocks[0]을 manuscript 기반으로 채움
                if len(state["content"]["blocks"]) == 0:
                    state["content"]["blocks"].append({})

                b0 = state["content"]["blocks"][0]
                m = state["manuscript"]

                b0["headline"] = m.get("headline", b0.get("headline", "Untitled"))
                b0["subhead"]  = m.get("subhead",  b0.get("subhead",  ""))
                b0["body"]     = m.get("body",     b0.get("body",     ""))
                b0["caption"]  = m.get("caption",  b0.get("caption",  ""))

            # C. 렌더링
            template = self.env.get_template(current_template_name)
            html_output = template.render(data=state, images=state.get('images', {}))
            
            # [D. A4 규격 강제 적용 CSS 주입]
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
            state["html_code"] = html_output
            
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
            state['html_code'] = f"<h3>Error: {e}</h3>"
            return state

# ---------------------------------------------------------
# [중요] 외부 파일(main.py)에서 import 할 수 있도록 함수 노출
# ---------------------------------------------------------
publisher_agent = PublisherAgent()

def run_publisher(state):
    out_state = publisher_agent.run_process(state, enable_hitl=False)

    # ✅ formatter/critique가 읽는 키로 맞춰서 반환
    return {
        "html_code": out_state.get("html_code", ""),
        "logs": ["Publisher: HTML assembled"]
    }