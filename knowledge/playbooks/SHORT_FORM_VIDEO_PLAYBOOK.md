# Kịch Bản Video Ngắn Đa Kênh (Short-Form Video Scripting Playbook)

Cẩm nang biên soạn kịch bản video ngắn (Facebook Reels, YouTube Shorts, TikTok) từ ý tưởng cốt lõi và video tham khảo mẫu.
Tham khảo kiến trúc thiết kế từ Charlie Hills (`charlie947/social-media-skills`, MIT). Viết mới hoàn toàn bằng tiếng Việt, thiết kế tương thích trực tiếp với luồng âm thanh `agent-voice-studio` (OmniVoice TTS) và luồng đồ họa `agent-video-studio` (HyperFrames).

---

## 1. Bản Chất Của Video Ngắn (0–60 Giây)

Video ngắn không phải là video dài cắt ngắn lại. Người xem video ngắn có xu hướng lướt liên tục (infinite swipe) với ngưỡng kiên nhẫn cực thấp. Nếu nội dung không tạo được điểm gián đoạn thị giác và thính giác trong **3 giây đầu tiên**, video coi như thất bại hoàn toàn.

### Bốn giai đoạn vàng của kịch bản 45–60 giây:

```
┌─────────────────┬──────────────────┬───────────────────────────────┬─────────────────┐
│  00:00 – 00:03  │  00:03 – 00:15   │         00:15 – 00:45         │  00:45 – 00:60  │
│  GIÁN ĐOẠN 3S   │   NỖI ĐAU CỤ THỂ │       BẺ LÁI & GIẢI PHÁP      │  KÊU GỌI & LẶP  │
│(Pattern Interrupt)│(Relatable Problem)│    (Turnaround & Core Value)  │  (CTA & Loop)   │
└─────────────────┴──────────────────┴───────────────────────────────┴─────────────────┘
```

1. **Giai đoạn 1 (00:00 – 00:03) — Gián đoạn mẫu hình (Pattern Interrupt):**
   * *Nhiệm vụ:* Chặn ngón tay lướt.
   * *Cơ chế 3 lớp:* Lời thoại giấu danh từ ("Cái này đã cứu tôi 20 giờ mỗi tuần...") + Hành động thị giác bất ngờ trên màn hình + Tiêu đề chữ động (Kinetic Text) to, rõ ràng.
2. **Giai đoạn 2 (00:03 – 00:15) — Đặt vấn đề / Nỗi đau đồng cảm (Relatable Problem):**
   * *Nhiệm vụ:* Giữ chân người xem ở lại để tìm câu trả lời.
   * *Cơ chế:* Nêu tình huống trớ trêu hoặc sai lầm mà 90% người trong ngành đang gặp phải bằng ngôn ngữ đời thường.
3. **Giai đoạn 3 (00:15 – 00:45) — Bẻ lái nhận thức & Trao giá trị (The Turnaround):**
   * *Nhiệm vụ:* Mang lại khoảnh khắc "Aha!" — giải pháp bất ngờ nhưng hợp lý.
   * *Cơ chế:* Cung cấp 2–3 bước thực hiện dứt khoát hoặc 1 nguyên lý cốt lõi. Không lan man giải thích lý thuyết.
4. **Giai đoạn 4 (00:45 – 00:60) — Kêu gọi hành động & Thiết kế vòng lặp (CTA & Seamless Loop):**
   * *Nhiệm vụ:* Kéo tương tác hoặc tạo vòng lặp vô tận (Loop) giúp người xem xem lại lần 2 (tăng thuật toán đề xuất).
   * *Cơ chế:* Câu kết video nối nhịp trực tiếp với câu mở đầu video, hoặc kêu gọi hành động bình luận nhận tài liệu ("Để lại comment 'AGENT', tôi gửi bạn checklist chi tiết").

---

## 2. Bóc Tách Cấu Trúc Video Tham Khảo (Reverse-Engineering Viral Reels)

Khi phân tích một video ngắn thành công trên mạng để học hỏi:
* **TUYỆT ĐỐI KHÔNG:** Chép lại lời thoại hoặc ăn cắp kịch bản nguyên văn.
* **CÁCH LÀM ĐÚNG:** Bóc tách khung xương cơ học (Skeleton Extraction) rồi điền thịt da bằng kiến thức, số liệu và giọng nói thật của tác giả:

