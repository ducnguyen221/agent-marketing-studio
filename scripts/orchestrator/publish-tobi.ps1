# ============================================================================
# CANH BAO 04/09/2026 — SCRIPT NAY CHUA CHAY DUOC TRONG REPO agent-marketing-studio.
# Do that, ba diem chan:
#   1. $root = $PSScriptRoot tro vao scripts\orchestrator\, nhung moi .py nam o
#      scripts\pipeline\ — moi loi goi Join-Path $root '<x>.py' deu tro hut.
#   2. Goi tobi_excel.py — repo chi co campaign_excel.py (mo hinh 5 sheet chua port).
#   3. $ASSET_ROOT tro vao kho cong ty, trong khi STATION la ~/.marketing/instances/.
# Bai AST-001 da dang bang cach chay TUNG BUOC bang tay, khong qua script nay.
# Ngoai ra script chua biet bo cuc thu muc moi (youtube/ atlas/ facebook/) — xem
# scripts/lib/post_paths.py. SUA HET BA DIEM TREN roi hay chay.
# ============================================================================
# publish-tobi.ps1 — Publish 1 bài tobi_post theo ĐÚNG thứ tự: Atlas → YouTube → Facebook → Result.
#
# Đọc meta.json + Excel Post row. Idempotent qua sidecar .sidecars\<post_id>.json
# (giống publish-hot-news.ps1): bước nào đã xong (blog_committed/video_id/fb_post_id) thì SKIP.
#
# CÁCH DÙNG (-Campaign BẮT BUỘC = tên folder NN_Ten, vd '01_Tobi_Posts'):
#   publish-tobi.ps1 -Campaign 01_Tobi_Posts -PostId P-0001
#   publish-tobi.ps1 -Campaign 01_Tobi_Posts -PostId P-0001 -Uat   # dry-run: in lệnh nhưng KHÔNG push/upload/đăng
#
# THỨ TỰ BẮT BUỘC:
#   (1) atlas.html -> Code\atlas\content\<category>\<slug>.html -> node generate-manifest.js -> git push -> blog_url
#   (2) youtube_upload.py video.mp4 (playlist "Học cùng Tobi") --desc-file youtube_desc.txt -> youtube_url
#   (3) post_facebook.py (message = fb_post.txt + blog_url đầu) --link <youtube_url> --at <giờ schedule>
#       (fb_desc.txt = caption ngắn cho nhánh reel nếu tool hỗ trợ)
#   (4) tobi_excel.py result : blog_url/youtube_url/fb_post_id/fb_permalink/fb_scheduled_at/published_at
#
# Exit: 0 ok / 1 fail. Fail sớm khi git push / upload trả exit!=0 (KHÔNG khi -Uat).
param(
  # Tên folder campaign (vd '01_Tobi_Posts') HOẶC campaign_code. BẮT BUỘC.
  [Parameter(Mandatory = $true)]
  [string]$Campaign,
  [Parameter(Mandatory = $true)]
  [string]$PostId,
  [switch]$Uat,
  [switch]$Now   # đăng Facebook NGAY (không hẹn lịch); mặc định hẹn theo --at/schedule_date
)

# --- fail-fast ---
$ErrorActionPreference = 'Stop'
try { chcp 65001 > $null } catch {}
$utf8 = New-Object System.Text.UTF8Encoding $false
$OutputEncoding = $utf8
try { [Console]::OutputEncoding = $utf8 } catch {}
$env:PYTHONIOENCODING = 'utf-8'; $env:PYTHONUTF8 = '1'
$env:PYTHONWARNINGS = 'ignore'   # chặn RequestsDependencyWarning (urllib3) ra stderr -> tránh EAP=Stop hiểu nhầm là lỗi

