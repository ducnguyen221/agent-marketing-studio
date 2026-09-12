#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Kho CỔNG DUYỆT — nơi DUY NHẤT ghi ba cổng, và mặt tiền TRONG PHIÊN.

## Vì sao có file này

Trước 12/09/2026, người ghi `g1` và `g3` duy nhất là `approve_bus.py` — mặt tiền Telegram.
Nghĩa là **Telegram không phải tuỳ chọn, nó là con đường duy nhất**: không có điện thoại
thì cả chiến dịch đứng. Mà cách làm việc mặc định lại là người ngồi cùng agent trong một
phiên, đọc file trên máy rồi gật ngay tại chỗ.

Nên tách làm hai tầng:

```
        mặt tiền                       kho cổng                  chỗ ở thật
  approve_bus.py  (Telegram) ─┐
                              ├─► approval_gate.open_gate() ─► campaign.md · publish.json
  approval_gate.py   (trong phiên)┘
```

Hai mặt tiền NGANG HÀNG. Cái nào cũng ghi vào đúng một chỗ, đúng một cách, cùng để lại
dấu vết trong `logs/events.jsonl`. Thêm mặt tiền thứ ba (web, CLI khác) chỉ cần gọi vào
đây, không được đẻ kho cổng riêng.

## Cổng ở đâu

| Cổng | Chỗ ở thật | Hàm ghi |
|---|---|---|
| **g1** — duyệt đề tài | cột `g1` + `status=approved` trong bảng Content của `campaign.md` | `write_g1` |
| **g2** — duyệt trước khi đăng | `publish.json → posts[].review` (+ ô `g2` mirror) | `write_g2` → gọi `register_publish approve` |
| **g3** — duyệt BẢN THẬT trên web | cột `g3` trong bảng Content | `write_column` |

Không đẻ kho phê duyệt thứ hai. Hai nguồn sự thật thì sớm muộn chúng nói khác nhau.

## Hai điều bắt buộc khi mở cổng

1. **`boi`** — AI duyệt. Cổng không có tên người là cổng vô chủ.
2. **`quote`** — NGUYÊN VĂN câu người nói. Không phải để đẹp hồ sơ: đây là thứ ngăn
   agent tự đóng dấu thay người. Agent chép được câu của người thì câu đó phải đã tồn tại.
   Cùng luật với `register_publish approve --note`, đặt ra từ 04/09/2026.

⚠️ **KHÔNG xếp việc.** Mở cổng xong có chạy tiếp hay không là quyết định của MẶT TIỀN:
Telegram xếp việc cho thợ chạy nền, còn agent trong phiên thường chạy bước kế tiếp ngay.
Gộp hai thứ vào đây thì một trong hai đường sẽ làm việc hai lần.

## Lệnh (dùng trong phiên, không cần Telegram)

```
approval_gate.py <chiến dịch> cho     --gate g1|g2|g3 [--json]
approval_gate.py <chiến dịch> open    --gate g1|g2|g3 --post A,B --by "Đức" --quote "..."
approval_gate.py <chiến dịch> reject --gate g1|g2|g3 --post A   --by "Đức" --quote "..."
```

`pending` in kèm **đường dẫn file để mở** — đó là thứ người cần để duyệt thật thay vì gật bừa.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "lib"))
import post_content  # noqa: E402
import md_io  # noqa: E402
import event_log as EV  # noqa: E402

GATES = ("g1", "g2", "g3")

# Tên file giữ tiền tố `tg-` vì LÝ DO DỮ LIỆU: chiến dịch đang chạy có sẵn file này, đổi
# tên là bỏ lại toàn bộ phản hồi cũ. Nội dung thì không riêng của Telegram nữa — phản hồi
# gõ trong phiên cũng vào đây, và vòng viết lại đọc chung một chỗ.
FEEDBACK_FILE = "feedback.json"


def loi(m: str) -> None:
    sys.stderr.write(f"approval_gate: {m}\n")


