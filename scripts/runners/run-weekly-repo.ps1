# Weekly "Repo Tuần Này" runner — CN tối: nghiên cứu 1 repo GitHub đáng giá tuần này
# (rubric adopt-repo), dựng video dài + short (template v2/escbase, my-voice), upload
# YouTube NGAY, hẹn Facebook 09:00 SÁNG THỨ 2, log Excel, ghi sổ chống-lặp repo.
#
#   run-weekly-repo.ps1 -Publish            # chạy đủ (mặc định cho task lịch)
#   run-weekly-repo.ps1 -Uat                # test: không upload YT, FB dry-run
#   run-weekly-repo.ps1 -SkipResearch       # tái dùng JSON sẵn có (chỉ render lại)
#   run-weekly-repo.ps1 -Register           # (chỉ Windows) tạo Task CN 20:00 qua wrapper NOTIFY_RUN
#
# Chống lặp: <kênh>/covered-repos.json = sổ VĨNH VIỄN các repo đã làm —
# check CỨNG theo repo.full_name sau khi sinh JSON; trùng -> xoá + sinh lại (3 lần).
# Exit: 0 ok / 1 fail.
param(
  [string]$Date  = (Get-Date -Format 'yyyy-MM-dd'),
  [string]$Profile = '',
  [switch]$SkipResearch,
  [switch]$Publish,
  [switch]$Uat,
  [switch]$Register,
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
$brandDir = Get-BrandDir 'repo'
$cfg      = Get-Cfg -Config $Config -BrandDir $brandDir
$self     = Join-Path $engine 'run-weekly-repo.ps1'
# Wrapper báo cáo của Task Scheduler KHÔNG nằm trong repo (hạ tầng của máy) — chỉ dùng ở
# -Register, và phải khai bằng NOTIFY_RUN. macOS dùng `scripts/runners/notify_run.py`.
$notify   = Get-EnvVar 'NOTIFY_RUN'
if ($notify) { $notify = Resolve-Home $notify }
# Script nghiên cứu last30days: L30_SCRIPT -> thư mục plugin của Claude (Find-Last30Days).
$l30      = Find-Last30Days
$ovpy     = Find-OmniVoicePython
$syspy    = Find-Python -Repo $script:RepoRoot
if (-not $syspy) { throw 'khong thay Python 3.10+ (dat MARKETING_STUDIO_PY).' }
# Bộ dựng video = `video-studio render --project topstory` qua python của trạm giọng — xem
# Invoke-TopstoryRender trong brand-paths.ps1 (spec ghép bởi engine/topstory_spec.py).
# Đường ra/log RIÊNG của chiến dịch khi có -Config; không có thì giữ đường cũ ở cấp
# kênh. Hai chiến dịch dùng CHUNG một thư mục log là ranh giới giữa chúng chỉ tồn tại
# trong tên file — đếm số của một chiến dịch phải lọc bằng mắt.
$outRoot  = if ($cfg.out_root) { [string]$cfg.out_root } else { Join-Path $brandDir 'weekly-out' }
# Prompt RIÊNG của chiến dịch khi có -Config. Hai chiến dịch cùng kênh (bản tin ngày
# và bản tin tuần) viết khác hẳn nhau, nên prompt không phải tài sản của kênh.
$prompt0  = if ($cfg.prompt_path) { [string]$cfg.prompt_path } else { Join-Path $brandDir 'repo-weekly-prompt.txt' }
$covered  = Join-Path $brandDir 'covered-repos.json'
$logdir   = if ($cfg.log_dir) { [string]$cfg.log_dir } else { Join-Path $brandDir 'logs' }
# VOICE_BGM_DIR -> <trạm video>/assets/news-bgm. Runner truyền TÊN style trong spec và đặt
# VOICE_BGM_DIR cho engine. AI chỉ được chọn style CÓ mp3 (Get-BgmCatalog).
$bgmDir   = if (Get-EnvVar 'VOICE_BGM_DIR') { Resolve-Home (Get-EnvVar 'VOICE_BGM_DIR') } elseif ($VideoStation) { [System.IO.Path]::Combine($VideoStation, 'assets', 'news-bgm') } else { '' }
$bgmCat   = Get-BgmCatalog $bgmDir
$bgmLib   = $bgmCat.lib
$bgmListText = $bgmCat.text
New-Item -ItemType Directory -Force -Path $logdir, $outRoot | Out-Null

# -Register: task CN 20:00 hàng tuần, QUA notify-run (rule CLAUDE.md §E2).
if ($Register) {
  if ($env:OS -ne 'Windows_NT') { Write-Host '-Register chi co tren Windows. macOS: scripts/runners/install_launchd.py'; exit 2 }
  if (-not ($notify -and (Test-Path -LiteralPath $notify))) { Write-Host '-Register: dat NOTIFY_RUN = duong toi wrapper bao cao cua Task Scheduler.'; exit 2 }
  $argStr = "-NoProfile -ExecutionPolicy Bypass -File `"$notify`" -Title `"Weekly Repo Sunday 8PM`" -Script `"$self`" -ScriptArgs `"-Publish`""
  # Trình PowerShell ĐANG chạy file này — không viết cứng tên chương trình.
  $act = New-ScheduledTaskAction -Execute ((Get-Process -Id $PID).Path) -Argument $argStr
  $trg = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At '20:00'
  $set = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 4) -MultipleInstances IgnoreNew
  Register-ScheduledTask -TaskName 'Weekly Repo Sunday 8PM' -Action $act -Trigger $trg -Settings $set `
    -Description 'Video "Repo Tuần Này": nghiên cứu 1 repo GitHub đáng giá -> YouTube ngay + FB hẹn 9h sáng T2. Qua notify-run (Telegram).' -Force | Out-Null
  Write-Host "Registered 'Weekly Repo Sunday 8PM' (CN 20:00, notify-run wrapped)."
  exit 0
}

$log = Join-Path $logdir ("repo-weekly-" + $Date + '.log')
function Log($m) {
  $ts = Get-Date -Format 'HH:mm:ss'
  [System.IO.File]::AppendAllText($log, ($ts + '  ' + $m + "`r`n"), $utf8)
  Write-Host $m
}

$startTime = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
Log '=== Weekly Repo Tuan Nay start ==='
Log ('secret: ' + $secretSrc + '  ' + $env:YT_TOKEN_PATH)
Log ('cfg: ' + $CfgSrc + $(if ($Config) { '  ' + $Config } else { '' }))   # nguon cau hinh: CONFIG = ban chup tu campaign.md, BRAND.JSON = duong cu
# Nhạc nền: kiểm TRƯỚC `claude -p` (rẻ) — ép một style/file không có thì DỪNG ngay.
$bgmEp = Resolve-ForcedBgm -Cfg $cfg -Dir $bgmDir -BrandDir $brandDir
if (-not $bgmEp.ok) { Log ("ERROR: bgm = '" + $cfg.bgm + "' khong co file mp3 (thu vien: " + $bgmDir + ")."); Log '=== failed ==='; exit 1 }
if (@($bgmCat.missing).Count -gt 0) { Log ('WARN: thu vien nhac nen thieu mp3 cho: ' + (@($bgmCat.missing) -join ', ') + ' (' + $bgmDir + ')') }
$dispDate = ([datetime]$Date).ToString('dd/MM/yyyy')
$outDir   = Join-Path $outRoot $Date
New-Item -ItemType Directory -Force -Path (Join-Path $outDir 'clips') | Out-Null
$jsonPath = Join-Path $outDir ($Date + '-top.json')
Log ("Date $Date  out $outDir")

$env:PYTHONIOENCODING = 'utf-8'
function JsonOk { (Test-Path $jsonPath) -and ((Get-Item $jsonPath).Length -ge 800) }
function CoveredList {
  try { @((Get-Content $covered -Raw -Encoding UTF8 | ConvertFrom-Json).repos) } catch { @() }
}

# ---- BƯỚC 1: nghiên cứu (claude headless) + DEDUP CỨNG theo repo.full_name ----
if ($SkipResearch -and (JsonOk)) { Log 'SkipResearch: reuse JSON.' }
elseif (JsonOk) { Log 'JSON đã có (restart) - skip research.' }
else {
  if (-not ($l30 -and (Test-Path -LiteralPath $l30 -PathType Leaf))) {
    Log ('ERROR: khong thay script last30days (' + $l30 + '). Cai plugin Claude last30days hoac dat L30_SCRIPT.'); Log '=== failed ==='; exit 1
  }
  $tmpl = Get-Content $prompt0 -Raw -Encoding UTF8
  $seen = ''
  CoveredList | ForEach-Object { $seen += "- $($_.full_name) (đã làm $($_.date))`n" }
  if (-not $seen) { $seen = '(chưa có repo nào được làm trước đó)' }
  Log ('Dedup: ' + (@(CoveredList).Count) + ' repo trong sổ.')

  # Hồ sơ TÁC GIẢ — dữ kiện về NGƯỜI, dùng chung mọi kênh. Dời từ `engine/assets/` về
  # trạm nội dung 07/09/2026: đó là NỘI DUNG, không phải code engine.
  # Đọc không được thì `{{VIEWPOINT}}` rỗng và bài mất phần chính kiến MÀ KHÔNG BÁO —
  # nên có dòng log ngay dưới để nhìn log là biết nó có tới nơi hay không.
  $vpFile = Join-Path $Station 'AUTHOR.md'
  $viewpoint = if (Test-Path $vpFile) { (Get-Content $vpFile -Raw -Encoding UTF8).Trim() } else { '' }
  $dMinus60 = ((Get-Date $Date).AddDays(-60)).ToString('yyyy-MM-dd')
  # Tập tool trừu tượng của agent_call (= allowlist cũ) — map sang cờ từng engine (P1-21).
  $tools = 'web,read,write,shell:curl,shell:python,shell:' + $ovpy

  $exclude = ''; $genOk = $false
  for ($att = 1; $att -le 3; $att++) {
    $seenFull = $seen.Trim(); if ($exclude) { $seenFull += "`n" + $exclude.TrimEnd() }
    $prompt = $tmpl.Replace('{{DISPLAY_DATE}}', $dispDate).Replace('{{JSON_PATH}}', $jsonPath).Replace('{{DIR}}', $outDir).Replace('{{DATE}}', $Date).Replace('{{DATE_MINUS_60}}', $dMinus60).Replace('{{L30_SCRIPT}}', $l30).Replace('{{YTDLP}}', $ovpy).Replace('{{SEEN_LIST}}', $seenFull).Replace('{{VIEWPOINT}}', $viewpoint).Replace('{{BGM_LIST}}', $bgmListText)

    Log ("Nghien cuu qua agent_call (engine theo order) ... [lan $att/3]")
    $ac = Invoke-AgentCall -Python $syspy -Prompt $prompt -Tools $tools -Cwd $outDir `
      -Expect @($jsonPath + ':800') -OnLine { param($s) Log ('agent: ' + $s) }
    if ($ac.code -eq 4) {
      $mo = if ($ac.result -and $ac.result.resets_at) { [string]$ac.result.resets_at } else { '?' }
      Log ("HET HAN MUC moi engine trong order (mo lai $mo) - dung, khong dang."); Log '=== failed ==='; exit 4
    }
    if ($ac.code -ne 0 -or -not (JsonOk)) {
      # agent_call DA thu lai + lui het chuoi engine: chay lai ngay cung la lam lai mot viec vua hong.
      Log ("ERROR: agent_call ma $($ac.code) - khong sinh duoc JSON. Abort."); Log '=== failed ==='
      exit $(if ($ac.code -in 2, 3) { $ac.code } else { 1 })
    }

    # DEDUP CỨNG: full_name đã có trong sổ -> huỷ, sinh lại
    $rname = ''
    try { $rname = [string]((Get-Content $jsonPath -Raw -Encoding UTF8 | ConvertFrom-Json).repo.full_name) } catch {}
    if (-not $rname) { Log 'WARN: JSON thieu repo.full_name -> sinh lai.'; Remove-Item $jsonPath -Force; continue }
    $dup = @(CoveredList | Where-Object { $_.full_name -eq $rname })
    if ($dup.Count -gt 0) {
      Log ("Dedup: '$rname' DA LAM ($($dup[0].date)) -> xoa + sinh lai.")
      Remove-Item $jsonPath -Force
      $exclude += "- (TUYET DOI KHONG chon lai) $rname`n"
      continue
    }
    Log ("Repo chon: $rname (chua tung lam) - OK.")
    $genOk = $true; break
  }
  if (-not $genOk) { Log 'ERROR: 3 lan khong ra repo KHONG TRUNG. Abort.'; Log '=== failed ==='; exit 1 }
}

