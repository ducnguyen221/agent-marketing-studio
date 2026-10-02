# run-daily-truyen.ps1 — runner lượt truyện hằng ngày (đọc chương -> dựng video -> đăng).
#
# Một runner cho MỌI phần truyện: phần nào khác nhau (nguồn, dải chương, playlist, tiền tố
# tiêu đề) nằm trong `truyen-state.json` CỦA CHIẾN DỊCH, không nằm ở đây.
#
#   campaign.md:  runtime.runner: run-daily-truyen.ps1     (run.ps1 tìm thấy nó trong repo)
#   chạy tay:     run-daily-truyen.ps1 -Campaign <thư mục chiến dịch>
#
# Thư mục chiến dịch: -Campaign -> suy từ bản chụp -Config (nằm ở `<chiến dịch>/logs/`).
# State: -State -> `<chiến dịch>/truyen-state.json`.
# Mã engine truyện: `story/daily_truyen.py` cạnh file này (repo) — không còn chép vào trạm.
# Python: python của TRẠM GIỌNG (Find-OmniVoicePython trong brand-paths.ps1) — venv có torch.
# Con trỏ bí mật riêng kênh truyện: YT_TOKEN_PATH__NGHE_TIEN_TRUYEN; YT_CLIENT_SECRET__NGHE_TIEN_TRUYEN
# (nếu khai) thay YT_CLIENT_SECRET cho riêng lượt này. Cả hai đọc qua Get-EnvVar
# (tiến trình -> registry User trên Windows -> <repo>/.env chế độ embedded).
# Exit: mã của daily_truyen.py (0 ok · khác 0 = hỏng, bộ lập lịch thấy đúng mã) — 124 = quá trần
# kể cả sau lượt chạy tiếp.
#
# Trần giờ + chạy tiếp (P1-23): daily_truyen.py chạy QUA `story/resume_once.py`. Lượt đầu trần
# -Budget giây; quá trần mà `<trạm giọng>/omnivoice/truyen-out/_resume.json` còn dải dở thì tự chạy
# tiếp ĐÚNG MỘT LẦN (dùng cache chương, trần -ResumeBudget), báo ⏳ qua Telegram. Nằm ở runner chứ
# không ở wrapper báo cáo để launchd lẫn Task Scheduler chạy y hệt; trần của bộ lập lịch/wrapper
# ngoài phải ≥ Budget + ResumeBudget + biên (plist `daily-story`: 42300 s; -Register tự tính).
#
#   -Register (chỉ Windows): tạo task Task Scheduler hằng ngày -Time, QUA wrapper NOTIFY_RUN, gọi
#             `<chiến dịch>/run.ps1` (thiếu thì gọi file này với -Campaign), ExecutionTimeLimit =
#             Budget + ResumeBudget + 1800 s. macOS: `install_launchd.py --only studio.marketing.daily-story`.
param(
  [string]$Campaign = '',
  [string]$State = '',
  # Bản chụp cấu hình do `campaign_cfg.py` sinh (run.ps1 luôn truyền).
  [string]$Config = '',
  # Cùng giá trị mặc định với story/resume_once.py (TRAN_DAU / TRAN_TIEP) — test giữ hai bên khớp.
  [int]$Budget = 30600,
  [int]$ResumeBudget = 10800,
  [switch]$Register,
  [string]$TaskName = '',
  [string]$Time = '03:00'
)

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false } catch {}
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
$env:HF_HUB_OFFLINE = '0'

$engine = $PSScriptRoot
. (Join-Path $engine 'brand-paths.ps1')

