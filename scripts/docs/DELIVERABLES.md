# tobi_post — BẢN KÊ DELIVERABLE v2 (duyệt trước khi build)

> Pipeline auto content COMPA / "Học cùng Tobi": Campaign → Topic → Blog+Post → Infographic+MP3+MP4 → Atlas HTML → Publish YouTube+FB. Excel làm chủ + duyệt từng bước. Subagent kết hợp.
> v3 = học giọng từ bài thật → blog xuất **.md** (KHÔNG Word), **đóng gói asset theo folder bài** dưới `32_PUBLIC_CONTENT`; mỗi campaign = 1 folder + 1 Excel + 1 md riêng.

---

## 0. ĐÃ XONG (nền tảng giọng văn)
- ✅ `30_MARKETING\agent\output-styles\compa-class-blog.md` — style blog (rút từ 5 blog thật).
- ✅ `30_MARKETING\agent\output-styles\tobi-post.md` — style FB post (rút từ 5 FB post thật).

---

## 1. SƠ ĐỒ LƯU TRỮ — 3 vùng

```
A) CODE (OneDrive-sync) ───────────────────────────────────
DOCS\agent\scripts\          (= …\30_MARKETING\agent\scripts\)
├── run-tobi-post.ps1        orchestrator 5 stage, scan Excel → làm bước đã duyệt
├── publish-tobi.ps1         publish: Atlas→YouTube→FB (đúng thứ tự)
├── tobi_excel.py            đọc/ghi Excel 5 sheet + cột duyệt + ánh xạ path asset
├── gen_article.py           tách content.md (CONTENT_TEMPLATE) → blog.md + fb_post.txt + youtube_desc.txt + fb_desc.txt
├── gen_infographic.py       dựng HTML cover → render thumbnail.png (Chrome headless + Pillow)
├── make_podcast.py          podcast script → audio.mp3 (OmniVoice my-voice, venv)
├── make_podcast_video.py    audio.mp3 + scenes.json → video.mp4 (ảnh Openverse + infographic + xfade)
├── build_blog_html.py       blog.md + thumbnail → Atlas self-contained HTML
├── prompts\{topic-gen,content-write,podcast-script,scenes-gen}-prompt.txt
├── PIPELINE_CONTRACT.md · DELIVERABLES.md · README.md
└── (fb_engagement.py, campaign_report.py, register_post.py, register_links.py, prepublish_check.py, update_registry.py …)

A2) SECRET + RUNTIME STATE (gitignored, KHÔNG sync OneDrive) ─
~\.video\tobi\          ← scripts trỏ qua biến $RUNTIME
├── facebook_config.json     (USER setup 1 lần — token Page)
├── .sidecars\<post_id>.json idempotent state
├── logs\
└── .tmp\

B) TRI THỨC + DỮ LIỆU DUYỆT ───────────────────────────────
~\KPIM…\30_MARKETING\
├── agent\output-styles\compa-class-blog.md   ✅ (blog style)
├── agent\output-styles\tobi-post.md          ✅ (FB style)
├── agent\commands\{create_campaign,campaign,report_campaign,scan_engagement}.md  4 command pipeline
├── agent\knowledge\KNOWLEDGE_MAP.md          bản đồ tri thức (agent lấy đâu)
├── agent\skills\tobi-content-pipeline\SKILL.md   contract end-to-end
├── agent\scripts\                            ★ SCRIPTS quy trình (.py/.ps1/prompts/CONTRACT)
├── 31_CAMPAIGNS\01_CAMPAIGNS\<NN_Ten>\<NN_Ten>.xlsx  ★ EXCEL mỗi campaign (5 sheet)
├── agent\templates\{CAMPAIGN_TEMPLATE,CONTENT_TEMPLATE}.md + CAMPAIGN_TRACKING_TEMPLATE.xlsx
└── 32_PUBLIC_CONTENT\01_ACADEMIC_BLOG\        ★ ASSET ĐÓNG GÓI THEO BÀI
    └── <nhóm-chủ-đề>\                          (vd 03_ai-agent)
        └── <post_id>_<slug>\                   (post_id = mã trong Excel)
            ├── content.md         ← instance CONTENT_TEMPLATE (mục 1-7): tư duy + phân tích + blog + FB post + 2 desc
            ├── blog.md            ← tách từ content.md mục 3 (markdown bài blog)
            ├── fb_post.txt        ← tách từ content.md mục 4 (bài FB FB-native)
            ├── youtube_desc.txt   ← tách từ content.md mục 5 (mô tả YouTube)
            ├── fb_desc.txt        ← tách từ content.md mục 6 (caption ngắn / reel)
            ├── thumbnail.png      ← cover landscape (gen_infographic)
            ├── audio.mp3          ← podcast văn nói (make_podcast, giọng clone)
            ├── scenes.json        ← kịch bản cảnh (ảnh Openverse + infographic) cho make_podcast_video
            ├── video.mp4          ← podcast video (make_podcast_video: ảnh + audio + xfade)
            ├── atlas.html         ← bản HTML đã build (copy đẩy lên atlas)
            └── meta.json          ← title, slug, pillar, category, urls

C) PUBLISHED ──────────────────────────────────────────────
~\Code\atlas\content\<category>\<slug>.html   → live ducnguyen.vn
```

