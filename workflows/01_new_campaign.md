# Khâu ①: Khởi Tạo Chiến Dịch (New Campaign)

| Thuộc tính | Chi tiết |
|---|---|
| **Vai trò chính** | `campaign-strategist` (hỗ trợ bởi `marketing-director`) |
| **Đầu vào (Input)** | Đề bài/Brief từ con người + `channel.yml` của kênh |
| **Công cụ (Tools)** | `scripts/pipeline/new_campaign.py` |
| **Đầu ra (Output)** | Thư mục chiến dịch + `campaign.md` đã điền đủ, `status: active` |

---

## 1. Trình Tự Thực Thi

### Bước 0 — Đã có kênh chưa?

Chiến dịch sống **bên trong một kênh**. Chưa có kênh thì tạo trước:

```
python scripts/pipeline/new_channel.py --id <ten-kenh> --label "<Tên kênh>" --path <ĐƯỜNG/DẪN>
```

`--path` **không có giá trị mặc định**, và đó là chủ ý: chỗ lưu kênh là quyết định của người,
không phải của máy. Kênh có thể nằm trên ổ khác, trong thư mục công ty, hay trong một kho
đồng bộ riêng — `CHANNELS.md` giữ địa chỉ. Thiếu `--path` thì script thoát với **mã 3** và in
ra đúng câu cần hỏi. **Gặp mã 3 thì HỎI NGƯỜI DÙNG, đừng tự chọn.**

### Bước 1 — Thu thập thông tin

Tiếp nhận đề bài. Còn thiếu bài toán kinh doanh, mục tiêu, đối tượng hay kênh thì hỏi lại
con người **một lượt rõ ràng**, không hỏi nhỏ giọt.

### Bước 2 — Khởi tạo bằng SCRIPT, không làm tay

```
python scripts/pipeline/new_campaign.py --channel <ten-kenh> --id CMP-YYMM-slug \
    --name "<Tên chiến dịch>" --prefix XXX [--station <trạm>]
```

Script copy `templates/campaign.md` vào thư mục chiến dịch và ghi dòng vào `CAMPAIGNS.md` của
kênh. `--prefix` là tiền tố mã bài (viết HOA), ví dụ `AST` → `AST-001`.

**Dùng script, không dựng tay.** Tự tạo thư mục rồi tự chép file là sớm muộn lệch cấu trúc —
và `check_tree.py` mới là chỗ phát hiện ra, sau khi đã làm được vài bài.

### Bước 3 — Chiến dịch sống ở TRẠM, không ở repo

Trạm phân giải theo thứ tự, dừng ở cái đầu tiên thấy: `--station` → biến môi trường
`MARKETING_STUDIO_DATA` → `~/.marketing`.

Kênh **không bắt buộc** nằm trong trạm. `CHANNELS.md` là cạnh **duy nhất** được phép trỏ ra
ngoài; script đọc nó chứ không quét thư mục. Kênh nằm trong trạm thì đường ghi **tương đối**
— để chép trạm sang máy khác vẫn chạy.

`examples/` trong repo là một trạm mẫu để đọc, không phải chỗ chứa chiến dịch thật.

### Bước 4 — Điền `campaign.md` cho ĐỦ

Frontmatter (bản một câu, máy đọc) **và** Mục 1–4 (bản dài, người đọc).

`new_post.py` **chặn** khi tám trường này còn nguyên chữ mẫu:

```
business_problem · campaign_goal · target_audience · audience_pain_points
key_message · content_pillar · channels · primary_cta
```

Vì sao chặn ở đây: bài viết ra từ một chiến dịch chưa rõ đối tượng và thông điệp thì viết
xong mới biết lệch — và lúc đó đã tốn cả vòng nghiên cứu, dựng tiếng và dựng hình. Chặn ở
khâu tạo rẻ hơn nhiều. Biết mình đang làm gì thì `--bo-qua-cong` bỏ chặn.

⚠️ `id` trong frontmatter phải **khớp tên thư mục**. Lệch là mọi tra cứu theo mã đều trượt,
và `check_tree.py` báo đỏ.

## 2. Tiêu Chuẩn Nghiệm Thu (Acceptance Criteria)

- [ ] `check_tree.py --station <trạm>` báo **0 đỏ**.
- [ ] `campaign.md` điền đủ tám trường bắt buộc — thử `new_post.py --dry-run`, không bị chặn.
- [ ] Mục 4 có danh sách **cái KHÔNG làm** — đây là cổng lọc ở khâu đề xuất chủ đề.
- [ ] Chuyển tiếp sang [Khâu ② (Plan)](02_plan_content.md).
