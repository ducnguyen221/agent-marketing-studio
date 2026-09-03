# Hệ Thống Quản Trị Tác Nhân AI (.agents Control Plane)

Thư mục này quản trị 10 vai trò tác nhân, kỹ năng thực thi và bộ kiểm định chất lượng cho hệ thống `agent-marketing-studio`.
Luật vận hành canonical nằm ở [`../AGENTS.md`](../AGENTS.md); bản đồ nạp tài liệu theo nhiệm vụ ở [`../MAP.md`](../MAP.md).

## 1. Mười Vai Trò Chuyên Trách (`roles/`)

| File | Vai | Khâu phụ trách |
|---|---|---|
| `marketing-director.md` | Điều phối tổng thể, giao vai, quản mức tự trị | xuyên suốt |
| `campaign-strategist.md` | Thiết lập brief chiến lược, khởi tạo campaign | ① new |
| `content-strategist.md` | Sinh N dòng Content (ý tưởng gốc) | ② plan |
| `content-producer.md` | Viết `content.md` đa kênh + sinh dòng Post | ③ produce |
| `seo-specialist.md` | Từ khoá, cluster, SEO on-page | hỗ trợ ② ③ |
| `qa-reviewer.md` | Tuân thủ, chặn phát hành | ④ selfqa |
| `content-editor.md` | Biên tập văn phong, tư vấn hay/rõ | ④ selfqa |
| `creative-producer.md` | Dựng ảnh, audio, video, short | ⑤ render |
| `distribution-manager.md` | Đăng/hẹn lịch đa kênh, ghi `publish_*` | ⑥ publish |
| `growth-analyst.md` | Kéo `actual_*`, chốt báo cáo | ⑦ measure |

## 2. Kỹ Năng Thực Thi (`skills/`)
- `campaign-pipeline` — điều hướng chu trình 7 khâu, 2 cổng.
- `content-production` — viết bài chuẩn hoá theo từng định dạng.
- `hook-writer` — tạo hook theo ma trận phân khúc × động cơ × format.
- `thread-writer` — tạo chuỗi bài viết liên kết.

## 3. Kiểm Định (`checklists/`)
- `QA_ASSET.md` — checklist máy tự chạy ở khâu ④ trước khi trình người (giọng, hashtag, `[KIỂM CHỨNG]`, claim có nguồn).

## 4. Hooks (`hooks/`) — mới ở mức THIẾT KẾ
`HOOKS_DESIGN.md` mô tả hook dự kiến. **Chưa có hook nào chạy**; hai cổng duyệt hiện được giữ bằng luật trong `AGENTS.md`, không phải bằng máy. Điều kiện để thi hành ghi trong chính file đó.

## 5. Bản tóm tắt (`source/`)
`core_governance.md`, `data_integrity.md` là bản **tóm tắt** để nạp nhanh. Nguồn canonical: `AGENTS.md` (luật) và `knowledge/data_model/DATA_MODEL.md` (quy ước dữ liệu). Mâu thuẫn thì nguồn canonical thắng — sửa ở đó trước, rồi mới sửa bản tóm tắt.
