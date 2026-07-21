# Ma trận đa kênh — một nội dung gốc, format lại theo từng kênh

> Nguyên tắc lõi: **1 nội dung gốc → FORMAT LẠI, không copy y nguyên.**
> Copy blog sang Facebook sẽ vỡ (markdown hiện thành ký tự literal); sang YouTube
> description sẽ thừa; sang X sẽ tràn 280 ký tự.

Chưng cất từ `30_MARKETING/agent/output-styles/multichannel-style.md` +
`tobi-post.md`, hợp nhất với giới hạn hashtag trong `schema/enums.yml`.

| Kênh | `format` | Độ dài | Hashtag | Vị trí link | CTA |
|---|---|---|---|---|---|
| Blog / long-form | `blog` | 2.500–4.000 từ | — (dùng keyword SEO) | internal ≥2 · external ≥2 | cuối bài, mềm |
| YouTube video dài | `long_video` | mô tả 150–300 từ | **≤3** | khối giữa/cuối mô tả | subscribe + xem tiếp |
| YouTube Shorts | `short` | 20–58 giây | **≤6** | trong mô tả ngắn | subscribe |
| Facebook post | `fb_post` | **2.000–3.500 từ, bản đầy đủ** | **6–13** | **ĐẦU bài** | câu hỏi cuối bài |
| Facebook Reel | `fb_reel` | caption 1–3 câu | ≤6 | sau hook | xem bản đầy đủ |
| YouTube Community | `yt_community` | 1–2 đoạn | ≤3 | không bắt buộc | vote / comment |
| Newsletter | `newsletter` | 5 khối cố định | — | trong từng khối | reply |

Giới hạn hashtag được `validate_calendar.py` kiểm tự động — sai là báo error, không phải cảnh báo.

## Facebook — điểm khác biệt hay bị làm sai nhất

- **Không viết teaser cụt.** FB post là bản nội dung đầy đủ. Người đọc không rời app
  để đọc bản dài ở nơi khác; cắt cụt chỉ làm tụt reach.
- **Link đặt ĐẦU bài**, không phải cuối. FB ưu tiên phân phối theo hành vi đọc đoạn đầu.
- FB **không render markdown**. Dùng **Unicode bold** cho heading, `———————` để ngắt
  đoạn, emoji số 1️⃣2️⃣3️⃣ cho danh sách.
  ⚠️ **Ký tự `Đ`/`đ` không có bản Unicode bold** — chuyển sẽ ra ký tự lạ (`Ĕ`).
  Heading chứa `Đ` thì để chữ thường, hoặc đổi cách diễn đạt.
- Đoạn 2–4 câu, xuống dòng thoáng. Khối chữ đặc là chết reach.
- Hashtag 6–13, trong đó 2–3 hashtag brand cố định.

## YouTube

- Mô tả **hook-first**: 2 dòng đầu là thứ hiện trên feed, đừng phí vào lời chào.
- Có `00:00` để YouTube nhận chapters.
- Số tập đặt **ở CUỐI** title (`… | Tên Series #3`), không phải đầu — đầu title là chỗ
  đắt nhất cho từ khoá.
- Shorts: **không dùng view thô làm thước đo** (YouTube đổi cách đếm view Shorts từ
  31/03/2025). Dùng `engaged_views`.

## Atomization — một nghiên cứu, nhiều asset, mỗi asset một chức năng riêng

```
research_brief
 └─ hero (long_video)        chứng minh — nơi đặt toàn bộ bằng chứng
     ├─ short 1              mở vấn đề        → Discovery
     ├─ short 2              chuyển đổi       → Return, dẫn về hero
     ├─ fb_post 1            mở vấn đề native → Discovery
     ├─ fb_post 2            giải thích sâu   → Trust
     ├─ fb_post 3            recap / đối thoại→ Engagement
     └─ yt_community         hỏi nhu cầu      → Demand research
```

**Mỗi asset một chức năng.** Nếu hai asset cùng hook, cùng luận điểm, cùng CTA thì
một trong hai là thừa — sửa hoặc bỏ, đừng đăng cả hai.

## Recycling 30 ngày

| Mốc | Việc |
|---|---|
| D0 | long-form gốc |
| D+3 | cắt short thứ 2 từ đoạn khác của cùng nội dung |
| D+14 | carousel / infographic từ khung tiêu chí trong bài |
| D+21 | re-cut short với hook khác |
| D+30 | blog evergreen + block newsletter |
| liên tục | comment-to-content: câu hỏi hay trong comment → asset mới |

Bảng theo dõi recycling nên có cột **"có ra lead không?"** — nếu không nối được content
về kết quả kinh doanh thì recycling chỉ là bận rộn.
