---
schema: content/1
content_id: GTX-001
campaign_id: CMP-2609-gioi-thieu
content_name: Vì sao một xưởng nội dung chạy bằng agent vẫn cần cổng của người
---
# Vì sao một xưởng nội dung chạy bằng agent vẫn cần cổng của người

> **File này là gì:** MỘT content = MỘT thư mục = MỘT `content.md`. File này chứa **toàn bộ text
> của mọi kênh**, mỗi kênh một khối `## post:<post_format>`.
>
> **Vì sao dùng neo:** mỗi phần tử `posts[]` trong `publish.json` trỏ tới đây qua `post_content`
> (vd `post:facebook_post`). Agent đọc đúng khối đó, không đoán theo kênh. Cùng một content có
> nhiều post trùng format → thêm hậu tố: `## post:facebook_post#2`.
>
> **Luật anchor — bắt buộc:**
> - Heading phải đúng `## post:<post_format>`, viết thường, không thêm chữ.
> - `<post_format>` phải là giá trị hợp lệ (xem `knowledge/data_model/DATA_MODEL.md` → `post_format`).
> - Chỉ tạo khối cho kênh có trong `Campaign.channels`. Kênh không đăng thì **xoá khối**, đừng để rỗng.
> - Mỗi khối phải có một phần tử tương ứng trong `publish.json → posts[]`. Có khối mà không
>   có phần tử = mồ côi; `check_tree.py` bắt được.
>
> **Trước khi viết, ĐỌC:** `output_styles/` (giọng của kênh, khai ở `channel.yml:brand_voice`) ·
> `knowledge/playbooks/COPY_FRAMEWORKS.md` · `knowledge/playbooks/SEO_PLAYBOOK.md` ·
> hồ sơ campaign `.md` (persona, cái KHÔNG làm, luật cross-post).
>
> **Quy tắc vàng:** cùng một brief → **FORMAT LẠI** theo từng kênh. Không copy y nguyên blog
> sang Facebook/YouTube.

---

# BRIEF — không đăng ở đâu cả

> Nguồn sự thật của content. Mọi khối `post:` bên dưới phải bám mục này. Nội dung mục này
> Brief chi tiết nằm ở frontmatter `research.md`; ở đây chỉ cần outline.

- **Mục tiêu content** (`content_goal`): người đọc chỉ ra được HAI chỗ trong quy trình của
  chính họ mà máy không nên tự quyết.
- **Người xem cụ thể** (`audience_profile`): người làm data/BI 2–8 năm, đã thử giao việc viết
  cho AI và thấy kết quả rỗng, chưa biết đặt ranh giới ở đâu.
- **Brief lõi** (`core_brief`): bài do agent viết nghe trôi chảy nhưng rỗng, và không khâu nào
  chặn lại → cái thiếu không phải chất lượng sinh chữ mà là ĐIỂM DỪNG có người → cái làm nội
  dung dùng được là chỗ NGƯỜI đặt tay vào.
- **Nguồn & bằng chứng** (`key_sources`): hai cổng trong `ATLAS_CHANNEL.md`; 23 cổng trong
  `blog_gates.py`; một bài đã đăng đủ ba kênh. Đều kiểm được bằng cách mở file. *Giả định
  chưa kiểm: cổng người tiết kiệm bao nhiêu thời gian — không đưa vào bài.*
- **Từ khoá chính** (`target_keyword`): quy trình nội dung với AI agent
- **Hướng sáng tạo** (`creative_direction`): đã cân nhắc 3 hướng (hướng dẫn từng bước · so
  sánh có/không cổng · kể một thứ đã đi qua mọi khâu mà vẫn rỗng) — chọn hướng thứ ba.
- **Giới hạn** (`constraints`): không hứa tự động hoá hoàn toàn; không nêu con số hiệu quả
  nào không đo được từ chính repo.
- **Vị trí trong series** (`content_relationship`): bài 1/3, dẫn sang GTX-002.

### Outline dùng chung
1. Một bài rỗng đi qua được mọi khâu — khâu nào lẽ ra phải chặn?
2. Hai chỗ máy không nên tự quyết: chọn đề tài, và duyệt trước khi đăng.
3. Cổng máy kiểm hình thức; chỉ người trả lời được "có đáng đăng không".

