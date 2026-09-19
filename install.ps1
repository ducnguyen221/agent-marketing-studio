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
    .\install.ps1                              # hoi ban chon che do cai
    .\install.ps1 -Yes                         # nhan khuyen nghi: embedded
    .\install.ps1 -Station "D:/noi-dung"       # tram ngoai repo, khong hoi
    .\install.ps1 -NonInteractive              # khong co ai tra loi -> embedded

.NOTES
    File này phải giữ BOM UTF-8 để PowerShell 5.1 đọc đúng tiếng Việt.
    PowerShell 5.1 không có '&&' và toán tử ba ngôi — đừng thêm vào.
#>
[CmdletBinding()]
param(
    [string] $Station,
    [ValidateSet('embedded', 'separate')]
    [string] $Mode,
    [switch] $Yes,
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
    # Chuyen huong luong loi cua LENH NGOAI duoi `Stop`: PS 5.1 boc tung dong stderr thanh
    # NativeCommandError, va dong DAU TIEN da la loi ket thuc. Mot Python CHAY DUOC nhung
    # in canh bao luc khoi dong (wrapper .cmd, shim pyenv/conda, mot .pth in ra) bi loai
    # OAN -> exit 2; pwsh 7 thi khong -> cung mot file, hai hanh vi (review P1, N1).
    # Ha ve `Continue` trong chinh scriptblock nay: goi bang `&` nen bien la CUC BO, khong
    # ro ri ra ngoai. Ket qua that van doc tu $LASTEXITCODE — noi loi la te hon chet.
    # Test: tests/test_find_python.py
    $ErrorActionPreference = 'Continue'
    try {
      $ra = @(& $exe -c 'import sys;print(sys.version_info[:2])' 2>$null)
      if ($LASTEXITCODE -ne 0) { return $false }
      # Dong CUOI chu khong phai ca stdout: `[string](@(...))` noi moi dong bang dau cach,
      # nen mot loi chao in truoc dong phien ban lam regex neo truot.
      $v = ''
      foreach ($d in $ra) { $t = ([string]$d).Trim(); if ($t) { $v = $t } }
      $m = [regex]::Match($v, '^\((\d+), (\d+)\)$')
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

# ── 2. Dựng trạm — mọi quyết định nằm ở init_station.py ──────────────────────
# Vỏ này CỐ TÌNH không tự hỏi chỗ đặt trạm nữa: `install.sh` (macOS/Linux) phải hỏi y hệt,
# và hai vỏ hỏi riêng thì sớm muộn chúng trôi khỏi nhau. Lõi Python là chỗ duy nhất biết
# hai chế độ cài, biết nhận diện máy đã có trạm, và biết dừng khi không có ai trả lời.
$init = Join-Path (Join-Path (Join-Path $RepoRoot 'scripts') 'pipeline') 'init_station.py'
$doi = @()
if ($Station) { $doi += @('--station', $Station) }
if ($Mode) { $doi += @('--mode', $Mode) }
# -NonInteractive = "không có ai ngồi đây": nhận khuyến nghị (embedded). Máy đã có trạm
# ngoài thì lõi vẫn tự chọn separate và bỏ qua cờ này — đó là chủ đích (F17.2).
if ($NonInteractive -or $Yes) { $doi += '--yes' }

Say ""
# Ha ErrorActionPreference quanh DUNG loi goi: init_station.py in moi log cho nguoi doc ra
# stderr (hop dong ba tram giu stdout sach cho dong JSON). Duoi `Stop`, neu ai do chay
# `install.ps1 2>&1 | …` thi PS 5.1 boc dong stderr DAU TIEN thanh NativeCommandError va
# giet bo cai giua chung — khi do "cai hong" va "cai xong co log" trong y het nhau.
$eapCu = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $py $init @doi
$ma = $LASTEXITCODE
$ErrorActionPreference = $eapCu
if ($ma -ne 0) {
    Say ""
    Say ("Bo cai dung o ma {0}. 2 = can sua cau hinh (hoac can ban chon che do); 3 = con thieu buoc cai." -f $ma) Yellow
}
exit $ma
