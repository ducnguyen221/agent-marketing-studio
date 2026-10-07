# run-calendar-pipeline.ps1 — Vo mong cho Task Scheduler va Terminal goi calendar_pipeline.py.
#
# Chay Auto Pipeline by Calendar theo 2 pha:
#   Pha 1: Doi soat bai do dang (comment + group share)
#   Pha 2: Thuc thi theo lich (due_today, overdue_recoverable, chan stale_overdue)
param(
  [string]$Campaign = '',
  [string]$Date = '',
  [int]$Lookback = 3,
  [int]$MaxPosts = 3,
  [string]$ShareToGroup = '',
  [string]$Station = '',
  [switch]$DryRun,
  [switch]$Json
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false } catch {}
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'

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

$goc = Split-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) -Parent
$py = Find-Python -Repo $goc
if (-not $py) { exit 2 }

if (-not $Campaign) {
  Write-Host 'run-calendar-pipeline: thieu -Campaign (duong dan thu muc chien dich).'
  exit 2
}

$calPy = Join-Path (Join-Path $goc 'scripts') 'pipeline'
$calPy = Join-Path $calPy 'calendar_pipeline.py'
if (-not (Test-Path $calPy)) {
  Write-Host ('run-calendar-pipeline: khong thay file: ' + $calPy)
  exit 2
}

$cmdArgs = @($calPy, $Campaign)
if ($Date) { $cmdArgs += @('--date', $Date) }
if ($Lookback -ge 0) { $cmdArgs += @('--lookback', [string]$Lookback) }
if ($MaxPosts -gt 0) { $cmdArgs += @('--max-posts', [string]$MaxPosts) }
if ($ShareToGroup) { $cmdArgs += @('--share-to-group', $ShareToGroup) }
if ($Station) { $cmdArgs += @('--station', $Station) }
if ($DryRun) { $cmdArgs += '--dry-run' }
if ($Json) { $cmdArgs += '--json' }

& $py @cmdArgs
exit $LASTEXITCODE
