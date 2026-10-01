# Weekly news runner (engine dùng chung). Cấu hình theo brand từ <trạm>/<kênh>/brand.json.
#   run-weekly-news.ps1 -Brand ai     (Thứ 6 21:00)
#   run-weekly-news.ps1 -Brand data   (Thứ 7 21:00)
#   -Uat : test an toàn (KHÔNG upload YouTube / KHÔNG git push / KHÔNG gửi mail / FB dry-run).
# Pipeline: seen-list -> claude headless -> OmniVoice media (recap + short) -> YouTube
# (thumbnail = frame cover) -> inject HTML -> build-index -> git push -> newsletter -> FB + Excel.
# Exit: 0 ok / 1 fail.
param(
  [string]$Brand = 'ai',
  [string]$Profile = '',
  [switch]$Uat,
  # Bản chụp cấu hình do `campaign_cfg.py` sinh từ `campaign.md`. KHÔNG truyền = chạy y
  # hệt như trước (đọc brand.json). Xem Get-Cfg trong brand-paths.ps1.
  [string]$Config = ''
)

$ErrorActionPreference = 'Continue'
try { chcp 65001 > $null } catch {}
$utf8 = New-Object System.Text.UTF8Encoding $false
$OutputEncoding = $utf8
try { [Console]::OutputEncoding = $utf8 } catch {}

$engine   = $PSScriptRoot
. (Join-Path $engine 'brand-paths.ps1')
Set-SecretEnv
$brandDir = Get-BrandDir $Brand
$cfg = Get-Cfg -Config $Config -BrandDir $brandDir
$Label    = $cfg.label
$repo     = $cfg.repo
$ghRepo   = $cfg.gh_repo
# `--brand-config` của bộ dựng video: dùng BẢN CHỤP khi có -Config.
# `daily_news_media.py:201` mở file này KHÔNG có guard — trỏ vào file không tồn tại
# là crash ở bước dựng video, sau khi đã tốn thời gian sinh nội dung.
# Bản chụp có sẵn đúng các khoá nó cần: a · b · site · tagline · tagline_short · welcome.
$brandCfg = if ($Config) { $Config } else { Join-Path $brandDir 'brand.json' }

$tool    = $engine          # script dùng chung
# Script nghiên cứu last30days: L30_SCRIPT -> thư mục plugin của Claude (Find-Last30Days).
$l30     = Find-Last30Days
$ovpy    = Find-OmniVoicePython
$syspy   = Find-Python -Repo $script:RepoRoot
if (-not $syspy) { throw 'khong thay Python 3.10+ (dat MARKETING_STUDIO_PY).' }
# Bộ dựng bản tin tuần (audio từng mục + recap + short + chèn HTML) = module
# `daily_news_media` trong họ template bản tin của repo agent-video-studio, cài trong venv
# giọng, gọi bằng `python -m` (không còn đường tới bộ dựng cũ trong trạm giọng).
# NỢ: đây là module nội bộ của video-studio, KHÔNG phải hợp đồng `video-studio render` —
# `render --project news-weekly` chỉ dựng video, chưa làm phần audio từng mục + chèn HTML.
# Tên module ghép bằng -join: chuỗi liền của nó chứa tên thư mục engine cũ mà cổng
# test_khong_tham_chieu_engine_cu đi cấm.
$media = @('-m', (@('video_studio', 'templates', 'news', 'daily_news_media') -join '.'))
# Thư viện nhạc nền (AI chọn theo nội dung). Manifest = nguồn chân lý.
# VOICE_BGM_DIR -> <trạm video>/assets/news-bgm. AI chỉ được chọn style CÓ mp3 (Get-BgmCatalog).
$bgmDir  = if (Get-EnvVar 'VOICE_BGM_DIR') { Resolve-Home (Get-EnvVar 'VOICE_BGM_DIR') } elseif ($VideoStation) { [System.IO.Path]::Combine($VideoStation, 'assets', 'news-bgm') } else { '' }
$bgmCat  = Get-BgmCatalog $bgmDir
$bgmLib  = $bgmCat.lib
$bgmListText = $bgmCat.text
# Đường ra/log RIÊNG của chiến dịch khi có -Config; không có thì giữ đường cũ ở cấp
# kênh. Hai chiến dịch dùng CHUNG một thư mục log là ranh giới giữa chúng chỉ tồn tại
# trong tên file — đếm số của một chiến dịch phải lọc bằng mắt.
$logdir  = if ($cfg.log_dir) { [string]$cfg.log_dir } else { Join-Path $brandDir 'logs' }
New-Item -ItemType Directory -Force -Path $logdir | Out-Null
# Con trỏ bí mật (ĐƯỜNG DẪN tới file trong kho secret của máy), lùi về file cũ cạnh brand nếu
# chưa có. Get-EnvVar: tiến trình -> registry User (chỉ Windows) -> <repo>/.env (embedded).
$ytTokMoi = Get-EnvVar 'YT_TOKEN_PATH'
$ytCliMoi = Get-EnvVar 'YT_CLIENT_SECRET'
if ($ytTokMoi -and (Test-Path $ytTokMoi)) { $env:YT_TOKEN_PATH = $ytTokMoi; $secretSrc = 'NEW' }
else { $env:YT_TOKEN_PATH = (Join-Path $brandDir 'youtube_token.json'); $secretSrc = 'OLD' }
if ($ytCliMoi -and (Test-Path $ytCliMoi)) { $env:YT_CLIENT_SECRET = $ytCliMoi }
else { $env:YT_CLIENT_SECRET = (Join-Path $brandDir 'youtube_client_secret.json') }

