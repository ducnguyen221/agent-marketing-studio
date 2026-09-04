# Khâu ③: Sản Xuất Nội Dung Đa Kênh (Produce Content)

| Thuộc tính | Chi tiết |
|---|---|
| **Vai trò chính** | `content-producer` (hỗ trợ bởi `seo-specialist`, skills: `hook-writer`, `thread-writer`) |
| **Đầu vào (Input)** | Dòng `Content` đã có `status = approved` và `approved_date` |
| **Công cụ (Tools)** | Markdown editor, `.agents/skills/hook-writer/` |
| **Đầu ra (Output)** | File `<folder_path>/content.md` + Các dòng `Post` tương ứng trong Excel |

---

## 1. Trình Tự Thực Thi

1. **Khởi tạo file nội dung:** Tạo file `<folder_path>/content.md` từ [`../templates/content.md`](../templates/content.md).
2. **Soạn thảo Brief & Nội dung theo Kênh:**
   - Đọc kỹ style của kênh tại [`../output_styles/`](../output_styles/).
   - Viết từng khối `## post:<channel>_<format>` (ví dụ: `## post:blog_article`, `## post:facebook_post`, `## post:youtube_script`).
   - Tái định dạng văn phong cho từng kênh (không copy nguyên văn giữa các kênh).
   - Claim/số liệu chưa kiểm chứng được phải gắn tag `[KIỂM CHỨNG]`.
3. **Sinh dòng Post tương ứng trong Sheet Post:**
   - Mỗi khối `## post:<format>` tương ứng với 1 dòng trong sheet `Post`.
   - Điền `post_id`, `content_id`, `channel`, `post_format`, `post_role`, `post_content` (= anchor trỏ vào khối text).
   - Kế thừa KPI: `target_view`, `target_interaction`.
   - Đặt `agent_status = completed`, `post_status = human_review`.
4. **Cập nhật Content:** Đặt `Content.status = in_production`. Chuyển tiếp sang [Khâu ④ (Self-QA)](04_self_qa.md).