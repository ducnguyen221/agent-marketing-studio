# Đánh giá định tuyến marketing

`tests/fixtures/marketing_routing_cases.yaml` khóa 24 tình huống giả lập, payload có nội dung, rubric và oracle riêng cho từng mốc A0/A1/B/C. `payload_refs` trỏ tới payload trong cùng fixture; không thay bằng nhãn `provided`/`synthetic` hoặc đường dẫn máy. Mỗi scenario variant là một input riêng, có oracle riêng. Bộ test pytest chỉ kiểm cấu trúc fixture; nó không chạy mô hình và không phải bằng chứng hành vi.

## Quy trình đánh giá

1. Chọn đúng mốc đã triển khai. Dùng prompt và context trong fixture; chỉ cấp cho model phần input, không đưa rubric/oracle vào context của model.
2. Chạy mỗi case hai lượt với cùng model ID, ngày, system/skill entrypoint, temperature và công cụ; ghi khác biệt cấu hình. Không chọn lượt đẹp nhất.
3. Chạy thêm từng `entrypoint_variants` được khai báo. Một case chỉ đạt khi cả hai lượt của mọi biến thể đều đạt. Báo tổng số invocation thực, không gọi hai lượt là hai case độc lập.
4. Reviewer độc lập chấm năm chiều định tuyến: route, câu hỏi làm rõ, phạm vi tài liệu, đầu ra và quyền hạn. Mỗi chiều là pass/fail. Case critical trượt ở bất kỳ lượt nào làm checkpoint không đạt.
5. Chấm riêng rubric SC6 chuyên môn gồm bốn mục 0/1/2: (a) insight gắn với nguồn và phân khúc, có bất đồng và giới hạn độ tin cậy; (b) chủ đề nối nhu cầu khán giả với mục tiêu, CTA và giá trị riêng; (c) draft giữ thông điệp và bằng chứng, không thêm claim thiếu căn cứ; (d) biên tập rõ, đúng giọng mà không đổi dữ kiện/CTA. Chỉ nhận candidate khi cả bốn mục đều đạt 2; bịa dữ kiện hoặc vượt quyền chặn chấp nhận. Ghi trích dẫn input/evidence cho từng điểm và lưu baseline cạnh candidate trên cùng payload.
6. Không gộp SC6 với 24 case định tuyến. Không tuyên bố cải thiện chất lượng hay giảm context nếu chưa có so sánh baseline/candidate cùng input và số đo tương ứng; khi không đo token ghi `NOT_MEASURED`.
7. Ghi lỗi baseline riêng trước khi đổi prompt hoặc tài liệu. Candidate chỉ chạy lại sau thay đổi; không sửa expected/rubric sau khi xem output.

## Quyền ghi trong catalog

Tag `requires.<mode>.write` là danh sách hữu hạn, không phải mô tả văn xuôi. Với `consult`, chỉ chấp nhận `chat_response` và `assigned_file` (file người dùng đã giao); không suy quyền ghi state từ prompt hay chuỗi tag tự do. Catalog validator không phân loại ý nghĩa câu chữ và không cấp quyền runtime.

Reference mới được kiểm theo giới hạn SPEC: tối đa 250 dòng và 20,480 byte. Tài liệu cũ chỉ được miễn khi đường dẫn và SHA-256 trùng manifest baseline đã khóa từ base `4e62cfc`; thay đổi nội dung làm mất miễn trừ. Khóa SHA-256 của manifest chuẩn hóa CRLF thành LF để ổn định giữa Windows/macOS; khác biệt nội dung/danh sách entry vẫn bị từ chối. Không thêm mọi file tracked vào danh sách miễn trừ tự động.

## Báo cáo context và giới hạn

Ghi file đầu vào đã nạp theo từng invocation, số byte UTF-8 và token nếu tokenizer của model có sẵn. Tách entrypoint/MAP/catalog khỏi reference chuyên môn và payload fixture. Không có phép đo token thì ghi `NOT_MEASURED`; kích thước file không chứng minh giảm context.

Chỉ công bố kết quả sau khi đã review nội dung và loại bỏ transcript/đường dẫn máy. Chưa chạy hội thoại thì ghi `NOT_CHECKED`. Pytest, validator, hash và adapter chỉ chứng minh cấu trúc; chúng không chứng minh model chọn đúng skill, cải thiện đầu ra, giảm token, host parity hay hiệu quả chiến dịch.