**Nguyên tắc:** mọi asset 1 bài nằm GỌN trong 1 folder `<post_id>_<slug>`. Excel ánh xạ tới asset bằng **đường dẫn tương đối từ root** `32_PUBLIC_CONTENT\01_ACADEMIC_BLOG\…`.

### Nhóm chủ đề (theo pillar — folder con của 01_ACADEMIC_BLOG)
`01_powerbi` · `02_fabric` · `03_ai-agent` · `04_career` (khớp 4 content pillar). Thêm nhóm series mới khi cần.

---

## 2. EXCEL — mỗi campaign 1 file riêng (5 sheet)

> Mô hình v3: **KHÔNG còn 1 Excel chủ chung**. Mỗi campaign instantiate từ `agent\templates\CAMPAIGN_TRACKING_TEMPLATE.xlsx` → `31_CAMPAIGNS\01_CAMPAIGNS\<NN_Ten>\<NN_Ten>.xlsx`. Thứ tự sheet: **Campaign · Post · Result · Engagement · Assets**. Định nghĩa cột canonical ở `agent\scripts\tobi_excel.py`.

### Sheet `Campaign` — FORM DỌC (cột A=field, B=value, C=gợi ý điền; KHÔNG phải bảng)
`campaign_id · campaign_code · name · pillar · status(proposed→active→paused→done) · owner · created · objective · description · target_audience · key_message · channels · cadence · schedule_start · schedule_end · num_posts_planned · kpi_targets · prompt_requirements · ai_summary · notes`

### Sheet `Post` — từng bài (★ nơi tick duyệt)
| Nhóm cột | Cột |
|---|---|
| Định danh | `post_id` (=mã folder) · `campaign_id` · `topic_title` · `angle` · `pillar` · `topic_group` · `slug` |
| Brief | `detail_prompt` · `schedule_date` |
| **Duyệt 1** | **`approve_topic`** → cho viết bài |
| Nội dung (path) | `content_md` · `blog_md` · `fb_post` · `youtube_desc` · `fb_desc` |
| **Duyệt 2** | **`approve_content`** → cho làm media |
| Short (optional) | **`make_short`** — tick `x` để dựng video-short; trống = bỏ qua (**luôn hỏi xác nhận** trước khi dựng short) |
| Media (path) | `infographic_png` (giữ tên cột; chứa path **thumbnail.png**) · `audio_mp3` · `video_mp4` · `atlas_html` |
| **Duyệt 3** | **`approve_final`** → cho publish |
| Trạng thái | `status` (proposed→drafted→media_ready→atlas_ready→published) · `folder_path` · `notes` |

### Sheet `Result` — sau publish
`post_id · blog_url · youtube_url · fb_post_id · fb_permalink · fb_scheduled_at · published_at · status`

### Sheet `Engagement` — chỉ số FB (lệnh `scan_engagement`, Graph API v21.0)
`post_id · fb_post_id · fb_permalink · likes · comments · reactions · shares · reach · impressions · fetched_at`

### Sheet `Assets` — bản kê path
`post_id · asset_type · rel_path · abs_path · size · created` (gen_*.py tự append).

> Duyệt **2 cách**: tick cột `approve_*` (x/TRUE) trong Excel, hoặc lệnh chat. Agent scan Excel → chỉ chạy bước đã được duyệt.

---

## 3. CÁC FILE .MD — nội dung + vị trí

| File | Lưu | Nội dung |
|------|-----|----------|
| `compa-class-blog.md` ✅ | output-styles | VOICE PROFILE blog + cấu trúc 6 phần + callout + câu chốt + checklist |
| `tobi-post.md` ✅ | output-styles | VOICE PROFILE FB + Unicode bold + hashtag + hook/chốt thật + checklist |
| `create_campaign.md` (+ campaign / report_campaign / scan_engagement) | agent\commands | Định nghĩa command pipeline: 5 stage, cách gọi script ở `agent\scripts`, xử lý duyệt Excel+chat, bản đồ file |
| `knowledge\KNOWLEDGE_MAP.md` | agent\knowledge | Bản đồ tri thức: voice→2 style file, pillar→content_pillars, góc nhìn→tobi-viewpoint, chuyên môn→00_AI_BRAIN\06_KNOWLEDGE |
| `tobi-content-pipeline\SKILL.md` | agent\skills | Contract end-to-end: input/output mỗi stage, điều kiện cổng duyệt, format md/PNG/MP3/MP4/HTML, continuity + guardrail + lịch giờ |
| `CAMPAIGN_TEMPLATE.md` / `CONTENT_TEMPLATE.md` | agent\templates | Template campaign (lịch đăng + prompt + pillar + cadence) + template content mỗi bài |

