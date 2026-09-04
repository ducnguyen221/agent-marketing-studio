# Khâu ②: Lập Kế Hoạch Nội Dung (Plan Content)

| Thuộc tính | Chi tiết |
|---|---|
| **Vai trò chính** | `content-strategist` (hỗ trợ bởi `seo-specialist`) |
| **Đầu vào (Input)** | frontmatter `campaign.md` + Mục 4 (Những điều KHÔNG làm) + `continuity.json` của kênh (tránh trùng đề tài) |
| **Công cụ (Tools)** | `scripts/pipeline/new_post.py` (có `--bulk` cho cả đợt) |
| **Đầu ra (Output)** | N dòng mới trong bảng Content, `status = proposed`, ô `g1` **rỗng** |

---

## 1. Trình Tự Thực Thi

1. **Nghiên cứu từ khóa & Chủ đề:** Tham khảo [`../knowledge/playbooks/SEO_PLAYBOOK.md`](../knowledge/playbooks/SEO_PLAYBOOK.md) và [`../knowledge/playbooks/COPY_FRAMEWORKS.md`](../knowledge/playbooks/COPY_FRAMEWORKS.md).
2. **Sinh N dòng Content:**
   - Điền nhóm **Strategy:** `content_goal`, `audience_profile`, `core_brief`.
   - Điền nhóm **Knowledge:** `key_sources`, `proof_points`.
   - Điền nhóm **SEO:** `target_keyword`, `secondary_keywords`.
   - Điền nhóm **Creativity:** `creative_direction`, `hook_angle`.
   - Điền nhóm **Planning:** `schedule_date` (rải đều theo cadence).
   - Đặt `Content.status = proposed`.
3. **Dừng & Báo Cáo:** Xuất danh sách các ý tưởng vừa đề xuất và yêu cầu con người phê duyệt tại Cổng 1.

---

## 🔒 CỔNG 1: PHÊ DUYỆT Ý TƯỞNG (Human Gate 1)

> ⚠️ **Điều kiện tiên quyết để chuyển sang Khâu ③:**
> - `Content.status = approved`
> - `Content.approved_date = YYYY-MM-DD` (có ngày hợp lệ)
> 
> **Agent TUYỆT ĐỐI KHÔNG tự động tick duyệt cổng này.**