# agent-marketing-studio

Engine điều hành và tự động hóa chiến dịch marketing đa kênh toàn diện bằng **Multi-Agent AI kết hợp với con người kiểm soát (Human-in-the-Loop)**.

---

## 1. Điểm Khác Biệt & Kiến Trúc Cốt Lõi

- **Markdown làm chủ trạng thái:** mỗi chiến dịch là **một file `campaign.md`** — brief ở
  đầu (frontmatter + Mục 1–10), bảng danh sách bài ở giữa (giữa marker
  `<!-- CONTENT:BEGIN/END -->`). Mỗi bài là một thư mục con. Không có định dạng nhị phân
  nào ở giữa bạn và dữ liệu: mở lên là đọc được, git chỉ ra đúng chữ đã đổi, và không ai
  khoá file của ai.
- **Excel là BẢN XUẤT, một chiều:** `export_excel.py` dựng `.xlsx` đúng bộ cột cũ để lọc,
  xoay, gửi cho người không dùng git. Sửa trong Excel **không** quay ngược về nguồn.
- **2 Cổng duyệt kiểm soát bởi con người:** AI tự động lập kế hoạch và sản xuất, nhưng con người giữ quyền quyết định ở 2 chốt chặn: duyệt ý tưởng (Cổng 1) và duyệt nội dung thành phẩm (Cổng 2).
- **Engine ở repo, nội dung ở TRẠM:** repo này chứa engine (script, cổng kiểm, quy trình,
  template). Nội dung thật sống ở một **trạm** nằm ngoài git — mặc định `~/.marketing`,
  nhưng chỗ nào là do bạn chọn. Kênh thậm chí không bắt buộc nằm trong trạm: `CHANNELS.md`
  là cạnh **duy nhất** được phép trỏ ra ngoài.
- **Chiến dịch chạy theo lịch, cùng một khuôn:** bản tin ngày/tuần và series tự động là
  chiến dịch như mọi chiến dịch khác — chỉ thêm `run.ps1` (điểm vào duy nhất, giống hệt nhau
  ở mọi chiến dịch) và khối `runtime:` trong `campaign.md`. `campaign_cfg.py` gộp bốn tầng
  cấu hình — `channel.yml:brand` → `brand.json` (nếu còn) → `brand.md` → `campaign.md` — thành
  một bản chụp JSON cho PowerShell 5.1 đọc, **fail-closed**: thiếu khoá bắt buộc thì dừng chứ
  không trả về JSON dở dang. Chi tiết: [`knowledge/toolchains/NEWS_PIPELINE.md`](knowledge/toolchains/NEWS_PIPELINE.md).
- **23 cổng kiểm bằng số, ba trạng thái:** xanh · đỏ · **thiếu**. Cổng không chạy được là
  *chưa biết*, **không bao giờ** được tính là *đã qua*.

---

## 2. Quy Trình 7 Khâu & 2 Cổng Duyệt

```
① new ─→ ② plan ─🔒 CỔNG 1 ─→ ③ produce ─→ ④ selfqa ─🔒 CỔNG 2 ─→ ⑤ render ─→ ⑥ publish ─→ ⑦ measure
```

1. **① new (Khởi tạo):** Lập hồ sơ chiến dịch từ brief của con người ([`workflows/01_new_campaign.md`](workflows/01_new_campaign.md)).
2. **② plan (Lập kế hoạch):** Đề xuất N ý tưởng content và từ khóa SEO ([`workflows/02_plan_content.md`](workflows/02_plan_content.md)).
   - 🔒 **CỔNG 1 — duyệt đề tài:** người đặt `status = approved` + ngày vào ô `g1` của bảng
     Content. Không có đường nào trong mã tự đặt giá trị này.
3. **③ produce (Sản xuất):** đọc chiến dịch + hồ sơ kênh + nghiên cứu của bài, rồi viết mọi
   kênh vào `content.md` ([`workflows/03_produce_content.md`](workflows/03_produce_content.md)).
4. **④ selfqa (Tự kiểm tra):** Máy tự kiểm định chất lượng, văn phong, quy chuẩn kênh ([`workflows/04_self_qa.md`](workflows/04_self_qa.md)).
   - 🔒 **CỔNG 2 — duyệt trước khi đăng:** `register_publish approve --by "<tên>"
     --note "<câu duyệt nguyên văn>"`. Bắt buộc cả hai — duyệt mà không để lại dấu vết thì
     sáu tháng sau không ai biết ai đã đồng ý với cái gì.
5. **⑤ render (Dựng Asset):** Tạo hình ảnh, audio lồng tiếng, short video ([`workflows/05_render_assets.md`](workflows/05_render_assets.md)).
6. **⑥ publish (Đăng bài):** YouTube → trang blog → Facebook, và URL thật ghi ngược vào
   bảng Content ([`workflows/06_publish.md`](workflows/06_publish.md)).
7. **⑦ measure (Đo lường):** ghi số vào `publish.json`, chốt số vào Mục 9 của `campaign.md`
   ([`workflows/07_measure.md`](workflows/07_measure.md)). Thu tự động qua API **chưa có** —
   hiện nhập tay.

---

## 3. Cấu Trúc Repository Chuẩn Hóa

### 3.1 Trạm nội dung — ba tầng lồng nhau

Kênh chứa chiến dịch, chiến dịch chứa bài. Mỗi tầng có **đúng một file giữ sự thật** của
tầng đó, và cả ba tầng đều là thư mục thật — mở ra là đọc được, không có cơ sở dữ liệu ở giữa.

