# run-approve-poller.ps1 — chiều NHẬN của cổng duyệt Telegram.
#
# ## Vì sao KHÔNG đi qua notify-run.ps1
#
# `notify-run.ps1` bọc mọi scheduled task và báo Telegram MỖI LƯỢT. Cái đó đúng cho việc
# chạy thưa (bản tin ngày, video tuần). Poller này chạy gần như liên tục — báo mỗi lượt là
# hàng nghìn tin một ngày, và tin báo mà nhiều tới mức đó thì không ai đọc nữa, tức là mất
# luôn tác dụng cảnh báo cho MỌI task khác. (Đức chốt 10/09/2026.)
#
# Đổi lại, nó tự có cách chứng minh còn sống: mỗi lượt `getUpdates` THÀNH CÔNG ghi một nhịp
# vào `logs/tg-poll-alive.json`. `approve_bus.py poller-status` đọc nhịp đó và nói sống/chết.
#
# ## Vì sao SỐNG CÓ HẠN rồi thoát, thay vì chạy mãi
#
# Telegram chặn long-poll ở ~50 giây (ĐO ĐƯỢC 10/09/2026, xin 100s vẫn trả về sau 50,7s),
# nên phủ liên tục thì phải nối nhiều lượt trong một tiến trình. Nhưng tiến trình sống mãi
# là một thứ phải trông, và chết câm thì kẹt cổng duyệt.
#
# Cách dùng: Task Scheduler gọi MỖI PHÚT với `MultipleInstances = IgnoreNew`.
#   · Đang chạy  -> Windows bỏ qua lượt gọi mới, tiến trình cũ tiếp tục.
#   · Đã chết    -> phút sau dựng lại.
#   · Sống đủ lâu-> tự thoát, để lượt sau bắt đầu sạch.
# Phủ gần 100%, và tự lành trong vòng 60 giây. Không service nào phải trông.
param(
  [Parameter(Mandatory = $true)][string]$Campaign,
  [int]$AliveSeconds = 3300               # ~55 phút rồi thoát
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

if (-not (Test-Path (Join-Path $Campaign 'campaign.md'))) {
  Write-Host ("run-approve-poller: " + $Campaign + " khong phai thu muc chien dich.")
  exit 2
}

$py = Join-Path $PSScriptRoot (Join-Path '..' (Join-Path 'pipeline' 'approve_bus.py'))

# GHI LOG RA FILE, bắt buộc. Task Scheduler gọi với `-WindowStyle Hidden` nên mọi thứ
# Write-Host/stderr in ra là BIẾN MẤT: task báo "Running" mà không ai biết nó đang làm gì
# hay đang lỗi vòng quanh. Đã mù đúng 10 phút vì chuyện này ngày 10/09/2026 — poller báo
# Running trong khi mọi chu kỳ đều trả `Conflict`, và không có một dòng nào để đọc.
#
# Poller này KHÔNG đi qua `notify-run.ps1` (chạy liên tục, báo mỗi lượt là spam), nên file
# log này là ĐƯỜNG DUY NHẤT để biết nó sống thế nào. Không có nó thì "không qua notify-run"
# biến thành "không quan sát được".
$logDir = Join-Path $Campaign 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ('tg-poller-' + (Get-Date -Format 'yyyy-MM-dd') + '.log')

function Ghi($m) {
  $d = (Get-Date -Format 'HH:mm:ss') + '  ' + $m
  [IO.File]::AppendAllText($log, $d + "`r`n", (New-Object System.Text.UTF8Encoding $false))
  Write-Host $m
}

Ghi ("=== poller cong duyet · " + (Split-Path $Campaign -Leaf) + " · song " + $AliveSeconds + "s ===")
$python = Find-Python -Repo (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
if (-not $python) {
  Ghi '=== DUNG: khong tim thay Python 3.10+ (xem dong Find-Python o tren), ma 2 ==='
  exit 2
}
# `2>&1` voi lenh ngoai duoi `Stop`: PowerShell 5.1 boc moi dong stderr thanh
# NativeCommandError, va dong DAU TIEN da la loi ket thuc -> runner chet exit 1 truoc
# khi kip ghi log (do 20/09/2026). Ha ve `Continue` DUNG quanh loi goi; "$_" doi dong
# stderr ve chu thuong; ket qua that doc tu $LASTEXITCODE. Test: tests/test_runner_stderr.py
$ErrorActionPreference = 'Continue'
& $python $py receive --campaign $Campaign --follow $AliveSeconds 2>&1 | ForEach-Object { Ghi ("  " + "$_") }
$ma = $LASTEXITCODE
$ErrorActionPreference = 'Stop'
Ghi ("=== thoat, ma " + $ma + " ===")
exit $ma
