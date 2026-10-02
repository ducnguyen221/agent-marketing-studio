# run-weekly-cleanup.ps1 — job dọn dung lượng hằng tuần (vỏ của `weekly_cleanup.py`).
#
# Dời media đã đăng + quá 14 ngày sang `<trạm>/_trash/<ngày>` (prune_media, theo BẰNG CHỨNG đã
# đăng), đổ `_trash` cũ hơn 30 ngày, xoay vòng log (60 ngày, cắt file > 5 MB), báo dung lượng.
# Chi tiết + vì sao: docstring của `weekly_cleanup.py`, `docs/RETENTION.md` §7.
#
#   run-weekly-cleanup.ps1 -DryRun     # chỉ in — không chạm một byte (nghiệm thu chạy cái này trước)
#   run-weekly-cleanup.ps1             # làm thật (lịch gọi thế này)
#   run-weekly-cleanup.ps1 -Register   # (chỉ Windows) task Chủ nhật -Time, QUA wrapper NOTIFY_RUN
#
# macOS: `install_launchd.py --only studio.marketing.weekly-cleanup` — job này KHÔNG nằm trong
# `--all`, phải gọi đích danh. Windows cũng vậy: chỉ có task khi ai đó gõ -Register.
# Exit: mã của weekly_cleanup.py (0 ổn · 1 có bước hỏng · 2 cầu dao/tham số · 3 chưa có trạm).
param(
  [switch]$DryRun,
  [switch]$Register,
  [string]$TaskName = 'Marketing Weekly Cleanup',
  [string]$Time = '04:00'
)

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false } catch {}
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'

$engine = $PSScriptRoot
. (Join-Path $engine 'brand-paths.ps1')

# -Register: task Chủ nhật, QUA wrapper báo cáo (NOTIFY_RUN — luật E2 của máy chạy lịch). Ngoài
# giờ các job khác: tin 18:00–21:00, repo tuần CN 20:00, truyện từ 00:00/03:00 (~6–9 h).
if ($Register) {
  if ($env:OS -ne 'Windows_NT') { Write-Output '-Register chi co tren Windows. macOS: scripts/runners/install_launchd.py --only studio.marketing.weekly-cleanup'; exit 2 }
  $notify = Get-EnvVar 'NOTIFY_RUN'
  if (-not ($notify -and (Test-Path -LiteralPath $notify))) { Write-Output '-Register: dat NOTIFY_RUN = duong toi wrapper bao cao cua Task Scheduler.'; exit 2 }
  $self = Join-Path $engine 'run-weekly-cleanup.ps1'
  $argStr = "-NoProfile -ExecutionPolicy Bypass -File `"$notify`" -Title `"$TaskName`" -Script `"$self`" -ScriptArgs `"`""
  # Trình PowerShell ĐANG chạy file này — không viết cứng tên chương trình.
  $act = New-ScheduledTaskAction -Execute ((Get-Process -Id $PID).Path) -Argument $argStr
  $trg = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $Time
  $set = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1) -MultipleInstances IgnoreNew
  Register-ScheduledTask -TaskName $TaskName -Action $act -Trigger $trg -Settings $set `
    -Description 'Don dung luong hang tuan: doi media da dang sang _trash, do _trash cu, xoay vong log, bao dung luong. Qua NOTIFY_RUN (Telegram).' -Force | Out-Null
  Write-Output ("Registered '" + $TaskName + "' Chu nhat " + $Time + ", notify-run wrapped.")
  exit 0
}

$py = Find-Python -Repo $script:RepoRoot
if (-not $py) { Write-Output '[don] LOI: khong thay Python 3.10+ cua repo.'; exit 3 }
$doiSo = @((Join-Path $engine 'weekly_cleanup.py'))
if ($DryRun) { $doiSo += '--dry-run' }
Write-Output ('=== Weekly cleanup ' + $(if ($DryRun) { '(dry-run) ' } else { '' }) + 'start ===')
& $py -u @doiSo 2>&1 | ForEach-Object { $s = Format-NativeLine $_; if ($null -ne $s) { Write-Output $s } }
$code = $LASTEXITCODE
Write-Output ('=== Weekly cleanup ' + $(if ($code -eq 0) { 'complete' } else { 'failed' }) + ' ===')
exit $code
