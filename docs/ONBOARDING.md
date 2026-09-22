# Onboarding — từ repo trắng tới lượt chạy đầu tiên

> Mười bước, theo đúng thứ tự phụ thuộc. Mỗi bước có **cách kiểm** riêng — làm xong một
> bước thì kiểm ngay, đừng để dồn tới cuối rồi đi tìm trong mười thứ xem cái nào hỏng.
>
> Đang **đổi máy** chứ không phải dựng mới? Đọc [`RUNBOOK-DOI-MAY.md`](RUNBOOK-DOI-MAY.md).
> Muốn biết thư mục nào chứa gì: [`WORKSPACE.md`](WORKSPACE.md).
> Bố cục ba trạm và bảng biến: [`STATION_LAYOUT.md`](../knowledge/toolchains/STATION_LAYOUT.md).

---

## Máy mới: repo, Python, phụ thuộc

```sh
git clone <repo> ~/Code/agent-marketing-studio
cd ~/Code/agent-marketing-studio
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt      # Windows: .venv\Scripts\python.exe
```

Cần thêm: **pwsh ≥ 7.4** (mọi `.ps1` của repo chạy được ở cả PowerShell 5.1 lẫn pwsh 7),
**Node ≥ 22**, **ffmpeg + ffprobe**. Thiếu cái nào thì `doctor` ở bước 7 nói rõ.

---

## Bước 1 — Chọn chế độ cài

```sh
./install.sh            # macOS/Linux — hỏi bạn chọn
.\install.ps1           # Windows
```

Hai vỏ đó chỉ dò Python rồi giao việc cho `scripts/pipeline/init_station.py`; mọi quyết
định nằm ở một chỗ đó.

| Chế độ | Nội dung của bạn nằm ở | Chọn khi |
|---|---|---|
| **`embedded`** (khuyến nghị cho người mới, Enter là nhận) | `<repo>/workspace/` — trong repo, nhưng bị `.gitignore` khoá và có hook `pre-commit` chặn | một máy, một bộ nội dung, muốn ít thứ phải nhớ |
| **`separate`** | một thư mục ngoài repo (mặc định `~/.marketing`) | máy đã có trạm, hoặc nhiều repo/nhiều máy dùng chung một trạm |

Bộ cài **tự chọn `separate` không hỏi** khi máy đã khai `MARKETING_STUDIO_DATA`,
`VOICE_STATION`, `VIDEO_STATION`… hoặc `~/.marketing` đã có `CHANNELS.md`. Nó chỉ báo là
đã nhận ra, không hỏi lại — nhận nhầm một trạm đang chạy là cách phá một trạm đang chạy.

Đổi ý sau: `python scripts/pipeline/studio.py migrate --to separate`.

**Kiểm:** `studio.local.json` ở gốc repo có `mode` đúng cái bạn chọn; `embedded` thì có
`workspace/`, `separate` thì **không**.

---

## Bước 2 — `AUTHOR.md`: bạn là ai

`<trạm>/AUTHOR.md` — người đứng tên, giọng chung, những gì bạn không viết. Đây là thứ mọi
prompt trong `.agents/prompts/` đọc để không tự bịa ra một danh tính.

**Kiểm:** file tồn tại và không còn chữ "ĐIỀN TRƯỚC KHI DÙNG" nào.

---

## Bước 3 — `CHANNELS.md`: sổ kênh

`<trạm>/CHANNELS.md` là **nguồn sự thật duy nhất** về "kênh nào nằm ở đâu". Script không
đi quét thư mục để đoán — kênh không khai ở đây thì không tồn tại.

Bước sau sẽ tự ghi vào file này, bạn chưa phải sửa tay.

---

## Bước 4 — Tạo kênh

```sh
python scripts/pipeline/new_channel.py \
    --id ten-kenh --label "Tên kênh" --path "<trạm>/ten-kenh" \
    --platforms web,youtube,facebook
```

`--path` **bắt buộc** và cố ý không có mặc định: chỗ để kênh là quyết định của bạn.

**Kiểm:** thư mục kênh có `channel.yml` + `brand.md`; `CHANNELS.md` có thêm một dòng.

---

## Bước 5 — `brand`: danh tính của kênh

Hai file, hai vai, đừng lẫn:

