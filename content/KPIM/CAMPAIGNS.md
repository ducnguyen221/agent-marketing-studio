# Sổ chiến dịch — KPIM

> Sinh tự động bởi `campaign_registry.py` · cập nhật 2026-07-22
> Đừng sửa tay file này — sửa `brief.yml` của chiến dịch rồi chạy lại.

**4 chiến dịch** · 102 asset · 62 đã đăng

## Đang chạy

*Chưa có chiến dịch nào ở trạng thái `running`.*

## Toàn bộ lịch sử

| Chiến dịch | Tên | Loại | Thời gian | Trạng thái | Asset | Đã đăng | KPI chính |
|---|---|---|---|---|---:|---:|---|
| `CMP-2026-Q1` |  |  |  →  |  | 25 | 15 |  |
| `CMP-2026-Q2` |  |  |  →  |  | 26 | 16 |  |
| `CMP-2026-Q3` |  |  |  →  |  | 26 | 16 |  |
| `CMP-2026-Q4` |  |  |  →  |  | 25 | 15 |  |

## Cách đọc

- **Cổng duyệt (T/C/F)** = số asset đã tick `approve_topic` / `approve_content` / `approve_final`. Chênh lệch lớn giữa T và C nghĩa là nội dung đang tắc ở khâu viết.
- **Tự động**: `hitl` người duyệt từng bài · `batch` duyệt cả loạt theo điều kiện · `auto` máy tự tick khi thoả điều kiện trong `brief.automation.auto_if`.
- Mỗi chiến dịch có thư mục riêng trong `02_campaigns/`, chứa cả nội dung và asset.
