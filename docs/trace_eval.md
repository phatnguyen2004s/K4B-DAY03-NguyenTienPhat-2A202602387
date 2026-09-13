# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** Nguyễn Tiến Phát  
> **Mã Sinh Viên / Mã Học viên:** 2A202602387  
> **Chủ đề Lựa chọn:** Trợ lý hỗ trợ kiểm soát lưu lượng hàng hoá: Hỗ trợ kiểm soát nhịp độ tiêu thụ hàng hoá của cửa hàng tiện lợi nhằm đưa ra những quyết định nên ưu tiên nhập mặt hàng nào.   

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- | :---: | :--- |
| **1. Multi-step Reasoning** | 4 / 5 | Bài toán không chỉ là tra cứu số liệu mà cần suy luận nhiều bước nối tiếp: tra cứu tồn kho và tốc độ tiêu thụ (velocity) của mặt hàng → tính số ngày còn đủ bán (days-of-stock-left) → đối chiếu ngưỡng an toàn, cân nhắc yếu tố mùa vụ/khuyến mãi → kết luận mặt hàng nào cần ưu tiên nhập và nhập bao nhiêu. Đây là suy luận đa yếu tố, gần mức "research agent" hơn là tra cứu FAQ (1/5). Chưa đạt 5 vì chuỗi bước còn tương đối cố định (tra cứu → tính → đặt hàng). |
| **2. Tool Interaction** | 4 / 5 | Hệ thống bắt buộc kết nối MCP Server với 2 công cụ: `inventory_query` (truy vấn cơ sở dữ liệu tồn kho/bán hàng thời gian thực) và `create_restock_order` (tạo đơn nhập hàng vào hệ thống). Có thể mở rộng thêm nguồn dữ liệu ngoài (thời tiết, lịch sự kiện địa phương ảnh hưởng nhu cầu). Cần phối hợp kết quả giữa các tool chứ không chỉ gọi đơn lẻ. |
| **3. Dynamic Decision** | 3 / 5 | Quyết định nhập hay không, nhập bao nhiêu, ưu tiên mức nào phụ thuộc hoàn toàn vào Observation của bước tra cứu (ví dụ TC04: chỉ tạo đơn khi số ngày còn hàng < 3). Tình huống bất ngờ (mặt hàng hết đột ngột, sự kiện làm tăng nhu cầu) khiến rule cứng không đủ. Tuy nhiên chỉ để 3 vì phần lớn logic vẫn có thể rule-hoá bằng ngưỡng số liệu tương đối rõ ràng (tồn kho < X ngày bán trung bình → cảnh báo). |
| **4. Long Horizon Goal** | 3 / 5 | Mục tiêu "không đứt hàng, không tồn kho thừa" là xuyên suốt và lặp lại theo chu kỳ nhập hàng, agent phải giữ mục tiêu này khi ra quyết định cho từng mặt hàng. Nhưng mỗi lượt xử lý (tra cứu → quyết định → tạo đơn) kết thúc trong một phiên ngắn, chưa cần theo dõi và tự điều chỉnh kế hoạch qua nhiều lượt dài hạn. |
| **TỔNG ĐIỂM AGENTIC FIT** | **14 / 20** | *Tổng điểm 14/20 > 12 → Bài toán phù hợp triển khai Agentic System (ReAct Agent) thay vì Chatbot Baseline: agent tự quyết định gọi tool nào, khi nào và lặp lại truy vấn/tính toán tuỳ theo dữ liệu thu được, vượt trội so với chatbot cố định 1–2 tool.* |

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

> ⚠️ **YÊU CẦU NGHIỆM THU:** Mở tệp `.env` điền `GEMINI_API_KEY` (hoặc `OPENAI_API_KEY`) để kết nối LLM thật trước khi thực thi `python src/app.py --all`. Bài nộp chỉ dùng Mock Offline Provider sẽ không đạt điểm nghiệm thực tế.

**Cấu hình thực thi:** `LLM_PROVIDER=gemini`, `LLM_MODEL=gemini-3.5-flash` (Google AI Studio Free Tier), MCP Server `store-inventory-mcp-server` với 2 tool `inventory_query` và `create_restock_order`. Mỗi sự kiện trace ghi rõ trường `provider` để xác nhận bước đó do LLM thật quyết định (không có sự kiện nào mang nhãn `mock`).

### 2.1. Tổng quan 10 sự kiện trong `docs/trace_waterfall.json`

