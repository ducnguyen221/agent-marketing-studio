# Khâu ⑦: Đo Lường & Báo Cáo (Measure & Analytics)

| Thuộc tính | Chi tiết |
|---|---|
| **Vai trò chính** | `growth-analyst` |
| **Đầu vào (Input)** | `publish.json → posts[]` có `publish.status = published` |
| **Công cụ (Tools)** | Analytics của từng nền tảng (đọc bằng tay) · `register_publish.py metrics` |
| **Đầu ra (Output)** | Số liệu trong `posts[].actual` + báo cáo append vào Mục 9 của `campaign.md` |

---

## 1. Trình Tự Thực Thi

1. **Thu số liệu thật.** Mở Analytics của từng kênh, lấy số tại một mốc rõ ràng (D+1, D+7,
   D+30). **Thu tự động qua API chưa có** — hiện nhập tay. Đừng ghi một con số mà không biết
   nó chốt tại thời điểm nào.

2. **Ghi vào `publish.json`:**
   ```
   python scripts/pipeline/register_publish.py <thư mục bài> metrics --post fb \
       --reach 1840 --reaction 37 --comment 6 --share 4
   ```
   Ghi vào `posts[].actual` và đặt `actual.updated_at`.

3. **CHỐT SỐ VÀO `campaign.md` MỤC 9 — BẮT BUỘC.**
   > ⚠️ `posts[].actual` **ghi đè**, không giữ lịch sử. Muốn so D+1 với D+30 thì Mục 9 là nơi
   > **duy nhất** giữ được diễn biến. Append một mục `### Báo cáo YYYY-MM-DD` mỗi lần chạy,
   > **không xoá mục cũ**, và ghi rõ số chốt tại thời điểm nào.

4. **Đối chiếu `target`.** So `posts[].actual` với `posts[].target`. Chưa đủ mẫu để kết luận
   thì viết **"chưa đủ mẫu"** — đừng đưa ra một con số đoán. Baseline là median của các bài
   gần nhất cùng định dạng **trên chính kênh này**, không phải "chuẩn ngành" đọc ở đâu đó.

5. **Xuất bản báo cáo** (tuỳ nhu cầu):
   ```
   python scripts/pipeline/build_views.py  --station <trạm>   # campaign.html + index.html
   python scripts/pipeline/export_excel.py --station <trạm>   # .xlsx cho người không dùng git
   ```

6. **Đóng chiến dịch.** Đạt mốc thời gian hoặc đạt KPI → `status = done`, rồi điền Mục 10
   (Retro) của `campaign.md`.
