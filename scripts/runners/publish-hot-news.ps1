# Hot News - publish pipeline (engine dùng chung). Chạy SAU khi đã dựng 2 video.
# Cấu hình theo brand đọc từ <trạm>/<kênh>/brand.json.
#   publish-hot-news.ps1 -Brand ai|data -Date <d> [-SkipUpload] [-Uat] [-Privacy public]
#   -Uat : test an toàn (KHÔNG upload YouTube, KHÔNG git push/update web, FB dry-run, Excel sheet UAT).
# Exit: 0 ok / 1 loi.
param(
  [string]$Brand = 'ai',
  [string]$Date = (Get-Date -Format 'yyyy-MM-dd'),
  [string]$Privacy = 'public',
  [switch]$SkipUpload,
  [switch]$Uat,
  [string]$StartTime = '',
  # ⚠️ KHÔNG CÒN DÙNG từ v3 (18/08/2026). Facebook nay ĐĂNG NGAY, không hẹn giờ —
  # vì bài hẹn giờ chưa tồn tại nên không gắn được comment mang link.
  # Giữ tham số lại CHỈ để run-toptoday-hot.ps1 truyền vào mà không lỗi. Đặt giá trị ở
  # đây sẽ KHÔNG có tác dụng gì. Muốn đổi giờ đăng thì đổi giờ chạy scheduled task.
  [string]$FbAt = '20:00',
  # Bản chụp cấu hình do `campaign_cfg.py` sinh từ `campaign.md`. KHÔNG truyền = chạy y
  # hệt như trước (đọc brand.json). Xem Get-Cfg trong brand-paths.ps1.
  [string]$Config = ''
)

$ErrorActionPreference = 'Continue'
try { chcp 65001 > $null } catch {}
$utf8 = New-Object System.Text.UTF8Encoding $false
$OutputEncoding = $utf8
try { [Console]::OutputEncoding = $utf8 } catch {}
$env:PYTHONIOENCODING = 'utf-8'; $env:PYTHONUTF8 = '1'

$engine   = $PSScriptRoot
. (Join-Path $engine 'brand-paths.ps1')
Set-SecretEnv
$brandDir = Get-BrandDir $Brand
$cfg = Get-Cfg -Config $Config -BrandDir $brandDir
$Label       = $cfg.label
$repo        = $cfg.repo
$Playlist    = $cfg.yt_playlist_daily
$pageUrl     = $cfg.page_hot
$SiteRoot    = $cfg.site_root
$TitlePrefix = $cfg.yt_title_prefix_daily

$tool    = $engine            # script dùng chung (build_hot_desc, youtube_upload, update_hot_index, post_facebook, append_excel_log)
$ToolDir = $brandDir          # config theo brand (facebook_config, youtube_token)
$ovpy    = Find-OmniVoicePython
$syspy   = Find-Python -Repo $script:RepoRoot
if (-not $syspy) { throw 'khong thay Python 3.10+ (dat MARKETING_STUDIO_PY).' }
# Đường ra/log RIÊNG của chiến dịch khi có -Config; không có thì giữ đường cũ ở cấp
# kênh. Hai chiến dịch dùng CHUNG một thư mục log là ranh giới giữa chúng chỉ tồn tại
# trong tên file — đếm số của một chiến dịch phải lọc bằng mắt.
$outRoot = if ($cfg.out_root) { [string]$cfg.out_root } else { Join-Path $brandDir 'daily-out' }
$logdir  = if ($cfg.log_dir) { [string]$cfg.log_dir } else { Join-Path $brandDir 'logs' }
New-Item -ItemType Directory -Force -Path $logdir | Out-Null
# Con trỏ bí mật (ĐƯỜNG DẪN tới file trong kho secret của máy), lùi về file cũ cạnh brand nếu
# chưa có. Get-EnvVar: tiến trình -> registry User (chỉ Windows) -> <repo>/.env (embedded).
# Đọc registry TRẦN ở đây (bản cũ) thì macOS nhận chuỗi rỗng và lặng lẽ bỏ qua upload.
$ytTokMoi = Get-EnvVar 'YT_TOKEN_PATH'
$ytCliMoi = Get-EnvVar 'YT_CLIENT_SECRET'
if ($ytTokMoi -and (Test-Path $ytTokMoi)) { $env:YT_TOKEN_PATH = $ytTokMoi; $secretSrc = 'NEW' }
else { $env:YT_TOKEN_PATH = (Join-Path $brandDir 'youtube_token.json'); $secretSrc = 'OLD' }
if ($ytCliMoi -and (Test-Path $ytCliMoi)) { $env:YT_CLIENT_SECRET = $ytCliMoi }
else { $env:YT_CLIENT_SECRET = (Join-Path $brandDir 'youtube_client_secret.json') }
$doUpload = -not ($SkipUpload -or $Uat)