---

## 4. SCRIPT — chức năng + I/O + tái dùng

| Script | Làm gì | Tái dùng |
|--------|--------|----------|
| `run-tobi-post.ps1` | Orchestrator. `-Stage topics\|draft\|media\|atlas\|publish` `-Campaign <id>` `-Uat`. Scan Excel, chạy đúng bước đã duyệt. Gọi claude headless cho stage cần sinh nội dung (subagent). | mirror `run-toptoday-hot.ps1` |
| `tobi_excel.py` | CRUD Excel **5 sheet** (Campaign form + Post/Result/Engagement/Assets), đọc cờ duyệt, ghi path asset, retry khi OneDrive khoá | pattern `append_excel_log.py` |
| `gen_article.py` | tách **content.md** (instance CONTENT_TEMPLATE) → **blog.md + fb_post.txt + youtube_desc.txt + fb_desc.txt** (parse heading mục 3-6; KHÔNG còn .docx) | stdlib |
| `gen_infographic.py` | dựng HTML cover on-brand → **thumbnail.png** (1280×720) | Chrome headless `.video` + Pillow |
| `make_podcast.py` | podcast script (văn nói) → **audio.mp3** my-voice | OmniVoice venv |
| `make_podcast_video.py` | audio.mp3 + **scenes.json** → **video.mp4** (ảnh Openverse + infographic + xfade) | ffmpeg (`.video`) |
| `build_blog_html.py` | blog.md + thumbnail → **Atlas self-contained HTML** (dark theme, theo `content/ai/databricks-genai.html`) | atlas template |
| `publish-tobi.ps1` | (1) atlas.html→`content\<cat>\`→`generate-manifest.js`→git push→**blog_url**; (2) YouTube upload mp4 (playlist "Học cùng Tobi") `--desc-file youtube_desc.txt`→**youtube_url**; (3) `post_facebook.py` message=`fb_post.txt`+blog+YT link → hẹn lịch (reel kèm `fb_desc.txt` nếu có short); (4) ghi Result. Sidecar idempotent. | youtube_upload + post_facebook |

---

## 5. LUỒNG 5 STAGE + SUBAGENT + CỔNG DUYỆT

```
[A] topics  → subagent research+pillar sinh chủ đề → Post tab (proposed)
                         │ approve_topic ✔
[B] draft   → subagent writer điền instance CONTENT_TEMPLATE → content.md
              → gen_article.py tách → blog.md + fb_post.txt + youtube_desc.txt + fb_desc.txt → drafted
                         │ approve_content ✔
[C] media   → gen_infographic(thumbnail.png) + make_podcast(audio.mp3) + make_podcast_video(scenes.json→video.mp4)
              → đóng gói vào folder bài → media_ready   (short video CHỈ khi cột make_short=x, luôn hỏi xác nhận)
                         │ (atlas build tự động, vẫn chờ approve_final)
[D] atlas   → build_blog_html → atlas.html (embed YouTube+mp3) trong folder bài (CHƯA push)
                         │ approve_final ✔
[E] publish → prepublish_check (guardrail asset+link) → atlas push (blog_url /atlas/) → YouTube (release 19:00, title "Bài N:")
              → FB hẹn 20:00 (đủ blog_url+youtube_url) → Result + register_links(Mục13)/register_post(Mục12) + BACKFILL report → published
```
Subagent: mỗi stage sinh nội dung chạy bằng `claude -p` allowlisted (Read/WebSearch/Write) — tách context, làm đúng style file.

---

## 6. USER SETUP 1 LẦN
1. **FB Page "Tobi Nguyễn"** → `facebook_config.json` (token Page, không paste chat).
2. **YouTube** reuse `.news\ai\youtube_token.json`; playlist "Học cùng Tobi" auto.
3. **Atlas** xác nhận quyền `git push`.
4. `my-voice` profile — có ✓. Pillow/Chrome/ffmpeg (Gyan) — có ✓.

---

## 7. VERIFY (chưa publish thật)
Parse-check .ps1 (UTF-8 BOM) + `import ast` mọi .py → tạo campaign mẫu → `-Stage topics` kiểm Post tab → tick approve_topic → `-Stage draft` mở content.md + blog.md/fb_post.txt/youtube_desc.txt/fb_desc.txt → tick approve_content → `-Stage media` xem PNG+mp3+mp4 trong folder bài → `-Stage atlas` preview HTML → `publish-tobi.ps1 -Uat` (dry-run) xác nhận thứ tự + link FB chứa 2 URL.

## 8. OUT OF SCOPE
Kênh/Page COMPA riêng · analytics tự động · web COMPA riêng.
```
