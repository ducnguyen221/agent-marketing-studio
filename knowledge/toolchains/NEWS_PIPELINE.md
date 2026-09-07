# Chiến dịch chạy theo lịch — bản tin, series tự động

> **Đọc khi:** dựng một chiến dịch chạy bằng scheduled task (bản tin ngày/tuần, series đọc
> truyện, tổng hợp repo), hoặc khi sửa engine dùng chung của chúng.
>
> Chiến dịch marketing viết tay thì đọc `workflows/` — luồng khác, không dùng file này.

---

## Khác gì chiến dịch marketing

| | Marketing | Chạy theo lịch |
|---|---|---|
| Ai khởi động | người | Windows Task Scheduler |
| Một Content là gì | một ý tưởng bài | **một số / một kỳ** |
| Mã chiến dịch | `CMP-YYMM-slug` (có tháng) | **slug chức năng** (`daily-ai-news`) — sống vô thời hạn nên gắn tháng vào là nói dối |
| File thêm | — | `run.ps1`, `prompt.txt`, khối `runtime:` trong `campaign.md` |

---

## Ba tầng, và ranh giới giữa chúng

```
campaign.md          NGƯỜI viết. Brief + cấu hình + câu chữ.
      │
      │  campaign_cfg.py  (Python đọc YAML — PowerShell 5.1 KHÔNG đọc được)
      ▼
logs/config-<ngày>.json    BẢN CHỤP. Nhật ký, cấm sửa tay, sinh lại mỗi lượt.
      │
      │  run.ps1 truyền qua  -Config
      ▼
engine (~/.news/engine)    Không truyền -Config = chạy y như trước, đọc brand.json.
```

**Vì sao có bước dịch:** máy này không có `powershell-yaml`, không có `ConvertFrom-Yaml`,
không có PowerShell 7. Thử tự parse frontmatter bằng regex: đọc được 27 khoá phẳng nhưng
**sót 7/34 dòng** — đúng chỗ đặt màu và các khối lồng. Nên chia việc theo thứ mỗi bên làm
được: Python đọc `.md`, PowerShell đọc JSON.

**Vì sao sinh lại mỗi lượt:** sửa `campaign.md` xong chạy lại là ăn ngay, không cache,
không có chuyện bản chụp cũ nói một đằng file nguồn nói một nẻo.

---

## Dựng một chiến dịch mới

```bash
python scripts/pipeline/new_channel.py  --id <kênh> --label "…" --path ./<kênh> \
       --platforms youtube,facebook            # bỏ qua nếu kênh đã có

python scripts/pipeline/new_campaign.py --channel <kênh> --id <slug> --name "…" \
       --prefix XXX --runner run-toptoday-hot.ps1 --runner-args "-Brand ai -Publish"
```

`--runner` là thứ biến một chiến dịch thường thành chiến dịch chạy theo lịch: nó thêm khối
`runtime:` vào `campaign.md` và chép `templates/station/_channel/_campaign/run.ps1` thành `run.ps1`.
Không có `--runner` thì không sinh `run.ps1` — **cố ý**: đẻ ra một điểm vào mà không ai gọi
là để lại thứ sáu tháng sau không ai dám xoá.

Rồi điền: `runtime.label`, `content_pillar` (phải nằm trong `channel.yml:pillars`), và các
mục 1–3 của `campaign.md`. Kiểm bằng:

```bash
python scripts/pipeline/check_tree.py --station <trạm>          # phải 0 đỏ
python scripts/pipeline/campaign_cfg.py --campaign <thư-mục>    # phải exit 0
```

---

## Chạy

```powershell
.\run.ps1                                   # chạy thật
.\run.ps1 -Uat                              # không upload YouTube, Facebook dry-run
.\run.ps1 -Date 2026-09-01 -SkipResearch    # tái dùng JSON cũ, chỉ render lại
```

`run.ps1` **giống hệt nhau ở mọi chiến dịch** — mọi khác biệt nằm trong `campaign.md`.
Chép nó sang chiến dịch mới là chạy được ngay.

Scheduled task vẫn phải đi qua wrapper `notify-run.ps1` để có báo cáo Telegram:

```
notify-run.ps1 -Title "<tên task>" -Script <đường-dẫn-run.ps1> -ScriptArgs ""
```

---

## Trước khi đổi nguồn cấu hình của một runner

Đừng sửa rồi chạy thử xem sản phẩm. Một khoá lệch **không làm gãy gì** — nó chỉ khiến video
ra sai tiêu đề hoặc đăng nhầm playlist, và không có dòng lỗi nào.

Cách đúng: đối chiếu bản chụp với `brand.json` **trên đúng bộ khoá mà runner đó thật sự
đọc** (lấy bằng `grep '\$cfg\.'`, không gõ tay). So cả bộ khoá chung sẽ báo động giả —
`run-weekly-repo` không đọc `repo`/`gh_repo` thì chúng khác nhau cũng vô hại.

Nhớ trừ hai khoá **có đường lùi trong code**, chúng khác về chữ nhưng trùng về hành vi:

| Khoá | Đường lùi | Ở đâu |
|---|---|---|
| `bgm_vol` | `else { '0.10' }` | `run-toptoday-hot.ps1` · `run-weekly-news.ps1` · `run-weekly-repo.ps1` |
| `fb_text_post` | `if (-not $cfg.…)` → `$null` ≡ `$false` | `publish-hot-news.ps1` · 2 runner còn lại |

Xong đối chiếu thì UAT chéo: chạy **cùng một lệnh hai lần**, một lần có `-Config` một lần
không, rồi so output. Khác biệt duy nhất được phép là số dòng Excel tăng lên.

---

## Ba cạm bẫy đã trả giá

1. **`.ps1` KHÔNG có BOM = PowerShell 5.1 parse-fail IM LẶNG.** Task "chạy" mà không làm gì.
   Sinh file bằng Python thì phải ghi `b"\xef\xbb\xbf"` trước; công cụ ghi file thường không
   tự thêm. Kiểm: `head -c3 file.ps1 | od -An -tx1` phải ra `ef bb bf`.
2. **Chuỗi Python không-thô nuốt escape.** `'Code\agent-…'` → `\a` thành ký tự BEL, đường dẫn
   hỏng mà nhìn vẫn gần đúng (`Codegent-…`). Dùng chuỗi thô `r'''…'''` khi sinh script.
3. **Runner tính `$engine = $PSScriptRoot`** rồi tìm mọi thứ cạnh mình. Chép runner vào thư
   mục chiến dịch là nó chạy tưởng đúng rồi chết ở bước 3–4, sau khi đã tốn thời gian GPU.
   `run.ps1` phải **GỌI** runner ở engine, không chép nó về.