# ── Bảng Content ────────────────────────────────────────────────────────────

def read_content_table(campaign: Path):
    fm, than = md_io.read_fm(Path(campaign) / "campaign.md")
    col, row = md_io.read_table(than, "CONTENT")
    return fm, than, col, row


def post_has_content(campaign: Path, row: dict) -> bool:
    """Bài của DÒNG này đã có chữ thật chưa. Không khai `folder` = chưa viết (fail-closed)."""
    f = (row.get("folder") or "").strip()
    if not f:
        return False
    return post_content.has_content(Path(campaign) / f.lstrip("./"))


def why_not_ready(campaign: Path, row: dict) -> str:
    """Lý do bài này CHƯA được phép đem ra hỏi ở Cổng 2. Chuỗi rỗng = được hỏi.

    FAIL-CLOSED ba nhánh (Đức chốt 11/09/2026):
      · chưa viết          — không có gì để đọc
      · chưa chấm cổng nào — KHÔNG ĐO ĐƯỢC nghĩa là *chưa biết*, không phải *đã qua*
      · máy chấm ĐỎ        — máy đã nói không thì đừng đem hỏi người

    Vì sao nhánh giữa quan trọng ngang nhánh cuối: `content.md` đầy đủ **không** chứng minh
    bài đã qua kiểm. Ca thật NEN-002 — gọi thẳng bộ viết, nhảy cóc bước chấm B4, file bài
    trông hoàn hảo mà chưa một cổng nào chạy.

    Trả LÝ DO chứ không trả bool: bỏ qua im lặng thì người vận hành không biết vì sao bài
    của mình không bao giờ tới cổng.
    """
    if not post_has_content(campaign, row):
        return "CHƯA VIẾT"

    f = (row.get("folder") or "").strip()
    p = Path(campaign) / f.lstrip("./") / "gates.json"
    if not p.is_file():
        return "CHƯA CHẤM cổng nào (thiếu gates.json) — chạy blog_gates.py trước"
    try:
        g = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "gates.json HỎNG — coi như chưa chấm"

    if (g.get("verdict") or "").lower() == "fail":
        do = [c.get("job_id", "?") for c in (g.get("gate") or [])
              if c.get("status") == "fail" and c.get("level") != "warn"]
        return (f"máy chấm ĐỎ ({g.get('fail_block', '?')} cổng chặn"
                + (f": {', '.join(do[:8])}" if do else "") + ")")
    return ""


def waiting_at(campaign: Path, gate: str) -> list[dict]:
    """Bài đang chờ đúng cổng đó. g1: chưa có g1. g2: có g1, chưa có g2."""
    _, _, _, row = read_content_table(campaign)
    if gate == "g1":
        return [d for d in row if not (d.get("g1") or "").strip()]
    if gate == "g3":
        # Cổng 3 duyệt BẢN THẬT: phải đã lên web mới có gì để xem. Và chỉ hỏi khi bảng
        # CÓ KHAI cột `g3` — bảng cũ không khai thì không có cổng này.
        return [d for d in row
                if "g3" in d and (d.get("web") or "").strip()
                and not (d.get("g3") or "").strip()]
    return [d for d in row
            if (d.get("g1") or "").strip() and not (d.get("g2") or "").strip()]