$log = Join-Path $logdir ('hot-publish-' + $Label + '-' + $Date + '.log')
function Log($m) {
  $ts = Get-Date -Format 'HH:mm:ss'; $line = $ts + '  ' + $m
  [System.IO.File]::AppendAllText($log, ($line + "`r`n"), $utf8); Write-Host $line
}

Log ("=== $TitlePrefix publish start ($Label)" + $(if ($Uat) { ' [UAT]' } else { '' }) + ' ===')

Log ('secret: ' + $secretSrc + '  ' + $env:YT_TOKEN_PATH)
Log ('cfg: ' + $CfgSrc + $(if ($Config) { '  ' + $Config } else { '' }))   # nguon cau hinh: CONFIG = ban chup tu campaign.md, BRAND.JSON = duong cu
Log ("Date " + $Date)

$srcDir   = Join-Path $outRoot $Date
$longSrc  = Join-Path $srcDir ($Date + '-top.mp4')
$shortSrc = Join-Path $srcDir ($Date + '-top-short.mp4')
$jsonPath = Join-Path $srcDir ($Date + '-top.json')
$sidecar  = $jsonPath + '.published.json'
# Restart guard: json LUON bat buoc. mp4 chi can khi CHUA publish — sau khi da co
# video_id trong sidecar, mp4 trong daily-out da bi don (YouTube la noi luu) nen
# re-run khong yeu cau mp4 nua.
$alreadyPub = $false
if (Test-Path $sidecar) {
  try { $sc0 = Get-Content $sidecar -Raw -Encoding UTF8 | ConvertFrom-Json; if ([string]$sc0.video_id) { $alreadyPub = $true } } catch {}
}
$need = if ($alreadyPub) { @($jsonPath) } else { @($longSrc, $shortSrc, $jsonPath) }
foreach ($f in $need) {
  if (-not (Test-Path $f)) { Log ("ERROR: missing " + $f); Log '=== failed ==='; exit 1 }
}

try {
  $brief = Get-Content $jsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
  $headline = [string]$brief.top_story.headline
} catch { Log ("ERROR: cannot parse " + $jsonPath + " : " + $_); exit 1 }
if (-not $headline) { Log 'ERROR: headline empty.'; exit 1 }
$ddmmyyyy = ([datetime]$Date).ToString('dd/MM/yyyy')
$ytTitle      = $TitlePrefix + ' | ' + $ddmmyyyy + ' | ' + $headline
# Short: tiêu đề RIÊNG để không trùng bản deep-dive trên kênh (youtube_upload tự thêm " #Shorts").
$ytTitleShort = '⚡ 60 giây | ' + $headline
Log ("YT title: " + $ytTitle)
Log ("YT title (short): " + $ytTitleShort + ' #Shorts')

# (KHONG copy mp4 vao repo nua — YouTube la noi luu video. mp4 trong daily-out se bi
#  don sau khi publish thanh cong, xem cuoi file.)

# --- descriptions ---
$descLong  = Join-Path $srcDir 'desc-top.txt'
$descShort = Join-Path $srcDir 'desc-top-short.txt'
# Tác giả đi qua cấu hình kênh (channel.yml brand.author) — không viết trong mã.
$descArgs = @('--top-json', $jsonPath, '--page-url', $pageUrl, '--site', $SiteRoot, '--label', $Label)
if ($cfg.author) { $descArgs += @('--author', [string]$cfg.author) }
& $ovpy (Join-Path $tool 'build_hot_desc.py') @descArgs --out $descLong  2>&1 | ForEach-Object { Log ('desc: ' + $_) }
& $ovpy (Join-Path $tool 'build_hot_desc.py') @descArgs --out $descShort --shorts 2>&1 | ForEach-Object { Log ('desc: ' + $_) }
# Thẻ YouTube: `yt_tags` của campaign.md; không khai thì bộ mặc định + tên trang của kênh.
$ytTags = if ($cfg.yt_tags) { [string]$cfg.yt_tags } elseif ($cfg.site_name) { 'AI,tin tức AI,' + [string]$cfg.site_name } else { 'AI,tin tức AI' }

if (-not $Uat) { Set-Location $repo; git pull --rebase --autostash origin main 2>&1 | ForEach-Object { Log ('git: ' + $_) } }

