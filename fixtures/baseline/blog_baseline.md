# Baseline — số đo thật của 3 bài blog đã xuất bản

> **Đây là MỐC ĐỐI CHỨNG, không phải luật.** Luật nằm ở `output_styles/`, `.agents/checklists/`
> và `scripts/pipeline/blog_gates.py`. File này trả lời một câu hỏi khác:
> *"khi con người thật viết bài thật, các con số rơi vào đâu?"*
>
> Vì sao cần: ngưỡng đặt bằng cảm giác thì hoặc quá lỏng (không bắt được gì) hoặc quá chặt
> (bài đạt chuẩn vẫn đỏ → người tắt cổng, và từ đó cổng thành đồ trang trí). Mọi ngưỡng
> trong `blog_gates.py` đều truy được về một dòng trong bảng dưới.
>
> Ba bài gọi là SAMPLE-001/002/003, viết cùng một tác giả, cùng một kênh, trong 14 giờ.
> Đã lược tên tổ chức và URL thật — con số giữ nguyên.

## 1. Bảng đo

| Chỉ số | S-001 | S-002 | S-003 | Ngưỡng lúc đó | Thực tế đạt |
|---|---:|---:|---:|---|---|
| `blog.md` — số từ | **2.126** | 3.800 | 3.580 | 2.500–4.000 | 2/3 |
| `blog.md` — ký tự | 9.423 | 17.265 | 16.920 | — | — |
| H1 / H2 / H3 | 1/8/0 | 1/11/0 | 1/9/0 | 6–12 H2 | 2/3 · **H3 chưa dùng bao giờ** |
| Bảng markdown | 3 | 3 | 3 | ≥1 | 3/3 ✅ |
| Callout `> <emoji>` | 4 | **7** | 5 | 2–4 (cũ) | 1/3 → **đã nới thành 3–8** |
| **URL nguồn ngoài** | **0** | **0** | 5 | ≥2 | **1/3** ❌ |
| Cụm "Theo \<nguồn\>" | 5 | 7 | 9 | — | — |
| Cụm "Theo mình" | 2 | 1 | 2 | ≥1 | 3/3 ✅ |
| Khối `> **Góc nhìn:**` | **0** | **0** | **0** | ≥1 | **0/3** — luật mới, chưa từng chạy |
| `content.md` — số từ | 4.770 | 6.399 | 7.191 | — | — |
| **`fb_post.txt` — ký tự** | 5.645 | 4.491 | 6.048 | (ghi nhầm đơn vị: "2.000–3.500 **từ**") | **→ ngưỡng mới 4.000–7.500 ký tự** |
| `fb_post.txt` — số từ | 1.238 | 998 | 1.331 | — | — |
| Hashtag FB | 9 | 10 | 11 | 6–13 | 3/3 ✅ |
| Ngắt `———` | 16 | 16 | 18 | → 8–9 mục | 3/3 |
| **Ký tự Unicode bold trong FB** | **212** | **0** | **0** | bắt buộc | **1/3** ❌ |
| Markdown literal trong FB | 0 | 0 | 0 | = 0 | 3/3 ✅ |
| Vị trí link FB | dòng 1 | dòng 1 | dòng 1 + 7 | (cũ) đầu bài | **0/3 theo luật mới** |
| `youtube_desc.txt` — ký tự | 982 | 1.141 | 1.214 | 150–300 từ | ✅ |
| `podcast.txt` — số từ | **692** | 930 | **1.545** | 750–1.000 | 1/3 |
| `audio.mp3` — giây | 184,6 | 245,7 | 405,4 | — | — |
| **Tốc độ đọc thật (từ/giây)** | 3,75 | 3,79 | 3,81 | prompt giả định **3,2** | lệch **+18%** |
| `scenes.json` — số scene | 8 | 8 | 8 | = 8 | 3/3 ✅ |
| Ảnh thật / đồ hoạ (trừ cover) | 3/4 | 3/4 | 3/4 | ~50/50 | 3/3 ✅ |
| `video.mp4` | 1280×720 · 184,6s | ·245,7s | ·405,4s | = độ dài audio | 3/3 ✅ |
| `thumbnail.png` | 1280×720 | 1280×720 | 1280×720 | 1280×720 | 3/3 ✅ |
| **Thẻ `og:` trong HTML** | **0** | **0** | **0** | 6 thẻ | **0/3** ❌ |
| JSON-LD `Article` | 0 | 0 | 0 | mong muốn | 0/3 |
| Continuity — tóm tắt (từ) | 36 | 43 | **87** | ≤60 | 2/3 |
| Continuity — key-terms | có | có | có | bắt buộc | 3/3 ✅ |
| Continuity — nguồn | **không** | **không** | có | bắt buộc | 1/3 |
| `[KIỂM CHỨNG]` còn mở | 0 | 0 | 0 | = 0 | 3/3 ✅ |
| Chính kiến bơm vào prompt | **rỗng** | **rỗng** | **rỗng** | phải có | **0/3** 🐛 |