### Ẩn dụ đời thường (≥1, bắt buộc)
Máy dò kim loại ở sân bay: nó bắt được kim loại, không bắt được ý định. Cổng tự động của
một xưởng nội dung cũng vậy — bắt được link gãy và chữ mẫu còn sót, không bắt được bài rỗng.

### Claim cần kiểm chứng
- [x] "script không có đường nào tự đặt approved" → có test `test_chuoi_day_du_va_KHONG_tu_dat_approved`
- [ ] "cổng người giảm số bài phải gỡ sau khi đăng" → chưa đủ mẫu, **không đưa vào bài**

---

## post:blog_article

> Bài blog đầy đủ. Sapo in đậm → 5–10 H2 → callout → câu chốt dạng "không phải X mà là Y".
> SEO: primary keyword ở title, H1, 100 từ đầu và kết luận; internal link ≥2.
> Viết markdown trực tiếp, không bọc code-fence.

# Vì sao một xưởng nội dung chạy bằng agent vẫn cần cổng của người

**Bài này nói về quy trình nội dung với AI agent, và về một bài viết đã đi qua đủ mọi khâu
kiểm tra tự động mà vẫn không nên đăng.**

Không phải vì mô hình yếu. Bài đó đúng ngữ pháp, đúng độ dài, đủ nguồn, không link gãy.
Nó chỉ không đáng đăng — và không có cổng máy nào nói được điều đó.

## Cổng tự động kiểm được cái gì

Xưởng này có 23 cổng chạy bằng số: độ dài bài, số nguồn trong phần nghiên cứu, link còn
sống hay đã chết, chữ mẫu còn sót lại, tên công cụ nội bộ lọt ra bản công khai. Mỗi cổng
trả về một trong ba trạng thái: **xanh · đỏ · thiếu**.

Trạng thái thứ ba mới là điều đáng nói. "Thiếu" nghĩa là cổng không chạy được — file không
có, tham số không truyền. Nó **không bao giờ** được cộng vào "xanh". Cổng không chạy được
là *chưa biết*, không phải *đã qua*.

> 💡 Một hệ kiểm tra mà trạng thái "không kiểm được" bị tính là "đạt" thì càng nhiều cổng
> càng nguy hiểm: nó tạo cảm giác an toàn mà không tạo ra an toàn.

## Hai chỗ máy không nên tự quyết

**Chỗ thứ nhất: chọn đề tài.** Viết về cái gì là một quyết định chiến lược — nó tiêu tiền,
tiêu uy tín, và loại trừ những đề tài khác. Script tạo bài ở trạng thái đề xuất với ô duyệt
để **trống**; không có đường nào trong mã tự đặt thành đã duyệt. Người điền ngày vào ô đó,
và đó là chữ ký.

**Chỗ thứ hai: duyệt trước khi đăng.** Đây là chỗ cuối cùng còn sửa được rẻ. Sau khi đăng,
sửa một bài đã có người đọc và người chia sẻ đắt hơn nhiều lần. Lệnh duyệt bắt buộc phải
có tên người duyệt và câu duyệt nguyên văn — duyệt mà không để lại dấu vết thì sáu tháng
sau không ai biết ai đã đồng ý với cái gì.

## Cái máy dò kim loại không bắt được

Máy dò ở sân bay bắt được kim loại. Nó không bắt được ý định. Cổng tự động của xưởng nội
dung cũng vậy: bắt được hình thức, không bắt được *bài này có đáng đăng không*.

Câu hỏi đó cần một người biết chiến dịch đang nhắm ai, đã hứa gì với họ, và tuần trước đã
nói gì. Không có mô hình nào trả lời hộ được, vì câu trả lời không nằm trong bài.

## Góc nhìn thẳng

Cổng người **làm chậm**. Đó là thứ được chọn, không phải thứ phải chịu đựng. Nhưng nếu đo
sai thì sẽ bỏ nó: đừng đo bằng *số bài mỗi tuần*, hãy đo bằng *số bài phải gỡ hoặc sửa sau
khi đã đăng*. Xưởng này chưa chạy đủ lâu để có con số đó, nên bài này không nêu con số nào.

