# Bài mẫu — một bài ngắn, một kết quả kỳ vọng cố định

Thư mục này là **bài thử đầu tiên** sau khi cài, và là thứ `doctor` xác minh **không cần
mạng**, không cần token, không cần trạm giọng hay trạm video. Nó chỉ chứa chữ.

| File | Là gì |
|---|---|
| `bai-mau/atlas/blog.md` | một bài blog **cố ý ngắn** (dưới ngưỡng độ dài của bài thật) |
| `bai-mau/facebook/post.txt` · `comment.txt` | bài Facebook và comment chứa link, đúng bố cục thư mục bài |
| `bai-mau/research.md` | ghi chú nghiên cứu mà cổng nguồn (G05) đối chiếu |
| `gates-expected.json` | **kết quả kỳ vọng cố định** khi chấm 24 cổng ở bước `write` |

Mọi đường link trong bài mẫu là tên miền ví dụ (`example.com`, `example.org`, `example.net`)
— không trỏ tới trang thật nào.

## Chạy thử

Từ gốc repo, trên Windows hay macOS như nhau:

```text
python scripts/pipeline/blog_gates.py samples/bai-mau --home-domain example.com --json-only
```

Lệnh này in kết quả và ghi thêm `samples/bai-mau/gates.json` (nhật ký cổng, `.gitignore` đã
bỏ qua nên không bao giờ lên git). Nó **thoát mã 1** vì bài mẫu bị chặn — đó là kết quả
đúng, không phải lỗi cài. `doctor` thì chấm trong bộ nhớ, không ghi file nào.

## Kết quả kỳ vọng (cố định)

| Mục | Kỳ vọng |
|---|---|
| `verdict` | `fail` — bài mẫu cố ý không đạt |
| Tổng số cổng | 24 |
| Xanh | 10 |
| Đỏ chặn (`fail_block`) | 6 — `G01` độ dài, `G02` số H2, `G05` nguồn ngoài, `G06` khối chính kiến, `G13`, `G24` |
| Đỏ cảnh báo (`fail_warn`) | 1 — `G10` |
| Chưa đo được (`missing`) | 7 — `G15`–`G20` thuộc bước sau (podcast, video, trang, đăng), `G22` vì bài mẫu không khai `brand.org_names` |

Trạng thái từng cổng nằm ở `gates-expected.json`. Hai điều bài mẫu kiểm cùng lúc:

- cổng **còn kêu**: bài ngắn thì `G01` phải đỏ;
- cổng **không kêu oan**: cổng thuộc bước sau báo `missing`, không báo đỏ.

## `doctor` kiểm gì

Dòng `samples` của `python scripts/pipeline/doctor.py`:

| Dòng | Nghĩa | Việc cần làm |
|---|---|---|
| `samples: PASS` | chấm lại bài mẫu ra đúng từng trạng thái trong `gates-expected.json` | không |
| `samples: WARN` | lệch ở ít nhất một cổng — bài mẫu bị sửa, hoặc cổng đổi luật mà chưa cập nhật kỳ vọng | `git status samples/`; đổi luật cổng thì cập nhật `gates-expected.json` trong cùng commit |
| `NOT_CHECKED samples` | bản cài không kèm `samples/` (không phải bản clone) | không bắt buộc |

`WARN` không làm `doctor` đỏ: bài mẫu là phép thử của bản cài, không phải điều kiện để chạy.
Cổng giữ kết quả này: `tests/test_samples.py`.
