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

# Runner tìm theo BA chỗ, ưu tiên từ gần tới xa:
#   1. ngay trong thư mục chiến dịch  (runner riêng của một chiến dịch, vd truyện)
#   2. `scripts/runners/` của REPO    (runner dùng chung, đi kèm repo — bản clone có ngay)
#   3. engine dùng chung của máy      (runner cũ ở ~/.news/engine)
# Chỗ 2 suy từ vị trí `campaign_cfg.py` chứ không trỏ cứng lần nữa: một đường dẫn cứng đã
# đủ, hai cái thì sớm muộn lệch nhau.
$repoScripts = Split-Path (Split-Path $cfgpy -Parent) -Parent
$runner = Join-Path $cam $cfg.runner
if (-not (Test-Path $runner)) { $runner = Join-Path $repoScripts (Join-Path 'runners' $cfg.runner) }
if (-not (Test-Path $runner)) { $runner = Join-Path $engine $cfg.runner }
if (-not (Test-Path $runner)) { Write-Host ('run.ps1: khong thay runner ' + $cfg.runner); exit 2 }

# ── Đối số cho runner: BẢNG BĂM, KHÔNG phải mảng ────────────────────────────
# ĐÃ TRẢ GIÁ 07–08/09/2026. Chỗ này từng là `& $runner @rargs -Config $snap` với `$rargs`
# là MẢNG. PowerShell splat mảng thì buộc tham số THEO VỊ TRÍ, không theo tên: chuỗi
# `-Brand ai -Publish` vào runner thành `$Brand = '-Brand'`, `$Profile = 'ai'`, còn
# `-Publish` BIẾN MẤT KHÔNG MỘT DÒNG BÁO. Hai kiểu hỏng, kiểu thứ hai đắt hơn nhiều:
#   · runner CÓ tham số -Brand  -> Get-BrandDir ném lỗi ngay, exit 1, thấy được
#     (Daily Hot Data 07/09, Daily Hot AI 08/09 chết đúng kiểu này);
#   · runner KHÔNG có -Brand    -> `-Publish` rơi vào $Date, switch $Publish = $false,
#     pipeline chạy trọn rồi `if (-not $Publish) { exit 0 }` => KHÔNG ĐĂNG GÌ mà
#     Telegram vẫn báo ✅ (hot-repo nằm đúng nhánh này, chưa kịp tới lịch).
# Splat BẢNG BĂM thì PowerShell buộc theo TÊN và switch vẫn là switch.
function ConvertTo-ThamSo {
  param([string[]]$Tokens, [string]$Nguon)
  $h = @{}
  for ($i = 0; $i -lt $Tokens.Count; $i++) {
    $t = [string]$Tokens[$i]
    if ($t -notmatch '^-{1,2}[A-Za-z]') {
      throw ("doi so runner khong doc duoc (tu " + $Nguon + "): '" + $t +
             "' khong phai ten tham so dang -Ten. Ca chuoi: " + ($Tokens -join ' '))
    }
    $ten = $t -replace '^-{1,2}', ''
    $ke  = $null
    if ($i + 1 -lt $Tokens.Count) { $ke = [string]$Tokens[$i + 1] }
    # `-1` là GIÁ TRỊ âm chứ không phải tên tham số -> chỉ coi là tên khi có chữ cái.
    if ($null -ne $ke -and $ke -notmatch '^-{1,2}[A-Za-z]') { $h[$ten] = $ke; $i++ }
    else { $h[$ten] = $true }
  }
  return $h
}

$toks = @()
if ($cfg.runner_args) { $toks += @([string]$cfg.runner_args -split '\s+' | Where-Object { $_ }) }
if ($args) { $toks += @($args | ForEach-Object { [string]$_ }) }

try {
  $tham = ConvertTo-ThamSo -Tokens $toks -Nguon 'campaign.md: runtime.runner_args + dong lenh'
} catch {
  Write-Host ('run.ps1: ' + $_.Exception.Message)
  exit 2
}
$tham['Config'] = $snap

# In ĐÚNG thứ sắp truyền xuống. Lượt chạy nền chỉ để lại cái log này; thiếu dòng này thì
# lần sau tham số rơi mất lại phải dò lại từ đầu.
Write-Host ('run.ps1: ' + $cfg.runner + ' <- ' +
  (($tham.Keys | Sort-Object | ForEach-Object { '-' + $_ + ' ' + $tham[$_] }) -join ' '))

& $runner @tham
exit $LASTEXITCODE