| TC | Step | action_type | provider | tool_name | latency_ms (LLM) | tool_latency_ms |
| :--- | :---: | :--- | :--- | :--- | ---: | ---: |
| TC01 | 1 | FINAL_ANSWER | gemini/gemini-3.5-flash | — | 5042.93 | — |
| TC02 | 1 | TOOL_EXECUTION | gemini/gemini-3.5-flash | inventory_query | 1620.38 | 0.09 |
| TC02 | 2 | FINAL_ANSWER | gemini/gemini-3.5-flash | — | 8327.68 | — |
| TC03 | 1 | TOOL_EXECUTION | gemini/gemini-3.5-flash | create_restock_order | 2503.91 | 0.12 |
| TC03 | 2 | FINAL_ANSWER | gemini/gemini-3.5-flash | — | 3063.68 | — |
| TC04 | 1 | TOOL_EXECUTION | gemini/gemini-3.5-flash | inventory_query | 2640.69 | 0.10 |
| TC04 | 2 | TOOL_EXECUTION | gemini/gemini-3.5-flash | create_restock_order | 33316.14 * | 0.11 |
| TC04 | 3 | FINAL_ANSWER | gemini/gemini-3.5-flash | — | 6512.52 | — |
| TC05 | 1 | TOOL_EXECUTION | gemini/gemini-3.5-flash | inventory_query | 1443.62 | 0.05 |
| TC05 | 2 | FINAL_ANSWER | gemini/gemini-3.5-flash | — | 2178.11 | — |

> \* `latency_ms` của TC04 Step 2 bao gồm ~27s chờ retry do Free Tier giới hạn 5 request/phút (429 RESOURCE_EXHAUSTED). Provider đã được bổ sung cơ chế `_call_with_retry()` đọc `retryDelay` và tự gọi lại thay vì fallback Mock.

**Nhận xét quan sát:** Toàn bộ độ trễ nằm ở phía LLM (1.4s – 8.3s/lượt); thời gian thực thi tool trên MCP Server chỉ ~0.1ms vì dữ liệu mock in-memory. Trong hệ thống thật, tối ưu nên tập trung vào giảm số vòng lặp LLM (prompt rõ ràng, tool trả về đủ dữ liệu phái sinh như `days_of_stock_left` để LLM không phải gọi thêm).

### 2.2. Trích xuất log tiêu biểu — TC04 (ReAct đa bước: Tra cứu → Quyết định → Tạo đơn)

Đây là bằng chứng rõ nhất cho tiêu chí **Dynamic Decision**: ở Step 2, LLM đọc Observation của Step 1 (`days_of_stock_left = 1.3 < 3`), tự tính `avg_daily_sales × 7 = 30 × 7 = 210` rồi mới quyết định gọi `create_restock_order` với `priority = HIGH`. Số 210 không xuất hiện trong câu hỏi hay prompt — hoàn toàn do LLM suy luận từ dữ liệu tool trả về.

```json
[
  {
    "step": 1,
    "query": "Kiểm tra mặt hàng SKU002 còn đủ bán bao nhiêu ngày. Nếu dưới 3 ngày thì tạo đơn nhập gấp (ưu tiên cao) với số lượng đủ bán cho 7 ngày tới.",
    "action_type": "TOOL_EXECUTION",
    "provider": "gemini/gemini-3.5-flash",
    "thought": "Gemini quyết định gọi công cụ 'inventory_query' với tham số: {\"sku\": \"SKU002\"}",
    "tool_name": "inventory_query",
    "arguments": { "sku": "SKU002" },
    "observation": {
      "status": "SUCCESS",
      "sku": "SKU002",
      "data": {
        "product_name": "Mì ly Hảo Hảo tôm chua cay",
        "stock_quantity": 40,
        "avg_daily_sales": 30,
        "unit": "ly",
        "supplier": "Acecook Việt Nam",
        "days_of_stock_left": 1.3,
        "restock_alert": true
      }
    },
    "mcp_server": "store-inventory-mcp-server",
    "latency_ms": 2640.69,
    "tool_latency_ms": 0.1
  },
  {
    "step": 2,
    "action_type": "TOOL_EXECUTION",
    "provider": "gemini/gemini-3.5-flash",
    "thought": "Gemini quyết định gọi công cụ 'create_restock_order' với tham số: {\"sku\": \"SKU002\", \"quantity\": 210, \"priority\": \"HIGH\"}",
    "tool_name": "create_restock_order",
    "arguments": { "sku": "SKU002", "quantity": 210, "priority": "HIGH" },
    "observation": {
      "status": "SUCCESS",
      "order_id": "PO-SKU002-20260913",
      "quantity": 210,
      "priority": "HIGH",
      "estimated_cost": 1890000,
      "message": "Đã tạo đơn nhập PO-SKU002-20260913: 210 ly Mì ly Hảo Hảo tôm chua cay (ưu tiên HIGH) từ Acecook Việt Nam, giao sớm nhất có thể."
    },
    "mcp_server": "store-inventory-mcp-server",
    "latency_ms": 33316.14,
    "tool_latency_ms": 0.11
  },
  {
    "step": 3,
    "action_type": "FINAL_ANSWER",
    "provider": "gemini/gemini-3.5-flash",
    "thought": "Gemini phản hồi trực tiếp bằng văn bản (không cần gọi công cụ).",
    "output": "... Số ngày còn đủ bán: 1.3 ngày (thấp hơn ngưỡng tối thiểu là 3 ngày). Vì số ngày còn đủ bán dưới 3 ngày, hệ thống đã tự động tạo đơn nhập hàng gấp (ưu tiên HIGH) ... Số lượng nhập: 30 ly/ngày × 7 ngày = 210 ly. Mã đơn nhập: PO-SKU002-20260913 ...",
    "latency_ms": 6512.52
  }
]
```

