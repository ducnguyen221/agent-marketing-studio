# -*- coding: utf-8 -*-
"""Gốc bộ test: `pytest` TRẦN ở gốc repo chỉ được gom test của REPO.

Máy đã cài `embedded` có `workspace/` ngay trong repo — và trạm là nội dung của người dùng,
có thể mang script + test riêng của họ (vd `workspace/<kênh>/test_*.py` cần `numpy`). Không
có dòng dưới thì `pytest` trần gom luôn chúng: bộ test của repo đỏ vì thư viện của trạm,
xanh trên CI checkout sạch và đỏ trên mọi máy chạy thật — đúng chỗ không ai muốn đỏ giả.

`.venv` (venv của bộ cài) cũng không bao giờ là test của repo. File này đứng ở GỐC (không
phải `tests/`) vì chỉ ở đây `collect_ignore` mới áp cho thư mục anh em của `tests/`; và
không dùng `[tool.pytest.ini_options]` trong `pyproject.toml` — xem chú thích ở đó.
Cổng: `tests/test_pytest_tran.py`, và job CI "cài embedded rồi pytest".
"""

collect_ignore = ["workspace", ".venv"]
