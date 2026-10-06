# IMAGE_GUIDELINES — Quy chuẩn thiết kế Ảnh (Cover Page & Infographic)

> **Mục tiêu:** Tài liệu quy chuẩn kỹ thuật và thị giác cho toàn bộ hình ảnh sản xuất trong studio:
> 1. **Cover Page (Ảnh bìa 16:9):** Dùng làm cover bài viết blog, thumbnail chia sẻ mạng xã hội.
> 2. **Infographic (Ảnh tóm tắt nội dung):** Người xem nắm trọn thông điệp cốt lõi trong **5 giây** mà không cần đọc hết bài.
>
> Chuẩn hóa theo tiêu chuẩn nhận diện thương hiệu, tối giản hóa văn bản để triệt tiêu lỗi vỡ dấu tiếng Việt của AI, và đa dạng hóa bố cục theo chủ đề.

---

## 1. Điều phối Model AI (AI Engine Routing)

Khi tạo ý tưởng thị giác, lập dàn ý hình ảnh và viết prompt sinh ảnh:

1. **Ưu tiên số 1 (Default): Gemini (`agy`).**
   - Gemini là engine mặc định có khả năng tư duy không gian (spatial reasoning) và hiểu ngữ cảnh văn hóa/tiếng Việt tốt nhất.
   - Luôn sử dụng Gemini để phân tích nội dung bài viết, chọn archetype bố cục và soạn thảo khối prompt sinh ảnh.
2. **Dự phòng (Fallback): OpenAI Codex (`codex`).**
   - Khi Gemini hết quota sử dụng (Graph API / CLI trả mã lỗi `4` hoặc `Quota Exhausted` / HTTP 429), pipeline và agent tự động chuyển sang gọi Codex qua cầu A2A (`CODEX_BRIDGE`).
   - Lời dặn Codex: Giữ nguyên prompt cấu trúc và tuân thủ chặt chẽ danh sách chuỗi chữ tiếng Việt đã khóa.

---

## 2. Quy tắc thiết kế Cover Page (Ảnh bìa bài viết 16:9)

Ảnh bìa đại diện cho toàn bộ bài viết trên blog (Atlas) và card preview khi chia sẻ link:

### 2.1 Thông số kỹ thuật
- **Tỷ lệ & Kích thước:** 16:9 — chuẩn **1920×1080 px** (hoặc tối thiểu 1280×720 px).
- **Vùng an toàn (Safe Zone):** Hình chữ nhật trung tâm **1200×630 px**. Toàn bộ tiêu đề chính, logo và chủ thể minh họa quan trọng PHẢI nằm gọn trong vùng an toàn để không bị cắt xén khi Facebook/LinkedIn crop ảnh dạng link preview 1.91:1 hoặc xem trên mobile.
- **Định dạng file:** PNG (chất lượng cao) hoặc JPG (nén tối ưu cho web).

### 2.2 Bố cục & Nhận diện
```
┌────────────────────────────────────────────────────────┐
│  [LOGO THƯƠNG HIỆU]                                    │
│  (Góc trên trái / padding 60px)                        │
│                                                        │
│   TIÊU ĐỀ BÀI VIẾT                                     │
│   (Tối đa 2 dòng, font sans-serif lớn)                 │
│                                                        │
│   Phụ đề / Tagline ngắn                                │
│   (Pill màu nhấn hoặc 1 dòng tóm tắt)                  │
│                                                        │
│                     [HÌNH MINH HỌA 3D CHỦ ĐẠO]         │
│                     (Bên phải hoặc chính giữa)         │
│                                                        │
│  ────────────────────────────────────────────────────  │
│  Thanh chân trang / Tên tác giả                        │
└────────────────────────────────────────────────────────┘
```
- **Logo:** Đặt tại góc trên bên trái bên trong vùng an toàn (safe-zone) hoặc thanh chân trang; dùng asset logo chính thức có nền trong suốt.
- **Tiêu đề:** Tối đa 2 dòng, font sans-serif hình học hiện đại (Montserrat, Inter, Be Vietnam Pro), độ tương phản cao so với nền (trắng trên nền tối, hoặc navy/đen trên nền sáng).
- **Minh họa chủ đạo:** Hình minh họa 3D Isometric hiện đại, màu sắc gradient tươi sáng theo brand palette. Không dùng ảnh chụp người thật cắt ghép lộn xộn.

