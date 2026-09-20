# -*- coding: utf-8 -*-
"""Test cho blog_gates.py — khẳng định cổng ĐỎ ĐÚNG LÝ DO, không chỉ đỏ.

Một bộ test chỉ chạy trên dữ liệu đẹp sẽ xanh mãi kể cả khi cổng đã hỏng hoàn toàn.
Nên ở đây có ba loại khẳng định, và thiếu loại nào cũng để lọt một kiểu hỏng:

  1. Trên `fixtures/bai_do/` — đỏ đúng TẬP mã cổng, và đúng SỐ ĐO. Nếu chỉ khẳng định
     "có đỏ" thì một cổng bắt nhầm lý do vẫn qua được.
  2. Trên bài hợp lệ dựng tại chỗ — KHÔNG cổng nào đỏ. Bắt ca cổng kêu oan, thứ khiến
     người ta tắt cổng đi và từ đó cổng thành đồ trang trí.
  3. Thiếu đầu vào phải ra trạng thái "thiếu", KHÔNG phải "xanh". Cổng báo xanh cho
     thứ nó chưa hề đo là cổng nói dối.
"""
import json
import re
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
import blog_gates as G  # noqa: E402
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import post_paths as PP  # noqa: E402
import fb_format as FF  # noqa: E402

BAI_DO = ROOT / "fixtures" / "bai_do"
HOME = "vidu.vn"
# G22 đo theo bộ tên tổ chức do KÊNH khai (`brand.org_names`). Trước 20/09 bộ tên này là
# hằng số trong mã và là tên thật của chủ repo — xem scripts/lib/brand.py.
TO_CHUC = ["Ví Dụ Corp", "Vidu Academy"]


def _theo_ma(result):
    return {r["id"]: r for r in result["gates"]}


# ------------------------------------------------------------------ 1. fixture đỏ

@pytest.fixture(scope="module")
def do():
    return _theo_ma(G.run_cmd(BAI_DO, HOME, stage="release", org_names=TO_CHUC))


def test_fixture_do_ton_tai():
    assert PP.p(BAI_DO, "blog").exists(), "fixture đỏ bị xoá -> mọi khẳng định dưới đây vô nghĩa"


def test_dung_tap_cong_bi_chan(do):
    chan = {job_id for job_id, r in do.items() if r["status"] == "fail" and r["level"] == G.CHAN}
    assert chan == {"G01", "G02", "G05", "G06", "G08", "G09", "G11",
                    "G12", "G13", "G14", "G17", "G18", "G19", "G20", "G24"}


def test_dung_tap_cong_canh_bao(do):
    cb = {job_id for job_id, r in do.items() if r["status"] == "fail" and r["level"] == G.CANH_BAO}
    assert cb == {"G04", "G07", "G10", "G15"}, "cảnh báo không được leo thành chặn"


def test_cong_xanh_khong_bi_do_lay(do):
    """Bài sai nhiều thứ nhưng CÓ bảng và KHÔNG lộ tên tool -> ba cổng này phải xanh."""
    assert do["G03"]["status"] == "pass"
    assert do["G21"]["status"] == "pass"
    assert do["G22"]["status"] == "pass"


def test_so_do_dung_chu_khong_chi_do(do):
    """Đây là phần phân biệt 'đỏ' với 'đỏ đúng lý do'."""
    assert do["G02"]["measured"] == 3            # 3 H2, ngưỡng 6-12
    # Đổi 12/09/2026: G05 đo MỤC `## Nguồn tham khảo`, và fixture đỏ không có mục đó.
    assert do["G05"]["measured"] == "không có mục"
    assert do["G06"]["measured"] == "0 khối / 0 từ"   # không có khối chính kiến nào
    assert do["G08"]["measured"] == 2            # 2 dấu [KIỂM CHỨNG] còn mở
    assert do["G09"]["measured"] == 2            # 2 URL trong thân post
    assert do["G11"]["measured"] == 0            # 0 ký tự bold
    assert do["G13"]["measured"] == 2            # 2 hashtag, ngưỡng 6-13
    # đỏ THUẦN vì đếm sai (5≠8): hình dạng đúng, ảnh src đúng — để phép đếm giữ nguyên ý nghĩa
    assert do["G17"]["measured"] == "5 scene, 0 thiếu nội dung, 0 mất ảnh src"
    assert do["G18"]["measured"] == "0 loại"      # không thẻ og: nào
    assert do["G20"]["measured"] == "95 / 1"     # tóm tắt 95 từ, 1 key-term


