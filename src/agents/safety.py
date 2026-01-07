from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.state import MagazineState
from src.config import config
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.state import MagazineState
from src.config import config
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
import re

# [수정 1] 출력 구조의 설명(Description)을 구체화하여 LLM의 판단 기준 완화
class SafetyCheck(BaseModel):
    is_safe: bool = Field(description="유해성 여부 (True: 잡지 발행, False: 발행 불가)")
    reason: str = Field(description="판단 이유. 안전하다면 'Safe content' 등으로 기재.")
    pii_detected: list = Field(description="실제 개인정보(주민번호, 개인 전화번호 등)만 포함. 브랜드명이나 모델명, 이름은 제외.")

def run_safety(state: MagazineState) -> dict:
    print("--- [2] Safety Filter: 매거진 정책 기반 검수 중... ---")
    llm = config.get_llm()

    # 1. Pydantic Parser 설정: LLM이 JSON 형식을 지키도록 강제합니다.
    parser = PydanticOutputParser(pydantic_object=SafetyCheck)
    
<<<<<<< HEAD
    user_input = state.get("user_input", "") 
=======
    # [수정 후] 입력값 타입 안전 처리
    raw_input = state.get("user_input") 

    # 1. None이거나 값이 비어있으면 빈 문자열로 처리
    if raw_input is None:
        user_input = ""
    # 2. 문자열이 아닌 경우(리스트, 객체 등) 강제로 문자열로 변환
    elif not isinstance(raw_input, str):
        user_input = str(raw_input)
    # 3. 정상 문자열인 경우
    else:
        user_input = raw_input
>>>>>>> main

    # 2. 정규표현식을 이용한 사전 PII 검사 (Email, Phone 등)
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    found_emails = re.findall(email_pattern, user_input)

    # [수정 2] 프롬프트 엔지니어링: 페르소나 변경 및 예외 상황(면책) 명시
    # - 프롬프트 수정: 잡지사 편집장(Chief Editor) 페르소나 적용
    # - 상업적 정보(브랜드, 제품명)는 PII가 아님을 명시
    prompt = ChatPromptTemplate.from_template(
        """
        You are the Chief Editor of a lifestyle magazine.
        Your goal is to approve content that is creative and engaging, while blocking illegal or harmful material.

        Analyze the text: "{user_input}"

        ### Guidelines for Approval:

        1. **PII (Personal Info):**
           - **ALLOW (Safe):** Names of public figures, interviewees, celebrities, brand names (e.g., Calvin Klein, Chanel), and models.
           - **BLOCK (Unsafe):** Private home addresses, SSNs, personal phone numbers, passwords.

        2. **Sexual Content:**
           - **ALLOW (Safe):** Fashion photography, artistic nudity, romance, swimsuit trends, or health-related topics.
           - **BLOCK (Unsafe):** Explicit pornography, non-consensual sexual content, or graphic sexual acts.

        3. **Hate & Violence (STRICT):**
           - **BLOCK (Unsafe):** Hate speech, promotion of terrorism, self-harm, or graphic violence.

        4. **Commercial Content:**
           - **ALLOW:** Product descriptions, prices, and marketing copies are 100% SAFE.

        {format_instructions}
        """
    ).partial(format_instructions=parser.get_format_instructions()) # Parser가 생성한 지침 삽입
    
    # 4. 체인 구성 및 호출
    # 변경 사항: StrOutputParser() 대신 위에서 정의한 parser를 사용합니다.
    chain = prompt | llm | parser

    try:
        # result는 이제 SafetyCheck 클래스의 인스턴스(객체)가 됩니다.
        result = chain.invoke({"user_input": user_input})
        
        # 5. 정규표현식 결과와 LLM 결과 병합
        # 변경 사항: LLM이 놓칠 수 있는 정규식 패턴(이메일 등)을 최종 결과에 강제로 추가합니다.
        if found_emails:
            # 단, 이메일이 회사 대표 메일(예: contact@samsung.com)인 경우 등은 
            # 추후 로직에서 제외할 수도 있으나, 일단 안전하게 차단 혹은 경고로 유지
            result.is_safe = False
            result.pii_detected = list(set(result.pii_detected + found_emails))
            result.reason += " [System] Email pattern detected."

    except Exception as e:
        print(f"❌ Safety Filter Error: {e}")
        # 폴백 시에도 너무 공격적으로 차단하지 않도록 기본값을 조정할 수 있으나,
        # 시스템 에러 상황이므로 False로 두는 것이 안전함.
        result = SafetyCheck(
            is_safe=False, 
            reason="Safety check failed due to system error. (Fallback activated)",
            pii_detected=[]
        )

    print(f"🛡️ 안전성 결과: {'SAFE' if result.is_safe else 'UNSAFE'} (사유: {result.reason})")

    # 6. 최종 State 반환
    # 변경 사항: A가 정의한 state 구조에 맞춰 'safety_check'와 상세 'safety_detail'을 함께 넘깁니다.
    return {
        "safety_check": "SAFE" if result.is_safe else "UNSAFE",
        "safety_detail": result.model_dump(), # 상세 데이터(사유, PII 목록) 저장 (Pydantic V2부터는 .dict() 대신 .model_dump()를 사용. dict 빗금발생)
        "logs": [f"Safety: {result.is_safe}, Reason: {result.reason}"]
    }
