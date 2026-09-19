<#
.SYNOPSIS
    Dựng một TRẠM (station) agent-marketing-studio: hỏi chỗ đặt, tạo khung, chỉ bước tiếp.

.DESCRIPTION
    Repo này chỉ chứa engine: script, cổng kiểm, quy trình và template.
    Nội dung của bạn sống ở một TRẠM nằm ngoài git.

    Cấu trúc trạm:
        <trạm>/CHANNELS.md          sổ kênh — kênh nào ở đâu
        <trạm>/<kênh>/channel.yml   hồ sơ kênh: nền tảng, trụ nội dung, mức tự trị
        <trạm>/<kênh>/brand.md      nhận diện, giọng, chính kiến (NGƯỜI đọc)
        <trạm>/<kênh>/<chiến dịch>/campaign.md   brief + bảng danh sách bài
        <trạm>/<kênh>/<chiến dịch>/<bài>/        research.md · content.md · publish.json

    Markdown là NGUỒN SỰ THẬT. Excel chỉ là bản xuất (export_excel.py), đi một chiều.

    Script này CỐ TÌNH không tạo kênh hộ bạn: chỗ lưu kênh là quyết định của bạn, và
    new_channel.py sẽ hỏi. Nó chỉ dựng trạm rỗng rồi chỉ đúng lệnh tiếp theo.

.EXAMPLE
    .\install.ps1
    .\install.ps1 -Station "D:\noi-dung" -NonInteractive

.NOTES
    File này phải giữ BOM UTF-8 để PowerShell 5.1 đọc đúng tiếng Việt.
    PowerShell 5.1 không có '&&' và toán tử ba ngôi — đừng thêm vào.
