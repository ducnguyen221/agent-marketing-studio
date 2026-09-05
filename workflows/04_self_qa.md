# Khâu ④: Máy Tự Kiểm Tra Chất Lượng (Self-QA)

| Thuộc tính | Chi tiết |
|---|---|
| **Vai trò chính** | `qa-reviewer` (kiểm tra tuân thủ & chặn lỗi) · `content-editor` (tư vấn chất lượng) |
| **Đầu vào (Input)** | `publish.json → posts[]` có `agent_status = completed` |
| **Công cụ (Tools)** | `scripts/pipeline/blog_gates.py` (23 cổng, kiểm bằng số) + [`.agents/checklists/QA_ASSET.md`](../.agents/checklists/QA_ASSET.md) |
| **Đầu ra (Output)** | `gates.json` + `quality_check = passed` / `failed` trong `publish.json` |

> **Ba trạng thái, không phải hai.** Mỗi cổng trả về xanh · đỏ · **thiếu**. "Thiếu" nghĩa là
> cổng không chạy được — thiếu file, thiếu tham số. Nó **không bao giờ** được cộng vào
> "xanh": không kiểm được là *chưa biết*, không phải *đã qua*. Một hệ mà "không kiểm được"
> bị tính là "đạt" thì càng nhiều cổng càng nguy hiểm.
>
> Miễn trừ một cổng thì **ghi lý do**: `--cho-phep "tên=lý do"`. Nới danh sách từ khoá cho
> đỡ đỏ là làm hỏng cổng đó cho mọi bài về sau.

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
   - Còn nghi vấn thì **không tự xác nhận `passed`** — để `failed` và ghi lý do, người quyết (không tự ý đánh dấu passed).
   - Trượt: `quality_check = failed`, `agent_status = blocked` (`register_publish qa` tự đặt cả hai), ghi rõ lý do vào `review_feedback`.
3. **Trình Con Người:** báo kết quả cổng, chờ Cổng 2. Không có trạng thái trung gian nào
   để đặt — `post_status` chỉ nhận `not_created` · `approved` · `published`.

---

## 🔒 CỔNG 2: PHÊ DUYỆT XUẤT BẢN (Human Gate 2)

> ⚠️ **Điều kiện tiên quyết để chuyển sang Khâu ⑤ Render và Khâu ⑥ Publish:**
> - `Post.review_status = approved`
> 
> **Agent TUYỆT ĐỐI KHÔNG tự động tick duyệt cổng này.**