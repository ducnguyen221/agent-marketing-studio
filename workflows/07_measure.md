# Khâu ⑦: Đo Lường & Báo Cáo (Measure & Analytics)

| Thuộc tính | Chi tiết |
|---|---|
| **Vai trò chính** | `growth-analyst` |
| **Đầu vào (Input)** | `publish.json → posts[]` có `publish.status = published` |
| **Công cụ (Tools)** | Analytics của từng nền tảng (đọc bằng tay) · `register_publish.py metrics` |
| **Đầu ra (Output)** | Số liệu trong `posts[].actual` + báo cáo append vào Mục 9 của `campaign.md` |

Định tuyến theo đầu ra: tracking/KPI plan trước publish là tư vấn/chuẩn bị; cập nhật số thực chỉ dành cho bài đã publish. Xem `.agents/roles/growth-analyst.md`; dùng trường chuẩn trong `DATA_MODEL.md`, không lấy tên cột bản xuất làm cấu trúc ghi.

---

## 1. Trình Tự Thực Thi

1. **Thu số liệu thật.** Mở Analytics của từng kênh, lấy số tại một mốc rõ ràng (D+1, D+7,
   D+30). **Thu tự động qua API chưa có** — hiện nhập tay. Đừng ghi một con số mà không biết
   nó chốt tại thời điểm nào. Nếu một chỉ số đã có giá trị nhưng không thể đo lại ở mốc này,
   dừng trước khi ghi snapshot mới; lệnh metrics chỉ cập nhật các chỉ số được truyền vào và giữ
   nguyên các chỉ số bỏ qua.

2. **Bảo toàn snapshot hiện tại trước khi ghi đè.** Đọc đúng `publish.json → posts[].actual`
   của post và `actual.updated_at`. Nếu có snapshot cũ chưa được chốt vào Mục 9, append đầy đủ
   các giá trị cùng thời điểm đó vào `campaign.md` Mục 9 trước; nếu snapshot chưa có số thì ghi
   rõ chưa có mốc đo, không thay bằng `0`. Không append trùng nếu đúng `actual.updated_at` đã
   được lưu trong báo cáo. Không xoá hay sửa các báo cáo cũ.

3. **Ghi snapshot mới vào `publish.json`:**
   Truyền lại mọi chỉ số đang có trong `actual` và đo được ở mốc mới; không bỏ một chỉ số cũ
   khỏi lệnh chỉ vì chưa đổi. Ví dụ dưới đây áp dụng khi các chỉ số nêu ra là toàn bộ số cần cập nhật:
   ```
   python scripts/pipeline/register_publish.py <thư mục bài> metrics --post fb \
       --reach 1840 --reaction 37 --comment 6 --share 4
   ```
   Ghi vào `posts[].actual` và đặt `actual.updated_at`.

4. **Đọc lại JSON để xác nhận**, rồi chốt snapshot mới vào `campaign.md` Mục 9. Xác nhận
   `posts[].actual` và `actual.updated_at` khớp lần đo vừa nhập; append một mục
   `### Báo cáo YYYY-MM-DD`, ghi rõ post, mốc D+1/D+7/D+30, thời điểm đo Analytics, nguồn và
   giá trị `actual.updated_at` để nhận diện mốc đã lưu. Đây là nơi giữ lịch sử; **không xoá mục
   cũ**. Nếu ghi JSON thành công nhưng chưa append được báo cáo,
   báo rõ Mục 9 cần hoàn tất và không tuyên bố lần đo đã lưu đủ.

5. **Đối chiếu `target`.** So `posts[].actual` với `posts[].target`. Chưa đủ mẫu để kết luận
   thì viết **"chưa đủ mẫu"** — đừng đưa ra một con số đoán. Nếu chọn baseline, nêu nhóm so sánh,
   cỡ mẫu và giới hạn; không trình median hay heuristic winner như chuẩn ngành hoặc bằng chứng nhân quả.

6. **Xuất bản báo cáo** (tuỳ nhu cầu):
   ```
   python scripts/pipeline/build_views.py  --station <trạm>   # campaign.html + index.html
   python scripts/pipeline/export_excel.py --station <trạm>   # .xlsx cho người không dùng git
   ```

7. **Đóng chiến dịch.** Đạt mốc thời gian hoặc đạt KPI → `status = done`, rồi điền Mục 10
   (Retro) của `campaign.md`.
