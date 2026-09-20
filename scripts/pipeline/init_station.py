#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dựng trạm nội dung — LÕI của bộ cài, dùng chung cho mọi hệ điều hành.

`install.ps1` (Windows) và `install.sh` (macOS/Linux) chỉ là **vỏ**: chúng dò Python rồi
gọi file này. Mọi quyết định — hỏi gì, tạo gì, ghi gì — nằm ở đây, một chỗ, để hai vỏ
không bao giờ trôi khỏi nhau.

## Hai chế độ cài (F17)

    embedded   trạm = <repo>/workspace/, biến cấu hình ở <repo>/.env (cả hai bị git bỏ qua)
               "mở một folder là thấy hết" — MẶC ĐỊNH và là khuyến nghị cho người mới
    separate   trạm ngoài repo (mặc định ~/.marketing), biến đặt ở cấp user, bí mật ở kho
               secret của máy — cho người nhiều máy, hoặc repo public của chính họ

Lựa chọn ghi vào `<repo>/studio.local.json`; `studio_paths.resolve_station()` đọc lại nó
cho MỌI script về sau.

## Ba luật của file này

1. **Bắt buộc hỏi, không tự chọn im lặng.** Chế độ quyết định nội dung của người dùng nằm
   trong hay ngoài repo — đó là quyết định của họ.
2. **Không có người trả lời thì DỪNG.** `stdin` không phải terminal (CI, tác vụ theo lịch,
   pipe) ⇒ in bảng lựa chọn ra stderr rồi thoát **mã 2**, chưa ghi một byte nào. Đoán hộ ở
   đây là dựng trạm sai chỗ, và người dùng chỉ phát hiện ra sau khi đã viết vài bài.
3. **Máy đã có trạm ngoài thì tự `separate`, không hỏi, KHÔNG BAO GIỜ tạo `workspace/`.**
   Hai nguồn sự thật cho cùng một repo là cách mất dữ liệu êm nhất. Đây cũng là thứ bảo vệ
   máy đang chạy lịch thật.

Chạy lại an toàn: không đè file đã có, không xoá gì.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import studio_contract as SC  # noqa: E402
import studio_paths as SP  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):     # stream bị thay (test, pipe lạ) — không phải lỗi
    pass

PROG = "init_station"
# Biến nào đã đặt cũng có nghĩa "máy này đã theo mô hình trạm ngoài" — kể cả biến của hai
# trạm năng lực kia: người đã tách trạm giọng/video ra thì không đời nào muốn trạm nội dung
# chui vào trong repo.
BIEN_NHAN_DIEN = ("MARKETING_STUDIO_DATA", "VOICE_STATION", "VIDEO_STATION",
                  "OMNIVOICE_DIR", "VIDEO_ROOT")
# Giá trị này ĐI VÀO studio.local.json, nên nó phải là ASCII và là một đường dẫn thật:
# một chuỗi mô tả có dấu ("~/.secret/<tài-khoản>/") đọc bằng công cụ khác encoding sẽ hiện
# ra rác, và không ai dán nó vào đâu được. Trùng mặc định của `studio.py migrate`.
KHO_SECRET = "~/.secret/marketing-studio"

BANG_LUA_CHON = """\
Chọn chỗ đặt TRẠM nội dung (nơi chứa kênh, chiến dịch, bài, sản phẩm đã dựng):

  [1] embedded — gọn trong repo   ← KHUYẾN NGHỊ (bấm Enter)
      Là gì : trạm nằm ở <repo>/workspace/, biến cấu hình ở <repo>/.env (git bỏ qua cả hai).
      Lợi   : mở một folder là thấy hết; không phải đặt biến môi trường; backup một phát.
      Hại   : xoá folder repo là mất luôn nội dung — đừng xoá repo để cài lại, dùng
              `studio.py update`; và nhớ `studio.py backup`.
      Chọn khi: một máy, muốn dùng được ngay, không rành kỹ thuật.

  [2] separate — trạm ngoài repo (mặc định ~/.marketing)
      Là gì : trạm ở thư mục riêng; bí mật ở kho secret của máy ({kho}).
      Lợi   : repo luôn sạch (an toàn khi repo là bản public của chính bạn); nhiều máy /
              nhiều repo dùng chung một trạm; cập nhật repo không đụng nội dung.
      Hại   : thêm một chỗ phải nhớ; nên đặt MARKETING_STUDIO_DATA cho lịch chạy thấy trạm.
      Chọn khi: rành kỹ thuật, nhiều máy, hoặc repo public của chính bạn.

Sau này đổi ý được: `python scripts/pipeline/studio.py migrate --to separate`.
""".format(kho=KHO_SECRET)


