# INFOGRAPHIC_PROMPT_TEMPLATE — dựng ảnh tóm tắt cả bài trong một hình

> **Mục tiêu của ảnh này, nói một câu:** người lướt qua nắm được ý chính của bài **trong
> 5 giây, không cần bấm gì**. Nó không phải ảnh minh hoạ cho đẹp — nó là bản rút gọn của
> bài viết, dùng làm ảnh đăng Facebook **và** đặt ở đầu trang blog.
>
> Ảnh này thay cho `fb_image.png` cũ (một nền + 3 dòng chữ). Một ảnh, hai chỗ dùng.

## 1. Ba việc phải làm trước khi viết prompt

1. **Rút 6 điểm cốt lõi của bài.** Không phải 6 tiêu đề mục — 6 điều người đọc cần nhớ.
   Mỗi điểm gồm một nhãn ngắn (2–4 từ) và một dòng giải thích (8–14 từ).
2. **Tìm một con số.** Ảnh không có số thì trông như khẩu hiệu. Ưu tiên số có so sánh
   ("40 phút thay vì 75 phút" mạnh hơn "nhanh hơn 47%").
3. **Viết sẵn TỪNG chuỗi chữ sẽ xuất hiện trên ảnh**, đúng chính tả, đúng dấu, rồi mới
   viết prompt. Đừng để model tự nghĩ chữ — nó sẽ tự nghĩ, và nó sẽ nghĩ sai.

## 2. Ngữ pháp thị giác (chưng cất từ các bài đã chạy)

Bố cục 5 vùng, đọc theo hình chữ Z:

```
┌──────────────────────────────────────────────────────┐
│  ①  TIÊU ĐỀ LỚN  +  pill phụ đề  +  dòng ngày/bối cảnh │
├───────────┬──────────────────────────┬───────────────┤
│ ② 3 thẻ   │   ③  MINH HOẠ TRUNG TÂM   │  ④ 3 thẻ      │
│   đánh số │   người + thiết bị + mũi  │    đánh số    │
│   1-2-3   │   tên luồng               │    4-5-6      │
├───────────┴──────────────────────────┴───────────────┤
│  ⑤  DẢI DƯỚI: luồng hành động  |  ô cảnh báo          │
├──────────────────────────────────────────────────────┤
│                  thanh thương hiệu                    │
└──────────────────────────────────────────────────────┘
```

- **Khổ 1920×1080 (16:9).** Facebook hiển thị tốt, nhúng vào bài blog vừa khung, và đọc
  được trên điện thoại khi phóng to. Infographic dày mà ép khổ đứng thì chữ bé không đọc nổi.
- **6 thẻ là trần.** 8 thẻ trở lên là ảnh biến thành trang văn bản, không ai đọc.
- **Minh hoạ trung tâm phải là NGƯỜI đang làm việc**, không phải biểu tượng trừu tượng.
  Người xem cần thấy mình trong đó.
- **Không chữ nhỏ bên trong minh hoạ** (màn hình, cửa sổ giao diện): chỗ đó là nơi model
  hay bịa ra chữ vô nghĩa nhất. Bảo nó vẽ đường kẻ và khối placeholder.

**Bảng màu mặc định** — đổi được, nhưng phải giữ tương phản cao:

| Vai trò | Mã |
|---|---|
| Nền | `#F5F9FF` trắng ngả xanh, chấm bi mờ ở góc |
| Tiêu đề | `#1B3A8C` navy đậm |
| Số thứ tự, icon | `#2563EB` xanh dương |
| Nhấn phụ | `#22D3EE` cyan |
| Cảnh báo (chỉ dùng cho khối "đừng làm") | `#F97316` cam |

## 3. Khung prompt — điền vào chỗ `{{...}}`

Gửi qua cầu Codex (`ask-codex.cmd ask --origin human --access workspace --cwd <repo>`),
yêu cầu dùng `image_gen` và lưu vào `.tmp/infographic.png`.

