# Quy trình tổng — agent nạp gì, lúc nào

File này là **điểm vào duy nhất**. Đọc nó trước, rồi chỉ nạp đúng file cần cho bước đang làm.
Đừng đọc cả repo — vừa tốn context vừa dễ lấy nhầm.

---

## Toàn cảnh

```
                    ┌─────────────── 👤 NGƯỜI ───────────────┐
                    │                                        │
  ①new ──▶ ②topics ─┤ approve_topic ├─▶ ③draft ─┤ approve_content ├─▶ ④media
                    │                                        │
                    │                    ┌─ approve_final ◀───┘
                    │                    ▼
                    └──────── ⑤publish ──▶ ⑥measure ──▶ ⑦learn ──┐
                                                                  │
                                        (quyết định 28 ngày) ◀────┘
```

Bảy bước, **ba chỗ dừng chờ người**. Người không tick thì CLI không trả việc ra — agent
không có đường vòng, và đó là chủ đích.

---

## Nạp gì ở mỗi bước

| Bước | Skill / lệnh | Knowledge cần đọc | Prompt | Checklist | Script | Template |
|---|---|---|---|---|---|---|
| **① new** — dựng chiến dịch | `campaign-new` | `KNOWLEDGE_MAP` | — | — | `new_campaign.py` | `templates/campaign-types/*.yml` + `brief.template.yml` |
| **② topics** — đề xuất chủ đề | `campaign-run` | `SCORING`, `MULTICHANNEL_MATRIX`, `<brand>/pillars.csv` | `prompts/topic-gen.md` | — | `campaign_excel.py list --stage topics` | `templates/research-brief.template.md` |
| 🔒 | **NGƯỜI tick `approve_topic`** | | | | `campaign_excel.py approve` | |
| **③ draft** — viết nội dung | `campaign-run` | `BRAND_VOICE`, `MULTICHANNEL_MATRIX` | `prompts/content-write.md` | `checklists/QA_ASSET.md` | `campaign_excel.py content` | `templates/content-blocks/*.md` |
| 🔒 | **NGƯỜI tick `approve_content`** | | | | | |
| **④ media** — brief hình & tiếng | `campaign-run` | `BRAND_VOICE` (mục ảnh) | — | `checklists/QA_ASSET.md` | `campaign_excel.py content --type media_prompt` | — |
| 🔒 | **NGƯỜI tick `approve_final`** | | | | | |
| **⑤ publish** — đăng | `campaign-run` | `MULTICHANNEL_MATRIX` | — | `checklists/QA_ASSET.md` | `campaign_excel.py publish-log` | — |
| **⑥ measure** — đo | `campaign-run` | `DIAGNOSTICS` | — | — | `collect/from_export.py` → `model/build_summary.py` | — |
| **⑦ learn** — chốt 28 ngày | `campaign-run` | `DIAGNOSTICS` | — | — | `campaign_excel.py set` | — |

**Persona dùng khi nào:** `content-strategist` ở ①②, `qa-reviewer` trước mỗi cổng 🔒,
`growth-analyst` ở ⑥⑦. Không gọi cả ba cùng lúc — mỗi bước một vai.

---

## Vòng lặp chuẩn — dùng cho mọi bước

```powershell
# 1. Luôn xem hiện trạng trước
python scripts/pipeline/campaign_excel.py status <wb.xlsx>

# 2. Hỏi việc — CLI chỉ trả asset đã qua cổng
python scripts/pipeline/campaign_excel.py list <wb.xlsx> --stage <stage> --json

# 3. Rỗng → DỪNG, báo ai cần tick cột nào. Không rỗng → xử lý TỪNG asset một.

# 4. Ghi kết quả về workbook
python scripts/pipeline/campaign_excel.py content <wb.xlsx> --asset <id> ...

# 5. Đổi trạng thái sang `to_status` khai ở schema/model.yml khối stages
python scripts/pipeline/campaign_excel.py set <wb.xlsx> --asset <id> --field status --value <...>

# 6. Báo cáo: đổi gì, ở asset nào, sheet nào, cột nào
```

