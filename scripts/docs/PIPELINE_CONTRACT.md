# tobi_post / create_campaign — PIPELINE CONTRACT v3 (CLI + schema — mọi script/agent PHẢI tuân thủ)

> v3 (2026-06-21): chuyển sang mô hình **mỗi campaign = 1 folder + 1 Excel riêng** (instantiate từ template). Đổi tên file, thêm sheet Engagement, thêm 4 command. Đọc kèm `DELIVERABLES.md`.

## Đường dẫn (Windows)
- SCRIPTS     = `DOCS\agent\scripts`  ← MỌI .py + run-tobi-post.ps1 + publish-tobi.ps1 + prompts\ + PIPELINE_CONTRACT.md/DELIVERABLES.md/README.md sống Ở ĐÂY (OneDrive-sync)
- RUNTIME     = `C:\Users\DucNguyen\.video\tobi`  ← CHỈ secret + runtime state: `facebook_config.json`, `.sidecars\`, `logs\`, `.tmp\` (gitignored, KHÔNG sync OneDrive). Scripts trỏ qua biến `$RUNTIME`.
- DOCS        = `$env:MARKETING_STUDIO_DATA (mac dinh ~/.marketing)`
- TEMPLATES   = `DOCS\agent\templates`        ← chứa CAMPAIGN_TEMPLATE.md + CAMPAIGN_TRACKING_TEMPLATE.xlsx
- CAMPAIGNS   = `DOCS\31_CAMPAIGNS\01_CAMPAIGNS`  ← mỗi campaign 1 folder `NN_Ten_Campaign` (mẫu CHUẨN = `02_VibeCoding_NonTech`)
- ASSET_ROOT  = `DOCS\32_PUBLIC_CONTENT\01_ACADEMIC_BLOG`  ← asset bài viết (giữ nguyên, đóng gói theo bài)
- ATLAS       = `C:\Users\DucNguyen\Code\ducnguyen221.github.io\atlas`
- OMNI        = `C:\Users\DucNguyen\.tts\omnivoice`  (venv TTS cho make_podcast.py)
- PY          = `C:\Users\DucNguyen\AppData\Local\Programs\Python\Python312\python.exe`

### Mỗi campaign 1 folder: `CAMPAIGNS\NN_Ten_Campaign\`
```
NN_Ten_Campaign\
├── NN_Ten_Campaign.md      ← từ CAMPAIGN_TEMPLATE.md, ĐÃ điền đủ; là HỒ SƠ chiến dịch:
│                             thông tin do user+AI xây + lịch sử bài đã chốt + lịch sử đăng
│                             + toàn bộ metadata nghiệp vụ + báo cáo AI (append theo thời gian)
└── NN_Ten_Campaign.xlsx    ← từ CAMPAIGN_TRACKING_TEMPLATE.xlsx, dữ liệu thực thi (5 sheet)
```
Asset từng bài ở `ASSET_ROOT\<topic_group>\<post_id>_<slug>\` — **KHÔNG còn .docx, tất cả markdown/txt**:
`content.md` (instance điền từ CONTENT_TEMPLATE: tư duy prompt + phân tích yếu tố + blog chi tiết + FB post chi tiết), `blog.md`, `fb_post.txt`, `youtube_desc.txt`, `fb_desc.txt`, `infographic.png`, `audio.mp3`, `video.mp4`, `atlas.html`, `meta.json`.
topic_group ∈ {01_powerbi,02_fabric,03_ai-agent,04_career}. category atlas: powerbi→bi, fabric→de, ai-agent→ai, career→strategy.

## EXCEL per-campaign — 5 sheet
- **Campaign** (Sheet1) = **FORM dọc key→value** (KHÔNG phải bảng): các hàng metadata nghiệp vụ:
  `campaign_id, campaign_code, name, pillar, status, owner, created, objective, description, target_audience, key_message, channels, cadence, schedule_start, schedule_end, num_posts_planned, kpi_targets, prompt_requirements, ai_summary, notes`
  (cột A = field, cột B = value; có chú thích gợi ý điền.)
- **Post** (bảng): `post_id,campaign_id,topic_title,angle,pillar,topic_group,slug,detail_prompt,schedule_date,approve_topic,content_md,blog_md,fb_post,youtube_desc,fb_desc,approve_content,make_short,infographic_png,audio_mp3,video_mp4,atlas_html,approve_final,status,folder_path,notes`  (md/txt, KHÔNG docx)
  - **`make_short`** = "Có short video" (OPTIONAL): tick `x` → stage media dựng thêm `video-short.mp4`; để trống → BỎ QUA short. Short luôn **hỏi xác nhận** trước khi dựng (chỉ làm khi make_short tick HOẶC user duyệt tại runtime).
- **Result** (bảng): `post_id,blog_url,youtube_url,fb_post_id,fb_permalink,fb_scheduled_at,published_at,status`
- **Engagement** (bảng — NEW): `post_id,fb_post_id,fb_permalink,likes,comments,reactions,shares,reach,impressions,fetched_at`
- **Assets** (bảng): `post_id,asset_type,rel_path,abs_path,size,created`
- approve_* truthy = `x/X/TRUE/✓`. status Post: `proposed→drafted→media_ready→atlas_ready→published`.

## CLI — tobi_excel.py (CLI + import; in JSON ra stdout; --path = Excel của campaign)
```
PY tobi_excel.py init-template   --path TEMPLATES\CAMPAIGN_TRACKING_TEMPLATE.xlsx   # tạo file template 5 sheet (Campaign form trống + header các bảng)
PY tobi_excel.py new-campaign    --template TEMPLATES\CAMPAIGN_TRACKING_TEMPLATE.xlsx --out <campaign.xlsx> --meta <campaign_meta.json>  # copy template + đổ Sheet Campaign từ json
PY tobi_excel.py set-campaign    --path <campaign.xlsx> --field F --value V          # set 1 field form Campaign
PY tobi_excel.py get-campaign    --path <campaign.xlsx>                              # in JSON toàn bộ form Campaign
PY tobi_excel.py list            --path <campaign.xlsx> --stage <draft|media|atlas|publish>
PY tobi_excel.py upsert          --path <campaign.xlsx> --json <post_row.json>
PY tobi_excel.py set             --path <campaign.xlsx> --post-id ID --field F --value V
PY tobi_excel.py result          --path <campaign.xlsx> --post-id ID --json <result.json>
PY tobi_excel.py add-asset       --path <campaign.xlsx> --post-id ID --type T --rel-path R --abs-path A
PY tobi_excel.py upsert-engagement --path <campaign.xlsx> --json <eng_row.json>      # ghi/cập nhật 1 hàng sheet Engagement (key=post_id)
```
Gating `list`: draft=approve_topic&status=proposed · media=approve_content&status=drafted · atlas=status=media_ready · publish=approve_final&status∈{atlas_ready,media_ready}

## CLI — gen/build (nhận meta.json bài + ghi vào folder bài)
```
PY gen_article.py     --content-md F --meta meta.json --out-dir FOLDER   # tách content.md -> blog.md + fb_post.txt + youtube_desc.txt + fb_desc.txt
PY gen_infographic.py --meta meta.json --blog-md F --out FOLDER\thumbnail.png   # COVER Inter/news-style (1280x720)
PY make_podcast.py    --script F --meta meta.json --out FOLDER\audio.mp3 --profile my-voice   # [OVPY venv]
PY make_podcast_video.py --audio FOLDER\audio.mp3 --scenes FOLDER\scenes.json --meta meta.json --out FOLDER\video.mp4 [--size 1280x720|1080x1920]
PY build_blog_html.py --blog-md F --meta meta.json --infographic FOLDER\thumbnail.png --out FOLDER\atlas.html
```
Mọi script in dòng cuối `OK <abs_path>`; exit!=0 khi lỗi.
**Stage draft**: claude điền CONTENT_TEMPLATE → `content.md`; gen_article tách. **Stage media (style hiện tại)**: gen_infographic→thumbnail.png(cover) · claude `podcast-script-prompt.txt`(MODE=full|short, VĂN NÓI)→podcast.txt→make_podcast(OVPY venv OmniVoice)→audio.mp3 (podcast văn nói) · claude `scenes-gen-prompt.txt`→scenes.json (xen ẢNH Openverse + INFOGRAPHIC, xfade) → make_podcast_video→video.mp4 · SHORT chỉ khi `make_short` tick. **DEAD — KHÔNG còn dùng trong pipeline: `top_story_video.py` + `blog_to_topjson.py` (đã xóa).** **Publish**: YouTube `--desc-file youtube_desc.txt` --thumbnail thumbnail.png; FB message = fb_post.txt + chèn blog_url.

## CLI — fb_engagement.py (NEW) + campaign_report.py (NEW)
```
PY fb_engagement.py   --campaign-xlsx <campaign.xlsx> --fb-config C:\Users\DucNguyen\.video\tobi\facebook_config.json
   # đọc sheet Result -> mỗi fb_post_id GET graph v21.0 ?fields=permalink_url,shares,likes.summary(true),comments.summary(true),reactions.summary(true)
   # reach/impressions: thử /{id}/insights (best-effort, bỏ qua nếu lỗi) -> upsert sheet Engagement
