# /home/sauser/final/Final-Project/src/agents/publisher.py
import os
import base64
import io
from PIL import Image
from jinja2 import Environment, FileSystemLoader
import traceback

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
    
    # -----------------------------
    # Layout Params Builder (NEW)
    # -----------------------------
    def _extract_main_image_src(self, state: dict):
        images = state.get("images") or {}
        if not isinstance(images, dict) or not images:
            return None
        return images.get("main_img") or next(iter(images.values()), None)

    def _open_pil_from_image_src(self, image_src: str):
        if not image_src or not isinstance(image_src, str):
            return None

        payload = image_src
        if payload.startswith("data:image"):
            payload = payload.split(",", 1)[-1]

        try:
            if self._looks_like_path(payload) and os.path.exists(payload):
                return Image.open(payload)
            img_bytes = base64.b64decode(payload)
            return Image.open(io.BytesIO(img_bytes))
        except Exception:
            return None

    def _compute_image_meta(self, state: dict) -> dict:
        img_src = self._extract_main_image_src(state)
        img = self._open_pil_from_image_src(img_src) if img_src else None
        if not img:
            return {"width": 0, "height": 0, "aspect_ratio": 1.0}

        w, h = img.size
        ar = float(w) / float(h if h else 1)
        return {"width": w, "height": h, "aspect_ratio": ar}

    def _pick_largest_box(self, boxes: list):
        best, best_area = None, -1
        for b in boxes:
            if not (isinstance(b, (list, tuple)) and len(b) == 4):
                continue
            ymin, xmin, ymax, xmax = b
            try:
                area = max(0, (xmax - xmin)) * max(0, (ymax - ymin))
            except Exception:
                continue
            if area > best_area:
                best_area = area
                best = [ymin, xmin, ymax, xmax]
        return best

    def _compute_split_params(self, state: dict) -> dict:
        planner = state.get("planner_result") or {}
        selected_type = str(planner.get("selected_type", "")).upper()

        vision = state.get("vision_result") or {}
        vw = (((vision.get("metadata") or {}).get("composition_analysis") or {}).get("visual_weight") or "")
        vw = str(vw)

        meta = state.get("image_meta") or {"aspect_ratio": 1.0}
        ar = float(meta.get("aspect_ratio", 1.0))

        # 방향: 가로면 row, 세로면 column
        direction = "row" if ar >= 1.25 else "column"

        # reverse: right-heavy면 텍스트를 왼쪽으로 (order 뒤집기)
        reverse = ("right-heavy" in vw.lower()) or (vw.strip().lower() == "right")

        # ratio: image-section 비중 (타입별)
        if "TYPE_LUXURY_PRODUCT" in selected_type:
            ratio = 0.45  # 텍스트 크게(이미지 작게)
        elif "TYPE_EDITORIAL_SPLIT" in selected_type:
            ratio = 0.55  # 55:45
        elif "TYPE_STREET_VIBE" in selected_type:
            ratio = 0.70  # 이미지 크게
        else:
            ratio = 0.55

        if direction == "column":
            ratio = min(0.65, max(0.50, ratio))

        return {"direction": direction, "ratio": float(ratio), "reverse": bool(reverse)}

    def _compute_overlay_params(self, state: dict) -> dict:
        vision = state.get("vision_result") or {}
        meta = state.get("image_meta") or {"width": 0, "height": 0}
        W, H = int(meta.get("width", 0)), int(meta.get("height", 0))

        boxes = vision.get("space_analysis") or vision.get("safe_areas")

        # safe_areas가 "Center" 같은 문자열이면 fallback
        if not isinstance(boxes, list) or W <= 0 or H <= 0:
            return {"box": {"left_pct": 8, "top_pct": 10, "width_pct": 60, "align": "left"}}

        best = self._pick_largest_box(boxes)
        if not best:
            return {"box": {"left_pct": 8, "top_pct": 10, "width_pct": 60, "align": "left"}}

        ymin, xmin, ymax, xmax = best

        # normalized(0~1) 가능성 판별
        is_norm = max(abs(ymin), abs(xmin), abs(ymax), abs(xmax)) <= 1.2
        if is_norm:
            ymin, ymax = ymin * H, ymax * H
            xmin, xmax = xmin * W, xmax * W

        left_pct = (xmin / W) * 100
        top_pct = (ymin / H) * 100
        width_pct = ((xmax - xmin) / W) * 100

        pad = 2.0
        left_pct = max(0.0, min(95.0, left_pct + pad))
        top_pct = max(0.0, min(90.0, top_pct + pad))
        width_pct = max(20.0, min(85.0, width_pct - (pad * 2)))

        cx = (xmin + xmax) / 2.0
        align = "right" if cx > (0.55 * W) else "left"

        return {"box": {"left_pct": round(left_pct, 2), "top_pct": round(top_pct, 2), "width_pct": round(width_pct, 2), "align": align}}

    def _build_layout_params(self, state: dict) -> None:
        print("🧩 main_img head:", (state.get("images", {}).get("main_img") or "")[:40])
        state["image_meta"] = self._compute_image_meta(state)
        state.setdefault("layout_params", {})
        state["layout_params"]["split"] = self._compute_split_params(state)
        state["layout_params"]["overlay"] = self._compute_overlay_params(state)

        # (옵션) vision alias: downstream 호환용
        vision = state.get("vision_result")
        if isinstance(vision, dict):
            vision.setdefault("safe_areas", vision.get("space_analysis") or vision.get("safe_areas") or "Center")



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


    # ------------------------------------------------------------------
    # [DEBUG + FIX VERSION] run_process (함수 호출 없이 내부 해결)
    # ------------------------------------------------------------------
    def run_process(self, state, enable_hitl=False):
        print("\n🐞 [DEBUG] Publisher run_process 시작")
        import traceback

        try:
            # 1. 데이터 가져오기
            planner_result = state.get("planner_result")
            vision_result = state.get("vision_results") or state.get("vision_result")
            manuscript = state.get("manuscript")
            design_spec = state.get("design_spec")

            # 2. [핵심 수정] 리스트가 들어오면 -> {id: data} 딕셔너리로 강제 변환
            # 별도 함수(_ensure_dict_map) 없이 여기서 바로 처리합니다.
            
            def to_dict_map(data, name):
                """내부용: 리스트를 딕셔너리로 변환"""
                if not data: 
                    return {}
                if isinstance(data, dict):
                    return data
                if isinstance(data, list):
                    print(f"⚠️ [Data Fix] '{name}'가 리스트여서 딕셔너리로 변환합니다.")
                    new_map = {}
                    for idx, item in enumerate(data):
                        if isinstance(item, dict):
                            # ID가 없으면 'main' 또는 인덱스 사용
                            key = str(item.get("id", "main"))
                            # 만약 key가 'None' 문자열이면 인덱스로 대체
                            if key == "None": key = str(idx)
                            new_map[key] = item
                    return new_map
                return {}

            plans_map = to_dict_map(planner_result, "planner_result")
            visions_map = to_dict_map(vision_result, "vision_result")
            manuscripts_map = to_dict_map(manuscript, "manuscript") # 👈 여기가 범인이었음
            designs_map = to_dict_map(design_spec, "design_spec")

            # 3. 처리할 아이템 리스트 확보
            user_input = state.get("user_input")
            if isinstance(user_input, list):
                items_to_process = user_input
            else:
                single_item = user_input if isinstance(user_input, dict) else {"id": "main"}
                if isinstance(single_item, dict):
                    single_item.setdefault("id", "main")
                items_to_process = [single_item]

            # 4. 이미지 데이터 처리
            raw_imgs = state.get("image_data") or state.get("images")
            images_map = {}
            
            if isinstance(raw_imgs, list):
                for idx, img in enumerate(raw_imgs):
                    if idx < len(items_to_process):
                        u_id = str(items_to_process[idx].get("id", "main"))
                        images_map[u_id] = img
            elif isinstance(raw_imgs, dict):
                images_map = raw_imgs
            else:
                if items_to_process:
                    first_id = str(items_to_process[0].get("id", "main"))
                    images_map[first_id] = raw_imgs

            accumulated_html = []

            # 5. 페이지 렌더링 루프
            for item in items_to_process:
                # ID가 없으면 'main'으로 통일
                a_id = str(item.get("id", "main"))
                print(f"🖨️ Publishing Page [ID:{a_id}] 처리 중...")

                # 데이터 매핑에서 안전하게 가져오기 (이제 리스트일 걱정 없음)
                p_res = plans_map.get(a_id, {}) or plans_map.get("main", {})
                v_res = visions_map.get(a_id, {}) or visions_map.get("main", {})
                m_res = manuscripts_map.get(a_id, {}) or manuscripts_map.get("main", {})
                d_res = designs_map.get(a_id, {}) or designs_map.get("main", {})

                # 혹시라도 리스트가 남아있을 경우를 대비한 최후의 방어선
                if isinstance(p_res, list): p_res = p_res[0] if p_res else {}
                if isinstance(v_res, list): v_res = v_res[0] if v_res else {}
                if isinstance(m_res, list): m_res = m_res[0] if m_res else {}
                if isinstance(d_res, list): d_res = d_res[0] if d_res else {}

                local_state = {
                    "user_input": item,
                    "planner_result": p_res,
                    "vision_result": v_res,
                    "manuscript": m_res,
                    "design_spec": d_res,
                    "intent": state.get("intent"),
                    "images": {} 
                }

                # (B) 이미지 처리
                raw_img = images_map.get(a_id) or images_map.get("main")
                if raw_img:
                    optimized = self._optimize_image(raw_img)
                    if optimized:
                        local_state["images"]["main_img"] = f"data:image/jpeg;base64,{optimized}"
                    else:
                        if isinstance(raw_img, str):
                             local_state["images"]["main_img"] = raw_img

                # (C) 레이아웃 파라미터 계산
                try:
                    self._build_layout_params(local_state)
                except Exception as e:
                    print(f"⚠️ [Error] _build_layout_params 실패 (ID:{a_id}): {e}")

                # (D) 템플릿 렌더링
                try:
                    planner_data = local_state.get("planner_result", {})
                    intent = local_state.get("intent") or planner_data.get("selected_type", "")
                    intent_str = str(intent).upper()
                    
                    vision = local_state.get("vision_result", {})
                    strategy = str((vision.get("layout_strategy") or {}).get("recommendation") or planner_data.get("layout_mode") or "")
                    
                    if strategy.lower() == "separated":
                        current_template_name = "layout_separated.html"
                    elif ("SPLIT" in intent_str) or ("PRODUCT" in intent_str) or ("SEPARATED" in intent_str):
                        current_template_name = "layout_separated.html"
                    else:
                        current_template_name = "layout_overlay.html"

                    # 원고 데이터 연결
                    m = local_state.get("manuscript")
                    if m and isinstance(m, dict):
                        local_state.setdefault("content", {"blocks": [{}]})
                        b0 = local_state["content"]["blocks"][0]
                        b0["headline"] = m.get("headline", "Untitled")
                        b0["subhead"] = m.get("subhead", "")
                        b0["body"] = m.get("body", "")
                        b0["caption"] = m.get("caption", "")

                    template = self.env.get_template(current_template_name)
                    page_html = template.render(data=local_state, images=local_state.get('images', {}))
                    accumulated_html.append(page_html)

                except Exception as e:
                    print(f"❌ Page Render Error [ID:{a_id}]: {e}")
                    traceback.print_exc()
                    accumulated_html.append(f"<div class='page'><h3>Error Rendering Page {a_id}: {e}</h3></div>")

            # 6. 최종 결과 합치기
            final_output = "\n".join(accumulated_html)
            
            global_style = """
                <style>
                    @media print {
                        .page { break-after: always; page-break-after: always; }
                        body { margin: 0; padding: 0; }
                    }
                </style>
            """
            final_output = global_style + final_output

            state["html_code"] = final_output
            
            output_path = os.path.join(self.project_root, "output", "final_magazine.html")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_output)
            
            print(f"✅ 매거진 조립 완료: {output_path}")
            return state

        except Exception as e:
            print("\n🚨 [CRITICAL ERROR] Publisher 전체 프로세스 중단")
            print(f"에러 메시지: {e}")
            traceback.print_exc()
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