# --- đường dẫn (PIPELINE_CONTRACT.md) ---
$root      = $PSScriptRoot   # = 30_MARKETING\agent\scripts (folder chuẩn KPIM cho script quy trình)
$RUNTIME   = "$env:USERPROFILE\.video\tobi"   # secret + state runtime (facebook_config/.sidecars/logs) — KHÔNG sync OneDrive
$PY        = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
# Danh tinh commit khi day bai len atlas. Mac dinh trung tinh: repo public, khong nhung
# email that cua ai vao ma nguon. Doi bang bien moi truong neu muon ghi ten that.
$gitName   = if ($env:ATLAS_GIT_NAME)  { $env:ATLAS_GIT_NAME }  else { "atlas-bot" }
$gitEmail  = if ($env:ATLAS_GIT_EMAIL) { $env:ATLAS_GIT_EMAIL } else { "atlas-bot@users.noreply.github.com" }
# Xem ghi chu ROOT_DOCS o run-tobi-post.ps1 — cung luat phan giai.
if (-not $ROOT_DOCS) {
  $ROOT_DOCS = if ($env:MARKETING_STUDIO_DATA) { $env:MARKETING_STUDIO_DATA }
               else { Join-Path $env:USERPROFILE '.marketing' }
}
$CAMPAIGNS = Join-Path $ROOT_DOCS '31_CAMPAIGNS\01_CAMPAIGNS'
$ASSET_ROOT = Join-Path $ROOT_DOCS '32_PUBLIC_CONTENT\01_ACADEMIC_BLOG'
$ATLAS     = if ($env:ATLAS_REPO) { $env:ATLAS_REPO } else { "$env:USERPROFILE\Code\ducnguyen221.github.io\atlas" }   # monorepo: atlas là thư mục con; push repo ducnguyen221.github.io (cutover 2026-06)
$SITE      = 'https://ducnguyen.vn/atlas'   # atlas là PROJECT PAGE: phục vụ ở /atlas/ (KHÔNG phải root)
$PLAYLIST  = 'Học cùng Tobi'

$xl        = Join-Path $root 'tobi_excel.py'
$prepub    = Join-Path $root 'prepublish_check.py'   # GUARDRAIL liệt kê + kiểm asset/link
$reglinks  = Join-Path $root 'register_links.py'     # ghi link vào hồ sơ campaign md (Mục 13)
$rp        = Join-Path $root 'register_post.py'       # ghi tóm tắt+key-terms+REF content vào Mục 12
# Script tái dùng từ .news\engine (KHÔNG viết lại):
$ytpy      = "$env:USERPROFILE\.news\engine\youtube_upload.py"
$fbpy      = "$env:USERPROFILE\.news\engine\post_facebook.py"
# YouTube token + FB config theo kênh "Tobi" (reuse .news\ai theo DELIVERABLES §6).
$env:YT_TOKEN_PATH    = "$env:USERPROFILE\.news\ai\youtube_token.json"
$env:YT_CLIENT_SECRET = "$env:USERPROFILE\.news\ai\youtube_client_secret.json"
$FB_TOOL   = $RUNTIME  # facebook_config.json giữ ở .video\tobi (gitignored, KHÔNG sync OneDrive)

$logdir    = Join-Path $RUNTIME 'logs'
$sideDir   = Join-Path $RUNTIME '.sidecars'
New-Item -ItemType Directory -Force -Path $logdir, $sideDir | Out-Null
$today     = Get-Date -Format 'yyyy-MM-dd'
$log = Join-Path $logdir ("tobi-publish-$PostId-$today.log")
function Log($m) {
  $ts = Get-Date -Format 'HH:mm:ss'; $line = $ts + '  ' + $m
  [System.IO.File]::AppendAllText($log, ($line + "`r`n"), $utf8); Write-Host $line
}

# Resolve -Campaign -> @{ Dir = <folder>; Excel = <folder>\<NN_Ten>.xlsx }.
# 1) Khớp trực tiếp tên folder NN_Ten dưới $CAMPAIGNS.
# 2) Nếu không có, duyệt từng folder con, đọc Sheet Campaign (get-campaign) so campaign_code.
function Resolve-Campaign {
  param([Parameter(Mandatory = $true)][string]$Name)
  if (-not (Test-Path $CAMPAIGNS)) { throw "thiếu thư mục CAMPAIGNS: $CAMPAIGNS" }

  $direct = Join-Path $CAMPAIGNS $Name
  if (Test-Path $direct -PathType Container) {
    $excel = Join-Path $direct ($Name + '.xlsx')
    if (-not (Test-Path $excel)) { throw "campaign folder '$Name' không có Excel: $excel" }
    return @{ Dir = $direct; Excel = $excel }
  }

  Log "Không khớp tên folder '$Name' — dò theo campaign_code ..."
  $dirs = Get-ChildItem $CAMPAIGNS -Directory -ErrorAction SilentlyContinue
  foreach ($d in $dirs) {
    $cx = Join-Path $d.FullName ($d.Name + '.xlsx')
    if (-not (Test-Path $cx)) { continue }
    $out = & $PY $xl 'get-campaign' '--path' $cx | Out-String
    if ($LASTEXITCODE -ne 0) { Log "WARN: get-campaign lỗi cho $($d.Name) — bỏ qua."; continue }
    try { $form = $out | ConvertFrom-Json } catch { Log "WARN: get-campaign JSON hỏng cho $($d.Name) — bỏ qua."; continue }
    $code = [string]$form.campaign_code
    if ($code -and ($code -eq $Name)) {
      Log "Khớp campaign_code='$code' -> folder $($d.Name)"
      return @{ Dir = $d.FullName; Excel = $cx }
    }
  }
  throw "Không resolve được -Campaign '$Name' (không khớp tên folder lẫn campaign_code dưới $CAMPAIGNS)"
}

