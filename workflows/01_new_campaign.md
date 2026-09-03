# Khâu ①: Khởi Tạo Chiến Dịch (New Campaign)

| Thuộc tính | Chi tiết |
|---|---|
| **Vai trò chính** | `campaign-strategist` (hỗ trợ bởi `marketing-director`) |
| **Đầu vào (Input)** | Đề bài/Brief từ con người + Cấu hình instance |
| **Công cụ (Tools)** | `openpyxl` / `shutil.copy2` |
| **Đầu ra (Output)** | Thư mục chiến dịch + Hồ sơ `<NN_Ten>.md` + Workbook `<NN_Ten>.xlsx` với `Campaign.status = active` |

---

## 1. Trình Tự Thực Thi

1. **Thu thập thông tin:** Tiếp nhận đề bài. Nếu còn thiếu ngân sách, mục tiêu, kênh hoặc đối tượng, hỏi lại con người 1 lượt rõ ràng.
2. **Khởi tạo bằng SCRIPT — không làm tay:**
   ```
   python scripts/workbook/new_campaign.py --code <NN_Ten> [--meta campaign_meta.json] [--instance <ten>]
   ```
   Script làm trọn: dựng thư mục + `assets/`, `shutil.copy2` cả hai template, dọn dữ liệu
   mẫu ở `Content`/`Post`, đổ sheet `Campaign`, đặt `status = active` và `created` = hôm nay.
   Thêm `--dry-run` để xem đích trước khi ghi.

   **TUYỆT ĐỐI KHÔNG DỰNG LẠI WORKBOOK TỪ ĐẦU.** Script copy template rồi mới sửa giá trị ô.
   Dựng mới bằng `openpyxl.Workbook()` sẽ mất sạch màu, độ rộng cột, freeze pane — tức mất
   đúng phần làm file này đọc được bằng mắt người. Template là hợp đồng HÌNH THỨC, không chỉ
   là danh sách cột. (`scripts/workbook/build_workbook.py` làm ngược lại và đã bị thay.)

3. **Chiến dịch sống ở STATION, KHÔNG ở repo.** Script tự phân giải, dừng ở cái đầu tiên thấy:
   `--station` → thư mục làm việc hiện tại nếu có `.marketing-studio/` hoặc `instance.yml`
   → biến `MARKETING_STUDIO_DATA` → `~/.marketing`.
   Nghĩa là làm việc trong folder dự án riêng thì asset sinh THẲNG vào đó. `content/` trong repo
   chỉ chứa **fixture mẫu**, không chứa chiến dịch thật.

4. **Điền nốt sheet Campaign:** script cảnh báo rõ trường nào còn trống. Điền đủ 26 trường
   (định nghĩa tại [`../knowledge/data_model/DATA_MODEL.md`](../knowledge/data_model/DATA_MODEL.md))
   trước khi sang khâu ②.

   ⚠️ `campaign_code` **luôn** lấy từ `--code`, meta không đè được — ô trong sheet phải khớp
   tên thư mục và tên file, lệch là mọi tra cứu theo mã đều trượt.

## 2. Tiêu Chuẩn Nghiệm Thu (Acceptance Criteria)
- [ ] Workbook mở được bình thường, giữ nguyên 4 sheet (`Campaign`, `Content`, `Post`, `_Legend`), giữ nguyên màu và độ rộng cột.
- [ ] Hồ sơ `.md` có đầy đủ thông tin bối cảnh, persona, và danh sách những điều KHÔNG làm (Mục 4).
- [ ] Chuyển tiếp sang [Khâu ② (Plan)](02_plan_content.md).