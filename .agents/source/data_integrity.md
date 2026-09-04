# Data Integrity — Quy Tắc Toàn Vẹn Dữ Liệu

1. **Ô Rỗng Có Nghĩa:** không điền số `0` hay chuỗi giả vào ô chưa có dữ liệu. Ô rỗng nói
   "chưa biết"; số 0 nói "đo được là 0". Cổng kiểm cũng vậy: trạng thái **thiếu** không bao
   giờ được tính là **xanh**.
2. **Dùng Script, Không Dựng Tay:** tạo kênh/chiến dịch/bài bằng `new_channel.py`,
   `new_campaign.py`, `new_post.py` — chúng copy từ `templates/` và ghi đúng chỗ. Tự dựng tay
   là sớm muộn lệch cấu trúc mà `check_tree.py` mới phát hiện ra.
3. **Chỉ Đụng Vùng Giữa Marker:** script cập nhật bảng phải đi qua `md_io.upsert_row`, không
   bao giờ regex cả file. Khoá không có trong bảng thì **ném lỗi**, đừng bỏ im lặng —
   `them_cot=True` để cố ý nới bảng.
4. **Quy Tắc Ghi Đè:** `posts[].actual` bị ghi đè mỗi lần đo, không giữ lịch sử. Vì vậy mỗi
   lần đo phải **chốt số** vào Mục 9 của `campaign.md` — đó là nơi duy nhất giữ được diễn biến.
