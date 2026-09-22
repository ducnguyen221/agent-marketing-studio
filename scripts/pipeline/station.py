#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`station export|import` — đóng gói một trạm nội dung và mở nó ra ở máy khác.

Đây là cái van của quy tắc "một máy chạy tại một thời điểm" (runbook đổi máy): tắt lịch
bên này -> `export` -> `import` bên kia -> bật lịch bên kia. Trạng thái chống-đăng-trùng
nằm trong đống JSON nhỏ mà gói này mang theo; bật lịch ở máy chưa import là đăng trùng.

Khác `studio.py backup` có chủ đích — hai lệnh KHÔNG gộp:

    backup   ảnh chụp cho chính mình. Zip cả trạm, không phán xét cái gì đáng mang.
    export   gói bàn giao. Danh sách khai rõ (`scripts/lib/station_manifest.py` theo kế
             hoạch §4) + manifest + sha256, và bên nhận đếm lại rồi BÁO THIẾU.

Ba luật của bên nhận, mỗi luật vì một cách hỏng đã thấy:

    KHÔNG ĐÈ        va chạm một file là DỪNG, chưa ghi byte nào. Trạng thái ở đích có thể
                    mới hơn trong gói; đè im lặng là mất nó mà không ai biết.
    KIỂM sha256     gói đi qua USB/mạng. Giải nén một gói hỏng = máy mới chạy bằng dữ liệu
                    sai, tệ hơn hẳn việc dừng lại và chép gói lần nữa.
    KHÔNG tin đường entry `../` trong zip ghi đè file ngoài thư mục đích (zip-slip).

Mã thoát theo `scripts/lib/studio_contract.py`: 0 · 1 · 2 · 3.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import station_manifest as SM  # noqa: E402
import studio_contract as SC  # noqa: E402
import studio_paths as SP  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

PROG = "station"
RUNBOOK = "docs/RUNBOOK-DOI-MAY.md"

# Windows: MAX_PATH là 260 KỂ CẢ ký tự kết thúc chuỗi ⇒ đường dài nhất dùng được là 259.
# Tiền tố `\\?\` (xem `_dai`) cho Python ghi vượt qua được, nhưng PowerShell 5.1 thì
# KHÔNG — kể cả khi máy đã bật LongPathsEnabled. Trạm này chạy bằng `.ps1` dưới PS 5.1,
# nên một đường vượt 259 là một file mà pipeline sẽ không bao giờ mở được. Thà dừng
# trước khi ghi và bảo người dùng chọn chỗ ngắn hơn, còn hơn giao một trạm hỏng ngầm.
GIOI_HAN_DUONG = 259

# Đuôi file được đổi đường máy cũ. Đúng danh sách của kế hoạch §2.7 — không nới thêm:
# mỗi đuôi thêm vào là một loại file nữa bị sửa nội dung sau lưng người dùng.
DUOI_DOI_DUONG = (".yml", ".yaml", ".md", ".py", ".ps1", ".json")


# ══ export ═══════════════════════════════════════════════════════════════════════════