# --- upload YouTube (restart guard via sidecar) ---
$ytpy = Join-Path $tool 'youtube_upload.py'
$tokenOk = Test-Path $env:YT_TOKEN_PATH
$vidLong = ''; $vidShort = ''; $fbDoneId = ''
if (Test-Path $sidecar) {
  try { $sc = Get-Content $sidecar -Raw -Encoding UTF8 | ConvertFrom-Json; $vidLong = [string]$sc.video_id; $vidShort = [string]$sc.short_id; $fbDoneId = [string]$sc.fb_post_id
        if ($vidLong) { Log ('YouTube: IDs already in sidecar - skip upload.') } } catch {}
}
# Ghi/merge sidecar (giữ video ids + fb id) — đảm bảo idempotent cho re-run.
function Save-Sidecar { @{ video_id = $vidLong; short_id = $vidShort; fb_post_id = $fbDoneId; uploaded_at = (Get-Date).ToString('s') } | ConvertTo-Json | Set-Content -Path $sidecar -Encoding UTF8 }
if (-not $doUpload) {
  Log $(if ($Uat) { 'UAT: skip YouTube upload.' } else { 'SkipUpload: bo qua YouTube.' })
} elseif (-not $tokenOk) {
  Log 'WARN: youtube_token.json khong co - bo qua upload.'
} elseif (-not $vidLong) {
  Log ('YouTube: uploading deep-dive (playlist "' + $Playlist + '") ...')
  $thumb = Join-Path $srcDir 'thumb.jpg'
  & (Find-Ffmpeg) -y -loglevel error -ss 2 -i $longSrc -frames:v 1 -q:v 2 $thumb 2>&1 | Out-Null
  if (-not (Test-Path $thumb)) { Log 'WARN: khong trich duoc anh dai dien.'; $thumb = '' }
  $out = & $ovpy $ytpy --file $longSrc --title $ytTitle --desc-file $descLong --privacy $Privacy --playlist $Playlist --tags $ytTags --thumbnail $thumb 2>&1 | Out-String
  $out -split "`r?`n" | Where-Object { $_ } | ForEach-Object { Log ('yt: ' + $_) }
  $m = [regex]::Match($out, 'VIDEO_ID=([A-Za-z0-9_-]+)'); if ($m.Success) { $vidLong = $m.Groups[1].Value }
  Log ('YouTube: uploading short (playlist "' + $Playlist + '") ...')
  $out = & $ovpy $ytpy --file $shortSrc --title $ytTitleShort --desc-file $descShort --privacy $Privacy --playlist $Playlist --tags $ytTags --shorts 2>&1 | Out-String
  $out -split "`r?`n" | Where-Object { $_ } | ForEach-Object { Log ('yt: ' + $_) }
  $m = [regex]::Match($out, 'VIDEO_ID=([A-Za-z0-9_-]+)'); if ($m.Success) { $vidShort = $m.Groups[1].Value }
  if ($vidLong -or $vidShort) { Save-Sidecar }
}

