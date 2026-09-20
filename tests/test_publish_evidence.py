# -*- coding: utf-8 -*-
"""Test cho `publish_evidence` — đọc BẰNG CHỨNG ĐÃ ĐĂNG của đường ống.

Vì sao có module này: luật dọn kho (Đức chốt 2026-09-20) không còn là "quá 14 ngày thì
xoá". Một file chỉ được dọn khi CÓ BẰNG CHỨNG nó đã ra khỏi máy — video đã lên YouTube,
audio đã có bản trong repo web. Không có bằng chứng ⇒ giữ, và nói rõ vì sao giữ.

Nguyên tắc của bộ test này: mỗi nguồn bằng chứng phải có CẢ HAI vế — một ca CÓ bằng chứng
và một ca THIẾU đúng khoá đó. Chỉ khẳng định "đọc được" thì một hàm luôn trả True vẫn xanh.

Khoá thật lấy từ đĩa 2026-09-20, không đoán:
  · tin    `*.published.json` → `video_id` · `short_id` · `fb_post_id` · `uploaded_at`
           (file có BOM — đọc bằng utf-8-sig, đọc bằng utf-8 là ValueError)
  · truyện `truyen-state.json` → `last_publish_ok` · `last_video` · `history[]`
           (mục history dạng `"2441-2446@20260813_0500"`)
  · truyện `playlist-youtube.json` → {tên playlist: [{title, video_id, published_at}]}
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import publish_evidence as PE  # noqa: E402


def _ghi(p: Path, d, bom=False) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2),
                 encoding="utf-8-sig" if bom else "utf-8", newline="\n")
    return p


# ── tin: *.published.json ────────────────────────────────────────────────────

def test_published_json_co_video_id_la_bang_chung(tmp_path):
    d = tmp_path / "out" / "2026-09-18"
    _ghi(d / "2026-09-18-top.json.published.json",
         {"uploaded_at": "2026-09-18T18:33:12", "fb_post_id": "1699850127757838",
          "video_id": "bYPZrV2LU-s", "short_id": "9WzVEXwNJ00"}, bom=True)
    bc = PE.BangChung.doc([])
    ra = bc.cho_video(d / "2026-09-18-top.mp4")
    assert ra and ra["key"] == "video_id" and ra["value"] == "bYPZrV2LU-s"


def test_published_json_BOM_van_doc_duoc(tmp_path):
    """Đường ống tin ghi `*.published.json` CÓ BOM. Đọc bằng utf-8 trần là `ValueError`, và
    một bằng chứng đọc-không-được bị coi là 'chưa đăng' ⇒ giữ mãi, đĩa đầy mà không ai hiểu."""
    d = tmp_path / "out" / "2026-09-18"
    f = _ghi(d / "x.json.published.json", {"video_id": "abc"}, bom=True)
    with pytest.raises(ValueError):
        json.loads(f.read_text(encoding="utf-8"))
    assert PE.BangChung.doc([]).cho_video(d / "x.mp4")


def test_short_mp4_doi_khoa_short_id_chu_khong_phai_video_id(tmp_path):
    """`-short.mp4` là video KHÁC với `-top.mp4`: nó lên YouTube bằng `short_id`. Lấy
    `video_id` cho nó là ghi nhận nhầm — bản short chưa đăng vẫn bị coi là đã đăng."""
    d = tmp_path / "out" / "2026-09-18"
    _ghi(d / "a.json.published.json", {"video_id": "co-that", "short_id": ""}, bom=True)
    assert PE.BangChung.doc([]).cho_video(d / "2026-09-18-top.mp4")
    assert PE.BangChung.doc([]).cho_video(d / "2026-09-18-top-short.mp4") is None


def test_published_json_thieu_video_id_thi_KHONG_phai_bang_chung(tmp_path):
    d = tmp_path / "out" / "2026-09-18"
    _ghi(d / "a.json.published.json", {"uploaded_at": "2026-09-18T18:33:12",
                                       "fb_post_id": "17", "video_id": ""}, bom=True)
    assert PE.BangChung.doc([]).cho_video(d / "2026-09-18-top.mp4") is None


def test_published_json_o_thu_muc_KHAC_khong_tinh(tmp_path):
    """Bằng chứng gắn với THƯ MỤC của nó. Một ngày đã đăng không chứng minh gì cho ngày khác."""
    _ghi(tmp_path / "out" / "2026-09-18" / "a.json.published.json", {"video_id": "x"}, bom=True)
    assert PE.BangChung.doc([]).cho_video(tmp_path / "out" / "2026-09-19" / "b.mp4") is None


# ── truyện: truyen-state.json ────────────────────────────────────────────────

def test_truyen_last_video_publish_ok_la_bang_chung(tmp_path):
    st = _ghi(tmp_path / "truyen-state.json",
              {"last_publish_ok": True, "last_video": "D:/x/out/PNTT 2441-2446.mp4",
               "history": ["2441-2446@20260813_0500"]})
    bc = PE.BangChung.doc([st])
    ra = bc.cho_video(tmp_path / "out" / "PNTT 2441-2446.mp4")
    assert ra and ra["source"].endswith("truyen-state.json")


def test_truyen_publish_KHONG_ok_thi_khong_phai_bang_chung(tmp_path):
    """`last_publish_ok=False` = lượt trước đăng hỏng. Chính `sweep_old` của truyện cũng
    giữ tất cả trong ca này — prune_media không được rộng tay hơn nó."""
    st = _ghi(tmp_path / "truyen-state.json",
              {"last_publish_ok": False, "last_video": "D:/x/out/PNTT 9-10.mp4",
               "history": []})
    assert PE.BangChung.doc([st]).cho_video(tmp_path / "out" / "PNTT 9-10.mp4") is None


def test_truyen_history_nhan_dai_chuong_cu(tmp_path):
    """`last_video` chỉ nói về lượt CUỐI. Tập cũ hơn nằm ở `history` dạng `2431-2438@…`."""
    st = _ghi(tmp_path / "truyen-state.json",
              {"last_publish_ok": True, "last_video": "D:/x/PNTT 2441-2446.mp4",
               "history": ["2431-2438@20260808_0300", "2439-2440@20260813_0100"]})
    bc = PE.BangChung.doc([st])
    assert bc.cho_video(tmp_path / "PNTT 2431-2438.mp4")
    assert bc.cho_video(tmp_path / "PNTT 2500-2510.mp4") is None


# ── truyện: playlist-youtube.json ────────────────────────────────────────────

def test_playlist_youtube_dai_chuong_trong_tieu_de(tmp_path):
    pl = _ghi(tmp_path / "playlist-youtube.json",
              {"Ph\u00e0m Nh\u00e2n Tu Ti\u00ean (P1)": [
                  {"title": "Ph\u00e0m Nh\u00e2n Tu Ti\u00ean | Vong Ng\u1eef (Ch\u01b0\u01a1ng 1141-1150)",
                   "video_id": "ljXwoI9YyCw", "published_at": "2026-06-18T03:25:51Z"}]})
    bc = PE.BangChung.doc([pl])
    ra = bc.cho_video(tmp_path / "PNTT 1141-1150.mp4")
    assert ra and ra["value"] == "ljXwoI9YyCw"
    assert bc.cho_video(tmp_path / "PNTT 1151-1160.mp4") is None


def test_playlist_muc_thieu_video_id_khong_tinh(tmp_path):
    pl = _ghi(tmp_path / "playlist-youtube.json",
              {"P1": [{"title": "Ch\u01b0\u01a1ng 10-20", "video_id": ""}]})
    assert PE.BangChung.doc([pl]).cho_video(tmp_path / "PNTT 10-20.mp4") is None


# ── hợp đồng: file bằng chứng hỏng phải nói ra, không nuốt ───────────────────

def test_evidence_khong_ton_tai_la_ma_3(tmp_path):
    with pytest.raises(PE.SC.StationMissing):
        PE.BangChung.doc([tmp_path / "khong-co"])


def test_evidence_khong_phai_json_la_ma_2(tmp_path):
    f = tmp_path / "hong.json"
    f.write_text("{khong phai json", encoding="utf-8")
    with pytest.raises(PE.SC.ContractError):
        PE.BangChung.doc([f])


def test_evidence_json_hop_le_nhung_KHONG_nhan_ra_la_ma_2(tmp_path):
    """Khai một file không phải sổ đăng nào cả = cấu hình sai. Im lặng nhận nó là tệ nhất:
    lượt dọn chạy với 0 bằng chứng mà người gõ tưởng mình đã khai."""
    f = _ghi(tmp_path / "la.json", {"chang": "lien quan"})
    with pytest.raises(PE.SC.ContractError):
        PE.BangChung.doc([f])


def test_nguon_ghi_lai_duoc_de_lan_nguoc(tmp_path):
    st = _ghi(tmp_path / "truyen-state.json",
              {"last_publish_ok": True, "last_video": "x/PNTT 1-2.mp4", "history": []})
    bc = PE.BangChung.doc([st])
    assert [Path(x["path"]).name for x in bc.nguon()] == ["truyen-state.json"]
    assert bc.nguon()[0]["kind"] == "truyen-state"
