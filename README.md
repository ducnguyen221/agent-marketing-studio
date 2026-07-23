# marketing-agent

Engine chạy một chiến dịch marketing **từ đầu đến cuối bằng AI, người vẫn cầm cương** —
theo đúng mô hình đã chuẩn hoá ở KPIM Academy: mỗi chiến dịch được một file Excel quản lý,
ba cổng duyệt là cột trong đó, agent không qua được cổng khi bạn chưa tick.

Repo này **chỉ chứa engine** — AGENTS, template, output-style, script. Nội dung và dữ liệu
của bạn nằm ở "instance" do `install.ps1` tạo ra, ở nơi bạn chọn, và **không lên GitHub**
(trừ bộ mẫu `KPIM`).

## Mô hình dữ liệu

**Mỗi campaign = 1 folder + 1 file `.md` (hồ sơ) + 1 file `.xlsx` (5 sheet).**

```
content/<instance>/02_campaigns/<NN_Ten>/
├─ <NN_Ten>.md        hồ sơ chiến dịch (từ CAMPAIGN_TEMPLATE) — nghiệp vụ + lịch sử
├─ <NN_Ten>.xlsx      dữ liệu thực thi — 5 sheet
└─ assets/<post_id>_<slug>/    content.md · blog.md · fb_post.txt · thumbnail.png · ...
```

Năm sheet:

| Sheet | 1 dòng = | Vai trò |
|---|---|---|
| **Campaign** | 1 field (form dọc) | Metadata nghiệp vụ: mục tiêu, persona, key message, KPI, kênh, lịch |
| **Post** | 1 bài | Bảng chủ. **3 cổng duyệt `approve_topic` / `approve_content` / `approve_final` ở đây.** status: proposed → drafted → media_ready → preview_ready → published |
| **Result** | 1 bài | URL + ID sau khi đăng (blog_url, youtube_url, fb_post_id, fb_permalink) |
| **Engagement** | 1 bài | Số liệu nền tảng kéo về (likes, reach, impressions…) — dữ liệu **duy nhất** đến từ ngoài file |
| **Assets** | 1 file | Sổ tài liệu: đường dẫn, loại, kích thước |

Cột lấy y hệt PIPELINE_CONTRACT của KPIM. Đặc tả: `schema/workbook_spec.yml`.

## Quy trình — 5 stage, 3 cổng duyệt

```
①new → ②topics ─[approve_topic]→ ③draft ─[approve_content]→ ④media → ⑤preview ─[approve_final]→ ⑥publish → ⑦report
```

Agent không đọc Excel để tự quyết. Nó hỏi CLI, và CLI chỉ trả bài đã qua cổng:

```powershell
python scripts/pipeline/campaign_excel.py status <wb.xlsx>
python scripts/pipeline/campaign_excel.py list   <wb.xlsx> --stage draft
```

Gating: `draft = approve_topic & proposed` · `media = approve_content & drafted` ·
`preview = media_ready` · `publish = approve_final & {preview_ready, media_ready}`.

**Agent không tick hộ cổng** — `campaign_excel.py set` từ chối ghi vào 3 cột approve_*.
Toàn bộ cách agent làm việc: [`AGENTS.md`](AGENTS.md).

## Cấu trúc repo

```
marketing-agent/
├─ AGENTS.md                    cách agent thực thi — quy trình 5 bước
├─ agent/
│  ├─ workflows/00_WORKFLOW_INDEX.md   điểm vào: nạp gì ở mỗi bước
│  ├─ templates/                CAMPAIGN_TEMPLATE · CONTENT_TEMPLATE · EMAIL · RECYCLING
│  ├─ output-styles/            compa-class-blog · tobi-post · multichannel-style
│  ├─ agents/                   content-strategist · growth-analyst · qa-reviewer
│  ├─ checklists/               QA_ASSET.md
│  └─ knowledge/                KNOWLEDGE_MAP · PLATFORM_SETUP
├─ schema/workbook_spec.yml     đặc tả 5 sheet + luật cổng
├─ scripts/
│  ├─ workbook/build_workbook.py     dựng workbook 5 sheet
│  ├─ pipeline/campaign_excel.py     CLI thao tác workbook (list/approve/set/result/...)
│  ├─ pipeline/campaign_registry.py  sổ chiến dịch (CAMPAIGNS.md + campaigns.xlsx)
│  └─ pipeline/build_preview.py      dựng preview.html tự chứa (ảnh nhúng base64)
├─ content/KPIM/                bộ mẫu (instance duy nhất vào git)
└─ docs/plans/                  lịch sử thiết kế
```

## Bộ mẫu `content/KPIM`

`content/KPIM/02_campaigns/01_Tobi_Posts/` — một campaign chạy đầy đủ, tái tạo đúng bản
chuẩn `01_Tobi_Posts` của KPIM Academy: hồ sơ `.md` + workbook 5 sheet + asset. Clone về
là xem được một chiến dịch hoàn chỉnh trông thế nào, không cần token.

## Style — đọc trước khi viết

| Kênh | File |
|---|---|
| Blog | `agent/output-styles/compa-class-blog.md` |
| Facebook (post dài + caption Reel) | `agent/output-styles/tobi-post.md` |
| Format đa kênh (YouTube/FB/X) | `agent/output-styles/multichannel-style.md` |

Quy tắc vàng: cùng 1 nội dung gốc, **FORMAT LẠI** theo từng kênh — không copy y nguyên.

## An toàn

- **Không có `approve_final` thì không đăng.** Cổng là cột trong Excel, không phải quy ước miệng.
- **Token không bao giờ vào repo.** Chỉ có `.env.example`. Quy trình lấy token + scope:
  `agent/knowledge/PLATFORM_SETUP.md`.
- **Dữ liệu nền tảng kéo về Sheet Engagement** qua `fb_post_id` — bằng API hoặc file export.

## Trạng thái

Đang xây. Tiến độ và quyết định thiết kế: [`docs/plans/2026-07-21-marketing-agent/`](docs/plans/2026-07-21-marketing-agent/).
