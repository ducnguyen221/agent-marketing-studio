# marketing-agent

Bộ engine chạy một chiến dịch marketing **từ đầu đến cuối bằng AI**: campaign brief → lịch nội dung → sinh nội dung → cổng phê duyệt → đăng YouTube/Facebook → thu số liệu → mô hình dữ liệu → dashboard → báo cáo có khuyến nghị.

Repo này **chỉ chứa engine** — skill, agent, workflow, script và template. Nội dung, dữ liệu và báo cáo của bạn nằm ở "instance" do `install.ps1` tạo ra, ở nơi bạn chọn, và **không bao giờ được đẩy lên GitHub**.

## Cài đặt

```powershell
git clone <repo> marketing-agent
cd marketing-agent
.\install.ps1
```

Script hỏi 7 câu (tên kênh · nơi đặt content · kênh · nguồn số liệu · mức tự trị · ngôn ngữ · brand voice) rồi dựng khung thư mục cho bạn. Enter hết = dùng mặc định trong repo.

## Cấu trúc

```
marketing-agent/
├─ agent/          MỌI THỨ DÀNH CHO AGENT
│  ├─ skills/          skill cross-tool (Claude · Codex · Antigravity)
│  ├─ agents/          persona: strategist · producer · QA reviewer · insight analyst
│  ├─ workflows/       pipeline xác định
│  ├─ prompts/         playbook theo pillar × định dạng
│  ├─ checklists/      QA gate · approval checklist
│  └─ knowledge/       .md: SOP, brand rules, luật vận hành
├─ schema/         HỢP ĐỒNG DỮ LIỆU (yml) — model · enums · crosswalk · workbook_spec
├─ scripts/        THỰC THI: calendar · workbook · publish · collect · model · courseware
├─ templates/      file mẫu: .pbip
├─ content/        ★ workbook Excel + nội dung  (gitignored, trừ KPIM)
├─ data/           export thô · star schema     (gitignored, trừ KPIM)
└─ reports/        báo cáo xuất ra              (gitignored, trừ KPIM)
```

**Ranh giới định dạng — mỗi loại file một việc:**

| Loại | Dùng cho | Vì sao |
|---|---|---|
| **YAML** (`schema/`) | Hợp đồng máy đọc: cột nào tồn tại, giá trị nào hợp lệ, tên nào ánh xạ tên nào | Cho phép ghi chú ngay cạnh từng dòng — Excel không giữ được lời giải thích |
| **Excel** (`content/`) | Thứ **bạn quyết định và duyệt**: brief, lịch, nội dung, phê duyệt, insight | Dropdown ràng buộc theo enum nên không gõ sai giá trị được |
| **Markdown** (`content/*/drafts/`) | Nội dung dài: kịch bản, bài Facebook | Ô Excel không chứa nổi, và cần diff từng câu |
| **CSV** (`data/`) | Dữ liệu khối lượng lớn máy tải/sinh ra | Power BI đọc thẳng, không khoá file |

Một instance có **3 gốc tách rời**, khai trong `instance.yml` — `content` có thể đặt ở kho tri thức riêng của bạn, `data`/`reports` để trong repo và không lên GitHub.

## Workbook một chiến dịch

Mỗi chiến dịch = một file `<CAMPAIGN_ID>.xlsx` **13 sheet**, dựng từ `schema/workbook_spec.yml`:

| Sheet | 1 dòng = | Ai ghi |
|---|---|---|
| `00_README` | hướng dẫn | 🤖 |
| `01_Brief` | 1 trường của brief | 👤 |
| `02_KPI_Target` | campaign × kênh × pillar × chỉ số × kỳ | 👤 target · ⚙️ baseline |
| `03_Calendar` | **1 asset** — sheet trung tâm | 🤖 sinh · 👤 duyệt |
| `04_Content` | 1 asset × 1 mảnh nội dung × 1 biến thể | 🤖 |
| `05_Approval` | 1 asset × 1 vòng duyệt (10 mục checklist) | 👤 |
| `06_Publish_Log` | 1 asset × 1 kênh × 1 lần chạy | ⚙️ |
| `07_Metrics_Daily` | asset × kênh × ngày | ⚙️ |
| `08_Metrics_Summary` | asset × kênh — winner, North Star, quyết định 28 ngày | ⚙️ tính · 👤 chốt |
| `09_Leads` | 1 lead | ⚙️ |
| `10_Insights` | 1 phát hiện — **bắt buộc có cột bằng chứng** | 🤖 đề xuất · 👤 duyệt |
| `_Lists` · `_Dictionary` | dropdown enum · data dictionary nhúng | ⚙️ |

🤖 agent · 👤 bạn · ⚙️ script. **Hàng tiêu đề nền vàng là cột của bạn — agent không bao giờ ghi đè.**

```powershell
python scripts/workbook/build_workbook.py --campaign-id <ID> --out <file.xlsx> `
    --brief brief.yml --calendar calendar.csv --kpi-target kpi_target.csv
