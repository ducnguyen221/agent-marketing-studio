---
scope: marketing-agent engine
governance_version: 2.0
canonical: true
---

# AGENTS.md — Quy Chuẩn Quản Trị & Vận Hành Cho AI Agent

> **marketing-agent** là hệ thống điều phối và thực thi chiến dịch marketing toàn diện kết hợp giữa con người và đa tác nhân AI Agent.
> **Quy ước nền tảng:** Mỗi chiến dịch = 1 thư mục + 1 hồ sơ `.md` + 1 workbook `.xlsx` (4 sheet). Excel quản lý trạng thái, con người kiểm soát 2 cổng duyệt.

---

## 1. Ranh Giới An Toàn & Quyền Hạn (Safety & Boundaries)

- **Pre-approved (Tự động thực thi):**
  - Đọc và phân tích hồ sơ chiến dịch, template, data model, output style.
  - Dự thảo nội dung, viết bài đa kênh vào file `<folder_path>/content.md`.
  - Đọc/ghi các trường trạng thái của Agent trong Excel (`agent_status`, `quality_check`).
  - Chạy script kiểm tra QA nội bộ.
- **Scope Gate (Phải có con người xác nhận):**
  - Chuyển sang khâu ③ Produce (Cần Cổng 1: `Content.status = approved` + `approved_date`).
  - Chuyển sang khâu ⑤ Render và ⑥ Publish (Cần Cổng 2: `Post.review_status = approved`).
  - Thay đổi cấu trúc bảng tính hoặc thêm trường dữ liệu mới vào Data Model.
- **Never (Tuyệt đối cấm):**
  - Tự ý đánh dấu đã duyệt ở Cổng 1 hoặc Cổng 2.
  - Tự ý xuất bản (Publish) ra môi trường live khi chưa có lệnh tường minh.
  - Đọc, lưu trữ hoặc in ra các API token, private keys, thông tin cá nhân khách hàng (PII).
  - Điền `0` thay cho các ô chưa có dữ liệu (ô rỗng là một giá trị hợp lệ).

---

## 2. Bản Đồ Ngữ Cảnh & Thứ Tự Đọc (Context Navigation)

> 📍 **Tra cứu nhanh tại [MAP.md](MAP.md) trước khi thực hiện bất kỳ nhiệm vụ nào.** Agent tuyệt đối không đọc toàn bộ kho tri thức một lúc.

### Ba nguồn tài liệu cốt lõi:
1. [`knowledge/data_model/DATA_MODEL.md`](knowledge/data_model/DATA_MODEL.md) — Định nghĩa chi tiết 75 trường dữ liệu và ràng buộc.
2. [`workflows/00_WORKFLOW_INDEX.md`](workflows/00_WORKFLOW_INDEX.md) — Tổng quan quy trình 7 khâu, 2 cổng duyệt.
3. [`output_styles/`](output_styles/) — Giọng văn thương hiệu chuẩn theo từng kênh.

---

## 3. Quy Trình 7 Khâu & 2 Cổng Duyệt

```
① new ─→ ② plan ─🔒cổng 1─→ ③ produce ─→ ④ selfqa ─🔒cổng 2─→ ⑤ render ─→ ⑥ publish ─→ ⑦ measure
         Content              content.md      quality_check      audio/video    Post.publish_*   actual_*
         (proposed)           + Post rows      (MÁY tự kiểm)                                     + báo cáo .md
```

| Cổng Duyệt | Điều Kiện Kích Hoạt | Khâu Được Phép Mở |
|---|---|---|
| **Cổng 1 — Duyệt Content** | `Content.status = approved` **và** có ngày `approved_date` | ③ produce |
| **Cổng 2 — Duyệt Post** | `Post.review_status = approved` | ⑤ render, ⑥ publish |

- **Quy tắc tạo chiến dịch mới:** Luôn sử dụng lệnh copy từ template (`templates/CAMPAIGN_TEMPLATE.xlsx` và `templates/CAMPAIGN_TEMPLATE.md`), **tuyệt đối không tự dựng lại từ đầu**.

---

## 4. Bảy Điều Tuyệt Đối Cần Tuân Thủ

1. **Không duyệt hộ:** Không bao giờ tự đặt `Content.status = approved`, `approved_date` hoặc `Post.review_status = approved`.
2. **Không xuất bản chui:** Không đăng thật khi chưa đủ token, chưa qua Cổng 2, hoặc chưa có lệnh phê duyệt.
3. **Không bịa đặt số liệu:** Số liệu chưa xác minh phải gắn tag `[KIỂM CHỨNG]` hoặc để trống.
4. **Không điền số 0 giả:** Ô rỗng là một giá trị có nghĩa, không điền `0` thay cho dữ liệu chưa có.
5. **Không lộ hạ tầng:** Không để lộ tên công cụ nội bộ (Prompt, Engine, Tool names) trong nội dung gửi khán giả.
6. **Tái định dạng theo kênh:** Cùng một ý tưởng phải format lại chuẩn bản địa của từng kênh, không copy paste nguyên văn.
7. **Báo cáo minh bạch:** Báo cáo rõ ràng các ô và dòng đã thay đổi sau mỗi lượt xử lý.