def post_files(campaign: Path, row: dict) -> dict:
    """Bài này có những file NÀO ĐANG CÓ THẬT để người mở ra kiểm.

    Đây là phần hay bị bỏ quên nhất của một cổng duyệt: hỏi "duyệt không?" mà không nói
    đọc ở đâu thì người chỉ còn cách gật bừa, và cổng thành con dấu cao su — đúng chỗ
    Cổng 2 đã dính ngày 11/09/2026.

    Chỉ liệt kê file **tồn tại**. Kê một đường dẫn không có thật còn tệ hơn không kê:
    người mở không được sẽ tưởng máy hỏng chứ không hiểu là bước đó chưa chạy.
    """
    campaign = Path(campaign)
    f = (row.get("folder") or "").strip().lstrip("./")
    ho_so: dict = {"content_id": row.get("content_id", ""),
                   "content_name": row.get("content_name", ""),
                   "folder": f, "file": {}, "web": (row.get("web") or "").strip()}
    if not f:
        return ho_so
    post = campaign / f
    for label, tuong_doi in (("bài", "content.md"),
                            ("nghiên cứu", "research.md"),
                            ("chấm cổng", "gates.json"),
                            ("blog tách kênh", "atlas/blog.md"),
                            ("trang dựng sẵn", "atlas/atlas.html"),
                            ("facebook", "facebook/post.txt"),
                            ("youtube", "youtube/description.txt")):
        p = post / tuong_doi
        if p.is_file():
            ho_so["file"][label] = str(p)
    return ho_so


# ── Phản hồi của người ──────────────────────────────────────────────────────

def read_feedback(campaign: Path, cid: str) -> list[dict]:
    """Mọi phản hồi của người cho một bài, theo thứ tự thời gian.

    GIỮ ĐỦ, không ghi đè: vòng viết lại có thể lặp, và ghi đè lần trước là mất dấu vết vì
    sao bài thành ra như thế. Sáu tháng sau đọc lại còn hiểu được.
    """
    p = Path(campaign) / "logs" / FEEDBACK_FILE
    if not p.is_file():
        return []
    try:
        return (json.loads(p.read_text(encoding="utf-8")) or {}).get(cid, [])
    except json.JSONDecodeError:
        loi(f"{p} hỏng — coi như chưa có phản hồi nào.")
        return []


def write_feedback(campaign: Path, cid: str, text: str) -> None:
    p = Path(campaign) / "logs" / FEEDBACK_FILE
    d = {}
    if p.is_file():
        try:
            d = json.loads(p.read_text(encoding="utf-8")) or {}
        except json.JSONDecodeError:
            pass
    d.setdefault(cid, []).append(
        {"at": datetime.now().astimezone().isoformat(), "text": text})
    p.parent.mkdir(parents=True, exist_ok=True)
    md_io.write_atomic(p, json.dumps(d, ensure_ascii=False, indent=2) + "\n")


# ── Ghi cổng ────────────────────────────────────────────────────────────────

def write_g1(campaign: Path, cids: list[str], day: str) -> list[str]:
    """Ghi cột g1 + status. IDEMPOTENT: bài đã có g1 thì bỏ qua, không ghi đè."""
    campaign = Path(campaign)
    fm, than, _, row = read_content_table(campaign)
    hien = {d["content_id"]: d for d in row}
    done = []
    for cid in cids:
        d = hien.get(cid)
        if d is None:
            loi(f"{cid}: không có trong bảng Content — bỏ qua.")
            continue
        if (d.get("g1") or "").strip():
            continue                       # đã duyệt rồi, không ghi lại
        than = md_io.upsert_row(than, "CONTENT", "content_id",
                                {"content_id": cid, "g1": day, "status": "approved"},
                                chi_cap_nhat=True)
        done.append(cid)
    if done:
        md_io.write_fm(campaign / "campaign.md", fm, than)
    return done


def write_column(campaign: Path, cids: list[str], col: str, gia_tri: str) -> list[str]:
    """Ghi một cột ngày duyệt. IDEMPOTENT: đã có thì bỏ qua, không ghi đè."""
    campaign = Path(campaign)
    fm, than, _, row = read_content_table(campaign)
    hien = {d["content_id"]: d for d in row}
    done = []
    for cid in cids:
        d = hien.get(cid)
        if d is None:
            loi(f"{cid}: không có trong bảng Content — bỏ qua.")
            continue
        if (d.get(col) or "").strip():
            continue
        than = md_io.upsert_row(than, "CONTENT", "content_id",
                                {"content_id": cid, col: gia_tri}, chi_cap_nhat=True)
        done.append(cid)
    if done:
        md_io.write_fm(campaign / "campaign.md", fm, than)
    return done