```

## Quy trình — người ở đâu trong vòng lặp

Năm bước, **ba chỗ dừng chờ người**. Cổng duyệt không phải quy ước miệng mà là **ba cột
trong sheet `03_Calendar`**: `approve_topic`, `approve_content`, `approve_final`.

```
topics ──▶ [👤 approve_topic] ──▶ draft ──▶ [👤 approve_content] ──▶ media
                                                                      │
                                            [👤 approve_final] ◀──────┘
                                                    │
                                                    ▼
                                             publish ──▶ measure
```

Agent không đọc Excel để tự quyết. Nó hỏi CLI, và CLI chỉ trả về asset đã qua cổng:

```powershell
python scripts/pipeline/campaign_excel.py status <wb.xlsx>
python scripts/pipeline/campaign_excel.py list   <wb.xlsx> --stage draft
```

Danh sách rỗng thì agent phải báo cáo và dừng — không có đường vòng. Luật cổng nằm ở
`schema/model.yml` khối `stages`, không hardcode trong code.

### Bốn thứ chặn cứng

| Chặn | Khi nào |
|---|---|
| Không có việc để làm | Chưa tick cổng của stage đó |
| `set` bị từ chối | Agent cố ghi vào cột của người (`approve_*`, `tos_score`, `hrs_score`, `qa_passed`, `approved_by/at`) |
| Không cho đăng | Chưa tick `approve_final`, hoặc còn `verification_open > 0` (còn `[KIỂM CHỨNG]` chưa đóng) |
| Không cho đăng thật | `mode=live` mà `instance.yml` chưa đặt `autonomy: full` |

Cả bốn đã được kiểm bằng UAT 12 bước trên bộ mẫu KPIM — xem
`docs/plans/2026-07-21-marketing-agent/plan.md`.

## Bộ agent

```
agent/
├─ workflows/00_WORKFLOW_INDEX.md   ★ ĐIỂM VÀO — 7 bước, nạp gì ở mỗi bước, bảng tra nhanh
├─ templates/                       khuôn dựng sẵn
│  ├─ campaign-types.yml            4 loại chiến dịch + nhịp đăng + KPI mặc định
│  ├─ brief.template.yml            khuôn brief, chỗ nào phải hỏi người thì ghi <<HỎI NGƯỜI>>
│  ├─ campaign_workbook.template.xlsx   workbook trống 13 sheet để xem cấu trúc chuẩn
│  └─ README.md                     chọn loại nào, đổi được gì, không đổi gì
├─ skills/campaign-run/SKILL.md     luồng 5 stage, việc của từng stage, điều cấm
├─ agents/
│  ├─ content-strategist.md         cái gì nên làm, bao nhiêu, tỷ trọng pillar
│  ├─ growth-analyst.md             số liệu nói gì, nên scale hay dừng
│  └─ qa-reviewer.md                soát trước khi người phải đọc
├─ knowledge/
│  ├─ KNOWLEDGE_MAP.md              cần gì đọc file nào + trạng thái thật của repo
│  ├─ BRAND_VOICE.md                hồ sơ giọng YAML + danh sách "không bao giờ"
│  ├─ MULTICHANNEL_MATRIX.md        độ dài · hashtag · vị trí link theo kênh
│  ├─ SCORING.md                    TOS / HRS / Hook Score + ngưỡng loại
│  └─ DIAGNOSTICS.md                10 dòng triệu chứng → nguyên nhân → hành động
├─ checklists/QA_ASSET.md           18 mục + luật không tự sửa nội dung public
└─ prompts/                         topic-gen · content-write
```

### Dựng chiến dịch mới từ khuôn

Bốn loại dựng sẵn — chọn sai loại thì nhịp đăng và cách đo đều sai theo:

| Loại | Thời lượng | Hero | KPI chính | Dùng khi |
|---|---|---|---|---|
| `series` | 28 ngày · 4 chu kỳ · 28 asset | video dài | `subs_per_1000_engaged_views` | Chủ đề lớn chia nhiều tập |
| `product_launch` | 84 ngày · 12 chu kỳ · 24 asset | bài Facebook | `leads` | Ra mắt sản phẩm, cần đăng ký |
| `hot_news` | 3 ngày · 3 asset | short | `impressions` | Sự kiện phải nói trong 24–72h |
| `evergreen` | 14 ngày · 5 asset | video dài | `avg_percentage_viewed` | Chủ đề tìm kiếm nhiều tháng |

```powershell
python scripts/pipeline/new_campaign.py --instance <content_root> `
    --campaign-id DNA-C02 --type series --name "Tên" --start 2026-09-01 --owner "Duc Nguyen"
```

Script bung `asset_pattern` thành lịch đầy đủ với `asset_id` ổn định, `function_role`
chống lặp và `parent_asset_id` trỏ về hero của chu kỳ. Thêm `--dry-run` để xem trước.

