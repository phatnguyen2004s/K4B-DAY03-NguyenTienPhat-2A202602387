"""
🔌 MODEL CONTEXT PROTOCOL (MCP) SERVER MODULE
Mô phỏng kiến trúc MCP Server (Client-Server Architecture) cung cấp công cụ chuẩn hóa.
"""

import json
import sys
from typing import Dict, Any, List
from tools import TOOLS_SCHEMA, dispatch_tool_call

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

class MCPAcademicServer:
    """
    Giả lập MCP Server tuân thủ chuẩn giao thức Model Context Protocol
    """
    def __init__(self, server_name: str = "store-inventory-mcp-server"):
        self.server_name = server_name
        self.version = "2026.1.0"
        
    def list_tools(self) -> List[Dict[str, Any]]:
        """Trả về danh sách các Tools chuẩn giao thức MCP"""
        return TOOLS_SCHEMA
        
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        [TASK 2.1] HỌC VIÊN HOÀN THIỆN HÀM THỰC THI TOOL TRÊN MCP SERVER
        Thực thi request gọi Tool theo chuẩn MCP JSON-RPC
        """
        # --------------------------------------------------------------------------
        # TODO 2.1: HỌC VIÊN HOÀN THIỆN HÀM GỌI TOOL CHUẨN MCP JSON-RPC
        # 🎯 YÊU CẦU THỰC THI THUẬT TOÁN:
        # 1. Gọi hàm dispatch_tool_call(tool_name, arguments) để lấy chuỗi JSON kết quả từ Tool Router.
        # 2. Chuyển đổi chuỗi JSON kết quả thành Python Dictionary (dùng json.loads).
        # 3. Đóng gói phản hồi và trả về Dict theo đúng chuẩn giao thức MCP JSON-RPC 2.0:
        #    - Các trường bắt buộc: "jsonrpc": "2.0", "server": self.server_name, "tool": tool_name, "result": content
        # --------------------------------------------------------------------------
        # Bước 1: Điều tuyến sang Tool Router để thực thi tool, nhận về chuỗi JSON
        raw_result = dispatch_tool_call(tool_name, arguments)

        # Bước 2: Parse chuỗi JSON thành Python Dict (fallback nếu tool trả về text thường)
        try:
            content = json.loads(raw_result)
        except (json.JSONDecodeError, TypeError):
            content = {"status": "RAW_OUTPUT", "content": str(raw_result)}

        # Bước 3: Đóng gói phản hồi theo chuẩn MCP JSON-RPC 2.0
        return {
            "jsonrpc": "2.0",
            "server": self.server_name,
            "tool": tool_name,
            "result": content
        }


if __name__ == "__main__":
    print("==========================================================")
    print("🔌 KIỂM THỬ ĐỘC LẬP MCP SERVER (store-inventory-mcp-server)")
    print("==========================================================")
    
    server = MCPAcademicServer()
    tools = server.list_tools()
    print(f"✅ Khởi tạo thành công MCP Server: {server.server_name} (Version: {server.version})")
    print(f"📦 Số lượng Tools công bố: {len(tools)}")
    
    # Kiểm tra trạng thái TODO 1.2 (Tool Schema)
    order_tool = next((t for t in tools if t.get("name") == "create_restock_order"), None)
    if not order_tool or not order_tool.get("parameters", {}).get("properties"):
        print("⏳ [TODO 1.2]: Tool 'create_restock_order' chưa được định nghĩa properties trong 'src/tools.py'.")
    else:
        print(f"✅ [TODO 1.2]: Tool 'create_restock_order' đã có schema đầy đủ "
              f"(required: {order_tool['parameters'].get('required')}).")

    # Kiểm tra trạng thái TODO 2.1 (call_tool)
    test_result = server.call_tool("inventory_query", {"sku": "SKU001"})
    if not test_result:
        print("⏳ [TODO 2.1]: Hàm call_tool() đang trả về rỗng. Học viên hãy hoàn thiện TODO 2.1 trong 'src/mcp_server.py'!")
    else:
        print(f"✅ [TODO 2.1]: Test dispatch tool 'inventory_query' thành công:")
        print(f"   Phản hồi JSON-RPC: {json.dumps(test_result, ensure_ascii=False)}")

    # Kiểm tra thêm: tool hành động + edge case
    test_order = server.call_tool("create_restock_order", {"sku": "SKU002", "quantity": 210, "priority": "HIGH"})
    print(f"✅ Test 'create_restock_order': {test_order['result'].get('status')} - {test_order['result'].get('order_id')}")
    test_missing = server.call_tool("inventory_query", {"sku": "SKU9999"})
    print(f"✅ Test edge case SKU9999: {test_missing['result'].get('status')}")
