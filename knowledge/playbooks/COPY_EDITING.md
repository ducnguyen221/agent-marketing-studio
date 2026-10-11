---
title: "Copy Editing Playbook"
doc: playbook
repo: agent-marketing-studio
version: "1.1.10"
---

# Sổ tay biên tập nội dung 7 lượt (7-Pass Copy Editing Playbook)

Đọc khi: cần biên tập, làm sắc nét và nâng cao chất lượng bản nháp bài viết (blog, mạng xã hội, email, landing copy) độc lập hoặc trong chiến dịch, đảm bảo giữ nguyên sự thật và giọng tác giả.

---

## 1. Nguyên tắc biên tập bất biến
1. **Giữ nguyên sự thật (Preserve Facts):** Tuyệt đối không thay đổi sự kiện, số liệu, tên người, kết quả hoặc điều khoản ưu đãi của tác giả.
2. **Tôn trọng giọng tác giả (Respect Voice):** Loại bỏ sáo rỗng và câu từ công thức của AI, nhưng giữ đúng phong cách cá nhân hoặc quy chuẩn giọng kênh (`brand.md`).
3. **Minh bạch thay đổi (Explain Edits):** Mọi chỉnh sửa lớn (đổi trật tự, cắt đoạn, đổi câu kết) phải đi kèm lý do ngắn gọn.
4. **Không tự quyết định thay đổi offer:** Nếu CTA hoặc gói dịch vụ trong bản nháp chưa rõ ràng, đưa ra phương án để người dùng chọn, không tự bịa đặt.

---

## 2. Quy trình biên tập 7 lượt (7-Pass Editing Framework)

### Lượt 1: Cấu trúc & Mạch lập luận (Structure & Flow)
- Kiểm tra bài viết có một thông điệp trung tâm duy nhất hay không.
- Đảm bảo trật tự chuyển đoạn hợp lý: Vấn đề → Phân tích nguyên nhân → Giải pháp / Bằng chứng → Hành động tiếp theo.
- Cắt bỏ các đoạn lan man, lạc đề hoặc lặp lại luận điểm đã trình bày.

### Lượt 2: Độ rõ ràng & Tinh gọn (Clarity & Conciseness)
- Cắt bỏ các từ ngữ sáo rỗng thường gặp của AI ("Trong kỷ nguyên số ngày nay", "bức tranh toàn cảnh", "đóng vai trò tối quan trọng", "không ngừng phát triển").
- Thay thế thể bị động nặng nề bằng thể chủ động trực diện.
- Rút ngắn các câu quá dài (>35 từ) thành 2 câu ngắn gọn, dễ hiểu.

### Lượt 3: Giọng tác giả & Kênh phát hành (Voice & Channel Fit)
- Đối chiếu với hướng dẫn phong cách của kênh (`brand.md`, `output_styles/`).
- Điều chỉnh đại từ xưng hô và mức độ trang trọng (thân mật cho mạng xã hội, chuyên nghiệp cho blog chuyên môn).
- Giữ các cách diễn đạt đặc trưng và đại từ tự nhiên của tác giả.

### Lượt 4: Bằng chứng & Tính cụ thể (Proof & Specificity)
- Thay thế các nhận định chung chung ("rất nhiều khách hàng", "tăng trưởng mạnh") bằng số liệu cụ thể hoặc dẫn chứng thực tế.
- Kiểm tra tính logic của các mối quan hệ nguyên nhân - kết quả.
- Gắn nhãn `[KIỂM CHỨNG]` cho mọi số liệu hoặc tuyên bố chưa có nguồn xác thực.

### Lượt 5: Lời kêu gọi hành động (Call to Action - CTA)
- Đảm bảo mỗi bài viết có đúng 1 hành động tiếp theo rõ ràng (không đưa ra 3-4 CTA xung đột nhau).
- CTA phải gắn liền với giá trị độc giả vừa nhận được trong bài (tải tài liệu, đọc tiếp, thảo luận, đăng ký).
- Lời văn CTA phải cụ thể, hướng về lợi ích người đọc thay vì khẩu hiệu kêu gọi chung chung.

### Lượt 6: Trình bày & Quét mắt (Formatting & Scannability)
- Sử dụng tiêu đề phụ (H2, H3), danh sách bullet points và in đậm từ khóa quan trọng để hỗ trợ người đọc lướt nhanh.
- Giữ độ dài mỗi đoạn văn dưới 3-4 câu trên nền tảng số.
- Đảm bảo độ tương phản thị giác giữa các khối ý chính.

### Lượt 7: Rà soát an toàn & Claim QA (Safety & Claim QA)
- Kiểm tra tuyệt đối không để lọt tên tool nội bộ, bí mật kỹ thuật hoặc PII.
- Tuân thủ quy định hashtag và giới hạn độ dài ký tự của từng kênh phát hành.
- Rà soát các cam kết pháp lý hoặc tuyên bố nhạy cảm.

---

## 3. Ranh giới giữa 2 chế độ
- **Chế độ Campaign:** Áp dụng khi bản nháp nằm trong một chiến dịch đã qua Gate 1. Sản xuất vào file `content.md`, liên kết anchor `## post:format` và chuẩn bị sang Gate 2.
- **Chế độ Standalone Edit:** Áp dụng khi người dùng gửi một đoạn nháp độc lập để biên tập. Trả về văn bản đã sửa + bảng ghi chú lý do sửa, không tạo thư mục bài viết hay thay đổi trạng thái hệ thống. Draft thuộc chiến dịch cấm dùng chế độ này để né cổng duyệt.
