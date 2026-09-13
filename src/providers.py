"""
🔌 MULTI-PROVIDER LLM ADAPTER (Google Gemini, OpenAI & Offline Mock)
Hỗ trợ Native Tool Calling và chuyển đổi linh hoạt qua biến môi trường LLM_PROVIDER.
"""

import os
import re
import sys
import json
import time
from typing import Dict, Any, List
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

def _call_with_retry(fn, provider_label: str, max_retries: int = 3):
    """
    Gọi API LLM với cơ chế retry khi gặp rate limit (429 RESOURCE_EXHAUSTED).
    Đọc retryDelay từ thông báo lỗi (nếu có), mặc định chờ 15s. Lỗi khác ném ra ngoài để caller fallback.
    """
    attempt = 0
    while True:
        try:
            return fn()
        except Exception as e:
            msg = str(e)
            is_rate_limit = "429" in msg or "RESOURCE_EXHAUSTED" in msg or "rate limit" in msg.lower()
            if not is_rate_limit or attempt >= max_retries:
                raise
            attempt += 1
            m = re.search(r"retry in ([\d.]+)s", msg, flags=re.IGNORECASE)
            wait_s = min(float(m.group(1)) + 1.0, 60.0) if m else 15.0
            print(f"⏳ [{provider_label}] Rate limit (429). Chờ {wait_s:.0f}s rồi thử lại (lần {attempt}/{max_retries})...")
            time.sleep(wait_s)


class BaseLLMProvider:
    """Interface cơ sở cho các LLM Provider hỗ trợ Native Tool Calling"""
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        raise NotImplementedError


