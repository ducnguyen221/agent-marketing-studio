# MAP.md — Task-Based Context Routing Map for agent-marketing-team

> **Mục đích:** Hướng dẫn tác nhân AI Agent và người điều phối nạp ĐÚNG tài liệu cần thiết cho từng loại nhiệm vụ cụ thể, triệt tiêu tình trạng đọc lan man gây tràn Context Window.

---

## 1. Bản Đồ Định Tuyến Theo 7 Khâu Vận Hành

| Khâu / Nhiệm Vụ | Điểm Bắt Đầu | Tài Liệu Cần Đọc Tiếp | Tài Liệu Tuyệt Đối KHÔNG Đọc |
|---|---|---|---|
| **① Khởi tạo Chiến dịch (new)** | `workflows/01_new_campaign.md` | • `.agents/skills/marketing-routing/SKILL.md` nếu chưa rõ hướng<br>• `.agents/skills/campaign-pipeline/SKILL.md`<br>• `templates/station/_channel/_campaign/campaign.md`<br>• `knowledge/data_model/DATA_MODEL.md` (Strategic Brief) | • `output_styles/*`<br>• Playbook không liên quan tới quyết định hiện tại |
| **② Lập Kế hoạch Content (plan)** | `workflows/02_plan_content.md` | • `knowledge/playbooks/SEO_PLAYBOOK.md`<br>• `knowledge/playbooks/COPY_FRAMEWORKS.md`<br>• frontmatter `campaign.md` của chiến dịch<br>• `continuity.json` của kênh (tránh trùng đề tài) | • `knowledge/toolchains/*`<br>• `output_styles/*` (chưa cần ở bước ý tưởng) |
| **③ Viết Bài Đa Kênh (produce)** | `workflows/03_produce_content.md` | **Bắt buộc cả ba:**<br>• `campaign.md` của chiến dịch<br>• `brand.md` ở gốc kênh (fail-closed)<br>• `research.md` của chính bài<br>Rồi: `output_styles/<brand_style>.md` · `.agents/skills/hook-writer/SKILL.md` | • `workflows/06_publish.md`<br>• `knowledge/toolchains/PLATFORM_SETUP.md` |
| **④ Máy Tự Kiểm Tra (selfqa)** | `workflows/04_self_qa.md` | • `.agents/checklists/QA_ASSET.md`<br>• `output_styles/<brand_style>.md` | • `templates/*`<br>• `knowledge/toolchains/*` |
| **⑤ Dựng Asset Hình/Tiếng (render)**| `workflows/05_render_assets.md` | • `knowledge/toolchains/ASSET_TOOLCHAIN.md` | • `output_styles/*`<br>• `knowledge/playbooks/*` |
| **⑥ Đăng Bài & Hẹn Giờ (publish)** | `workflows/06_publish.md` | • `knowledge/toolchains/ATLAS_CHANNEL.md` (trình tự 10 bước một bài blog)<br>• `knowledge/toolchains/PLATFORM_SETUP.md`<br>• Hồ sơ `.md` Mục 5 (Giờ vàng đăng bài) | • `templates/*`<br>• `knowledge/psychology/*` |
| **⑦ Đo Lường & Báo Cáo (measure)**| `workflows/07_measure.md` | • `.agents/roles/growth-analyst.md`<br>• `knowledge/data_model/DATA_MODEL.md` (Measurement)<br>• `campaign.md` Mục 9 (nơi DUY NHẤT giữ lịch sử đo)<br>• Trước publish: hỏi growth-analyst để tư vấn kế hoạch KPI/tracking | • `output_styles/*`<br>• Template không liên quan tới câu hỏi đo lường |

---

## 2. Bản Đồ Định Tuyến Theo Tác Vụ Đặc Thù

