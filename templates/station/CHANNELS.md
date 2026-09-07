---
schema: channels/1
updated: 2026-01-01
channels:
  - id: ten-kenh
    label: "Tên kênh đọc được"
    path: ./ten-kenh          # hoặc D:/duong/dan/rieng — kênh KHÔNG bắt buộc nằm trong STATION
    status: active            # active | paused | archived
    note: ""
---

# Sổ kênh

> **Một dòng mỗi kênh, kể cả kênh nằm ngoài thư mục này.** Mọi script tìm kênh qua file
> này chứ không dò thư mục — dò thư mục thì kênh để ở ổ khác trở nên vô hình, và vô hình
> một cách im lặng.
>
> Thêm kênh: `new_channel.py`. Nó **hỏi** bạn muốn lưu kênh ở đâu và không có giá trị mặc
> định — chỗ lưu là quyết định của người, không phải của máy.
> Dời thư mục kênh thì sửa `path` ở đây, rồi chạy `check_tree.py` để chắc đường còn sống.

## ten-kenh
Kênh này của ai, đăng ở đâu, vì sao tách riêng.