- **`<kênh>/brand.md`** — NGƯỜI đọc: nhận diện, giọng, chính kiến, những gì không nói.
- **`<kênh>/channel.yml`** khối `brand:` — MÁY đọc: `site_name`, `author`, `domain`,
  `og_image`, `footer`, `org_names`. Trang web, ảnh, chân video, cổng chấm bài đều lấy từ
  đây.

**Thiếu khối `brand:` là lỗi, không phải cảnh báo.** Engine dừng với mã 2 thay vì lùi về
một tên mặc định — vì cái tên mặc định ấy sẽ là danh tính của người khác.

Kênh có audio/video thì khai thêm trong `channel.yml` — **chỉ khi** bạn đã hoặc sẽ bật
năng lực giọng (bước 8); khai sẵn khi chưa có trạm giọng thì `doctor` chỉ nhắc, không đỏ:

- `voice_profile:` — tên một profile **có thật** trong kho giọng. Khi trạm giọng đã bật,
  `doctor` đối chiếu tên này với kho và trả **mã 2** nếu không khớp — khai sai mà không
  kiểm thì bạn biết lúc 3 giờ sáng.
- `bgm_style:` — style trong thư viện nhạc nền của trạm giọng.

**Kiểm:** `python scripts/pipeline/check_tree.py --channel ten-kenh` → `0 đỏ`.

---

## Bước 6 — Chiến dịch và bài

```sh
python scripts/pipeline/new_campaign.py \
    --channel ten-kenh --id CMP-2601-vi-du --name "Tên chiến dịch" --prefix ABC

python scripts/pipeline/new_post.py --campaign CMP-2601-vi-du --id ABC-001 \
    --slug bai-dau-tien --title "Bài đầu tiên"
```

Chiến dịch chạy theo lịch thì thêm `--runner <tên script engine>` để sinh luôn `run.ps1`.

`campaign.md` là **nguồn sự thật**; `logs/config-<ngày>.json` chỉ là bản chụp sinh lại mỗi
lượt — cấm sửa tay. Excel là bản xuất một chiều (`export_excel.py`), không phải nguồn.

---

## Bước 7 — Hook viết, hook đăng

`campaign.md` khai bốn hook — chúng là chỗ bạn cắm công cụ của mình vào:
`writer_cmd` · `audio_cmd` · `youtube_cmd` · `facebook_cmd`.

Repo **không** kèm công cụ viết: mẫu ở `templates/hooks/write-post.SAMPLE.ps1`, chép ra
rồi sửa. Hook nhận đường bài qua `{post}` và trả JSON có `url` (với hai hook đăng).

**Kiểm:** chạy khô một bước — `run-blog-campaign.ps1 -Step write -DryRun` — rồi đọc lời
dẫn in ra: nó phải chứa đúng skill/tham số bạn nghĩ. Ba bước runner nhận là `create-post`,
`write`, `publish`.

---

## Bước 8 — Trạm giọng và trạm video (NĂNG LỰC THÊM — bỏ qua được)

**Bước này không bắt buộc.** Lõi của repo là viết bài và đăng; nó
**không bắt buộc trạm giọng/video**. Bảy bước trên đã đủ để bạn viết và đăng bài đầu tiên.

Repo này **không** tự dựng hình, không tự đọc. Nó gọi hai trạm năng lực riêng qua
`scripts/lib/voice.py` và `scripts/lib/video.py`. Không làm audio/video thì bỏ qua cả bước
— `doctor` sẽ ghi *"giọng: chưa bật — cần khi bạn muốn lồng tiếng…"* và vẫn trả mã 0. Khi
nào bạn chạy một bước thật sự cần giọng (ví dụ `make_podcast.py`), chính bước đó dừng lại
với **mã 3** và in ra đúng các lệnh dưới đây — không ai phải nhớ trước.

```sh
git clone <repo giọng> ~/Code/agent-voice-studio
git clone <repo video> ~/Code/agent-video-studio

# MỘT venv chung cho cả hai — torch là phụ thuộc nặng duy nhất và cả hai đều cần
python -m venv <trạm giọng>/omnivoice/.venv
<OMNIVOICE_PY> -m pip install -e ~/Code/agent-voice-studio
<OMNIVOICE_PY> -m pip install -e ~/Code/agent-video-studio
```

### Ngoại lệ `pip install -e` — và khi nào KHÔNG được dùng nó