def export_station(station, out, *, with_git=False, logs_state=False, dry_run=False) -> dict:
    st = Path(station).expanduser().resolve()
    if not st.is_dir():
        raise SC.StationMissing(
            f"không có trạm ở {st} — trỏ --station vào gốc trạm (thư mục có CHANNELS.md).")
    out = Path(out).expanduser().resolve()
    if out == st or st in out.parents:
        raise SC.ContractError(
            f"--out nằm TRONG trạm ({out}). Lần export sau sẽ gói chính file zip này và "
            "kích thước nhân đôi mỗi lượt — chọn chỗ ngoài trạm.")

    files = SM.chon(st, logs_state=logs_state, with_git=with_git)
    rels = [rel for _, rel in files]
    xau = SM.kiem_secret(rels)
    if xau:
        raise SC.ContractError(
            "TỪ CHỐI đóng gói — những đường sau trông giống secret: " + ", ".join(xau) +
            ". Secret sống ở kho secret của máy; trạm chỉ giữ ĐƯỜNG DẪN tới chúng. "
            "Dời chúng ra rồi chạy lại.")
    if SM.MANIFEST in rels:
        raise SC.ContractError(f"trạm có sẵn file tên {SM.MANIFEST} — đổi tên nó rồi chạy lại "
                               "(tên đó là của manifest gói).")

    dem = SM.kiem_ke(rels)
    thu_muc = SM.thu_muc_giu(st, rels)
    if dry_run:
        mot_so = [{"path": rel, "size": f.stat().st_size} for f, rel in files]
        return {"out": str(out), "station": str(st), "dry_run": True,
                "count": len(files), "bytes": sum(m["size"] for m in mot_so),
                "with_git": bool(with_git), "logs_state": bool(logs_state),
                "state_files": dem, "dirs": thu_muc, "files": mot_so}

    muc = []
    out.parent.mkdir(parents=True, exist_ok=True)
    tam = out.with_name(out.name + ".part")
    try:
        with zipfile.ZipFile(tam, "w", zipfile.ZIP_DEFLATED) as z:
            for f, rel in files:
                muc.append({"path": rel, "size": f.stat().st_size, "sha256": SM.sha256(f)})
                z.write(f, rel)
            z.writestr(SM.MANIFEST, json.dumps({
                "kind": SM.KIND, "format": SM.FORMAT,
                "created": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                # Bên nhận cần biết ĐÚNG chuỗi thư mục nhà của máy cũ để đổi thành `~`.
                # Đoán bằng một regex "ổ đĩa + thư mục người dùng + tên nào đó" thì một
                # bài viết có nhắc đường dẫn của người khác cũng bị sửa theo.
                "source_home": str(Path.home()), "source_os": platform.system(),
                "station": str(st), "with_git": bool(with_git),
                "logs_state": bool(logs_state), "count": len(muc),
                "bytes": sum(m["size"] for m in muc), "state_files": dem,
                "dirs": thu_muc, "files": muc,
            }, ensure_ascii=False, indent=2))
        os.replace(tam, out)
    finally:
        if tam.exists():
            tam.unlink()
    return {"out": str(out), "station": str(st), "dry_run": False, "count": len(muc),
            "bytes": sum(m["size"] for m in muc), "with_git": bool(with_git),
            "logs_state": bool(logs_state), "state_files": dem, "dirs": thu_muc,
            "files": muc}


# ══ import ═══════════════════════════════════════════════════════════════════════════

def _dai(p: Path) -> Path:
    r"""Windows: bọc tiền tố `\\?\` để vượt giới hạn 260 ký tự của MAX_PATH.

    Gặp thật khi chạy T16: gói export xong gọn gàng, nhưng `import` chết giữa chừng vì
    một thư mục bài có slug dài nằm dưới một thư mục đích đã sâu sẵn. Hai điều đáng nhớ:

      · Giới hạn nằm ở BÊN NHẬN, không ở bên gửi — nên nó nổ đúng lúc người ta đang đổi
        máy và không còn máy cũ để thử lại.
      · Thư mục dựng tạm phải NGẮN, vì nó cộng thêm vào mọi đường bên trong: một cái tên
        dựng tạm dài hơn tên đích là tự làm hỏng thứ lẽ ra vừa đủ chỗ.

    Đường có tiền tố chỉ hợp lệ khi đã tuyệt đối và dùng `\`, nên phải `abspath` trước.
    """
    if os.name != "nt":
        return p
    s = os.path.abspath(str(p))
    if s.startswith("\\\\?\\"):
        return Path(s)
    if s.startswith("\\\\"):                       # UNC: \\may\chia -> \\?\UNC\may\chia
        return Path("\\\\?\\UNC" + s[1:])
    return Path("\\\\?\\" + s)


def _an_toan(duong: str) -> bool:
    """Entry của zip chỉ được là đường TƯƠNG ĐỐI, đi xuống, không có `..`, không ổ đĩa."""
    if not duong or duong.startswith("/") or "\\" in duong or ":" in duong:
        return False
    return ".." not in duong.split("/") and not Path(duong).is_absolute()


