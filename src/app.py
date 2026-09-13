"""
🚀 CORE AGENT APPLICATION (DAY 03: CHATBOT VS REACT AGENT)
Thực thi so sánh giữa Chatbot Baseline (Cấp 2) và ReAct Agent kết nối MCP Server (Cấp 3).
"""

import json
import os
import sys
import time
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from mcp_server import MCPInventoryServer
from prompts import (
    CHATBOT_BASELINE_PROMPT,
    REACT_AGENT_SYSTEM_PROMPT,
    REACT_SCRATCHPAD_TEMPLATE,
    MAX_ITERATIONS
)
from providers import get_llm_provider

load_dotenv()

def load_test_cases():
    """Tải danh sách 5 test cases từ config/test_cases.json hoặc config/test_cases.example.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    if not os.path.exists(config_path):
        example_path = os.path.join(base_dir, "config", "test_cases.example.json")
        if os.path.exists(example_path):
            print("⚠️ [CONFIG NOTICE]: Chưa thấy file 'config/test_cases.json'. Đang dùng mẫu 'config/test_cases.example.json'.")
            print("👉 Hãy chạy: copy config/test_cases.example.json config/test_cases.json và viết test cases theo đề tài của bạn!\n")
            config_path = example_path
        else:
            config_path = "test_cases.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_waterfall_trace(trace_data: list):
    """Ghi vết log Waterfall Trace Log ra file docs/trace_waterfall.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    trace_path = os.path.join(docs_dir, "trace_waterfall.json")
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, ensure_ascii=False, indent=2)
    print(f"📊 [OBSERVABILITY]: Đã lưu {len(trace_data)} sự kiện Waterfall Trace tại '{trace_path}'!")


def run_baseline_chatbot(user_query: str, provider):
    """Chạy Chatbot gốc (Cấp 2) không có công cụ gọi Tool"""
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot phản hồi:\n{response}")


def build_react_prompt(user_query: str, scratchpad: list) -> str:
    """
    Ghép câu hỏi gốc với lịch sử Thought/Action/Observation (scratchpad)
    để nạp lại cho LLM ở vòng lặp kế tiếp.
    """
    if not scratchpad:
        return user_query
    history_lines = []
    for entry in scratchpad:
        history_lines.append(
            f"Step {entry['step']}:\n"
            f"  Thought: {entry['thought']}\n"
            f"  Action: {entry['tool_name']}({json.dumps(entry['arguments'], ensure_ascii=False)})\n"
            f"  Observation: {json.dumps(entry['observation'], ensure_ascii=False)}"
        )
    return f"{user_query}\n" + REACT_SCRATCHPAD_TEMPLATE.format(history="\n".join(history_lines))


def summarize_observations(scratchpad: list) -> str:
    """Câu trả lời dự phòng khi vòng lặp kết thúc mà LLM chưa đưa ra Final Answer"""
    if not scratchpad:
        return "Chưa thu thập được dữ liệu nào từ MCP Server để trả lời."
    parts = []
    for entry in scratchpad:
        obs = entry["observation"]
        if obs.get("message"):
            parts.append(obs["message"])
        else:
            parts.append(f"{entry['tool_name']} -> {json.dumps(obs, ensure_ascii=False)}")
    return "Tổng hợp kết quả từ các công cụ: " + " | ".join(parts)