```text
~/.marketing/                      # TRẠM (ngoài git — chỗ nào là do bạn chọn)
├── CHANNELS.md                    # sổ kênh: kênh nào ở đâu (cạnh DUY NHẤT trỏ ra ngoài)
├── AUTHOR.md                      # tác giả là ai — dùng chung mọi kênh
└── <kênh>/                        # ① MỘT KÊNH = một giọng, một tập người đọc
    ├── channel.yml                #   MÁY đọc: nền tảng · trụ nội dung · theme · brand · paths
    ├── brand.md                   #   NGƯỜI đọc: nhận diện · giọng · chính kiến · cái KHÔNG làm
    ├── CAMPAIGNS.md               #   sổ chiến dịch của kênh
    ├── continuity.json            #   sổ bài đã đăng — để khỏi trùng đề tài
    └── <chiến-dịch>/              # ② MỘT CHIẾN DỊCH
        ├── campaign.md            #   brief + bảng Content + khối `runtime:`
        ├── prompt.txt             #   prompt bước CHỌN đề tài (chạy mỗi kỳ)
        ├── run.ps1                #   [chạy theo lịch] điểm vào duy nhất
        ├── out/  logs/            #   sản phẩm & nhật ký RIÊNG của chiến dịch này
        └── <mã>_<slug>/           # ③ MỘT BÀI = một ý tưởng, nhiều bản đăng
            ├── prompt.txt         #   prompt bước VIẾT bài này
            ├── research.md        #   nguồn & ràng buộc — đóng băng ở đây
            ├── content.md         #   nội dung MỌI kênh, tách bằng `## post:<format>`
            └── publish.json       #   cổng 2 · URL thật · số đo
```

Ba lệnh dựng ba tầng, mỗi lệnh chép từ `templates/station/`:

```bash
python scripts/pipeline/new_channel.py  --id <kênh> --label "…" --path ./<kênh>
python scripts/pipeline/new_campaign.py --channel <kênh> --id <slug> --name "…" --prefix XXX
python scripts/pipeline/new_post.py     --campaign <slug> --id XXX-001 --slug … --title "…"
python scripts/pipeline/check_tree.py   --station ~/.marketing      # soi lại cây thật
```

**Ba loại file, ba vai — đừng trộn:** `.yml` cho **máy**, `.md` cho **người**, `.txt` cho
**model**. Một file vừa là cấu hình vừa là tài liệu thì sửa câu chữ cũng phải sợ làm hỏng máy.

### 3.2 Repo — engine và khuôn

```text
agent-marketing-studio/
├── AGENTS.md                  # Quy chuẩn quản trị đa tác nhân (Governance)
├── MAP.md                     # Bản đồ định tuyến context nhiệm vụ (Context Router)
├── README.md                  # Hướng dẫn tổng quan hệ thống
├── CONTRIBUTING.md            # Quy ước phát triển và đóng góp
├── SECURITY.md                # Chính sách bảo mật token và dữ liệu
├── install.ps1                # Dựng trạm: hỏi 1 câu rồi in ra ba lệnh tiếp theo
├── .agents/                   # Tầng quản trị Agent (Roles, Skills, Checklists, Prompts)
├── scripts/
│   ├── lib/                   # md_io (đọc/ghi Markdown nguyên tử) · studio_paths · post_paths
│   └── pipeline/              # new_channel · new_campaign · new_post · gen_article
│                              # campaign_cfg (gộp cấu hình → JSON cho PowerShell)
│                              # blog_gates · register_publish · check_tree · build_views · export_excel
├── tests/                     # 197 test — chạy `pytest tests/ -q`
├── knowledge/                 # Kho tri thức marketing (Data Model, Playbooks, Toolchains)
├── output_styles/             # Giọng văn thương hiệu chuẩn theo từng kênh
├── templates/
│   ├── README.md              # khuôn nào dùng khi nào
│   └── station/               # CÂY MẪU lồng đúng như trạm thật:
│                              #   _channel/ → _campaign/ → _content/
├── workflows/                 # Đặc tả chi tiết 7 khâu vận hành
├── examples/                  # TRẠM MẪU đã điền — 1 kênh, 1 chiến dịch, 3 bài ở 3 trạng thái
└── content/                   # Bộ dữ liệu mô phỏng dùng cho dạy học (KPIM)
```

---

## 4. Tài Liệu Quan Trọng

- 📖 **Mô hình Dữ liệu 75 trường:** [`knowledge/data_model/DATA_MODEL.md`](knowledge/data_model/DATA_MODEL.md)
- 🗺️ **Bản đồ nhiệm vụ cho Agent:** [`MAP.md`](MAP.md)
- 🎯 **Quy trình tổng thể:** [`workflows/00_WORKFLOW_INDEX.md`](workflows/00_WORKFLOW_INDEX.md)
- ✍️ **Bộ quy chuẩn giọng văn:** [`output_styles/`](output_styles/)
- 🔍 **Trạm mẫu đã điền:** [`examples/`](examples/) — đọc `examples/README.md` trước.
- ⏱️ **Chiến dịch chạy theo lịch:** [`knowledge/toolchains/NEWS_PIPELINE.md`](knowledge/toolchains/NEWS_PIPELINE.md)
- 🧱 **Khuôn dựng kênh/chiến dịch/bài:** [`templates/README.md`](templates/README.md)
- 📊 **Bộ dữ liệu mô phỏng (dạy học):** `content/KPIM/02_campaigns/01_Tobi_Posts/`