Log "=== tobi publish $PostId | campaign=$Campaign$(if ($Uat) { ' [UAT dry-run]' } else { '' }) ==="

# --- resolve campaign -> $CAMPAIGN_DIR + $EXCEL (per-campaign) ---
try {
  $resolved = Resolve-Campaign -Name $Campaign
} catch {
  Log ("ERROR: " + $_.Exception.Message); Log '=== failed ==='; exit 1
}
$CAMPAIGN_DIR = $resolved.Dir
$EXCEL        = $resolved.Excel
$campName     = Split-Path $CAMPAIGN_DIR -Leaf
$CAMPAIGN_MD  = Join-Path $CAMPAIGN_DIR ($campName + '.md')
Log "campaign dir = $CAMPAIGN_DIR | excel = $EXCEL"

# --- sidecar idempotent ---
$sidecar = Join-Path $sideDir ($PostId + '.json')
$state = [ordered]@{ blog_committed = $false; blog_url = ''; video_id = ''; youtube_url = ''; fb_post_id = ''; fb_permalink = ''; fb_scheduled_at = '' }
if (Test-Path $sidecar) {
  try {
    $sc = Get-Content $sidecar -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($k in @($state.Keys)) { if ($null -ne $sc.$k) { $state[$k] = $sc.$k } }
    Log "Sidecar đã có — sẽ SKIP các bước hoàn tất."
  } catch { Log "WARN: sidecar hỏng, bỏ qua: $_" }
}
function Save-Sidecar { ($state | ConvertTo-Json -Depth 4) | Set-Content -Path $sidecar -Encoding UTF8 }

