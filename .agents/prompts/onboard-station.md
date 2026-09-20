# Prompt — dẫn một người dựng trạm từ đầu

> Dành cho **agent** được giao việc "giúp tôi dựng trạm". Bản cho người đọc là
> `docs/ONBOARDING.md` — đọc nó trước, prompt này chỉ nói **cách dẫn**, không lặp lại nội
> dung mười bước.

## Nguyên tắc

1. **Đi đúng thứ tự phụ thuộc.** `AUTHOR.md` → `CHANNELS.md` → kênh → `brand` → chiến dịch
   → hook → giọng/video → secret → lịch → kiểm cuối. Nhảy cóc thì bước sau hỏng vì bước
   trước chưa có, và người dùng sẽ đi sửa nhầm chỗ.
2. **Kiểm sau MỖI bước, không dồn tới cuối.** Mỗi bước trong `docs/ONBOARDING.md` có một
   dòng "Kiểm" — chạy nó, đọc kết quả, rồi mới sang bước sau.
3. **Không đoán danh tính.** Tên người, tên site, tên miền, tên tổ chức đều **hỏi**.
   Không có thì để chỗ trống và nói rõ là chỗ trống. Một cái tên bịa ra ở bước 2 sẽ đi
   thẳng vào mọi trang web dựng ra sau đó.
4. **Không đoán chỗ đặt trạm.** `new_channel.py --path` cố ý không có mặc định. Hỏi.
5. **Không tự chọn chế độ cài hộ.** Trình hai dòng `embedded` / `separate` kèm lợi–hại rồi
   để người ta chọn. Ngoại lệ duy nhất: máy đã có trạm ngoài thì bộ cài **tự nhận**
   `separate` — khi đó chỉ báo là đã nhận ra, không hỏi lại.
6. **Không chạm kho secret.** Agent chỉ được nói *tên biến* và *đường dẫn*. Giá trị bí mật
   do chính người dùng đặt vào `~/.secret/<tài khoản>/`. Không đọc, không in, không chép.
7. **Không bật lịch hộ.** Dựng xong thì `--dry-run` cho người ta xem, rồi dừng lại và để
   họ gõ câu bật. Ba job `worker`, `approve-poller`, `daily-story` lại càng không.

## Câu phải hỏi trước khi gõ lệnh đầu tiên

- Máy này đã có trạm nào chưa? (quyết định `embedded` hay `separate`)
- Kênh đầu tiên tên gì, đăng lên những nền tảng nào, đặt ở thư mục nào?
- Có làm audio/video không? (có thì phải dựng thêm trạm giọng và trạm video)
- Chạy theo lịch hay chạy tay? (chạy lịch thì cài **bản sao**, không `pip install -e` —
  `-e` trói venv vào nhánh đang checkout)

## Dấu hiệu phải DỪNG và hỏi lại

- `check_tree.py` còn đỏ mà bạn không giải thích được vì sao.
- `doctor.py` trả mã 2 — đó là hợp đồng sai, sửa cấu hình, **đừng** lùi về giá trị mặc định.
- Người dùng bảo "cứ điền tạm tên gì đó" cho khối `brand:` — khối đó là danh tính công
  khai của họ; tạm ở đây nghĩa là vĩnh viễn.
- Trạm đích của `import` không trống.
- Nhật ký `<trạm>/MAY-DANG-CHAY.md` nói một máy khác đang chạy lịch.

## Kết thúc bằng

```
python scripts/pipeline/check_tree.py      → 0 đỏ
python scripts/pipeline/doctor.py          → mã 0
```

Rồi báo lại đúng ba thứ: chế độ cài đã chọn, đường trạm, và **việc còn lại người dùng
phải tự làm** (secret, bật lịch).
