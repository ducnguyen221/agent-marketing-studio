# Thiết Kế Slide Carousel & Whiteboard Infographic (Carousel & Infographic Playbook)

Cẩm nang biên soạn kịch bản Slide Carousel đa trang và cấu trúc Prompt sinh ảnh Infographic dạng vẽ tay (Whiteboard Style) cho Gemini / AI Visual Generator.
Tham khảo kiến trúc thiết kế từ Charlie Hills (`charlie947/social-media-skills`, MIT). Viết mới hoàn toàn bằng tiếng Việt, thiết kế kết nối với `agent-slide-studio` và xưởng đồ họa của OpcOS.

---

## 1. Vai Trò Của Slide Carousel Trên Mạng Xã Hội

Slide Carousel (định dạng tài liệu PDF tải lên LinkedIn hoặc chuỗi ảnh vuốt ngang trên Facebook/Instagram) là một trong những định dạng có **tỷ lệ lưu bài (Save/Bookmark) và chia sẻ cao nhất** trên mạng xã hội hiện nay vì:
* **Hành vi vuốt (Swipe):** Kéo dài thời gian dừng của người dùng trên bài đăng (Dwell Time), gửi tín hiệu mạnh mẽ đến thuật toán phân phối.
* **Độ nén thông tin cao:** Người đọc tiếp nhận được một quy trình hoặc cẩm nang hoàn chỉnh mà không cần rời khỏi nền tảng.
* **Tỷ lệ khung hình tối ưu:** Chuẩn **4:5 (1080 × 1350 px)** chiếm trọn diện tích màn hình điện thoại di động theo chiều dọc, loại bỏ hoàn toàn các yếu tố gây xao nhãng khác trong bảng tin.

---

## 2. Cấu Trúc Kịch Bản Carousel Chuẩn 6–8 Slide

Một bộ Carousel chất lượng cao luôn tuân thủ cấu trúc tiến trình tâm lý sau:

```
┌─────────────┐   ┌─────────────┐   ┌───────────────────────────┐   ┌─────────────┐   ┌─────────────┐
│   SLIDE 1   │   │   SLIDE 2   │   │       SLIDE 3 – 5         │   │   SLIDE 6   │   │   SLIDE 7   │
│  HOOK BÌA   │──►│   BỐI CẢNH  │──►│    3 BƯỚC / GIẢI PHÁP     │──►│  CHECKLIST  │──►│    CTA      │
│(Pattern Stop│   │  & NỖI ĐAU  │   │     (Core Breakdown)      │   │   TỔNG KẾT  │   │ (Save/Follow│
└─────────────┘   └─────────────┘   └───────────────────────────┘   └─────────────┘   └─────────────┘
```

| Thứ tự Slide | Tên slide | Mục tiêu nội dung | Quy chuẩn chữ & Thiết kế |
|---|---|---|---|
| **Slide 1** | **Bìa Hook (The Cover)** | Khiến ngón tay người dùng dừng lại và bấm vuốt sang trang 2. | Tiêu đề lớn, dưới 10 từ. Có yếu tố đối lập hoặc con số cụ thể. Chữ chiếm 40% diện tích, có mũi tên gợi ý vuốt 👉. |
| **Slide 2** | **Ngữ cảnh (The Conflict)** | Nêu thực trạng hoặc sai lầm mà đa số đang gặp phải. | 1 câu khẳng định ngắn + 2 gạch đầu dòng biểu hiện. Tối đa 25 từ. |
| **Slide 3** | **Bước 1 / Luận điểm 1** | Trọng tâm của giải pháp đầu tiên. | Tiêu đề số to rõ + giải thích hành động cụ thể + 1 mẹo nhỏ (Pro-tip). |
| **Slide 4** | **Bước 2 / Luận điểm 2** | Trọng tâm của giải pháp thứ hai. | Đồng bộ font chữ và cấu trúc với Slide 3. Có biểu đồ/sơ đồ trực quan nếu có thể. |
| **Slide 5** | **Bước 3 / Luận điểm 3** | Trọng tâm của giải pháp thứ ba. | Hoàn thiện chuỗi giải pháp. Nhấn mạnh vào kết quả đạt được. |
| **Slide 6** | **Tóm tắt (The Cheat Sheet)** | Gom toàn bộ giá trị bài viết vào một trang duy nhất. | Bảng đối chiếu hoặc sơ đồ tóm lược. Đây là slide kích hoạt hành vi "Chụp màn hình" và "Lưu bài". |
| **Slide 7** | **Hành động (The Outro & CTA)** | Hướng dẫn người đọc bước tiếp theo. | Lời kêu gọi cụ thể: "Lưu lại bài viết để tra cứu khi cần", "Theo dõi [Tên] để nhận phân tích mới mỗi tuần". |

---

## 3. Mẫu Kịch Bản Carousel Hoàn Chỉnh (Text Brief)

### Chủ đề mẫu: "Quy trình 3 bước làm sạch dữ liệu trước khi dựng Dashboard"