def test_cong_noi_ra_bang_chung_cu_the(do):
    """Cổng phải chỉ được chỗ sai, không chỉ nói 'sai'."""
    assert "https://" in do["G09"]["note"], "G09 phải liệt kê chính các URL nó bắt được"


def test_khong_suy_dien_hau_qua(do):
    """Luật phát ngôn: cổng chỉ nói cái nó ĐO ĐƯỢC."""
    campaign = ["reach", "bóp", "thuật toán", "sẽ bị", "chất lượng kém", "bài dở"]
    for job_id, r in do.items():
        van_ban = f"{r['name']} {r['note']}".lower()
        for tu in campaign:
            assert tu not in van_ban, f"{job_id} suy diễn hậu quả thay vì báo số đo: {r}"


# ------------------------------------------------------------------ 2. bài hợp lệ

@pytest.fixture
def bai_xanh(tmp_path):
    d = tmp_path / "post"
    d.mkdir()
    PP.make_dirs(d)
    than = "\n\n".join(
        [f"## Mục {i}\n\nMột đoạn nội dung. " * 3 for i in range(1, 9)]
    )
    (PP.p(d, "blog")).write_text(
        "# Tiêu đề\n\n" + than + "\n\n"
        + "| a | b |\n|---|---|\n| 1 | 2 |\n\n"
        + "".join(f"> 💡 Callout số {i}\n\n" for i in range(1, 5))
        # >=40 từ: một khối chính kiến rỗng hoặc cụt không phải là chính kiến, mà cổng
        # bản đầu vẫn cho xanh vì nó chỉ khớp dòng tiêu đề của khối.
        + "> **Góc nhìn:** " + "chính kiến của tác giả nói rõ ra. " * 12 + "\n\n"
        + "Theo Reuters, số liệu như vậy. Theo mình thì khác.\n\n"
        # Nguồn nay phải kê ở MỤC RIÊNG cuối bài, không rải trong thân — đổi 12/09/2026.
        + "\n## Nguồn tham khảo\n\n"
        + "\n".join(f"- Nguồn {i}: https://vidu{i}.com/bai-viet (truy cập 04/09/2026)"
                    for i in range(1, 5))
        # Đệm cho bài rơi vào dải 2500-4000 từ. Con số 500 chọn bằng cách ĐO rồi chỉnh:
        # 900 cho ra 4748 từ và làm G01 đỏ — tức fixture sai, không phải cổng sai.
        + "\n\n" + "thêm chữ cho đủ dài. " * 500,
        encoding="utf-8")
    (PP.p(d, "fb_post")).write_text(
        FF.bold("Tiêu đề đậm") + "\n\n" + "Nội dung bài. " * 400 + "\n\n"
        + "#AI #Data #CongNghe #Prompt #Agent #HocMai\n", encoding="utf-8")
    (PP.p(d, "fb_comment")).write_text(
        "Bản đầy đủ 👇\nhttps://vidu.vn/atlas/content/ai/x.html\n", encoding="utf-8")
    (PP.p(d, "podcast")).write_text("từ " * 850, encoding="utf-8")
    (PP.p(d, "scenes")).write_text(
        json.dumps([{"kind": "concept", "title": f"Scene {i}"} for i in range(8)]),
        encoding="utf-8")
    (PP.p(d, "atlas_html")).write_text(
        "".join(f'<meta property="og:{k}" content="x">'
                for k in ("type", "title", "description", "url", "image", "site_name")),
        encoding="utf-8")
    (PP.p(d, "publish")).write_text(
        json.dumps({"summary": "Tóm tắt ngắn gọn.",
                    "key_terms_explained": ["thuật ngữ một", "thuật ngữ hai",
                                            "thuật ngữ ba"]}, ensure_ascii=False),
        encoding="utf-8")
    # PNG tối thiểu nhưng CÓ THẬT kích thước trong IHDR — cổng đọc 8 byte tại offset 16,
    # nên một file chỉ có chữ ký (như bản fixture cũ) không còn qua được.
    _sig = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
    (PP.p(d, "fb_image")).write_bytes(
        _sig + bytes(4) + b"IHDR" + (1080).to_bytes(4, "big") + (1350).to_bytes(4, "big"))
    (PP.p(d, "fb_prompt")).write_text("prompt đã dùng để sinh ảnh. " * 25,
                                          encoding="utf-8")
    # research.md phải CÓ, và host phải khớp mục Nguồn tham khảo — G05 đối chiếu hai bên.
    (PP.p(d, "research")).write_text(
        "---\nkey_sources: bảng nguồn\n---\n\n"
        + "\n".join(f"| {i} | https://vidu{i}.com/goc | tác giả {i} |"
                    for i in range(1, 5)),
        encoding="utf-8")
    return d


