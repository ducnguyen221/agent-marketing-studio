# Khâu ④: Máy Tự Kiểm Tra Chất Lượng (Self-QA)

| Thuộc tính | Chi tiết |
|---|---|
| **Vai trò chính** | `qa-reviewer` (kiểm tra tuân thủ & chặn lỗi) · `content-editor` (tư vấn chất lượng) |
| **Đầu vào (Input)** | Dòng `Post` có `agent_status = completed` |
| **Công cụ (Tools)** | [`.agents/checklists/QA_ASSET.md`](../.agents/checklists/QA_ASSET.md) |
| **Đầu ra (Output)** | `quality_check = passed` / `needs_review` / `failed` trong sheet `Post` |

---

## 1. Trình Tự Thực Thi

1. **Chạy Bộ Checklist QA:**
   - Đối chiếu với bảng kiểm tra [`.agents/checklists/QA_ASSET.md`](../.agents/checklists/QA_ASSET.md).
   - Kiểm tra giọng văn thương hiệu (`output_styles/`).
   - Kiểm tra rò rỉ tên công cụ nội bộ (không chứa prompt, engine name).
   - Kiểm tra tag `[KIỂM CHỨNG]` còn sót lại hay không.
   - Kiểm tra quy chuẩn định dạng từng kênh (Facebook không để markdown code block, Blog có đủ H2/H3 và meta description).
2. **Cập nhật Trạng Thái:**
   - Nếu đạt: `quality_check = passed`.
   - Nếu còn nghi vấn: `quality_check = needs_review` (không tự ý đánh dấu passed).
   - Nếu trượt: `quality_check = failed`, `agent_status = ai_qa_failed`, ghi rõ lý do vào `review_feedback`.
3. **Trình Con Người:** Đặt `post_status = human_review`.

---

## 🔒 CỔNG 2: PHÊ DUYỆT XUẤT BẢN (Human Gate 2)

> ⚠️ **Điều kiện tiên quyết để chuyển sang Khâu ⑤ Render và Khâu ⑥ Publish:**
> - `Post.review_status = approved`
> 
> **Agent TUYỆT ĐỐI KHÔNG tự động tick duyệt cổng này.**