| Yếu tố cơ học | Câu hỏi bóc tách | Cách chuyển thể sang nội dung OpcOS |
|---|---|---|
| **Cơ chế Hook** | Video mẫu dùng câu hỏi, số liệu gây sốc, hay hành động kỳ lạ? | Thay thế bằng số đo thật từ bài toán nội bộ (vd: thời gian deploy, số lỗi DAX). |
| **Nhịp cắt (Pacing)** | Bao nhiêu giây đổi khung hình/chữ một lần? | Chuẩn bị các thẻ đồ họa (graphic cards) trong HyperFrames xuất hiện mỗi 2.5–3.5 giây. |
| **Góc nhìn lật ngược** | Điểm mấu chốt khiến video hấp dẫn là gì? | Dùng bài học thực tế từ dự án khách hàng của KPIM / OpcOS. |

---

## 3. Mẫu Kịch Bản Chuẩn 3 Cột (3-Column Production Script)

Kịch bản phải được định dạng theo bảng 3 cột để sẵn sàng chuyển giao cho hai xưởng tự động hoá:
* **Cột Thoại:** Cung cấp cho `agent-voice-studio` (bộ máy OmniVoice TTS tổng hợp âm thanh giọng nói).
* **Cột Hình ảnh & Chữ:** Cung cấp cho `agent-video-studio` (bộ máy HyperFrames render video và phụ đề động).

### Ví dụ kịch bản hoàn chỉnh (Chủ đề: Tối ưu dữ liệu Power BI):

| Thời gian | Thoại (Chuẩn ngữ điệu OmniVoice TTS) | Hình ảnh & Chữ hiển thị (HyperFrames) |
|---|---|---|
| **00:00 – 00:03** | Đừng bao giờ viết measure kiểu này nếu không muốn báo cáo chạy mất hai phút. | *Cận cảnh:* Màn hình loading xoay tròn đỏ rực. **Chữ lớn:** "LỖI NÀY LÀM CHẬM BÁO CÁO 2 PHÚT". |
| **00:03 – 00:14** | Đa số các bạn mới học thường dùng hàm CALCULATE lồng bên trong hàm FILTER trên một bảng dữ liệu một triệu dòng. Máy tính sẽ phải quét toàn bộ bảng đó hàng nghìn lần. | *Đồ họa:* Đoạn mã DAX bị gạch chéo đỏ. Biểu đồ thanh CPU nhảy vọt lên 100%. |
| **00:14 – 00:30** | Cách đúng ở đây là: Hãy dùng bảng chiều đã lọc từ trước, hoặc đẩy thẳng logic tính toán về tầng SQL lúc nạp dữ liệu. Giữ DAX chỉ làm đúng một việc: tổng hợp số đo. | *Chuyển cảnh:* Mã DAX tối ưu xuất hiện viền xanh lá. Đồ họa Star Schema nối mũi tên mượt mà. |
| **00:30 – 00:45** | Thay đổi nhỏ này vừa giúp giảm tám mươi phần trăm dung lượng RAM, vừa giúp báo cáo mở lên tức thì khi sếp bấm chuột. | *Đồ họa:* Đồng hồ đếm ngược từ 120 giây rơi xuống 0.5 giây. Chữ nổi bật: "GIẢM 80% RAM". |
| **00:45 – 00:55** | Tôi đã gom toàn bộ danh sách bảy lỗi DAX phổ biến nhất vào một trang tài liệu tra cứu nhanh. Bình luận từ khóa BÁO CÁO bên dưới để nhận ngay nhé! | *Góc máy:* Tác giả chỉ tay xuống phần bình luận. Thẻ mockup tài liệu PDF hiện ra kèm mũi tên. |

---

## 4. Quy Chuẩn Viết Lời Thoại Cho Máy Lồng Tiếng (TTS Rules)

Khi viết lời thoại cho `agent-voice-studio` (OmniVoice TTS):
1. **Viết chữ đầy đủ cho số và ký hiệu:** Viết "hai phút" (không viết "2p"), "tám mươi phần trăm" (không viết "80%"), "hai mươi mốt tháng mười" (không viết "21/10").
2. **Phiên âm từ chuyên ngành mượt mà:** Các từ tiếng Anh quen thuộc viết chuẩn hoa thường rõ ràng; từ phát âm lạ kèm chú thích ngữ điệu.
3. **Dấu ngắt nhịp:** Dùng dấu phẩy (`,`) cho nhịp nghỉ ngắn 0.3s; dùng dấu chấm (`.`) hoặc gạch nối dài (`—`) cho nhịp ngắt 0.6s để tạo điểm nhấn tư duy.
4. **Độ dài câu:** Câu thoại không dài quá 18 từ để tránh tình trạng máy đọc bị hụt hơi hoặc dồn chữ.
