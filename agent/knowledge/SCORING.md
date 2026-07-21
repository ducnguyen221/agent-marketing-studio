# Chấm điểm — quyết định có sản xuất hay không

Chấm **trước** khi viết. Mục đích là loại sớm, không phải để trang trí workbook.

## TOS — Topic Opportunity Score (0–5 mỗi tiêu chí)

```
TOS = R×0.20 + T×0.15 + I×0.15 + O×0.20 + E×0.15 + S×0.10 + B×0.05
```

| Mã | Tiêu chí | Hỏi gì |
|---|---|---|
| R | Relevance | Đúng người mình muốn phục vụ không? |
| T | Timeliness | Bây giờ có lý do để nói không? |
| I | Impact | Người đọc đổi được gì sau khi biết? |
| O | Original insight | Mình có gì mà nơi khác không có? |
| E | Evidence quality | Có bằng chứng kiểm được không? |
| S | Series fit | Nối được vào mạch nội dung đang có không? |
| B | Business alignment | Có dẫn về việc mình làm không? |

| TOS | Làm gì |
|---|---|
| **≥ 4.0** | Campaign đầy đủ — hero + các asset bổ trợ |
| 3.2 – 3.99 | Chỉ làm short / post, hoặc video gọn |
| 2.5 – 3.19 | Đưa vào backlog, chưa làm |
| **< 2.5** | **Loại.** Đừng đề xuất cho đủ số lượng. |

## HRS — Hype Risk Score (0–5, là cờ, không nhân trọng số)

Chấm mức độ chủ đề đang bị thổi phồng và mình có nguy cơ nói quá.

- **HRS ≥ 3** → **bắt buộc** gắn nhãn "chưa được kiểm chứng đầy đủ" trong nội dung,
  title không được khẳng định tuyệt đối, và phải chờ nguồn sơ cấp trước khi lên lịch.
- Validator cảnh báo khi `hrs_score ≥ 3`.

## Hook Score (0–5 mỗi tiêu chí) — chọn đoạn lên short / chọn title

| Tiêu chí | |
|---|---|
| Xung đột rõ | có căng thẳng, có thứ đang bị đe doạ |
| Dễ bám | người lạ hiểu ngay nhân vật/bối cảnh |
| Stakes | hỏng thì mất gì |
| Cliffhanger thật | không phải cliffhanger giả tạo |
| **Hiểu độc lập** | xem riêng đoạn này vẫn hiểu |
| Không spoil quá | không phá trải nghiệm bản đầy đủ |

**Ngưỡng: tổng ≥ 20/30 VÀ "Hiểu độc lập" ≥ 3.** Không đạt "hiểu độc lập" thì bỏ,
dù kịch tính đến mấy — người lướt qua sẽ không hiểu gì.

Hook Score dùng để **chọn**, không dùng để đổi nội dung gốc cho kịch tính hơn.

## Ghi vào đâu

`03_Calendar.tos_score` và `.hrs_score`. Hai cột này **của người** — agent đề xuất điểm
trong phần trả lời, người tự điền hoặc xác nhận. `campaign_excel.py set` từ chối ghi.

Lý do: điểm số quyết định cái gì được sản xuất. Nếu agent tự chấm rồi tự làm theo điểm
mình chấm, vòng lặp đó không có ai kiểm.
