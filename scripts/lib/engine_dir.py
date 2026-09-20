# -*- coding: utf-8 -*-
"""Luật MỘT CÂU của `<trạm>/engine`: **hoặc không tồn tại, hoặc đủ bộ chạy.**

Không có trạng thái giữa, và đây là lý do:

`run.ps1` — file GIỐNG HỆT NHAU ở mọi chiến dịch — coi **sự tồn tại** của `<trạm>/engine`
là tín hiệu "engine đã dọn về trạm". Thấy thư mục thì nó **bỏ đường lùi** sang engine dùng
chung trong thư mục nhà của máy nguồn, rồi tìm runner **trong đó**:

    if (-not (Test-Path $engine)) { ...đường lùi... }      # chỉ hỏi CÓ hay KHÔNG
    $runner = Join-Path $engine $cfg.runner                # rồi tìm runner ở đây

Nghĩa là thư mục `engine/` mang **ngữ nghĩa điều khiển**, không phải chỗ chứa file. Một
thư mục rỗng — hay một thư mục ra đời vì ai đó ghi một file JSON vào `<trạm>/engine/x.json`,
và lệnh ghi file tự `mkdir` cha — bật đúng cái nhánh "đã dọn xong" trong khi chưa dọn gì.

Đêm 20→21/09/2026 đã xảy ra đúng thế: 5 task tin theo lịch sẽ `exit 2` ("khong thay
runner"), lượt đầu dính là 21/09 19:00. Nó **im lặng** (không lệnh nào báo lỗi lúc thư mục
ra đời), **hoãn** (hậu quả rơi vào lượt lịch kế tiếp, ở một tiến trình khác) và **lan**
(một thư mục tắt đường lùi của tất cả chiến dịch cùng lúc). Phát hiện được chỉ vì mọi gói
chạm trạm đều phải báo `Test-Path <trạm>/engine`.

## Cổng chỉ nói cái nó ĐO ĐƯỢC

Nó không biết ai tạo thư mục kia và không được đoán. Nó đo **trạng thái** — có mặt mà
thiếu runner — rồi nêu **hai** đường sửa, để người đọc chọn bằng thứ họ biết mà cổng không
biết: dời nội dung đi và xoá thư mục (đường lùi sống lại), hay chép nốt bộ chạy vào.

Mã thoát 2 (`CONTRACT_ERROR` — "cấu hình SAI, phải sửa") chứ không phải 3 ("cài tiếp"):
đó đúng là mã `run.ps1` sẽ trả lúc 19:00. Cổng trả mã khác cái thực tế sẽ trả thì người
đọc không nối được hai chuyện với nhau.

Dùng ở hai nơi, một luật: `scripts/pipeline/check_engine.py` (chạy tay, chạy trong CI) và
`doctor` (`kham_engine`). Test: `tests/test_engine_dir.py`.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import studio_contract as SC  # noqa: E402
import studio_paths as SP  # noqa: E402

# Tên thư mục engine — cố định, `run.ps1` viết thẳng `Join-Path $station 'engine'`.
TEN_ENGINE = "engine"

# Bộ chạy TỐI THIỂU. Đây là DỮ LIỆU: thêm runner vào bộ là sửa một dòng, không phải sửa
# luồng. Giữ ở mức tối thiểu có chủ đích — cổng này chặn "thư mục có mà rỗng ruột", không
# phải kiểm kê đầy đủ bộ chạy (việc đó là của `station_manifest.DEM_HA_TANG`).
RUNNER_BAT_BUOC = ("run-toptoday-hot.ps1",)

# Chỗ ĐÚNG cho cấu hình theo máy: không mang nghĩa nào với `run.ps1`.
THU_MUC_CAU_HINH = "_agent-call"

# Bao nhiêu tên được liệt ra khi báo "đang có gì trong đó". Đủ để nhận ra thư mục, không
# đủ để dòng báo thành một lượt `ls`.
_TOI_DA_LIET = 8


def duong(station=None) -> Path:
    """`<trạm>/engine` — chỉ ghép đường, không đụng đĩa."""
    return SP.root(station) / TEN_ENGINE


def _dang_co(eng: Path) -> list[str]:
    try:
        return sorted(p.name + ("/" if p.is_dir() else "") for p in eng.iterdir())
    except OSError:
        return []


def kiem(station=None) -> dict:
    """Khám `<trạm>/engine`.

    -> {"ok", "code", "state", "engine", "missing", "found", "fail"}
       state ∈ `vang` (không có thư mục) · `du` (đủ bộ chạy) · `thieu-runner` ·
               `khong-phai-thu-muc`.
    """
    eng = duong(station)
    ra = {"ok": True, "code": SC.OK, "state": "vang", "engine": str(eng),
          "missing": [], "found": [], "fail": []}

    if not eng.exists():
        return ra

    if not eng.is_dir():
        ra.update(ok=False, code=SC.CONTRACT_ERROR, state="khong-phai-thu-muc",
                  fail=[f"{eng} tồn tại nhưng KHÔNG phải thư mục. `run.ps1` chỉ hỏi "
                        f"`Test-Path` nên nó vẫn coi đây là engine đã dọn về trạm, bỏ đường "
                        f"lùi, rồi không tìm nổi runner nào ⇒ mọi lượt theo lịch thoát mã 2. "
                        f"Xoá hoặc đổi tên file này."])
        return ra

    co = _dang_co(eng)
    thieu = [r for r in RUNNER_BAT_BUOC if not (eng / r).is_file()]
    ra["found"] = co
    if not thieu:
        ra["state"] = "du"
        return ra

    liet = ", ".join(co[:_TOI_DA_LIET]) + ("…" if len(co) > _TOI_DA_LIET else "")
    ra.update(ok=False, code=SC.CONTRACT_ERROR, state="thieu-runner", missing=thieu,
              fail=[f"{eng} tồn tại nhưng thiếu runner bắt buộc: {', '.join(thieu)} "
                    f"(đang có: {liet or '(rỗng)'}). "
                    f"`run.ps1` của MỌI chiến dịch coi sự TỒN TẠI của thư mục này là tín "
                    f"hiệu 'engine đã dọn về trạm': nó bỏ đường lùi sang engine dùng chung "
                    f"rồi tìm runner trong đây ⇒ mọi lượt theo lịch thoát mã 2, và không có "
                    f"gì báo cho tới lượt lịch kế tiếp. "
                    f"Sửa MỘT trong hai cách: "
                    f"(a) thư mục ra đời ngoài ý muốn (một lệnh ghi file tự tạo nó) — dời "
                    f"nội dung sang <trạm>/{THU_MUC_CAU_HINH}/ rồi xoá thư mục "
                    f"{TEN_ENGINE}/, đường lùi sống lại; "
                    f"(b) engine THẬT SỰ đã dời về trạm — chép nốt bộ chạy vào đây "
                    f"({', '.join(RUNNER_BAT_BUOC)})."])
    return ra
