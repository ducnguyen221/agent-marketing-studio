#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vòng đời một bản cài: `update` · `backup` · `migrate --to separate` · `uninstall`.

Bốn lệnh cho bốn lúc trong đời một bản cài, và cả bốn viết ra vì cùng một lý do: người dùng
chế độ `embedded` có nội dung nằm TRONG thư mục repo, nên những thao tác quen thuộc với
repo (xoá đi clone lại, `git clean`, chép tay) sẽ ăn mất nội dung của họ.

    update   = `git pull --ff-only`, KHÔNG BAO GIỜ xoá gì; checkout có file sửa chưa commit
               thì dừng trước khi kéo. Tài liệu nói thẳng: đừng xoá folder repo để cài lại.
    uninstall = gỡ đúng phần bộ cài tạo (`studio.local.json`, hook pre-commit của nó);
               GIỮ trạm, `.env` và repo.
    backup   = zip cả trạm. Mặc định KHÔNG kèm `.env`; kèm thì phải xin rõ `--with-env`.
    migrate  = đường ra khi người dùng lớn lên: dời `<repo>/workspace/` ra ngoài repo và
               `.env` về kho secret của máy, rồi ghi lại lựa chọn.

`export/import` gói chuyển máy (có manifest + sha256, chọn file theo danh sách khai rõ) là
việc của `station.py` — khác mục đích: `backup` là ảnh chụp cho chính mình, `export` là gói
bàn giao sang máy khác.