PY campaign_report.py --campaign-dir <CAMPAIGNS\NN_Ten> [--refresh-engagement]
   # (tùy chọn) gọi fb_engagement trước -> tổng hợp Post+Result+Engagement -> in báo cáo + APPEND mục "## Báo cáo <ngày>" vào NN_Ten.md
```
FB Graph: base `https://graph.facebook.com/v21.0`, version giống post_facebook.py. Engagement cơ bản ĐÃ verify lấy được; insights cần read_insights (best-effort). KHÔNG in token ra log.

## COMMANDS (.md ở DOCS\agent\commands\)
- **create_campaign.md** (đổi tên từ tobi_post.md; alias "start_campaign"): quy trình từ đầu→cuối:
  1) user mô tả + yêu cầu campaign → AI hỏi làm rõ (interactive) →
  2) chốt → điền đủ `CAMPAIGN_TEMPLATE.md` → tạo folder `CAMPAIGNS\NN_Ten` + đặt file `NN_Ten.md` →
  3) `tobi_excel.py new-campaign` tạo `NN_Ten.xlsx` + đổ Sheet Campaign (form) → finalize →
  4) triển khai bài: sinh topic → điền sheet Post → cổng duyệt → bài approve chạy pipeline content (draft→media→atlas→publish).
- **campaign.md** (NEW): arg = tên/mã campaign → AI tìm folder `CAMPAIGNS\NN_*`, đọc `.md`+`.xlsx`, BÁO CÁO hiện trạng + nạp context, rồi LOOP xử lý mọi item đã approve nhưng chưa làm (chạy stage kế tiếp tương ứng).
- **report_campaign.md** (NEW): arg = tên campaign → gọi `campaign_report.py --refresh-engagement` → update chỉ số + báo cáo status + kết quả từng bài; append báo cáo vào `.md`.
- **scan_engagement.md** (NEW): arg = tên campaign → gọi `fb_engagement.py` → quét FB, đổ sheet Engagement (không báo cáo dài; chỉ pull data).

