# P-Q1-18 · Reel · Tuần lễ hoàn tiền siêu thị

**Chức năng riêng:** mở vấn đề — người xem tự thấy mình đang bỏ sót tiền, chưa bán gì.
**Pillar:** Promo · **Funnel:** discovery · **Thời lượng đích:** 24–28 giây

---

## Hook (0–2s)

> Mỗi tháng bạn tiêu 6 triệu đi siêu thị. Bạn đang bỏ lại bao nhiêu trên bàn?

## Kịch bản

| Mốc | Hình | Lời |
|---|---|---|
| 0–2s | Cận cảnh hoá đơn siêu thị dài | Mỗi tháng bạn tiêu 6 triệu đi siêu thị. Bạn đang bỏ lại bao nhiêu trên bàn? |
| 2–8s | Tay quẹt thẻ, số tiền hiện lên | Hoàn tiền 5% nghe thì nhỏ. Nhưng 5% của 6 triệu là 300 nghìn. Một tháng. |
| 8–16s | Chồng 12 hoá đơn xếp lên | Nhân 12 tháng. Bằng đúng một lần đi chợ Tết. Tiền đó vốn đã là của bạn — chỉ là bạn chưa nhận. |
| 16–24s | Màn hình app hiện mức hoàn | Tuần lễ này mức hoàn tối đa là 500 nghìn. Hết hạn mức thì thôi, không cộng dồn sang tháng sau. `[KIỂM CHỨNG 1]` |
| 24–28s | Logo + dòng điều kiện | Xem điều kiện áp dụng trước khi đăng ký. Đọc kỹ phần hạn mức. |

## Ghi chú sản xuất

- Không quay mặt người thật, không hiện số thẻ, không hiện tên chủ thẻ.
- Con số 6 triệu là **ví dụ minh hoạ**, phải hiện chữ "ví dụ" trên màn hình — không được
  để người xem hiểu là mức chi tiêu trung bình có thật.
- Chữ tiếng Việt overlay lúc dựng, không để model sinh chữ trong ảnh.

## `[KIỂM CHỨNG]` còn mở

1. **Hạn mức 500.000đ có cộng dồn sang kỳ sau không?** Phải lấy xác nhận từ biểu phí
   chính thức trước khi quay. Nếu có cộng dồn thì câu ở mốc 16–24s sai và phải viết lại.

## Mục QA chưa tự tin đạt

- `chk_primary_source`: mức hoàn 5% và trần 500.000đ đang lấy từ tiêu đề kế hoạch, **chưa
  đối chiếu biểu phí**. Cần link biểu phí trước khi qua cổng duyệt nội dung.
- `chk_cta_ok`: chưa rõ chiến dịch này có được phép CTA thương mại trực tiếp không —
  `01_Brief.commercial_cta_episodes` của CMP-2026-Q1 cần người xác nhận.
