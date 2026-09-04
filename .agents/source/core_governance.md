# Core Governance — Luật Cốt Lõi Của agent-marketing-studio

1. **Markdown Là Nguồn Sự Thật:** mọi trạng thái sống trong `campaign.md` (bảng Content giữa
   marker `<!-- CONTENT:BEGIN/END -->`) và `publish.json` của từng bài. File `.xlsx` là **bản
   xuất một chiều** (`export_excel.py`) — sửa trong Excel KHÔNG quay ngược về nguồn.
2. **Con Người Kiểm Soát 2 Cổng Duyệt:**
   - Cổng 1 — chọn đề tài: `status = approved` + ngày ở ô `g1` của bảng Content.
   - Cổng 2 — trước khi đăng: `publish.json → posts[].review.status = approved`, **bắt buộc**
     kèm `approved_by` và câu duyệt nguyên văn.
   Agent không bao giờ tự ý vượt cổng, và không có đường nào trong mã tự đặt `approved`.
3. **Bảo Mật Tuyệt Đối:** không đưa token, secret hoặc dữ liệu khách hàng vào repo. Trạm nội
   dung nằm ngoài git; `profile.md` và `publish.json` không bao giờ được commit lên repo công khai.