if (-not (JsonOk)) { Log 'ERROR: JSON missing. Abort.'; Log '=== failed ==='; exit 1 }
$brief = Get-Content $jsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
$repoName = [string]$brief.repo.full_name
$repoUrl  = [string]$brief.repo.url
$headline = [string]$brief.top_story.headline
Log ("JSON OK: $repoName | $headline")

# ---- BƯỚC 2: render long + short (video-studio render --project topstory) ----
# Thương hiệu đi TRONG spec (campaign.md: identity); màu nhấn vẫn qua TOPSTORY_ACCENTS
# (template topstory của video-studio 0.1.0 còn đọc biến đó).
Remove-Item Env:TOPSTORY_ACCENTS -ErrorAction SilentlyContinue
if ($cfg.topstory_accents) { $env:TOPSTORY_ACCENTS = $cfg.topstory_accents }
$env:HF_HUB_OFFLINE = '1'; $env:TRANSFORMERS_OFFLINE = '1'

$bgmVol = if ($cfg.bgm_vol) { [string]$cfg.bgm_vol } else { '0.10' }
$pick = ''; try { $pick = [string]$brief.bgm } catch {}
$bgmPath = Select-Bgm -Forced $bgmEp -Catalog $bgmCat -Pick $pick
if ($bgmPath -and (Test-Path $bgmPath)) { Log ("BGM: " + [System.IO.Path]::GetFileNameWithoutExtension($bgmPath) + " @ $bgmVol") }
else { $bgmPath = ''; Log 'BGM: tat' }

