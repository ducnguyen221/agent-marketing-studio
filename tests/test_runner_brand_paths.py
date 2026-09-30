# -*- coding: utf-8 -*-
"""`brand-paths.ps1` (PowerShell) và `studio_paths.py` (Python) phải phân giải CÙNG một bố cục ra
CÙNG một kết quả — chúng là hai bản của một luật (P1-14).

Dựng một thư mục cha giả chứa: bản clone marketing (chế độ embedded, `.env`, `workspace/`), repo
anh em `agent-voice-studio` (trạm `workspace/`) và `agent-video-studio` (trạm `station_path`
tương đối + `.venv`). Tên thư mục KHÔNG phải tên repo — nhận diện phải đi bằng `pyproject.toml`.
Không mạng, không trạm thật: HOME trỏ thư mục tạm, biến trạm bị gỡ khỏi tiến trình.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BP = ROOT / "scripts" / "runners" / "brand-paths.ps1"
PS = shutil.which("pwsh") or shutil.which("powershell")
BIEN = ("MARKETING_STUDIO_DATA", "MARKETING_STUDIO_HOME", "VOICE_STATION", "OMNIVOICE_DIR",
        "VIDEO_STATION", "VIDEO_ROOT", "OMNIVOICE_PY", "VOICE_BGM_DIR", "WEB_REPO_DIR",
        "L30_SCRIPT", "CLAUDE_CONFIG_DIR")

pytestmark = pytest.mark.skipif(not PS, reason="khong co PowerShell")


def _registry_co_bien() -> list[str]:
    """Máy Windows đã `setx` biến trạm ở cấp User: Get-EnvVar CỐ Ý đọc registry, nên bố cục giả
    không cô lập được trên máy đó. CI (không registry) chạy đủ."""
    if os.name != "nt":
        return []
    import winreg
    co = []
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            for n in BIEN:
                try:
                    if str(winreg.QueryValueEx(k, n)[0]).strip():
                        co.append(n)
                except OSError:
                    pass
    except OSError:
        pass
    return co


def _viet(p: Path, s: str = "") -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")
    return p


@pytest.fixture
def bo_cuc(tmp_path):
    cha = tmp_path / "noi-chua-repo"
    mkt = cha / "ban-marketing"                          # tên thư mục ≠ tên repo
    (mkt / "scripts" / "runners").mkdir(parents=True)
    shutil.copy2(BP, mkt / "scripts" / "runners" / "brand-paths.ps1")
    _viet(mkt / "scripts" / "pipeline" / "campaign_cfg.py")
    (mkt / "scripts" / "lib").mkdir(parents=True)
    _viet(mkt / "install.ps1")
    _viet(mkt / "pyproject.toml", '[project]\nname = "agent-marketing-studio"\n')
    _viet(mkt / "studio.local.json", '{"mode": "embedded"}')
    ws = mkt / "workspace"
    _viet(ws / "CHANNELS.md", "---\nchannels: []\n---\n")
    _viet(ws / "k" / "c" / "logs" / "config.json", "{}")
    bgm = tmp_path / "nhac"
    bgm.mkdir()
    _viet(mkt / ".env", f"VOICE_BGM_DIR={bgm}\nWEB_REPO_DIR={tmp_path / 'web'}\n")
    giong = cha / "giong-x"
    _viet(giong / "pyproject.toml", '[project]\nname = "agent-voice-studio"\n')
    (giong / "workspace").mkdir()
    video = cha / "video-y"
    _viet(video / "pyproject.toml", "[project]\nname = 'agent-video-studio'\n")
    _viet(video / "studio.local.json", '{"station_path": "tram-rieng"}')
    (video / "tram-rieng").mkdir()
    con = "Scripts" if os.name == "nt" else "bin"
    ten = "python.exe" if os.name == "nt" else "python3"
    vpy = _viet(video / ".venv" / con / ten)
    return {"cha": cha, "mkt": mkt, "ws": ws, "giong": giong, "video": video, "bgm": bgm,
            "vpy": vpy, "nha": tmp_path / "nha", "tmp": tmp_path}


def _chay(b, config: str = "") -> dict:
    lai = b["tmp"] / "lai.ps1"
    lai.write_text(
        "param([string]$Config = '')\n$ErrorActionPreference = 'Stop'\n"
        f". '{b['mkt'] / 'scripts' / 'runners' / 'brand-paths.ps1'}'\n"
        "$c = [pscustomobject]@{ repo = 'news/ai' }\n"
        "$c2 = [pscustomobject]@{ repo = '${WEB_REPO_DIR}/data' }\n"
        "$bj = Join-Path ([IO.Path]::GetTempPath()) ('bp-' + [guid]::NewGuid().ToString('N') + '.json')\n"
        "@{ repo = 'news/ai' } | ConvertTo-Json | Set-Content -Path $bj -Encoding UTF8\n"
        "$g = Get-Cfg -BrandDir (Split-Path $bj -Parent) -Config $bj\n"
        "@{ repo = '${WEB_REPO_DIR}/data' } | ConvertTo-Json | Set-Content -Path $bj -Encoding UTF8\n"
        "$g2 = Get-Cfg -BrandDir (Split-Path $bj -Parent) -Config $bj\n"
        "Remove-Item $bj -Force\n"
        "[pscustomobject]@{ station = $Station; repo = $script:RepoRoot; voice = $VoiceStation;"
        " video = $VideoStation; bgm = (Get-EnvVar 'VOICE_BGM_DIR'); ovpy = (Find-OmniVoicePython);"
        " web = $g.repo; web2 = $g2.repo } | ConvertTo-Json -Compress\n",
        encoding="utf-8-sig")
    env = {k: v for k, v in os.environ.items() if k not in BIEN}
    env.update(HOME=str(b["nha"]), USERPROFILE=str(b["nha"]))
    a = [PS, "-NoProfile", "-NonInteractive", "-File", str(lai)]
    if config:
        a += ["-Config", config]
    r = subprocess.run(a, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


def _cung(a, b) -> bool:
    return os.path.normcase(os.path.realpath(str(a))) == os.path.normcase(os.path.realpath(str(b)))


def test_PS_va_Python_phan_giai_CUNG_bo_cuc(bo_cuc, monkeypatch):
    co = _registry_co_bien()
    if co:
        pytest.skip(f"registry User có {co} — Get-EnvVar cố ý đọc nó; CI chạy đủ ca này")
    kq = _chay(bo_cuc, str(bo_cuc["ws"] / "k" / "c" / "logs" / "config.json"))
    assert _cung(kq["station"], bo_cuc["ws"]), kq
    assert _cung(kq["repo"], bo_cuc["mkt"]), kq
    assert _cung(kq["voice"], bo_cuc["giong"] / "workspace"), kq
    assert _cung(kq["video"], bo_cuc["video"] / "tram-rieng"), kq
    assert _cung(kq["bgm"], bo_cuc["bgm"]), "embedded: Get-EnvVar phải đọc <repo>/.env"
    assert _cung(kq["ovpy"], bo_cuc["vpy"]), "python giọng: .venv của repo anh em video"
    assert _cung(kq["web"], bo_cuc["cha"] / "news" / "ai"), "repo tương đối theo thư mục CHA"
    assert _cung(kq["web2"], bo_cuc["tmp"] / "web" / "data"), "${WEB_REPO_DIR} nở từ .env"

    # Cùng bố cục qua studio_paths (Python) — hai bản của MỘT luật.
    for n in BIEN:
        monkeypatch.delenv(n, raising=False)
    monkeypatch.setenv("MARKETING_STUDIO_HOME", str(bo_cuc["mkt"]))
    sys.path.insert(0, str(ROOT / "scripts" / "lib"))
    import studio_paths as SP
    assert _cung(SP.voice_station(), kq["voice"])
    assert _cung(SP.video_station(), kq["video"])
    assert _cung(SP.duong_repo_web("news/ai"), kq["web"])


def test_khong_Config_thi_tram_embedded_la_workspace(bo_cuc):
    if _registry_co_bien():
        pytest.skip("registry User có biến trạm — CI chạy đủ ca này")
    assert _cung(_chay(bo_cuc)["station"], bo_cuc["ws"])