# --- web index + git push (bỏ qua khi UAT) ---
if (-not $Uat) {
  # Join-Path LỒNG từng đoạn: trên macOS gạch ngược là một ký tự trong TÊN file, nên
  # 'hot-today\hot-news.json' tạo một file lạ ở gốc repo web và trang Hot Today đứng im.
  $dataJson = Join-Path (Join-Path $repo 'hot-today') 'hot-news.json'
  $pubAt = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ss')
  & $ovpy (Join-Path $tool 'update_hot_index.py') --top-json $jsonPath --data $dataJson --date $Date `
      --video-id $vidLong --short-id $vidShort --published-at $pubAt 2>&1 | ForEach-Object { Log ('index: ' + $_) }
  Set-Location $repo
  git add hot-today .gitignore 2>&1 | ForEach-Object { Log ('git: ' + $_) }
  $gitAuthor = Get-GitAuthorArgs $cfg
  git @gitAuthor commit -m ($TitlePrefix + ' - ' + $Date + ' - ' + $headline) 2>&1 | ForEach-Object { Log ('git: ' + $_) }
  git push origin main 2>&1 | ForEach-Object { Log ('git: ' + $_) }
  if ($LASTEXITCODE -ne 0) { Log 'ERROR: git push failed.'; Log '=== failed ==='; exit 1 }
}
Log ('DONE. Page: ' + $pageUrl)
if ($vidLong) { Log ('  video: https://youtu.be/' + $vidLong) }

# --- Facebook (hẹn 9h) + Excel log (best-effort) ---
$fbStatus = 'skip'
try {
  $fbText = [string]$brief.facebook_post
  $fbCfg = if ($env:FB_CONFIG) { $env:FB_CONFIG } else { Join-Path $ToolDir 'facebook_config.json' }
  if (-not (Test-Path $fbCfg)) { $fbStatus = 'chưa thiết lập token'; Log 'FB: chưa có facebook_config.json - bỏ qua.' }
  elseif (-not $fbText) { $fbStatus = 'thiếu facebook_post'; Log 'FB: brief không có facebook_post.' }
  elseif ($fbDoneId -and -not $Uat) { $fbStatus = 'đã đăng trước đó (' + $fbDoneId + ') - skip'; Log ('FB: ' + $fbStatus) }
  else {
    $fbFile = Join-Path $srcDir 'fb-post.txt'
    [System.IO.File]::WriteAllText($fbFile, $fbText, $utf8)
    # ── CHIẾN LƯỢC v2 (18/08/2026): VIDEO NATIVE, KHÔNG LINK ────────────────────
    # Trước: bài text + thẻ link trỏ trang tin của kênh (để Meta Pixel đo). Nhưng Facebook dìm
    # phân phối MỌI bài dẫn ra ngoài, mà Page đang chết đói reach (1-11 view/bài) — đo
    # chính xác một con số bằng 0 thì vô nghĩa. Nay video được HOST TRÊN CHÍNH FACEBOOK,
    # phần chữ đi trong description của video. Không còn bài text riêng, không còn link.
    # Đánh đổi đã biết và đã chọn: Pixel gần như không thu được gì từ Facebook giai đoạn này.
    # Kênh tách hẳn: YouTube giữ bản của YouTube, Facebook giữ bản của Facebook, KHÔNG trỏ nhau.
    # v3 (18/08/2026): Reel là object DUY NHẤT trên Facebook, mang TOÀN VĂN bài blog.
    # BỎ video dài khỏi Facebook: Meta gộp MỌI video của Page thành Reel và KHÔNG có
    # opt-out (about.fb.com — "all videos on Facebook will be shared as reels"), nên video
    # ngang 16:9 lọt vào thư viện Reel, bìa bị crop mất tiêu đề, làm hỏng bố cục thư viện.
    # Video dài vẫn sống trên YouTube; link của nó nằm ở COMMENT chứ không trong bài.
    # ĐĂNG NGAY (không --at): bài hẹn giờ chưa tồn tại nên không comment được.
    $fbArgs = @((Join-Path $tool 'post_facebook.py'), '--tool', $ToolDir, '--message-file', $fbFile, '--no-link', '--reel-main')
    # Bài chữ riêng: TẮT mặc định từ 05/09/2026. `--reel-main` chỉ đổi caption chứ không
    # tắt nhánh đăng, nên trước nay mỗi lượt đẻ HAI object trùng nguyên văn.
    # Bật lại = thêm "fb_text_post": true vào brand.json (khoá vắng mặt = tắt).
    if (-not $cfg.fb_text_post) { $fbArgs += '--no-text-post' }
    # Comment mang link — Meta KHUYẾN NGHỊ đặt link ở comment thay vì caption; caption có
    # link bị dìm nặng, comment thì không bị tính vào phân phối của bài.
    $cmtFile = Join-Path $srcDir 'fb-comment.txt'
    $cmtLines = @('📖 Bài đầy đủ (có ảnh + nguồn): ' + $pageUrl)
    if ($vidLong) { $cmtLines += '🎬 Bản video dài: https://youtu.be/' + $vidLong }
    [System.IO.File]::WriteAllText($cmtFile, ($cmtLines -join "`n"), $utf8)
    $fbArgs += @('--comment-file', $cmtFile)
    if (Test-Path $shortSrc) { $fbArgs += @('--reel', $shortSrc) }   # video Reel dọc 9:16 — object DUY NHẤT trên FB
    else { Log 'FB: KHONG co video short -> khong dang duoc gi len Facebook' }
    # Caption Reel do AI viết riêng (trường facebook_reel trong brief). Thiếu trường này thì
    # post_facebook tự dựng caption dự phòng có hook riêng — xem compose_reel().
    $fbReelText = [string]$brief.facebook_reel
    if ($fbReelText) {
      $fbReelFile = Join-Path $srcDir 'fb-reel.txt'
      [System.IO.File]::WriteAllText($fbReelFile, $fbReelText, $utf8)
      $fbArgs += @('--reel-desc-file', $fbReelFile)
    }
    if ($Uat) { $fbArgs += '--dry-run' }
    $fbout = & $syspy @fbArgs 2>&1 | Out-String
    $fbout -split "`r?`n" | Where-Object { $_ } | ForEach-Object { Log ('fb: ' + $_) }
    $mm = [regex]::Match($fbout, 'STATUS=(.+)')
    if ($Uat) { $fbStatus = 'UAT dry-run' } elseif ($mm.Success) { $fbStatus = $mm.Groups[1].Value.Trim() } else { $fbStatus = 'lỗi (không có STATUS)' }
    # ghi id vào sidecar để re-run không đăng lại (chỉ khi đăng thật thành công)
    # ƯU TIÊN FB_REEL_ID: từ 05/09/2026 bài chữ đã tắt nên FB_POST_ID luôn in "-", khớp
    # regex không nổi -> sidecar rỗng -> lượt chạy lại sẽ đăng Reel LẦN HAI mà không ai báo.
    # Dấu "-" không lọt qua [0-9_]+ nên nhánh lùi tự động đúng khi bài chữ được bật lại.
    $fbidm = [regex]::Match($fbout, 'FB_REEL_ID=([0-9_]+)')
    if (-not $fbidm.Success) { $fbidm = [regex]::Match($fbout, 'FB_POST_ID=([0-9_]+)') }
    if ((-not $Uat) -and $fbidm.Success) { $fbDoneId = $fbidm.Groups[1].Value; Save-Sidecar }
  }
} catch { $fbStatus = 'lỗi: ' + $_; Log ('FB: exception ' + $_) }