```
Nhiệm vụ: dùng image_gen sinh MỘT ảnh infographic tiếng Việt, khổ ngang 1920x1080,
lưu vào: {{ĐƯỜNG DẪN TUYỆT ĐỐI}}

QUAN TRỌNG NHẤT — CHỮ TIẾNG VIỆT PHẢI ĐÚNG DẤU TUYỆT ĐỐI. Chép NGUYÊN VĂN từng chuỗi
dưới đây, không diễn đạt lại, không bỏ dấu, không thêm chữ nào ngoài danh sách.
Nếu không vẽ nổi một chuỗi cho đúng dấu thì thà để trống chỗ đó còn hơn vẽ sai.

PHONG CÁCH: infographic giáo dục hiện đại kiểu tạp chí công nghệ. Nền {{MÃ MÀU}} có hoa
văn chấm bi mờ ở góc. Khối nội dung là thẻ bo tròn trắng, đổ bóng mềm, viền rất mảnh.
Màu nhấn: {{BẢNG MÀU}}. Icon phẳng nét mảnh đồng bộ một bộ. Chữ sans-serif đậm, tương
phản cao. Bố cục thoáng, nhiều khoảng trắng, căn lưới rõ.

【VÙNG 1 — ĐẦU TRANG】
Tiêu đề rất lớn in đậm căn giữa, một dòng:  {{TIÊU ĐỀ ≤ 55 KÝ TỰ}}
Pill bo tròn nền xanh đậm chữ trắng:        {{PHỤ ĐỀ ≤ 60 KÝ TỰ}}
Dòng nhỏ có icon lịch:                      {{NGÀY · BỐI CẢNH}}

【VÙNG 2 — CỘT TRÁI, 3 thẻ dọc, đánh số 1-2-3】
Mỗi thẻ: ô vuông bo tròn xanh chứa SỐ trắng + icon + tiêu đề đậm + một dòng mô tả xám.
Thẻ 1 — icon {{...}}:  tiêu đề: {{...}}  mô tả: {{...}}
Thẻ 2 — icon {{...}}:  tiêu đề: {{...}}  mô tả: {{...}}
Thẻ 3 — icon {{...}}:  tiêu đề: {{...}}  mô tả: {{...}}

【VÙNG 3 — GIỮA, minh hoạ】
{{NGƯỜI + THIẾT BỊ + LUỒNG}}. Phong cách hoạt hoạ 3D thân thiện.
KHÔNG có chữ nhỏ nào bên trong các cửa sổ giao diện — chỉ đường kẻ và khối placeholder.

【VÙNG 4 — CỘT PHẢI, 3 thẻ dọc, đánh số 4-5-6】
(cùng kiểu thẻ như cột trái)

【VÙNG 5 — DẢI DƯỚI】
Trái: pill "{{TIÊU ĐỀ HÀNH ĐỘNG}}" + luồng ngang 4 bước nối bằng mũi tên:
   {{B1}} → {{B2}} → {{B3}} → {{B4}}
Phải: ba ô nền cam nhạt, mỗi ô icon chấm than + một dòng:
   {{ĐỪNG 1}} / {{ĐỪNG 2}} / {{ĐỪNG 3}}

【CHÂN TRANG】 thanh ngang navy, chữ trắng, icon sách mở: {{THƯƠNG HIỆU}}

TUYỆT ĐỐI KHÔNG: logo hãng, watermark, ảnh chụp người thật, chữ ngoài danh sách,
chữ tiếng Anh trang trí.
```

## 4. Cổng kiểm — bắt buộc, không được bỏ

Model sinh ảnh **vẫn vỡ dấu tiếng Việt**. Các ảnh đã dựng trước đây có lỗi thật:
`Cloud deploymenh` · `Thư cọc diectory` · `Project nnếu muốn tực open source`.
Ảnh đã đăng công khai thì không sửa được. Nên:

1. **Cắt riêng từng vùng chữ, phóng to ≥2×, đọc lại.** Đừng nhìn ảnh thu nhỏ rồi kết luận.
2. **Đối chiếu từng chuỗi với danh sách đã viết ở bước 1.3** — không phải đối chiếu với
   trí nhớ.
3. **Đối chiếu SỐ với `research.md`**, không chỉ với bản nháp đã soạn. Đây là bài học thật:
   một ảnh từng ghi "Nhanh hơn 47%" trong khi nguồn nói "47% *less time*" — chuỗi khớp
   chính tả 5/5 nhưng **sai nghĩa**, và cổng chính tả không thấy gì cả. Chính tả và nghĩa
   là hai phép kiểm khác nhau.
4. Sai một dấu, hoặc sai một chữ số → **sinh lại**, không "tạm chấp nhận".

**Sửa một dòng chữ thì không cần sinh lại cả ảnh.** Nếu nền quanh chữ là màu phẳng, vẽ đè
bằng Pillow rẻ hơn nhiều và giữ nguyên bố cục đã duyệt (đo màu nền, nội suy theo cột để
giữ vignette, dùng đúng font/cỡ). Sinh lại là mất ảnh đã duyệt và phải kiểm lại từ đầu.

## 5. Sidecar bắt buộc

Lưu `infographic.prompt.txt` cạnh ảnh, ghi: prompt đã dùng · **nguyên văn mọi chuỗi chữ
trên ảnh** · ngày kiểm chính tả và kết quả · mọi lần sửa sau đó và lý do.

Model **không tái lập**: cùng prompt cho ra ảnh khác. Mất prompt là mất cách dựng lại, và
**cấm sinh lại lúc đăng** — sinh lại nghĩa là bài đăng lên mang ảnh khác ảnh đã duyệt.

## 6. Ảnh này đi những đâu

| Nơi | Dùng thế nào |
|---|---|
| Bài Facebook | ảnh đính kèm post (thân bài không có link; link ở comment đầu) |
| Trang blog | đặt **ở đầu bài**, trước video, kèm caption "Tóm tắt cả bài trong một hình" |
| Tên file trên atlas | `<slug>-1.jpg` — **không** đặt `<slug>.jpg`, `findThumb` sẽ nhặt nhầm làm cover card |

`thumbnail.png` là việc khác: ảnh bìa 1280×720 dựng bằng `gen_infographic.py` (HTML +
Chrome, chữ luôn đúng), dùng làm cover card trên atlas và hình thu nhỏ YouTube.
