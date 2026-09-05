# Nối bí mật cho kênh và chiến dịch mới

> **Đọc trước khi dựng kênh mới, hoặc khi một script cần token/mật khẩu.**
>
> Một luật, và mọi thứ dưới đây chỉ là hệ quả của nó:
>
> **Cấu hình giữ TÊN BIẾN. Biến giữ ĐƯỜNG DẪN. File giữ GIÁ TRỊ.**
> Không bao giờ đảo thứ tự đó.

---

## Vì sao ba tầng chứ không phải một

| Nếu làm thế này | Cái gì hỏng |
|---|---|
| Ghi giá trị vào `channel.yml` | `channel.yml` nằm trong trạm, bị sao chép, bị chia sẻ, bị zip. Một bản sao là một bản rò rỉ. |
| Ghi đường dẫn cứng vào code | Đổi máy là gãy. Đổi chỗ file là gãy. Và tên người dùng nằm luôn trong code. |
| Ghi giá trị vào biến môi trường | Token Google **tự ghi đè file** mỗi lần làm mới — nó cần một file thật, không phải một chuỗi. Và biến môi trường thì không mở ra đọc được khi cần lấy tay. |
| **Ba tầng như trên** | Đổi chỗ file → sửa một biến. Đổi tài khoản → sửa một file. Chia sẻ cấu hình → không lộ gì. |

Chữ **`PATH`** trong `YT_TOKEN_PATH` là cố ý: biến giữ *đường dẫn tới file*, không giữ nội
dung. Nhờ vậy file vẫn mở ra đọc được — và thư viện Google vẫn ghi đè được khi làm mới token.

---

## Thư mục bí mật

Bí mật sống ở **một thư mục ngoài mọi kho git**, mặc định `~/.secret/`, gom theo **TÀI KHOẢN**
chứ không theo kênh:

```
~/.secret/
├── README.md                    ← MỤC LỤC: biến nào ↔ file nào ↔ ai đọc
├── <nền-tảng>-<tài-khoản>/      ← vd: youtube-ducnguyen-ai/, facebook-tobinguyen/
└── telegram/config.json         ← bot + danh sách chat
```

**Một tài khoản = một file, dù bao nhiêu kênh dùng chung.** Nhân bản là chỗ mà một bản được
cập nhật còn bản kia thì không — và bạn chỉ phát hiện lúc pipeline chạy lúc 19h.

Ba lý do thư mục này không được nằm trong kho git, kể cả kho riêng tư:

1. `.gitignore` là **một dòng text**; `git add -f` bỏ qua nó không cần hỏi.
2. Máy có thể chạy nhiều phiên agent song song — một `git add -A` sai chỗ là xong.
3. Riêng tư trên GitHub vẫn là **đã rời khỏi máy**; token vào lịch sử commit thì xoá không đơn giản.

Cắt kế thừa quyền **trước** khi copy byte đầu tiên vào đó. Copy trước rồi siết sau là để hở
một cửa sổ mà file nằm dưới quyền kế thừa của thư mục cha.

---

## Dựng kênh mới — bốn bước

### 1. Kênh dùng tài khoản ĐÃ CÓ (trường hợp thường gặp)

Mở `~/.secret/README.md`, tìm dòng của tài khoản đó, chép **tên biến** vào `channel.yml`:

```yaml
platforms:
  - channel: youtube
    handle: "Tên kênh · @handle"
    post_formats: [youtube_video]
    secrets_env: { token: YT_TOKEN_PATH, client: YT_CLIENT_SECRET }
  - channel: facebook
    handle: "Tên Page · id 1234567890"
    post_formats: [facebook_post]
    secrets_env: { config: FB_CONFIG }
```

Hết. Không tạo file mới, không `setx` gì thêm.

### 2. Kênh dùng tài khoản MỚI

```
① tạo ~/.secret/<nền-tảng>-<tài-khoản>/ và đặt file vào
② setx <TÊN_BIẾN> "<đường dẫn>"        ← cấp user, để scheduled task nhìn thấy
③ THÊM MỘT DÒNG vào bảng trong ~/.secret/README.md
④ khai tên biến đó trong channel.yml
```