| Tác Vụ Đặc Thù | Điểm Bắt Đầu | Tài Liệu Cần Đọc Tiếp |
|---|---|---|
| **Thêm kênh mạng xã hội mới** | `knowledge/toolchains/PLATFORM_SETUP.md` | `knowledge/toolchains/SECRETS.md` (nối token) · `knowledge/data_model/DATA_MODEL.md` (enum `channels`) |
| **Nối token/mật khẩu cho kênh mới** | `knowledge/toolchains/SECRETS.md` | mục lục bí mật của trạm (`~/.secret/README.md`) |
| **Thêm giọng văn thương hiệu mới** | `output_styles/README.md` | `output_styles/WEBSITE_BLOG_GUIDELINE.md` (file mẫu) |
| **Sửa đổi trường dữ liệu** | `knowledge/data_model/DATA_MODEL.md` | `templates/station/_channel/_campaign/campaign.md` · `scripts/pipeline/export_excel.py` (bộ cột bản xuất) |
| **Dựng trạm nội dung mới** | `docs/ONBOARDING.md` (mười bước, có cách kiểm từng bước) | `install.ps1` / `install.sh` · `docs/WORKSPACE.md` · `examples/README.md` (trạm mẫu đã điền) |
| **Dẫn NGƯỜI KHÁC dựng trạm** (agent làm hướng dẫn viên) | `.agents/prompts/onboard-station.md` | `docs/ONBOARDING.md` |
| **ĐỔI MÁY chạy trạm** (Windows ↔ macOS) — *một máy chạy tại một thời điểm* | `docs/RUNBOOK-DOI-MAY.md` | `scripts/pipeline/station.py` (export/import) · `knowledge/toolchains/STATION_LAYOUT.md` |
| **Cài lịch chạy trên macOS** | `scripts/runners/install_launchd.py` | `templates/launchd/` · `docs/RUNBOOK-DOI-MAY.md` §launchd không có giới hạn thời gian |
| **Trạm nào giữ gì · biến nào trỏ đâu** (ba trạm) | `knowledge/toolchains/STATION_LAYOUT.md` | `knowledge/toolchains/SECRETS.md` · `scripts/pipeline/doctor.py` |
| **Xem một trạm đã điền trông thế nào** | `examples/README.md` | `examples/example-studio/` |
| **Kiểm cây liên kết / tìm bài mồ côi** | `scripts/pipeline/check_tree.py` | `workflows/00_WORKFLOW_INDEX.md` |
| **Sắp ghi file vào gốc trạm** (cấu hình theo máy, sổ, hàng đợi) | `scripts/lib/engine_dir.py` (vì sao `<trạm>/engine` không phải chỗ chứa file) | `scripts/pipeline/check_engine.py` (chạy cổng) · `knowledge/toolchains/STATION_LAYOUT.md` |
| **Dọn media quá hạn ở trạm** (chỉ dọn khi CÓ BẰNG CHỨNG đã đăng; 14 ngày là sàn an toàn) | `docs/RETENTION.md` | `scripts/pipeline/prune_media.py` · `scripts/lib/publish_evidence.py` · `knowledge/toolchains/SECRETS.md` (`WEB_REPO_DIR`) |
| **Dựng chiến dịch CHẠY THEO LỊCH** (bản tin, series tự động) | `knowledge/toolchains/NEWS_PIPELINE.md` | `templates/README.md` · `scripts/pipeline/campaign_cfg.py` (bản chụp cấu hình) |
| **Sửa nguồn cấu hình của một runner** | `knowledge/toolchains/NEWS_PIPELINE.md` §"Trước khi đổi nguồn cấu hình" | `scripts/pipeline/campaign_cfg.py` · `tests/test_campaign_cfg.py` |
| **Đổi bộ màu / thiết kế của kênh** | `templates/station/_channel/channel.yml` (khối `theme:`) | `brand.md` (ghi nhận định thiết kế) — script chỉ đọc `theme:` khi kênh khai; kênh cũ giữ màu cứng trong code |
| **Nâng cấp công cụ / Role Agent** | `.agents/README.md` | `.agents/roles/`, `.agents/skills/` |
---

## 3. Tra Cứu Theo Nhu Cầu (không gắn với khâu nào)