$today = Get-Date -Format 'yyyy-MM-dd'
$log   = Join-Path $logdir ($today + '.log')
function Log($m) {
  $ts = Get-Date -Format 'HH:mm:ss'
  [System.IO.File]::AppendAllText($log, ($ts + '  ' + $m + "`r`n"), $utf8)
  # Write-Host BẮT BUỘC — không phải để xem cho vui.
  # notify-run.ps1 dựng tin Telegram từ STDOUT của runner (dòng 74), nó KHÔNG đọc file log.
  # Thiếu dòng này thì compose_report.py nhận log rỗng và tin báo chỉ còn tiêu đề + thời
  # lượng (hai thứ lấy từ tham số), mất sạch link/bước/độ phủ; lúc FAIL thì triage.py cũng
  # không chẩn được gì. Đã dính thật đêm 05/09/2026 với số W36.
  # In $m KHÔNG kèm timestamp: $stepRe trong notify-run neo '^(===|Launching|...)' — thêm
  # tiền tố giờ vào là hỏng khớp bước. Hai runner anh em (toptoday, weekly-repo) cũng vậy.
  Write-Host $m
}

$startTime = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
Log ("=== $Label News weekly run start" + $(if ($Uat) { ' [UAT]' } else { '' }) + ' ===')
Log ('secret: ' + $secretSrc + '  ' + $env:YT_TOKEN_PATH)
Log ('cfg: ' + $CfgSrc + $(if ($Config) { '  ' + $Config } else { '' }))   # nguon cau hinh: CONFIG = ban chup tu campaign.md, BRAND.JSON = duong cu
# Nhạc nền: kiểm TRƯỚC `claude -p` — ép một style/file không có thì DỪNG ngay (rẻ); style
# thiếu mp3 chỉ nhắc, AI không được chọn chúng.
$bgmEp = Resolve-ForcedBgm -Cfg $cfg -Dir $bgmDir -BrandDir $brandDir
if (-not $bgmEp.ok) { Log ("ERROR: bgm = '" + $cfg.bgm + "' khong co file mp3 (thu vien: " + $bgmDir + ")."); Log '=== run failed ==='; exit 1 }
if (@($bgmCat.missing).Count -gt 0) { Log ('WARN: thu vien nhac nen thieu mp3 cho: ' + (@($bgmCat.missing) -join ', ') + ' (' + $bgmDir + ')') }

$now = Get-Date
$thu = $now.AddDays(3 - ((([int]$now.DayOfWeek) + 6) % 7))
$isoYear = $thu.Year
$isoWeek = [int]([math]::Floor(($thu.DayOfYear - 1) / 7) + 1)
$wk = '{0:D2}' -f $isoWeek
$weekLabel = 'W' + $wk
$monday = $thu.AddDays(-3); $sunday = $thu.AddDays(3)
$range = $monday.ToString('dd/MM') + ' - ' + $sunday.ToString('dd/MM/yyyy')
$displayDate = $now.ToString('dd/MM/yyyy')
$month = $now.ToString('MM')
Log ('Date ' + $today + '  ' + $weekLabel + '  range ' + $range + '  brand ' + $Brand)

