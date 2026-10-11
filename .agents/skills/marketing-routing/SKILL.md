---
name: marketing-routing
description: >
  Route marketing requests by scope, current state, and desired output; clarify missing brief
  details and preserve existing approval gates. Use when the right capability is unclear.
---

# Marketing Routing

## Mục đích
Chọn một skill chính và tối đa hai skill hỗ trợ có lý do. Đây là hướng dẫn đọc và quyết định, không phải bộ phân loại runtime hay quyền thực thi.

## Dùng khi / không dùng khi
- Dùng khi yêu cầu chưa gọi rõ skill phù hợp, có nhiều hướng, hoặc cần quyết định bước tiếp theo.
- Nếu người dùng gọi rõ một skill phù hợp, kiểm phần catalog liên quan rồi đi thẳng vào skill đó.
- Không dùng để tự duyệt G1/G2/G3, ghi trạng thái, đăng bài hoặc gọi skill con theo vòng.

## Đầu vào và trao đổi
Đọc yêu cầu, phạm vi, trạng thái và nguồn được giao. Chỉ đối chiếu `knowledge/data_model/DATA_MODEL.md` khi cần phân định field, trạng thái hoặc cổng của campaign; dùng hội thoại theo [`references/consultation.md`](references/consultation.md). Phản chiếu mục tiêu và bằng chứng trước khi hỏi phần còn thiếu; gom câu hỏi quyết định trong một lượt, rồi dùng câu trả lời đã có.

## Các bước
1. Xác định phạm vi: tư vấn độc lập, campaign, draft độc lập, hoặc trạng thái của một campaign/post.
2. Xác định trạng thái hiện tại và điều kiện/cổng áp dụng; đọc hiện trạng được phép dù chưa qua cổng.
3. Tìm thông tin còn thiếu có thể đổi quyết định. Nếu hướng đi mơ hồ, nêu 2–3 cách hiểu rồi hỏi một câu chọn hướng.
4. Chọn theo đầu ra cần có, không theo từ khóa trong tài liệu. Tra catalog cho `use_when`, `do_not_use_when`, `modes`, `requires`, `references` và `supports`.
5. Chọn một skill chính, thêm tối đa hai hỗ trợ chỉ khi bước hiện tại cần chúng. Không chọn router làm hỗ trợ; không mở toàn bộ references.
6. Nếu không có skill phù hợp, kiểm MAP để tìm role/workflow hiện có; chỉ chuyển sang đó khi tài liệu thật hỗ trợ yêu cầu. Nếu không có nguồn/chuyên môn áp dụng được, nêu giới hạn. Không bịa fallback, không trỏ tới đường dẫn chưa tồn tại.
7. Trình bày nhu cầu, dữ kiện còn thiếu, skill chính/hỗ trợ kèm lý do, tài liệu cần đọc ngay, bước tiếp theo và điều kiện dừng.

## Ranh giới
- `consult`: trả lời trong chat hoặc file được giao; không tạo trạm/campaign/post, không ghi trạng thái.
- `prepare`: làm rõ brief và đề xuất; chỉ tạo artifact bằng script hiện có khi đủ đầu vào, đường dẫn và phạm vi. Dừng trước sản xuất phụ thuộc G1.
- `execute`: đọc tài liệu/trạng thái của khâu hiện tại và chỉ làm khi điều kiện/cổng tương ứng đạt.
- Hỏi tư vấn không mở hoặc đánh dấu G1/G2/G3. Campaign chưa G1 vẫn có thể được đọc/chẩn đoán; nội dung phụ thuộc campaign chưa được sản xuất.
- Draft độc lập không tạo campaign/post hay trạng thái. Draft thuộc campaign luôn theo mode campaign và cổng hiện hành; không dùng sửa chữ để né G1.
- Lập kế hoạch đo trước publish là tư vấn/chuẩn bị; số thực chỉ cập nhật ở measure sau publish.

## Kiểm chất lượng và dừng
Kiểm tra skill có thật, mode khai báo, đầu vào/đầu ra và references liên quan trong catalog. Dừng phần phụ thuộc nếu thiếu nguồn, đường dẫn, quyết định quan trọng hoặc điều kiện cổng; nói rõ điều đang thiếu và bước hợp lệ kế tiếp.