### 2.3. Trích xuất log — TC05 (Edge case: mã hàng không tồn tại, Anti-Hallucination)

```json
[
  {
    "step": 1,
    "query": "Tra cứu tồn kho của mặt hàng SKU9999.",
    "action_type": "TOOL_EXECUTION",
    "provider": "gemini/gemini-3.5-flash",
    "tool_name": "inventory_query",
    "arguments": { "sku": "SKU9999" },
    "observation": {
      "status": "NOT_FOUND",
      "message": "Không tìm thấy mặt hàng có mã 'SKU9999' trong hệ thống tồn kho"
    },
    "latency_ms": 1443.62
  },
  {
    "step": 2,
    "action_type": "FINAL_ANSWER",
    "provider": "gemini/gemini-3.5-flash",
    "output": "Rất tiếc, hệ thống không tìm thấy mặt hàng nào có mã **SKU9999** trong cơ sở dữ liệu tồn kho. Bạn vui lòng kiểm tra lại mã SKU xem đã chính xác chưa nhé!",
    "latency_ms": 2178.11
  }
]
```

Agent nhận `NOT_FOUND` và trả lời lịch sự, **không bịa bất kỳ số liệu tồn kho nào** — đúng kỳ vọng của test case.

### 2.4. Chế độ Interactive Chat CLI (`python src/app.py --interactive`)

Đã thử nghiệm 5 câu hỏi tự do, log đầy đủ lưu tại `docs/interactive_session.log`. Hai quan sát đáng chú ý từ LLM thật:

- Câu *"Tạo đơn nhập 200 đơn vị SKU001 ưu tiên cao, giao ngày 15 tháng 9 năm 2026"* → LLM tự chuẩn hoá ngày viết tự nhiên thành `"delivery_date": "15/09/2026"` đúng định dạng khai báo trong schema.
- Câu *"Kiểm tra tổn kho?"* (thiếu mã hàng, có lỗi chính tả) → LLM **không tự bịa SKU** để gọi tool mà hỏi lại người dùng: *"bạn vui lòng cung cấp mã hàng (SKU) cụ thể"*.

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [x] Đã điền API Key thật trong `.env` và xác nhận Agent chạy mượt mà trên LLM API thật (Gemini `gemini-3.5-flash`).
- **Tổng số Test Cases đã chạy thành công:** **5 / 5** test cases (TC01 direct_query, TC02 single_tool_query, TC03 restock_order, TC04 multi_step_reasoning, TC05 edge_case_handling).
- **Số lượt gọi Tool qua MCP Server chính xác:** **5** lượt (`inventory_query` × 3: SKU001, SKU002, SKU9999; `create_restock_order` × 2: SKU001/200/HIGH, SKU002/210/HIGH) — 100% đúng tool và đúng tham số so với `expected_behavior`.
- **Tổng số sự kiện Waterfall Trace:** 10 sự kiện, tất cả mang nhãn `provider = gemini/gemini-3.5-flash`.
- **Kết quả đẩy Repo nộp bài:** [x] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

### So sánh Chatbot Baseline (Cấp 2) vs ReAct Agent (Cấp 3) trên cùng bộ test

| Test Case | Chatbot Baseline (không có Tool) | ReAct Agent + MCP Server |
| :--- | :--- | :--- |
| TC01 – Câu hỏi chung | ✅ Trả lời được từ System Prompt | ✅ Trả lời trực tiếp, không gọi Tool (tránh tốn latency) |
| TC02 – Tra cứu SKU001 | ❌ "Không có quyền truy cập dữ liệu thời gian thực" | ✅ Gọi `inventory_query`, trả về số liệu thật |
| TC03 – Tạo đơn nhập | ❌ Không thể thực hiện hành động | ✅ Gọi `create_restock_order`, trích đủ 4 tham số |
| TC04 – Đa bước có điều kiện | ❌ Không thể | ✅ 2 tool call nối tiếp, quyết định dựa trên Observation |
| TC05 – Mã không tồn tại | ⚠️ Có nguy cơ bịa đặt | ✅ Nhận `NOT_FOUND`, trả lời trung thực |

### Ghi chú kỹ thuật & bài học rút ra

1. **Vòng lặp ReAct thật sự cần scratchpad:** Observation của bước trước phải được nạp lại vào prompt của bước sau (`build_react_prompt()` trong `src/app.py`), nếu không LLM không thể ra quyết định đa bước như TC04.
2. **Rate limit là rủi ro vận hành thực tế:** Free Tier Gemini giới hạn 5 req/phút và 20 req/ngày/model. Đã bổ sung retry với `retryDelay` và gắn nhãn `provider` vào trace để phân biệt minh bạch bước nào chạy LLM thật, bước nào fallback Mock.
3. **Thiết kế tool trả về dữ liệu phái sinh** (`days_of_stock_left`, `restock_alert`) giúp giảm số vòng lặp LLM và giảm sai số tính toán.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
