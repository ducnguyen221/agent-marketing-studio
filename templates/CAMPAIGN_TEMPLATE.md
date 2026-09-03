---
campaign_code: {{NN_Ten_Campaign}}   # = TÊN FOLDER, khớp Campaign.campaign_code trong .xlsx
name: {{Tên chiến dịch dễ đọc}}
owner: {{Tên người phụ trách}}
created: {{YYYY-MM-DD}}
status: {{proposed}}                 # proposed → active → paused → done → archived
workbook: {{NN_Ten_Campaign.xlsx}}   # file Excel song hành, cùng thư mục
---

# Hồ sơ chiến dịch — {{Tên chiến dịch}}

> Copy file này từ `templates/CAMPAIGN_TEMPLATE.md` vào thư mục campaign rồi đổi tên
> **giống thư mục** (`NN_Ten_Campaign.md`). Nó đi cặp với `NN_Ten_Campaign.xlsx`.
>
> `{{...}}` = cần điền. Mục 4–6 là **chuẩn dùng chung** — giữ làm mặc định, chỉ chỉnh khi
> campaign này thật sự khác.

## Bản đồ dữ liệu — cái gì sống ở đâu

Đây là luật chống trùng lặp. Một sự thật chỉ có **một** nơi canonical.

| Thứ | Nơi canonical | File .md này |
|---|---|---|
| Brief chiến lược, KPI, ngân sách, lịch | Excel · sheet **Campaign** | không chép lại |
| Danh sách ý tưởng, brief từng chủ đề, lịch từng content | Excel · sheet **Content** | không chép lại |
| Từng bài đăng theo kênh, trạng thái, link, **số liệu thật** | Excel · sheet **Post** (cột `actual_*`) | không chép lại |
| Định nghĩa mọi trường + luật hành động cho agent | `knowledge/data_model/DATA_MODEL.md` (sheet `_Legend` trong Excel chỉ là tóm tắt) | không chép lại |
| Text nội dung mọi kênh | `<folder_path>/content.md` | không chép lại |
| Ảnh · audio · video | chính thư mục `<folder_path>` | không chép lại |
| **Vì sao** làm campaign này lúc này | — | **Mục 1** |
| **Persona sâu** (Excel chỉ có 1 ô tóm tắt) | — | **Mục 2** |
| **Phạm vi: cái KHÔNG làm** | — | **Mục 4** |
| **Playbook phân phối** (vai kênh, giờ vàng, luật cross-post) | — | **Mục 5** |
| **Quy ước file & asset** | — | **Mục 6** |
| **Nhật ký quyết định** (đã chốt gì, vì sao) | — | **Mục 8** |
| **Báo cáo định kỳ · retro** | — | **Mục 9, 10** |

Thấy mình sắp gõ lại một con số đã có trong Excel → dừng, trỏ sang Excel thay vì chép.

---

## 1. Bối cảnh — vì sao làm, vì sao lúc này

- **Vấn đề cần giải**: {{vấn đề kinh doanh/truyền thông, KHÔNG phải chủ đề nội dung}}
- **Vì sao là bây giờ**: {{sự kiện, mùa vụ, thay đổi thị trường, động thái đối thủ}}
- **Trụ nội dung phục vụ + lý do chọn**: {{pillar — vì sao trụ này chứ không phải trụ khác}}
- **Điều kiện coi là thành công**: {{1–2 câu, cụ thể tới mức cãi được}}
- **Điều campaign này KHÔNG nhằm làm**: {{chống phình phạm vi}}

> Bản rút gọn của mục này nằm ở `Campaign.business_problem` và `Campaign.campaign_goal`.
> Ở đây viết đủ dài để người mới đọc là hiểu; Excel chỉ giữ bản một câu.

## 2. Đối tượng

- **Persona chính**: {{tên gọi nội bộ}} — {{vai trò, thâm niên, công cụ đang dùng}}
- **Một ngày của họ**: {{bối cảnh công việc thật, họ đọc nội dung lúc nào}}
- **Nỗi đau**: {{đau thật, không phải đau giả định}}
- **Rào cản/niềm tin sai cần gỡ**: {{cái làm họ không hành động}}
- **Họ đã tin gì rồi**: {{để không giảng lại thứ họ biết}}
- **Persona phụ** (nếu có): {{...}}

## 3. Thông điệp & bằng chứng

- **Thông điệp lõi**: {{một câu, lặp xuyên suốt campaign}}
- **Bằng chứng được phép dùng**: {{demo, số liệu, case study, tài liệu — kèm nguồn}}
- **Claim bị cấm**: {{điều tuyệt đối không được nói, kể cả khi nghe hay}}
- **Giọng**: {{tính từ + ví dụ câu đúng giọng}} — chi tiết ở `output_styles/`
- **CTA chính**: {{awareness | engagement | traffic | lead_generation | conversion | community | retention}}
- **Offer** (nếu có): {{thứ người xem nhận được}}

