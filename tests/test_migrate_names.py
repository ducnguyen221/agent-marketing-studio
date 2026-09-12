# -*- coding: utf-8 -*-
"""`scripts/pipeline/migrate_names.py` — di trú DỮ LIỆU TRÊN ĐĨA sang bộ tên tiếng Anh.

Di trú là loại script chỉ chạy một lần trong đời, nên nó là loại dễ sai nhất: không ai
chạy nó đủ nhiều để phát hiện lỗi. Bốn thứ file này canh:

· **Không xoá nguồn khi chưa ghi được bản mới.** Sai mà đã xoá thì không còn đường lùi.
· **Chạy lại được.** Di trú hay bị ngắt giữa chừng; lần hai phải đi tiếp, không được nhân đôi.
· **`--dry-run` KHÔNG đụng đĩa.** In ra rồi mới làm là cách duy nhất soi trước được.
· **Dòng hỏng thì chép nguyên.** Sổ sự kiện là bằng chứng, không phải chỗ để sửa văn bản.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import migrate_names as MG  # noqa: E402
import work_queue as WQ  # noqa: E402

FM = """---
schema: campaign/1
id: CD-THU
channel: kenh-thu
id_prefix: T
name: Thử
---

# Thử
"""


def _cu(tmp_path):
    """Một chiến dịch mang ĐÚNG hình dạng cũ: thư mục, khoá và giá trị tiếng Việt."""
    campaign = tmp_path / "CD-THU"
    (campaign / "logs" / "viec" / "cho").mkdir(parents=True)
    (campaign / "logs" / "viec" / "xong").mkdir(parents=True)
    (campaign / "campaign.md").write_text(FM, encoding="utf-8", newline="\n")

    (campaign / "logs" / "su-kien.jsonl").write_text(
        json.dumps({"luc": "2026-09-01T10:00:00+07:00", "viec": "g1_duyet",
                    "bai": "T-001", "boi": "Đức", "qua": "phiên"}, ensure_ascii=False)
        + "\n"
        + json.dumps({"luc": "2026-09-01T11:00:00+07:00", "viec": "viec_hong",
                      "bai": "T-001", "buoc": "cham-cong", "ly_do": "x",
                      "se_thu_lai": True}, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n")

    (campaign / "logs" / "viec" / "cho" / "j1.json").write_text(
        json.dumps({"ma": "j1", "viec": "tiep", "bai": "T-001", "so_lan": 0,
                    "tao_luc": "2026-09-01T10:00:00+07:00", "nguon": "g1_duyet"},
                   ensure_ascii=False), encoding="utf-8", newline="\n")

    bai = campaign / "T-001_mot"
    bai.mkdir()
    (bai / "gates.json").write_text(json.dumps({
        "thu_muc": str(bai), "mien_tru": {}, "tong": 2, "xanh": 1, "do_chan": 1,
        "ket_luan": "do",
        "cong": [{"ma": "G01", "cong": "Độ dài", "do_duoc": 100, "luat": "2500-4000",
                  "trang_thai": "do", "muc": "chan", "ghi_chu": ""}]},
        ensure_ascii=False), encoding="utf-8", newline="\n")
    (bai / ".viet-lan.json").write_text('{"so_lan": 2}', encoding="utf-8", newline="\n")
    (campaign / "logs" / "tg-phan-hoi.json").write_text(
        json.dumps({"T-001": [{"luc": "2026-09-01T12:00:00+07:00", "noi_dung": "sửa"}]},
                   ensure_ascii=False), encoding="utf-8", newline="\n")
    (campaign / "logs" / "tg-approve.json").write_text(
        json.dumps({"offset": 42, "cho": {"tok": {"cong": "g1"}}}),
        encoding="utf-8", newline="\n")
    return campaign


# ── dry-run ─────────────────────────────────────────────────────────────────

def test_dry_run_KHONG_dung_vao_dia(tmp_path):
    """Không xem trước được thì không ai dám chạy — mà không chạy thì dữ liệu kẹt luôn."""
    campaign = _cu(tmp_path)
    viec = MG.di_tru(campaign, that=False)
    assert viec, "không liệt kê được việc nào"
    assert (campaign / "logs" / "su-kien.jsonl").is_file()
    assert not (campaign / "logs" / "events.jsonl").exists()
    assert (campaign / "logs" / "viec" / "cho" / "j1.json").is_file()


# ── nội dung sau di trú ─────────────────────────────────────────────────────

def test_so_su_kien_doi_ca_KHOA_len_TEN_su_kien(tmp_path):
    campaign = _cu(tmp_path)
    MG.di_tru(campaign, that=True)
    ds = [json.loads(x) for x in
          (campaign / "logs" / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [d["job"] for d in ds] == ["g1_approved", "job_failed"]
    assert ds[0]["at"] and ds[0]["post"] == "T-001" and ds[0]["by"] == "Đức"
    assert ds[0]["via"] == "phiên"
    assert ds[1]["step"] == "check-gates", "tên bước trong sổ cũng phải đổi"
    assert ds[1]["will_retry"] is True


def test_hang_cho_sang_dung_O_va_dung_KHOA(tmp_path):
    campaign = _cu(tmp_path)
    MG.di_tru(campaign, that=True)
    p = campaign / "logs" / "jobs" / "pending" / "j1.json"
    assert p.is_file(), "việc đang chờ không sang được hộp mới ⇒ nó nằm im mãi mãi"
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d["job_id"] == "j1" and d["job"] == "next" and d["post"] == "T-001"
    assert d["attempts"] == 0 and d["created_at"] and d["source"] == "g1_duyet"
    assert not (campaign / "logs" / "viec").exists()


def test_hang_cho_moi_DOC_DUOC_bang_work_queue(tmp_path):
    """Phép thử thật của di trú: code MỚI có đọc được dữ liệu ĐÃ ĐỔI không."""
    campaign = _cu(tmp_path)
    MG.di_tru(campaign, that=True)
    assert WQ.count(campaign)["pending"] == 1
    v = WQ.claim(campaign)
    assert v and v["post"] == "T-001"


def test_gates_doi_ca_khoa_LAN_gia_tri(tmp_path):
    campaign = _cu(tmp_path)
    MG.di_tru(campaign, that=True)
    g = json.loads((campaign / "T-001_mot" / "gates.json").read_text(encoding="utf-8"))
    assert g["verdict"] == "fail", "giá trị `do` không đổi thì mọi phép so sánh trượt"
    assert g["total"] == 2 and g["pass"] == 1 and g["fail_block"] == 1
    assert g["gates"][0]["id"] == "G01" and g["gates"][0]["status"] == "fail"
    assert g["gates"][0]["level"] == "block" and g["gates"][0]["rule"] == "2500-4000"


def test_file_le_va_telegram(tmp_path):
    campaign = _cu(tmp_path)
    MG.di_tru(campaign, that=True)
    assert (campaign / "T-001_mot" / ".write-count.json").is_file()
    ph = json.loads((campaign / "logs" / "feedback.json").read_text(encoding="utf-8"))
    assert ph["T-001"][0]["at"] and ph["T-001"][0]["text"] == "sửa"
    st = json.loads((campaign / "logs" / "tg-approve.json").read_text(encoding="utf-8"))
    assert st["offset"] == 42, "mất offset là poller xử lý lại toàn bộ update cũ"
    assert st["pending"] == {}


# ── an toàn ─────────────────────────────────────────────────────────────────

def test_chay_LAI_khong_doi_gi_them(tmp_path):
    """Di trú hay bị ngắt giữa chừng. Lần hai phải đi tiếp, không được nhân đôi."""
    campaign = _cu(tmp_path)
    MG.di_tru(campaign, that=True)
    truoc = (campaign / "logs" / "events.jsonl").read_text(encoding="utf-8")
    assert MG.di_tru(campaign, that=True) == []
    assert (campaign / "logs" / "events.jsonl").read_text(encoding="utf-8") == truoc


def test_GIU_ban_cu_lam_duong_lui(tmp_path):
    campaign = _cu(tmp_path)
    MG.di_tru(campaign, that=True)
    bak = list((campaign / "logs").glob("su-kien.jsonl.bak-*"))
    assert bak, "xoá nguồn mà không giữ bản lùi — di trú sai là mất trắng"
    assert "g1_duyet" in bak[0].read_text(encoding="utf-8")


def test_dong_HONG_duoc_chep_nguyen_khong_lam_do_ca_so(tmp_path):
    """Sổ sự kiện là bằng chứng. Một dòng rách không được làm mất 400 dòng còn lại."""
    campaign = _cu(tmp_path)
    p = campaign / "logs" / "su-kien.jsonl"
    p.write_text(p.read_text(encoding="utf-8") + "{ rách\n", encoding="utf-8", newline="\n")
    MG.di_tru(campaign, that=True)
    ra = (campaign / "logs" / "events.jsonl").read_text(encoding="utf-8")
    assert "{ rách" in ra and ra.count("\n") == 3


def test_bo_qua_thu_muc_khong_phai_chien_dich(tmp_path):
    (tmp_path / "linh-tinh").mkdir()
    assert MG.main([str(tmp_path / "linh-tinh")]) == 0
