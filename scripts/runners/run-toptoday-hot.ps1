# Daily HOT TOP-1 deep-dive runner (engine dùng chung) — dựng 2 video, rồi publish.
#
# Cấu hình: bản chụp `-Config` (campaign.md) — không có thì <trạm>/<kênh>/brand.json.
# Code = thư mục chứa file này (`<repo>/scripts/runners`); trạm/kênh phân giải ở brand-paths.ps1.
#   AI:   run-toptoday-hot.ps1 -Brand ai   -Publish
#   Data: run-toptoday-hot.ps1 -Brand data -Publish
#   -SkipResearch : tái dùng <date>-top.json sẵn có (chỉ render lại).
#   -Uat          : chế độ test an toàn (không upload YouTube, FB dry-run, Excel sheet UAT).
#   -Register     : (chỉ Windows) tạo Task Scheduler (-TaskName, -Time HH:mm, -EveryDays N)
#                   rồi thoát. macOS: `scripts/runners/install_launchd.py`.
#   -IgnoreCadence: bỏ qua nhịp 2 ngày/lần của campaign.md (chạy tay một ngày lệch nhịp).
# Nhịp: runner tự kiểm `runtime.cadence_days/cadence_anchor` (Test-Cadence) — ngày lệch nhịp
# thoát 0 với dòng "skip parity" (launchd trên macOS gọi mỗi ngày).
# Dựng video: `video-studio render --project topstory` (repo agent-video-studio, cài trong venv
# giọng) với spec do `topstory_spec.py` ghép từ -top.json + bản chụp cấu hình.
# Exit: 0 ok / 1 fail / 3 thiếu công cụ render / 4 hết hạn mức / 5 môi trường render kẹt
#       (Invoke-RenderPreflight, P1-24 — DỪNG trước nghiên cứu/TTS, khởi động lại máy rồi chạy lại);
#       rào render cũng dừng với 1 (phép thử hỏng) / 2 (cấu hình render sai) / 3 (thiếu công cụ).
param(
  [string]$Brand = 'ai',
  [string]$Date  = (Get-Date -Format 'yyyy-MM-dd'),
  [string]$Profile = '',
  [switch]$SkipResearch,
  [switch]$Publish,
  [switch]$Uat,
  [switch]$Register,
  [string]$TaskName = '',
  [string]$Time = '01:00',
  [int]$EveryDays = 2,  # tần suất Task Scheduler: 2 = chạy 2 ngày/lần (daily news ai+data từ 2026-06-26)
  [switch]$IgnoreCadence,
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
$cfg   = Get-Cfg -Config $Config -BrandDir $brandDir
$Label = $cfg.label

$self    = Join-Path $engine 'run-toptoday-hot.ps1'
# Script nghiên cứu last30days: L30_SCRIPT -> thư mục plugin của Claude (Find-Last30Days).
$l30     = Find-Last30Days
$ovpy    = Find-OmniVoicePython
# Python của repo — chạy `agent_call.py` (bước nghiên cứu đi theo `order`, P1-21).
$syspy   = Find-Python -Repo $script:RepoRoot
if (-not $syspy) { throw 'khong thay Python 3.10+ (dat MARKETING_STUDIO_PY).' }
# Bộ dựng video = `video-studio render --project topstory` qua python của trạm giọng — xem
# Invoke-TopstoryRender trong brand-paths.ps1 (spec ghép bởi engine/topstory_spec.py).
# Đường ra/log RIÊNG của chiến dịch khi có -Config; không có thì giữ đường cũ ở cấp
# kênh. Hai chiến dịch dùng CHUNG một thư mục log là ranh giới giữa chúng chỉ tồn tại
# trong tên file — đếm số của một chiến dịch phải lọc bằng mắt.
$outRoot = if ($cfg.out_root) { [string]$cfg.out_root } else { Join-Path $brandDir 'daily-out' }
# Prompt RIÊNG của chiến dịch khi có -Config. Hai chiến dịch cùng kênh (bản tin ngày
# và bản tin tuần) viết khác hẳn nhau, nên prompt không phải tài sản của kênh.
$prompt0 = if ($cfg.prompt_path) { [string]$cfg.prompt_path } else { Join-Path $brandDir 'toptoday-prompt.txt' }
# Thư viện nhạc nền (AI chọn theo nội dung). Manifest = nguồn chân lý.
# VOICE_BGM_DIR -> <trạm video>/assets/news-bgm. Runner truyền TÊN style trong spec và đặt
# VOICE_BGM_DIR cho engine. AI chỉ được chọn style CÓ mp3 (Get-BgmCatalog).
$bgmDir  = if (Get-EnvVar 'VOICE_BGM_DIR') { Resolve-Home (Get-EnvVar 'VOICE_BGM_DIR') } elseif ($VideoStation) { [System.IO.Path]::Combine($VideoStation, 'assets', 'news-bgm') } else { '' }
$bgmCat  = Get-BgmCatalog $bgmDir
$bgmLib  = $bgmCat.lib
$bgmListText = $bgmCat.text
$logdir  = if ($cfg.log_dir) { [string]$cfg.log_dir } else { Join-Path $brandDir 'logs' }
New-Item -ItemType Directory -Force -Path $logdir, $outRoot | Out-Null

# -Register: create a daily Task Scheduler entry and exit.
if ($Register) {
  if ($env:OS -ne 'Windows_NT') { Write-Host '-Register chi co tren Windows. macOS: scripts/runners/install_launchd.py'; exit 2 }
  if (-not $TaskName) { $TaskName = "Daily Hot $Label" }
  $pubFlag = ''; if ($Publish) { $pubFlag = ' -Publish' }
  # Trình PowerShell ĐANG chạy file này — không viết cứng tên chương trình.
  $psHost = (Get-Process -Id $PID).Path
  $action = "`"$psHost`" -NoProfile -ExecutionPolicy Bypass -File `"$self`" -Brand $Brand$pubFlag"
  schtasks /Create /TN $TaskName /TR $action /SC DAILY /MO $EveryDays /ST $Time /F
  Write-Host "Registered '$TaskName' every $EveryDays day(s) at $Time."
  exit $LASTEXITCODE
}

$log = Join-Path $logdir ("toptoday-$Label-" + $Date + '.log')
function Log($m) {
  $ts = Get-Date -Format 'HH:mm:ss'
  [System.IO.File]::AppendAllText($log, ($ts + '  ' + $m + "`r`n"), $utf8)
  Write-Host $m
}

$startTime = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
# Nhịp 2 ngày/lần: kiểm TRƯỚC mọi bước tốn tiền (claude -p, TTS, render).
$cad = Test-Cadence -Date $Date -Cfg $cfg
if ($cad -and -not $cad.run) {
  if ($IgnoreCadence) {
    Log ("cadence: $Date lech nhip (" + $cad.days + ' ngay/lan tu ' + $cad.anchor + ') - IgnoreCadence -> van chay')
  } else {
    Log ("skip parity: $Date khong phai ngay chay (" + $cad.days + ' ngay/lan tu ' + $cad.anchor + ', lech ' + $cad.offset + ')')
    Log '=== skipped (cadence) ==='
    exit 0
  }
}
Log "=== Daily HOT $Label (TOP-1 deep-dive) start ==="
# Nhạc nền: kiểm TRƯỚC mọi bước tốn tiền. Ép một style/file không có thì DỪNG ngay — chết ở
# bước dựng (sau `claude -p` + TTS) là kiểu hỏng đắt nhất. Style thiếu mp3 thì chỉ nhắc: AI
# không được chọn chúng (BGM_LIST chỉ gồm style có file).
$bgmEp = Resolve-ForcedBgm -Cfg $cfg -Dir $bgmDir -BrandDir $brandDir
if (-not $bgmEp.ok) { Log ("ERROR: bgm = '" + $cfg.bgm + "' khong co file mp3 (thu vien: " + $bgmDir + "). Sua campaign.md hoac chep mp3 vao thu vien."); Log '=== failed ==='; exit 1 }
if (@($bgmCat.missing).Count -gt 0) { Log ('WARN: thu vien nhac nen thieu mp3 cho: ' + (@($bgmCat.missing) -join ', ') + ' (' + $bgmDir + ')') }
# Rào render (P1-24): phép thử HyperFrames rẻ TRƯỚC nghiên cứu/TTS — kẹt thì dừng ngay (mã 5),
# không đốt agent + TTS + 40 phút. Xem Invoke-RenderPreflight trong brand-paths.ps1.
if (-not $ovpy) { Log 'ERROR: khong thay python cua tram giong (OMNIVOICE_PY / VOICE_STATION).'; Log '=== failed ==='; exit 3 }
$pf = Invoke-RenderPreflight -Python $ovpy -OnLine { param($l) Log $l }
# Bất cứ thứ gì không phải số nguyên (hàm hỏng giữa chừng dưới EAP Continue) là HỎNG: `exit $null`
# ra mã 0, tức tin ✅ cho một lượt đã dừng (review 02/10).
if ($pf -isnot [int]) { $pf = 1 }
if ($pf -ne 0) { Log '=== failed ==='; exit $pf }
$dispDate = ([datetime]$Date).ToString('dd/MM/yyyy')
$outDir   = Join-Path $outRoot $Date
New-Item -ItemType Directory -Force -Path (Join-Path $outDir 'clips') | Out-Null
$jsonPath = Join-Path $outDir ($Date + '-top.json')
Log ("Date $Date  brand $Brand  out $outDir")

$env:PYTHONIOENCODING = 'utf-8'
function JsonOk { (Test-Path $jsonPath) -and ((Get-Item $jsonPath).Length -ge 800) }

if ($SkipResearch -and (JsonOk)) {
  Log 'SkipResearch: reuse existing -top.json.'
} elseif (JsonOk) {
  Log '-top.json already exists (restarted run) - skip claude regen.'
} else {
  if (-not (Test-Path $prompt0)) { Log "ERROR: prompt missing: $prompt0"; exit 1 }
  if (-not ($l30 -and (Test-Path -LiteralPath $l30 -PathType Leaf))) {
    Log ('ERROR: khong thay script last30days (' + $l30 + '). Cai plugin Claude last30days hoac dat L30_SCRIPT.'); Log '=== failed ==='; exit 1
  }
  $tmpl = Get-Content $prompt0 -Raw -Encoding UTF8

  # Seen-list (chong trung) = N tieu de DA DANG gan nhat tu hot-news.json (nguon
  # BEN). KHONG dung folder daily-out vi bi don dinh ky -> mat tri nho chong trung.
  $hotJson = Join-Path (Join-Path $cfg.repo 'hot-today') 'hot-news.json'
  $seen = ''
  if (Test-Path $hotJson) {
    try {
      $hd = Get-Content $hotJson -Raw -Encoding UTF8 | ConvertFrom-Json
      @($hd.entries) | Where-Object { $_.date -and ($_.date -lt $Date) } | Select-Object -First 30 | ForEach-Object {
        $seen += "- ($($_.date)) " + $_.title + "`n"
      }
    } catch {}
  }
  if (-not $seen) {
    Get-ChildItem $outRoot -Directory -ErrorAction SilentlyContinue |
      Where-Object { $_.Name -lt $Date } | Sort-Object Name -Descending | Select-Object -First 5 | ForEach-Object {
        $jp = Join-Path $_.FullName ($_.Name + '-top.json')
        if (Test-Path $jp) { try { $sc = Get-Content $jp -Raw -Encoding UTF8 | ConvertFrom-Json; $h = [string]$sc.top_story.headline; if ($h) { $seen += "- ($($_.Name)) " + $h + "`n" } } catch {} }
      }
  }
  if (-not $seen) { $seen = '(chua co video Hot Today truoc do)' }
  Log ('Dedup seen-list: ' + (([regex]::Matches($seen, '(?m)^- ')).Count) + ' tin (tu hot-news.json)')

  # Hồ sơ TÁC GIẢ — dữ kiện về NGƯỜI, dùng chung mọi kênh. Dời từ `engine/assets/` về
  # trạm nội dung 07/09/2026: đó là NỘI DUNG, không phải code engine.
  # Đọc không được thì `{{VIEWPOINT}}` rỗng và bài mất phần chính kiến MÀ KHÔNG BÁO —
  # nên có dòng log ngay dưới để nhìn log là biết nó có tới nơi hay không.
  $vpFile = Join-Path $Station 'AUTHOR.md'
  $viewpoint = if (Test-Path $vpFile) { (Get-Content $vpFile -Raw -Encoding UTF8).Trim() } else { '' }
  Log ('Viewpoint digest: ' + $viewpoint.Length + ' chars')

  # Tập tool trừu tượng của agent_call (= allowlist cũ: WebSearch/WebFetch, Read, Write/Edit,
  # Bash(curl|python|<python giọng>)) — agent_call map sang cờ của từng engine.
  $tools = 'web,read,write,shell:curl,shell:python,shell:' + $ovpy
  $chk = Join-Path $engine 'check_duplicate.py'

  # Sinh tin + KIEM TRA TRUNG CUNG: trung tin da dang -> xoa & sinh lai (toi da 3 lan).
  # Khong sinh duoc tin KHAC -> abort, KHONG dang trung.
  $exclude = ''; $genOk = $false
  for ($att = 1; $att -le 3; $att++) {
    $seenFull = $seen.Trim(); if ($exclude) { $seenFull += "`n" + $exclude.TrimEnd() }
    $prompt = $tmpl.Replace('{{DISPLAY_DATE}}', $dispDate).Replace('{{JSON_PATH}}', $jsonPath).Replace('{{DIR}}', $outDir).Replace('{{DATE}}', $Date).Replace('{{L30_SCRIPT}}', $l30).Replace('{{YTDLP}}', $ovpy).Replace('{{SEEN_LIST}}', $seenFull).Replace('{{VIEWPOINT}}', $viewpoint).Replace('{{BGM_LIST}}', $bgmListText)

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

    $dup = (& $ovpy $chk $jsonPath $hotJson $Date 2>&1 | Out-String).Trim()
    Log ("Dedup check: $dup")
    if ($dup -match 'DUP=yes') {
      $m = [regex]::Match($dup, 'match=[0-9-]+\|(.+)$'); $bad = if ($m.Success) { $m.Groups[1].Value.Trim() } else { '' }
      Log ("Dedup: TRUNG tin da dang -> xoa & sinh lai. ($bad)")
      Remove-Item $jsonPath -Force -ErrorAction SilentlyContinue
      if ($bad) { $exclude += "- (TUYET DOI KHONG lap lai tin nay) " + $bad + "`n" }
      continue
    }
    $genOk = $true; break
  }
  if (-not $genOk) { Log 'ERROR: khong sinh duoc tin KHONG TRUNG sau 3 lan. Abort.'; Log '=== failed ==='; exit 1 }
}

if (-not (JsonOk)) { Log 'ERROR: -top.json missing/too small. Abort.'; Log '=== failed ==='; exit 1 }
Log ('JSON OK, ' + (Get-Item $jsonPath).Length + ' bytes')

# Thương hiệu (a, b, kicker, site, pronounce) đi TRONG spec — topstory_spec.py đọc từ bản chụp
# (campaign.md: identity + channel.yml: brand). Riêng màu nhấn: template topstory của
# video-studio 0.1.0 vẫn đọc biến TOPSTORY_ACCENTS.
Remove-Item Env:TOPSTORY_ACCENTS -ErrorAction SilentlyContinue
if ($cfg.topstory_accents) { $env:TOPSTORY_ACCENTS = $cfg.topstory_accents }

$env:HF_HUB_OFFLINE = '1'; $env:TRANSFORMERS_OFFLINE = '1'
# Nhạc nền (mix 10% dưới giọng đọc) — AI CHỌN theo nội dung (field "bgm" trong JSON), áp cho CẢ long + short.
# brand.json "bgm": tên-style/đường-dẫn = ÉP cố định; "" = TẮT; bỏ trống = theo lựa chọn của AI.
$bgmVol = if ($cfg.bgm_vol) { [string]$cfg.bgm_vol } else { '0.10' }
$bgmPath = Select-Bgm -Forced $bgmEp -Catalog $bgmCat -Pick (Read-BgmPick $jsonPath)
if ($bgmPath -and (Test-Path $bgmPath)) { Log ("BGM: " + (Split-Path $bgmPath -Leaf) + " @ " + $bgmVol) }
else { $bgmPath = ''; Log 'BGM: tat' }
Log 'Rendering deep-dive + short (my-voice) ...'
# --- Luan phien giong (2026-08-26) -------------------------------------------------
# Khong truyen -Profile thi tu chon theo series + ngay. Deterministic, khong can state:
# pick-voice.ps1 gan giong cho MOI series chay cung ngay sao cho khong cap nao qua
# giong nhau (my-voice va my-voice3 la cap sinh doi 0.91, khong bao gio dat canh).
# Truyen -Profile tuong minh thi van uu tien caller.
if (-not $Profile) {
  $vseries = if ($Brand -eq 'data') { 'data-hot' } else { 'ai-hot' }
  $Profile = & (Join-Path $PSScriptRoot 'pick-voice.ps1') -Series $vseries
  Log ("Voice: " + $Profile + "  (tu chon theo series ai/data-hot + ngay)")
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
if ((Test-Path $long) -and (Test-Path $short)) {
  Log ("DONE -> $long  +  $short")
  if ($Publish) {
    Log 'Publishing (YouTube + hot-today page + Facebook + Excel) ...'
    $pub = Join-Path $engine 'publish-hot-news.ps1'
    # MUST be a hashtable splat (named binding). An array splat @('-Brand',$Brand,...)
    # binds POSITIONALLY -> publish sees Brand='-Brand', Date='ai' and fails.
    # Lech gio hen Reel theo brand: 2 reel hen DUNG cung gio tren CUNG 1 page co the
    # bi FB rot 1 cai (link-post thi chiu duoc). AI 20:00 / Data 20:10.
    $fbAt = if ($Brand -eq 'data') { '20:10' } else { '20:00' }
    $pubArgs = @{ Brand = $Brand; Date = $Date; StartTime = $startTime; FbAt = $fbAt }
    if ($Uat) { $pubArgs['Uat'] = $true }
    # Truyền tiếp bản chụp xuống bước publish. Quên dòng này thì nửa trên của lượt chạy
    # dùng campaign.md còn nửa dưới quay về brand.json — hai nguồn cấu hình trong CÙNG
    # một lượt, và chỉ lộ khi hai bên bắt đầu lệch nhau.
    if ($Config) { $pubArgs['Config'] = $Config }
    & $pub @pubArgs 2>&1 | ForEach-Object { Log ('publish: ' + $_) }
    if ($LASTEXITCODE -ne 0) { Log "ERROR: publish failed (exit $LASTEXITCODE)"; Log '=== failed ==='; exit 1 }
  }
  Log '=== complete ==='
  exit 0
} else {
  Log ("ERROR: missing output (long=" + (Test-Path $long) + " short=" + (Test-Path $short) + ')')
  Log '=== failed ==='
  exit 1
}
