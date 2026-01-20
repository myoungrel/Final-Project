"""
[MCP Client Wrapper]
Google Nano Banana (External Service)와의 통신을 담당합니다.
이미지 리스트(Multi-image)를 지원하도록 업데이트되었습니다.
"""
import asyncio
import os
import json
from typing import List, Union

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    
class AURAClient:
    def __init__(self):
        # Resolve absolute path to mcp_server.py
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Assuming mcp_server.py is in the parent directory of tool/
        default_server = os.path.join(os.path.dirname(script_dir), "mcp_server.py")
        self.server_script = os.getenv("MCP_SERVER_SCRIPT", default_server) 
        self.is_connected = False

    async def generate_layout(self, 
                              headline: str, 
                              body: str, 
                              image_data: Union[str, List[str]], # ✨ List 지원 추가
                              layout_override: str,
                              vision_json: str,
                              design_json: str,
                              plan_json: str) -> str:
        
        if not MCP_AVAILABLE:
            return self._mock_generation(headline, layout_override)

        server_params = StdioServerParameters(
            command="python",
            args=[self.server_script], 
            env=os.environ.copy()
        )

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Tool 실행 (with Timeout)
                    try:
                        result = await asyncio.wait_for(
                            session.call_tool(
                                "generate_magazine_layout",
                                arguments={
                                    "headline": headline,
                                    "body": body,
                                    "image_data": json.dumps(image_data) if isinstance(image_data, list) else image_data,
                                    "layout_override": layout_override,
                                    "vision_context": vision_json,
                                    "design_spec": design_json,
                                    "planner_intent": plan_json
                                }
                            ),
                            timeout=300.0 # 300초 타임아웃 (LLM Judge + retry loop 대응)
                        )
                    except asyncio.TimeoutError:
                        print("❌ [AURA Client] Timeout detected!")
                        return "<div>Layout generation timed out. Please try again.</div>"
                    
                    final_html = ""
                    for content in result.content:
                        if content.type == 'text':
                            final_html += content.text
                            
                    return final_html
                    
        except Exception as e:
            print(f"❌ [AURA Client] Error: {e}")
            print(f"   Server script path: {self.server_script}")
            return f"<div style='color:red'>MCP Error: {e}</div>"

    def _mock_generation(self, headline, layout_override):
        return f"<div>Mock: MCP Client not available. ({headline})</div>"

mcp_client = AURAClient()