if (-not $Campaign -and $Config) { $Campaign = Split-Path (Split-Path $Config -Parent) -Parent }
if (-not $Campaign -or -not (Test-Path -LiteralPath $Campaign)) {
  Write-Output ('[truyen] LOI: khong xac dinh duoc thu muc chien dich (' + $Campaign + '). Truyen -Campaign hoac chay qua run.ps1.')
  exit 2
}
# -Register: task Task Scheduler QUA wrapper báo cáo (NOTIFY_RUN — luật E2 của máy chạy lịch).
if ($Register) {
  if ($env:OS -ne 'Windows_NT') { Write-Output '-Register chi co tren Windows. macOS: scripts/runners/install_launchd.py --only studio.marketing.daily-story'; exit 2 }
  $notify = Get-EnvVar 'NOTIFY_RUN'
  if (-not ($notify -and (Test-Path -LiteralPath $notify))) { Write-Output '-Register: dat NOTIFY_RUN = duong toi wrapper bao cao cua Task Scheduler.'; exit 2 }
  if (-not $TaskName) { $TaskName = 'Truyen ' + (Split-Path $Campaign -Leaf) }
  $runPs1 = Join-Path $Campaign 'run.ps1'
  if (Test-Path -LiteralPath $runPs1) { $target = $runPs1; $sargs = '' }
  else { $target = Join-Path $PSScriptRoot 'run-daily-truyen.ps1'; $sargs = '-Campaign \"' + $Campaign + '\"' }
  $argStr = "-NoProfile -ExecutionPolicy Bypass -File `"$notify`" -Title `"$TaskName`" -Script `"$target`" -ScriptArgs `"$sargs`""
  # Task cũ (tạo tay / bởi wrapper máy) trỏ CÙNG chiến dịch mà tên khác ⇒ hai task cùng giờ chạy
  # song song cùng dải (sweep_old của task này xoá _work của task kia), và task cũ giữ
  # ExecutionTimeLimit cũ (giết lượt chạy tiếp). Không tự gỡ task của người khác — nói ra.
  $leaf = Split-Path $Campaign -Leaf
  $trung = @(Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object {
      $_.TaskName -ne $TaskName -and (@($_.Actions | ForEach-Object { [string]$_.Arguments }) -join ' ') -match [regex]::Escape($leaf) })
  foreach ($x in $trung) {
    Write-Output ("WARN: task '" + $x.TaskPath + $x.TaskName + "' cung tro chien dich " + $leaf + " (trang thai " + $x.State + ", tran " + $x.Settings.ExecutionTimeLimit + ") - Disable/Unregister no, hoac dat -TaskName trung ten de ghi de.")
  }
  $limit = New-TimeSpan -Seconds ($Budget + $ResumeBudget + 1800)
  # Trình PowerShell ĐANG chạy file này — không viết cứng tên chương trình.
  $act = New-ScheduledTaskAction -Execute ((Get-Process -Id $PID).Path) -Argument $argStr
  $trg = New-ScheduledTaskTrigger -Daily -At $Time
  $set = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit $limit -MultipleInstances IgnoreNew
  Register-ScheduledTask -TaskName $TaskName -Action $act -Trigger $trg -Settings $set `
    -Description 'Luot truyen hang ngay (doc -> dung video -> dang); qua tran thi tu chay tiep 1 lan (resume_once.py). Qua NOTIFY_RUN (Telegram).' -Force | Out-Null
  Write-Output ("Registered '" + $TaskName + "' hang ngay " + $Time + ", ExecutionTimeLimit " + $limit + ", notify-run wrapped.")
  exit 0
}

if (-not $State) { $State = Join-Path $Campaign 'truyen-state.json' }
if (-not (Test-Path -LiteralPath $State -PathType Leaf)) {
  Write-Output ('[truyen] LOI: thieu state ' + $State)
  exit 2
}

try { $py = Find-OmniVoicePython } catch {
  Write-Output ('[truyen] LOI: ' + $_.Exception.Message)
  Write-Output '[truyen] Dat VOICE_STATION (goc tram giong, vd <repo agent-voice-studio>/workspace) hoac OMNIVOICE_PY.'
  exit 1
}

# Con trỏ bí mật riêng kênh truyện -> môi trường tiến trình con (Python không đọc registry
# hay `.env` của repo). Chỉ nhận giá trị có hình dạng ĐƯỜNG DẪN — không bao giờ in giá trị.
$tok = Get-EnvVar 'YT_TOKEN_PATH__NGHE_TIEN_TRUYEN'
if ($tok -and (Test-IsPathValue $tok)) { $env:YT_TOKEN_PATH__NGHE_TIEN_TRUYEN = (Resolve-Home $tok) }
$cli = Get-EnvVar 'YT_CLIENT_SECRET__NGHE_TIEN_TRUYEN'
if ($cli -and (Test-IsPathValue $cli)) { $env:YT_CLIENT_SECRET = (Resolve-Home $cli) }
else {
  $cli = Get-EnvVar 'YT_CLIENT_SECRET'
  if ($cli -and -not $env:YT_CLIENT_SECRET -and (Test-IsPathValue $cli)) { $env:YT_CLIENT_SECRET = (Resolve-Home $cli) }
}

$daily = Join-Path (Join-Path $engine 'story') 'daily_truyen.py'
$guard = Join-Path (Join-Path $engine 'story') 'resume_once.py'
Write-Output ('[truyen] chien dich ' + $Campaign + ' · state ' + (Split-Path $State -Leaf) + ' · python ' + $py +
              ' · tran ' + $Budget + 's (+ chay tiep 1 lan ' + $ResumeBudget + 's)')
& $py -u $guard --title ('Truyen · ' + (Split-Path $Campaign -Leaf)) --budget $Budget --resume-budget $ResumeBudget `
  -- $py -u $daily --state $State
exit $LASTEXITCODE
