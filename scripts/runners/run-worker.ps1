# run-worker.ps1 — THỢ: nhặt MỘT việc khỏi hàng chờ, làm, rồi thoát.
#
# ## Vì sao một việc rồi thoát, không phải vòng lặp
#
# Task Scheduler gọi mỗi phút với `MultipleInstances = IgnoreNew`. Thợ chạy 10 phút thì 10
# lượt gọi kế tiếp bị Windows chặn — ĐÓ CHÍNH LÀ giới hạn một-agent-một-lúc, và nó đến từ
# hệ điều hành chứ không từ code ta tự viết.
#
# Duyệt cả lô 10 bài thì 10 việc xếp hàng, không phải 10 agent cùng sống. Ngày 11/09/2026
# đúng chỗ này đã thành 335 tiến trình và 16,4 GB RAM, và máy sập.
#
# Hàng rỗng thì thoát ngay và êm — đường chạy bình thường, không phải lỗi.
#
# ## Vì sao KHÔNG đi qua notify-run.ps1
#
# Cùng lý do với poller: gọi mỗi phút mà báo Telegram mỗi lượt là hàng nghìn tin một ngày.
# Thợ tự báo khi CÓ CHUYỆN (xong bước, chạm trần, hỏng hẳn), còn lượt rỗng thì im lặng.
param(
  [Parameter(Mandatory = $true)][string]$Campaign
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

if (-not (Test-Path (Join-Path $Campaign 'campaign.md'))) {
  Write-Host ("run-worker: " + $Campaign + " khong phai thu muc chien dich.")
  exit 2
}

$py = Join-Path $PSScriptRoot (Join-Path '..' (Join-Path 'pipeline' 'worker.py'))

# Ghi log ra file: task chay `-WindowStyle Hidden` nen moi thu in ra la BIEN MAT.
$logDir = Join-Path $Campaign 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ('tho-viec-' + (Get-Date -Format 'yyyy-MM-dd') + '.log')

function Ghi($m) {
  $d = (Get-Date -Format 'HH:mm:ss') + '  ' + $m
  [IO.File]::AppendAllText($log, $d + "`r`n", (New-Object System.Text.UTF8Encoding $false))
  Write-Host $m
}

$python = Find-Python -Repo (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
if (-not $python) {
  Ghi '=== tho DUNG: khong tim thay Python 3.10+ (xem dong Find-Python o tren), ma 2 ==='
  exit 2
}

$ra = & $python $py $Campaign 2>&1
$ma = $LASTEXITCODE

# Luot RONG thi KHONG ghi log — moi phut mot dong "hang rong" la 1.440 dong/ngay rac.
if ($ra -notmatch 'hang rong|hàng rỗng') {
  foreach ($d in $ra) { Ghi ("  " + $d) }
  Ghi ("=== tho thoat, ma " + $ma + " ===")
}
exit $ma