Mã thoát theo `scripts/lib/studio_contract.py`: 0 · 1 · 2 · 3.
"""
from __future__ import annotations

import argparse
import errno
import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import station_manifest as SM  # noqa: E402
import studio_contract as SC  # noqa: E402
import studio_paths as SP  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

PROG = "studio"
KHO_SECRET_MAC_DINH = Path.home() / ".secret" / "marketing-studio"

# Tên nhìn giống secret: không bao giờ tự động vào gói. Bộ mẫu khai ở `station_manifest`
# và dùng chung với `station.py export` — hai bản sao của một danh sách secret sẽ lệch
# nhau, và cái lệch là cái rò.
MAU_GIONG_SECRET = SM.MAU_GIONG_SECRET
_giong_secret = SM.giong_secret
BO_QUA_THU_MUC = {".git", "__pycache__", ".venv", "venv", ".tmp", ".pytest_cache"}
BO_QUA_FILE = ("*.pyc", "~$*")


def _bo_qua_file(ten: str) -> bool:
    return any(fnmatch.fnmatch(os.path.basename(ten), m) for m in BO_QUA_FILE)


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for khoi in iter(lambda: f.read(1 << 20), b""):
            h.update(khoi)
    return h.hexdigest()


# ── update ────────────────────────────────────────────────────────────────────────────

def _sua_doi_cuc_bo(repo: Path) -> list[str]:
    """File ĐÃ TRACK đang có sửa đổi chưa commit. File bị ignore (`workspace/`, `.env`,
    `studio.local.json`) không tính — đó là dữ liệu của người dùng, không phải mã."""
    r = subprocess.run(["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=no"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=60)
    if r.returncode != 0:
        raise SC.EngineError("`git status` không chạy được: " + (r.stderr or r.stdout).strip())
    return [d[3:] for d in (r.stdout or "").splitlines() if d.strip()]


def update() -> dict:
    repo = SP.repo_root()
    if not repo or not (repo / ".git").exists():
        raise SC.ContractError("không thấy bản clone git của repo — `update` chỉ chạy trên "
                               "bản clone (git clone, đừng tải zip).")
    # Kiểm TRƯỚC khi kéo: `pull --ff-only` vẫn chạy khi file sửa tay không đụng file mới về,
    # và người dùng không hề biết bản mình đang chạy là "mã mới + sửa cũ". Có sửa đổi thì
    # dừng; KHÔNG stash, KHÔNG reset, KHÔNG clean — chỗ sửa đó có thể là công việc của họ.
    ban = _sua_doi_cuc_bo(repo)
    if ban:
        raise SC.ContractError(
            f"checkout có {len(ban)} file đã sửa mà chưa commit: {', '.join(ban[:6])}. "
            "Commit hoặc tự cất chúng đi rồi chạy lại — `update` không bao giờ tự bỏ sửa "
            "đổi của bạn. Chưa kéo gì.")
    r = subprocess.run(["git", "-C", str(repo), "pull", "--ff-only"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=300)
    if r.returncode != 0:
        raise SC.EngineError(
            "`git pull --ff-only` không chạy được (nhánh lệch, hoặc có sửa đổi cục bộ). "
            "KHÔNG xoá gì cả — xử lý tay rồi chạy lại.\n" + (r.stderr or r.stdout).strip())
    return {"repo": str(repo), "output": (r.stdout or "").strip()}


# ── uninstall ─────────────────────────────────────────────────────────────────────────
#
# Gỡ ĐÚNG phần bộ cài sở hữu, không hơn. Bộ cài (`init_station.py`) tạo ra bốn thứ:
#
#   studio.local.json   lựa chọn chế độ + đường trạm        → GỠ
#   hook pre-commit     rào lớp hai của embedded            → GỠ nếu đúng là hook của bộ cài
#   .env                chép từ .env.example rồi BẠN điền   → GIỮ (cấu hình của bạn)
#   trạm                workspace/ hoặc thư mục ngoài       → GIỮ (nội dung của bạn)
#
# Xoá nội dung không bao giờ là một phần của gỡ công cụ. Skill và adapter host là file
# được git theo dõi trong repo — gỡ chúng là xoá repo, việc đó người dùng tự làm.

DAU_HOOK = "Hook pre-commit của chế độ cài `embedded`"


def _hook_pre_commit(repo: Path) -> Path | None:
    """Đường hook THẬT theo git (worktree có `.git` là file). Không tạo gì."""
    try:
        r = subprocess.run(["git", "-C", str(repo), "rev-parse", "--git-path", "hooks"],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0 or not (r.stdout or "").strip():
        return None
    p = Path((r.stdout or "").strip())
    return (p if p.is_absolute() else repo / p) / "pre-commit"


def uninstall(dry_run: bool = False) -> dict:
    repo = SP.repo_root()
    if not repo:
        raise SC.ContractError("không xác định được gốc repo (đặt MARKETING_STUDIO_HOME).")
    try:
        lc = SP.local_config(repo)
    except SP.StudioPathsError:
        lc = {}                      # file hỏng vẫn là file của bộ cài — gỡ được
    try:
        tram, nguon = SP.resolve_station()
    except SP.StudioPathsError:
        tram, nguon = None, None
    go, giu = [], []

    f = repo / SP.LOCAL_CONFIG
    if f.is_file():
        go.append(str(f))
        if not dry_run:
            f.unlink()

    hook = _hook_pre_commit(repo)
    if hook and hook.is_file():
        try:
            cua_bo_cai = DAU_HOOK in hook.read_text(encoding="utf-8", errors="replace")
        except OSError:
            cua_bo_cai = False
        if cua_bo_cai:
            go.append(str(hook))
            if not dry_run:
                hook.unlink()
        else:
            giu.append(f"{hook} — không phải hook của bộ cài, không đụng")

    env = repo / ".env"
    if env.is_file():
        giu.append(f"{env} — cấu hình bạn đã điền (xoá tay nếu chắc không cần)")
    if tram is not None and tram.is_dir():
        giu.append(f"{tram} — trạm nội dung (nguồn: {nguon}); gỡ công cụ KHÔNG xoá nội dung")
    if (os.environ.get("MARKETING_STUDIO_DATA") or "").strip():
        giu.append("biến MARKETING_STUDIO_DATA vẫn đặt ở máy — gỡ tay nếu không dùng trạm đó nữa")
    return {"repo": str(repo), "dry_run": bool(dry_run), "mode": lc.get("mode"),
            "station": str(tram) if tram else None, "removed": go, "kept": giu}


# ── backup ────────────────────────────────────────────────────────────────────────────

def _liet_ke(st: Path):
    for dp, dn, fn in os.walk(st):
        dn[:] = [d for d in dn if d not in BO_QUA_THU_MUC]
        for n in sorted(fn):
            f = Path(dp) / n
            rel = f.relative_to(st).as_posix()
            if not _bo_qua_file(rel):
                yield f, rel


def backup(out, station=None, with_env=False) -> dict:
    st = SP.root(station)
    if not st.is_dir():
        raise SC.StationMissing(f"không có trạm ở {st} — chạy init_station.py trước")
    files = list(_liet_ke(st))
    xau = [rel for _, rel in files if _giong_secret(rel)]
    if xau:
        raise SC.ContractError(
            "từ chối đóng gói — trong trạm có file trông giống secret: " + ", ".join(xau) +
            ". Dời chúng về kho secret của máy rồi chạy lại (biến chỉ giữ ĐƯỜNG DẪN).")
    repo = SP.repo_root()
    if with_env and repo and (repo / ".env").is_file():
        files.append((repo / ".env", ".env"))
    manifest = {"kind": "backup", "station": str(st), "with_env": bool(with_env),
                "files": [rel for _, rel in files]}
    out = Path(out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    tam = out.with_suffix(out.suffix + ".part")
    try:
        with zipfile.ZipFile(tam, "w", zipfile.ZIP_DEFLATED) as z:
            for f, rel in files:
                z.write(f, rel)
            z.writestr("marketing-studio-backup.json",
                       json.dumps(manifest, ensure_ascii=False, indent=2))
        os.replace(tam, out)
    finally:
        if tam.exists():
            tam.unlink()
    return {"out": str(out), "files": manifest["files"], "station": str(st),
            "with_env": bool(with_env)}


# ── migrate --to separate ─────────────────────────────────────────────────────────────

def _doi_cay(nguon: Path, dich: Path):
    """Dời thư mục an toàn. Cùng ổ: `os.rename` — hỏng thì hỏng SẠCH, chưa đụng gì.
    Khác ổ: chép → đối chiếu sha256 từng file → mới xoá nguồn (ba bước rời).

    KHÔNG dùng `shutil.move` cho thư mục: khi `rename` bị từ chối (một chương trình đang
    giữ file) nó âm thầm rơi về copytree + rmtree, và rmtree dừng giữa chừng ⇒ cây nằm hai
    nơi, trông y như mất dữ liệu.
    """
    try:
        os.rename(nguon, dich)
        return
    except OSError as e:
        khac_o = e.errno == errno.EXDEV or getattr(e, "winerror", None) == 17
        if not khac_o:
            raise SC.ContractError(
                f"không dời được {nguon} → {dich} ({e}). Có thể một chương trình đang mở file "
                "trong trạm — đóng nó rồi chạy lại. CHƯA đụng gì.")
    shutil.copytree(nguon, dich)
    for dp, _dn, fn in os.walk(nguon):
        for n in fn:
            a = Path(dp) / n
            b = dich / a.relative_to(nguon)
            if not b.is_file() or _sha256(a) != _sha256(b):
                raise SC.EngineError(
                    f"bản chép sang {dich} không khớp ở {b} — nguồn {nguon} GIỮ NGUYÊN. "
                    "Xoá bản chép dở ở đích rồi chạy lại.")
    try:
        shutil.rmtree(nguon)
    except OSError as e:
        raise SC.EngineError(
            f"đã chép đủ và khớp sang {dich}, nhưng xoá nguồn {nguon} dở dang ({e}). Phần còn "
            "lại ở nguồn là BẢN SAO — đừng chạy lại lệnh; đóng chương trình đang giữ file rồi "
            "xoá tay.")


def _doi_file(nguon: Path, dich: Path):
    try:
        os.rename(nguon, dich)
    except OSError:
        shutil.copy2(nguon, dich)
        if _sha256(nguon) != _sha256(dich):
            dich.unlink()
            raise SC.EngineError(f"chép {nguon} → {dich} không khớp; giữ nguyên nguồn")
        nguon.unlink()


def migrate_sang_separate(station=None, kho_secret=None) -> dict:
    repo = SP.repo_root()
    if not repo:
        raise SC.ContractError("không xác định được gốc repo (đặt MARKETING_STUDIO_HOME).")
    if SP.mode(repo) != "embedded":
        raise SC.ContractError(
            f"máy này không ở chế độ embedded (đang: {SP.mode(repo) or 'chưa cài'}) — "
            "không có gì để dời.")
    ws = repo / SP.WORKSPACE
    if not ws.is_dir():
        raise SC.StationMissing(f"không có {ws} — chưa có trạm nào nằm trong repo.")
    dich = Path(station).expanduser().resolve() if station else \
        (Path.home() / ".marketing").resolve()
    if dich.exists() and any(dich.iterdir()):
        raise SC.ContractError(f"thư mục đích không rỗng: {dich} — chọn chỗ khác (--station).")
    kho = Path(kho_secret).expanduser().resolve() if kho_secret else KHO_SECRET_MAC_DINH

    # Kiểm MỌI điều kiện TRƯỚC khi dời byte đầu tiên: dời được nửa đường rồi mới phát hiện
    # đích kẹt là kiểu hỏng khó dọn nhất.
    f_env = repo / ".env"
    env_dich = (kho / ".env") if f_env.is_file() else None
    if env_dich and env_dich.exists():
        raise SC.ContractError(
            f"{env_dich} đã có — gộp tay rồi xoá {f_env}, sau đó chạy lại. Chưa đụng gì.")

    if dich.is_dir():
        dich.rmdir()
    dich.parent.mkdir(parents=True, exist_ok=True)
    _doi_cay(ws, dich)
    if env_dich:
        kho.mkdir(parents=True, exist_ok=True)
        _doi_file(f_env, env_dich)

    lc = SP.local_config(repo)
    lc.update({"mode": "separate", "station_path": str(dich), "secrets": str(kho)})
    (repo / SP.LOCAL_CONFIG).write_text(json.dumps(lc, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8", newline="\n")
    return {"mode": "separate", "station": str(dich),
            "env_moved_to": str(env_dich) if env_dich else None}


# ── CLI ───────────────────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog=PROG,
                                 description="Vòng đời bản cài: update · backup · migrate · uninstall.")
    con = ap.add_subparsers(dest="lenh", required=True)

    con.add_parser("update", help="git pull --ff-only (không bao giờ xoá gì)")

    b = con.add_parser("backup", help="zip cả trạm (mặc định KHÔNG kèm .env)")
    b.add_argument("--out", required=True, help="file zip đích")
    b.add_argument("--station", help="trạm nguồn (mặc định: trạm đang phân giải)")
    b.add_argument("--with-env", action="store_true", help="kèm <repo>/.env (CHỨA cấu hình bí mật)")

    m = con.add_parser("migrate", help="dời trạm embedded ra ngoài repo")
    m.add_argument("--to", required=True, choices=["separate"])
    m.add_argument("--station", help="đích (mặc định ~/.marketing)")
    m.add_argument("--secret-dir", help="kho secret nhận .env (mặc định ~/.secret/marketing-studio)")

    u = con.add_parser("uninstall", help="gỡ phần bộ cài sở hữu; GIỮ trạm, .env, repo")
    u.add_argument("--dry-run", action="store_true", help="chỉ liệt kê, không gỡ gì")

    for p in (ap, b, m, u):
        p.add_argument("--json", action="store_true")
    args, ma = SC.parse(ap, argv)
    if args is None:
        return ma
    args.prog = PROG

    def chay(a):
        if a.lenh == "update":
            kq = update()
            SC.log(kq["output"] or "[update] đã mới nhất")
        elif a.lenh == "backup":
            kq = backup(a.out, a.station, a.with_env)
            SC.log(f"[backup] {len(kq['files'])} file → {kq['out']}")
        elif a.lenh == "uninstall":
            kq = uninstall(a.dry_run)
            dau = "(xem trước — chưa gỡ gì) " if kq["dry_run"] else ""
            SC.log(f"[uninstall] {dau}gỡ {len(kq['removed'])} mục của bộ cài")
            for x in kq["removed"]:
                SC.log(f"  - {x}")
            for x in kq["kept"]:
                SC.log(f"  giữ {x}")
        else:
            kq = migrate_sang_separate(a.station, a.secret_dir)
            SC.log(f"[migrate] trạm giờ ở {kq['station']} — đặt MARKETING_STUDIO_DATA trỏ vào đó")
            if kq["env_moved_to"]:
                SC.log(f"[migrate] .env → {kq['env_moved_to']}")
        return kq
    return SC.run(chay, args, getattr(args, "json", False))


if __name__ == "__main__":
    sys.exit(main())
