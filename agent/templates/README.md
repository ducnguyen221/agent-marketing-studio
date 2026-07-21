# Template — khuôn dựng sẵn cho agent

Agent **không tự nghĩ ra nhịp đăng và cấu trúc file**. Nó chọn khuôn ở đây rồi tinh chỉnh
theo bối cảnh. Như vậy mọi chiến dịch ra cùng một hình dạng, và dashboard so sánh được
giữa các chiến dịch.

| File | Dùng khi | Ai đọc |
|---|---|---|
| `campaign-types.yml` | Dựng chiến dịch mới — chọn 1 trong 4 loại | `new_campaign.py` |
| `brief.template.yml` | Sinh `01_Brief` cho chiến dịch mới | `new_campaign.py` |
| `campaign_workbook.template.xlsx` | Xem cấu trúc chuẩn 13 sheet khi chưa có dữ liệu | Người |
| `research-brief.template.md` | Trước khi viết nội dung có nhận định/kiểm chứng | Agent |
| `content-blocks/` | Khuôn từng loại nội dung theo kênh | Agent ở stage `draft` |

## Bốn loại chiến dịch

| Loại | Thời lượng | Hero | KPI chính | Dùng khi |
|---|---|---|---|---|
| `series` | 28 ngày · 4 chu kỳ | video dài | `subs_per_1000_engaged_views` | Chủ đề lớn chia nhiều tập, muốn người quay lại |
| `product_launch` | 84 ngày · 12 chu kỳ | bài Facebook | `leads` | Ra mắt sản phẩm/dịch vụ, cần đăng ký |
| `hot_news` | 3 ngày | short | `impressions` | Sự kiện vừa xảy ra, phải nói trong 24–72h |
| `evergreen` | 14 ngày | video dài | `avg_percentage_viewed` | Chủ đề người ta tìm kiếm nhiều tháng |

Chọn sai loại thì nhịp đăng và cách đo đều sai theo. Nếu người dùng mô tả nhu cầu không
khớp loại nào, **hỏi lại** thay vì ép vào loại gần nhất.

## Dựng chiến dịch mới

```powershell
python scripts/pipeline/new_campaign.py `
    --instance <content_root> `
    --campaign-id DNA-C02 `
    --type series `
    --name "Tên chiến dịch" `
    --start 2026-09-01 `
    --owner "Duc Nguyen"
```

Script sinh: thư mục chiến dịch · `brief.yml` (điền sẵn KPI + luật winner theo loại) ·
`calendar.csv` (bung từ `asset_pattern`, đủ `asset_id`, `function_role`, `parent_asset_id`)
· `drafts/` · workbook `.xlsx` 13 sheet.

**Script cố ý để trống** những thứ chỉ người mới trả lời được: `big_idea`, `objective`,
`persona`, `title_draft` từng asset, `tos_score`, `hrs_score`. Agent phải hỏi trước khi điền.

## Luật khi tinh chỉnh khuôn

1. **Đổi được:** ngày cụ thể, số chu kỳ, tiêu đề, pillar, thêm/bớt asset.
2. **Đổi phải nêu lý do:** bỏ hero khỏi chu kỳ · đổi `function_role` thành trùng nhau ·
   thêm CTA thương mại vào chu kỳ không được phép.
3. **Không đổi:** quy ước `asset_id` · tên cột canonical · luật cổng duyệt.

Sau mọi tinh chỉnh, chạy validator:

```powershell
python scripts/calendar/validate_calendar.py <calendar.csv> --pillars <pillars.csv>
```