---

## 3. Quy tắc thiết kế Infographic & Tối giản chữ

### 3.1 Nguyên tắc tối giản chữ (Text Minimization Rule)
> **Bài học xương máu:** Model sinh ảnh (ImageGen / DALL-E / Imagen) **rất dễ vỡ dấu tiếng Việt** khi phải vẽ các đoạn văn bản dài (`Cloud deploymenh`, `Thư cọc diectory`).
> **Quy tắc vàng:** *"Tối đa hóa hình khối và số liệu — Tối thiểu hóa câu chữ"*.

1. **Số từ tối đa:**
   - Tiêu đề chính / Tiêu đề thẻ: **3–5 từ** (ví dụ: `01. Thu thập dữ liệu`, `Tối ưu hóa chi phí`).
   - Diễn giải ngắn gọn đi kèm: **≤ 10 từ** (ví dụ: `Tự động hóa pipeline qua Cloud Run hàng ngày`). Tuyệt đối không nhồi nhét đoạn văn dài vào ảnh; chia thành nhiều ảnh/carousel nếu cần diễn giải sâu.
2. **Ưu tiên số liệu có so sánh:** Số liệu giúp ảnh có chiều sâu và khoa học (ví dụ: `40 phút thay vì 75 phút` mạnh hơn `Nhanh hơn 47%`).
3. **Cấm tuyệt đối chữ rác bên trong hình vẽ minh họa:** Khi vẽ màn hình laptop, dashboard hay sơ đồ, yêu cầu model chỉ vẽ các vạch ngang/khối placeholder trừu tượng, KHÔNG cố vẽ text giả lập vì model sẽ tự bịa ra ký tự vô nghĩa.
4. **Khóa cứng danh sách chuỗi chữ:** Từng chuỗi chữ xuất hiện trên ảnh phải được viết sẵn trong prompt, đúng dấu 100%, yêu cầu AI chép nguyên văn.

---

## 4. Ma trận tư vấn & 5 Archetype Bố cục Infographic

Không gò bó infographic vào một khuôn mẫu duy nhất. Tùy thuộc vào chủ đề bài viết, hãy tham khảo ma trận sau để chọn layout tối ưu:

| Archetype Bố cục | Khi nào nên chọn (Chủ đề phù hợp) | Cấu trúc thị giác |
|---|---|---|
| **A. Z-Layout Tổng hợp (Overview Grid)** | Bài tổng kết, tin tức tuần, phân tích đa chiều nhiều khía cạnh độc lập | 5 vùng đọc theo chữ Z: Tiêu đề trên ➔ Cột trái 3 thẻ ➔ Minh họa giữa ➔ Cột phải 3 thẻ ➔ Dải dưới |
| **B. Linear Process (Quy trình tuyến tính)** | Bài hướng dẫn từng bước (Tutorial), lộ trình phát triển (Roadmap), luồng dữ liệu (Data Pipeline) | Trục ngang hoặc dọc: 4–6 khối bước nối tiếp nhau bằng mũi tên điều hướng (`B1 ➔ B2 ➔ B3 ➔ B4`) |
| **C. Circular Loop (Vòng lặp chu trình)** | Chu trình khép kín, Sprint Agile, vòng đời dữ liệu/sản phẩm (Lifecycle), Feedback flywheel | Vòng tròn 3–5 chặng quay quanh một lõi giá trị trung tâm với các mũi tên xoay chiều |
| **D. Comparison / Versus (So sánh đối đầu)** | Đánh giá công nghệ (Tool A vs Tool B), Before & After, Cách làm cũ vs Cách làm mới | Chia đôi khung hình dạng 2 cột đối xứng với bảng màu tương phản (ví dụ: Đỏ/Xám vs Xanh) |
| **E. Hierarchical Stack (Phân tầng kiến trúc)** | Kiến trúc phần mềm, Tech Stack, kiến trúc nền tảng dữ liệu (Data Platform) | Xếp chồng từ đáy lên đỉnh: Tầng 1 Hạ tầng ➔ Tầng 2 Xử lý/Lưu trữ ➔ Tầng 3 Ứng dụng/Báo cáo |