def write_g2(campaign: Path, cids: list[str], by: str, note: str) -> list[str]:
    """Gọi ĐÚNG `register_publish approve` — giữ nguyên dấu vết duyệt đang có."""
    campaign = Path(campaign)
    _, _, _, row = read_content_table(campaign)
    hien = {d["content_id"]: d for d in row}
    rp = _HERE / "register_publish.py"
    done = []
    for cid in cids:
        d = hien.get(cid)
        if d is None:
            loi(f"{cid}: không có trong bảng Content — bỏ qua.")
            continue
        folder = (d.get("folder") or "").strip().lstrip("./")
        post = campaign / folder
        if not post.is_dir():
            loi(f"{cid}: không thấy thư mục bài {post} — bỏ qua.")
            continue
        r = subprocess.run(
            [sys.executable, str(rp), str(post), "approve", "--by", by, "--note", note],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            loi(f"{cid}: register_publish approve thất bại — {r.stdout}{r.stderr}")
            continue
        done.append(cid)
    return done


# ── Mở / từ chối cổng — lối vào DUY NHẤT của mọi mặt tiền ───────────────────

def _require_witness(by: str, quote: str) -> None:
    """Cổng phải biết AI duyệt và người đó nói GÌ. Thiếu một trong hai là ném lỗi.

    Fail-closed chứ không cảnh báo rồi ghi: một cổng ghi được mà không có chứng nhân thì
    hồ sơ nói "đã duyệt" trong khi không ai duyệt, và không gì phát hiện ra sau đó.
    """
    if not (by or "").strip():
        raise ValueError("thiếu `boi`: cổng phải biết AI duyệt.")
    if not (quote or "").strip():
        raise ValueError(
            "thiếu `quote`: chép NGUYÊN VĂN câu duyệt của người. "
            "Đây là thứ ngăn agent tự đóng dấu thay người.")


def open_gate(campaign: Path, gate: str, cids: list[str], *, by: str, quote: str,
            via: str, now: datetime | None = None) -> list[str]:
    """Mở một cổng cho các bài đã nêu. Trả về danh sách bài THỰC SỰ được ghi.

    Idempotent: bài đã qua cổng thì không nằm trong kết quả và không sinh sự kiện mới.
    KHÔNG xếp việc — xem cảnh báo ở đầu file.
    """
    campaign = Path(campaign)
    if gate not in GATES:
        raise ValueError(f"cổng lạ: {gate!r} — chỉ có {', '.join(GATES)}")
    _require_witness(by, quote)
    now = now or datetime.now().astimezone()

    if gate == "g1":
        done = write_g1(campaign, cids, now.date().isoformat())
    elif gate == "g3":
        done = write_column(campaign, cids, "g3", now.date().isoformat())
    else:
        done = write_g2(campaign, cids, by, quote)

    for cid in done:
        EV.write(campaign, f"{gate}_approved", post=cid, by=by, via=via, note=quote[:300])
    return done


def reject(campaign: Path, gate: str, cids: list[str], *, by: str, quote: str,
            via: str) -> list[str]:
    """Ghi từ chối + phản hồi. KHÔNG đụng vào cổng: từ chối là *chưa duyệt*, không phải xoá.

    Phản hồi vào kho chung để vòng viết lại đọc được. Từ chối mà không nói vì sao thì lần
    viết lại sau cũng ra đúng bài cũ.
    """
    campaign = Path(campaign)
    if gate not in GATES:
        raise ValueError(f"cổng lạ: {gate!r} — chỉ có {', '.join(GATES)}")
    _require_witness(by, quote)
    for cid in cids:
        EV.write(campaign, f"{gate}_rejected", post=cid, by=by, via=via, reason=quote[:300])
        write_feedback(campaign, cid, quote)
    return list(cids)


# ── CLI trong phiên ─────────────────────────────────────────────────────────

def _print_waiting(campaign: Path, gate: str, *, ra_json: bool) -> int:
    ds = waiting_at(campaign, gate)
    ho_so = []
    for d in ds:
        h = post_files(campaign, d)
        if gate == "g2":
            h["not_ready"] = why_not_ready(campaign, d)
        ho_so.append(h)

    if ra_json:
        print(json.dumps({"gate": gate, "count": len(ho_so), "post": ho_so},
                         ensure_ascii=False, indent=2))
        return 0

    if not ho_so:
        print(f"{gate}: không bài nào đang chờ.")
        return 0

    # TÁCH HAI NHÓM. Cổng 2 gọi là "đang chờ" cả những bài mới chỉ có dòng trong bảng —
    # chúng chưa viết nên không có file nào để mở. Trộn chung thì một lô 20 bài đổ ra 20
    # mục dài, người phải tự dò xem mục nào thật sự cần đọc. Bản JSON giữ nguyên cả hai
    # nhóm: máy không cần được chiều, người thì cần.
    ready = [h for h in ho_so if not h.get("not_ready")]
    chua = [h for h in ho_so if h.get("not_ready")]

    print(f"{gate}: {len(ready)}/{len(ho_so)} bài sẵn sàng hỏi\n")
    for h in ready:
        print(f"· {h['content_id']} — {h['content_name']}")
        for label, p in h["file"].items():
            print(f"    {label:<16} {p}")
        if h["web"]:
            print(f"    {'bản thật':<16} {h['web']}")
        print()
    if chua:
        print(f"Chưa được đem ra hỏi ({len(chua)} bài):")
        for h in chua:
            print(f"  ⛔ {h['content_id']:<10} {h['not_ready']}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Cổng duyệt — mặt tiền TRONG PHIÊN, không cần Telegram.")
    ap.add_argument("campaign", help="thư mục chiến dịch")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("waiting", help="bài nào đang chờ cổng, kèm file để mở kiểm")
    pc.add_argument("--gate", choices=list(GATES), required=True)
    pc.add_argument("--json", action="store_true")

    for name, tro in (("open", "mở cổng"), ("reject", "ghi từ chối + phản hồi")):
        p = sub.add_parser(name, help=tro)
        p.add_argument("--gate", choices=list(GATES), required=True)
        p.add_argument("--post", required=True, help="mã bài, phân tách bằng dấu phẩy")
        p.add_argument("--by", required=True, help="ai duyệt")
        p.add_argument("--quote", required=True,
                       help="NGUYÊN VĂN câu người nói — agent KHÔNG được tự bịa")
        p.add_argument("--via", default="phiên", help="mặt tiền nào (mặc định: phiên)")

    a = ap.parse_args(argv)
    campaign = Path(a.campaign)
    if not (campaign / "campaign.md").is_file():
        loi(f"không thấy {campaign / 'campaign.md'}")
        return 2

    if a.cmd == "waiting":
        return _print_waiting(campaign, a.gate, ra_json=a.json)

    cids = [x.strip() for x in a.post.split(",") if x.strip()]
    if not cids:
        loi("--post rỗng")
        return 2
    try:
        if a.cmd == "open":
            done = open_gate(campaign, a.gate, cids, by=a.by,
                           quote=a.quote, via=a.via)
            print(f"{a.gate}: đã mở cho {len(done)}/{len(cids)} bài"
                  + (f" — {', '.join(done)}" if done else " (không bài nào đổi)"))
        else:
            done = reject(campaign, a.gate, cids, by=a.by,
                           quote=a.quote, via=a.via)
            print(f"{a.gate}: đã ghi từ chối {len(done)} bài — {', '.join(done)}")
    except ValueError as e:
        loi(str(e))
        return 2
    # Không bài nào đổi ≠ hỏng: idempotent nghĩa là chạy lại vẫn 0.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
