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
# Exit: mã của daily_truyen.py (0 ok · khác 0 = hỏng, bộ lập lịch thấy đúng mã).
param(
  [string]$Campaign = '',
  [string]$State = '',
  # Bản chụp cấu hình do `campaign_cfg.py` sinh (run.ps1 luôn truyền).
  [string]$Config = ''
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
Write-Output ('[truyen] chien dich ' + $Campaign + ' · state ' + (Split-Path $State -Leaf) + ' · python ' + $py)
& $py -u $daily --state $State
exit $LASTEXITCODE
