# run-blog-campaign.ps1 — VỎ MỎNG cho Task Scheduler. Logic thật nằm ở campaign_step.py.
#
# Vì sao mỏng: bước `dung-bai` phải đọc bảng Content trong Markdown để biết bài nào tới
# hạn. PowerShell 5.1 không đọc nổi YAML/Markdown có cấu trúc — đó chính là lý do
# `campaign_cfg.py` ra đời. Viết lại bộ đọc bảng bằng PowerShell là đi ngược một bài học
# đã trả giá. PowerShell chỉ giữ vai nó làm tốt: mặt tiền cho Task Scheduler và
# notify-run.ps1.
#
# Ba bước RỜI, mỗi lượt chạy đúng một bước:
#   dung-bai ──[ Cổng 1 ]── soan ──[ Cổng 2 ]── dang
# Gộp lại là dựng lại đúng cái đã bị gỡ 04/09/2026 vì nuốt cổng duyệt của người.
#
#   .\run.ps1 -Buoc dung-bai              dựng bài tới hạn rồi xin duyệt Cổng 1
#   .\run.ps1 -Buoc soan                  soạn bài đã qua Cổng 1 rồi xin duyệt Cổng 2
#   .\run.ps1 -Buoc dang                  đăng bài đã qua Cổng 2
#   .\run.ps1 -Buoc dang -Uat             đăng thử: web ra thư mục nháp, không đụng repo
param(
  [ValidateSet('dung-bai', 'soan', 'dang')][string]$Buoc = 'dung-bai',
  [string]$Config = '',
  [int]$Truoc = -1,
  [switch]$Uat,
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false } catch {}
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'

# Thư mục chiến dịch suy từ đường dẫn BẢN CHỤP: `run.ps1` luôn ghi nó vào
# `<chiến dịch>/logs/config-<ngày>.json`. Suy từ đó thay vì nhận thêm một tham số nữa —
# một nguồn sự thật, và không có cách nào truyền lệch hai giá trị cho nhau.
if (-not $Config) {
  Write-Host 'run-blog-campaign: thieu -Config (ban chup do campaign_cfg.py sinh).'
  exit 2
}
if (-not (Test-Path $Config)) {
  Write-Host ("run-blog-campaign: khong thay ban chup: " + $Config)
  exit 2
}
$cam = Split-Path (Split-Path $Config -Parent) -Parent
if (-not (Test-Path (Join-Path $cam 'campaign.md'))) {
  Write-Host ("run-blog-campaign: " + $cam + " khong phai thu muc chien dich (thieu campaign.md).")
  exit 2
}

$cfg = Get-Content $Config -Raw -Encoding UTF8 | ConvertFrom-Json

# `autonomy` đi theo bản chụp vì PowerShell không đọc được channel.yml. In ra để lượt chạy
# nền để lại dấu vết: đọc log là biết ngay lượt đó có dừng ở cổng hay không.
$muc = if ($cfg.autonomy) { [string]$cfg.autonomy } else { 'suggest' }
Write-Host ("=== " + $Buoc + " · " + (Split-Path $cam -Leaf) + " · autonomy=" + $muc + " ===")
if ($muc -ne 'full') {
  Write-Host 'che do SUGGEST: buoc nay se DUNG o cong va gui Telegram xin duyet.'
} else {
  Write-Host 'che do FULL: hai cong tu mo, KHONG hoi nguoi.'
}

$py = Join-Path $PSScriptRoot (Join-Path '..' (Join-Path 'pipeline' 'campaign_step.py'))
if (-not (Test-Path $py)) {
  Write-Host ("run-blog-campaign: khong thay " + $py)
  exit 2
}

$argv = @($cam, $Buoc)
if ($Truoc -ge 0) { $argv += @('--truoc', [string]$Truoc) }
if ($Uat)         { $argv += '--uat' }
if ($DryRun)      { $argv += '--dry-run' }

& python $py @argv
exit $LASTEXITCODE