Luật chung của nhà là **không** `pip install -e`. Hai package này là **ngoại lệ đã chốt**:
chúng có `pyproject` chuẩn, và cài `-e` vào venv engine giữ cho một bản mã = một bản chạy,
không phải chép đi chép lại.

**Nhưng `-e` trói venv vào cây repo — kể cả vào NHÁNH đang checkout.** Trạm chạy theo lịch
mà cài `-e` thì đêm nào bạn để repo ở nhánh đang sửa dở, đêm đó lịch chạy bằng nhánh đang
sửa dở. Không có gì báo; chỉ có sản phẩm sai.

⇒ **Trạm chạy lịch thì cài BẢN SAO, không cài `-e`:**

```sh
<OMNIVOICE_PY> -m pip install ~/Code/agent-voice-studio      # không có -e
<OMNIVOICE_PY> -m pip install ~/Code/agent-video-studio
```

Dùng `-e` cho máy đang phát triển; dùng bản sao cho máy chạy lịch. Nâng cấp bản sao =
`git pull` rồi `pip install` lại — một câu, và nó là câu **bạn chọn lúc nào chạy**.

**Kiểm:**

```sh
python scripts/pipeline/doctor.py
```

Đạt khi trả mã **0** — và nó trả mã 0 **cả khi bạn bỏ qua cả bước 8 này**. `doctor` chỉ đỏ
khi LÕI hỏng: mã **2** là cấu hình sai (hai nguồn sự thật, rào `.gitignore` thủng, tên
profile khai trong `channel.yml` không có trong kho giọng), mã **3** là chưa có trạm nội
dung. Cài dở trạm giọng/video thì nó **nhắc**, không đỏ: dòng nhắc nói rõ còn thiếu gì và
bước nào sẽ dừng. `doctor` cố tình **không** tự cài repo khác cho bạn.

---

## Bước 9 — Secret

Luật ba tầng, không bao giờ đổi:

> `channel.yml` khai **TÊN BIẾN** · biến giữ **ĐƯỜNG DẪN** · file JSON ngoài git giữ
> **GIÁ TRỊ**.

Giá trị bí mật sống trong `~/.secret/<tài khoản>/…`. Đặt biến ở đâu thì tuỳ chế độ cài:
`separate` → cấp user (`setx` / khối `EnvironmentVariables` của plist); `embedded` →
`<repo>/.env` (đã bị `.gitignore` khoá và hook `pre-commit` chặn).

Danh mục biến đầy đủ, mỗi biến ai đọc và không đặt thì sao:
[`SECRETS.md`](../knowledge/toolchains/SECRETS.md). Lấy token cho từng nền tảng:
[`PLATFORM_SETUP.md`](../knowledge/toolchains/PLATFORM_SETUP.md).

**Kiểm:** biến trỏ vào file **có thật**; `doctor` mã 0.

---

## Bước 10 — Lịch chạy

**macOS (launchd)**

```sh
python scripts/runners/install_launchd.py --list
python scripts/runners/install_launchd.py --dry-run
python scripts/runners/install_launchd.py --only studio.marketing.daily-news-a
```

**Windows (Task Scheduler)** — gọi `run.ps1` của chiến dịch, bọc bằng một wrapper báo
Telegram. Bản trong repo là `scripts/runners/notify_run.py`.

⚠️ **launchd không có `ExecutionTimeLimit`.** Một lượt treo treo mãi, và lượt kế tiếp bị
bỏ qua lặng lẽ. Trần giờ phải nằm ở wrapper: `notify_run.py --timeout <giây>` — các plist
mẫu đã bật sẵn. Giải thích đầy đủ ở [`RUNBOOK-DOI-MAY.md`](RUNBOOK-DOI-MAY.md).

---

## Kiểm lần cuối

```sh
python scripts/pipeline/check_tree.py      # cây trạm có liền mạch không  → 0 đỏ
python scripts/pipeline/doctor.py          # bản CÀI có đủ để chạy không  → mã 0
```

Hai công cụ, hai câu hỏi khác nhau, **cố ý không gộp**: gộp thì một lỗi cấu hình máy hiện
ra như một lỗi nội dung, và bạn đi sửa nhầm chỗ.

Xanh cả hai ⇒ chạy thử một lượt thật ở chế độ UAT trước khi giao cho bộ lập lịch.