def _doc_manifest(z: zipfile.ZipFile, goi: Path) -> dict:
    try:
        mf = json.loads(z.read(SM.MANIFEST).decode("utf-8"))
    except KeyError:
        raise SC.ContractError(
            f"{goi} không có {SM.MANIFEST} — đây không phải gói của `station export`. "
            f"(Zip của `studio.py backup` mở bằng `studio.py`, không phải lệnh này.)")
    except (ValueError, UnicodeDecodeError) as e:
        raise SC.ContractError(f"{SM.MANIFEST} trong {goi} hỏng: {e}")
    if mf.get("kind") != SM.KIND:
        raise SC.ContractError(f"{goi}: manifest ghi kind={mf.get('kind')!r}, cần {SM.KIND!r}")
    if mf.get("format") != SM.FORMAT:
        raise SC.ContractError(
            f"{goi}: gói ở định dạng {mf.get('format')!r}, bản này đọc {SM.FORMAT}. "
            "Dùng đúng bản repo đã tạo gói.")
    return mf


# Byte có thể NỐI DÀI một tên thư mục. Ký tự ngay sau đường nhà mà nằm trong đây thì
# chuỗi vừa khớp chỉ là TIỀN TỐ của một tên khác, không phải đường nhà.
_NOI_TEN = frozenset(
    bytes([c]) for c in b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.")


def _doi_duong(b: bytes, nha_cu: str) -> bytes:
    """Đổi đường nhà của máy cũ thành `~`. Làm trên BYTE, không decode.

    Vì sao byte: `.ps1` mất BOM là PowerShell 5.1 parse hỏng và task chạy lịch im lặng
    không đăng gì; một vòng decode/encode cũng đủ để CRLF thành LF. Thay byte thì mọi thứ
    ngoài đúng chỗ được thay đều nguyên vẹn.

    Ba dạng của cùng một đường, thay theo thứ tự dài-trước: gạch chéo ngược ĐÔI (cách JSON
    viết đường Windows), gạch chéo ngược ĐƠN (trong `.ps1`/`.md`), và gạch chéo XUÔI
    (trong `.yml`). Trên máy POSIX cả ba là một, nên phép thay chỉ chạy không.

    Phép thay NEO RANH GIỚI: ký tự ngay sau đường nhà không được là ký tự có thể NỐI DÀI
    tên thư mục đó. Thay theo tiền tố thô thì thư mục nhà của một người là tiền tố tên nhà
    của người khác (`…/an` và `…/an-cu`), và một bản sao lưu cạnh đó bị viết lại thành
    một đường vô nghĩa (REVIEW-P2 Ghi nhận 1).
    """
    if len(nha_cu) < 4:
        return b
    _BS = chr(92)
    for truoc in (nha_cu.replace(_BS, _BS * 2), nha_cu, nha_cu.replace(_BS, "/")):
        goc = truoc.encode("utf-8")
        ra, i = bytearray(), 0
        while True:
            k = b.find(goc, i)
            if k < 0:
                ra += b[i:]
                break
            sau = b[k + len(goc):k + len(goc) + 1]
            ra += b[i:k] + (b"~" if sau not in _NOI_TEN else goc)
            i = k + len(goc)
        b = bytes(ra)
    return b


def _nen_doi(rel: str) -> bool:
    """`out/` KHÔNG bao giờ đổi: đó là nhật ký của cái đã đăng, và `*.published.json` là
    chốt chống upload trùng — nó phải giống hệt bản máy cũ, kể cả khi có đường dẫn trong đó."""
    phan = rel.split("/")
    if SM.VUNG_OUT in phan[:-1]:
        return False
    return Path(rel).suffix.lower() in DUOI_DOI_DUONG


def _git_refresh(st: Path) -> bool:
    """`.git` mang stat cache của hệ điều hành cũ ⇒ `git status` sau import đỏ rực dù
    không file nào đổi. Người dùng thấy thế sẽ `checkout -- .` và đè mất trạng thái vừa
    mang sang. `update-index --refresh` là cách nói với git "đọc lại đĩa đi".

    Mã thoát của nó KHÔNG phải tín hiệu lỗi: nó trả khác 0 khi có file thật sự đổi.
    """
    if not (st / ".git").is_dir() or not shutil.which("git"):
        return False
    try:
        subprocess.run(["git", "-C", str(st), "update-index", "--refresh"],
                       capture_output=True, timeout=300)
    except (OSError, subprocess.SubprocessError):
        return False
    return True


def _kham(st: Path) -> tuple[dict, dict]:
    """`check_tree` + `doctor` — hai câu hỏi khác nhau, chạy cả hai, KHÔNG lấy mã của
    chúng làm mã của `import`: máy vừa nhận gói gần như chắc chắn chưa cài xong trạm
    giọng/video (đó là lý do người ta đang import). Để `doctor` quyết mã thoát ở đây là
    biến bước đầu tiên của việc đổi máy thành một thất bại."""
    import check_tree as CT
    import doctor as DR
    try:
        s = CT.run_cmd(str(st))
        cay = {"fail": s.do, "warn": s.canh_bao}
    except Exception as e:                               # noqa: BLE001
        cay = {"fail": [f"check_tree không chạy được: {e}"], "warn": []}
    try:
        bs = DR.kham(str(st))
    except Exception as e:                               # noqa: BLE001
        bs = {"code": None, "station": str(st), "fail": [f"doctor không chạy được: {e}"],
              "warn": [], "info": []}
    return cay, bs


def import_station(archive, station) -> dict:
    goi = Path(archive).expanduser().resolve()
    if not goi.is_file():
        raise SC.StationMissing(f"không thấy gói {goi}")
    st = Path(station).expanduser().resolve()

    with zipfile.ZipFile(goi) as z:
        mf = _doc_manifest(z, goi)
        muc = mf.get("files") or []
        thu_muc = [d for d in (mf.get("dirs") or []) if isinstance(d, str)]
        xau = [d for d in thu_muc if not _an_toan(d)]
        xau += [m.get("path") for m in muc if not _an_toan(str(m.get("path") or ""))]
        if xau:
            raise SC.ContractError(
                f"TỪ CHỐI — gói có đường đi ra ngoài thư mục đích: {xau[:5]}. "
                "Gói này không phải do `station export` tạo, hoặc đã bị sửa.")
        stw = _dai(st)
        cham = [m["path"] for m in muc if (stw / m["path"]).exists()]
        if cham:
            raise SC.ContractError(
                f"TỪ CHỐI — {len(cham)} file đã có ở {st}, ví dụ: {cham[:5]}. "
                "`import` KHÔNG ĐÈ: bản ở đích có thể mới hơn bản trong gói. Dọn thư mục "
                "đích (hoặc trỏ --station vào chỗ trống) rồi chạy lại. CHƯA ghi gì.")
        ket = _to_tien_la_file(stw, [m["path"] for m in muc] + thu_muc)
        if ket:
            raise SC.ContractError(
                f"TỪ CHỐI — ở {st} đang có FILE trùng tên THƯ MỤC của gói: {ket[:5]}. "
                "Cổng trên chỉ so từng đường file nên không thấy ca này; để nó chạy tiếp "
                "là nổ giữa vòng chuyển và để lại cây nửa vời. Dọn/đổi tên chỗ đó rồi chạy "
                "lại. CHƯA ghi gì.")

        if os.name == "nt":
            dai = sorted(((len(str(st / m["path"])), m["path"]) for m in muc), reverse=True)
            if dai and dai[0][0] > GIOI_HAN_DUONG:
                raise SC.ContractError(
                    f"TỪ CHỐI — đích {st} quá sâu: {sum(1 for n, _ in dai if n > GIOI_HAN_DUONG)}"
                    f" đường sẽ vượt {GIOI_HAN_DUONG} ký tự (dài nhất {dai[0][0]}: "
                    f"{dai[0][1]}). PowerShell 5.1 không mở được đường dài hơn thế, nên "
                    "pipeline sẽ hỏng ngầm. Trỏ --station vào thư mục nông hơn "
                    "(ví dụ ngay trong thư mục nhà). CHƯA ghi gì.")
        _dai(st.parent).mkdir(parents=True, exist_ok=True)
        tam = _dai(st.parent / f".imp{os.getpid()}")
        if tam.exists():
            shutil.rmtree(tam)
        doi = []
        try:
            for m in muc:
                rel, cho = m["path"], tam / m["path"]
                try:
                    b = z.read(rel)
                except KeyError:
                    raise SC.ContractError(f"gói thiếu entry {rel!r} mà manifest có khai — "
                                           "gói hỏng, chép lại từ máy nguồn.")
                if m.get("sha256") and SM.sha256_bytes(b) != m["sha256"]:
                    raise SC.ContractError(
                        f"sha256 KHÔNG khớp ở {rel} — gói hỏng dọc đường. Chưa ghi gì vào "
                        f"{st}; chép lại gói từ máy nguồn rồi chạy lại.")
                if _nen_doi(rel):
                    moi = _doi_duong(b, str(mf.get("source_home") or ""))
                    if moi != b:
                        doi.append(rel)
                        b = moi
                cho.parent.mkdir(parents=True, exist_ok=True)
                cho.write_bytes(b)
            for d in thu_muc:
                (tam / d).mkdir(parents=True, exist_ok=True)
            try:
                _dat_vao_cho(tam, stw)
            except OSError as e:
                # `classify` xếp `OSError` vào mã 1 = "thử lại được", và bộ lập lịch thử
                # lại mã 1. Va chạm ở đích không bao giờ tự khỏi: phải là mã 2 (REVIEW-P2 N5).
                raise SC.ContractError(
                    f"không đưa được cây vừa dựng vào {st}: {e}. Đích có thứ gì đó chặn "
                    f"(file trùng tên thư mục, quyền, hoặc đường quá dài) — sửa rồi chạy "
                    f"lại; chạy lại nguyên trạng là vô ích.") from e
        finally:
            if tam.exists():
                shutil.rmtree(tam, ignore_errors=True)

    rels = [m["path"] for m in muc]
    dem = SM.kiem_ke(rels)
    cay, bs = _kham(st)
    return {"station": str(st), "count": len(muc),
            "bytes": sum(int(m.get("size") or 0) for m in muc),
            "source_home": mf.get("source_home"), "source_os": mf.get("source_os"),
            "state_files": dem, "dirs": thu_muc, "missing": SM.thieu(dem), "rewritten": doi,
            "git_refreshed": _git_refresh(st), "check_tree": cay, "doctor": bs}


def _to_tien_la_file(stw: Path, rels) -> list[str]:
    """Thư mục tổ tiên nào của gói đang là một FILE ở đích.

    Cổng va chạm phía trên chỉ so ĐƯỜNG FILE. Gói có `engine/run.ps1` mà đích có sẵn một
    FILE tên `engine` thì không đường file nào trùng — cổng cho qua, rồi `mkdir` nổ giữa
    vòng chuyển và để lại cây nửa vời (REVIEW-P2 N5)."""
    xau, da_xem = [], set()
    for rel in rels:
        for cha in Path(str(rel)).parents:
            k = cha.as_posix()
            if k in (".", "") or k in da_xem:
                continue
            da_xem.add(k)
            if (stw / cha).is_file():
                xau.append(k)
    return sorted(xau)


def _dat_vao_cho(tam: Path, st: Path):
    """Dựng xong ở thư mục dựng tạm rồi mới đưa vào chỗ: một lỗi giữa chừng để lại thư mục
    đích y như trước, thay vì một cây giải nén dở dang trông như đã import xong."""
    if not st.exists():
        try:
            os.replace(tam, st)
            return
        except OSError:
            pass                                  # khác ổ đĩa — chuyển từng file
    for dp, _dn, fn in os.walk(tam):
        goc = Path(dp)
        # Tạo cả thư mục RỖNG: `out/<ngày>/` rỗng là một mục có nghĩa (xem
        # `station_manifest.thu_muc_giu`), và nhánh này chỉ chuyển file thì nó biến mất
        # đúng trong trường hợp khó thấy nhất — đích đã tồn tại, hoặc khác ổ đĩa.
        (st / goc.relative_to(tam)).mkdir(parents=True, exist_ok=True)
        for n in fn:
            a = goc / n
            b = st / a.relative_to(tam)
            try:
                os.replace(a, b)
            except OSError:
                shutil.copy2(a, b)
                a.unlink()


# ══ CLI ══════════════════════════════════════════════════════════════════════════════

def _in_export(kq: dict):
    SC.log(f"[export] trạm {kq['station']}")
    SC.log(f"[export] {kq['count']} file · {kq['bytes'] / 1e6:.1f} MB"
           f"{' · kèm .git' if kq['with_git'] else ''}"
           f"{' · kèm trạng thái logs' if kq['logs_state'] else ''}")
    for nhan, n in kq["state_files"].items():
        SC.log(f"           {nhan:<24} {n}")
    # Nói HẬU QUẢ ngay ở export, không đợi tới import: lúc import người ta đã ở máy mới và
    # không còn máy cũ để lấy lại thứ thiếu (REVIEW-P2 Ghi nhận 2).
    for dong in SM.thieu(kq["state_files"]):
        SC.log(f"[export] ⚠ {dong}")
    if kq["dry_run"]:
        SC.log("[export] --dry-run: chưa ghi gì.")
    else:
        SC.log(f"[export] -> {kq['out']}")


def _in_import(kq: dict):
    SC.log(f"[import] {kq['count']} file -> {kq['station']}")
    if kq["rewritten"]:
        SC.log(f"[import] đổi đường máy cũ ({kq['source_home']}) thành ~ trong "
               f"{len(kq['rewritten'])} file")
        ma = [r for r in kq["rewritten"] if Path(r).suffix.lower() in (".py", ".ps1")]
        if ma:
            # `~` chỉ là một KÝ TỰ cho tới khi ai đó nở nó. PowerShell nở khi phân giải
            # đường; Python thì KHÔNG, trừ khi code gọi `expanduser`. Một đường cứng nằm
            # trong `.py` vì thế vẫn hỏng sau khi đổi — chỉ khác là hỏng ở chỗ nhìn thấy
            # được, thay vì trỏ vào một ổ đĩa không tồn tại trên máy mới.
            SC.log(f"  SOÁT   {len(ma)} file mã có đường vừa đổi: {', '.join(ma[:6])}"
                   f"{' …' if len(ma) > 6 else ''}\n"
                   "         `~` chỉ nở khi shell/PowerShell phân giải đường hoặc code gọi "
                   "expanduser — file .py giữ đường cứng thì vẫn phải sửa tay.")
    if kq["git_refreshed"]:
        SC.log("[import] đã chạy `git update-index --refresh` (stat cache khác hệ điều hành)")
    for x in kq["missing"]:
        SC.log(f"  THIẾU  {x}")
    for x in kq["check_tree"]["fail"]:
        SC.log(f"  cây    ĐỎ {x}")
    for x in kq["doctor"]["fail"]:
        SC.log(f"  bản cài ĐỎ {x}")
    SC.log(f"\n[import] xong. `doctor` trả mã {kq['doctor'].get('code')} — máy mới thường còn "
           f"thiếu trạm giọng/video, đó là việc tiếp theo, không phải lỗi của gói.")
    SC.log(f"[import] ĐỌC TRƯỚC KHI BẬT LỊCH: {RUNBOOK} — một máy chạy tại một thời điểm.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog=PROG, description="Đóng gói trạm để đổi máy, và mở gói ở máy mới.")
    con = ap.add_subparsers(dest="cmd", required=True)

    e = con.add_parser("export", help="đóng gói trạm theo danh sách khai rõ (§4)")
    e.add_argument("--station", help="gốc trạm nguồn (mặc định: trạm đang phân giải)")
    e.add_argument("--out", required=True, help="file zip đích (phải nằm NGOÀI trạm)")
    e.add_argument("--with-git", action="store_true",
                   help="kèm .git/ — một gói, đủ lịch sử (~19 MB)")
    e.add_argument("--include-logs-state", action="store_true",
                   help="kèm trạng thái trong logs/: tin duyệt chờ, việc chờ, nhật ký sự kiện")
    e.add_argument("--dry-run", action="store_true", help="chỉ liệt kê, không ghi gì")

    i = con.add_parser("import", help="mở gói vào một trạm (KHÔNG đè file đã có)")
    i.add_argument("archive", help="file zip do `export` tạo")
    i.add_argument("--station", required=True, help="gốc trạm đích")

    for p in (ap, e, i):
        p.add_argument("--json", action="store_true")
    args, ma = SC.parse(ap, argv)
    if args is None:
        return ma
    args.prog = PROG

    def chay(a):
        if a.cmd == "export":
            kq = export_station(a.station or SP.root(), a.out, with_git=a.with_git,
                                logs_state=a.include_logs_state, dry_run=a.dry_run)
            _in_export(kq)
        else:
            kq = import_station(a.archive, a.station)
            _in_import(kq)
        return kq
    return SC.run(chay, args, getattr(args, "json", False))


if __name__ == "__main__":
    sys.exit(main())