def test_bai_hop_le_khong_bi_keu_oan(bai_xanh):
    result = G.run_cmd(bai_xanh, HOME, stage="release")
    do_ra = [(r["id"], r["name"], r["measured"], r["rule"])
             for r in result["gates"] if r["status"] == "fail"]
    assert do_ra == [], f"cổng kêu oan trên bài hợp lệ: {do_ra}"


# ------------------------------------------------------------------ 3. thiếu ≠ xanh

def test_thieu_dau_vao_khong_duoc_bao_xanh(tmp_path):
    result = G.run_cmd(tmp_path, HOME, stage="release")
    theo = _theo_ma(result)
    assert theo["G01"]["status"] == "missing"
    assert theo["G18"]["status"] == "missing"
    assert result["pass"] == 0, "thư mục rỗng mà có cổng xanh = cổng đang nói dối"
    assert result["missing"] == 23


def test_g23_bat_placeholder_con_sot(bai_xanh):
    """Placeholder sót lại = bài chưa điền link, nhưng nó im lặng hoàn toàn.

    Vòng 1 chỉ nhìn placeholder GIÁN TIẾP qua G14 (comment phải có URL). Nên
    youtube_desc.txt mang nguyên {{BLOG_URL}} vẫn qua sạch — đo được trên bài thật 04/09.
    Với quy trình đăng TAY thì đây là lỗ chết người: người dán nguyên văn lên YouTube.
    """
    assert _theo_ma(G.run_cmd(bai_xanh, HOME, stage="release"))["G23"]["status"] == "pass"

    (PP.p(bai_xanh, "yt_desc")).write_text("Bản đầy đủ: {{BLOG_URL}}", encoding="utf-8")
    r = _theo_ma(G.run_cmd(bai_xanh, HOME, stage="release"))["G23"]
    assert r["status"] == "fail" and r["level"] == G.CHAN
    assert "description.txt" in r["note"] and "{{BLOG_URL}}" in r["note"], \
        "cổng phải chỉ rõ placeholder nào ở file nào, không chỉ nói 'có placeholder'"


def test_thu_muc_rong_van_bao_thieu_G23(tmp_path):
    assert _theo_ma(G.run_cmd(tmp_path, HOME, stage="release"))["G23"]["status"] == "missing"


# ------------------------------------------------------------------ 4. miễn trừ G21

def _bai_co_ten_tool(tmp_path, name="codex"):
    d = tmp_path / "post"
    d.mkdir()
    PP.make_dirs(d)
    (PP.p(d, "blog")).write_text(f"# Bài\n\nBài này nói về {name} của một hãng khác.\n",
                               encoding="utf-8")
    return d


def test_g21_chan_khi_khong_mien_tru(tmp_path):
    theo = _theo_ma(G.run_cmd(_bai_co_ten_tool(tmp_path), HOME))
    assert theo["G21"]["status"] == "fail"
    assert theo["G21"]["level"] == G.CHAN