Log 'Rendering deep-dive + short ...'
# --- Luan phien giong (2026-08-26) -------------------------------------------------
# Khong truyen -Profile thi tu chon theo series + ngay. Deterministic, khong can state:
# pick-voice.ps1 gan giong cho MOI series chay cung ngay sao cho khong cap nao qua
# giong nhau (my-voice va my-voice3 la cap sinh doi 0.91, khong bao gio dat canh).
# Truyen -Profile tuong minh thi van uu tien caller.
if (-not $Profile) {
  $Profile = & (Join-Path $PSScriptRoot 'pick-voice.ps1') -Series 'repo-weekly'
  Log ("Voice: " + $Profile + "  (tu chon theo series repo-weekly + ngay)")
}
# ------------------------------------------------------------------------------------

$cfgFile = if ($Config) { $Config } else { Join-Path $brandDir 'brand.json' }
$rv = Invoke-TopstoryRender -Python $ovpy -JsonPath $jsonPath -ConfigFile $cfgFile -Date $Date `
        -OutDir $outDir -VoiceProfile $Profile -BgmPath $bgmPath -BgmDir $bgmDir -BgmVol $bgmVol `
        -OnLine { param($l) Log ('video: ' + $l) }
Log ('video-studio: ma ' + $rv.code + ' (' + (Get-VideoStudioCodeText $rv.code) + ')  spec ' + $rv.spec)
if ($rv.result) {
  foreach ($o in @($rv.result.outputs)) { Log ('video-studio: ' + $o.kind + ' ' + $o.duration + 's -> ' + $o.path) }
  if ($rv.result.engine) { Log ('video-studio: engine ' + ($rv.result.engine | ConvertTo-Json -Compress)) }
}
# Mã khác 0 là HỎNG dù trên đĩa có mp4: file cùng tên có thể là của một lượt trước.
if ($rv.code -ne 0) { Log ('ERROR: video-studio render that bai (ma ' + $rv.code + ').'); Log '=== failed ==='; exit 1 }

