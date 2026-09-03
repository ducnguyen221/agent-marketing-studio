---
campaign_id: {{CMP-YYYY-NN}}            # mã định danh duy nhất, vd CMP-2026-06-AI
campaign_code: {{NN_Ten_Campaign}}      # = TÊN FOLDER (vd 01_Tobi_Posts) — dùng để resolve
name: {{Tên chiến dịch dễ đọc}}
pillar: {{powerbi | fabric | ai-agent | career}}
linked_okr: {{OKR-...}}                  # OKR mà campaign phục vụ (xem 31.01_mission_okr.md)
owner: Duc
created: {{YYYY-MM-DD}}
status: draft                            # draft → ready → running → done
---

# Hồ sơ & đặc tả chiến dịch — {{Tên chiến dịch}}

> File này được **copy từ** `agent/templates/CAMPAIGN_TEMPLATE.md` vào folder campaign
> `31_CAMPAIGNS/01_CAMPAIGNS/NN_Ten_Campaign/` rồi **đổi tên** giống folder (`NN_Ten_Campaign.md`).
> Đây là **HỒ SƠ + ĐẶC TẢ chiến dịch**: thông tin nghiệp vụ do user + AI xây, chuẩn nội dung/phân phối
> dùng chung, cùng lịch sử + báo cáo.
> Dữ liệu thực thi từng bài nằm ở `NN_Ten_Campaign.xlsx` (5 sheet). Hai file song hành.
> Quy trình tạo/vận hành: `agent/commands/create_campaign.md`, `campaign.md`, `report_campaign.md`.
> Hợp đồng kỹ thuật: `…\30_MARKETING\agent\scripts\PIPELINE_CONTRACT.md` (scripts ở `agent\scripts`; secret/state ở `.video\tobi`).

> **Quy ước template:** phần `{{...}}` = cần điền theo campaign cụ thể. Các mục **chuẩn hóa chung**
> (Content Pillars, Distribution playbook, Asset registry, Channel performance) đã có **nội dung thật
> làm mặc định** — giữ nguyên, chỉ **chỉnh theo campaign nếu cần**.

---

## 1. Mô tả & bối cảnh
- **Mô tả ngắn**: {{1–2 câu campaign này là gì}}
- **Business context**: {{vì sao làm lúc này; nhu cầu/thị trường/sự kiện kích hoạt}}
- **OKR phục vụ**: {{OKR-... — xem 31.01_mission_okr.md}}
- **Pillar phục vụ + lý do**: {{vd ai-agent (25%) — đúng sở trường + đang hot}}

## 2. Mục tiêu
- **Business goal**: {{awareness | demand | conversion | retention}} — {{mô tả cụ thể}}
- **Content KPI** (đối chiếu sau publish ở mục Nhật ký):

| KPI | Target |
|---|---|
| Blog views / bài | {{500}} |
| YouTube views / video | {{200}} |
| FB engagement / post | {{30 reactions}} |
| Social impressions | {{...}} |
| Engagement rate | {{...}} |
| Inbound leads | {{...}} |
| Newsletter sub | {{...}} |
| {{KPI khác}} | {{...}} |

## 3. Đối tượng (persona)
- **Primary persona**: {{Mai / Hùng / Anh Tâm / Linh / Hà — xem 00_AI_BRAIN/06_KNOWLEDGE/market_intelligence/21.03_personas.md}}
- **Pain cần giải**: {{nỗi đau thật của persona}}
- **Journey stage**: {{awareness | consideration | decision}}

## 4. Key message
- **Hook**: {{câu mở khơi gợi}}
- **Core message**: {{thông điệp lõi xuyên suốt campaign}}
- **Proof points**: {{bằng chứng / ví dụ / case làm tin}}
- **CTA**: {{hành động mong muốn}}

