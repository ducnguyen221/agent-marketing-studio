# Khâu ⑥: Xuất Bản & Hẹn Giờ Đa Kênh (Publish Distribution)

| Thuộc tính | Chi tiết |
|---|---|
| **Vai trò chính** | `distribution-manager` |
| **Đầu vào (Input)** | Dòng `Post` có `review_status = approved` VÀ `quality_check = passed` |
| **Công cụ (Tools)** | [`../knowledge/toolchains/PLATFORM_SETUP.md`](../knowledge/toolchains/PLATFORM_SETUP.md) |
| **Đầu ra (Output)** | Bài đăng đã xuất bản/hẹn giờ, cập nhật `publish_status`, `publish_link` |

---

## 1. Trình Tự Thực Thi

1. **Kiểm Tra Token & Quyền Hạn:** Đọc cấu hình token tại `.env`. Nếu thiếu token → dừng lại và báo cáo, không retry mù.
2. **Khung Giờ Đăng Bài:** Đăng/hẹn lịch theo đúng giờ vàng đã khai trong hồ sơ `.md` Mục 5.
3. **Cập Nhật Workbook:**
   - Cập nhật dòng `Post`: `publish_status = scheduled` hoặc `published`, `publish_link = <url>`, `post_status = published`.
   - Cập nhật dòng `Content`: `Content.status = published`, `published_date = <ngày post đầu tiên đăng>`.