$long  = Join-Path $outDir ($Date + '-top.mp4')
$short = Join-Path $outDir ($Date + '-top-short.mp4')
if (-not ((Test-Path $long) -and (Test-Path $short))) {
  Log ("ERROR: missing output (long=" + (Test-Path $long) + " short=" + (Test-Path $short) + ')'); Log '=== failed ==='; exit 1
}
Log ("DONE render -> $long + $short")
if (-not $Publish) { Log '=== complete (no publish) ==='; exit 0 }

# ---- BƯỚC 3: publish — YT ngay + FB hẹn 09:00 sáng hôm sau (CN chạy -> T2 sáng) ----
# Con trỏ bí mật (ĐƯỜNG DẪN tới file trong kho secret của máy). Get-EnvVar: tiến trình ->
# registry User (chỉ Windows) -> <repo>/.env (embedded). Đọc registry TRẦN (bản cũ) thì macOS
# nhận chuỗi rỗng và lượt chết ở đây dù plist đã khai đủ biến.
$ytTokMoi = Get-EnvVar 'YT_TOKEN_PATH'
$ytCliMoi = Get-EnvVar 'YT_CLIENT_SECRET'
# FAIL-CLOSED. Đường lùi cũ trỏ vào thư mục kênh trong engine dùng chung — thư mục đó
# dời đi 05/09/2026, nên nhánh lùi chỉ sinh ra một đường chết rồi hỏng ở tận bước upload.
if (-not ($ytTokMoi -and (Test-Path $ytTokMoi))) { throw 'thieu YT_TOKEN_PATH (hoac file khong ton tai).' }
if (-not ($ytCliMoi -and (Test-Path $ytCliMoi))) { throw 'thieu YT_CLIENT_SECRET (hoac file khong ton tai).' }
$env:YT_TOKEN_PATH = $ytTokMoi; $secretSrc = 'NEW'
$env:YT_CLIENT_SECRET = $ytCliMoi
$sidecar = $jsonPath + '.published.json'
$vidLong = ''; $vidShort = ''; $fbDoneId = ''
if (Test-Path $sidecar) {
  try { $sc = Get-Content $sidecar -Raw -Encoding UTF8 | ConvertFrom-Json; $vidLong = [string]$sc.video_id; $vidShort = [string]$sc.short_id; $fbDoneId = [string]$sc.fb_post_id } catch {}
}
function Save-Sidecar { @{ video_id = $vidLong; short_id = $vidShort; fb_post_id = $fbDoneId; uploaded_at = (Get-Date).ToString('s') } | ConvertTo-Json | Set-Content -Path $sidecar -Encoding UTF8 }