---

## 5. Chi tiết 5 Archetype Bố cục

### Archetype A: Z-Layout Tổng hợp (5 vùng)
```
┌────────────────────────────────────────────────────────┐
│  ① TIÊU ĐỀ LỚN + Pill phụ đề + Dòng bối cảnh           │
├─────────────┬────────────────────────────┬─────────────┤
│ ② 3 THẺ DỌC │    ③ MINH HỌA TRUNG TÂM    │ ④ 3 THẺ DỌC │
│   Đánh số   │   Người làm việc + thiết bị│   Đánh số   │
│    1-2-3    │      + Luồng trừu tượng    │    4-5-6    │
├─────────────┴────────────────────────────┴─────────────┤
│  ⑤ DẢI DƯỚI: Luồng hành động hoặc 3 ô lưu ý quan trọng │
├────────────────────────────────────────────────────────┤
│                  THANH THƯƠNG HIỆU                     │
└────────────────────────────────────────────────────────┘
```

### Archetype B: Linear Process (Quy trình 4–5 bước)
```
┌────────────────────────────────────────────────────────┐
│  TIÊU ĐỀ QUY TRÌNH: [TÊN QUY TRÌNH / PIPELINE]         │
│  Phụ đề: 4 bước triển khai tinh gọn từ ý tưởng đến thực tế│
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐      │
│  │ BƯỚC 01  │  ──> │ BƯỚC 02  │  ──> │ BƯỚC 03  │  ... │
│  │ Icon +   │      │ Icon +   │      │ Icon +   │      │
│  │ Tên bước │      │ Tên bước │      │ Tên bước │      │
│  │ Mô tả ≤10│      │ Mô tả ≤10│      │ Mô tả ≤10│      │
│  └──────────┘      └──────────┘      └──────────┘      │
│                                                        │
├────────────────────────────────────────────────────────┤
│  KẾT QUẢ ĐẦU RA / THƯƠNG HIỆU                          │
└────────────────────────────────────────────────────────┘
```

### Archetype C: Circular Loop (Vòng lặp chu trình)
```
┌────────────────────────────────────────────────────────┐
│  TIÊU ĐỀ CHU TRÌNH: [VÒNG LẶP / VÒNG ĐỜI DỮ LIỆU]      │
├────────────────────────────────────────────────────────┤
│                     [ CHẶNG 1 ]                        │
│                     Lập kế hoạch                       │
│                         ▲    │                         │
│                         │    ▼                         │
│          [ CHẶNG 4 ]  [ LÕI ]  [ CHẶNG 2 ]             │
│          Đo lường     TRUNG TÂM Thực thi               │
│                         ▲    │                         │
│                         │    ▼                         │
│                     [ CHẶNG 3 ]                        │
│                     Tối ưu hóa                         │
├────────────────────────────────────────────────────────┤
│  THANH THƯƠNG HIỆU                                     │
└────────────────────────────────────────────────────────┘
```

### Archetype D: Comparison / Versus (So sánh đối đầu)
```
┌────────────────────────────────────────────────────────┐
│  TIÊU ĐỀ SO SÁNH: [CÁCH CŨ VS CÁCH MỚI / TOOL A VS B]  │
├──────────────────────────┬─────────────────────────────┤
│  CỘT TRÁI (TRUYỀN THỐNG) │  CỘT PHẢI (HIỆN ĐẠI / TỐI ƯU│
│  - Thủ công, tốn 8h      │  - Tự động hóa qua Agent    │
│  - Dễ sai sót dữ liệu    │  - Bắt lỗi theo thời gian thực│
│  - Khó mở rộng quy mô    │  - Tăng tốc x5 lần hiệu suất│
├──────────────────────────┴─────────────────────────────┤
│  LỜI KHUYÊN / KẾT LUẬN TỔNG QUAN                       │
└────────────────────────────────────────────────────────┘
```