Ai hợp: người có thương hiệu để mất. Ai không hợp: người cần một trăm bài tuần này.

## Kết luận

Thứ làm nội dung dùng được không nằm ở chỗ mô hình viết hay hơn. **Không phải mô hình mạnh
hơn, mà là chỗ người đặt tay vào.**

Muốn xem hai cổng đó trông thế nào trong mã, xưởng này để mở — clone về và chạy một bài
tới bước đăng.

---

## post:youtube_desc

> Mô tả video YouTube. 2–3 dòng đầu là phần hiện trên preview — quan trọng nhất.
> 150–300 từ là đủ. Tối đa 3 hashtag.

Bài do AI viết nghe trôi chảy mà vẫn rỗng — và đi qua được mọi khâu kiểm tra tự động.
Video này chỉ ra hai chỗ trong quy trình nội dung với AI agent mà máy không nên tự quyết.

Mình dựng một xưởng nội dung chạy bằng agent với 23 cổng kiểm bằng số. Cổng bắt được link
gãy, chữ mẫu còn sót, tên công cụ lọt ra ngoài. Không cổng nào trả lời được câu "bài này
có đáng đăng không". Video đi qua đúng chỗ đó: vì sao chọn đề tài và duyệt trước khi đăng
phải là quyết định của người, và cái giá phải trả khi bỏ hai cổng ấy.

⏱️ Nội dung chính:
00:00 Một bài rỗng đi qua được mọi cổng
01:20 Ba trạng thái: xanh, đỏ, và "thiếu"
03:05 Chỗ thứ nhất máy không nên tự quyết: chọn đề tài
05:10 Chỗ thứ hai: duyệt trước khi đăng
07:30 Cổng người làm chậm — đo thế nào cho đúng

📖 Bản blog đầy đủ: {{BLOG_URL}}

👉 Đăng ký kênh nếu bạn đang đưa agent vào việc thật.

#AIAgent #QuyTrinhNoiDung #Data

---

## post:facebook_post

> Bản FULL cho feed, không phải teaser cụt. Facebook-native: **không markdown literal**,
> tiêu đề phụ dùng Unicode bold, ngắt bằng `———`, đoạn ngắn 2–4 câu.
> **Thân bài KHÔNG chứa URL nào.** Mọi link đi vào khối `### comment_1` bên dưới.

Một bài viết đi qua đủ 23 cổng kiểm tra tự động. Không link gãy, không thiếu nguồn,
không sai độ dài. Và nó vẫn không nên đăng. 🚀

———————
𝐂𝐨̂̉𝐧𝐠 𝐦𝐚́𝐲 𝐛𝐚̆́𝐭 đ𝐮̛𝐨̛̣𝐜 𝐠𝐢̀ 🧠
Bắt được hình thức: link chết, chữ mẫu còn sót, tên công cụ nội bộ lọt ra bản công khai.

Có một trạng thái thứ ba ít ai để ý: "thiếu" — cổng không chạy được. Nó không bao giờ
được tính là "xanh". Cổng không chạy được là chưa biết, không phải đã qua.

———————
𝐇𝐚𝐢 𝐜𝐡𝐨̂̃ 𝐦𝐚́𝐲 𝐤𝐡𝐨̂𝐧𝐠 𝐧𝐞̂𝐧 𝐭𝐮̛̣ 𝐪𝐮𝐲𝐞̂́𝐭
Chọn đề tài: viết về cái gì là quyết định chiến lược, không phải việc sinh chữ.

Duyệt trước khi đăng: chỗ cuối cùng còn sửa được rẻ. Sau khi đăng thì đắt hơn nhiều lần.

———————
Máy dò ở sân bay bắt được kim loại, không bắt được ý định.

Bản đầy đủ mình để ở comment.

#AIAgent #QuyTrinhNoiDung #Data #Marketing #NoiDung #DuLieu

### comment_1

> Comment ĐẦU TIÊN, đăng ngay sau post (≤60 giây). Đây là chỗ DUY NHẤT chứa link.
> Tách ra `facebook/comment.txt` ở bước B3. Thiếu khối này = bài chưa đăng xong.

Bản đầy đủ mình để ở đây nhé 👇

{{BLOG_URL}}

🎬 Xem video: {{YOUTUBE_URL}}

---