$ddmmyyyy = ([datetime]$Date).ToString('dd/MM/yyyy')
$ytTitle      = $cfg.yt_title_prefix + ' | ' + $ddmmyyyy + ' | ' + $headline
$ytTitleShort = '⚡ 60 giây | ' + $headline
$descLong  = Join-Path $outDir 'desc-top.txt'
$descShort = Join-Path $outDir 'desc-top-short.txt'
# Tác giả đi qua cấu hình kênh (channel.yml brand.author) — không viết trong mã.
$descArgs = @('--top-json', $jsonPath, '--page-url', $repoUrl, '--site', 'github.com', '--label', 'Repo')
if ($cfg.author) { $descArgs += @('--author', [string]$cfg.author) }
# Thẻ YouTube: `yt_tags` của campaign.md; không khai thì bộ mặc định + tên trang của kênh.
$ytTags = if ($cfg.yt_tags) { [string]$cfg.yt_tags } elseif ($cfg.site_name) { 'AI,tin tức AI,' + [string]$cfg.site_name } else { 'AI,tin tức AI' }
# page-url = LINK REPO GITHUB -> mô tả YouTube dẫn thẳng tới repo
& $ovpy (Join-Path $engine 'build_hot_desc.py') @descArgs --out $descLong  2>&1 | ForEach-Object { Log ('desc: ' + $_) }
& $ovpy (Join-Path $engine 'build_hot_desc.py') @descArgs --out $descShort --shorts 2>&1 | ForEach-Object { Log ('desc: ' + $_) }

if ($Uat) { Log 'UAT: skip YouTube upload.' }
elseif (-not (Test-Path $env:YT_TOKEN_PATH)) { Log 'WARN: thieu youtube_token.json - bo qua upload.' }
elseif (-not $vidLong) {
  $ytpy = Join-Path $engine 'youtube_upload.py'
  Log ('YouTube: upload deep-dive (playlist "' + $cfg.yt_playlist + '") ...')
  $thumb = Join-Path $outDir 'thumb.jpg'
  & (Find-Ffmpeg) -y -loglevel error -ss 2 -i $long -frames:v 1 -q:v 2 $thumb 2>&1 | Out-Null
  if (-not (Test-Path $thumb)) { $thumb = '' }
  $out = & $ovpy $ytpy --file $long --title $ytTitle --desc-file $descLong --privacy public --playlist $cfg.yt_playlist --tags $ytTags --thumbnail $thumb 2>&1 | Out-String
  $out -split "`r?`n" | Where-Object { $_ } | ForEach-Object { Log ('yt: ' + $_) }
  $m = [regex]::Match($out, 'VIDEO_ID=([A-Za-z0-9_-]+)'); if ($m.Success) { $vidLong = $m.Groups[1].Value }
  Log 'YouTube: upload short ...'
  $out = & $ovpy $ytpy --file $short --title $ytTitleShort --desc-file $descShort --privacy public --playlist $cfg.yt_playlist --tags $ytTags --shorts 2>&1 | Out-String
  $out -split "`r?`n" | Where-Object { $_ } | ForEach-Object { Log ('yt: ' + $_) }
  $m = [regex]::Match($out, 'VIDEO_ID=([A-Za-z0-9_-]+)'); if ($m.Success) { $vidShort = $m.Groups[1].Value }
  if (-not $vidLong) { Log 'ERROR: upload deep-dive that bai.'; Log '=== failed ==='; exit 1 }
  Save-Sidecar
  Log ('PUBLISHED https://youtu.be/' + $vidLong)
  if ($vidShort) { Log ('PUBLISHED https://youtu.be/' + $vidShort) }
}