| Cần gì | Đọc |
|---|---|
| Cách agent làm việc, ranh giới an toàn, 3 cổng duyệt | `AGENTS.md` |
| Không biết bắt đầu từ đâu · ai làm khâu nào | `workflows/00_WORKFLOW_INDEX.md` |
| Điều hướng cả chu trình 7 khâu | `.agents/skills/campaign-pipeline/SKILL.md` |
| Sản xuất nội dung từ Content đã duyệt | `.agents/skills/content-production/SKILL.md` |
| Viết hook / câu mở chặn lướt | `.agents/skills/hook-writer/SKILL.md` |
| Viết thread / chuỗi bài | `.agents/skills/thread-writer/SKILL.md` |
| Tâm lý học marketing, vì sao người ta mua | `knowledge/psychology/MARKETING_PSYCHOLOGY.md` |
| Retention / thumbnail / Shorts YouTube | `knowledge/playbooks/YOUTUBE_PLAYBOOK.md` |
| Chuỗi email nuôi dưỡng / chuyển đổi | `knowledge/toolchains/EMAIL_SEQUENCES.md` |
| Newsletter định kỳ | `templates/EMAIL_NEWSLETTER_TEMPLATE.md` |
| Tái chế nội dung 30 ngày | `templates/RECYCLING_PLAN_TEMPLATE.md` |
| Dựng ảnh bìa nhẹ cho card trang chủ (PNG 400KB → JPG ~50KB) | `scripts/pipeline/make_card_thumb.py` |
| Dựng HTML tự chứa để xem trước bài | `scripts/pipeline/build_blog_html.py` |
| Xem toàn cảnh chiến dịch / mọi bài | `scripts/pipeline/build_views.py` (mở `index.html` bằng cách bấm đúp) |
| Một campaign hoàn chỉnh trông thế nào | `content/KPIM/02_campaigns/01_Tobi_Posts/` |
| **CHẠY CHIẾN DỊCH TRONG PHIÊN — quy trình MẶC ĐỊNH** (agent chạy trọn đường ống, dừng ở 3 cổng hỏi người ngay; agent phải trả về gì mỗi bước) | `knowledge/toolchains/IN_SESSION_PIPELINE.md` |
| **Bản mô tả đường ống MÁY ĐỌC ĐƯỢC** (10 trạng thái · 3 cổng · lệnh · artefact · 2 chế độ chạy) | `knowledge/data_model/pipeline.yaml` |
| **Thứ tự các bước và CỔNG DUYỆT nằm ở đâu** (4 lệnh, 3 cổng — đọc TRƯỚC hai dòng dưới) | `knowledge/toolchains/CAMPAIGN_PIPELINE.md` |
| **Telegram làm TRUNG GIAN người ↔ agent** (vòng đời tiến trình · chuyện "50 giây" · vỡ vòng thì nối lại) | `knowledge/toolchains/TELEGRAM_BRIDGE.md` |
| **Một bài blog đi từ đâu tới đâu** (10 bước, 3 cổng duyệt — Cổng 3 khi bảng có cột `g3`) | `knowledge/toolchains/ATLAS_CHANNEL.md` |
| **Duyệt bài qua Telegram · chạy tự động · đăng web** (tầng điều phối trên 10 bước đó) | `knowledge/toolchains/APPROVAL_BUS.md` |
| **Điều phối cả đường ống trong phiên** (chạy tới cổng rồi dừng, kê file cho người mở) | `scripts/pipeline/run_pipeline.py` |
| **Mở / từ chối cổng KHÔNG cần Telegram** (kho cổng dùng chung của mọi mặt tiền) | `scripts/pipeline/approval_gate.py` |
| Chạy MỘT bước của chiến dịch dài kỳ (`create-post`/`write`/`build-page`/`release`) | `scripts/pipeline/campaign_step.py` |
| **Nối kênh ngoài của BẠN** (`audio_cmd`/`youtube_cmd`/`facebook_cmd` — không khoá CLI nào) | `knowledge/toolchains/TELEGRAM_BRIDGE.md` §6b |
| **Nối bộ viết của BẠN vào bước `write`** (`runtime.writer_cmd`, không khoá CLI nào) | `knowledge/toolchains/CAMPAIGN_PIPELINE.md` §6 |
| Gửi/nhận cổng duyệt Telegram | `scripts/pipeline/approve_bus.py` |
| **Bài nào đang ở bước nào** (suy ra, ~350 token thay vì nạp cả campaign.md) | `campaign_step.py <cam> status [--detail]` |
| **Vì sao bài tới trạng thái đó** (sổ sự kiện chỉ-nối-thêm) | `logs/events.jsonl` · `scripts/lib/event_log.py` |
| **Hàng chờ việc** (thư mục là trạng thái, `rename` là phép giành lượt) | `logs/jobs/{cho,running,xong,hong}/` · `scripts/lib/work_queue.py` |
| **Thợ tự gọi agent sau khi duyệt** (một việc mỗi lượt, một agent một lúc) | `scripts/pipeline/worker.py` · `scripts/runners/run-worker.ps1` |
| Đăng bài lên web (đích khai bằng cấu hình, không khoá cứng) | `scripts/pipeline/web_publish.py` |
| **Kiểm định dạng bài Facebook** (bold, link, hashtag) | `scripts/pipeline/fb_format.py --check` |
| **Chấm một bài bằng 24 cổng đếm được** | `scripts/pipeline/blog_gates.py <thư mục bài>` |
| **Số đo thật của bài đã đăng, để đặt ngưỡng** | `fixtures/baseline/blog_baseline.md` |
| **Dựng ảnh infographic tóm tắt cả bài** (prompt mẫu + cổng kiểm chính tả) | `templates/IMAGE_GUIDELINES.md` |
| Nguồn chưng cất của kho tri thức (ghi công) | `knowledge/README.md` |

