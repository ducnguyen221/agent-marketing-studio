<#
.SYNOPSIS
    Gỡ phần bộ cài agent-marketing-studio sở hữu — GIỮ trạm nội dung, .env và repo.

.DESCRIPTION
    Vỏ mỏng: tìm Python rồi gọi `scripts/pipeline/studio.py uninstall`. Mọi quyết định gỡ
    cái gì, giữ cái gì nằm ở lõi Python, một chỗ, dùng chung với `uninstall.sh`.

    Gỡ   : <repo>/studio.local.json · hook pre-commit do bộ cài đặt
    Giữ  : trạm nội dung (workspace/ hoặc thư mục ngoài) · <repo>/.env · mọi file của repo

.EXAMPLE
    .\uninstall.ps1 -DryRun     # xem trước, chưa gỡ gì
    .\uninstall.ps1             # gỡ

.NOTES
    File này phải giữ BOM UTF-8 để PowerShell 5.1 đọc đúng tiếng Việt.
    PowerShell 5.1 không có '&&' và toán tử ba ngôi — đừng thêm vào.
#>
[CmdletBinding()]
param(
    [switch] $DryRun,
    [switch] $Json
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

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

$py = Find-Python -Repo $RepoRoot
if (-not $py) {
    Write-Host "Khong tim thay Python 3.10+ (hoac dat MARKETING_STUDIO_PY)." -ForegroundColor Red
    exit 1
}
$studio = Join-Path (Join-Path (Join-Path $RepoRoot 'scripts') 'pipeline') 'studio.py'
$doi = @('uninstall')
if ($DryRun) { $doi += '--dry-run' }
if ($Json) { $doi += '--json' }
# Log cho nguoi doc di ra stderr; ha ErrorActionPreference quanh DUNG loi goi de PS 5.1
# khong boc dong stderr dau tien thanh loi ket thuc (cung ly do voi install.ps1).
$eapCu = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $py $studio @doi
$ma = $LASTEXITCODE
$ErrorActionPreference = $eapCu
exit $ma