# Facebook: hẹn 09:00 kế tiếp (chạy CN tối -> đăng SÁNG THỨ 2). Link repo đã nằm trong bài (prompt bắt buộc).
$fbStatus = 'skip'
try {
  $fbText = [string]$brief.facebook_post
  # Một Page dùng chung mọi kênh -> con trỏ FB_CONFIG (không đường lùi viết trong mã).
  $fbCfg = Get-EnvVar 'FB_CONFIG'
  if ($fbCfg) { $fbCfg = Resolve-Home $fbCfg }
  if (-not ($fbCfg -and (Test-Path $fbCfg))) { throw ("thieu facebook_config: '" + $fbCfg + "' (dat FB_CONFIG).") }
  $env:FB_CONFIG = $fbCfg
  if (-not $fbText) { $fbStatus = 'thieu facebook_post'; Log 'FB: JSON khong co facebook_post.' }
  elseif ($fbDoneId -and -not $Uat) { $fbStatus = "da dang truoc do ($fbDoneId)"; Log ('FB: ' + $fbStatus) }
  else {
    $fbFile = Join-Path $outDir 'fb-post.txt'
    [System.IO.File]::WriteAllText($fbFile, $fbText, $utf8)
    # ── v3 (18/08/2026): Reel là object DUY NHẤT trên Facebook, mang TOÀN VĂN bài blog.
    # BỎ video dài khỏi FB: Meta gộp MỌI video của Page thành Reel, KHÔNG có opt-out, nên
    # video ngang 16:9 lọt vào thư viện Reel và làm hỏng bố cục. Video dài sống ở YouTube;
    # link của nó nằm ở COMMENT. ĐĂNG NGAY (bỏ hẹn giờ) vì bài hẹn giờ chưa tồn tại để comment.
    $fbArgs = @((Join-Path $engine 'post_facebook.py'), '--message-file', $fbFile, '--no-link', '--reel-main')
    # Bài chữ riêng: TẮT mặc định từ 05/09/2026 (khoá vắng mặt = tắt).
    # Bật lại = thêm "fb_text_post": true vào brand.json.
    if (-not $cfg.fb_text_post) { $fbArgs += '--no-text-post' }
    $cmtFile = Join-Path $outDir 'fb-comment.txt'
    # Trang chủ tin = thư mục CHA của `site_base` kênh (vd .../news/ai -> .../news/).
    $cmtLines = @()
    if ($cfg.site_base) {
      $sb = ([string]$cfg.site_base).TrimEnd('/')
      $cmtLines += '📖 Tin & bài đầy đủ: ' + $sb.Substring(0, $sb.LastIndexOf('/') + 1)
    }
    if ($repoUrl) { $cmtLines += '⭐ Repo: ' + $repoUrl }
    if ($vidLong) { $cmtLines += '🎬 Video đầy đủ: https://youtu.be/' + $vidLong }
    [System.IO.File]::WriteAllText($cmtFile, ($cmtLines -join "`n"), $utf8)
    $fbArgs += @('--comment-file', $cmtFile)
    if (Test-Path $short) { $fbArgs += @('--reel', $short) }
    # Caption Reel rieng do AI viet (truong facebook_reel). Thieu -> compose_reel() lo.
    $fbReelText = [string]$brief.facebook_reel
    if ($fbReelText) {
      $fbReelFile = Join-Path $outDir 'fb-reel.txt'
      [System.IO.File]::WriteAllText($fbReelFile, $fbReelText, $utf8)
      $fbArgs += @('--reel-desc-file', $fbReelFile)
    }
    if ($Uat) { $fbArgs += '--dry-run' }
    $fbout = & $syspy @fbArgs 2>&1 | Out-String
    $fbout -split "`r?`n" | Where-Object { $_ } | ForEach-Object { Log ('fb: ' + $_) }
    $mm = [regex]::Match($fbout, 'STATUS=(.+)'); $fbStatus = if ($Uat) { 'UAT dry-run' } elseif ($mm.Success) { $mm.Groups[1].Value.Trim() } else { 'loi (khong co STATUS)' }
    # ƯU TIÊN FB_REEL_ID — xem chú thích cùng chỗ trong publish-hot-news.ps1: bài chữ tắt
    # thì FB_POST_ID in "-", guard rỗng, re-run đăng Reel lần hai.
    $fbidm = [regex]::Match($fbout, 'FB_REEL_ID=([0-9_]+)')
    if (-not $fbidm.Success) { $fbidm = [regex]::Match($fbout, 'FB_POST_ID=([0-9_]+)') }
    if ((-not $Uat) -and $fbidm.Success) { $fbDoneId = $fbidm.Groups[1].Value; Save-Sidecar }
  }
} catch { $fbStatus = 'loi: ' + $_; Log ('FB: exception ' + $_) }
Log ('FB status: ' + $fbStatus + ' (hen ' + $cfg.fb_at + ' sang hom sau)')

