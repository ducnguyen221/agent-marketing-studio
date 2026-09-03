# Khâu ⑦: Đo Lường & Báo Cáo (Measure & Analytics)

| Thuộc tính | Chi tiết |
|---|---|
| **Vai trò chính** | `growth-analyst` |
| **Đầu vào (Input)** | Dòng `Post` có `publish_status = published` |
| **Công cụ (Tools)** | Platform Analytics APIs, `openpyxl` |
| **Đầu ra (Output)** | Số liệu điền vào các cột `actual_*` + Báo cáo append vào Mục 9 hồ sơ `.md` |

---

## 1. Trình Tự Thực Thi

1. **Thu Thập Số Liệu Thật:** Thu thập `actual_view`, `actual_interaction`, `actual_lead`, `actual_conversion`.
2. **Ghi Đè Vào Sheet Post:** Cập nhật các cột `actual_*` và cập nhật `metric_updated_at = YYYY-MM-DD HH:MM`.
3. **Lưu Trữ Lịch Sử Vào Hồ Sơ `.md` (BẮT BUỘC):**
   > ⚠️ **Vì các cột `actual_*` trong Excel bị GHI ĐÈ nên để theo dõi diễn biến D+1, D+7, D+30, Agent BẮT BUỘC phải append số liệu vào Mục 9 của hồ sơ `<NN_Ten>.md`.**
4. **Đóng Chiến Dịch:** Khi đạt mốc thời gian kết thúc hoặc đạt KPI, chuyển `post_status = completed`.