class MockOfflineProvider(BaseLLMProvider):
    """
    Offline Mock Provider dùng để chạy thử mà không tốn API Key.
    Mô phỏng Native Tool Calling theo chủ đề kiểm soát hàng hoá (inventory_query / create_restock_order),
    có nhận biết scratchpad (lịch sử Observation) để mô phỏng suy luận ReAct đa bước.
    """
    def __init__(self):
        self.model_name = "Offline-Mock-Model-2026"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return (f"[Mock Chatbot Response]: Xin chào! Tôi đã nhận được câu hỏi '{prompt}'. "
                f"(Chế độ Chatbot không có Tool tra cứu tồn kho thời gian thực).")

    @staticmethod
    def _extract_sku(text: str):
        m = re.search(r"\bSKU\d+\b", text, flags=re.IGNORECASE)
        return m.group(0).upper() if m else None

    @staticmethod
    def _extract_int(pattern: str, text: str, default=None):
        m = re.search(pattern, text, flags=re.IGNORECASE)
        return int(m.group(1)) if m else default

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        result = self._decide(prompt)
        result["provider"] = f"mock/{self.model_name}"
        return result

    def _decide(self, prompt: str) -> Dict[str, Any]:
        # Tách câu hỏi gốc và phần scratchpad (nếu app đã nạp lịch sử Observation)
        has_history = "[LỊCH SỬ SUY LUẬN REACT" in prompt
        user_query = prompt.split("\n[LỊCH SỬ SUY LUẬN REACT")[0] if has_history else prompt
        q = user_query.lower()
        sku = self._extract_sku(user_query)

        # ---------- Có Observation từ bước trước: quyết định bước tiếp theo ----------
        if has_history:
            observations = re.findall(r"Observation: (\{.*\})", prompt)
            last_obs = {}
            try:
                last_obs = json.loads(observations[-1]) if observations else {}
            except json.JSONDecodeError:
                last_obs = {}

            if last_obs.get("status") == "NOT_FOUND":
                return {
                    "type": "text",
                    "content": f"Rất tiếc, mã hàng {sku or 'bạn cung cấp'} không tồn tại trong hệ thống tồn kho. "
                               f"Vui lòng kiểm tra lại mã SKU. Tôi không thể cung cấp số liệu cho mã hàng này.",
                    "thought": "Tool trả về NOT_FOUND, trả lời lịch sự và không bịa đặt số liệu."
                }

            # Kết quả tra cứu tồn kho: nếu người dùng yêu cầu điều kiện 'nếu ... thì tạo đơn'
            if last_obs.get("tool") is None and "data" in last_obs and ("tạo đơn" in q or "nhập" in q):
                d = last_obs["data"]
                threshold = self._extract_int(r"dưới\s+(\d+)\s+ngày", user_query, 3)
                reserve_days = self._extract_int(r"(\d+)\s+ngày tới", user_query, 7)
                days_left = d.get("days_of_stock_left", 0)
                if days_left is not None and days_left < threshold:
                    qty = int(d.get("avg_daily_sales", 0) * reserve_days)
                    return {
                        "type": "tool_call",
                        "tool_name": "create_restock_order",
                        "arguments": {"sku": last_obs.get("sku", sku), "quantity": qty, "priority": "HIGH"},
                        "thought": (f"Observation cho thấy {last_obs.get('sku')} chỉ còn {days_left} ngày bán (< {threshold} ngày). "
                                    f"Cần nhập {d.get('avg_daily_sales')} x {reserve_days} = {qty} {d.get('unit', '')} với ưu tiên HIGH.")
                    }
                return {
                    "type": "text",
                    "content": (f"Mặt hàng {last_obs.get('sku')} ({d.get('product_name')}) còn {days_left} ngày bán "
                                f"(tồn {d.get('stock_quantity')} {d.get('unit')}, bán {d.get('avg_daily_sales')}/ngày), "
                                f"trên ngưỡng {threshold} ngày nên chưa cần tạo đơn nhập gấp."),
                    "thought": f"Số ngày còn hàng {days_left} >= ngưỡng {threshold}, không cần tạo đơn nhập."
                }

            # Đã có kết quả tạo đơn hoặc tra cứu đơn thuần -> tổng hợp Final Answer
            if last_obs.get("order_id"):
                return {
                    "type": "text",
                    "content": f"{last_obs.get('message')} Tổng chi phí ước tính: {last_obs.get('estimated_cost'):,} VND.",
                    "thought": "Đơn nhập đã được tạo thành công, tổng hợp kết quả cho người dùng."
                }
            if "data" in last_obs:
                d = last_obs["data"]
                alert = "⚠️ CẦN ưu tiên nhập hàng." if d.get("restock_alert") else "Tồn kho vẫn ở mức an toàn."
                return {
                    "type": "text",
                    "content": (f"Mặt hàng {last_obs.get('sku')} - {d.get('product_name')}: tồn kho {d.get('stock_quantity')} {d.get('unit')}, "
                                f"bán trung bình {d.get('avg_daily_sales')} {d.get('unit')}/ngày, còn đủ bán khoảng {d.get('days_of_stock_left')} ngày. "
                                f"Nhà cung cấp: {d.get('supplier')}, nhập gần nhất {d.get('last_restock_date')}. {alert}"),
                    "thought": "Đã có dữ liệu tồn kho từ Tool, tổng hợp câu trả lời cuối cùng."
                }
            return {
                "type": "text",
                "content": f"Kết quả từ hệ thống: {last_obs.get('message', json.dumps(last_obs, ensure_ascii=False))}",
                "thought": "Tổng hợp kết quả Observation thành câu trả lời."
            }

        # ---------- Chưa có Observation: nhận diện intent ban đầu ----------
        wants_order = ("tạo đơn" in q or "đặt hàng" in q or "nhập" in q)
        wants_lookup = ("tra cứu" in q or "kiểm tra" in q or "tồn kho" in q or "còn đủ" in q)

        if sku and wants_order and not wants_lookup:
            qty = self._extract_int(r"nhập\s+(\d+)", user_query, 100)
            priority = "HIGH" if ("cao" in q or "gấp" in q) else ("LOW" if "thấp" in q else "MEDIUM")
            date_m = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", user_query)
            args = {"sku": sku, "quantity": qty, "priority": priority}
            if date_m:
                args["delivery_date"] = date_m.group(1)
            return {
                "type": "tool_call",
                "tool_name": "create_restock_order",
                "arguments": args,
                "thought": f"Người dùng yêu cầu tạo đơn nhập cho {sku} với đầy đủ thông tin. Gọi tool create_restock_order."
            }
        if sku and (wants_lookup or wants_order):
            return {
                "type": "tool_call",
                "tool_name": "inventory_query",
                "arguments": {"sku": sku},
                "thought": f"Cần dữ liệu tồn kho thời gian thực của {sku} trước khi trả lời. Gọi tool inventory_query."
            }
        return {
            "type": "text",
            "content": ("[Mock Agent Response]: Nguyên tắc cơ bản: theo dõi tốc độ bán trung bình/ngày của từng mặt hàng, "
                        "tính số ngày còn đủ bán = tồn kho / tốc độ bán; mặt hàng nào còn dưới 3 ngày bán thì ưu tiên nhập trước, "
                        "đồng thời cân nhắc mùa vụ, khuyến mãi và sự kiện làm tăng nhu cầu."),
            "thought": "Câu hỏi chung về nguyên tắc quản lý tồn kho, trả lời trực tiếp không cần gọi Tool."
        }


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider (Native Tool Calling với Google GenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-2.5-flash"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(model=self.model_name, contents=contents)
            return response.text
        except Exception as e:
            return f"[Gemini Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            print("ℹ️ [Gemini Provider]: Chưa tìm thấy GEMINI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)
        
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            
            # Chuẩn hóa function declarations cho Gemini SDK
            function_declarations = []
            for tool in tools_schema:
                # Bỏ qua các tool schema chưa được định nghĩa hoàn chỉnh
                if not tool.get("name") or not tool.get("parameters"):
                    continue
                function_declarations.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {})
                })

            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
                tools=[{"function_declarations": function_declarations}] if function_declarations else None,
                temperature=0.2
            )

            response = _call_with_retry(
                lambda: client.models.generate_content(model=self.model_name, contents=prompt, config=config),
                provider_label="Gemini Provider"
            )
            provider_label = f"gemini/{self.model_name}"

            # Kiểm tra xem Gemini có trả về Tool Call không
            if response.function_calls:
                call = response.function_calls[0]
                args = dict(call.args) if hasattr(call, 'args') and call.args else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.name,
                    "arguments": args,
                    "thought": f"Gemini quyết định gọi công cụ '{call.name}' với tham số: {json.dumps(args, ensure_ascii=False)}",
                    "provider": provider_label
                }
            else:
                return {
                    "type": "text",
                    "content": response.text or "",
                    "thought": "Gemini phản hồi trực tiếp bằng văn bản (không cần gọi công cụ).",
                    "provider": provider_label
                }

        except Exception as e:
            print(f"⚠️ [Gemini API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (Native Tool Calling với OpenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return "[OpenAI Error]: Chưa cấu hình OPENAI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(model=self.model_name, messages=messages)
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[OpenAI Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            print("ℹ️ [OpenAI Provider]: Chưa tìm thấy OPENAI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)

            tools = []
            for tool in tools_schema:
                if not tool.get("name"):
                    continue
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {})
                    }
                })

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = _call_with_retry(
                lambda: client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    tools=tools if tools else None,
                    tool_choice="auto" if tools else None
                ),
                provider_label="OpenAI Provider"
            )
            provider_label = f"openai/{self.model_name}"

            msg = response.choices[0].message
            if msg.tool_calls:
                call = msg.tool_calls[0]
                args = json.loads(call.function.arguments) if call.function.arguments else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.function.name,
                    "arguments": args,
                    "thought": f"OpenAI quyết định gọi công cụ '{call.function.name}' với tham số: {json.dumps(args, ensure_ascii=False)}",
                    "provider": provider_label
                }
            else:
                return {
                    "type": "text",
                    "content": msg.content or "",
                    "thought": "OpenAI phản hồi trực tiếp bằng văn bản (không cần gọi công cụ).",
                    "provider": provider_label
                }
        except Exception as e:
            print(f"⚠️ [OpenAI API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)


def get_llm_provider() -> BaseLLMProvider:
    """Factory function khởi tạo Provider theo LLM_PROVIDER env variable"""
    provider_type = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    if provider_type == "gemini":
        key = os.getenv("GEMINI_API_KEY")
        if key and key != "your_gemini_api_key_here":
            return GeminiProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if key and key != "your_openai_api_key_here":
            return OpenAIProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "mock":
        return MockOfflineProvider()
    else:
        return MockOfflineProvider()