# ── nhận diện máy đã có trạm ngoài (F17.2) ────────────────────────────────────────────

def nha_marketing() -> Path:
    return (Path.home() / ".marketing").resolve()


def tram_ngoai_co_san():
    """-> (gốc trạm, lý do) nếu máy này đã theo mô hình trạm ngoài; không thì None.

    KHÔNG ghi gì, không tạo gì — chỉ đọc biến và một lần `is_file()`.
    """
    ly_do = [b for b in BIEN_NHAN_DIEN if (os.environ.get(b) or "").strip()]
    if ly_do:
        bien_tram = (os.environ.get("MARKETING_STUDIO_DATA") or "").strip()
        goc = Path(bien_tram).expanduser().resolve() if bien_tram else nha_marketing()
        return goc, "biến " + ", ".join(ly_do) + " đã đặt"
    nha = nha_marketing()
    if (nha / SP.SO_KENH).is_file():
        return nha, f"{nha} đã là một trạm (có {SP.SO_KENH})"
    return None


def _co_nguoi_tra_loi() -> bool:
    try:
        return sys.stdin is not None and sys.stdin.isatty()
    except Exception:            # noqa: BLE001 — stdin bị thay (pytest, dịch vụ nền)
        return False


def _hoi_ban_phim(bang: str) -> str:
    SC.log(bang)
    sys.stderr.write("Chọn [1/2] (Enter = 1, embedded): ")
    sys.stderr.flush()
    return input()


def chon_che_do(station=None, mode=None, yes=False, ask=None, non_interactive=False):
    """-> (chế độ, gốc trạm, lý do). Ném ContractError khi cần người chọn mà không hỏi được.

    `non_interactive` = người gọi TỰ KHAI "không có ai ngồi đây". Nó KHÔNG có nghĩa là
    "cứ đoán hộ tôi": thiếu `--yes`/`--mode`/`--station` thì vẫn là mã 2. Hai vỏ cài
    (`install.ps1 -NonInteractive`, `install.sh --non-interactive`) cùng đổ vào đây, nên
    chúng không thể trôi khỏi nhau nữa (REVIEW-P2 N8)."""
    repo = SP.repo_root()
    if station:
        return "separate", Path(station).expanduser().resolve(), "--station"
    ngoai = tram_ngoai_co_san()
    if ngoai:
        if mode == "embedded":
            raise SC.ContractError(
                f"máy này đã có trạm ngoài ({ngoai[1]}) — tạo thêm {SP.WORKSPACE}/ trong repo "
                "sẽ thành hai nguồn sự thật cho cùng một repo. Bỏ --mode để dùng trạm đó, "
                "hoặc gỡ biến / dời trạm cũ trước.")
        return "separate", ngoai[0], f"nhận diện trạm có sẵn — {ngoai[1]}"
    if mode:
        ly_do = "--mode"
    else:
        truoc = SP.mode(repo) if repo else None
        if truoc == "separate":
            return "separate", SP.resolve_station()[0], f"{SP.LOCAL_CONFIG} (lần chọn trước)"
        if truoc:
            mode, ly_do = truoc, f"{SP.LOCAL_CONFIG} (lần chọn trước)"
        elif yes:
            mode, ly_do = "embedded", "--yes (nhận khuyến nghị)"
        else:
            if ask is None:
                if non_interactive or not _co_nguoi_tra_loi():
                    SC.log(BANG_LUA_CHON)
                    raise SC.ContractError(
                        "cần người dùng chọn chế độ cài. Agent: trình bảng ở trên cho người "
                        "dùng, rồi chạy lại với --mode embedded|separate (hoặc --yes = embedded).")
                ask = _hoi_ban_phim
            try:
                tra = (ask(BANG_LUA_CHON) or "").strip().lower()
            except EOFError:
                # Windows: stdin là NUL vẫn báo isatty() = True — hết dữ liệu nghĩa là
                # không có ai ngồi đó.
                raise SC.ContractError(
                    "không đọc được lựa chọn (stdin không có người). Agent: trình bảng lựa "
                    "chọn cho người dùng, rồi chạy lại với --mode embedded|separate.")
            if tra in ("", "1", "embedded"):
                mode = "embedded"
            elif tra in ("2", "separate"):
                mode = "separate"
            else:
                raise SC.ContractError(
                    f"lựa chọn không hợp lệ: {tra!r} (1 = embedded, 2 = separate)")
            ly_do = "người dùng chọn"
    if mode == "embedded":
        if not repo:
            raise SC.ContractError(
                "chế độ embedded cần chạy từ bản clone repo; không xác định được gốc repo "
                "(đặt MARKETING_STUDIO_HOME trỏ vào đó).")
        return "embedded", (repo / SP.WORKSPACE).resolve(), ly_do
    return "separate", nha_marketing(), ly_do


