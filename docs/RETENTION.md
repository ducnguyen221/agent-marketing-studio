# Giữ và dọn media ở trạm

> Công cụ: `scripts/pipeline/prune_media.py` · cổng: `tests/test_prune_media.py`,
> `tests/test_publish_evidence.py` · sổ bằng chứng: `scripts/lib/publish_evidence.py`

Đường ống sinh audio/video mỗi ngày; đĩa thì không tự lớn. Trang này nói **cái gì được
dọn, dựa vào bằng chứng nào, và lấy lại bằng cách nào khi dọn nhầm**.

---

## 1. Luật một dòng

```
dọn  ⇐  (có BẰNG CHỨNG đã đăng)  ∧  (quá --days ngày)
giữ  ⇐  mọi trường hợp còn lại, kèm lý do nói rõ THIẾU bằng chứng nào
```

Tuổi file chỉ nói file cũ. Nó **không** nói sản phẩm đã ra khỏi máy: một lượt render hỏng
nửa chừng cũng già đi đúng 14 ngày như một tập đã lên sóng. Nên tuổi là **sàn an toàn**,
không phải căn cứ.

Vì sao vẫn giữ sàn 14 ngày dù đã có bằng chứng: YouTube xử lý chậm, và có lúc phải đăng
lại. Đường ống truyện giữ video của lượt trước tới tận lượt sau vì đúng lý do đó. Muốn dọn
ngay khi có bằng chứng thì `--days 0`; ở chế độ `--delete` còn phải gõ thêm
`--allow-days-0`.

---

## 2. Bằng chứng lấy từ đâu

| Loại | Bằng chứng | Nguồn | Khai thế nào |
|---|---|---|---|
| **Video** | đã lên YouTube | `*.published.json` cạnh file — khoá `video_id`, hoặc `short_id` cho bản `-short` | tự nhặt, không cần khai |
| **Video** (truyện) | đã lên YouTube | `truyen-state.json` — `last_publish_ok` + `last_video`, và các dải chương trong `history` | `--evidence <đường>` |
| **Video** (truyện, tập cũ) | đã lên YouTube | `playlist-youtube.json` — `video_id` của mục có dải chương trong tiêu đề | `--evidence <đường>` |
| **Audio** | đã có bản trên web | `<repo web>/<kênh>/audio/<ngày>/<tên file>.*` | `--web-repo` hoặc biến `WEB_REPO_DIR` |

Ba điều đáng nhớ:

- **Sổ của truyện phải khai ra.** Nó nằm ở trạm nội dung, còn video nằm ở trạm giọng —
  hai cây khác nhau, không có cách nào đoán đúng mà không cắm đường dẫn của một cái máy
  vào mã nguồn. Khai một file không phải sổ nào cả là **mã 2**, không phải cảnh báo.
- **`last_publish_ok: false`** (lượt trước đăng hỏng) ⇒ `last_video` **không** được tính
  là bằng chứng. `sweep_old()` của đường ống truyện cũng giữ nguyên mọi thứ trong ca đó.
- **Audio so theo TỪNG FILE**, không theo thư mục. Thư mục của ngày đó tồn tại chỉ chứng
  minh rằng *một* file nào đó đã đăng; `podcast.mp3` đã đăng không chứng minh gì cho
  `raw.wav` bên cạnh. Đuôi không cần khớp (web phát `.mp3`, trạm giữ `.wav` của cùng bản
  dựng) — cùng `stem` là cùng một bản.

---

## 3. Ba chế độ

| Chế độ | Cờ | Ghi kê khai |
|---|---|---|
| Chỉ in (mặc định) | — (hoặc `--dry-run` cho rõ ý) | chỉ khi `--manifest` |
| Dời | `--move-to <thư mục>` | `<thư mục>/manifest-prune-media.json` |
| Xoá | `--delete` | **bắt buộc** — `--manifest`, hoặc mặc định `<gốc>/../prune-media-log/<ngày>-<nhãn>-prune-media.json` |

Kê khai ghi **trước** khi đụng byte đầu tiên (trạng thái `planned`), rồi ghi lại sau khi
xong (`done`). Ghi sau thì một lần bị giết giữa chừng là mất cả hai: file lẫn danh sách
những gì đã mất. Không ghi được sổ ⇒ **mã 2 và không dọn gì**.

**Cầu dao:** `--max-files` (mặc định 200) và `--max-bytes` (mặc định 50 GiB) chặn trước khi
thi hành; vượt trần là mã 2 và không chạm file nào. `-1` là bỏ trần — gõ ra thì chịu trách
nhiệm. Cầu dao **không** chặn bản chỉ-in: chặn cả kế hoạch là bịt mắt người dùng.

---

## 4. Hai ngoại lệ có chủ đích

`--audio-policy age` và `--video-policy age` dọn theo tuổi, bỏ qua bằng chứng. Chúng dành
cho trạm mà media chỉ là bản render trung gian, không sổ đăng nào đối chiếu được — trạm
truyện dùng `--audio-policy age` vì kênh đó không đăng web. Cả hai **phải được gõ ra**:
mặc định im lặng dọn theo tuổi là đúng cái bẫy ở §1, chỉ khác là không ai thấy lúc nó xảy
ra.

`--audio-policy keep` / `--video-policy keep`: không bao giờ dọn loại đó.

---

## 5. Thứ không bao giờ bị đụng

`.raw/` · `voices/` · `assets/` · `.venv` · `venv` · `site-packages` · `node_modules` ·
`__pycache__` · `.git` — so khớp theo **từng thành phần** đường dẫn, nên `assets/` ở tầng
thứ tư vẫn bị loại. Mọi đuôi ngoài danh sách media cũng vậy: `.json` cạnh một `.wav` là
bảng cue, xoá nó là hỏng bản dựng.

`--root` trỏ thẳng vào một thư mục cấm bị **từ chối** (mã 2).

**Liên kết thư mục không bao giờ đi xuyên qua.** `Path.is_symlink()` trả `False` cho
junction của Windows, nên một `mklink /J` trong trạm đủ để kéo cả một cây ngoài trạm vào
kế hoạch xoá.

---

## 6. Hoàn tác

- **Đã dời** (`--move-to`): đọc `manifest-prune-media.json`, mỗi mục `prune` có `path`
  (chỗ cũ) và `moved_to` (chỗ mới) — chép ngược lại.
- **Đã xoá** (`--delete`): file không lấy lại được, nhưng kê khai nói **chính xác** mất
  gì: đường, kích thước, ngày, và **bằng chứng nào** đã cho phép xoá. Nếu bằng chứng đó
  sai (ví dụ `video_id` của một bản đăng nhầm), đây là chỗ duy nhất lần ngược ra được.

---

## 7. Trước khi gắn vào lịch chạy

1. Chạy bản chỉ-in vài đợt, đọc mục "giữ N vì:" trong báo cáo — nó nói thẳng thiếu bằng
   chứng nào.
2. `WEB_REPO_DIR` phải nằm **trong môi trường của chính scheduled task**. Thiếu nó thì mọi
   audio bị giữ *im lặng* (script ghi lý do vào báo cáo, không làm đỏ).
3. Chốt `--audio-policy` / `--video-policy` cho **từng trạm**, và khai `--evidence` cho
   trạm truyện. Đó là quyết định của chủ máy, không phải mặc định của script.
4. Đặt cầu dao theo cỡ thật của trạm đó, rồi mới đổi `--move-to` thành `--delete`.