def test_g21_mien_tru_thi_khong_chan_nhung_VAN_BAO_CAO(tmp_path):
    """Điểm mấu chốt: miễn trừ KHÁC với im lặng bỏ qua.

    Nếu miễn trừ làm cái tên biến mất khỏi báo cáo thì sáu tháng sau không ai biết nó ở
    đó, và nó được sao chép sang bài sau mà không ai xét lại.
    """
    theo = _theo_ma(G.run_cmd(_bai_co_ten_tool(tmp_path), HOME,
                           allow={"codex": "là chủ đề bài báo, không phải tool nội bộ"}))
    assert theo["G21"]["status"] == "pass"
    assert "codex" in theo["G21"]["note"], "tên được miễn trừ vẫn phải hiện trong báo cáo"
    assert "MIỄN TRỪ" in theo["G21"]["note"]
    assert "chủ đề bài báo" in theo["G21"]["note"], "lý do phải đi kèm, không chỉ là cờ bật"


def test_mien_tru_duoc_ghi_vao_gates_json(tmp_path):
    result = G.run_cmd(_bai_co_ten_tool(tmp_path), HOME, allow={"codex": "lý do X"})
    assert result["waived"] == {"codex": "lý do X"}, "gates.json phải lưu lại ai miễn trừ cái gì"


def test_mien_tru_mot_ten_khong_mo_duong_cho_ten_khac(tmp_path):
    """Miễn trừ phải hẹp đúng cái tên được nêu."""
    d = tmp_path / "post"
    d.mkdir()
    PP.make_dirs(d)
    (PP.p(d, "blog")).write_text("Bài nhắc codex và nhắc cả omnivoice.", encoding="utf-8")
    theo = _theo_ma(G.run_cmd(d, HOME, allow={"codex": "chủ đề bài"}, stage="release"))
    assert theo["G21"]["status"] == "fail", "omnivoice không được miễn trừ nên vẫn phải chặn"
    assert "omnivoice" in theo["G21"]["note"]


def test_g17_bat_dang_dict_du_dem_dung_8(tmp_path):
    """Cổng phải đo đúng HỢP ĐỒNG CỦA CÔNG CỤ, không chỉ đếm cho có.

    Ca thật 04/09: scenes.json viết dạng {"scenes": [...]} với đủ 8 phần tử. Cổng bản cũ
    chấp nhận cả hai dạng nên báo XANH, trong khi make_podcast_video.py `json.load` rồi
    lặp thẳng, gặp chuỗi và chết bằng "'str' object has no attribute 'get'".
    Cổng dễ dãi hơn công cụ thật thì tệ hơn không có cổng — nó cấp một lời bảo đảm sai.
    """
    d = tmp_path / "post"
    d.mkdir()
    PP.make_dirs(d)
    (PP.p(d, "scenes")).write_text(
        json.dumps({"scenes": [{"kind": "concept"} for _ in range(8)]}), encoding="utf-8")
    r = _theo_ma(G.run_cmd(d, HOME, stage="release"))["G17"]
    assert r["status"] == "fail", "đủ 8 phần tử nhưng sai dạng thì renderer vẫn vỡ"
    assert "mảng" in r["rule"]


def test_cli_tu_choi_mien_tru_khong_ly_do(tmp_path, capsys):
    d = _bai_co_ten_tool(tmp_path)
    assert G.main([str(d), "--home-domain", HOME, "--allow", "codex", "--json-only"]) == 2
    assert "thiếu lý do" in capsys.readouterr().err


def test_cli_ghi_gates_json_va_exit_khac_0(tmp_path):
    d = tmp_path / "bai_do"
    shutil.copytree(BAI_DO, d)
    assert G.main([str(d), "--home-domain", HOME, "--json-only"]) == 1
    write = json.loads((d / "gates.json").read_text(encoding="utf-8"))
    assert write["total"] == 24 and write["verdict"] == "fail"


# ── Phân bước: cổng của bước sau KHÔNG được chặn bước soạn ──────────────────
# Đo thật 12/09/2026: chấm trọn 23 cổng ngay sau khi soạn thì bài không bao giờ xanh
# được, và 3 bài kẹt ở `fix-gates` suốt một ngày vì bị chặn bởi đúng những cổng mà bước
# soạn không có cách nào làm cho xanh.

def _theo_ma_stage(bai, stage):
    return {r["id"]: r for r in G.run_cmd(bai, HOME, stage=stage)["gates"]}


def test_cong_cua_buoc_SAU_bao_missing_chu_khong_bao_do(tmp_path):
    theo = _theo_ma_stage(BAI_DO, "write")
    for ma in ("G14", "G19", "G20"):
        assert theo[ma]["status"] == "missing", f"{ma} chặn ở bước soạn: {theo[ma]}"
        assert "chưa tới lượt" in theo[ma]["note"], theo[ma]["note"]


