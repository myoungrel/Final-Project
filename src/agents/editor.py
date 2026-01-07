# src/agents/editor.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from src.state import MagazineState
from src.config import config

def run_editor(state: MagazineState) -> dict:
    print("--- [4] Editor Agent: English Article Generation ---")
    llm = config.get_llm()
    parser = JsonOutputParser()
    
    # ------------------------------------------------------------------
    # [Old Code] 기존 단일 처리 로직 (주석 처리)
    # ------------------------------------------------------------------
    # 1. 데이터 추출
    # user_request = state["user_input"]
    #
    # [sm수정/추가] 유저 직접 입력 본문 유무 확인 (A와 협의된 state 키값 사용)
    # user_body_text가 있고, 일정 길이(예: 50자) 이상이면 '교정' 모드로 동작
    # user_body_text = state.get("user_body_text", "").strip()
    # is_direct_input = len(user_body_text) > 50
    # 
    # vision_data = state.get("vision_result", {})
    # if isinstance(vision_data, str):
    #     image_mood = vision_data 
    #     image_desc = "No visual description provided."
    # else:
    #     image_mood = vision_data.get("mood", "General")
    #     image_desc = vision_data.get("description", "No visual description provided.")

    # # planner 들어오면 활성화
    # # B. Planner Data (기획 의도/전략) -> 톤 매칭 & 구조용
    # planner_data = state.get("planner_result", {})
    # # Planner가 정해준 톤을 가져오고, 없으면 기본값 'Elegant'
    # target_tone = planner_data.get("target_tone", "Elegant & Lyrical")
    # planner_intent = state.get("intent", "General Magazine Article")
    # ------------------------------------------------------------------

    # ✨ [New Logic] 다중 입력 데이터 로드
    user_inputs = state.get("user_input", [])       # List[Dict]
    plans = state.get("planner_result", {})                  # Dict[id, plan_json]
    vision_results = state.get("vision_result", {}) # Dict[id, vision_json]
    
    manuscripts = [] # ✨ 최종 결과물 리스트




    # # [sm추가] 분기에 따른 프롬프트 명령어 설정 (이제 프롬프트 안으로 들어감)------------------------------
    # if is_direct_input:
    #     # 본문이 있는 경우: 교정 및 스타일 변환 모드
    #     mode_instruction = """
    #     MODE: Polish & Format (User provided a draft)
    #     - The user has provided a full draft. DO NOT change the core facts or story.
    #     - Your job is to improve the grammar, flow, and vocabulary to match the [Target Tone].
    #     - Ensure it reads like a high-end magazine article while keeping the original meaning.
    #     """
    #     source_text = user_body_text
    # else:
    #     # 본문이 없는 경우: 키워드 기반 생성 모드
    #     mode_instruction = """
    #     MODE: Creative Writing (User provided keywords/request)
    #     - The user has provided keywords or a brief request. 
    #     - Your job is to generate a full, captivating English magazine article from scratch.
    #     - Expand on the ideas to create a rich narrative that fits the [Target Tone].
    #     """
    #     source_text = user_request
    #------------------------------------------------------------------


    # ------------------------------------------------------------------
    # [프롬프트 설계 의도 - 개발자 참고용]
    # 1. Role: Kinfolk, Vogue급의 하이엔드 영어 에디터 페르소나 주입.
    # 2. Critical Rule: 
    #    - 결과물은 무조건 '영어'여야 함 (User Input이 한글이어도 번역+작문).
    #    - 사실 관계 왜곡 금지 (지어내기 X).
    # 3. Tone Matching 전략:
    #       1. Elegant: 우아/시적 (Vogue)
    #       2. Bold: 강렬/역동 (Nike/GQ)
    #       3. Analytical: 분석/객관 (Time/HBR)
    #       4. Friendly: 친근/대화 (Lifestyle Blog)
    #       5. Witty: 재치/풍자 (New Yorker/Wired) - 유머와 언어유희 사용
    #       6. Dramatic: 서사/웅장 (NatGeo) - 감동과 긴장감 조성
    #       7. Minimalist: 절제/건조 (Apple/Kinfolk) - 군더더기 없는 단문
    #       8. Nostalgic: 회상/따뜻함 (Retro) - 감상적인 과거 회상 어조
    # 4. Smart Caption: 
    #    - Body: 이미지 묘사 강제 삽입 로직(Context Block)을 '삭제'함.
    #    -> 오직 사용자 입력의 톤(Tone)만 변경하여 번역/작문.
    #    - Caption: 이미지와 글의 관계를 맺어주는 역할은 'Caption'에게 전임.
    # 5. Constraints:
    #    - Headline: 7단어 이내 (영어 잡지 표준).
    #    - Body: adaptive를 적용하여 사용자가 넣은 글의 길이에 맞춰서 생성
    #    - Formatting : 긴 글일 경우 문단(\n\n)을 나누라고 지시
    # ------------------------------------------------------------------
    
    # 2. 프롬프트 정의 (Pure English for LLM Performance)
    prompt = ChatPromptTemplate.from_template(
        """
        You are a Professional Editor for a High-End English Magazine (like Kinfolk, Vogue, or Time).
        
        {mode_instruction}

        !!! CRITICAL RULE: ENGLISH OUTPUT ONLY !!!
        - The final output must be in **ENGLISH**.
        - Do NOT invent new fictional stories. Keep the facts intact.
        - Do not add any new entities, places, dates, or numbers not present in the source.
        - **Primary Task**: Correct spelling, grammar, punctuation, and spacing errors.
        - **Tone Policy**: Preserve the user's original voice and style as much as possible.
        - **Exception**: ONLY modify the tone if the current text is **critically mismatched** with the [Target Tone] (e.g., Slang in a Medical article). Otherwise, keep it as is.


        [Input Data]
        - User Request (Source): {user_request}
        - Planner Intent: {planner_intent}
        - Image Mood: {image_mood}
        - Image Description: {image_desc}
        - **Target Tone (GIVEN)**: {target_tone}
        - **Visual Context**: {image_desc} (Use ONLY for Caption generation)
        
        [Directives]
        1. **Tone Reference (For Consistency Check)**: 
           Use the definitions below to check for "Critical Mismatches". Do not force this style if the original text is already acceptable.
           - **(A) Elegant & Lyrical**: Poetic, flowing, sophisticated.
           - **(B) Bold & Energetic**: Punchy, active voice, strong verbs.
           - **(C) Analytical & Professional**: Precise, objective, logic-focused.
           - **(D) Friendly & Conversational**: Warm, inviting, uses "You".
           - **(E) Witty & Satirical**: Clever wordplay, sharp humor.
           - **(F) Dramatic & Cinematic**: Suspenseful, emotional, sensory.
           - **(G) Minimalist & Clean**: Concise, dry, direct.
           - **(H) Nostalgic & Warm**: Evocative, cozy, retro.
           
        2. **Smart Captioning (The Bridge)**: 
           - Do NOT mention the image in the 'Body'.
           - Instead, write a separate **'Caption'** that connects the [Image Description] with the core theme of the text.
           - **Length Constraint**: Keep it concise (Max 15 words). It sits under the image, so brevity is key.
           - Example Format: "[Visual Detail from Image], [Connection Verb] the article's theme of [Core Topic]."
           - Concrete Example: "The golden sunset at Uluwatu, reflecting the article's theme of inner peace."
            (Use this pattern, but strictly based on YOUR input data.)
           
        3. **Adaptive Formatting (Crucial for Layout)**:
           - **If input is long (e.g., Interview, Essay):** Keep the length. Break the 'Body' into readable paragraphs using double line breaks (\\n\\n).
           - **If input is Q&A:** Maintain the Question & Answer format.
           - **Headline**: Max 7 words. Catchy.           
           - **Output**: JSON format ONLY. Do not include markdown tags.
        
        Output JSON format:
        {{
            "headline": "English Title Here",
            "subhead": "Subtitle goes here",
            "body": "English content matching the mood...",
            "pull_quote": "Short quote from text",
            "caption": "Visual description connecting image to text",
            "tags": ["Tag1", "Tag2"]
        }}
        """
    )
    
    chain = prompt | llm | parser
    
    # ------------------------------------------------------------------ 
    # try:
    #     #sm [수정] 분기에 따라 결정된 mode_instruction과 active_text를 전달
    #     manuscript = chain.invoke({
    #         "mode_instruction": mode_instruction, #sm 새로 추가된 분기 지시어
    #         "user_request": source_text,          #sm 상황에 맞는 텍스트(초안 vs 키워드) 전달
    #         "planner_intent": planner_intent,
    #         "image_mood": image_mood,
    #         "target_tone": target_tone, # Planner가 정해준 걸 그대로 주입
    #         "image_desc": image_desc
    #     })
    # except Exception as e:
    #     print(f"❌ Editor Error: {e}")
    #     manuscript = {
    #         "headline": "Generation Failed",
    #         "subhead": "Error",
    #         "body": f"An error occurred while generating content. ({user_request})",
    #         "pull_quote": "System Error",
    #         "caption": "Image context missing",
    #         "tags": ["Error"]
    #     }
        
    # return {
    #     "manuscript": manuscript,
    #     #[기존주석] "logs": [f"Editor: '{manuscript.get('headline')}' (English) Completed"],
    #     #[기존코드] "logs": [f"Editor: Executed strategy '{target_tone}'"] # planner 들어오면 활성화
    #    # [sm수정] 로그에 현재 어떤 모드로 실행되었는지 표시----------------------
    #     "logs": [f"Editor: Executed '{target_tone}' (Mode: {'Polish' if is_direct_input else 'Create'})"]
    # }
    # ------------------------------------------------------------------

    # 🔄 [New Logic] 반복문을 통한 다중 원고 처리 시작
    for item in user_inputs:
        a_id = str(item.get("id"))
        is_gen = item.get("is_generated", True) # AI 생성 여부
        
        title_text = item.get("title", "Untitled")
        req_text = item.get("request", "")
        
        # 💡 Planner & Vision 데이터 매칭
        plan_data = plans.get(a_id, {})
        vis_data = vision_results.get(a_id, {})
        metadata = vis_data.get("metadata", {})
        
        # 🎯 [톤 결정 로직] Planner 우선 -> 사용자 입력 style 순
        planned_tone = plan_data.get("selected_type") or plan_data.get("tone")
        user_pref_style = item.get("style", "Elegant")

        vision_strategy_data = vis_data.get("layout_strategy", {})
        target_layout = vision_strategy_data.get("recommendation", "Overlay")
        

        if planned_tone:
            target_tone = planned_tone
            print(f"   -> 💡 Planner 전략 적용: {target_tone}")
        else:
            target_tone = user_pref_style
            print(f"   -> 👤 User 스타일 적용: {target_tone}")
            
        planner_intent = plan_data.get("intent", "General Magazine Article")
        
        # 🖼️ 이미지 정보 추출
        image_mood = metadata.get("mood", "General")
        image_desc = metadata.get("description", "No visual description provided.") 

        print(f"✍️ Editor 작업 중... ID:{a_id} | 생성모드:{is_gen} | 톤:{target_tone}")

        article_content = {}

        # --- [Case 1: ✋ 사용자 직접 입력 (AI 작문 건너뜀)] ---
        if not is_gen:
            print(f"   -> 👤 사용자 본문 그대로 유지 (ID: {a_id})")
            article_content = {
                "id": a_id,
                "headline": title_text,
                "subhead": "Original Draft",
                "body": req_text,
                "pull_quote": "",
                "caption": f"Visual context for {title_text}",
                "tags": [user_pref_style]
            }

        # --- [Case 2: 🤖 AI 자동 생성 및 교정] ---
        else:
            # ✨ [sm수정] 어제 로직 반영: 텍스트 길이에 따른 Polish vs Create 모드 분기
            # 반복문 내 개별 아이템(req_text)의 길이를 체크하여 모드 결정
            is_polish_mode = len(req_text.strip()) > 50
            
            if is_polish_mode:
                # 📝 [수정] 교정 모드: "쓰기"가 아니라 "고치기"에 집중
                mode_instruction = """
                MODE: Proofreading & Minor Fixes (User provided a draft)
                - The user has provided a full draft. **Preserve the original meaning and nuances.**
                - Focus strictly on correcting grammar, spelling, and awkward phrasing.
                - Only adjust the tone if it is completely inappropriate for the [Target Tone].
                """
            else:
                mode_instruction = """
                MODE: Creative Writing (User provided keywords/request)
                - The user has provided keywords or a brief request. 
                - Your job is to generate a full, captivating English magazine article from scratch.
                - Expand on the ideas to create a rich narrative that fits the [Target Tone].
                """

            try:
                print(f"   -> 🚀 AI 작문 시작 (Mode: {'Polish' if is_polish_mode else 'Create'})")
                
                # [Old Code] 단일 호출
                # manuscript = chain.invoke({...})

                # ✨ [New Code] 체인 호출 (필요한 모든 변수 주입)
                generated = chain.invoke({
                    "mode_instruction": mode_instruction, # ✨ 모드 지시어
                    "user_request": req_text,             # ✨ 사용자 입력 텍스트
                    "planner_intent": planner_intent,
                    "target_tone": target_tone,
                    "image_mood": image_mood,
                    "image_desc": image_desc
                })
                
                # ✨ ID 주입 및 제목 유지 (사용자 제목이 있으면 우선순위)
                generated["id"] = a_id
                if title_text and title_text != "Untitled":
                    generated["headline"] = title_text
                
                article_content = generated

            except Exception as e:
                print(f"❌ Editor Error (ID: {a_id}): {e}")
                article_content = {
                    "id": a_id,
                    "headline": title_text,
                    "subhead": "Error",
                    "body": "Content generation failed.",
                    "caption": "Image context missing",
                    "tags": ["Error"]
                }
        # ✨ Layout 정보 주입
        article_content["layout"] = target_layout
        
        # ✅ 결과 리스트 적재
        manuscripts.append(article_content)
        
    return {
        "manuscript": manuscripts, # ✨ List[Dict] 형태로 반환
        # [Old Code]
        # "logs": [f"Editor: Executed strategy '{target_tone}'"]
        # [New Code]
        "logs": [f"Editor: {len(manuscripts)}개 원고 처리 완료 (AI 생성 및 직접 입력 포함)"]
    }