**Bước ③ không được bỏ.** Bảng thiếu một dòng thì sáu tháng sau không ai biết file đó của ai,
và không ai dám xoá nó.

Tên biến: dùng **tên trần** (`YT_TOKEN_PATH`) cho tài khoản mặc định, **thêm hậu tố**
(`YT_TOKEN_PATH__NGHE_TIEN_TRUYEN`) cho tài khoản thứ hai trở đi. Không có sơ đồ bắt buộc —
điều duy nhất phải khớp là: **tên trong `channel.yml` == tên biến đã đặt**.

### 3. Bí mật KHÔNG có file

Đăng nhập trình duyệt, credential manager, token dịch vụ… **Đừng tạo file giả.** Thêm một
dòng vào bảng *"Bí mật KHÔNG có file"* của mục lục, kèm **cách lấy lại**.

Thiếu những thứ này thì pipeline hỏng **im lặng** — không có thông báo, trang web không cập
nhật — và không ai đoán ra vì sao. Đó là lý do chúng vẫn phải có mặt trong mục lục.

### 4. Chiến dịch mới trong kênh đã có

Không làm gì cả. Chiến dịch **thừa hưởng** bí mật của kênh; `campaign.md` không bao giờ khai
`secrets_env`. Chiến dịch cần tài khoản khác nghĩa là nó thuộc về một **kênh khác**.

---

## Viết code đọc bí mật

Một khuôn duy nhất, dùng cho mọi ngôn ngữ: **biến trước, đường lùi sau, và nói ra đã dùng cái nào.**

```python
# Python
CFG = os.environ.get("FB_CONFIG") or os.path.join(THU_MUC_CU, "facebook_config.json")
```

```powershell
# PowerShell — đọc thẳng registry, đừng đọc $env:
# Biến vừa `setx` thì tiến trình đang chạy CHƯA thấy; đọc registry thì thấy ngay.
$moi = [Environment]::GetEnvironmentVariable('YT_TOKEN_PATH','User')
if ($moi -and (Test-Path $moi)) { $env:YT_TOKEN_PATH = $moi; $nguon = 'NEW' }
else { $env:YT_TOKEN_PATH = $duongCu; $nguon = 'OLD' }
Log ("secret: $nguon  " + $env:YT_TOKEN_PATH)
```

Ba điều trong khuôn đó, mỗi điều đổi lấy một lần hỏng:

- **Đường lùi** để lúc chuyển đổi không phải dừng pipeline.
- **Ghi lại đã dùng đường nào** — hỏng mà không biết hỏng bên nào là kiểu hỏng đắt nhất.
- **Không in giá trị.** Chỉ in đường dẫn. Một dòng log dính token là token đã lộ.

### Ba điều tuyệt đối không làm

1. **Không hardcode đường dẫn.** `C:\Users\<tên>\...` trong code là code chỉ chạy trên đúng
   một máy, và mang theo tên người dùng.
2. **Không `print` giá trị bí mật**, kể cả khi gỡ lỗi. Kể cả một phần. Log tồn tại lâu hơn
   phiên gỡ lỗi.
3. **Không liệt kê biến môi trường theo tiền tố rồi in ra.** Có biến giữ *đường dẫn*, có
   biến giữ *giá trị* — lọc theo tiền tố là sớm muộn in nhầm cái thứ hai.
   *(Đã trả giá: một `TG_BOT_TOKEN` lọt vào transcript ngày 05/09/2026 đúng theo cách này.)*

---

## Kiểm trước khi tin

```bash
# 1. biến trỏ vào file có thật chưa
python -c "import os;[print(f'{k:34} {os.path.isfile(os.environ.get(k,\"\"))}') for k in ('YT_TOKEN_PATH','YT_CLIENT_SECRET','FB_CONFIG','EMAIL_CONFIG')]"

# 2. chạy khô toàn tuyến — phải thấy dòng `secret: NEW` trong log
<runner> -Uat

# 3. quyền của thư mục bí mật: protected, KHÔNG có tài khoản sandbox
powershell -c "(Get-Acl ~/.secret).AreAccessRulesProtected"
```

Chỉ xoá bản gốc ở chỗ cũ **sau khi một chu kỳ chạy đầy đủ báo xanh**. Trước đó chúng là lưới
an toàn, không phải rác.