def test_cung_bai_do_o_buoc_SAU_thi_cong_do_QUAY_LAI_chan():
    """Hạ xuống `missing` là HOÃN, không phải tha. Tới bước của nó thì nó lại chặn."""
    som, muon = _theo_ma_stage(BAI_DO, "write"), _theo_ma_stage(BAI_DO, "release")
    assert som["G19"]["status"] == "missing"
    assert muon["G19"]["status"] == "fail" and muon["G19"]["level"] == "block"


def test_phan_buoc_KHONG_dung_toi_cong_cua_chinh_buoc_soan():
    """G01/G05/G06 là lỗi THẬT của bước soạn — phân bước không được làm chúng biến mất."""
    theo = _theo_ma_stage(BAI_DO, "write")
    for ma in ("G01", "G05", "G06"):
        assert theo[ma]["status"] in ("pass", "fail"), f"{ma} bị hoãn nhầm: {theo[ma]}"


def test_hai_placeholder_cua_buoc_DANG_khong_lam_G23_do(tmp_path, bai_xanh):
    """G23 và G14 từng chặn nhau: điền link thì chưa có link, để chỗ giữ thì G23 đỏ."""
    (bai_xanh / "facebook").mkdir(exist_ok=True)
    fb = bai_xanh / "facebook" / "comment.txt"
    fb.write_text("Bài đầy đủ: {{BLOG_URL}}\nVideo: {{YOUTUBE_URL}}\n",
                  encoding="utf-8", newline="\n")
    assert _theo_ma_stage(bai_xanh, "write")["G23"]["status"] == "pass"

    fb.write_text("Bài: {{BLOG_URL}}\nTác giả: {{TEN_TAC_GIA}}\n",
                  encoding="utf-8", newline="\n")
    r = _theo_ma_stage(bai_xanh, "write")["G23"]
    assert r["status"] == "fail", "placeholder KHÁC vẫn phải bị bắt"
    assert "TEN_TAC_GIA" in r["note"] and "BLOG_URL" not in r["note"]


def test_gates_json_ghi_lai_da_cham_o_BUOC_nao():
    """Đọc `gates.json` mà không biết nó chấm ở mốc nào thì con số vô nghĩa."""
    assert G.run_cmd(BAI_DO, HOME, stage="write")["stage"] == "write"


def test_mien_placeholder_la_HOAN_theo_buoc_khong_phai_THA(bai_xanh):
    """Từ bước `publish` trở đi, `{{BLOG_URL}}` phải biến mất — bài học 04/09/2026.

    Hôm đó `youtube/description.txt` mang nguyên `{{BLOG_URL}}` lọt qua cổng, và với quy
    trình đăng TAY thì người dán nguyên văn chuỗi đó lên YouTube.
    """
    (PP.p(bai_xanh, "yt_desc")).write_text("Bản đầy đủ: {{BLOG_URL}}", encoding="utf-8")
    assert _theo_ma_stage(bai_xanh, "write")["G23"]["status"] == "pass"
    for stage in ("publish", "release"):
        r = _theo_ma_stage(bai_xanh, stage)["G23"]
        assert r["status"] == "fail" and r["level"] == G.CHAN, f"{stage}: {r}"


# ── G05 và G06 đo CHẤT, không đo vỏ (đổi 12/09/2026) ────────────────────────

def test_G05_dem_nguon_o_MUC_RIENG_khong_dem_link_trong_than(bai_xanh):
    """Đo thật: NEN-004 có 3 link trong thân nhưng đều là link NỘI BỘ, và 5 nguồn thật
    nằm ở research.md. Cổng bản cũ đếm link thân bài nên báo 0 và chặn một bài có kỷ luật
    nguồn tốt. Nay đếm ở mục người đọc kiểm chứng được."""
    theo = _theo_ma_stage(bai_xanh, "write")
    assert theo["G05"]["status"] == "pass", theo["G05"]

    blog = PP.p(bai_xanh, "blog")
    t = blog.read_text(encoding="utf-8")
    blog.write_text(t.replace("## Nguồn tham khảo", "## Một mục khác"),
                    encoding="utf-8", newline="\n")
    r = _theo_ma_stage(bai_xanh, "write")["G05"]
    assert r["status"] == "fail" and "không có mục" in str(r["measured"]), r


