# run.ps1 — điểm vào DUY NHẤT của chiến dịch này.
#
# Mọi thứ khác biệt giữa các chiến dịch nằm trong `campaign.md`, KHÔNG nằm ở đây. Vì vậy
# file này GIỐNG HỆT NHAU ở mọi chiến dịch — chép sang chiến dịch mới là chạy được ngay,
# và nó cũng chính là bản mẫu trong `agent-marketing-studio/templates/station/_channel/_campaign/run.ps1`.
#
# Ba bước: đọc campaign.md -> ghi bản chụp JSON -> gọi engine với -Config.
# Không truyền -Config thì engine chạy y như trước (đọc brand.json); bản chụp đã được
# `.tmp/doi-chieu-config.ps1` chứng minh tương đương trên đúng bộ khoá từng runner đọc.
#
#   .\run.ps1                                  chạy thật
#   .\run.ps1 -Uat                             UAT: không upload YouTube, Facebook dry-run
#   .\run.ps1 -Date 2026-09-01 -SkipResearch   tái dùng JSON cũ, chỉ render lại
#
# Tham số thừa được truyền THẲNG xuống runner qua $args, không diễn giải lại ở đây.

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false } catch {}

$cam    = $PSScriptRoot
$engine = Join-Path $env:USERPROFILE (Join-Path '.news' 'engine')
$cfgpy  = Join-Path $env:USERPROFILE (Join-Path 'Code' (Join-Path 'agent-marketing-studio' (Join-Path 'scripts' (Join-Path 'pipeline' 'campaign_cfg.py'))))
$logs   = Join-Path $cam 'logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null

# Bản chụp sinh LẠI mỗi lượt -> sửa campaign.md xong chạy lại là ăn ngay, không cache.
# Đây là NHẬT KÝ, không phải nguồn: đừng sửa tay, lượt sau ghi đè.
$snap = Join-Path $logs ('config-' + (Get-Date -Format 'yyyy-MM-dd') + '.json')
$env:PYTHONIOENCODING = 'utf-8'
& python $cfgpy --campaign $cam --out $snap
if ($LASTEXITCODE -ne 0) {
  Write-Host 'run.ps1: campaign_cfg.py that bai -> DUNG. Khong chay tiep voi cau hinh thieu.'
  exit 2
}

$cfg = Get-Content $snap -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $cfg.runner) { Write-Host 'run.ps1: campaign.md thieu runtime.runner -> DUNG.'; exit 2 }

# Runner có thể nằm NGAY TRONG thư mục chiến dịch (truyện) hoặc ở engine dùng chung (tin).
$runner = Join-Path $cam $cfg.runner
if (-not (Test-Path $runner)) { $runner = Join-Path $engine $cfg.runner }
if (-not (Test-Path $runner)) { Write-Host ('run.ps1: khong thay runner ' + $cfg.runner); exit 2 }

$rargs = @()
if ($cfg.runner_args) { $rargs = @([string]$cfg.runner_args -split '\s+' | Where-Object { $_ }) }
if ($args) { $rargs += $args }

& $runner @rargs -Config $snap
exit $LASTEXITCODE