## Orchestrator (đổi để nhận campaign)
```
run-tobi-post.ps1 -Campaign <NN_Ten|code> -Stage <topics|draft|media|atlas|publish> [-Uat]
publish-tobi.ps1  -Campaign <NN_Ten> -PostId ID [-Uat]
```
- Resolve campaign folder: tìm `CAMPAIGNS\<NN_Ten>` (hoặc match theo campaign_code trong Sheet Campaign). EXCEL = `<folder>\<NN_Ten>.xlsx`.
- publish ghi `fb_post_id` + `fb_permalink` vào Result (để engagement match sau).
- Thứ tự publish: Atlas→YouTube→FB; sidecar `.sidecars\<post_id>.json` idempotent; `-Uat` dry-run.
- **CONTINUITY**: stage topics/draft bơm `{{PRIOR_POSTS}}` = `register_post.py --list` (tóm tắt+key-terms+ref các bài đã chốt ở Mục 12) → bài mới LIÊN KẾT mạch + TRÁNH lặp thuật ngữ. Sau publish: `register_post.py` ghi Mục 12 (tóm tắt + key-terms trích từ content.md mục 7 `Tóm tắt:`/`Key-terms:` + **cột Hồ sơ refer tới content.md/blog.md**) + RÀ SOÁT content.md/blog.md (audit độ dày). FB/social PHẢI có CẢ blog_url + youtube_url. Content sâu: key-term + framework + quy trình + use-case DOANH NGHIỆP THẬT (WebSearch nguồn uy tín, có dẫn nguồn). Blog 2.500-4.000 từ, podcast 750-1000 từ.
- **GUARDRAIL (publish-tobi.ps1)**: (0) đầu publish gọi `prepublish_check.py --mode assets` LIỆT KÊ + chặn nếu thiếu asset bắt buộc (blog.md/fb_post.txt/youtube_desc.txt/thumbnail.png/video.mp4/atlas.html/meta.json). (2b) SAU Atlas+YouTube: ghi `blog_url`+`youtube_url` vào Excel Result + `register_links.py` ghi vào hồ sơ md (Mục 13) → `prepublish_check.py --mode links` CHẶN: phải đủ blog_url+youtube_url MỚI cho đăng Facebook (FB cần đủ link). (4) sau FB ghi `fb_permalink` vào Result + md. → `prepublish_check.py`, `register_links.py` (NEW, PY hệ thống).
- `git add` CHỈ `content/<cat>/<slug>.html data/manifest.json` (KHÔNG -A). Registry: `DOCS\31_CAMPAIGNS\31.02_campaign_registry.md`.