# ── dựng cây ──────────────────────────────────────────────────────────────────────────

def cay_mau(repo: Path | None) -> Path | None:
    t = (repo or Path(__file__).resolve().parents[2]) / "templates" / SP.WORKSPACE
    return t if t.is_dir() else None


def _chep_cay(nguon: Path, dich: Path, da_tao: list):
    """Chép cây mẫu, KHÔNG đè file đã có — chạy lại bộ cài không được ăn mất nội dung."""
    for dp, _dn, fn in os.walk(nguon):
        rel = Path(dp).relative_to(nguon)
        for n in fn:
            f = dich / rel / n
            if f.exists():
                continue
            f.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(dp) / n, f)
            da_tao.append(str((rel / n).as_posix()))


def _chep_env(repo: Path, da_tao: list):
    """`embedded`: dọn sẵn `<repo>/.env` từ `.env.example` và khoá quyền 600 trên POSIX."""
    mau, dich = repo / ".env.example", repo / ".env"
    if dich.exists() or not mau.is_file():
        return
    shutil.copyfile(mau, dich)
    da_tao.append(".env")
    if os.name != "nt":
        try:
            os.chmod(dich, stat.S_IRUSR | stat.S_IWUSR)
        except OSError as e:               # hệ tệp không hỗ trợ (exFAT, chia sẻ mạng)
            SC.log(f"[init] không đặt được quyền 600 cho .env ({e}) — kiểm tay.")