## 2. Công thức thời lượng podcast

Đo thật trên 3 bài: **3,75 · 3,79 · 3,81 từ/giây** — rất ổn định (lệch <2% giữa các bài).
Prompt cũ giả định **3,2 từ/giây**, tức **thấp hơn thực tế 18%**, nên mọi ước lượng thời lượng
đều dài hơn thực tế và không ai phát hiện vì không có cổng nào so lại.

```
thời lượng (giây) ≈ số từ / 3,8
số từ cần cho T giây ≈ T × 3,8
```

Suy ra dải 750–1.000 từ ⇒ **≈ 197–263 giây** (3,3–4,4 phút). Nếu muốn video 5 phút thì cần
≈ 1.140 từ — **phải nới ngưỡng một cách có ý thức**, đừng để bài tự trôi như S-003 (1.545 từ).

## 3. Bốn điều bảng này nói ra mà mắt thường không thấy

1. **Luật định tính không tự thực thi.** "Phải dẫn nguồn thật" được ghi rõ trong prompt, mà
   2/3 bài có **0 nguồn ngoài**. Luật không có cổng đếm = luật không tồn tại.
2. **Chất lượng trôi theo thời gian, không trôi ngẫu nhiên.** Unicode bold: bài 1 có 212 ký
   tự, bài 2 và 3 rơi thẳng về 0. Bài đầu làm kỹ, các bài sau cuốn theo nhịp — đây là lý do
   cổng phải chạy **mỗi bài**, không phải "kiểm lúc thiết lập quy trình".
3. **Đo sai đại lượng còn tệ hơn không đo.** Ngưỡng FB ghi "2.000–3.500 từ" trong khi bài
   thật 998–1.331 từ. Theo chữ thì cả 3 bài đều trượt; nhưng đo bằng ký tự (thứ Facebook
   thật sự đếm) thì cả 3 đều nằm trong dải hợp lý. Ngưỡng cũ khiến người bỏ qua cổng.
4. **Một tham số optional có thể làm hỏng cả 3 bài trong im lặng.** Chính kiến tác giả chưa
   bao giờ được bơm vào prompt — file nguồn nằm ở đường dẫn khác. Không có gì báo lỗi vì
   tham số là optional. Đây là lý do bước đọc chính kiến phải **fail-closed**.

## 4. Cách tái lập

```bash
# Ép UTF-8 khi in tiếng Việt ra stdout trên Windows, nếu không sẽ crash cp1252:
export PYTHONIOENCODING=utf-8
python scripts/pipeline/blog_gates.py <thư mục bài>
python scripts/pipeline/fb_format.py --check <thư mục bài>/fb_post.txt
```

Bảng trên dựng từ chính hai lệnh đó cộng `ffprobe` cho thời lượng audio/video.
Cập nhật bảng này khi có thêm ≥3 bài mới — **thêm cột, đừng sửa cột cũ**: mốc mất giá trị
nếu bị viết đè.