## 5. prompt_requirements (đề bài cho AI stage `topics`)
> Đoạn này được đổ vào field `prompt_requirements` của Sheet Campaign. Càng cụ thể, chủ đề sinh ra càng đúng.
- **Angle mong muốn**: {{góc nhìn / cách phá định kiến}}
- **Phải có**: {{ví dụ đời thường, use-case thật, dẫn nguồn...}}
- **Phải tránh**: {{buzzword, listicle "top tool", "AI thay thế..."}}
- **Nguồn tham khảo** (nếu có): {{link / tài liệu}}

---

## 6. Content Pillars — KPIM Academy
> 4 trụ chủ đề. Mỗi piece content phải fit ít nhất 1 pillar. Out-of-pillar content = noise.
> Đây là chuẩn chung của Academy — **giữ nguyên làm mặc định**, chỉ chỉnh tỷ trọng nếu campaign cần.

### Pillar 1 — Power BI mastery (35% content)
- **Topics:** DAX deep-dive (context, time intel, advanced patterns) · Star schema design, dimensional modeling · Performance optimization (DirectQuery, aggregations, caching) · RLS / OLS chuẩn enterprise · Power BI service ops (deployment, gateway, governance) · Power Query (M) tricks
- **Audience:** Mai (Head of Data), Hà (BI dev), Linh (Senior analyst)
- **Format mix:** Blog deep-dive (45%), social tips (40%), micro (15%)

### Pillar 2 — Microsoft Fabric & data platform (25%)
- **Topics:** Fabric architecture (OneLake, Lakehouse, Warehouse, Direct Lake) · Migration Power BI Premium → Fabric · Dataflow Gen2 vs Gen1 · Real-time intelligence · Cost optimization Fabric
- **Audience:** Mai, Hà, technical team lead
- **Format mix:** Blog (50%), social technical (35%), micro (15%)

### Pillar 3 — AI Agent for Data Practitioner (25%)
- **Topics:** LLM basics for analyst (no buzzword) · Prompt engineering practical · Agent framework, tool use, MCP · RAG cho enterprise data · Use-case: data quality auditor agent, dashboard explainer, code reviewer · AI in Power BI (Copilot critique + when actually useful)
- **Audience:** Linh, Hà, BI dev curious về AI
- **Format mix:** Blog (40%), social opinion (40%), micro (20%)

### Pillar 4 — Career, mindset, behind-the-scene (15%)
- **Topics:** Solo consultant playbook · AI-augmented operator (1 người làm 10 việc) · Bilingual career (VN + JP/EN) · Public speaking, teaching journey · Tool stack, productivity · Behind-the-scene của KPIM Academy
- **Audience:** Linh + Hà (career-driven), broader audience
- **Format mix:** Social personal (50%), blog reflection (20%), micro story (30%)

### Content quota per quarter

| Pillar | % Total | Q2 target (24 pieces) |
|---|---|---|
| 1. Power BI | 35% | 8 |
| 2. Fabric | 25% | 6 |
| 3. AI Agent | 25% | 6 |
| 4. Career/BTS | 15% | 4 |

(Các con số này lỏng lẻo — adjust theo pipeline content tự nhiên.)

### What we DON'T cover
- ❌ Generic AI hype không có technical depth
- ❌ Excel beginner tutorial (mismatch positioning)
- ❌ "Top 10 best AI tools" listicle
- ❌ Crypto, web3, NFT
- ❌ Politics, controversy không liên quan core

---

## 7. Distribution playbook
> "Content tốt mà không phân phối = content phí." Workflow chuẩn để mọi piece được đưa tới audience đúng.
> Chuẩn chung — **giữ làm mặc định**, ghi rõ ở Mục 1/2 kênh nào bắt buộc / tùy chọn cho campaign này.

### Channel role