$folder = Join-Path (Join-Path $repo $now.ToString('yyyy')) $month
New-Item -ItemType Directory -Force -Path $folder | Out-Null
$target = Join-Path $folder ('w' + $wk + '.html')
$pageUrlPub = $cfg.page_weekly_base + $now.ToString('yyyy') + '/' + $month + '/w' + $wk + '.html'
$recapTitle = $cfg.weekly_recap_title.Replace('{week}', $weekLabel).Replace('{range}', $range)
$shortTitle = $cfg.weekly_short_title.Replace('{week}', $weekLabel).Replace('{range}', $range)
Log ('Target: ' + $target)

Set-Location $repo
git pull --rebase --autostash origin main 2>&1 | ForEach-Object { Log ('git: ' + $_) }
$env:PYTHONIOENCODING = 'utf-8'
function BriefOk { (Test-Path $target) -and ((Get-Item $target).Length -ge 1000) }

if (BriefOk) {
  Log 'Brief already exists (restarted run) - skipping claude regen.'
} else {
  $p0 = if ($cfg.prompt_path) { [string]$cfg.prompt_path } else { Join-Path $brandDir 'weekly-news-prompt.txt' }
  if (-not (Test-Path $p0)) { Log ("ERROR: prompt missing: " + $p0); Log '=== run failed ==='; exit 1 }
  if (-not ($l30 -and (Test-Path -LiteralPath $l30 -PathType Leaf))) {
    Log ('ERROR: khong thay script last30days (' + $l30 + '). Cai plugin Claude last30days hoac dat L30_SCRIPT.'); Log '=== run failed ==='; exit 1
  }
  $tmpl = Get-Content $p0 -Raw -Encoding UTF8
  $prompt = $tmpl.Replace('{{TARGET_PATH}}', $target).Replace('{{DISPLAY_DATE}}', $displayDate)
  $prompt = $prompt.Replace('{{L30_SCRIPT}}', $l30).Replace('{{WEEK}}', $weekLabel).Replace('{{RANGE}}', $range)
  $prompt = $prompt.Replace('{{PAGE_URL}}', $pageUrlPub)
  $mondayIso = $monday.ToString('yyyy-MM-dd')
  $seen = & $ovpy (Join-Path $tool 'build_seen_list.py') $repo $mondayIso 3 2>&1 | Out-String
  Log ('Seen-list items: ' + (([regex]::Matches($seen, '(?m)^- ')).Count))
  $prompt = $prompt.Replace('{{SEEN_LIST}}', $seen.Trim())
  # Hồ sơ TÁC GIẢ — dữ kiện về NGƯỜI, dùng chung mọi kênh. Dời từ `engine/assets/` về
  # trạm nội dung 07/09/2026: đó là NỘI DUNG, không phải code engine.
  # Đọc không được thì `{{VIEWPOINT}}` rỗng và bài mất phần chính kiến MÀ KHÔNG BÁO —
  # nên có dòng log ngay dưới để nhìn log là biết nó có tới nơi hay không.
  $vpFile = Join-Path $Station 'AUTHOR.md'
  $viewpoint = if (Test-Path $vpFile) { (Get-Content $vpFile -Raw -Encoding UTF8).Trim() } else { '' }
  $prompt = $prompt.Replace('{{VIEWPOINT}}', $viewpoint)
  $prompt = $prompt.Replace('{{BGM_LIST}}', $bgmListText)
  Log ('Viewpoint digest: ' + $viewpoint.Length + ' chars')
  # Bước nghiên cứu đi theo `order` của engines.json, không `claude -p` thô (P1-21). Tập tool
  # trừu tượng = allowlist cũ. -NoContentGate: giữ nguyên hành vi trang tuần như trước — cổng
  # chữ nội bộ của agent_call chưa từng áp cho trang này.
  Log 'Nghien cuu qua agent_call (engine theo order) ...'
  $ac = Invoke-AgentCall -Python $syspy -Prompt $prompt -Tools 'web,read,write,shell:curl,shell:python' `
    -Cwd $folder -Expect @($target + ':1000') -NoContentGate -OnLine { param($s) Log ('agent: ' + $s) }
  if ($ac.code -eq 4) {
    $mo = if ($ac.result -and $ac.result.resets_at) { [string]$ac.result.resets_at } else { '?' }
    Log ("HET HAN MUC moi engine trong order (mo lai $mo) - dung, khong dang."); Log '=== run failed ==='; exit 4
  }
  if ($ac.code -in 2, 3) { Log ("ERROR: agent_call ma $($ac.code)."); Log '=== run failed ==='; exit $ac.code }
}
if (-not (BriefOk)) { Log 'ERROR: briefing missing/too small.'; Log '=== run failed ==='; exit 1 }
Log ('Briefing OK, ' + (Get-Item $target).Length + ' bytes')

$env:HF_HUB_OFFLINE = '1'; $env:TRANSFORMERS_OFFLINE = '1'
# Nhạc nền (mix 10% dưới giọng đọc) — AI CHỌN theo nội dung (field "bgm" trong sidecar), áp cho CẢ recap + short.
# brand.json "bgm": tên-style/đường-dẫn = ÉP cố định; "" = TẮT; bỏ trống = theo lựa chọn của AI.
$bgmVol = if ($cfg.bgm_vol) { [string]$cfg.bgm_vol } else { '0.10' }
$bgmPath = Select-Bgm -Forced $bgmEp -Catalog $bgmCat -Pick (Read-BgmPick ($target + '.json'))
# Bộ dựng bản tin trộn nhạc ở bước ghép tiếng theo biến VOICE_BGM/VOICE_BGM_VOL (engine giọng;
# tên cũ NEWS_BGM* chỉ còn đọc một phiên bản) — gỡ cả hai bộ tên trước để không sót giá trị cũ.
Remove-Item Env:NEWS_BGM, Env:NEWS_BGM_VOL, Env:VOICE_BGM, Env:VOICE_BGM_VOL -ErrorAction SilentlyContinue
if ($bgmPath -and (Test-Path $bgmPath)) { $env:VOICE_BGM = $bgmPath; $env:VOICE_BGM_VOL = $bgmVol; Log ("BGM: " + (Split-Path $bgmPath -Leaf) + " @ " + $bgmVol) }
else { Log 'BGM: tat' }
Log 'Media pass: audio + recap video + short (no-inject) ...'
# --- Luan phien giong (2026-08-26) -------------------------------------------------
# Khong truyen -Profile thi tu chon theo series + ngay. Deterministic, khong can state:
# pick-voice.ps1 gan giong cho MOI series chay cung ngay sao cho khong cap nao qua
# giong nhau (my-voice va my-voice3 la cap sinh doi 0.91, khong bao gio dat canh).
# Truyen -Profile tuong minh thi van uu tien caller.
if (-not $Profile) {
  $vseries = if ($Brand -eq 'data') { 'data-weekly' } else { 'ai-weekly' }
  $Profile = & (Join-Path $PSScriptRoot 'pick-voice.ps1') -Series $vseries
  Log ("Voice: " + $Profile + "  (tu chon theo series ai/data-weekly + ngay)")
}
# ------------------------------------------------------------------------------------

# Mảng đối số dựng CÓ ĐIỀU KIỆN: PS 5.1 bỏ mất chuỗi rỗng khi truyền cho lệnh ngoài.
$ma = @($media + @('--html', $target, '--repo', $repo, '--date', $today, '--no-inject', '--brand-config', $brandCfg))
if ($Profile) { $ma += @('--profile', $Profile) }
& $ovpy @ma 2>&1 | ForEach-Object { $l = Format-NativeLine $_; if ($null -ne $l) { Log ('media: ' + $l) } }

$videoDir = Join-Path (Join-Path $repo 'video') $today
$recapFile = Join-Path $videoDir ($today + '.mp4')
$shortFile = Join-Path $videoDir ($today + '-short.mp4')
$ytpy = Join-Path $tool 'youtube_upload.py'
$ytRecap = ''; $ytShort = ''
$sidecarPath = $target + '.json'
if (Test-Path $sidecarPath) {
  try { $sc = Get-Content $sidecarPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($sc.youtube -and $sc.youtube.recap) { $ytRecap = [string]$sc.youtube.recap; $ytShort = [string]$sc.youtube.short
          Log ('YouTube: IDs already in sidecar - skip upload.') } } catch {}
}

if ($Uat) {
  Log 'UAT: skip YouTube upload.'
} elseif ((-not $ytRecap) -and (Test-Path $recapFile) -and (Test-Path $env:YT_TOKEN_PATH)) {
  $descpy = Join-Path $brandDir 'build_yt_desc.py'   # per-brand (text/hashtag riêng)
  # Bản khuôn mới (`templates/station/_channel/build_yt_desc.py`) lấy nhận diện kênh từ bản
  # chụp `--config`; bản cũ trong kênh không có cờ đó (argparse sẽ chết). Hỏi CHÍNH file.
  $descCfg = @()
  if ($Config -and ((Get-Content -LiteralPath $descpy -Raw -Encoding UTF8) -match "'--config'")) { $descCfg = @('--config', $Config) }
  $descRecap = Join-Path $videoDir 'desc-recap.txt'
  $descShort = Join-Path $videoDir 'desc-short.txt'
  $chaptersF = $recapFile + '.chapters.json'
  & $ovpy $descpy --sidecar $sidecarPath --page-url $pageUrlPub --chapters $chaptersF --out $descRecap @descCfg 2>&1 | ForEach-Object { $l = Format-NativeLine $_; if ($null -ne $l) { Log ('yt: ' + $l) } }
  & $ovpy $descpy --sidecar $sidecarPath --page-url $pageUrlPub --out $descShort --shorts @descCfg 2>&1 | ForEach-Object { $l = Format-NativeLine $_; if ($null -ne $l) { Log ('yt: ' + $l) } }
  # Thẻ YouTube: `yt_tags` của campaign.md; không khai thì bộ mặc định + tên trang của kênh.
  $ytTags = if ($cfg.yt_tags) { [string]$cfg.yt_tags } elseif ($cfg.site_name) { 'AI,tin tức AI,' + [string]$cfg.site_name } else { 'AI,tin tức AI' }
  Log ('YouTube: uploading weekly recap (playlist "' + $cfg.yt_playlist_weekly + '") ...')
  $thumb = Join-Path $logdir 'thumb-recap.jpg'   # ảnh đại diện = frame slide mở đầu
  & (Find-Ffmpeg) -y -loglevel error -ss 2 -i $recapFile -frames:v 1 -q:v 2 $thumb 2>&1 | Out-Null
  $out = & $ovpy $ytpy --file $recapFile --title $recapTitle --desc-file $descRecap --playlist ([string]$cfg.yt_playlist_weekly) --tags $ytTags --thumbnail $thumb 2>&1 | ForEach-Object { Format-NativeLine $_ }
  $out | ForEach-Object { Log ('yt: ' + $_) }
  $m = [regex]::Match(($out | Out-String), 'VIDEO_ID=([A-Za-z0-9_-]+)'); if ($m.Success) { $ytRecap = $m.Groups[1].Value }
  if (Test-Path $shortFile) {
    Log 'YouTube: uploading vertical short ...'
    $out = & $ovpy $ytpy --file $shortFile --title $shortTitle --desc-file $descShort --playlist ([string]$cfg.yt_playlist_weekly) --tags $ytTags --shorts 2>&1 | ForEach-Object { Format-NativeLine $_ }
    $out | ForEach-Object { Log ('yt: ' + $_) }
    $m = [regex]::Match(($out | Out-String), 'VIDEO_ID=([A-Za-z0-9_-]+)'); if ($m.Success) { $ytShort = $m.Groups[1].Value }
  }
}

# Inject video/audio vào HTML
if ($ytRecap) {
  $ma = @($media + @('--html', $target, '--repo', $repo, '--date', $today, '--inject-only', '--yt-recap', $ytRecap, '--brand-config', $brandCfg))
  if ($ytShort) { $ma += @('--yt-short', $ytShort) }
  & $ovpy @ma 2>&1 | ForEach-Object { $l = Format-NativeLine $_; if ($null -ne $l) { Log ('media: ' + $l) } }
} elseif ((-not $Uat) -and (Test-Path $recapFile)) {
  Log 'WARN: YouTube unavailable - fallback Release.'
  $relTag = 'media-' + $today
  $mediaBase = 'https://github.com/' + $ghRepo + '/releases/download/' + $relTag + '/'
  & gh release view $relTag --repo $ghRepo 2>&1 | Out-Null
  if ($LASTEXITCODE -ne 0) { & gh release create $relTag --repo $ghRepo --title ('Media ' + $today) --notes ($Label + ' weekly ' + $today) 2>&1 | ForEach-Object { $l = Format-NativeLine $_; if ($null -ne $l) { Log ('gh: ' + $l) } } }
  $vidList = @(Get-ChildItem $videoDir -Filter '*.mp4' | ForEach-Object { $_.FullName })
  & gh release upload $relTag --repo $ghRepo --clobber @vidList 2>&1 | ForEach-Object { $l = Format-NativeLine $_; if ($null -ne $l) { Log ('gh: ' + $l) } }
  $ma = @($media + @('--html', $target, '--repo', $repo, '--date', $today, '--inject-only', '--media-base', $mediaBase, '--brand-config', $brandCfg))
  & $ovpy @ma 2>&1 | ForEach-Object { $l = Format-NativeLine $_; if ($null -ne $l) { Log ('media: ' + $l) } }
} else {
  $ma = @($media + @('--html', $target, '--repo', $repo, '--date', $today, '--inject-only', '--brand-config', $brandCfg))
  & $ovpy @ma 2>&1 | ForEach-Object { $l = Format-NativeLine $_; if ($null -ne $l) { Log ('media: ' + $l) } }
}

Get-ChildItem (Join-Path $repo 'video') -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -Skip 14 | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# --- prune audio cũ: giữ N bản tin mới nhất (mp3 PHẢI ở trên Pages để phát mobile);
#     số cũ hơn -> xóa mp3 + gỡ player/ẩn nút đọc khỏi HTML (nội dung bài giữ nguyên).
#     UAT chỉ dry-run (không xóa). N từ brand.json audio_keep (mặc định 54 ~ 1 năm).
$keepN = if ($cfg.audio_keep) { [int]$cfg.audio_keep } else { 54 }
$prunepy = Join-Path $tool 'prune_audio.py'
$pruneArgs = @($prunepy, '--repo', $repo, '--keep', $keepN); if ($Uat) { $pruneArgs += '--dry-run' }
& $ovpy @pruneArgs 2>&1 | ForEach-Object { Log ('prune: ' + $_) }

# Truyền bản chụp xuống: build-index lấy `script_url` từ đó để dựng form đăng ký.
# Thiếu nó thì form BIẾN MẤT khỏi trang mà không lỗi gì — đã dính 05/09/2026.
$biArgs = @{ Repo = $repo }
if ($Config) { $biArgs['Config'] = $Config }
& (Join-Path $brandDir 'build-index.ps1') @biArgs 2>&1 | ForEach-Object { Log ('index: ' + $_) }

if (-not $Uat) {
  Set-Location $repo
  git add -A 2>&1 | ForEach-Object { Log ('git: ' + $_) }
  $gitAuthor = Get-GitAuthorArgs $cfg
  git @gitAuthor commit -m ($Label + ' News weekly - ' + $today + ' (' + $weekLabel + ')') 2>&1 | ForEach-Object { Log ('git: ' + $_) }
  git push origin main 2>&1 | ForEach-Object { Log ('git: ' + $_) }
  if ($LASTEXITCODE -ne 0) { Log 'ERROR: git push failed.'; Log '=== run failed ==='; exit 1 }
  # Bí mật email nay ở kho secret của máy (biến EMAIL_CONFIG, nạp bởi Set-SecretEnv). Cổng cũ gác
  # bằng file trong thư mục brand — file đó đã dời đi, nên cổng luôn đóng và newsletter
  # bị bỏ qua IM LẶNG. Không ai biết tuần đó thư không gửi.
  $mailCfg = if ($env:EMAIL_CONFIG) { $env:EMAIL_CONFIG } else { Join-Path $brandDir 'email-config.json' }
  if (-not (Test-Path $mailCfg)) { Log ('Newsletter: BO QUA - khong thay cau hinh ' + $mailCfg) }
  else {
    Log 'Newsletter: sending ...'
    & $ovpy (Join-Path $brandDir 'send_newsletter.py') 2>&1 | ForEach-Object { $l = Format-NativeLine $_; if ($null -ne $l) { Log ('mail: ' + $l) } }
  }
}

# Facebook (hẹn 9h) + Excel log (best-effort)
$fbStatus = 'skip'
try {
  $fbText = ''
  try { $sc2 = Get-Content $sidecarPath -Raw -Encoding UTF8 | ConvertFrom-Json; $fbText = [string]$sc2.facebook_post } catch {}
  $fbCfg = if ($env:FB_CONFIG) { $env:FB_CONFIG } else { Join-Path $brandDir 'facebook_config.json' }
  if (-not (Test-Path $fbCfg)) { $fbStatus = 'chưa thiết lập token'; Log 'FB: chưa có facebook_config.json.' }
  elseif (-not $fbText) { $fbStatus = 'thiếu facebook_post'; Log 'FB: sidecar không có facebook_post.' }
  else {
    $fbFile = Join-Path $logdir 'fb-post.txt'
    [System.IO.File]::WriteAllText($fbFile, $fbText, $utf8)
    # ── v3 (18/08/2026): Reel là object DUY NHẤT trên Facebook, mang TOÀN VĂN bài blog.
    # BỎ video dài khỏi FB: Meta gộp MỌI video của Page thành Reel, KHÔNG có opt-out, nên
    # video ngang 16:9 lọt vào thư viện Reel và làm hỏng bố cục. Video dài sống ở YouTube;
    # link của nó nằm ở COMMENT. ĐĂNG NGAY (bỏ hẹn giờ) vì bài hẹn giờ chưa tồn tại để comment.
    $fbArgs = @((Join-Path $tool 'post_facebook.py'), '--tool', $brandDir, '--message-file', $fbFile, '--no-link', '--reel-main')
    # Bài chữ riêng: TẮT mặc định từ 05/09/2026 (khoá vắng mặt = tắt).
    # Bật lại = thêm "fb_text_post": true vào brand.json.
    if (-not $cfg.fb_text_post) { $fbArgs += '--no-text-post' }
    $cmtFile = Join-Path $logdir 'fb-comment.txt'
    $cmtLines = @('📖 Bản tin đầy đủ: ' + $pageUrlPub)
    if ($ytRecap) { $cmtLines += '🎬 Video recap đầy đủ: https://youtu.be/' + $ytRecap }
    [System.IO.File]::WriteAllText($cmtFile, ($cmtLines -join "`n"), $utf8)
    $fbArgs += @('--comment-file', $cmtFile)
    if (Test-Path $shortFile) { $fbArgs += @('--reel', $shortFile) }
    # Caption Reel riêng do AI viết. $sc2 gán trong try ở trên nên có thể null -> phải guard.
    $fbReelText = if ($sc2) { [string]$sc2.facebook_reel } else { '' }
    if ($fbReelText) {
      $fbReelFile = Join-Path $logdir 'fb-reel.txt'
      [System.IO.File]::WriteAllText($fbReelFile, $fbReelText, $utf8)
      $fbArgs += @('--reel-desc-file', $fbReelFile)
    }
    if ($Uat) { $fbArgs += '--dry-run' }
    $fbout = & $syspy @fbArgs 2>&1 | Out-String
    $fbout -split "`r?`n" | Where-Object { $_ } | ForEach-Object { Log ('fb: ' + $_) }
    $mm = [regex]::Match($fbout, 'STATUS=(.+)')
    if ($Uat) { $fbStatus = 'UAT dry-run' } elseif ($mm.Success) { $fbStatus = $mm.Groups[1].Value.Trim() } else { $fbStatus = 'lỗi (không có STATUS)' }
  }
} catch { $fbStatus = 'lỗi: ' + $_; Log ('FB: exception ' + $_) }