## 4. Bảng chọn skill (sinh từ catalog)

Đọc catalog cho điều kiện mode/đầu vào/đầu ra; dùng router khi chưa rõ năng lực. Gọi thẳng skill phù hợp là fast path.

<!-- SKILL_ROUTING:START -->
| Skill | Tình huống | Đầu ra | Ranh giới |
|---|---|---|---|
| marketing-routing | The right capability is unclear or the request has multiple steps.; A campaign brief needs clarification or its valid next step is unclear. | need_and_scope; missing_information; primary_skill_and_reason; next_step_and_stop_condition | The user directly invoked a suitable skill for a single-skill request.; The request asks to approve a gate, publish, or update actual metrics. |
| campaign-pipeline | The user wants to prepare or continue a specific campaign.; The current campaign stage or valid next step must be identified. | campaign_status_and_blocker; valid_next_step; prepared_campaign_artifact_or_stage_output | Only customer research or independent draft editing is requested.; Required paths or brief details are missing for campaign creation, or production gates are unmet. |
| content-production | Content must be produced from campaign items that passed Gate 1.; Channel-specific assets are needed from an established brief, voice, and sources.; An independent draft must be edited, polished, or revised without changing facts or voice. | channel_formatted_content; claims_needing_sources; qa_ready_post_entries; edited_draft_with_change_notes | The campaign has not passed Gate 1 or required campaign, brand, or research inputs are missing.; Strategy consultation, offer changes, or edits that bypass campaign gates are requested. |
| hook-writer | The current step needs distinct openings grounded in the message and sources. | hook_options_with_distinct_angles | A campaign, content calendar, or complete asset is needed. |
| thread-writer | The requested output is a thread or multi-part post sequence. | thread_outline; connected_post_draft; CTA | A content calendar, full campaign, or single non-thread post is needed. |
| customer-research | The user wants to understand buyer needs, objections, or real feedback.; Customer reviews, interview transcripts, or survey responses must be analyzed. | customer_insights_by_segment; voice_of_customer_matrix; research_gaps | The task only needs ad-hoc news research for an individual article.; A complete brief is already available and drafting is requested. |
| content-strategy | The user asks what to write this month, needs a content calendar, or wants an SEO topic cluster.; Content topics must be scored and prioritized by business impact and audience demand. | prioritized_topics_matrix; topic_cluster_map; distribution_plan | A specific topic is already selected and needs drafting or execution.; The request is to review campaign progression across the 7 stages. |
| offer-design | Packaging a service, course, software, or consulting offer into a complete offer stack.; Designing bonuses and risk-reversal guarantees for an existing product. | offer_brief; value_stack; risk_reversal_terms | The offer is already finalized and only copy drafting is requested.; The user asks to unilaterally change prices, discounts, or legal terms without approval. |
| lead-generation | Designing a lead magnet to capture targeted prospect interest.; Drafting opt-in page copy, delivery messaging, or a nurture email sequence. | lead_magnet_plan; optin_copy; nurture_email_sequence | The user requests sending bulk emails, configuring live CRMs, or collecting sensitive PII.; A complete campaign already exists and only asset QA is requested. |
| conversion-optimization | A landing page or opt-in form receives traffic but exhibits low conversion rates.; Diagnosing friction, visual hierarchy, or missing value propositions on conversion assets. | cro_diagnostic_report; quick_wins_list; test_hypotheses_matrix | The task only requires minor text polishing for a social post or blog article.; The user demands guaranteed conversion percentage increases without testing. |
| marketing-measurement | Setting up campaign tracking, event taxonomy, UTM conventions, or KPI hierarchies.; Designing controlled A/B test briefs with sample sizes, primary metrics, and guardrails. | tracking_plan; experiment_brief; measurement_snapshot_report | The user assumes automated live analytics sync without manual entry or data verification.; A complete campaign is not yet published and drafting copy is requested. |
<!-- SKILL_ROUTING:END -->

**Luật chống ảo giác:** thư mục chỉ có `README`/`.gitkeep` = kho rỗng — không suy nội dung từ tên thư mục.
File không có thông tin thì nói "chưa có", đừng dựng ra.