| Channel | Audience primary | Goal | Best format |
|---|---|---|---|
| Blog (own ducnguyen.vn/atlas + LinkedIn article) | Search/SEO + LinkedIn audience | Authority, SEO | Long-form 2500-4000w |
| LinkedIn post | Mid-senior VN data + JP expat | Reach + lead | Post 200-400w + carousel |
| Facebook (page "Tobi Nguyễn" + cá nhân) | VN community broad | Reach + community | Story-driven, video clip |
| X / Threads | Global tech + bilingual | Hot take + thought leadership | One-liner, thread 5-10 |
| Email newsletter | Warm audience | Conversion + retention | Curated + insight |
| YouTube (playlist "Học cùng Tobi"; mở rộng Q3+) | Visual learner | Tutorial + talk | Long video, shorts |

### Posting cadence (per week)

| Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|---|---|---|---|---|---|---|
| LinkedIn | X (3-5) | LinkedIn + FB | X (3-5) | LinkedIn | (rest / engage) | FB story |
| | Blog publish (bi-weekly Tue 9:00 VN) | | Newsletter (bi-weekly Thu 9:00 VN) | | | |

### Time-of-day (VN audience)
- LinkedIn: 8-10 AM, 4-6 PM (work commute)
- FB: 12-2 PM, 8-10 PM (lunch + evening)
- X: 9-11 AM, 9-11 PM (global mix)

### Cross-post rules
- KHÔNG paste y nguyên giữa channel — tweak voice/length/format
- Blog → LinkedIn article (full or excerpt + link)
- LinkedIn post → FB (less professional, more personal)
- Long thread X → carousel LinkedIn
- Newsletter section → standalone post 1 tuần sau

### Recycling plan (cho campaign này)
- {{Long-form A → cắt thành: ...}}
- {{Visual asset chia sẻ: ...}}

### Engagement after publish
- T+0 to T+2h: trả lời comment ngay
- T+2 to T+24h: reply DM, engage commenter
- T+1 day: scan để re-share / pin top comment
- T+3 day: check engagement → save winning hook cho post sau

### Distribution checklist (mỗi piece)
- [ ] Brand voice check ✅
- [ ] Hook compelling
- [ ] Visual ready (đúng kích thước channel)
- [ ] CTA rõ
- [ ] Schedule đúng giờ vàng
- [ ] Link tracker (UTM nếu cần)
- [ ] Cross-post version ready
- [ ] Recycling plan filed

---

## 8. Lịch / cadence của campaign
- **schedule_start**: {{YYYY-MM-DD}}
- **schedule_end**: {{YYYY-MM-DD}}
- **cadence**: {{weekly | 2x-week | biweekly}}
- **num_posts_planned**: {{2}}
- **topic_group asset**: {{01_powerbi | 02_fabric | 03_ai-agent | 04_career}}

### Kế hoạch theo tuần (Gantt-ish)

| Week | Task | Channel | Status |
|---|---|---|---|
| 1 | {{Outline + draft long-form}} | {{Blog}} | |
| 2 | {{Publish long-form + 3 social}} | {{Blog, LinkedIn, FB}} | |
| 3 | {{Social drumbeat + email}} | {{LinkedIn, FB, X, email}} | |
| 4 | {{Recap + retro}} | {{All}} | |

### Rủi ro & giảm thiểu

| Risk | Mitigation |
|---|---|
| {{Content trễ}} | {{Outline xong T-7, draft T-3}} |
| {{Engagement thấp}} | {{Recycle hook, A/B title}} |

---

## 9. Content calendar
> Master calendar cho mọi piece content của campaign (blog, social, email). Sync: thứ 2 hàng tuần.

### {{2026-Q2}}

| Week | Date | Content ID | Type | Pillar | Title (working) | Channel | Status |
|---|---|---|---|---|---|---|---|
| {{W17}} | {{2026-04-27}} | {{BLG-2026-001}} | {{Long-form}} | {{Pillar 2}} | {{Microsoft Fabric End-to-End: 3 thứ phải biết trước khi migrate}} | {{Blog}} | {{draft}} |
| {{W17}} | {{2026-04-29}} | {{POS-2026-001}} | {{Social}} | {{Pillar 1}} | {{DAX context transition — minh họa với 1 measure}} | {{LinkedIn}} | {{planned}} |
| ... | | | | | | | |

