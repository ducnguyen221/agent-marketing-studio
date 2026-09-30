# -*- coding: utf-8 -*-
"""Cổng chặn tái diễn: không file nào trong repo được giả định TÊN thư mục chứa các repo.

Đức, 30/09/2026: "cài ở một máy tính mới ở folder bất kỳ nó vẫn phải nhận diện được, không
hard code mà phải theo folder cha — gọi là repo hay code đều phải được". Bản 1.0.1 viết cứng
`~/Code/...` ở `run.ps1`, `web_publish.py`, hai chuỗi hướng dẫn cài, `.env.example` và năm
tài liệu; Mac clone ở `~/Repo` phải ghi đè tay. Đường tới repo anh em / repo web nay suy từ
thư mục cha của bản clone (`studio_paths.repo_anh_em`, `duong_repo_web`, `run.ps1` đi lên
từ trạm) — file này giữ cho literal cũ không quay lại.

Quét mọi file git theo dõi, TRỪ lịch sử (`CHANGELOG.md`) — lịch sử kể lại đúng chuyện đã
xảy ra, sửa nó là viết lại quá khứ. Chỗ nào thật sự cần literal thì thêm vào `CHO_PHEP`
kèm LÝ DO; không có lý do thì không được thêm.
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEN_FILE_NAY = Path(__file__).resolve().relative_to(ROOT).as_posix()

# `~/Code/…`, `$HOME/Code/…`, `…Code/agent-…`, và hai cách ghép né literal đã từng dùng:
# `Join-Path $HOME (Join-Path 'Code' …)` (PowerShell) và `Path.home() / "Code"` (Python).
CAM = re.compile(r"""~[/\\]Code\b|\$HOME[/\\]Code\b|\bCode[/\\]agent-"""
                 r"""|Join-Path\s+['"]Code['"]|/\s*['"]Code['"]""")

# {đường tương đối: lý do}. Mỗi mục phải nói vì sao literal ở đó KHÔNG phải một giả định.
CHO_PHEP: dict[str, str] = {
    "knowledge/toolchains/NEWS_PIPELINE.md":
        "bài học về chuỗi Python không-thô (`'…\\agent-…'` → ký tự BEL): literal là VÍ DỤ "
        "của lỗi escape, không phải đường ai đọc",
    "scripts/runners/install_launchd.py":
        "docstring của `render`: ví dụ một tên thư mục có ký tự XML (`&`) để giải thích vì sao "
        "phải thoát XML — không phải đường mã đọc",
    "tests/test_launchd_templates.py":
        "dữ liệu GIẢ điền chỗ trống mẫu plist (`__REPO__`, `__HOME__`) để kiểm render/thoát "
        "XML — không phải đường mã đọc",
    "tests/test_run_args.py":
        "mồi nhử: dựng repo ở `<nhà giả>/Code/agent-marketing-studio` (đường lùi cũ) để "
        "CHỨNG MINH run.ps1 không còn dùng nó",
}

BO_QUA = {"CHANGELOG.md"}        # lịch sử — không viết lại


def _file_theo_doi() -> list[str]:
    r = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True)
    if r.returncode == 0 and r.stdout:
        return [x for x in r.stdout.decode("utf-8", "replace").split("\0") if x]
    # Không có git (bản tải zip): quét cây, bỏ thư mục không thuộc repo.
    bo = {".git", ".venv", "workspace", "node_modules", "__pycache__", ".tmp"}
    return [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*")
            if p.is_file() and not (bo & set(p.relative_to(ROOT).parts))]


def test_quet_duoc_file():
    """Danh sách rỗng thì cổng dưới xanh mà không đo gì."""
    ds = _file_theo_doi()
    assert "scripts/lib/studio_paths.py" in ds and len(ds) > 100, len(ds)


def test_mau_cam_bat_dung_cac_kieu_da_gap():
    for mau in ("~/Code/agent-marketing-studio", "$HOME/Code/news",
                "Join-Path $HOME (Join-Path 'Code' 'agent-marketing-studio')",
                'Path.home() / "Code"', r"D:\du-an\Code\agent-voice-studio"):
        assert CAM.search(mau), mau
    for sach in ("<thư mục cha chứa các repo>/agent-voice-studio", "`Code`, `Repo`",
                 "CodeQL/agent", "src/code/agent-x"):
        assert not CAM.search(sach), sach


def test_KHONG_con_literal_thu_muc_cha_cua_may_nao():
    sai = []
    for ten in _file_theo_doi():
        if ten in BO_QUA or ten in CHO_PHEP or ten == TEN_FILE_NAY:
            continue
        p = ROOT / ten
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue                         # nhị phân (ảnh, font) — không phải mã
        for i, dong in enumerate(text.splitlines(), 1):
            if CAM.search(dong):
                sai.append(f"{ten}:{i}: {dong.strip()[:120]}")
    assert not sai, ("literal giả định thư mục chứa repo (dùng thư mục cha của bản clone — "
                     "studio_paths.repo_anh_em / duong_repo_web — hoặc thêm vào CHO_PHEP "
                     "kèm lý do):\n  " + "\n  ".join(sai))


def test_CHO_PHEP_nao_cung_co_ly_do_va_file_con_ton_tai():
    for ten, ly_do in CHO_PHEP.items():
        assert len(ly_do.strip()) >= 20, f"{ten}: lý do quá ngắn"
        assert (ROOT / ten).is_file(), f"{ten}: không còn — gỡ khỏi CHO_PHEP"