## 4. Phạm vi nội dung

### Trụ nội dung
| Trụ | Tỷ trọng | Chủ đề bao gồm | Dành cho persona |
|---|---|---|---|
| {{Trụ 1}} | {{35%}} | {{...}} | {{...}} |
| {{Trụ 2}} | {{25%}} | {{...}} | {{...}} |

Nhóm chi tiết dùng ở `Content.content_pillar` (xem giá trị hợp lệ tại `knowledge/data_model/DATA_MODEL.md`):
{{01_... | 02_... | 03_...}}

### Cái KHÔNG làm
- ❌ {{chủ đề lệch định vị}}
- ❌ {{dạng nội dung không muốn gắn tên vào}}
- ❌ {{vùng nhạy cảm}}

> Đây là **cổng lọc ở khâu đề xuất chủ đề**. Ý tưởng rơi vào danh sách này → loại, không thương lượng.

## 5. Playbook phân phối

### Vai từng kênh
| Kênh | Đối tượng | Vai trò | Format mạnh nhất |
|---|---|---|---|
| {{Blog}} | {{search/SEO}} | {{authority}} | {{long-form}} |
| {{YouTube}} | {{visual learner}} | {{tutorial}} | {{video dài + short}} |
| {{Facebook}} | {{cộng đồng}} | {{reach}} | {{story-driven}} |

Kênh khai ở đây phải khớp `Campaign.channels`. Post chỉ được tạo cho kênh trong danh sách này.

### Giờ đăng
{{Kênh A: 8–10h, 16–18h · Kênh B: 12–14h, 20–22h}}

### Luật cross-post
- **KHÔNG** copy y nguyên giữa các kênh — format lại theo từng kênh.
- {{Blog → cắt thành ... }}
- {{Video dài → rút insight độc lập thành short, không cắt ngẫu nhiên}}

### Sau khi đăng
- T+0→2h: trả lời bình luận
- T+1 ngày: xem lại, ghim bình luận tốt
- T+3 ngày: đối chiếu `actual_*` với `target_*` trong sheet Post → lưu hook thắng

## 6. Quy ước file & asset

### Một content = một thư mục = một `content.md`
```
<folder_path>/
├── content.md          ← TEXT của MỌI kênh, tách bằng heading '## post:<post_format>'
├── thumbnail.png
├── audio.mp3
├── video.mp4
└── short.mp4
```

`Content.folder_path` trỏ tới thư mục này. `Post.post_content` là **anchor** trỏ vào đúng đoạn
trong `content.md` — ví dụ `post:facebook_post`. Cùng một content có nhiều post trùng format
thì thêm hậu tố: `post:facebook_post#2`.

### Asset mặc định theo kênh × format
`Post.asset_ref` **để trống** = dùng đúng bảng này. Chỉ điền khi khác mặc định.

| post_format | Asset dùng |
|---|---|
| `blog_article` | `thumbnail.png` (+ `audio.mp3` nếu `Content.audio = yes`) |
| `youtube_video` | `video.mp4` + `thumbnail.png` |
| `youtube_short` · `reel` | `short.mp4` |
| `facebook_post` | `thumbnail.png` |
| `carousel` · `infographic` | phải điền `asset_ref` — không có mặc định |

Thư mục **chính là** kho asset. Không có sổ asset riêng, không có sheet Asset.

## 7. Rủi ro

| Rủi ro | Dấu hiệu sớm | Cách giảm |
|---|---|---|
| {{Content trễ}} | {{quá 2 content ở in_production}} | {{...}} |
| {{Tương tác thấp}} | {{actual_interaction < 50% target 3 bài liền}} | {{...}} |

## 8. Nhật ký quyết định

> Ghi mỗi khi chốt một điều **không suy ra được từ dữ liệu** — đổi hướng, bỏ chủ đề, đổi giọng.
> Đây là thứ Excel không giữ được: **lý do**. Append, không xoá dòng cũ.

| Ngày | Quyết định | Vì sao | Ai chốt |
|---|---|---|---|
| {{YYYY-MM-DD}} | {{...}} | {{...}} | {{...}} |

## 9. Báo cáo

> Append một mục `### Báo cáo YYYY-MM-DD` mỗi lần chạy. **KHÔNG xoá mục cũ.**
>
> Vì cột `actual_*` trong sheet Post **ghi đè** (không lưu lịch sử), chỗ này chính là nơi
> duy nhất giữ được diễn biến theo thời gian. Mỗi báo cáo phải chốt số tại thời điểm chạy.

<!-- BÁO CÁO APPEND BÊN DƯỚI -->

## 10. Retro

> Điền khi campaign chuyển `done`.

| Cái chạy được | Cái không chạy | Lần sau làm khác |
|---|---|---|
| {{...}} | {{...}} | {{...}} |

---

**Chủ campaign:** {{...}} · **Rà pillar/playbook:** {{định kỳ}} · **Đối chiếu Excel:** {{hàng tuần}}