# ---- Hau kiem DO PHU (read-only, best-effort) - xem chu thich o check_fb_reach.py.
# Soi bai cua cac lan chay TRUOC; bai vua hen chua publish nen khong nam trong tam do.
try {
  # Khong con `--tool`: cau hinh den tu FB_CONFIG (check_fb_reach.py: cfg_path).
  $rcArgs = @((Join-Path $engine 'check_fb_reach.py'), '--label', 'Weekly Repo', '--hours', '192')
  $rcOut = & $syspy @rcArgs 2>&1 | Out-String
  $rcOut -split "`r?`n" | Where-Object { $_ } | ForEach-Object { Log $_ }
} catch { Log ('reach: exception ' + $_) }

# ---- BƯỚC 4: GHI SỔ chống lặp (chỉ khi publish thật thành công) + Excel + dọn mp4 ----
if (-not $Uat) {
  try {
    $doc = Get-Content $covered -Raw -Encoding UTF8 | ConvertFrom-Json
    $entry = [ordered]@{ full_name = $repoName; url = $repoUrl; date = $Date; headline = $headline
                         video = $(if ($vidLong) { 'https://youtu.be/' + $vidLong } else { '' }) }
    $doc.repos = @($doc.repos) + @([pscustomobject]$entry)
    # runner-ups vào backlog tham khảo (không chặn dedup — chỉ repo ĐÃ LÀM mới chặn)
    $doc | ConvertTo-Json -Depth 5 | Set-Content -Path $covered -Encoding UTF8
    Log ("Covered log: +$repoName (tong " + (@($doc.repos).Count) + ' repo).')
  } catch { Log ('WARN: khong ghi duoc covered log: ' + $_) }

  try {
    $rowFile = Join-Path $outDir 'xlsx-row.json'
    ([ordered]@{ time_start = $startTime; time_end = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
                 status = 'success'; script = 'run-weekly-repo.ps1'; title = $ytTitle
                 video_location = $(if ($vidLong) { 'https://youtu.be/' + $vidLong } else { '(chua upload)' })
                 post = [string]$brief.facebook_post; note = "repo=$repoName; FB: $fbStatus" } |
      ConvertTo-Json -Depth 3) | Set-Content -Path $rowFile -Encoding UTF8
    & $syspy (Join-Path $engine 'append_excel_log.py') --sheet 'Weekly Repo' --row $rowFile --log $log 2>&1 | ForEach-Object { Log ('xlsx: ' + $_) }
  } catch { Log ('WARN: Excel log loi: ' + $_) }

  # dọn mp4 sau publish OK (YouTube là nơi lưu) — giữ json/desc/log để tra cứu
  if ($vidLong) {
    Remove-Item $long, $short -Force -ErrorAction SilentlyContinue
    Get-ChildItem (Join-Path $outDir 'clips') -File -ErrorAction SilentlyContinue | Remove-Item -Force
    Log 'Don mp4 + clips sau publish.'
  }
}

Log '=== complete ==='
exit 0
