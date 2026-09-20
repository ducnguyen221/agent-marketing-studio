---
scope: agent-marketing-studio engine
governance_version: 2.0
canonical: true
---

# AGENTS.md — Quy Chuẩn Quản Trị & Vận Hành Cho AI Agent

> **agent-marketing-studio** là hệ thống điều phối và thực thi chiến dịch marketing toàn diện kết hợp giữa con người và đa tác nhân AI Agent.
> **Quy ước nền tảng:** Mỗi chiến dịch = 1 thư mục + 1 file `campaign.md`; mỗi bài = 1 thư mục con.
> **Markdown quản lý trạng thái** (bảng Content giữa marker, và `publish.json` của từng bài);
> `.xlsx` chỉ là bản xuất một chiều. Con người kiểm soát 3 cổng duyệt.
>
> **Chiến dịch dài kỳ chạy TRONG PHIÊN là mặc định** — agent đi trọn đường ống, dừng ở
> mỗi cổng hỏi người ngay tại chỗ và kê đường dẫn file để người mở kiểm. Telegram là mặt
> tiền thứ hai của cùng kho cổng, dùng khi người không ngồi trước máy. Hợp đồng đầy đủ:
> [`knowledge/toolchains/IN_SESSION_PIPELINE.md`](knowledge/toolchains/IN_SESSION_PIPELINE.md).

---

## 1. Ranh Giới An Toàn & Quyền Hạn (Safety & Boundaries)

- **Pre-approved (Tự động thực thi):**
  - Đọc và phân tích hồ sơ chiến dịch, template, data model, output style.
  - Dự thảo nội dung, viết bài đa kênh vào file `<folder_path>/content.md`.
  - Đọc/ghi các trường trạng thái của Agent trong `publish.json` (`agent_status`, `quality_check`).
  - Chạy script kiểm tra QA nội bộ.
- **Scope Gate (Phải có con người xác nhận):**
  - Chuyển sang khâu ③ Produce (Cần Cổng 1: bảng Content `status = approved` **và** ô `g1` có ngày).
  - Chuyển sang khâu ⑤ Render và ⑥ Publish (Cần Cổng 2: `publish.json → posts[].review.status = approved`, kèm `approved_by` + câu duyệt nguyên văn).
  - Phát YouTube/Facebook sau khi web đã lên (Cần Cổng 3 — chỉ khi bảng Content có cột `g3`: ô `g3` có ngày).
  - Thay đổi cấu trúc bảng tính hoặc thêm trường dữ liệu mới vào Data Model.
- **Never (Tuyệt đối cấm):**
  - Tự ý đánh dấu đã duyệt ở bất kỳ cổng nào (1, 2 hoặc 3).
  - Ghi cổng mà không chép được NGUYÊN VĂN câu duyệt của người — `approval_gate.py` từ chối chạy.
  - Tự ý xuất bản (Publish) ra môi trường live khi chưa có lệnh tường minh.
  - Đọc, lưu trữ hoặc in ra các API token, private keys, thông tin cá nhân khách hàng (PII).
  - Điền `0` thay cho các ô chưa có dữ liệu (ô rỗng là một giá trị hợp lệ).

---

## 2. Bản Đồ Ngữ Cảnh & Thứ Tự Đọc (Context Navigation)

> 📍 **Tra cứu nhanh tại [MAP.md](MAP.md) trước khi thực hiện bất kỳ nhiệm vụ nào.** Agent tuyệt đối không đọc toàn bộ kho tri thức một lúc.

### Ba nguồn tài liệu cốt lõi:
1. [`knowledge/data_model/DATA_MODEL.md`](knowledge/data_model/DATA_MODEL.md) — Định nghĩa chi tiết 75 trường dữ liệu và ràng buộc.
2. [`workflows/00_WORKFLOW_INDEX.md`](workflows/00_WORKFLOW_INDEX.md) — Tổng quan quy trình 7 khâu, 3 cổng duyệt.
3. [`output_styles/`](output_styles/) — Giọng văn thương hiệu chuẩn theo từng kênh.

---

## 3. Quy Trình 7 Khâu & 3 Cổng Duyệt

```
① new ─→ ② plan ─🔒cổng 1─→ ③ produce ─→ ④ selfqa ─🔒cổng 2─→ ⑤ render ─→ ⑥ publish ─→ ⑦ measure
     bảng Content         content.md      24 cổng kiểm       audio/video    publish.json     actual_*
      (proposed)          + posts[]        (MÁY tự kiểm)                    + URL vào bảng   + báo cáo .md
                                                                  🔒cổng 3 nằm TRONG ⑥: web → cổng 3 → YouTube · Facebook
```

| Cổng Duyệt | Điều Kiện Kích Hoạt | Khâu Được Phép Mở |
|---|---|---|
| **Cổng 1 — Duyệt đề tài** | bảng Content: `status = approved` **và** có ngày ở ô `g1` | ③ produce |
| **Cổng 2 — Duyệt trước khi đăng** | `publish.json → posts[].review.status = approved`, kèm `approved_by` + câu duyệt nguyên văn | ⑤ render, ⑥ publish |
| **Cổng 3 — Duyệt bản thật trên web (tuỳ chọn)** | bảng Content có cột `g3` **và** ô `g3` có ngày — trang web lên trước, người xem bằng mắt | phát YouTube / Facebook (`release`) |

- **Quy tắc tạo mới:** luôn dùng script — `new_channel.py` → `new_campaign.py` → `new_post.py`
  (có `--bulk` để tạo cả loạt). Chúng copy từ `templates/` và ghi đúng chỗ.
  **Tuyệt đối không tự dựng thư mục bằng tay.**
- **`new_post.py` CHẶN** nếu `campaign.md` chưa điền đủ tám trường bắt buộc. Điền xong hãy tạo bài.
- **Trước khi viết một chữ, agent PHẢI đọc:** `campaign.md` của chiến dịch · `brand.md` của
  kênh · `research.md` của chính bài đó. Chi tiết ở `knowledge/toolchains/ATLAS_CHANNEL.md`.

---

## 4. Bảy Điều Tuyệt Đối Cần Tuân Thủ

1. **Không duyệt hộ:** Không bao giờ tự đặt `status = approved`, ô `g1`/`g3` trong bảng Content, hay `posts[].review.status = approved` trong `publish.json`.
2. **Không xuất bản chui:** Không đăng thật khi chưa đủ token, chưa qua cổng tương ứng (Cổng 2; Cổng 3 nếu chiến dịch có bật), hoặc chưa có lệnh phê duyệt.
3. **Không bịa đặt số liệu:** Số liệu chưa xác minh phải gắn tag `[KIỂM CHỨNG]` hoặc để trống.
4. **Không điền số 0 giả:** Ô rỗng là một giá trị có nghĩa, không điền `0` thay cho dữ liệu chưa có.
5. **Không lộ hạ tầng:** Không để lộ tên công cụ nội bộ (Prompt, Engine, Tool names) trong nội dung gửi khán giả.
6. **Tái định dạng theo kênh:** Cùng một ý tưởng phải format lại chuẩn bản địa của từng kênh, không copy paste nguyên văn.
7. **Báo cáo minh bạch:** Báo cáo rõ ràng các ô và dòng đã thay đổi sau mỗi lượt xử lý.