try {
  # --- đọc meta.json (nguồn chân lý) ---
  # Xác định folder bài: ưu tiên Excel folder_path; fallback dò theo <post_id>_* trong các topic_group.
  $folder = ''
  # contract không có lệnh 'get row' -> dò folder bằng glob (post_id là tiền tố thư mục).
  $cand = Get-ChildItem $ASSET_ROOT -Directory -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like ($PostId + '_*') } | Select-Object -First 1
  if (-not $cand) { throw "Không tìm thấy folder bài cho $PostId dưới $ASSET_ROOT" }
  $folder = $cand.FullName
  Log "Folder: $folder"

  $meta = Join-Path $folder 'meta.json'
  if (-not (Test-Path $meta)) { throw "thiếu meta.json: $meta" }
  $m = Get-Content $meta -Raw -Encoding UTF8 | ConvertFrom-Json
  $slug = [string]$m.slug
  $category = [string]$m.category
  $title = [string]$m.title
  $schedDate = [string]$m.schedule_date
  if (-not $slug -or -not $category) { throw "meta.json thiếu slug/category" }

  # Số thứ tự bài (VC-001 -> 1) -> tiêu đề YouTube "Bài N: <title>".
  $num = 0; $nm = [regex]::Match($PostId, '(\d+)\s*$'); if ($nm.Success) { $num = [int]$nm.Groups[1].Value }
  $ytTitle = if ($num -gt 0) { "Bài ${num}: $title" } else { $title }

  # Lịch GIỜ đăng (mặc định, trừ -Now): YouTube publish 19:00 — FB 20:00 (giờ VN) của schedule_date.
  $ytPublishAt = ''; $fbWhen = ''
  if (-not $Now -and $schedDate -match '^\d{4}-\d{2}-\d{2}') {
    $d = $schedDate.Substring(0, 10)
    try {
      $ytDt = [datetime]::ParseExact("$d 19:00", 'yyyy-MM-dd HH:mm', $null)
      $ytPublishAt = $ytDt.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")  # RFC3339 UTC
      $fbDt = [datetime]::ParseExact("$d 20:00", 'yyyy-MM-dd HH:mm', $null)
      $fbWhen = [string]([DateTimeOffset]$fbDt).ToUnixTimeSeconds()
    } catch { Log "WARN: parse schedule_date '$schedDate' lỗi — sẽ đăng ngay." }
  }

  # ===== GUARDRAIL (0): liệt kê + kiểm ĐỦ ASSET trước khi publish =====
  Log "(0) Pre-publish asset check ..."
  & $PY $prepub --folder $folder --mode assets 2>&1 | ForEach-Object { Log ('check: ' + $_) }
  if ($LASTEXITCODE -ne 0) { throw "Pre-publish: THIẾU asset bắt buộc (xem checklist trên). Build đủ rồi publish lại." }

  $atlasHtml = Join-Path $folder 'atlas.html'
  $video = Join-Path $folder 'video.mp4'
  $fbPostTxt = Join-Path $folder 'fb_post.txt'       # message FB chính
  $ytDescTxt = Join-Path $folder 'youtube_desc.txt'  # mô tả YouTube
  $fbDescTxt = Join-Path $folder 'fb_desc.txt'       # caption ngắn (reel) — best-effort
  $fbCommentTxt = Join-Path $folder 'fb_comment.txt' # COMMENT dau — noi DUY NHAT chua link
  $infographic = Join-Path $folder 'thumbnail.png'   # cover/thumbnail (đổi từ infographic.png)

  # ============================================================ (1) ATLAS
  if ($state.blog_committed -and $state.blog_url) {
    Log "(1) Atlas: đã commit trước đó ($($state.blog_url)) — SKIP."
  } else {
    if (-not (Test-Path $atlasHtml)) { throw "thiếu atlas.html: $atlasHtml" }
    $destDir = Join-Path (Join-Path $ATLAS 'content') $category
    $dest = Join-Path $destDir ($slug + '.html')
    # URL pattern (xác nhận từ generate-manifest.js: card href = path = "content/<cat>/<slug>.html"):
    $blogUrl = "$SITE/content/$category/$slug.html"

    if ($Uat) {
      Log "(1) [UAT] copy '$atlasHtml' -> '$dest'"
      Log "(1) [UAT] node $ATLAS\scripts\generate-manifest.js"
      Log "(1) [UAT] git add/commit/push (atlas) — BỎ QUA"
      Log "(1) [UAT] blog_url = $blogUrl"
      $state.blog_url = $blogUrl
    } else {
      New-Item -ItemType Directory -Force -Path $destDir | Out-Null
      Copy-Item $atlasHtml $dest -Force
      Log "(1) copied -> $dest"
      # node + git in cảnh báo ra stderr (vd "LF will be replaced by CRLF") -> với EAP=Stop bị coi
      # là lỗi terminating dù exit 0. Chạy block dưới EAP=Continue, GATE bằng $LASTEXITCODE.
      Push-Location $ATLAS
      $savedEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
      try {
        & node (Join-Path $ATLAS 'scripts\generate-manifest.js') 2>&1 | ForEach-Object { Log ('manifest: ' + $_) }
        if ($LASTEXITCODE -ne 0) { throw "generate-manifest.js failed (exit $LASTEXITCODE)" }
        git add ('content/' + $category + '/' + $slug + '.html') 'data/manifest.json' 2>&1 | ForEach-Object { Log ('git: ' + $_) }
        if ($LASTEXITCODE -ne 0) { throw "git add failed (exit $LASTEXITCODE)" }
        git -c user.name=$gitName -c user.email=$gitEmail commit -m ("tobi: " + $PostId + " - " + $title) 2>&1 | ForEach-Object { Log ('git: ' + $_) }
        # commit có thể exit!=0 nếu không có thay đổi (re-run) — chấp nhận, vẫn push.
        git push origin main 2>&1 | ForEach-Object { Log ('git: ' + $_) }
        if ($LASTEXITCODE -ne 0) { throw "git push failed (exit $LASTEXITCODE)" }
      } finally { $ErrorActionPreference = $savedEAP; Pop-Location }
      $state.blog_committed = $true
      $state.blog_url = $blogUrl
      Save-Sidecar
      Log "(1) DONE blog_url = $blogUrl"
    }
  }

  # ============================================================ (2) YOUTUBE
  if ($state.video_id) {
    Log "(2) YouTube: đã upload ($($state.video_id)) — SKIP."
  } else {
    if (-not (Test-Path $video)) { throw "thiếu video.mp4: $video" }
    # Mô tả YouTube: ưu tiên file tách từ content.md (youtube_desc.txt). Nếu thiếu, dựng tối thiểu.
    $descFile = $ytDescTxt
    if (-not (Test-Path $descFile)) {
      $descFile = Join-Path $folder 'yt-desc.txt'
      # desc tối thiểu = title + blog_url (không hardcode secret).
      [System.IO.File]::WriteAllText($descFile, ($title + "`r`n`r`n" + $state.blog_url + "`r`n"), $utf8)
    }
    $thumb = if (Test-Path $infographic) { $infographic } else { '' }
    $ytArgs = @($ytpy, '--file', $video, '--title', $ytTitle, '--desc-file', $descFile, '--playlist', $PLAYLIST)
    if ($thumb) { $ytArgs += @('--thumbnail', $thumb) }
    if ($ytPublishAt) {
      $ytArgs += @('--publish-at', $ytPublishAt)
      Log "(2) YouTube SCHEDULED publish @ $ytPublishAt (UTC) = 19:00 VN $($schedDate.Substring(0,10)) — tự public đúng giờ."
    }
    if ($Uat) {
      Log ("(2) [UAT] $PY " + ($ytArgs -join ' ') + "  — BỎ QUA upload")
    } else {
      Log ("(2) uploading YouTube (playlist '$PLAYLIST') ...")
      $savedEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
      $out = & $PY @ytArgs 2>&1 | Out-String   # 2>&1: gom stderr-warning python vào output (EAP=Continue -> không throw)
      $ErrorActionPreference = $savedEAP
      if ($LASTEXITCODE -ne 0) { Log ('yt: ' + $out); throw "youtube_upload.py failed (exit $LASTEXITCODE)" }
      $out -split "`r?`n" | Where-Object { $_ } | ForEach-Object { Log ('yt: ' + $_) }
      $vm = [regex]::Match($out, 'VIDEO_ID=([A-Za-z0-9_-]+)')
      if (-not $vm.Success) { throw "(2) không bắt được VIDEO_ID từ output youtube_upload.py" }
      $state.video_id = $vm.Groups[1].Value
      $state.youtube_url = 'https://youtu.be/' + $state.video_id
      Save-Sidecar
      Log "(2) DONE youtube_url = $($state.youtube_url)"
    }
  }
  # ============================================================ (2c) EMBED -> ATLAS
  # Sau khi có youtube_url: rebuild atlas.html NHÚNG video YouTube + audio mp3 (giống ai-news),
  # copy mp3 sang atlas, re-push. (atlas-stage build trước đó chưa có youtube_url nên chưa nhúng.)
  if (-not $Uat -and $state.youtube_url -and $state.blog_committed) {
    $bbh = Join-Path $root 'build_blog_html.py'
    $blogMd2 = Join-Path $folder 'blog.md'
    $audioFile = Join-Path $folder 'audio.mp3'
    $audioSrc = "$slug.mp3"
    & $PY $bbh --blog-md $blogMd2 --meta $meta --infographic $infographic --youtube-url $state.youtube_url --audio-src $audioSrc --out $atlasHtml 2>&1 | ForEach-Object { Log ('embed: ' + $_) }
    if ($LASTEXITCODE -ne 0) { throw "build_blog_html (embed) failed (exit $LASTEXITCODE)" }
    $destDir = Join-Path (Join-Path $ATLAS 'content') $category
    Copy-Item $atlasHtml (Join-Path $destDir "$slug.html") -Force
    if (Test-Path $audioFile) { Copy-Item $audioFile (Join-Path $destDir "$slug.mp3") -Force }
    # Card thumbnail (JPG nhẹ ~50KB) cho dải "Mới nhất" trên trang chủ atlas (manifest tự bắt theo tên <slug>.jpg).
    if (Test-Path $infographic) {
      & $PY (Join-Path $root 'make_card_thumb.py') --src $infographic --out (Join-Path $destDir "$slug.jpg") 2>&1 | ForEach-Object { Log ('thumb: ' + $_) }
    }
    Push-Location $ATLAS
    $savedEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try {
      & node (Join-Path $ATLAS 'scripts\generate-manifest.js') 2>&1 | ForEach-Object { Log ('manifest: ' + $_) }
      git add ("content/$category/$slug.html") ("content/$category/$slug.mp3") ("content/$category/$slug.jpg") 'data/manifest.json' 2>&1 | ForEach-Object { Log ('git: ' + $_) }
      git -c user.name=$gitName -c user.email=$gitEmail commit -m ("tobi embed: " + $PostId) 2>&1 | ForEach-Object { Log ('git: ' + $_) }
      git push origin main 2>&1 | ForEach-Object { Log ('git: ' + $_) }
      if ($LASTEXITCODE -ne 0) { throw "git push (embed) failed (exit $LASTEXITCODE)" }
    } finally { $ErrorActionPreference = $savedEAP; Pop-Location }
    Log "(2c) DONE nhúng YouTube + audio vào atlas"
  }

  # URL YouTube cho bước FB (dry-run vẫn cần placeholder để soạn message).
  $ytUrl = if ($state.youtube_url) { $state.youtube_url } else { '(youtube_url sẽ có sau upload)' }

  # ===== Cập nhật LINK (blog_url + youtube_url) vào Excel + hồ sơ md TRƯỚC khi đăng FB =====
  # ===== rồi GUARDRAIL link: đủ link mới cho phép đăng Facebook =====
  if (-not $Uat) {
    $linkJson = Join-Path $folder 'result.json'
    ([ordered]@{
        post_id = $PostId; blog_url = $state.blog_url; youtube_url = $state.youtube_url
        fb_post_id = $state.fb_post_id; fb_permalink = $state.fb_permalink; fb_scheduled_at = ''
        published_at = ''; status = 'publishing'
      } | ConvertTo-Json -Depth 4) | Set-Content -Path $linkJson -Encoding UTF8
    & $PY $xl result --path $EXCEL --post-id $PostId --json $linkJson | ForEach-Object { Log ('link: ' + $_) }
    if ($LASTEXITCODE -ne 0) { throw "ghi link Result thất bại (exit $LASTEXITCODE)" }
    if (Test-Path $CAMPAIGN_MD) {
      & $PY $reglinks --campaign-md $CAMPAIGN_MD --post-id $PostId --blog-url $state.blog_url --youtube-url $state.youtube_url --date $today | ForEach-Object { Log ('link: ' + $_) }
    }
    Log "(2b) GUARDRAIL link trước FB ..."
    & $PY $prepub --xlsx $EXCEL --post-id $PostId --mode links 2>&1 | ForEach-Object { Log ('check: ' + $_) }
    if ($LASTEXITCODE -ne 0) { throw "Pre-FB: THIẾU link (blog_url/youtube_url). KHÔNG đăng Facebook khi chưa đủ link." }
  } else {
    Log "(2b) [UAT] sẽ ghi blog_url+youtube_url vào Excel+md rồi GUARDRAIL link trước khi đăng FB."
  }

  # ============================================================ (3) FACEBOOK
  if ($state.fb_post_id) {
    Log "(3) Facebook: đã đăng ($($state.fb_post_id)) — SKIP."
  } else {
    if (-not (Test-Path $fbPostTxt)) { throw "thiếu fb_post.txt: $fbPostTxt" }
    # LUAT 04/09/2026: THAN BAI KHONG CHUA URL NAO. Moi link di vao COMMENT DAU TIEN.
    # Ban cu o day CHU DONG CHEN '📖 Đọc blog:' + '🎬 Xem video:' vao sau dong dau neu
    # thay thieu link — tuc script dang tu tay dao nguoc dung cai luat vua doi. Da bo.
    $msg = (Get-Content $fbPostTxt -Raw -Encoding UTF8)
    $msgFile = Join-Path $folder 'fb-message.txt'
    [System.IO.File]::WriteAllText($msgFile, $msg, $utf8)

    # Comment dau tien = noi DUY NHAT chua link. Placeholder thay o DAY, khong thay o body.
    if (-not (Test-Path $fbCommentTxt)) { throw "thieu fb_comment.txt: $fbCommentTxt — bai khong co cho de dat link" }
    $cmt = (Get-Content $fbCommentTxt -Raw -Encoding UTF8).Replace('{{BLOG_URL}}', [string]$state.blog_url).Replace('{{YOUTUBE_URL}}', [string]$state.youtube_url)
    if ($cmt -notmatch 'https?://') { throw 'fb_comment.txt khong con URL nao sau khi thay placeholder — dung lai, dung dang bai mo coi' }
    $cmtFile = Join-Path $folder 'fb-comment.txt'
    [System.IO.File]::WriteAllText($cmtFile, $cmt, $utf8)

    # CONG FAIL-CLOSED truoc khi dang: dinh dang sai thi DUNG, vi bai da len Facebook
    # roi thi sua duoc nhung nguoi da nhin thay roi.
    $chk = Join-Path $root 'fb_format.py'
    if (Test-Path $chk) {
      $savedEAP2 = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
      $chkOut = & $PY $chk '--check' $msgFile '--comment' $cmtFile 2>&1 | Out-String
      $chkCode = $LASTEXITCODE; $ErrorActionPreference = $savedEAP2
      if ($chkCode -ne 0) { Log ('fb_format: ' + $chkOut); throw "fb_format.py --check bao do (exit $chkCode) — khong dang" }
    } else {
      Log '(3) CANH BAO: khong thay fb_format.py — dang MA KHONG kiem dinh dang.'
    }

    $fbArgs = @($fbpy, '--tool', $FB_TOOL, '--message-file', $msgFile, '--link', $ytUrl,
                '--comment-file', $cmtFile)
    if ($Now -or -not $fbWhen) {
      Log "(3) đăng FB NGAY (không hẹn lịch)."
    } else {
      $fbArgs += @('--when', $fbWhen)
      Log "(3) FB hẹn lịch 20:00 VN $($schedDate.Substring(0,10)) (when=$fbWhen) — sau YouTube 1 tiếng."
    }
    # Nhánh reel (best-effort): nếu có video short 9:16 + caption fb_desc.txt thì kèm.
    $reelVid = Get-ChildItem $folder -Filter '*-short*.mp4' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($reelVid -and (Test-Path $fbDescTxt)) {
      $fbArgs += @('--reel', $reelVid.FullName, '--reel-desc-file', $fbDescTxt)
    }
    if ($Uat) {
      Log ("(3) [UAT] $PY " + ($fbArgs -join ' ') + ' --dry-run')
      Log "(3) [UAT] message preview (than bai KHONG co URL — link nam o comment):"
      ($msg -split "`r?`n" | Select-Object -First 4) | ForEach-Object { Log ('    | ' + $_) }
    } else {
      Log "(3) đăng Facebook$(if ($Now -or -not $fbWhen) { ' NGAY' } else { ' (hẹn 20:00 VN ' + $schedDate.Substring(0, 10) + ')' }) ..."
      $savedEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
      $out = & $PY @fbArgs 2>&1 | Out-String
      $ErrorActionPreference = $savedEAP
      if ($LASTEXITCODE -ne 0) { Log ('fb: ' + $out); throw "post_facebook.py failed (exit $LASTEXITCODE)" }
      $out -split "`r?`n" | Where-Object { $_ } | ForEach-Object { Log ('fb: ' + $_) }
      # post_facebook.py emit FB_POST_ID=<id|-> FB_REEL_ID=<id|-> STATUS=<scheduled@iso|published|error:...>
      $fm = [regex]::Match($out, 'FB_POST_ID=([0-9_]+)')
      if ($fm.Success -and $fm.Groups[1].Value -ne '-') { $state.fb_post_id = $fm.Groups[1].Value }
      $pm = [regex]::Match($out, 'PERMALINK=(\S+)')   # nếu tool có in permalink thì ưu tiên dùng.
      if ($pm.Success -and $pm.Groups[1].Value -ne '-') {
        $state.fb_permalink = $pm.Groups[1].Value
      } elseif ($state.fb_post_id) {
        # post_facebook.py không in permalink -> suy ra từ fb_post_id (fb_engagement.py sẽ ghi đè permalink_url chuẩn sau).
        $state.fb_permalink = 'https://www.facebook.com/' + $state.fb_post_id
      }
      # Engine hien CHI dinh comment vao REEL, chua dinh vao bai thuong (post_facebook.py:612
      # gate tren reel_id). Neu comment khong len thi bai vua khong co link trong than,
      # vua khong co link o comment — te hon ca truoc khi doi luat. Nen BAT O DAY.
      $cm = [regex]::Match($out, 'FB_COMMENT_ID=(\S+)')
      $cmtId = if ($cm.Success) { $cm.Groups[1].Value } else { '-' }
      if ($cmtId -eq '-') {
        throw "FB da dang (post_id=$($state.fb_post_id)) NHUNG COMMENT KHONG LEN. Bai dang khong co link o dau ca. Vao Facebook dan comment bang tay tu $cmtFile, roi sua engine de no comment duoc ca bai thuong."
      }
      $state.fb_comment_id = $cmtId
      $sm = [regex]::Match($out, 'STATUS=(.+)')
      if ($sm.Success) {
        $st = $sm.Groups[1].Value.Trim()
        $am = [regex]::Match($st, 'scheduled@(\S+)'); if ($am.Success) { $state.fb_scheduled_at = $am.Groups[1].Value }
      }
      Save-Sidecar
      Log "(3) DONE fb_post_id = $($state.fb_post_id)  fb_comment_id = $($state.fb_comment_id)  fb_permalink = $($state.fb_permalink)  scheduled_at = $($state.fb_scheduled_at)"
    }
  }

  # ============================================================ (4) RESULT
  $publishedAt = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ss')
  $resJson = Join-Path $folder 'result.json'
  ([ordered]@{
      post_id = $PostId; blog_url = $state.blog_url; youtube_url = $state.youtube_url
      fb_post_id = $state.fb_post_id; fb_permalink = $state.fb_permalink; fb_scheduled_at = $state.fb_scheduled_at
      published_at = $publishedAt; status = $(if ($Uat) { 'uat' } else { 'published' })
    } | ConvertTo-Json -Depth 4) | Set-Content -Path $resJson -Encoding UTF8

  if ($Uat) {
    Log "(4) [UAT] $PY $xl result --path $EXCEL --post-id $PostId --json $resJson  — BỎ QUA ghi Excel"
  } else {
    Log "(4) ghi Result tab ..."
    & $PY $xl result --path $EXCEL --post-id $PostId --json $resJson | ForEach-Object { Log ('result: ' + $_) }
    if ($LASTEXITCODE -ne 0) { throw "tobi_excel.py result failed (exit $LASTEXITCODE)" }
    & $PY $xl set --path $EXCEL --post-id $PostId --field status --value published | ForEach-Object { Log ('result: ' + $_) }
    if ($LASTEXITCODE -ne 0) { throw "tobi_excel.py set status failed (exit $LASTEXITCODE)" }
    # ghi đủ link (kèm fb_permalink) vào hồ sơ campaign md (Mục 13)
    $relFolder = $folder.Replace($ASSET_ROOT, '').TrimStart('\', '/').Replace('\', '/')
    $contentMd = Join-Path $folder 'content.md'
    if (Test-Path $CAMPAIGN_MD) {
      & $PY $reglinks --campaign-md $CAMPAIGN_MD --post-id $PostId --blog-url $state.blog_url --youtube-url $state.youtube_url --fb-permalink $state.fb_permalink --date $today | ForEach-Object { Log ('md13: ' + $_) }
      # Mục 12: tóm tắt + key-terms + REFER tới content chi tiết (cho continuity bài sau)
      & $PY $rp --campaign-md $CAMPAIGN_MD --post-id $PostId --content-md $contentMd --meta $meta --title $title --folder $relFolder --date $today | ForEach-Object { Log ('md12: ' + $_) }
    }
    # (5) RÀ SOÁT content sau publish: content.md + blog.md tồn tại + đủ dày
    foreach ($cf in @('content.md', 'blog.md')) {
      $p = Join-Path $folder $cf
      if (-not (Test-Path $p)) { Log "AUDIT WARN: thiếu $cf" }
      elseif ((Get-Item $p).Length -lt 1500) { Log "AUDIT WARN: $cf mỏng (<1.5KB) — kiểm chiều sâu" }
      else { Log ("audit: $cf OK (" + [int]((Get-Item $p).Length / 1024) + 'KB)') }
    }
    # ===== BÁO CÁO BACKFILL (đã tự cập nhật gì, ở đâu) =====
    Log "===== BÁO CÁO BACKFILL ($PostId) — đã tự cập nhật: ====="
    Log "  [Excel Result] blog_url + youtube_url + fb_post_id + fb_permalink + status=published  ($EXCEL)"
    Log "  [md Mục 13 - Lịch sử đăng tải] blog/youtube/fb permalink + ngày  ($CAMPAIGN_MD)"
    Log "  [md Mục 12 - Lịch sử đã chốt] Tóm tắt + Key-terms + Hồ sơ(ref content) — cho continuity bài sau"
    Log "  [Atlas] content/$category/$slug.html (+ $slug.mp3) đã push — nhúng YouTube + audio"
    Log "  [Sidecar] $sidecar (idempotent)"
    Log "(4) DONE — published $PostId | blog=$($state.blog_url) | yt=$($state.youtube_url) | fb=$($state.fb_permalink)"
  }
}
catch {
  Log ("ERROR: " + $_.Exception.Message)
  Log '=== failed ==='
  exit 1
}

Log '=== complete ==='
exit 0
