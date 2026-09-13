"""
🛠️ TOOL DEFINITIONS & EXECUTION BACKEND
Mã nguồn chứa danh sách Tool Schemas (JSON Schema) và Execution Layer phục vụ cho MCP Server.

Chủ đề (Đề tài Mở): Trợ lý kiểm soát lưu lượng hàng hoá cửa hàng tiện lợi
  - inventory_query        : Tool TRA CỨU tồn kho & tốc độ tiêu thụ theo mã hàng (SKU)
  - create_restock_order   : Tool HÀNH ĐỘNG tạo đơn nhập hàng ưu tiên
"""

import json
from datetime import date
from typing import Dict, Any

# ==============================================================================
# 1. KHAI BÁO TOOL SCHEMAS CHUẨN NATIVE JSON SCHEMA (TASK 1.2)
# ==============================================================================

TOOLS_SCHEMA = [
    # Tool 1: Tra cứu tồn kho & nhịp độ tiêu thụ của một mặt hàng
    {
        "name": "inventory_query",
        "description": (
            "Tra cứu tình hình tồn kho và tốc độ tiêu thụ của một mặt hàng trong cửa hàng tiện lợi "
            "bằng mã hàng (SKU). Trả về số lượng tồn, tốc độ bán trung bình mỗi ngày, "
            "số ngày còn đủ bán, nhà cung cấp và ngày nhập gần nhất."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sku": {
                    "type": "string",
                    "description": "Mã hàng (SKU) cần tra cứu (ví dụ: 'SKU001')"
                }
            },
            "required": ["sku"]
        }
    },

    # Tool 2: Tạo đơn nhập hàng (hành động) cho một mặt hàng
    {
        "name": "create_restock_order",
        "description": (
            "Tạo đơn nhập hàng cho một mặt hàng khi tồn kho thấp hoặc theo yêu cầu của quản lý cửa hàng. "
            "Chỉ gọi tool này sau khi đã xác định rõ mã hàng, số lượng và mức ưu tiên."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sku": {
                    "type": "string",
                    "description": "Mã hàng (SKU) cần nhập (ví dụ: 'SKU001')"
                },
                "quantity": {
                    "type": "integer",
                    "description": "Số lượng đơn vị cần nhập (số nguyên dương, ví dụ: 200)"
                },
                "priority": {
                    "type": "string",
                    "enum": ["HIGH", "MEDIUM", "LOW"],
                    "description": "Mức ưu tiên của đơn nhập: HIGH (gấp, sắp hết hàng), MEDIUM, LOW"
                },
                "delivery_date": {
                    "type": "string",
                    "description": "Ngày mong muốn nhận hàng, định dạng DD/MM/YYYY (ví dụ: '15/09/2026')"
                }
            },
            "required": ["sku", "quantity", "priority"]
        }
    }
]

# ==============================================================================
# 2. MÔ PHỎNG DỮ LIỆU & HÀM THỰC THI TOOL (EXECUTION LAYER)
# ==============================================================================

MOCK_DATABASE = {
    "SKU001": {
        "product_name": "Nước suối Lavie 500ml",
        "category": "Đồ uống",
        "stock_quantity": 320,
        "avg_daily_sales": 45,
        "unit": "chai",
        "unit_price": 6000,
        "supplier": "Công ty Lavie Việt Nam",
        "last_restock_date": "10/09/2026"
    },
    "SKU002": {
        "product_name": "Mì ly Hảo Hảo tôm chua cay",
        "category": "Thực phẩm ăn liền",
        "stock_quantity": 40,
        "avg_daily_sales": 30,
        "unit": "ly",
        "unit_price": 9000,
        "supplier": "Acecook Việt Nam",
        "last_restock_date": "05/09/2026"
    },
    "SKU003": {
        "product_name": "Sữa tươi Vinamilk 1L",
        "category": "Sữa & sản phẩm từ sữa",
        "stock_quantity": 85,
        "avg_daily_sales": 20,
        "unit": "hộp",
        "unit_price": 32000,
        "supplier": "Vinamilk",
        "last_restock_date": "11/09/2026"
    }
}