**Script cố ý để trống** những thứ chỉ người mới trả lời được — `big_idea`, `objective`,
`persona`, tiêu đề từng asset, `tos_score`, `hrs_score`. Chúng hiện thành `<<HỎI NGƯỜI>>`
trong brief, và asset nằm ở `status: idea` cho tới khi stage `topics` chạy.

### Luật vận hành agent phải tuân

1. **Báo cáo hiện trạng trước, làm sau.** Mỗi lượt bắt đầu bằng `status`.
2. **Không tick hộ cổng duyệt.** Đó là chữ ký của người khác.
3. **Không đăng thật khi `autonomy` chưa phải `full`**, kể cả khi được bảo "cứ đăng đi".
4. **Không bịa số, không bịa nguồn.** Claim chưa xác minh mang tag `[KIỂM CHỨNG]` và
   `verification_open` phải đếm đúng — hệ thống sẽ chặn publish.
5. **Không tự sửa nội dung public-facing.** Liệt kê lỗi kèm **độ tự tin**; tự tin thấp thì
   nêu 2 phương án cho người chọn.
6. **Không lộ tên công cụ/hạ tầng sản xuất nội bộ** trong bất kỳ nội dung công khai nào.
7. **Insight phải có bằng chứng.** Thiếu `evidence_metric` + `evidence_value` thì không ghi dòng.
8. **Chưa đủ 10 mẫu thì không so với median.** Để trống và nói "chưa đủ mẫu".
9. **Cuối mỗi lượt báo đã đổi gì ở đâu** — asset nào, sheet nào, cột nào.

### Tri thức được chưng cất từ đâu

Bộ `agent/` không viết từ số không. Nó chưng cất từ hai nguồn đã chạy thật:

| Nguồn | Lấy gì |
|---|---|
| KPIM Academy `30_MARKETING/agent/` | Kiến trúc nhiều stage + cổng duyệt **mã hoá thành cột Excel** thay vì "nhớ hỏi user"; ma trận đa kênh; cơ chế chống lặp giữa các bài trong cùng chiến dịch; mẫu "cần X → đọc file nào" kèm luật chống ảo giác; ngưỡng STOP có số cụ thể trong persona |
| `Brain/` — 08.01 Writing Voice · AI_GUIDE · 51.01/51.02 Channel Strategy · 52.03–52.05 | Hồ sơ giọng + danh sách điều cấm; ba mức tự trị `suggest → auto_safe → full`; bảng chẩn đoán triệu chứng→hành động; TOS/HRS/Hook Score và ngưỡng loại; luật "winner" theo median nội bộ; nhịp đo 24h/72h/7d/28d; luật QA không tự sửa nội dung public |

## Bộ mẫu `content/KPIM`

`content/KPIM/` là một instance chạy đầy đủ bằng **dữ liệu mô phỏng** của một ngân hàng giả định (KPIM Bank): brief → 15 bài → duyệt → đăng mô phỏng → số liệu → dashboard. Dùng để:

- học viên khoá **MKA-101 Marketing Analytics** clone về là chạy được ngay, không cần token, không cần tài khoản;
- người mới xem một campaign hoàn chỉnh trông như thế nào trước khi dựng của mình.

Không có PII, không có credential, không đăng gì lên đâu cả.

## Nguyên tắc an toàn

- **`--dry-run` là mặc định.** Publish adapter từ chối chạy thật trừ khi instance đặt `autonomy: full` và bạn xác nhận bằng tay.
- **Không có `status: approved` thì không đăng.** Cổng duyệt nằm trong máy trạng thái, không phải quy ước miệng.
- **Token không bao giờ vào repo.** Chỉ có `.env.example`; `.env` và mọi file `*token*.json` đã bị gitignore.
- **Không đo thì không kết luận.** Khi chưa đủ 10 mẫu cùng định dạng để tính baseline, dashboard hiện "chưa đủ mẫu" thay vì một con số đoán.

## Schema

Toàn bộ mô hình dữ liệu nằm ở `schema/`:

| File | Vai trò |
|---|---|
| `model.yml` | star schema canonical: `dim_campaign` · `dim_asset` · `dim_pillar` · `dim_kpi_target` · `fact_metrics_daily` · `fact_lead` + quan hệ + measure |
| `enums.yml` | giá trị hợp lệ: format · platform · funnel_stage · status (kèm máy trạng thái) · cta_type · lead_source · autonomy |
| `crosswalk.yml` | ánh xạ 4 hệ tên đang tồn tại (canonical ↔ tài liệu khoá học ↔ file kế hoạch ↔ Facebook export tiếng Việt) |

Sửa schema ở đây là sửa cho mọi instance — kể cả bộ mẫu đem đi dạy.

## Trạng thái

Đang xây. Tiến độ và quyết định thiết kế: [`docs/plans/2026-07-21-marketing-agent/`](docs/plans/2026-07-21-marketing-agent/).