```markdown
### SLIDE 1 (Bìa Hook):
- Tiêu đề lớn: 3 LỖI DỮ LIỆU KHIẾN BÁO CÁO CỦA BẠN BỊ SẾP BÁC BỎ
- Tiêu đề phụ: (Và checklist 5 phút để kiểm tra trước khi thuyết trình)
- Visual: Biểu đồ cột đỏ gãy khúc, dấu chấm than cảnh báo.

### SLIDE 2 (Ngữ cảnh):
- Tiêu đề: Bạn mất 2 ngày dựng dashboard đẹp mắt...
- Nội dung: Nhưng chỉ cần 1 con số bị lệch, toàn bộ uy tín phân tích sẽ biến mất.
- Thống kê: 70% lỗi số liệu bắt nguồn từ việc thiếu chuẩn hóa kiểu dữ liệu ở tầng nguồn.

### SLIDE 3 (Bước 1: Chuẩn hóa Schema):
- Tiêu đề: Bước 1: Khóa kiểu dữ liệu (Strict Typing)
- Hành động: Đừng để cột ngày tháng ở dạng chuỗi văn bản (Text).
- Cạm bẫy: Định dạng ngày tháng DD/MM và MM/DD bị đảo lộn âm thầm là nguyên nhân số 1 gây sai lệch doanh thu.

### SLIDE 4 (Bước 2: Xử lý giá trị Trống):
- Tiêu đề: Bước 2: Phân biệt rõ Null và Zero
- Hành động: Null nghĩa là "chưa có dữ liệu", Zero nghĩa là "giá trị bằng 0".
- Giải pháp: Gán giá trị mặc định có chủ đích, tránh để hàm tính trung bình (AVERAGE) bị méo kết quả.

### SLIDE 5 (Bước 3: Khử trùng lặp khóa chính):
- Tiêu đề: Bước 3: Rà soát tính duy nhất (Granularity Check)
- Hành động: Luôn kiểm tra khóa chính của bảng chiều (Dimension Table).
- Cảnh báo: Quan hệ Many-to-Many ngoài ý muốn sẽ nhân đôi số đo doanh thu của bạn.

### SLIDE 6 (Bảng tra cứu nhanh):
- Tiêu đề: CHECKLIST KIỂM TOÁN 5 PHÚT
- Bảng 3 dòng:
  * Cột Ngày tháng -> Chuẩn hóa kiểu Date ISO.
  * Cột Số đo -> Kiểm tra giá trị Null / Âm bất thường.
  * Khóa liên kết -> Xác minh quan hệ 1-to-Many.

### SLIDE 7 (Kêu gọi hành động):
- Tiêu đề: BẠN CÓ THẤY QUEN THUỘC KHÔNG?
- Lời kêu gọi:
  * 📌 Bấm Lưu bài viết để dùng lại checklist này trước kỳ báo cáo tới.
  * 💬 Chia sẻ lỗi dữ liệu trớ trêu nhất bạn từng gặp bên dưới phần bình luận!
```

---

## 4. Khuôn Prompt Sinh Ảnh Whiteboard Infographic Cho Gemini / AI Visual

Khi cần chuyển thể 1 bài phân tích thành 1 hình ảnh Infographic dạng sơ đồ bảng trắng vẽ tay (Whiteboard Drawing) để đăng kèm bài viết:

### Cấu trúc Prompt chuẩn:
```text
A professional hand-drawn whiteboard infographic about [CHỦ ĐỀ].
Style: Clean whiteboard drawing with black, deep blue, and accent amber markers. 
Minimalist diagrammatic layout, structured handwritten typography, high contrast, crisp lines.
Visual elements: 
- Central concept: [Ý TƯỞNG TRUNG TÂM] represented by a clear flow diagram / modular boxes.
- Three key steps: [BƯỚC 1], [BƯỚC 2], [BƯỚC 3] connected with directional sketched arrows.
- Comparison callout box: "[XANH: NÊN LÀM] vs [ĐỎ: NÊN TRÁNH]" highlighted with subtle marker hatching.
Background: Clean dry-erase white surface with subtle lighting.
No messy scribbles, no 3D corporate cartoon characters, no distorted pseudo-text. Highly legible layout suitable for LinkedIn professional feed.
Aspect ratio: 4:5 or 1:1.
```

### Nguyên tắc kiểm định ảnh sinh ra:
1. **Kiểm tra tính dễ đọc (Legibility):** Chữ trên hình phải đọc được rõ ràng khi hiển thị ở kích thước thu nhỏ 360px trên điện thoại.
2. **Không có "chữ ma" (AI gibberish text):** Nếu AI sinh các khối chữ vô nghĩa, yêu cầu bỏ khối chữ đó và thay bằng biểu tượng sơ đồ (schematic icon) sạch sẽ.
3. **Màu sắc tối giản:** Tối đa 3 màu mực (Đen chủ đạo + Xanh dương định hướng + Cam/Đỏ nhấn mạnh). Tránh hình vẽ sặc sỡ biến thành tranh biếm hoạ.