# ── Hậu kiểm ĐỘ PHỦ (read-only, best-effort) — xem chú thích ở check_fb_reach.py.
# Soi bài của các lần chạy TRƯỚC; bài vừa hẹn chưa publish nên không nằm trong tầm đo.
try {
  $rcArgs = @((Join-Path $tool 'check_fb_reach.py'), '--tool', $brandDir, '--label', ('Weekly ' + $Label), '--hours', '192')
  $rcOut = & $syspy @rcArgs 2>&1 | Out-String
  $rcOut -split "`r?`n" | Where-Object { $_ } | ForEach-Object { Log $_ }
} catch { Log ('reach: exception ' + $_) }

try {
  $rowFile = Join-Path $logdir 'xlsx-row.json'
  ([ordered]@{
    time_start = $startTime; time_end = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    status = $(if ($Uat) { 'UAT' } else { 'success' })
    script = 'run-weekly-news.ps1'; title = $recapTitle
    video_location = $recapFile; post = $fbText; note = 'FB: ' + $fbStatus
  } | ConvertTo-Json -Depth 4) | Set-Content -Path $rowFile -Encoding UTF8
  $sheet = $(if ($Uat) { 'UAT Weekly ' + $Label } else { 'Weekly ' + $Label })
  & $syspy (Join-Path $tool 'append_excel_log.py') --sheet $sheet --row $rowFile --log $log 2>&1 | ForEach-Object { Log ('xlsx: ' + $_) }
} catch { Log ('xlsx: exception ' + $_) }

Log '=== run complete ==='
exit 0