## REFERENCE FILES sau tái cấu trúc — mọi script/doc trỏ tên CHUẨN (có prefix `31.0x`)
- `31_CAMPAIGNS\31.01_mission_okr.md` · `31_CAMPAIGNS\31.02_campaign_registry.md` · `31_CAMPAIGNS\31.03_seo_playbook.md`. (Folder con campaign trong `01_CAMPAIGNS\` giữ `NN_Ten` KHÔNG prefix 31: `01_Tobi_Posts`, `02_VibeCoding_NonTech`.)
- 5 file ĐÃ GỘP vào `agent\templates\CAMPAIGN_TEMPLATE.md` rồi XÓA: content_pillars, distribution_playbook, asset_registry, channel_perf, content_calendar. → Mọi tham chiếu "content_pillars/pillars" giờ trỏ CAMPAIGN_TEMPLATE (hoặc Sheet Campaign của campaign cụ thể).
- Templates: `CAMPAIGN_TEMPLATE.md` (gộp CAMPAIGN_BRIEF_TEMPLATE — đã xóa brief) + `CONTENT_TEMPLATE.md` (← CONTENT_BRIEF_TEMPLATE) + `CAMPAIGN_TRACKING_TEMPLATE.xlsx`.
- Style đa kênh: `agent\output-styles\multichannel-style.md` (YouTube desc + Facebook + X) — tóm tắt + link trong `31.03_seo_playbook.md`. Giọng blog `compa-class-blog.md`, FB `tobi-post.md` giữ nguyên.

## Tái dùng (đọc interface, đừng viết lại)
`.news\engine\{youtube_upload.py,post_facebook.py,append_excel_log.py}` · `OMNI\mcp_server.py` (TTS) · atlas `content\ai\databricks-genai.html`+`scripts\generate-manifest.js` · orchestration mẫu `.news\engine\{run-toptoday-hot.ps1,publish-hot-news.ps1}`.
.ps1 = UTF-8 BOM; KHÔNG `2>&1`/Stop trên node/claude stderr; fail-fast `$LASTEXITCODE`.

## INTERPRETER (QUAN TRỌNG)
- Script thường (tobi_excel, gen_article, gen_infographic, make_podcast_video, build_blog_html, fb_engagement, campaign_report, update_registry) → **PY hệ thống** `…Python312\python.exe`.
- **TTS/Audio** (make_podcast.py) → **VENV OmniVoice** `C:\Users\DucNguyen\.tts\omnivoice\.venv\Scripts\python.exe` (`$OVPY`). Chạy bằng PY hệ thống sẽ lỗi `ModuleNotFoundError: soundfile`. Orchestrator dùng `Invoke-Py -Exe $OVPY` cho bước này. (make_podcast_video chỉ ghép ảnh+audio bằng ffmpeg → PY hệ thống.)
- gen_infographic = COVER landscape 1280×720 kiểu hero compaclass (gradient xanh→teal, network/shape trừu tượng, tiêu đề+subtitle, KHÔNG list số).
```