def test_G05_van_bat_nguon_LAC_khong_co_trong_research(bai_xanh):
    """Kê nguồn ở mục riêng không có nghĩa là muốn kê gì cũng được."""
    blog = PP.p(bai_xanh, "blog")
    t = blog.read_text(encoding="utf-8")
    blog.write_text(t + "\n- Nguồn bịa: https://khong-co-trong-research.com/x\n",
                    encoding="utf-8", newline="\n")
    r = _theo_ma_stage(bai_xanh, "write")["G05"]
    assert r["status"] == "fail" and "lạc" in str(r["measured"]), r


def test_G06_nhan_CA_H2_lan_khoi_trich_dan(tmp_path, bai_xanh):
    """Đo thật: NEN-004 có `## Góc nhìn của mình` dài 399 từ mà cổng cũ báo 0 khối."""
    blog = PP.p(bai_xanh, "blog")
    t = blog.read_text(encoding="utf-8")
    # Bỏ khối trích dẫn, thay bằng một mục H2 cùng nghĩa.
    t = re.sub(r"(?m)^>\s*\*\*Góc nhìn:.*$", "", t)
    t += "\n## Góc nhìn của mình\n\n" + "chính kiến nói rõ ra. " * 20 + "\n"
    blog.write_text(t, encoding="utf-8", newline="\n")
    r = _theo_ma_stage(bai_xanh, "write")["G06"]
    assert r["status"] == "pass", r


def test_G06_H2_RONG_van_do(bai_xanh):
    """Nhận thêm hình dạng không có nghĩa là hạ chuẩn: mục rỗng vẫn là không có chính kiến."""
    blog = PP.p(bai_xanh, "blog")
    t = re.sub(r"(?m)^>\s*\*\*Góc nhìn:.*$", "", blog.read_text(encoding="utf-8"))
    blog.write_text(t + "\n## Góc nhìn của mình\n\nNgắn thôi.\n",
                    encoding="utf-8", newline="\n")
    r = _theo_ma_stage(bai_xanh, "write")["G06"]
    assert r["status"] == "fail", r


def test_G05_KHONG_dem_link_nam_trong_THAN_bai(bai_xanh):
    """Link rải trong thân không còn bị tính — kể cả link không có trong research.md.

    Đây là chỗ phân biệt "đếm ở mục Nguồn" với "đếm cả bài". Nếu cổng vẫn quét cả bài thì
    một link minh hoạ giữa thân sẽ bị tính là nguồn lạc và chặn oan.
    """
    blog = PP.p(bai_xanh, "blog")
    t = blog.read_text(encoding="utf-8")
    dau = t.index("## Nguồn tham khảo")
    t = t[:dau] + "\nMinh hoạ: https://mot-trang-minh-hoa.com/anh\n\n" + t[dau:]
    blog.write_text(t, encoding="utf-8", newline="\n")

    r = _theo_ma_stage(bai_xanh, "write")["G05"]
    assert r["status"] == "pass", f"link trong thân bị tính là nguồn: {r}"
    assert r["measured"] == "4 nguồn, 0 lạc", r["measured"]


# ------------------------------------------------------------------ G24 prompt ảnh

def test_G24_thieu_prompt_thi_DO_ngay_o_buoc_viet(bai_xanh):
    """G19 đo ảnh nên ở bước viết chỉ báo 'chưa tới lượt'. Thiếu prompt phải đỏ NGAY,
    nếu không vòng viết lại không bao giờ được kích và bước tạo ảnh chờ mãi."""
    PP.p(bai_xanh, "fb_prompt").unlink()
    r = _theo_ma_stage(bai_xanh, "write")["G24"]
    assert r["status"] == "fail" and r["level"] == G.CHAN, r