def execute_inventory_query(sku: str) -> str:
    """Thực thi tra cứu tồn kho & tốc độ tiêu thụ theo mã hàng (SKU)"""
    sku_key = sku.strip().upper()
    item = MOCK_DATABASE.get(sku_key)
    if item:
        avg = item["avg_daily_sales"]
        days_left = round(item["stock_quantity"] / avg, 1) if avg > 0 else None
        return json.dumps({
            "status": "SUCCESS",
            "sku": sku_key,
            "data": {
                **item,
                "days_of_stock_left": days_left,
                "restock_alert": days_left is not None and days_left < 3
            }
        }, ensure_ascii=False)
    else:
        return json.dumps({
            "status": "NOT_FOUND",
            "message": f"Không tìm thấy mặt hàng có mã '{sku}' trong hệ thống tồn kho"
        }, ensure_ascii=False)


def execute_create_restock_order(sku: str, quantity: int, priority: str = "MEDIUM", delivery_date: str = "") -> str:
    """Thực thi tạo đơn nhập hàng cho một mặt hàng"""
    sku_key = sku.strip().upper()
    item = MOCK_DATABASE.get(sku_key)
    if not item:
        return json.dumps({
            "status": "NOT_FOUND",
            "message": f"Không thể tạo đơn nhập: mã hàng '{sku}' không tồn tại trong hệ thống"
        }, ensure_ascii=False)

    priority = priority.strip().upper()
    if priority not in ("HIGH", "MEDIUM", "LOW"):
        return json.dumps({
            "status": "INVALID_ARGUMENT",
            "message": f"Mức ưu tiên '{priority}' không hợp lệ. Chỉ chấp nhận HIGH / MEDIUM / LOW"
        }, ensure_ascii=False)

    quantity = int(quantity)
    if quantity <= 0:
        return json.dumps({
            "status": "INVALID_ARGUMENT",
            "message": "Số lượng nhập phải là số nguyên dương"
        }, ensure_ascii=False)

    order_id = f"PO-{sku_key}-{date.today().strftime('%Y%m%d')}"
    return json.dumps({
        "status": "SUCCESS",
        "order_id": order_id,
        "sku": sku_key,
        "product_name": item["product_name"],
        "quantity": quantity,
        "unit": item["unit"],
        "priority": priority,
        "supplier": item["supplier"],
        "delivery_date": delivery_date or "Sớm nhất có thể",
        "estimated_cost": quantity * item["unit_price"],
        "message": (
            f"Đã tạo đơn nhập {order_id}: {quantity} {item['unit']} {item['product_name']} "
            f"(ưu tiên {priority}) từ {item['supplier']}, giao {delivery_date or 'sớm nhất có thể'}."
        )
    }, ensure_ascii=False)


# Router gọi tool thực tế
TOOL_ROUTER = {
    "inventory_query": execute_inventory_query,
    "create_restock_order": execute_create_restock_order
}

def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Hàm trung chuyển thực thi tool"""
    if tool_name in TOOL_ROUTER:
        try:
            return TOOL_ROUTER[tool_name](**arguments)
        except Exception as e:
            return json.dumps({"status": "EXECUTION_ERROR", "error": str(e)}, ensure_ascii=False)
    return json.dumps({"status": "UNKNOWN_TOOL", "error": f"Tool '{tool_name}' không tồn tại!"}, ensure_ascii=False)


# ==============================================================================
# 3. KIỂM THỬ ĐỘC LẬP DISPATCHER (CHECKPOINT 2): python src/tools.py
# ==============================================================================
if __name__ == "__main__":
    import sys
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    tool_names = [t["name"] for t in TOOLS_SCHEMA]
    print(f"✅ [TOOLS CHECK]: Đã đăng ký thành công {len(TOOLS_SCHEMA)} Native Tools trong TOOLS_SCHEMA! {tool_names}")

    result = json.loads(dispatch_tool_call("inventory_query", {"sku": "SKU001"}))
    if result.get("status") == "SUCCESS":
        d = result["data"]
        print(f"🧪 Kết quả gọi thử inventory_query: Status SUCCESS "
              f"({d['product_name']} - tồn {d['stock_quantity']} {d['unit']}, còn {d['days_of_stock_left']} ngày bán)")
    else:
        print(f"❌ Kết quả gọi thử inventory_query: {result}")

    result = json.loads(dispatch_tool_call(
        "create_restock_order", {"sku": "SKU002", "quantity": 210, "priority": "HIGH", "delivery_date": "15/09/2026"}
    ))
    print(f"🧪 Kết quả gọi thử create_restock_order: Status {result.get('status')} ({result.get('message', result)})")

    result = json.loads(dispatch_tool_call("inventory_query", {"sku": "SKU9999"}))
    print(f"🧪 Kết quả gọi thử edge case SKU9999: Status {result.get('status')}")