Luật cổng nằm ở `schema/model.yml` khối `stages`. **Đọc file, đừng nhớ thuộc lòng** —
luật đổi thì hành vi phải đổi theo.

---

## Bảng tra nhanh

| Tình huống người dùng nói | Làm gì |
|---|---|
| "Tạo chiến dịch mới cho …" | Bước ① — chọn loại ở `templates/campaign-types/`, hỏi đủ 8 câu rồi mới tạo |
| "Chiến dịch X đang tới đâu rồi" | `status` — báo cáo, **không tự làm gì tiếp** |
| "Chạy tiếp đi" / "làm bước sau" | `status` → hỏi người muốn stage nào → vòng lặp chuẩn |
| "Viết nội dung cho …" | Bước ③ — nhưng phải `list --stage draft` trước. Chưa duyệt topic thì báo, không viết chui |
| "Đăng bài đi" | Bước ⑤ — mặc định `--mode dry_run`. Chỉ `live` khi `instance.yml` ghi `autonomy: full` **và** người nói rõ trong lượt này |
| "Kết quả thế nào" | Bước ⑥⑦ — `DIAGNOSTICS`, insight phải có `evidence_metric` + `evidence_value` |
| "Bài này ổn chưa" | `qa-reviewer` + `checklists/QA_ASSET.md` — chỉ báo cáo, **không tự sửa nội dung public** |
| "Duyệt hết đi cho nhanh" | **Từ chối.** Cổng là chữ ký của người. Hướng dẫn họ tick trong Excel hoặc dùng `approve` |

---

## Bảy điều tuyệt đối

1. Không tick hộ cổng duyệt.
2. Không đăng thật khi `autonomy` chưa phải `full` — kể cả khi được bảo "cứ đăng".
3. Không bịa số, bịa nguồn, bịa kết quả. Claim chưa xác minh mang tag `[KIỂM CHỨNG]`.
4. Không tự sửa nội dung public-facing — liệt kê kèm **độ tự tin**, tự tin thấp thì nêu 2 phương án.
5. Không lộ tên công cụ/hạ tầng sản xuất nội bộ.
6. Không ghi insight thiếu bằng chứng số.
7. Không so với median khi `baseline_n < 10` — để trống, ghi "chưa đủ mẫu".

---

## Trạng thái repo — cái gì dùng được hôm nay

| Vùng | |
|---|---|
| `schema/` · `scripts/{calendar,workbook,pipeline,courseware,collect,model}` · `agent/` | ✅ chạy được |
| Đo bằng **file export tay** | ✅ `collect/from_export.py` → `model/build_summary.py` |
| Đo bằng **API** (`collect/from_api_*`) và **đăng thật** (`publish/`) | ⛔ **chưa có** — cần quyền API |

### Đo bằng file export tay — chạy được ngay, không cần token

```powershell
python scripts/collect/from_export.py --calendar <calendar.csv> `
    --facebook-daily "Facebook Post Daily.csv" --youtube youtube_export.csv `
    --out <fact_metrics_daily.csv> --workbook <wb.xlsx>

python scripts/model/build_summary.py --calendar <calendar.csv> `
    --metrics <fact_metrics_daily.csv> --brief <brief.yml> `
    --leads-bridge <cta_lead_bridge.csv> --out <summary.csv> --workbook <wb.xlsx>
```

Hai điều script sẽ **từ chối làm im lặng**, và agent phải đọc cảnh báo chứ đừng bỏ qua:
- `primary_kpi` trong brief không phải tên cột đo được → in ✖ kèm danh sách cột hợp lệ,
  và **không kết luận winner**. Nhãn tiếng Việt để ở `primary_kpi_label`.
- Chưa đủ 10 nội dung cùng định dạng → `vs_median_*` để **trống**, in cảnh báo
  "CHƯA ĐỦ MẪU". Không được tự điền số thay thế.

Thư mục chỉ có `README` hoặc `.gitkeep` = **kho rỗng**. Không suy nội dung từ tên thư mục.