#>
[CmdletBinding()]
param(
    [string] $Station,
    [switch] $NonInteractive
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Say($t, $c = 'Gray') { Write-Host $t -ForegroundColor $c }

function Find-Python {
  # CHÉP NGUYÊN giữa các .ps1 của repo (PS 5.1 không có module chung); cổng
  # tests/test_ps1_portable.py giữ mọi bản giống hệt nhau. Thứ tự dò:
  #   MARKETING_STUDIO_PY -> <repo>/.venv -> python -> python3 -> py
  # Mỗi ứng viên phải CHẠY được và tự khai là Python 3.10+: trên Windows `python3` có
  # thể là stub của Microsoft Store — Get-Command thấy, chạy thì hỏng.
  param([string]$Repo)
  $chay = {
    param([string]$exe)
    try {
      $v = [string](& $exe -c 'import sys;print(sys.version_info[:2])' 2>$null)
      if ($LASTEXITCODE -ne 0) { return $false }
      $m = [regex]::Match($v.Trim(), '^\((\d+), (\d+)\)$')
      return ($m.Success -and [int]$m.Groups[1].Value -eq 3 -and [int]$m.Groups[2].Value -ge 10)
    } catch { return $false }
  }
  if ($env:MARKETING_STUDIO_PY) {
    if (& $chay $env:MARKETING_STUDIO_PY) { return $env:MARKETING_STUDIO_PY }
    Write-Host ('Find-Python: MARKETING_STUDIO_PY=' + $env:MARKETING_STUDIO_PY + ' khong chay duoc Python 3.10+ -> DUNG.')
    return $null
  }
  $ung = @()
  if ($Repo) {
    foreach ($con in @('Scripts', 'bin')) {
      $thu = Join-Path (Join-Path $Repo '.venv') $con
      if (Test-Path $thu) {
        $ung += @(Get-ChildItem -Path $thu -Filter 'python*' -File -ErrorAction SilentlyContinue |
          Where-Object { $_.BaseName -eq 'python' -or $_.BaseName -eq 'python3' } |
          Sort-Object Name | ForEach-Object { $_.FullName })
      }
    }
  }
  $ung += @('python', 'python3', 'py')
  foreach ($u in $ung) {
    if (& $chay $u) { return $u }
  }
  Write-Host 'Find-Python: khong thay Python 3.10+ (MARKETING_STUDIO_PY, .venv, python, python3, py) -> DUNG.'
  return $null
}

Say ""
Say "=== agent-marketing-studio - dung tram noi dung ===" Green
Say ""

# ── 1. Python và phụ thuộc ───────────────────────────────────────────────────
# Kiểm TRƯỚC khi tạo thư mục: dựng xong khung rồi mới báo thiếu Python là bắt người
# dùng đi dọn một thứ họ chưa dùng được.
$py = Find-Python -Repo $RepoRoot
if (-not $py) {
    Say "Khong tim thay Python. Cai Python 3.10+ roi chay lai (hoac dat MARKETING_STUDIO_PY)." Red
    exit 1
}
$ver = & $py -c "import sys;print('%d.%d' % sys.version_info[:2])"
Say ("Python  : {0} ({1})" -f $ver, $py)

$thieu = & $py -c @"
import importlib.util as u
print(' '.join(n for m, n in (('yaml','pyyaml'),('openpyxl','openpyxl'),('requests','requests'))
               if u.find_spec(m) is None))
"@
if ($thieu.Trim()) {
    Say ("Thieu goi: {0}" -f $thieu.Trim()) Yellow
    Say "  Cai bang: pip install -r requirements.txt" Yellow
    Say ""
} else {
    Say "Phu thuoc: du"
}

# ── 2. Chỗ đặt trạm ──────────────────────────────────────────────────────────
$macDinh = Join-Path $HOME ".marketing"
if (-not $Station) {
    if ($NonInteractive) {
        $Station = $macDinh
    } else {
        Say ""
        Say "Dat TRAM o dau? (noi dung cua ban song o day, khong vao git)" Cyan
        Say ("  Enter = {0}" -f $macDinh)
        $tra = Read-Host "  Duong dan"
        if ([string]::IsNullOrWhiteSpace($tra)) { $Station = $macDinh } else { $Station = $tra }
    }
}
$Station = [System.IO.Path]::GetFullPath($Station)

if (Test-Path (Join-Path $Station "CHANNELS.md")) {
    Say ""
    Say ("Da co tram o {0} - khong ghi de." -f $Station) Yellow
} else {
    New-Item -ItemType Directory -Force -Path $Station | Out-Null
    Copy-Item (Join-Path $RepoRoot (Join-Path "templates" (Join-Path "station" "CHANNELS.md"))) (Join-Path $Station "CHANNELS.md")
    Say ""
    Say ("Tram    : {0}" -f $Station) Green
}

# ── 3. Bước tiếp theo ────────────────────────────────────────────────────────
# In ra lệnh THẬT, chạy dán được. Hướng dẫn mà phải sửa mới chạy là hướng dẫn hỏng.
Say ""
Say "Buoc tiep theo:" Cyan
Say ""
Say ("  # 1. Tao kenh dau tien (--path la BAT BUOC: cho luu la quyet dinh cua ban)")
# Đường trong lệnh in bằng `/`: Python nhận `/` trên cả Windows lẫn macOS, còn `\` thì
# macOS coi là một ký tự trong tên file. Python in đúng cái Find-Python vừa tìm ra; là
# đường đầy đủ (vd .venv) thì phải có `&` mới chạy được trong PowerShell.
if ($py -match '[\\/]') { $pyTen = '& "' + $py + '"' } else { $pyTen = $py }
Say ("  {0} scripts/pipeline/new_channel.py --id ten-kenh --label ""Ten kenh"" ``" -f $pyTen)
Say ("      --path ""{0}"" --station ""{1}""" -f (Join-Path $Station "ten-kenh"), $Station)
Say ""
Say ("  # 2. Tao chien dich")
Say ("  {0} scripts/pipeline/new_campaign.py --channel ten-kenh --id CMP-2609-abc ``" -f $pyTen)
Say ("      --name ""Ten chien dich"" --prefix ABC --station ""{0}""" -f $Station)
Say ""
Say ("  # 3. Dien du campaign.md, roi tao bai (buoc nay CHAN neu campaign.md con chu mau)")
Say ("  {0} scripts/pipeline/new_post.py --campaign CMP-2609-abc --id ABC-001 ``" -f $pyTen)
Say ("      --slug bai-dau-tien --title ""Tieu de"" --station ""{0}""" -f $Station)
Say ""
Say ("  # Xem truoc mot tram da dien san:")
Say ("  {0} scripts/pipeline/check_tree.py --station ./examples" -f $pyTen)
Say ("  (roi mo examples/index.html bang cach bam dup)")
Say ""
