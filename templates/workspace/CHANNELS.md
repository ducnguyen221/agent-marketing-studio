---
schema: channels/1
updated: 2026-01-01
channels: []
# Mỗi kênh MỘT mục, `new_channel.py` tự thêm vào đây. Hình dạng một mục:
#   - id: ten-kenh
#     label: "Tên kênh đọc được"
#     path: ./ten-kenh        # hoặc D:/duong/dan/rieng — kênh KHÔNG bắt buộc nằm trong trạm
#     status: active          # active | paused | archived
#     note: ""
# Danh sách rỗng là trạng thái HỢP LỆ của một trạm vừa dựng: khai sẵn một kênh mẫu chưa
# tồn tại thì `check_tree.py` đỏ ngay từ phút đầu vì một đường dẫn không có thật.
---

# Sổ kênh

> **Một dòng mỗi kênh, kể cả kênh nằm ngoài thư mục này.** Mọi script tìm kênh qua file
> này chứ không dò thư mục — dò thư mục thì kênh để ở ổ khác trở nên vô hình, và vô hình
> một cách im lặng.
>
> Thêm kênh: `new_channel.py`. Nó **hỏi** bạn muốn lưu kênh ở đâu và không có giá trị mặc
> định — chỗ lưu là quyết định của người, không phải của máy.
> Dời thư mục kênh thì sửa `path` ở đây, rồi chạy `check_tree.py` để chắc đường còn sống.