# ── Hậu kiểm ĐỘ PHỦ (read-only, best-effort) ────────────────────────────────
# Soi bài của các lần chạy TRƯỚC — bài vừa hẹn chưa publish nên không nằm trong tầm đo.
# Có mặt vì: 61 bài từ 20/06→17/08/2026 báo "scheduled@..." xanh mượt mà KHÔNG AI NGOÀI
# THẤY (app Meta còn Development mode). "API nhận bài" không chứng minh bài tới tay ai;
# chỉ có người thật xem/tương tác mới chứng minh được. notify-run.ps1 đẩy khối này lên Telegram.
try {
  $rcArgs = @((Join-Path $tool 'check_fb_reach.py'), '--tool', $ToolDir, '--label', $Label, '--hours', '48')
  $rcOut = & $syspy @rcArgs 2>&1 | Out-String
  $rcOut -split "`r?`n" | Where-Object { $_ } | ForEach-Object { Log $_ }
} catch { Log ('reach: exception ' + $_) }

try {
  $rowFile = Join-Path $srcDir 'xlsx-row.json'
  ([ordered]@{
    time_start = $StartTime; time_end = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    status = $(if ($Uat) { 'UAT' } else { 'success' })
    script = 'run-toptoday-hot.ps1 -> publish-hot-news.ps1'; title = $ytTitle
    video_location = $(if ($vidLong) { 'https://youtu.be/' + $vidLong } else { '(chua upload)' }); post = [string]$brief.facebook_post; note = 'FB: ' + $fbStatus
  } | ConvertTo-Json -Depth 4) | Set-Content -Path $rowFile -Encoding UTF8
  $sheet = $(if ($Uat) { 'UAT ' + $Label } else { 'Daily ' + $Label })
  & $syspy (Join-Path $tool 'append_excel_log.py') --sheet $sheet --row $rowFile --log $log 2>&1 | ForEach-Object { Log ('xlsx: ' + $_) }
} catch { Log ('xlsx: exception ' + $_) }

# --- don dia: video da an toan tren YouTube => xoa mp4 nang trong daily-out ---
# Giu lai cac file NHE lam guard/log: <date>-top.json, *.published.json (sidecar),
# desc-top*.txt, fb-post.txt, xlsx-row.json. KHONG dong file gi vao repo (web dung
# YouTube embed). UAT/khong-upload (vidLong rong) -> GIU mp4 de kiem tra thu cong.
if ((-not $Uat) -and $vidLong) {
  foreach ($f in @($longSrc, $shortSrc, (Join-Path $srcDir 'thumb.jpg'))) {
    if (Test-Path $f) { Remove-Item $f -Force -ErrorAction SilentlyContinue; Log ('cleanup: xoa ' + (Split-Path $f -Leaf)) }
  }
} else {
  Log 'cleanup: GIU mp4 (UAT/chua-upload) - chua co ban YouTube an toan.'
}

Log '=== complete ==='
exit 0