def run_react_agent(user_query: str, provider, mcp_server: MCPInventoryServer) -> list:
    """
    [REACT AGENT LOOP - TASK 2.2] Thực thi vòng lặp Thought -> Action -> Observation với MCP Server
    - type == "text"      : LLM đưa ra Final Answer -> in kết luận và dừng vòng lặp.
    - type == "tool_call" : Thực thi Tool qua MCP Server, nạp Observation vào scratchpad cho lượt kế tiếp.
    Trả về danh sách trace log (Waterfall Trace) của phiên thực thi.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")

    step = 0
    trace_logs = []
    scratchpad = []          # Lịch sử Thought/Action/Observation nạp lại cho LLM
    executed_calls = set()   # Guard chống lặp vô hạn: (tool_name, arguments) đã gọi
    tools_list = mcp_server.list_tools()
    final_answer = None

    while step < MAX_ITERATIONS:
        step += 1
        step_start_time = time.time()
        print(f"\n--- 🔄 Vòng lặp ReAct Loop (Step {step}/{MAX_ITERATIONS}) ---")

        # Gọi LLM với Native Tool Calling Specs + lịch sử Observation (nếu có)
        prompt = build_react_prompt(user_query, scratchpad)
        llm_response = provider.generate_with_tools(prompt, tools_list, system_prompt=REACT_AGENT_SYSTEM_PROMPT)
        llm_latency_ms = round((time.time() - step_start_time) * 1000, 2)

        thought = llm_response.get("thought", "Đang suy luận...")
        llm_provider = llm_response.get("provider", "unknown")
        print(f"🧠 [Thought]: {thought}")

        # ---------------- Trường hợp 1: LLM trả lời bằng văn bản (Final Answer) ----------------
        if llm_response.get("type") == "text":
            final_answer = llm_response.get("content", "") or summarize_observations(scratchpad)
            print(f"🏁 [Final Answer]: {final_answer}")
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "provider": llm_provider,
                "thought": thought,
                "output": final_answer,
                "latency_ms": llm_latency_ms
            })
            break

        # ---------------- Trường hợp 2: LLM đề xuất gọi Tool (Action) ----------------
        elif llm_response.get("type") == "tool_call":
            tool_name = llm_response.get("tool_name")
            arguments = llm_response.get("arguments", {}) or {}
            print(f"🛠️ [Action Proposed]: {tool_name}({json.dumps(arguments, ensure_ascii=False)})")

            # Guard: LLM gọi lại y hệt một tool đã có Observation -> dừng để tránh lặp vô hạn
            call_signature = (tool_name, json.dumps(arguments, sort_keys=True, ensure_ascii=False))
            if call_signature in executed_calls:
                print(f"⚠️ [LOOP GUARD]: Tool '{tool_name}' với tham số này đã được gọi trước đó. Dừng vòng lặp.")
                final_answer = summarize_observations(scratchpad)
                trace_logs.append({
                    "step": step,
                    "query": user_query,
                    "action_type": "LOOP_GUARD_STOP",
                    "thought": thought,
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "output": final_answer,
                    "latency_ms": llm_latency_ms
                })
                print(f"🏁 [Final Answer]: {final_answer}")
                break
            executed_calls.add(call_signature)

            # Thực thi Tool qua MCP Server (JSON-RPC) và đo thời gian thực thi tool
            tool_start_time = time.time()
            mcp_result = mcp_server.call_tool(tool_name, arguments)
            tool_latency_ms = round((time.time() - tool_start_time) * 1000, 2)
            obs_data = mcp_result.get("result", {}) if mcp_result else {}

            if not obs_data:
                print("👁️ [Observation từ MCP Server]: {}")
                print("⚠️ [CHÚ Ý]: MCP Server trả về kết quả rỗng! Hãy kiểm tra TODO 2.1 trong 'src/mcp_server.py'.")
                obs_data = {"status": "EMPTY_RESULT", "message": "MCP Server không trả về dữ liệu."}
            else:
                print(f"👁️ [Observation từ MCP Server]: {json.dumps(obs_data, ensure_ascii=False)}")

            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "TOOL_EXECUTION",
                "provider": llm_provider,
                "thought": thought,
                "tool_name": tool_name,
                "arguments": arguments,
                "observation": obs_data,
                "mcp_server": mcp_result.get("server") if mcp_result else None,
                "latency_ms": llm_latency_ms,
                "tool_latency_ms": tool_latency_ms
            })

            # Nạp Observation vào scratchpad -> LLM sẽ đọc lại ở Step kế tiếp
            scratchpad.append({
                "step": step,
                "thought": thought,
                "tool_name": tool_name,
                "arguments": arguments,
                "observation": obs_data
            })
            continue

        # ---------------- Trường hợp khác: phản hồi không hợp lệ ----------------
        else:
            print(f"⚠️ [WARNING]: Phản hồi LLM không hợp lệ: {llm_response}")
            final_answer = summarize_observations(scratchpad)
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "INVALID_RESPONSE",
                "provider": llm_provider,
                "thought": thought,
                "output": final_answer,
                "latency_ms": llm_latency_ms
            })
            break

    # Hết MAX_ITERATIONS mà LLM vẫn chưa kết luận -> trả lời dự phòng từ các Observation đã có
    if final_answer is None:
        final_answer = summarize_observations(scratchpad)
        print(f"⏱️ [MAX ITERATIONS]: Đã đạt giới hạn {MAX_ITERATIONS} vòng lặp. Tổng hợp kết quả hiện có.")
        print(f"🏁 [Final Answer]: {final_answer}")
        trace_logs.append({
            "step": step + 1,
            "query": user_query,
            "action_type": "MAX_ITERATIONS_REACHED",
            "thought": "Đạt giới hạn vòng lặp, tổng hợp từ các Observation đã thu thập.",
            "output": final_answer,
            "latency_ms": 0.0
        })

    return trace_logs


if __name__ == "__main__":
    print("==========================================================")
    print("🏫 VINUNI AI COURSE - DAY 03 LAB: CHATBOT VS REACT AGENT")
    print("==========================================================")
    
    provider = get_llm_provider()
    mcp_server = MCPInventoryServer()
    
    print(f"🔌 LLM Provider: {provider.__class__.__name__}")
    print(f"🌐 MCP Server: {mcp_server.server_name}\n")
    
    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases thử nghiệm.\n")
    
    if "--interactive" in sys.argv:
        print("🎮 [INTERACTIVE MODE] Trò chuyện trực tiếp với ReAct Agent:")
        print("💡 Gợi ý câu hỏi thử nghiệm:")
        print("   - Câu hỏi chung: 'Nguyên tắc ưu tiên nhập hàng ở cửa hàng tiện lợi là gì?'")
        print("   - Tra cứu tồn kho: 'Hãy tra cứu tình hình tồn kho của mặt hàng SKU001'")
        print("   - Tạo đơn nhập: 'Tạo đơn nhập 200 đơn vị SKU001 ưu tiên cao, giao ngày 15/09/2026'")
        print("   - Đa bước: 'Kiểm tra SKU002 còn đủ bán mấy ngày, nếu dưới 3 ngày thì tạo đơn nhập gấp đủ bán 7 ngày'")
        print("   - Gõ 'exit' hoặc 'quit' để kết thúc phiên trò chuyện.\n")
        while True:
            try:
                user_input = input("👤 Quản lý cửa hàng hỏi: ").strip()
                if not user_input or user_input.lower() in ["exit", "quit"]:
                    print("👋 Tạm biệt! Kết thúc phiên trò chuyện.")
                    break
                logs = run_react_agent(user_input, provider, mcp_server)
                save_waterfall_trace(logs)
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Đã thoát phiên tương tác.")
                break
    elif "--all" in sys.argv:
        print("🚀 [TEST SUITE MODE] Kiểm tra 5 Test Cases:")
        completed_count = 0
        todo_count = 0
        all_traces = []
        
        for tc in tests:
            print(f"\n==================================================")
            print(f"🧪 [{tc['id']}] Loại test: {tc['type']} (Độ phức tạp: {tc['complexity']})")
            print(f"📌 Kỳ vọng: {tc['expected_behavior']}")
            
            if tc["question"].strip().startswith("TODO"):
                print(f"⏸️ [CHƯA KÍCH HOẠT - ĐANG LÀ TODO]:")
                print(f"   {tc['question']}")
                print(f"   👉 Hãy mở file 'config/test_cases.json' để viết câu hỏi thực tế cho Test Case này!")
                todo_count += 1
            else:
                logs = run_react_agent(tc["question"], provider, mcp_server)
                all_traces.extend(logs)
                completed_count += 1
                
        print(f"\n==================================================")
        print(f"📊 [KẾT QUẢ TEST SUITE]: Đã thực thi {completed_count}/{len(tests)} Test Cases | {todo_count} Test Cases đang chờ điền câu hỏi (TODO)")
        if all_traces:
            save_waterfall_trace(all_traces)
        print(f"💡 Để trò chuyện trực tiếp từng câu: Chạy 'python src/app.py --interactive'")
    else:
        # Chế độ mặc định khi chỉ gõ 'python src/app.py'
        print("ℹ️ HƯỚNG DẪN SỬ DỤNG CHƯƠNG TRÌNH:")
        print("  1. Chat trực tiếp liên tục:   python src/app.py --interactive")
        print("  2. Chạy toàn bộ Test Cases:    python src/app.py --all\n")
        
        sample_query = tests[1]["question"]
        print(f"--- 🏁 DEMO CHẠY THỬ 1 TEST CASE MẪU (TC02: Tra cứu tồn kho) ---")
        logs = run_react_agent(sample_query, provider, mcp_server)
        save_waterfall_trace(logs)
        print("\n💡 Hãy thử ngay lệnh: python src/app.py --interactive để chat trực tiếp!")
