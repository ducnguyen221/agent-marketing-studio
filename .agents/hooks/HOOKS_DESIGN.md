# Hooks — THIẾT KẾ, CHƯA THI HÀNH

> **Trạng thái: chưa có hook nào chạy.** Thư mục này chỉ giữ *ý định thiết kế*. Không harness nào
> (Claude Code / Codex / Antigravity) đọc file ở đây; hai cổng duyệt hiện được giữ **bằng luật
> trong `AGENTS.md`** và bằng việc con người tự tay đặt giá trị trong Excel — không phải bằng máy.

## Vì sao ghi rõ như vậy

Bản trước ở đây là một `hooks.json` chỉ có chuỗi `condition`, không có handler/command, không harness
nào nạp — tức là một **cổng giả**: tài liệu mô tả nó như guardrail đang bảo vệ, trong khi thực tế
không gì chặn cả. Một cổng giả nguy hiểm hơn không có cổng, vì người đọc tin là đã được bảo vệ.

## Hook dự kiến (khi hiện thực hoá)

| Tên | Điểm móc | Điều kiện chặn | Mục đích |
|---|---|---|---|
| `gate-keeper` | PreToolUse (lệnh ghi Excel) | lệnh ghi vào `Content.approved_date` hoặc đặt `Post.review_status = approved` | Không cho agent tự đánh dấu đã duyệt ở Cổng 1 / Cổng 2 |

## Điều kiện để chuyển từ thiết kế sang thi hành

1. Có handler thật (script) trả `deny` cho đúng harness đang dùng, khai trong cấu hình hook của harness
   đó (vd `.claude/settings.json`) — **không** phải file JSON tự chế ở đây.
2. Có test chứng minh hook **đỏ đúng lý do**: lệnh ghi `approved_date` bị chặn, lệnh ghi cột khác đi qua.
3. Cập nhật `AGENTS.md` và `.agents/README.md` nói rõ cổng nào do máy giữ, cổng nào do luật giữ.

Chưa đủ ba điều trên thì file này vẫn là thiết kế, và tài liệu khác **không được** mô tả nó như guardrail đang chạy.
