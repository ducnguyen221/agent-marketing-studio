# Trạm nội dung — thư mục này là của BẠN

Repo `agent-marketing-studio` chỉ chứa **engine**: script, cổng kiểm, quy trình, khuôn mẫu.
Thư mục này — gọi là **trạm** — chứa **nội dung của bạn**: kênh, chiến dịch, bài, nhật ký,
sản phẩm đã dựng. Hai thứ tách nhau để cập nhật engine không bao giờ đụng vào nội dung.

Trạm nằm ở đâu là tuỳ chế độ cài (xem `docs/WORKSPACE.md` trong repo):

| Chế độ | Trạm nằm ở | Biến cấu hình |
|---|---|---|
| `embedded` | `<repo>/workspace/` (bị git bỏ qua) | `<repo>/.env` |
| `separate` | ngoài repo, mặc định `~/.marketing` | đặt ở cấp user (`setx` / plist launchd) |

## Cây thư mục

```text
<trạm>/
├── CHANNELS.md          sổ kênh — kênh nào ở đâu (cạnh DUY NHẤT được trỏ ra ngoài cây)
├── AUTHOR.md            tác giả là ai — dùng chung mọi kênh
└── <kênh>/              một kênh = một giọng, một tập người đọc
    ├── channel.yml      MÁY đọc: nền tảng · trụ nội dung · khối `brand:` · secrets_env
    ├── brand.md         NGƯỜI đọc: nhận diện · giọng · chính kiến · cái KHÔNG làm
    ├── CAMPAIGNS.md     sổ chiến dịch của kênh
    ├── continuity.json  sổ bài đã đăng — để khỏi trùng đề tài
    └── <chiến-dịch>/
        ├── campaign.md  brief + bảng Content + khối `runtime:`
        ├── prompt.txt   prompt bước CHỌN đề tài
        ├── run.ps1      điểm vào khi chạy theo lịch
        ├── out/ logs/   sản phẩm & nhật ký RIÊNG của chiến dịch
        └── <mã>_<slug>/ một bài: research.md · content.md · publish.json
```

Thư mục này mới chỉ có tầng trên cùng. **Ba tầng còn lại mọc ra bằng lệnh**, mỗi lệnh chép
khuôn từ `templates/station/` của repo — đừng tạo tay, vì tên thư mục và khoá trong file
phải khớp nhau thì cổng kiểm mới soi được:

```bash
python scripts/pipeline/new_channel.py  --id <kênh> --label "…" --path ./<kênh>
python scripts/pipeline/new_campaign.py --channel <kênh> --id <mã> --name "…" --prefix XXX
python scripts/pipeline/new_post.py     --campaign <mã> --id XXX-001 --slug … --title "…"
python scripts/pipeline/check_tree.py                       # soi lại cả cây
```

Muốn xem một trạm **đã điền sẵn** trước khi tự dựng: `examples/` trong repo là một trạm
hoàn chỉnh, chạy được `check_tree.py --station ./examples`.

## Cái gì được xoá, cái gì không

| Thư mục / file | Ai ghi | Xoá được? |
|---|---|---|
| `CHANNELS.md`, `AUTHOR.md`, `<kênh>/channel.yml`, `brand.md` | bạn | **không** — mất là dựng lại tay |
| `<chiến-dịch>/campaign.md`, `<bài>/*.md` | bạn + agent | **không** — đây là nội dung |
| `<bài>/publish.json`, `continuity.json` | script lúc đăng | **không** — mất là đăng trùng |
| `out/` | script dựng ảnh/video/trang | được, dựng lại được |
| `logs/` | script | được, chỉ mất dấu vết |

Bảng đầy đủ từng thư mục (ai ghi · có vào gói backup không · có nhạy cảm không):
`docs/WORKSPACE.md` trong repo.