### Archetype E: Hierarchical Stack (Phân tầng kiến trúc)
```
┌────────────────────────────────────────────────────────┐
│  TIÊU ĐỀ KIẾN TRÚC: [TECH STACK / HỆ THỐNG PHÂN TẦNG]   │
├────────────────────────────────────────────────────────┤
│  TẦNG 3: ỨNG DỤNG & GIAO DIỆN (Dashboard, API, Mobile)  │
├────────────────────────────────────────────────────────┤
│  TẦNG 2: XỬ LÝ & TÍNH TOÁN (Cloud Run, Semantic Model) │
├────────────────────────────────────────────────────────┤
│  TẦNG 1: DỮ LIỆU & HẠ TẦNG (PostgreSQL, Data Lakehouse)│
├────────────────────────────────────────────────────────┤
│  THANH THƯƠNG HIỆU                                     │
└────────────────────────────────────────────────────────┘
```

---

## 6. Khung Prompt mẫu chuẩn

### 6.1 Prompt mẫu Cover Page 16:9
```
Nhiệm vụ: Sinh MỘT ảnh bìa bài viết công nghệ hiện đại, khổ ngang 1920x1080 (16:9).
QUAN TRỌNG: Chỉ dùng các chuỗi chữ tiếng Việt được cung cấp dưới đây, đúng dấu tuyệt đối.

PHONG CÁCH:
- Nền xanh navy đậm (#0F172A) kết hợp hiệu ứng ánh sáng gradient cyan/blue công nghệ hiện đại.
- Không gian 3D Isometric thoáng đãng, sang trọng, mang tính chuyên môn cao.
- Chủ thể minh họa: Biểu tượng công nghệ 3D (dữ liệu, mạng lưới agent, đám mây) nổi bật ở nửa bên phải.

CÁC CHUỖI VĂN BẢN (KHÓA NGUYÊN VĂN):
- Tiêu đề chính (lớn, căn trái, font sans-serif trắng): "{{TIÊU ĐỀ BÀI VIẾT}}"
- Pill phụ đề (nền xanh dương #2563EB, chữ trắng): "{{PHỤ ĐỀ HOẶC CHỦ ĐỀ}}"
- Chân trang (chữ nhỏ màu xám nhạt #94A3B8): "{{TÊN KÊNH / THƯƠNG HIỆU}}"

TUYỆT ĐỐI KHÔNG: Watermark, chữ tiếng Anh lung tung, hình ảnh người thật cắt ghép.
```

### 6.2 Prompt mẫu Infographic (Linear Process - Quy trình)
```
Nhiệm vụ: Sinh MỘT ảnh infographic quy trình công nghệ tiếng Việt, khổ ngang 1920x1080.
QUAN TRỌNG: Chữ tiếng Việt phải đúng dấu 100%. Không tự ý thêm chữ ngoài danh sách.

BỐ CỤC: Luồng tuyến tính từ trái sang phải gồm 4 bước nối nhau bằng mũi tên ánh sáng:
- Tiêu đề trên cùng (navy đậm, căn giữa): "{{TIÊU ĐỀ QUY TRÌNH}}"
- Bước 1: [Icon] "{{TÊN BƯỚC 1}}" — "{{MÔ TẢ NGẮN BƯỚC 1}}"
- Bước 2: [Icon] "{{TÊN BƯỚC 2}}" — "{{MÔ TẢ NGẮN BƯỚC 2}}"
- Bước 3: [Icon] "{{TÊN BƯỚC 3}}" — "{{MÔ TẢ NGẮN BƯỚC 3}}"
- Bước 4: [Icon] "{{TÊN BƯỚC 4}}" — "{{MÔ TẢ NGẮN BƯỚC 4}}"
- Chân trang: "{{THƯƠNG HIỆU}}"

PHONG CÁCH: Nền trắng ngả xanh (#F8FAFC), thẻ bo tròn đổ bóng mềm, viền mảnh cao cấp.
```

---

## 7. Cổng kiểm duyệt & Sidecar hồ sơ

1. **Soát dấu tiếng Việt:** Phóng to ≥ 2x và đọc từng vùng chữ trước khi duyệt đăng.
2. **Sidecar files:**
   - `facebook/infographic.prompt.txt` — Prompt gốc tách từ `content.md`.
   - `facebook/infographic.meta.json` — Ghi nhận thời gian tạo, model tạo, sha256 và kết quả soát chữ của người (`text_check`).
3. **Thư mục Reference Assets:** Xem các mẫu ảnh tham khảo và logo chuẩn tại `knowledge/` và `assets/`.
