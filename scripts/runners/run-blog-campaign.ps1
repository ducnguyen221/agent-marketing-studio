# run-blog-campaign.ps1 — VỎ MỎNG cho Task Scheduler. Logic thật nằm ở campaign_step.py.
#
# Vì sao mỏng: bước `create-post` phải đọc bảng Content trong Markdown để biết bài nào tới
# hạn. PowerShell 5.1 không đọc nổi YAML/Markdown có cấu trúc — đó chính là lý do
# `campaign_cfg.py` ra đời. Viết lại bộ đọc bảng bằng PowerShell là đi ngược một bài học
# đã trả giá. PowerShell chỉ giữ vai nó làm tốt: mặt tiền cho Task Scheduler và
# notify-run.ps1.
#
# Ba bước RỜI, mỗi lượt chạy đúng một bước:
#   create-post ──[ Cổng 1 ]── soan ──[ Cổng 2 ]── dang
# Gộp lại là dựng lại đúng cái đã bị gỡ 04/09/2026 vì nuốt cổng duyệt của người.
#
#   .\run.ps1 -Step create-post              dựng bài tới hạn rồi xin duyệt Cổng 1
#   .\run.ps1 -Step write                  soạn bài đã qua Cổng 1 rồi xin duyệt Cổng 2
#   .\run.ps1 -Step publish                  đăng bài đã qua Cổng 2
#   .\run.ps1 -Step publish -Uat             đăng thử: web ra thư mục nháp, không đụng repo
param(
  [ValidateSet('create-post', 'write', 'publish')][string]$Step = 'create-post',
  [string]$Config = '',
  [int]$Lookahead = -1,
  [switch]$Uat,
  [switch]$DryRun
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
Write-Host ("=== " + $Step + " · " + (Split-Path $cam -Leaf) + " · autonomy=" + $muc + " ===")
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

$argv = @($cam, $Step)
if ($Lookahead -ge 0) { $argv += @('--lookahead', [string]$Lookahead) }
if ($Uat)         { $argv += '--uat' }
if ($DryRun)      { $argv += '--dry-run' }

$python = Find-Python -Repo (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
if (-not $python) { exit 2 }
& $python $py @argv
exit $LASTEXITCODE
