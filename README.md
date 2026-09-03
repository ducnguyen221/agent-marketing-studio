# agent-marketing-studio

Engine điều hành và tự động hóa chiến dịch marketing đa kênh toàn diện bằng **Multi-Agent AI kết hợp với con người kiểm soát (Human-in-the-Loop)**.

---

## 1. Điểm Khác Biệt & Kiến Trúc Cốt Lõi

- **Excel làm chủ trạng thái (Single Execution State):** Mỗi chiến dịch được quản trị bằng 1 workbook `.xlsx` chuẩn 4 sheet (`Campaign`, `Content`, `Post`, `_Legend`) và 1 hồ sơ chiến lược Markdown.
- **2 Cổng duyệt kiểm soát bởi con người:** AI tự động lập kế hoạch và sản xuất, nhưng con người giữ quyền quyết định ở 2 chốt chặn: duyệt ý tưởng (Cổng 1) và duyệt nội dung thành phẩm (Cổng 2).
- **Phân tách rạch ròi Engine & Instance:** Repository này chứa engine lõi (quản trị agent, quy trình, tri thức, template). Dữ liệu chiến dịch thực tế của từng doanh nghiệp được lưu trữ độc lập tại instance riêng và không đưa lên Git công khai.

---

## 2. Quy Trình 7 Khâu & 2 Cổng Duyệt

```
① new ─→ ② plan ─🔒 CỔNG 1 ─→ ③ produce ─→ ④ selfqa ─🔒 CỔNG 2 ─→ ⑤ render ─→ ⑥ publish ─→ ⑦ measure
```

1. **① new (Khởi tạo):** Lập hồ sơ chiến dịch từ brief của con người ([`workflows/01_new_campaign.md`](workflows/01_new_campaign.md)).
2. **② plan (Lập kế hoạch):** Đề xuất N ý tưởng content và từ khóa SEO ([`workflows/02_plan_content.md`](workflows/02_plan_content.md)).
   - 🔒 **CỔNG 1:** Người duyệt `Content.status = approved` + `approved_date`.
3. **③ produce (Sản xuất):** Viết bài chi tiết cho mọi kênh vào `content.md` và sinh dòng Post ([`workflows/03_produce_content.md`](workflows/03_produce_content.md)).
4. **④ selfqa (Tự kiểm tra):** Máy tự kiểm định chất lượng, văn phong, quy chuẩn kênh ([`workflows/04_self_qa.md`](workflows/04_self_qa.md)).
   - 🔒 **CỔNG 2:** Người duyệt `Post.review_status = approved`.
5. **⑤ render (Dựng Asset):** Tạo hình ảnh, audio lồng tiếng, short video ([`workflows/05_render_assets.md`](workflows/05_render_assets.md)).
6. **⑥ publish (Đăng bài):** Lên lịch và xuất bản đa kênh ([`workflows/06_publish.md`](workflows/06_publish.md)).
7. **⑦ measure (Đo lường):** Thu thập số liệu hiệu quả và chốt báo cáo ([`workflows/07_measure.md`](workflows/07_measure.md)).

---

## 3. Cấu Trúc Repository Chuẩn Hóa

```text
agent-marketing-studio/
├── AGENTS.md                  # Quy chuẩn quản trị đa tác nhân (Governance)
├── MAP.md                     # Bản đồ định tuyến context nhiệm vụ (Context Router)
├── README.md                  # Hướng dẫn tổng quan hệ thống
├── CONTRIBUTING.md            # Quy ước phát triển và đóng góp
├── SECURITY.md                # Chính sách bảo mật token và dữ liệu
├── .agents/                   # Tầng quản trị Agent (Roles, Skills, Checklists; hooks mới ở mức thiết kế)
├── scripts/                   # Mã Python xử lý workbook (một phần còn theo mô hình 5 sheet cũ — xem workflows/00)
├── schema/                    # Đặc tả workbook cũ (5 sheet), sắp archive — nguồn sự thật là knowledge/data_model
├── knowledge/                 # Kho tri thức marketing (Data Model, Playbooks, Toolchains)
├── output_styles/             # Giọng văn thương hiệu chuẩn theo từng kênh
├── templates/                 # Khuôn mẫu chuẩn (Workbook 4 sheet, Content template)
├── workflows/                 # Đặc tả chi tiết 7 khâu vận hành
└── content/                   # Dữ liệu instances (Instance mẫu: KPIM)
```

---

## 4. Tài Liệu Quan Trọng

- 📖 **Mô hình Dữ liệu 75 trường:** [`knowledge/data_model/DATA_MODEL.md`](knowledge/data_model/DATA_MODEL.md)
- 🗺️ **Bản đồ nhiệm vụ cho Agent:** [`MAP.md`](MAP.md)
- 🎯 **Quy trình tổng thể:** [`workflows/00_WORKFLOW_INDEX.md`](workflows/00_WORKFLOW_INDEX.md)
- ✍️ **Bộ quy chuẩn giọng văn:** [`output_styles/`](output_styles/)
- 🔍 **Chiến dịch mẫu tham khảo:** `content/KPIM/02_campaigns/01_Tobi_Posts/`
