---
campaign_id: CMP-2026-06-TOBI
campaign_code: 01_Tobi_Posts
name: "AI Agent cho người làm Data — nhập môn không buzzword"
pillar: ai-agent
owner: Duc
created: 2026-06-21
status: active
---

# Hồ sơ chiến dịch — AI Agent cho người làm Data (nhập môn không buzzword)

> File này được copy từ `agent/templates/CAMPAIGN_TEMPLATE.md`, đổi tên giống folder (`01_Tobi_Posts.md`).
> Đây là HỒ SƠ chiến dịch; dữ liệu thực thi từng bài ở `01_Tobi_Posts.xlsx` (5 sheet).
> Quy trình: `AGENTS.md` (Bước 1–5) + `agent/workflows/00_WORKFLOW_INDEX.md`.

---

## 1. Mô tả & bối cảnh
- **Mô tả ngắn**: Series 2 bài nhập môn AI Agent cho dân làm data, hạ bệ hype, dạy bắt đầu từ chiến thắng nhỏ.
- **Business context**: Nhiều analyst hỏi "AI Agent là gì, có thay được mình không" nhưng tài liệu phổ biến toàn buzzword.
- **Pillar phục vụ + lý do**: ai-agent (25%) — đúng sở trường, đang hot, ít nội dung tiếng Việt chất lượng.

## 2. Mục tiêu
- **Business goal**: awareness — xây uy tín "Học cùng Tobi" như nguồn giải thích AI Agent tỉnh táo, thực chiến.
- **Content KPI**:

| KPI | Target |
|---|---|
| Blog views / bài | 500 |
| YouTube views / video | 200 |
| FB engagement / post | 30 reactions |

## 3. Đối tượng (persona)
- **Primary persona**: Linh (senior analyst tò mò AI), Hà (BI dev).
- **Pain cần giải**: sợ tụt hậu, không biết bắt đầu từ đâu, sợ AI "nói hay nhưng tính sai".
- **Journey stage**: awareness.

## 4. Key message
- **Hook**: "Agent không phải phép thuật — nó là đội thợ AI có việc rõ ràng."
- **Core message**: AI Agent là công cụ có giới hạn rõ; người làm data biết giao đúng việc sẽ mạnh hơn, không bị thay thế.
- **Proof points**: 1 ví dụ đời thường + 1 use-case data thật (data-quality auditor / dashboard explainer).
- **CTA**: theo dõi series + thử dựng agent nhỏ đầu tiên theo bài 2.

## 5. prompt_requirements (đề bài cho AI stage `topics`)
- **Angle mong muốn**: hạ bệ hype — "agent không phải phép thuật, là đội thợ AI có việc rõ ràng".
- **Phải có**: 1 ví dụ đời thường + 1 use-case data thật; dẫn nguồn khi so sánh framework.
- **Phải tránh**: "AI thay thế analyst", listicle "top tool", buzzword rỗng.
- **Nguồn tham khảo**: tin/framework agent mới nhất qua WebSearch (ghi rõ nguồn).

---

## 6. Content Pillars, 7. Distribution playbook, 9. Content calendar, 10. Asset registry, 11. Channel performance
> Giữ chuẩn chung ở `agent/templates/CAMPAIGN_TEMPLATE.md` (các mục này có nội dung mặc định).
> Chỉ chỉnh ở đây nếu campaign cần khác chuẩn.

## 8. Lịch / cadence
- **schedule_start**: 2026-06-25 · **schedule_end**: 2026-07-02 · **cadence**: 2 bài/tuần · **num_posts_planned**: 2
- **topic_group asset**: 03_ai-agent

---

## 12. Lịch sử bài đã chốt

| post_id | Tiêu đề | Tóm tắt | Key-terms | Hồ sơ (content) | Ngày chốt |
|---|---|---|---|---|---|
| TOBI-001 | AI Agent là gì với người làm data — và khi nào KHÔNG nên dùng | Định nghĩa agent qua ví dụ đời thường; agent = đội thợ AI có việc rõ | agent, tool use, giới hạn | assets/TOBI-001_ai-agent-la-gi/content.md | 2026-06-21 |
| TOBI-002 | Dựng agent kiểm chất lượng dữ liệu đầu tiên: bắt đầu từ chiến thắng nhỏ | Use-case data-quality auditor; bắt đầu từ 1 rule nhỏ | data quality, auditor agent | (chưa) | 2026-06-21 |

## 13. Lịch sử đăng tải
> Append khi publish xong (ghi Sheet Result).

| post_id | blog_url | youtube_url | fb_permalink | Ngày đăng |
|---|---|---|---|---|
| TOBI-001 | https://ducnguyen.vn/atlas/ai/ai-agent-la-gi | https://youtu.be/DEMO-001 | https://facebook.com/DEMO-001 | 2026-06-25 |

## 14. Nhật ký & báo cáo AI
> Command `report_campaign` append `## Báo cáo <ngày>` bên dưới sau mỗi lần chạy.

<!-- BÁO CÁO APPEND BÊN DƯỚI -->

## 15. Retro (post-campaign)
> Điền sau khi campaign kết thúc (status → done).

| What worked | What didn't | Next time |
|---|---|---|
| | | |
