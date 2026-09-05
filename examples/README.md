# `examples/` — một STATION đã điền, để đọc chứ không để chạy

Thư mục này là **một trạm nội dung hoàn chỉnh, thu nhỏ**: một kênh, một chiến dịch, ba bài
ở ba trạng thái khác nhau. Nội dung của nó nói về chính xưởng này — nên đọc ví dụ cũng là
đọc tài liệu.

Nó ở đây để trả lời câu hỏi mà một file mẫu rỗng không trả lời được: *điền xong thì trông
như thế nào?*

> **Trạm thật của bạn KHÔNG nằm trong repo.** Nó nằm ở chỗ bạn chọn (mặc định `~/.marketing`,
> nhưng có thể là bất cứ đâu — `CHANNELS.md` giữ địa chỉ). `profile.md` chứa thông tin cá
> nhân, `publish.json` chứa link thật: không thứ nào nên đi vào một repo công khai.
> File `profile.md` ở đây là **ví dụ bịa**, và mọi URL đều dùng `example.vn` / `EXAMPLE0001`
> — tên miền dành riêng cho ví dụ, không trỏ vào đâu thật.

## Cây thư mục — và vì sao nó như vậy

```
examples/                          ← STATION (trạm)
├── CHANNELS.md                    ← sổ kênh: kênh nào ở đâu. Kênh KHÔNG bắt buộc nằm
│                                     trong trạm; đây là chỗ duy nhất được trỏ ra ngoài.
├── index.html                      ← bản đọc TOÀN CẢNH, bấm đúp là mở (build_views.py)
└── vi-du-studio/                  ← MỘT KÊNH: một giọng, một tập người đọc
    ├── channel.yml                ← nền tảng nào, trụ nội dung nào, KPI mặc định
    ├── profile.md                 ← giọng, tác phong, chính kiến — file phẳng, không thư mục
    ├── continuity.json            ← sổ bài đã đăng, để B0 khỏi chọn trùng đề tài
    ├── CAMPAIGNS.md               ← sổ chiến dịch của kênh
    └── CMP-2609-gioi-thieu/       ← MỘT CHIẾN DỊCH
        ├── campaign.md            ← NGUỒN SỰ THẬT: brief + bảng Content
        ├── campaign.html          ← bản đọc của chiến dịch này
        ├── CMP-2609-gioi-thieu.xlsx  ← BẢN XUẤT (export_excel.py), một chiều
        └── GTX-001_.../           ← MỘT BÀI = một thư mục
            ├── research.md        ← brief chi tiết + nguồn (ĐÓNG BĂNG sau B1)
            ├── content.md         ← text MỌI kênh, tách bằng neo `## post:`
            ├── meta.json · publish.json · gates.json
            ├── atlas/  youtube/  facebook/   ← thứ đem đăng, sinh ra từ content.md
```

Thư mục kênh chỉ có **file phẳng + các thư mục chiến dịch**. Trước đây `profile/` và
`memory/` mỗi cái chứa đúng một file — lồng thêm một cấp chỉ để phải bấm thêm một lần.

## Ba bài, ba trạng thái

| Bài | Trạng thái | Có gì | Xem để hiểu |
|---|---|---|---|
| **GTX-001** | `published` | đủ: research, content, ba file kênh, `publish.json` với URL và số liệu | một bài hoàn chỉnh trông thế nào, và URL thật được ghi ở đâu |
| **GTX-002** | `approved` | mới qua Cổng 1, chưa viết | trạng thái ngay sau khi người duyệt đề tài |
| **GTX-003** | `proposed` | vừa tạo | thứ `new_post.py` sinh ra |

Ba bài này được tạo **một lượt** bằng `new_post.py --bulk`, đúng cách dùng khi lên lịch cả
đợt: đọc chiến dịch và hồ sơ một lần rồi viết cả loạt.

## `gates.json` của bài ví dụ ĐANG ĐỎ — và đó là chủ ý

Chạy 23 cổng trên GTX-001 ra **9 xanh · 7 đỏ-chặn · 3 cảnh báo · 4 thiếu**. Không phải lỗi:
bài ví dụ cố tình ngắn (~640 từ, luật là 2500–4000) và không có audio/video/ảnh. Giữ lại
file này để bạn thấy **một báo cáo cổng trông như thế nào khi đỏ**, thay vì chỉ thấy lúc
mọi thứ xanh.

Đáng chú ý là cột thứ tư: **`thiếu`**. Cổng không chạy được — thiếu file, thiếu tham số —
không bao giờ được cộng vào `xanh`. Không kiểm được là *chưa biết*, không phải *đã qua*.

Và đây cũng là chỗ ví dụ dạy nốt **đường miễn trừ**: `publish.json` của GTX-001 có
`quality_check: failed`, nhưng vẫn qua Cổng 2 vì người duyệt dùng
`approve --override-qa "<lý do>"` — lý do được chép thẳng vào `review.note`. Chặn cứng
một cổng đỏ nghe có vẻ an toàn hơn, nhưng thực tế nó khiến người ta đi sửa `gates.json`
cho xanh. Một lý do được ghi lại tốt hơn nhiều.

```bash
python scripts/pipeline/blog_gates.py \
  examples/vi-du-studio/CMP-2609-gioi-thieu/GTX-001_vi-sao-agent-can-cong-cua-nguoi \
  --home-domain example.vn
```

## Chạy thử trên chính thư mục này

Mọi lệnh dưới đây chỉ đọc và sinh lại file trong `examples/` — không đụng gì ngoài đó.
Sinh lại thì `git diff` sẽ thấy đổi (bản HTML mang giờ sinh, `.xlsx` là nhị phân);
`git checkout examples/` trả lại như cũ.

```bash
# kiểm liên kết hai chiều ở mọi cạnh (phải ra 0 đỏ)
python scripts/pipeline/check_tree.py --station ./examples

# sinh lại hai bản HTML
python scripts/pipeline/build_views.py --station ./examples

# xuất Excel
python scripts/pipeline/export_excel.py --station ./examples

# tách content.md ra các file đem đăng
python scripts/pipeline/gen_article.py \
  --content-md examples/vi-du-studio/CMP-2609-gioi-thieu/GTX-001_.../content.md \
  --meta       examples/vi-du-studio/CMP-2609-gioi-thieu/GTX-001_.../meta.json \
  --out-dir    examples/vi-du-studio/CMP-2609-gioi-thieu/GTX-001_...
```

`check_tree` sẽ báo **2 nhắc**: GTX-002 và GTX-003 chưa có `publish.json`. Đúng — hai bài
đó chưa đăng.

## Dựng trạm của riêng bạn

```bash
python scripts/pipeline/new_channel.py --id <ten-kenh> --label "<Tên>" --path <ĐƯỜNG/DẪN>
```

`--path` **không có giá trị mặc định**, và đó là chủ ý: chỗ lưu kênh là quyết định của bạn,
không phải của máy. Thiếu nó, script thoát với mã 3 và in ra đúng câu cần hỏi.

Rồi `new_campaign.py` → điền `campaign.md` cho đủ → `new_post.py`. Bước cuối **chặn** nếu
`campaign.md` còn chữ mẫu: bài viết ra từ một chiến dịch chưa rõ đối tượng thì viết xong
mới biết lệch, và lúc đó đã tốn cả vòng nghiên cứu, dựng tiếng và dựng hình.
