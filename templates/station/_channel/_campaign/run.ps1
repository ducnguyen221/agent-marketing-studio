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

$cam = $PSScriptRoot

# ── Trạm · engine · repo: phân giải, KHÔNG trỏ cứng đường của máy nào ────────
# Cùng một file chạy ở Windows (PS 5.1) và macOS (pwsh 7), nên không có ổ đĩa, không có
# thư mục người dùng nào được viết sẵn ở đây.
#   Trạm   : đi LÊN từ thư mục chiến dịch tới thư mục có CHANNELS.md
#            -> biến MARKETING_STUDIO_DATA -> $HOME/.marketing
#   Engine : <trạm>/engine — tên cố định
#   Repo   : biến MARKETING_STUDIO_HOME -> $HOME/Code/agent-marketing-studio
$station = $null
$d = $cam
while ($d) {
  if (Test-Path (Join-Path $d 'CHANNELS.md')) { $station = $d; break }
  $cha = Split-Path $d -Parent
  if ($cha -eq $d) { break }
  $d = $cha
}
if (-not $station) {
  if ($env:MARKETING_STUDIO_DATA) { $station = $env:MARKETING_STUDIO_DATA }
  else { $station = Join-Path $HOME '.marketing' }
}
$engine = Join-Path $station 'engine'
# ĐƯỜNG LÙI TẠM — gỡ ở bước 3A.4 của kế hoạch chuyển máy, khi engine đã vào trạm.
# Tới lúc đó engine dùng chung còn nằm ở thư mục `.news/engine` trong thư mục nhà.
if (-not (Test-Path $engine)) {
  $engineCu = Join-Path $HOME (Join-Path '.news' 'engine')
  if (Test-Path $engineCu) {
    Write-Host ('run.ps1: chua co ' + $engine + ' -> tam dung engine cu ' + $engineCu + ' (duong lui, go o 3A.4)')
    $engine = $engineCu
  }
}
if ($env:MARKETING_STUDIO_HOME) { $repo = $env:MARKETING_STUDIO_HOME }
else { $repo = Join-Path $HOME (Join-Path 'Code' 'agent-marketing-studio') }
$cfgpy = Join-Path $repo (Join-Path 'scripts' (Join-Path 'pipeline' 'campaign_cfg.py'))
Write-Host ('run.ps1: station=' + $station + ' engine=' + $engine + ' repo=' + $repo)
if (-not (Test-Path $cfgpy)) {
  Write-Host ('run.ps1: khong thay ' + $cfgpy + ' -> DUNG. Dat bien MARKETING_STUDIO_HOME = thu muc repo.')
  exit 2
}

$python = Find-Python -Repo $repo
if (-not $python) { exit 2 }

$logs = Join-Path $cam 'logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null

# Bản chụp sinh LẠI mỗi lượt -> sửa campaign.md xong chạy lại là ăn ngay, không cache.
# Đây là NHẬT KÝ, không phải nguồn: đừng sửa tay, lượt sau ghi đè.
$snap = Join-Path $logs ('config-' + (Get-Date -Format 'yyyy-MM-dd') + '.json')
$env:PYTHONIOENCODING = 'utf-8'
& $python $cfgpy --campaign $cam --out $snap
if ($LASTEXITCODE -ne 0) {
  Write-Host 'run.ps1: campaign_cfg.py that bai -> DUNG. Khong chay tiep voi cau hinh thieu.'
  exit 2
}

$cfg = Get-Content $snap -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $cfg.runner) { Write-Host 'run.ps1: campaign.md thieu runtime.runner -> DUNG.'; exit 2 }

# Runner tìm theo BA chỗ, ưu tiên từ gần tới xa:
#   1. ngay trong thư mục chiến dịch  (runner riêng của một chiến dịch, vd truyện)
#   2. `scripts/runners/` của REPO    (runner dùng chung, đi kèm repo — bản clone có ngay)
#   3. engine dùng chung của trạm     (<trạm>/engine — xem phần phân giải ở trên)
# Chỗ 2 suy từ cùng biến $repo đã tìm ra `campaign_cfg.py`: một nguồn cho đường repo,
# hai nguồn thì sớm muộn lệch nhau.
$repoScripts = Join-Path $repo 'scripts'
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