def test_G24_prompt_ngan_hoac_con_cho_trong_thi_do(bai_xanh):
    PP.p(bai_xanh, "fb_prompt").write_text("Vẽ ảnh. " * 10, encoding="utf-8")
    assert _theo_ma_stage(bai_xanh, "write")["G24"]["status"] == "fail"
    PP.p(bai_xanh, "fb_prompt").write_text("Vẽ ảnh đúng dấu. " * 60 + "Tiêu đề: {{TIÊU ĐỀ}}",
                                           encoding="utf-8")
    r = _theo_ma_stage(bai_xanh, "write")["G24"]
    assert r["status"] == "fail" and "{{TIÊU ĐỀ}}" in r["note"], r


def test_G24_prompt_du_thi_xanh(bai_xanh):
    assert _theo_ma_stage(bai_xanh, "write")["G24"]["status"] == "pass"


def test_G24_bai_khong_dang_facebook_thi_khong_doi_prompt(bai_xanh):
    PP.p(bai_xanh, "fb_post").unlink()
    assert _theo_ma_stage(bai_xanh, "write")["G24"]["status"] == "missing"


# ------------------------------------------------------- G22 theo cấu hình kênh

def test_G22_do_theo_bo_ten_cua_KENH():
    """Tên tổ chức là CẤU HÌNH, không phải hằng số trong mã.

    Trước 20/09 bộ tên nằm cứng trong `blog_gates.py` và là tên thật của chủ repo: vừa
    là rò danh tính trong một repo public, vừa làm cổng này vô dụng ở mọi máy khác —
    người clone về không bao giờ bị cảnh báo vì tên tổ chức CỦA HỌ lọt ra bản công khai.
    """
    import tempfile
    from pathlib import Path as P
    d = P(tempfile.mkdtemp())
    (d / "facebook").mkdir()
    (d / "facebook" / "post.txt").write_text("Bài do Acme Corp thực hiện.\n", encoding="utf-8")
    r = _theo_ma(G.run_cmd(d, HOME, stage="release", org_names=["Acme Corp"]))["G22"]
    assert r["status"] == "fail" and r["measured"] == 1
    r2 = _theo_ma(G.run_cmd(d, HOME, stage="release", org_names=["Beta Ltd"]))["G22"]
    assert r2["status"] == "pass"
    import shutil
    shutil.rmtree(d, ignore_errors=True)


def test_G22_khong_khai_ten_thi_bao_THIEU_chu_khong_bao_xanh():
    """Không có bộ tên thì cổng không đo được gì. Báo xanh ở đây là xanh giả —
    người đọc báo cáo sẽ tin rằng bản công khai đã được soi, trong khi chưa hề."""
    r = _theo_ma(G.run_cmd(BAI_DO, HOME, stage="release", org_names=[]))["G22"]
    assert r["status"] == "missing"
    assert "org_names" in r["note"]


def test_link_tran_co_gach_noi_chi_dem_MOT_lan():
    """`vi-du.vn/x` từng bị đếm hai lần: một lần trọn, một lần từ sau dấu gạch nối."""
    assert G._URL_TRAN.findall("xem vi-du.vn/atlas/x roi thoi") == ["vi-du.vn/atlas/x"]


def test_tom_tat_KHONG_giau_cong_chua_do_duoc(capsys):
    """REVIEW-P2 Ghi nhận 17. `missing` là "chưa đo được", không phải "xanh". Tóm tắt cũ
    bỏ qua chúng nên người đọc thấy "✔ KHÔNG cổng nào chặn" trong khi G22 chưa đo được
    (`brand.org_names` để trống) — đúng thứ mà chính G22 sinh ra để tránh."""
    ket = {"stage": "write", "gates": [
        {"id": "G01", "name": "Do duoc", "status": "pass", "level": G.CHAN,
         "measured": "1", "rule": "x", "note": ""},
        {"id": "G22", "name": "Ten to chuc", "status": "missing", "level": G.CHAN,
         "measured": "-", "rule": "x", "note": "brand.org_names trong"},
        {"id": "G20", "name": "Trang web", "status": "missing", "level": G.CHAN,
         "measured": "-", "rule": "x", "note": "chưa tới lượt"},
    ]}
    G._in_vi_sao_bi_chan(ket)
    ra = capsys.readouterr().out
    assert "G22" in ra and "CH\u01afA \u0110O \u0110\u01af\u1ee2C" in ra
    assert "G20" not in ra.split("CH\u01afA \u0110O")[-1], "cong HOAN khong duoc dem hai lan"