### Pillar distribution check

| Pillar | Q target | Q actual |
|---|---|---|
| 1. Power BI | {{8}} | {{0}} |
| 2. Fabric | {{6}} | {{0}} |
| 3. AI Agent | {{6}} | {{0}} |
| 4. Career/BTS | {{4}} | {{0}} |

---

## 10. Asset registry — Visual & Creative
> Reusable visual asset (illustration, diagram, photo, icon set). Quy ước chung cho mọi campaign.

| ID | Type | Description | File path | License | Used in |
|---|---|---|---|---|---|
| AST-001 | Diagram | Star schema visual | `assets/diagrams/star-schema.svg` | own | (TBD) |
| AST-002 | Photo | Duc speaking | `assets/photos/duc-speaking-1.jpg` | own | (TBD) |
| AST-003 | Icon set | Lucide outline | (CDN) | open | (cross-use) |
| {{AST-NNN}} | {{...}} | {{...}} | {{...}} | {{own / open / ...}} | {{campaign}} |

**Cách thêm asset:**
- File lưu trong `30_MARKETING/31_CAMPAIGNS/assets/<type>/`
- Append row + license source
- Không add nếu chưa rõ license

---

## 11. Channel performance snapshot
> Weekly snapshot. Không tốn quá 30 phút điền. Mỗi tuần append một block `### YYYY-Www`.

### {{2026-W17}}

| Channel | Followers | Posts | Impressions | Engagement rate | DM | Inbound lead |
|---|---|---|---|---|---|---|
| LinkedIn | | | | | | |
| Facebook page | | | | | | |
| X | | | | | | |
| Newsletter | (subs) | | (open rate) | (CTR) | | |
| Blog | (page views) | | | | | |

- **Top performer this week:** {{...}}
- **Worst performer this week:** {{...}}
- **Action:** {{...}}

---

## 12. Lịch sử bài đã chốt
> `register_post.py` ghi/cập nhật mỗi khi 1 bài publish: **Tóm tắt + Key-terms** (để bài sau LIÊN KẾT mạch
> + TRÁNH lặp thuật ngữ đã viết) + **Hồ sơ (content)** = đường dẫn refer tới content.md/blog.md chi tiết.

| post_id | Tiêu đề | Tóm tắt | Key-terms | Hồ sơ (content) | Ngày chốt |
|---|---|---|---|---|---|
| {{P-0001}} | {{tiêu đề bài}} | {{1-2 câu}} | {{term1, term2, …}} | {{32_PUBLIC_CONTENT/…/folder}} | {{YYYY-MM-DD}} |

## 13. Lịch sử đăng tải
> AI **append** mỗi khi 1 bài publish xong (ghi Sheet Result). Một dòng / bài.

| post_id | blog_url | youtube_url | fb_permalink | Ngày đăng |
|---|---|---|---|---|
| {{P-0001}} | {{https://ducnguyen.vn/...}} | {{https://youtu.be/...}} | {{https://facebook.com/...}} | {{YYYY-MM-DD}} |

## 14. Nhật ký & báo cáo AI
> Command `report_campaign` **append** mỗi lần chạy một mục `## Báo cáo <ngày>` ngay dưới đây
> (số liệu engagement + status từng bài + rollup). KHÔNG xóa mục cũ — giữ lịch sử theo thời gian.

<!-- BÁO CÁO APPEND BÊN DƯỚI -->

---

## 15. Retro (post-campaign)
> Điền sau khi campaign kết thúc (status → done).

| What worked | What didn't | Next time |
|---|---|---|
| {{...}} | {{...}} | {{...}} |

---

**Owner:** Duc | **Review pillars/playbook:** Quarterly | **Sync calendar/perf:** Weekly (Mon)