def _thu_muc_hook(repo: Path) -> Path | None:
    """`.git/hooks` THẬT — hỏi git, không đoán.

    Trong một `git worktree` thì `.git` là một FILE trỏ sang chỗ khác, nên phép thử
    `(repo/".git"/"hooks").is_dir()` sai và rào lớp hai lặng lẽ vắng mặt đúng ở nơi người
    ta hay thử nghiệm (REVIEW-P2 Ghi nhận 3)."""
    try:
        r = subprocess.run(["git", "-C", str(repo), "rev-parse", "--git-path", "hooks"],
                           capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and (r.stdout or "").strip():
            p = Path((r.stdout or "").strip())
            p = p if p.is_absolute() else (repo / p)
            p.mkdir(parents=True, exist_ok=True)
            return p
    except (OSError, subprocess.SubprocessError):
        pass
    hooks = repo / ".git" / "hooks"
    return hooks if hooks.is_dir() else None


def _cai_hook(repo: Path) -> str:
    hooks = _thu_muc_hook(repo)
    if hooks is None:
        return "không có .git/hooks"
    hook = hooks / "pre-commit"
    if hook.exists():
        return "giữ bản có sẵn"
    khuon = repo / "templates" / "hooks" / "pre-commit"
    if not khuon.is_file():
        return "không thấy khuôn"
    noi_dung = (khuon.read_text(encoding="utf-8")
                .replace("__PY__", sys.executable.replace("\\", "/"))
                .replace("__REPO__", str(repo).replace("\\", "/")))
    hook.write_text(noi_dung, encoding="utf-8", newline="\n")
    try:
        os.chmod(hook, 0o755)
    except OSError:
        pass
    return "đã cài"


def _tram_nang_luc_da_co(repo: Path | None) -> dict:
    """Cross-repo (F17.3): máy đã có trạm giọng/video thì ghi lại để `doctor` khỏi dò lại."""
    ra = {}
    for khoa, ham in (("voice_station", SP.voice_station), ("video_station", SP.video_station)):
        p = ham(repo)
        if p and p.is_dir():
            ra[khoa] = str(p)
    return ra


def _ghi_local(repo: Path, mode: str, st: Path, da_tao: list):
    f = repo / SP.LOCAL_CONFIG
    cu = SP.local_config(repo)
    cu.update({
        "mode": mode,
        "station_path": SP.WORKSPACE if mode == "embedded" else str(st),
        "secrets": ".env" if mode == "embedded" else KHO_SECRET,
    })
    cu.update(_tram_nang_luc_da_co(repo))
    f.write_text(json.dumps(cu, ensure_ascii=False, indent=2) + "\n",
                 encoding="utf-8", newline="\n")
    da_tao.append(SP.LOCAL_CONFIG)


# Windows không mở được đường dài hơn ngần này nếu chưa bật long path — cùng con số với
# `station.py:GIOI_HAN_DUONG`, và cùng bài học: kiểm TRƯỚC khi ghi.
GIOI_HAN_DUONG = 259


def _kiem_cho_dung(st: Path, existing: bool) -> None:
    """Hai lỗi CẤU HÌNH phải nổ thành mã 2, TRƯỚC khi ghi byte nào (REVIEW-P2 N6, N7).

    Cả hai đều từng lọt ra thành `FileExistsError`/`FileNotFoundError`, và `SC.classify`
    xếp chúng vào mã 1 hoặc 3 — mã 1 thì bộ lập lịch/CI thử lại vô hạn một thứ không bao
    giờ tự khỏi, còn cây nửa vời thì người dùng không biết mình phải dọn gì."""
    if st.exists() and not st.is_dir():
        raise SC.ContractError(
            f"--station {st} đang là một FILE, không phải thư mục. Đây là lỗi cấu hình: "
            f"chạy lại nguyên trạng là vô ích. Trỏ sang một thư mục (hoặc chỗ trống).")
    if os.name == "nt" and len(str(st)) > GIOI_HAN_DUONG - 60 and not existing:
        # Trừ hao 60 ký tự cho đường con sâu nhất của cây mẫu: kiểm đúng gốc trạm thì
        # cây dựng xong vẫn có thể có file không mở được, và nó hỏng ngầm về sau.
        raise SC.ContractError(
            f"--station {st} dài {len(str(st))} ký tự — cây trạm dựng bên trong sẽ vượt "
            f"giới hạn 260 ký tự của Windows và đường ống hỏng ngầm về sau. Trỏ vào một "
            f"thư mục nông hơn (ví dụ ngay trong thư mục nhà). CHƯA ghi gì.")


def _mkdir_don_neu_hong(st: Path) -> None:
    """Tạo gốc trạm; nổ giữa chừng thì dọn đúng phần MÌNH vừa tạo rồi báo mã 2."""
    da_co = [p for p in [st, *st.parents] if p.exists()]
    moc = da_co[0] if da_co else None
    try:
        st.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        p = st
        while p != moc and p.is_dir() and not any(p.iterdir()):
            cha = p.parent
            try:
                p.rmdir()
            except OSError:
                break
            p = cha
        raise SC.ContractError(
            f"không tạo được thư mục trạm {st}: {e}. Lỗi cấu hình — sửa đường dẫn rồi chạy "
            f"lại; phần cây vừa tạo dở đã được dọn.") from e


def do_init(station=None, mode=None, yes=False, existing=False, dry_run=False, ask=None,
            non_interactive=False) -> dict:
    mode, st, ly_do = chon_che_do(station=station, mode=mode, yes=yes, ask=ask,
                                  non_interactive=non_interactive)
    repo = SP.repo_root()
    kq = {"mode": mode, "station": str(st), "reason": ly_do, "repo": str(repo) if repo else None,
          "dry_run": bool(dry_run), "created": [], "hook": None}
    if existing and not st.is_dir():
        raise SC.StationMissing(
            f"--existing nhưng không có thư mục trạm: {st}. Bỏ --existing để dựng mới.")
    if dry_run:
        return kq
    _kiem_cho_dung(st, existing)
    da_tao = kq["created"]
    if not existing:
        _mkdir_don_neu_hong(st)
        t = cay_mau(repo)
        if t:
            _chep_cay(t, st, da_tao)
        else:
            SC.log("[init] không thấy templates/workspace — trạm dựng rỗng.")
    if repo:
        if mode == "embedded":
            _chep_env(repo, da_tao)
        _ghi_local(repo, mode, st, da_tao)
        if mode == "embedded":
            kq["hook"] = _cai_hook(repo)
    return kq


# ── in ra cho người đọc ───────────────────────────────────────────────────────────────

def _in(kq: dict):
    log = SC.log
    dau = "(xem trước — chưa ghi gì) " if kq["dry_run"] else ""
    log(f"[init] {dau}chế độ: {kq['mode']} · trạm: {kq['station']}")
    log(f"[init] lý do: {kq['reason']}")
    if kq["dry_run"]:
        return
    for c in kq["created"]:
        log(f"  + {c}")
    if kq["hook"]:
        log(f"[init] hook pre-commit: {kq['hook']}")
    if kq["mode"] == "separate":
        log(f"\nNên đặt biến cho lịch chạy thấy trạm: MARKETING_STUDIO_DATA={kq['station']}")
        log(f"Bí mật để ở kho secret của máy ({KHO_SECRET}); biến chỉ giữ ĐƯỜNG DẪN.")
    else:
        log("\nĐiền biến của bạn vào <repo>/.env (chỉ đường dẫn + cấu hình, KHÔNG token).")
    log("\nBước tiếp theo:")
    log(f"  python scripts/pipeline/new_channel.py --id ten-kenh --label \"Tên kênh\" "
        f"--path \"{Path(kq['station']) / 'ten-kenh'}\"")
    log("  python scripts/pipeline/new_campaign.py --channel ten-kenh --id CMP-001 "
        "--name \"Tên chiến dịch\" --prefix ABC")
    log("  python scripts/pipeline/check_tree.py")
    log("\nĐọc trước khi dùng: docs/ONBOARDING.md (dựng từ đầu) · docs/WORKSPACE.md "
        "(thư mục nào chứa gì)")
    log("Đổi máy — MỘT máy chạy tại một thời điểm: docs/RUNBOOK-DOI-MAY.md")


def _goi_doctor(kq: dict):
    """`doctor` là bước cuối của bộ cài. Bản cài rút gọn không kèm nó thì bỏ qua, không nổ.

    Gọi **không** `--station`: cả việc của bước này là kiểm rằng cái vừa ghi ra
    (`studio.local.json`, `workspace/`) khiến các script khác phân giải đúng trạm. Truyền
    sẵn đường trạm vào là tự trả lời hộ câu hỏi duy nhất đáng hỏi.
    """
    d = Path(__file__).resolve().parent / "doctor.py"
    if not d.is_file():
        return None
    SC.log("")
    r = subprocess.run([sys.executable, str(d)], text=True, encoding="utf-8", errors="replace")
    return r.returncode


def _parser_help() -> str:
    """Văn bản `--help` của lõi — để cổng parity so được cờ nào lõi thật sự hiểu."""
    return _parser().format_help()


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog=PROG, description="Dựng trạm nội dung (hai chế độ: embedded / separate).")
    ap.add_argument("--station", help="trạm ngoài repo — chọn separate, không hỏi")
    ap.add_argument("--mode", choices=SP.MODES, help="chọn chế độ, không hỏi")
    ap.add_argument("--yes", action="store_true", help="nhận khuyến nghị (embedded), không hỏi")
    ap.add_argument("--non-interactive", action="store_true",
                    help="không có ai trả lời: KHÔNG hỏi và KHÔNG đoán — thiếu "
                         "--yes/--mode/--station thì dừng với mã 2")
    ap.add_argument("--existing", action="store_true",
                    help="nhận một trạm đang chạy: không rải file mẫu")
    ap.add_argument("--dry-run", action="store_true", help="chỉ báo sẽ làm gì, không ghi")
    ap.add_argument("--no-doctor", action="store_true", help="bỏ bước kiểm cuối")
    ap.add_argument("--json", action="store_true", help="in một dòng JSON kết quả ra stdout")
    return ap


def main(argv=None) -> int:
    args, ma = SC.parse(_parser(), argv)
    if args is None:
        return ma
    args.prog = PROG

    def chay(a):
        kq = do_init(station=a.station, mode=a.mode, yes=a.yes, existing=a.existing,
                     dry_run=a.dry_run, non_interactive=a.non_interactive)
        _in(kq)
        if not a.dry_run and not a.no_doctor:
            kq["doctor"] = _goi_doctor(kq)
        return kq
    return SC.run(chay, args, args.json)


if __name__ == "__main__":
    sys.exit(main())
