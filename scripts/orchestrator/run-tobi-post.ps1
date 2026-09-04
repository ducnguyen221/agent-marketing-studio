# run-tobi-post.ps1 — Orchestrator pipeline "tobi_post" (COMPA / "Học cùng Tobi").
#
# MÔ HÌNH MỚI (v3): mỗi campaign = 1 folder + 1 Excel riêng.
# Resolve -Campaign -> folder CAMPAIGNS\<NN_Ten> + EXCEL = <folder>\<NN_Ten>.xlsx,
# rồi với mỗi Post row ĐỦ ĐIỀU KIỆN (đã duyệt + đúng status) chạy đúng 1 stage.
# Mỗi stage sinh nội dung gọi `claude -p` headless allowlist (theo khuôn
# run-toptoday-hot.ps1) + python gen/build.
#
# CÁCH DÙNG (-Campaign BẮT BUỘC; khớp tên folder NN_Ten HOẶC campaign_code):
#   run-tobi-post.ps1 -Campaign 01_Tobi_Posts        -Stage topics
#   run-tobi-post.ps1 -Campaign 01_Tobi_Posts        -Stage draft
#   run-tobi-post.ps1 -Campaign CMP-2026-06-AI       -Stage media     # khớp theo campaign_code
#   run-tobi-post.ps1 -Campaign 01_Tobi_Posts        -Stage atlas
#   run-tobi-post.ps1 -Campaign 01_Tobi_Posts        -Stage publish   # gọi publish-tobi.ps1 cho từng bài đã duyệt
#   run-tobi-post.ps1 -Campaign 01_Tobi_Posts        -Stage publish -Uat   # dry-run (KHÔNG push/upload/đăng)
#
# Gating (do tobi_excel.py list quyết định):
#   topics  : (không list — sinh chủ đề mới cho -Campaign)
#   draft   : approve_topic truthy & status=proposed
#   media   : approve_content truthy & status=drafted
#   atlas   : status=media_ready
#   publish : approve_final truthy & status in {atlas_ready, media_ready}
#
# Exit: 0 ok / 1 fail. Fail sớm khi lệnh python/native trả exit!=0.
param(
  # Tên folder campaign (vd '01_Tobi_Posts') HOẶC campaign_code (vd 'CMP-2026-06-AI'). BẮT BUỘC.
  [Parameter(Mandatory = $true)]
  [string]$Campaign,
  [Parameter(Mandatory = $true)]
  [ValidateSet('topics', 'draft', 'media', 'atlas', 'publish')]
  [string]$Stage,
  [switch]$Uat
)

# --- fail-fast (bài học: chained deploy phải fail-fast) ---
$ErrorActionPreference = 'Stop'
try { chcp 65001 > $null } catch {}
$utf8 = New-Object System.Text.UTF8Encoding $false
$OutputEncoding = $utf8
try { [Console]::OutputEncoding = $utf8 } catch {}
$env:PYTHONIOENCODING = 'utf-8'; $env:PYTHONUTF8 = '1'

# --- đường dẫn (theo PIPELINE_CONTRACT.md) ---
$root      = $PSScriptRoot   # = 30_MARKETING\agent\scripts (folder chuẩn KPIM cho script quy trình)
$RUNTIME   = 'C:\Users\DucNguyen\.video\tobi'   # secret + state runtime (facebook_config/.sidecars/logs/.tmp) — KHÔNG sync OneDrive
$PY        = 'C:\Users\DucNguyen\AppData\Local\Programs\Python\Python312\python.exe'
$OVPY      = 'C:\Users\DucNguyen\.tts\omnivoice\.venv\Scripts\python.exe'  # venv OmniVoice (soundfile+torch) cho mp3/mp4
# ROOT_DOCS: thu muc du lieu chien dich. KHONG hardcode duong dan may/to chuc —
# repo nay PUBLIC va nguoi khac clone ve se co duong dan khac.
# Thu tu phan giai: tham so -RootDocs > bien MARKETING_STUDIO_DATA > ~/.marketing
if (-not $ROOT_DOCS) {
  $ROOT_DOCS = if ($env:MARKETING_STUDIO_DATA) { $env:MARKETING_STUDIO_DATA }
               else { Join-Path $env:USERPROFILE '.marketing' }
}
$CAMPAIGNS = Join-Path $ROOT_DOCS '31_CAMPAIGNS\01_CAMPAIGNS'
$ASSET_ROOT = Join-Path $ROOT_DOCS '32_PUBLIC_CONTENT\01_ACADEMIC_BLOG'
# Registry: file ở 31_CAMPAIGNS (KHÔNG ở 01_CAMPAIGNS).
$REGISTRY  = Join-Path $ROOT_DOCS '31_CAMPAIGNS\31.02_campaign_registry.md'
$PROFILE   = 'my-voice'
$today     = Get-Date -Format 'yyyy-MM-dd'

$xl        = Join-Path $root 'tobi_excel.py'
$promptDir = Join-Path $root 'prompts'
$logdir    = Join-Path $RUNTIME 'logs'
New-Item -ItemType Directory -Force -Path $logdir | Out-Null
$log = Join-Path $logdir ("tobi-$Stage-$today.log")
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

  # (1) khớp tên folder trực tiếp.
  $direct = Join-Path $CAMPAIGNS $Name
  if (Test-Path $direct -PathType Container) {
    $excel = Join-Path $direct ($Name + '.xlsx')
    if (-not (Test-Path $excel)) { throw "campaign folder '$Name' không có Excel: $excel" }
    return @{ Dir = $direct; Excel = $excel }
  }

  # (2) duyệt các folder, đọc campaign_code qua get-campaign.
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

# Chạy python fail-fast: KHÔNG '2>&1' trên stderr; bắt $LASTEXITCODE.
function Invoke-Py {
  # -Exe: interpreter (mặc định $PY hệ thống; truyền $OVPY cho TTS/video cần venv OmniVoice).
  param([Parameter(Mandatory = $true)][string[]]$Args, [string]$Tag = 'py', [string]$Exe = $PY)
  Log ($Tag + '$ ' + ($Args -join ' '))
  & $Exe @Args | ForEach-Object { Log ($Tag + ': ' + $_) }
  if ($LASTEXITCODE -ne 0) { throw "$Tag failed (exit $LASTEXITCODE): $($Args -join ' ')" }
}
# Như trên nhưng GOM stdout để regex (vẫn fail-fast).
function Invoke-PyCapture {
  param([Parameter(Mandatory = $true)][string[]]$Args, [string]$Tag = 'py')
  Log ($Tag + '$ ' + ($Args -join ' '))
  $out = & $PY @Args | Out-String
  if ($LASTEXITCODE -ne 0) { Log ($Tag + ': ' + $out); throw "$Tag failed (exit $LASTEXITCODE)" }
  $out -split "`r?`n" | Where-Object { $_ } | ForEach-Object { Log ($Tag + ': ' + $_) }
  return $out
}

# claude -p headless allowlist (khuôn run-toptoday-hot.ps1): allow Read/WebSearch/Write/Bash.
# KHÔNG '2>&1' trên claude stderr theo cách làm hỏng exit — ta pipe & log từng dòng.
$claudeAllow = @('Read', 'WebSearch', 'WebFetch', 'Write', 'Edit', "Bash($($PY):*)", 'Bash(python:*)', 'Bash(node:*)')
function Invoke-Claude {
  param([Parameter(Mandatory = $true)][string]$Prompt, [string]$Tag = 'claude')
  Log "Launching claude -p (headless, allowlist) ..."
  # EAP=Continue quanh claude: PS 5.1 biến MỖI dòng stderr của native exe (vd thông báo
  # "Added ... Design MCP connector") thành NativeCommandError -> dưới EAP=Stop sẽ THROW giết stage.
  # Thành công verify bằng Test-Path file output ở mỗi stage, KHÔNG dựa exit code claude.
  $eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
  try {
    $Prompt | claude -p --allowedTools $claudeAllow 2>&1 | ForEach-Object { Log ($Tag + ': ' + $_) }
  }
  finally { $ErrorActionPreference = $eap }
}

function Read-Prompt {
  param([Parameter(Mandatory = $true)][string]$Name, [hashtable]$Vars)
  $p = Join-Path $promptDir $Name
  if (-not (Test-Path $p)) { throw "prompt thiếu: $p" }
  $t = Get-Content $p -Raw -Encoding UTF8
  if ($Vars) { foreach ($k in $Vars.Keys) { $t = $t.Replace('{{' + $k + '}}', [string]$Vars[$k]) } }
  return $t
}

# Lấy danh sách row đủ điều kiện cho stage qua tobi_excel.py list (in JSON).
# Excel ĐÃ là per-campaign nên không truyền --campaign nữa.
function Get-Rows {
  param([string]$ListStage)
  $a = @($xl, 'list', '--path', $EXCEL, '--stage', $ListStage)
  Log ('list$ ' + ($a -join ' '))
  $json = & $PY @a | Out-String
  if ($LASTEXITCODE -ne 0) { Log ('list: ' + $json); throw "tobi_excel.py list failed (exit $LASTEXITCODE)" }
  if (-not $json.Trim()) { return @() }
  try { $rows = $json | ConvertFrom-Json } catch { throw "list: JSON không parse được: $_" }
  if ($null -eq $rows) { return @() }
  return @($rows)
}

# Folder bài theo contract: ASSET_ROOT\<topic_group>\<post_id>_<slug>\
function Get-Folder {
  param($Row)
  if ($Row.folder_path) {
    $fp = [string]$Row.folder_path
    if ([System.IO.Path]::IsPathRooted($fp)) { return $fp }
    return (Join-Path $ASSET_ROOT $fp)
  }
  return (Join-Path (Join-Path $ASSET_ROOT $Row.topic_group) ("$($Row.post_id)_$($Row.slug)"))
}

# --- resolve campaign -> $CAMPAIGN_DIR + $EXCEL (per-campaign) ---
try {
  $resolved = Resolve-Campaign -Name $Campaign
} catch {
  Log ("ERROR: " + $_.Exception.Message); exit 1
}
$CAMPAIGN_DIR = $resolved.Dir
$EXCEL        = $resolved.Excel
$CAMPAIGN_MD  = Join-Path $CAMPAIGN_DIR ((Split-Path $CAMPAIGN_DIR -Leaf) + '.md')
$rp           = Join-Path $root 'register_post.py'
if (-not (Test-Path $EXCEL)) { Log "ERROR: thiếu Excel: $EXCEL"; exit 1 }

# PRIOR_POSTS: tóm tắt + key-terms + ref các bài đã chốt (Mục 12) -> bơm vào prompt topics/draft
# để bài mới LIÊN KẾT mạch + TRÁNH LẶP thuật ngữ đã viết.
$PRIOR_POSTS = '(chưa có bài nào chốt trước)'
if (Test-Path $CAMPAIGN_MD) {
  $pp = & $PY $rp '--campaign-md' $CAMPAIGN_MD '--list' 2>$null | Out-String
  if ($pp.Trim()) { $PRIOR_POSTS = $pp.Trim() }
}

# Nội dung style/template/knowledge/spec (đọc 1 LẦN) -> inject INLINE vào content-write-prompt.txt.
# (Bug cũ: các placeholder {{CONTENT_TEMPLATE}}/{{BLOG_STYLE}}/{{POST_STYLE}}/{{MULTICHANNEL_STYLE}}/
#  {{VIEWPOINT}}/{{CAMPAIGN_SPEC}}/{{KNOWLEDGE_INDEX}}/{{TOPIC}} bị bỏ trống -> claude phải tự đọc file bù.)
# CHỦ Ý: KHÔNG set {{BLOG_URL}}/{{YOUTUBE_URL}} -> giữ literal trong fb_post để publish thay link thật.
function Read-FileOrEmpty([string]$p) { if ($p -and (Test-Path $p)) { Get-Content $p -Raw -Encoding UTF8 } else { '' } }
$STYLE_DIR = Join-Path $ROOT_DOCS 'agent\output-styles'
$TPL_DIR   = Join-Path $ROOT_DOCS 'agent\templates'
$C_CONTENT_TEMPLATE   = Read-FileOrEmpty (Join-Path $TPL_DIR 'CONTENT_TEMPLATE.md')
$C_BLOG_STYLE         = Read-FileOrEmpty (Join-Path $STYLE_DIR 'compa-class-blog.md')
$C_POST_STYLE         = Read-FileOrEmpty (Join-Path $STYLE_DIR 'tobi-post.md')
$C_MULTICHANNEL_STYLE = Read-FileOrEmpty (Join-Path $STYLE_DIR 'multichannel-style.md')
# BUG DA VA 04/09: duong cu 'agent\knowledge\tobi-viewpoint.md' KHONG TON TAI, ma tham so
# nay la optional nen script IM LANG chay tiep => ca VC-001/002/003 deu viet voi chinh kien RONG
# ma khong ai biet. Nay FAIL-CLOSED: khong doc duoc thi DUNG.
# Bai khong co chinh kien thi khong phai bai chia se ca nhan — no la bai tong hop.
$VP_PATHS = @(
  (Join-Path $ROOT_DOCS 'profile\viewpoint.md'),
  (Join-Path $env:USERPROFILE '.marketing\profile\viewpoint.md'),
  (Join-Path $env:USERPROFILE '.news\engine\assets\tobi-viewpoint.md')
)
$C_VIEWPOINT = ''
foreach ($vp in $VP_PATHS) { if (Test-Path $vp) { $C_VIEWPOINT = Get-Content $vp -Raw -Encoding UTF8; break } }
if (-not $C_VIEWPOINT) {
  Write-Host 'LOI: khong tim thay ho so chinh kien (viewpoint) o bat ky duong nao:' -ForegroundColor Red
  $VP_PATHS | ForEach-Object { Write-Host "   - $_" }
  Write-Host 'Dat file do roi chay lai. KHONG viet bai voi chinh kien rong.' -ForegroundColor Red
  exit 1
}
$C_KNOWLEDGE_INDEX    = Read-FileOrEmpty (Join-Path $ROOT_DOCS 'agent\knowledge\KNOWLEDGE_MAP.md')
$C_CAMPAIGN_SPEC      = Read-FileOrEmpty $CAMPAIGN_MD

Log "=== tobi_post run | campaign=$Campaign | dir=$CAMPAIGN_DIR | stage=$Stage | excel=$EXCEL$(if ($Uat) { ' [UAT]' } else { '' }) ==="

try {
  switch ($Stage) {

    # ---------------------------------------------------------------- TOPICS
    # Sinh danh sách chủ đề cho 1 campaign → upsert từng Post row (status=proposed).
    'topics' {
      if (-not $Campaign) { throw "stage 'topics' cần -Campaign <id>" }
      # Đọc pillars từ campaign row (best-effort qua list publish? -> dùng set/get gián tiếp):
      # contract không có 'get campaign' → để claude tự đọc Excel/registry. Truyền pillars rỗng nếu chưa biết.
      $pillars = '01_powerbi, 02_fabric, 03_ai-agent, 04_career'
      $outJson = Join-Path $RUNTIME (".tmp\topics-$Campaign.json")
      New-Item -ItemType Directory -Force -Path (Split-Path $outJson) | Out-Null
      $prompt = Read-Prompt 'topic-gen-prompt.txt' @{
        CAMPAIGN    = $Campaign
        PILLARS     = $pillars
        EXCEL       = $EXCEL
        XL_SCRIPT   = $xl
        PY          = $PY
        OUT_JSON    = $outJson
        REGISTRY    = $REGISTRY
        PRIOR_POSTS = $PRIOR_POSTS
      }
      Invoke-Claude -Prompt $prompt -Tag 'topics'
      # claude được hướng dẫn tự gọi `tobi_excel.py upsert` từng row + cập nhật registry.
      # Nếu claude chỉ ghi OUT_JSON (mảng row), ta upsert dự phòng tại đây.
      if (Test-Path $outJson) {
        try {
          $rows = Get-Content $outJson -Raw -Encoding UTF8 | ConvertFrom-Json
          foreach ($r in @($rows)) {
            $rf = Join-Path $RUNTIME (".tmp\upsert-$($r.post_id).json")
            ($r | ConvertTo-Json -Depth 6) | Set-Content -Path $rf -Encoding UTF8
            Invoke-Py -Tag 'upsert' -Args @($xl, 'upsert', '--path', $EXCEL, '--json', $rf)
          }
          Log ("Upsert dự phòng: " + (@($rows).Count) + " Post row (proposed).")
        } catch { Log ("WARN: không đọc được $outJson ($_) — giả định claude đã upsert trực tiếp.") }
      } else {
        Log "Lưu ý: không thấy $outJson — giả định claude đã upsert Post row + cập nhật registry trực tiếp."
      }
    }

    # ---------------------------------------------------------------- DRAFT
    # approve_topic ✔ & status=proposed → folder bài + meta.json + content.md (instance
    # CONTENT_TEMPLATE) → gen_article.py tách content.md ra blog.md/fb_post.txt/youtube_desc.txt/fb_desc.txt.
    'draft' {
      $rows = Get-Rows 'draft'
      Log ("draft: " + $rows.Count + " bài đủ điều kiện.")
      foreach ($r in $rows) {
        $postId = [string]$r.post_id
        Log "--- draft $postId : $($r.topic_title)"
        $folder = Get-Folder $r
        New-Item -ItemType Directory -Force -Path $folder | Out-Null

        # category map (powerbi->bi, fabric->de, ai-agent->ai, career->strategy); meta override.
        $catMap = @{ 'powerbi' = 'bi'; 'fabric' = 'de'; 'ai-agent' = 'ai'; 'career' = 'strategy' }
        $cat = if ($r.category) { [string]$r.category } elseif ($catMap.ContainsKey([string]$r.pillar)) { $catMap[[string]$r.pillar] } else { 'other' }

        $meta = Join-Path $folder 'meta.json'
        ([ordered]@{
            post_id = $postId; campaign_id = [string]$r.campaign_id; title = [string]$r.topic_title
            slug = [string]$r.slug; pillar = [string]$r.pillar; topic_group = [string]$r.topic_group
            category = $cat; angle = [string]$r.angle; schedule_date = [string]$r.schedule_date
            hashtags = @(); blog_url = ''; youtube_url = ''
          } | ConvertTo-Json -Depth 6) | Set-Content -Path $meta -Encoding UTF8

        # 1) claude điền instance CONTENT_TEMPLATE (mục 1-7) -> content.md
        $contentMd = Join-Path $folder 'content.md'
        $topicStr = "Tiêu đề: $([string]$r.topic_title)`nGóc nhìn (angle): $([string]$r.angle)`nPillar: $([string]$r.pillar)`nYêu cầu chi tiết: $([string]$r.detail_prompt)"
        $vars = @{
          CONTENT_TEMPLATE   = $C_CONTENT_TEMPLATE
          BLOG_STYLE         = $C_BLOG_STYLE
          POST_STYLE         = $C_POST_STYLE
          MULTICHANNEL_STYLE = $C_MULTICHANNEL_STYLE
          VIEWPOINT          = $C_VIEWPOINT
          CAMPAIGN_SPEC      = $C_CAMPAIGN_SPEC
          KNOWLEDGE_INDEX    = $C_KNOWLEDGE_INDEX
          TOPIC              = $topicStr
          CONTENT_MD         = $contentMd
          PRIOR_POSTS        = $PRIOR_POSTS
          # KHÔNG set BLOG_URL/YOUTUBE_URL -> giữ literal cho publish thay sau.
        }
        Invoke-Claude -Prompt (Read-Prompt 'content-write-prompt.txt' $vars) -Tag 'content'
        if (-not (Test-Path $contentMd)) { throw "draft $postId : claude không sinh content.md" }

        # 2) tách content.md -> blog.md/fb_post.txt/youtube_desc.txt/fb_desc.txt
        Invoke-Py -Tag 'split' -Args @((Join-Path $root 'gen_article.py'),
          '--content-md', $contentMd, '--meta', $meta, '--out-dir', $folder)
        $blogMd = Join-Path $folder 'blog.md'
        if (-not (Test-Path $blogMd)) { throw "draft $postId : gen_article.py không tách được blog.md" }

        $relFolder = $folder.Replace($ASSET_ROOT, '').TrimStart('\', '/')
        Invoke-Py -Tag 'set' -Args @($xl, 'set', '--path', $EXCEL, '--post-id', $postId, '--field', 'content_md', '--value', (Join-Path $relFolder 'content.md'))
        Invoke-Py -Tag 'set' -Args @($xl, 'set', '--path', $EXCEL, '--post-id', $postId, '--field', 'blog_md', '--value', (Join-Path $relFolder 'blog.md'))
        # Các kênh phụ chỉ ghi cột nếu file tách ra thực sự tồn tại.
        if (Test-Path (Join-Path $folder 'fb_post.txt')) {
          Invoke-Py -Tag 'set' -Args @($xl, 'set', '--path', $EXCEL, '--post-id', $postId, '--field', 'fb_post', '--value', (Join-Path $relFolder 'fb_post.txt'))
        }
        if (Test-Path (Join-Path $folder 'youtube_desc.txt')) {
          Invoke-Py -Tag 'set' -Args @($xl, 'set', '--path', $EXCEL, '--post-id', $postId, '--field', 'youtube_desc', '--value', (Join-Path $relFolder 'youtube_desc.txt'))
        }
        if (Test-Path (Join-Path $folder 'fb_desc.txt')) {
          Invoke-Py -Tag 'set' -Args @($xl, 'set', '--path', $EXCEL, '--post-id', $postId, '--field', 'fb_desc', '--value', (Join-Path $relFolder 'fb_desc.txt'))
        }
        Invoke-Py -Tag 'set' -Args @($xl, 'set', '--path', $EXCEL, '--post-id', $postId, '--field', 'folder_path', '--value', $relFolder)
        Invoke-Py -Tag 'set' -Args @($xl, 'set', '--path', $EXCEL, '--post-id', $postId, '--field', 'status', '--value', 'drafted')
        Log "drafted $postId OK"
      }
    }

    # ---------------------------------------------------------------- MEDIA (style mới)
    # approve_content ✔ & status=drafted → thumbnail + podcast (văn nói my-voice)
    #   + video (lồng audio + slide xen ẢNH THẬT/INFOGRAPHIC, xfade). Short = optional (make_short).
    'media' {
      $rows = Get-Rows 'media'
      Log ("media: " + $rows.Count + " bài đủ điều kiện.")
      foreach ($r in $rows) {
        $postId = [string]$r.post_id
        Log "--- media $postId : $($r.topic_title)"
        $folder = Get-Folder $r
        if (-not (Test-Path $folder)) { throw "media $postId : folder thiếu $folder" }
        $meta = Join-Path $folder 'meta.json'
        $blogMd = Join-Path $folder 'blog.md'
        foreach ($f in @($meta, $blogMd)) { if (-not (Test-Path $f)) { throw "media $postId : thiếu $f" } }
        $thumb = Join-Path $folder 'thumbnail.png'
        $audio = Join-Path $folder 'audio.mp3'
        $podScript = Join-Path $folder 'podcast.txt'
        $scenes = Join-Path $folder 'scenes.json'
        $video = Join-Path $folder 'video.mp4'

        # 1) thumbnail (cover Inter/news-style)
        Invoke-Py -Tag 'thumbnail' -Args @((Join-Path $root 'gen_infographic.py'),
          '--meta', $meta, '--blog-md', $blogMd, '--out', $thumb)

        # 2) podcast VĂN NÓI: claude sinh podcast.txt -> make_podcast (venv my-voice) -> audio.mp3
        Invoke-Claude -Prompt (Read-Prompt 'podcast-script-prompt.txt' @{
            POST_ID = $postId; BLOG_MD = $blogMd; META = $meta; OUT = $podScript; FOLDER = $folder; MODE = 'full'
          }) -Tag 'podscript'
        if (-not (Test-Path $podScript)) { throw "media $postId : claude không sinh podcast.txt" }
        Invoke-Py -Tag 'podcast' -Exe $OVPY -Args @((Join-Path $root 'make_podcast.py'),
          '--script', $podScript, '--meta', $meta, '--out', $audio, '--profile', $PROFILE)

        # 3) scenes (claude từ blog) -> make_podcast_video (audio + ảnh Openverse + infographic, xfade)
        Invoke-Claude -Prompt (Read-Prompt 'scenes-gen-prompt.txt' @{
            POST_ID = $postId; BLOG_MD = $blogMd; META = $meta; OUT = $scenes; FOLDER = $folder; MODE = 'full'
          }) -Tag 'scenes'
        if (-not (Test-Path $scenes)) { throw "media $postId : claude không sinh scenes.json" }
        Invoke-Py -Tag 'video' -Args @((Join-Path $root 'make_podcast_video.py'),
          '--audio', $audio, '--scenes', $scenes, '--meta', $meta, '--out', $video, '--size', '1280x720')
        if (-not (Test-Path $video)) { throw "media $postId : không sinh video.mp4" }

        # 3b) SHORT (OPTIONAL): chỉ khi cột make_short tick.
        $mk = ([string]$r.make_short).Trim().ToLower()
        if (@('x', 'true', '✓', '1', 'yes') -contains $mk) {
          Log "media $postId : make_short ✔ -> dựng video-short (portrait)."
          $podShort = Join-Path $folder 'podcast-short.txt'
          $scnShort = Join-Path $folder 'scenes-short.json'
          $audShort = Join-Path $folder 'audio-short.mp3'
          $vidShort = Join-Path $folder 'video-short.mp4'
          Invoke-Claude -Prompt (Read-Prompt 'podcast-script-prompt.txt' @{
              POST_ID = $postId; BLOG_MD = $blogMd; META = $meta; OUT = $podShort; FOLDER = $folder; MODE = 'short'
            }) -Tag 'podshort'
          if (Test-Path $podShort) {
            Invoke-Py -Tag 'audshort' -Exe $OVPY -Args @((Join-Path $root 'make_podcast.py'),
              '--script', $podShort, '--meta', $meta, '--out', $audShort, '--profile', $PROFILE)
            Invoke-Claude -Prompt (Read-Prompt 'scenes-gen-prompt.txt' @{
                POST_ID = $postId; BLOG_MD = $blogMd; META = $meta; OUT = $scnShort; FOLDER = $folder; MODE = 'short'
              }) -Tag 'scnshort'
            if (Test-Path $scnShort) {
              Invoke-Py -Tag 'vidshort' -Args @((Join-Path $root 'make_podcast_video.py'),
                '--audio', $audShort, '--scenes', $scnShort, '--meta', $meta, '--out', $vidShort, '--size', '1080x1920')
            }
          }
        }

        $relFolder = $folder.Replace($ASSET_ROOT, '').TrimStart('\', '/')
        # cột tên 'infographic_png' giữ nguyên (schema) nhưng trỏ thumbnail.png.
        Invoke-Py -Tag 'set' -Args @($xl, 'set', '--path', $EXCEL, '--post-id', $postId, '--field', 'infographic_png', '--value', (Join-Path $relFolder 'thumbnail.png'))
        Invoke-Py -Tag 'set' -Args @($xl, 'set', '--path', $EXCEL, '--post-id', $postId, '--field', 'audio_mp3', '--value', (Join-Path $relFolder 'audio.mp3'))
        Invoke-Py -Tag 'set' -Args @($xl, 'set', '--path', $EXCEL, '--post-id', $postId, '--field', 'video_mp4', '--value', (Join-Path $relFolder 'video.mp4'))
        Invoke-Py -Tag 'set' -Args @($xl, 'set', '--path', $EXCEL, '--post-id', $postId, '--field', 'status', '--value', 'media_ready')
        Log "media_ready $postId OK"
      }
    }

    # ---------------------------------------------------------------- ATLAS
    # status=media_ready → build_blog_html → atlas.html (CHƯA push).
    'atlas' {
      $rows = Get-Rows 'atlas'
      Log ("atlas: " + $rows.Count + " bài đủ điều kiện.")
      foreach ($r in $rows) {
        $postId = [string]$r.post_id
        Log "--- atlas $postId : $($r.topic_title)"
        $folder = Get-Folder $r
        $meta = Join-Path $folder 'meta.json'
        $blogMd = Join-Path $folder 'blog.md'
        $thumb = Join-Path $folder 'thumbnail.png'
        $atlasHtml = Join-Path $folder 'atlas.html'
        foreach ($f in @($meta, $blogMd, $thumb)) { if (-not (Test-Path $f)) { throw "atlas $postId : thiếu $f" } }
        Invoke-Py -Tag 'atlas' -Args @((Join-Path $root 'build_blog_html.py'),
          '--blog-md', $blogMd, '--meta', $meta, '--infographic', $thumb, '--out', $atlasHtml)
        if (-not (Test-Path $atlasHtml)) { throw "atlas $postId : không sinh atlas.html" }

        $relFolder = $folder.Replace($ASSET_ROOT, '').TrimStart('\', '/')
        Invoke-Py -Tag 'set' -Args @($xl, 'set', '--path', $EXCEL, '--post-id', $postId, '--field', 'atlas_html', '--value', (Join-Path $relFolder 'atlas.html'))
        Invoke-Py -Tag 'set' -Args @($xl, 'set', '--path', $EXCEL, '--post-id', $postId, '--field', 'status', '--value', 'atlas_ready')
        Log "atlas_ready $postId OK"
      }
    }

    # ---------------------------------------------------------------- PUBLISH
    # approve_final ✔ & status in {atlas_ready, media_ready} → publish-tobi.ps1 cho từng bài.
    'publish' {
      $rows = Get-Rows 'publish'
      Log ("publish: " + $rows.Count + " bài đủ điều kiện.")
      $pub = Join-Path $root 'publish-tobi.ps1'
      if (-not (Test-Path $pub)) { throw "thiếu publish-tobi.ps1: $pub" }
      foreach ($r in $rows) {
        $postId = [string]$r.post_id
        Log "--- publish $postId : $($r.topic_title)"
        $pubArgs = @{ Campaign = $Campaign; PostId = $postId }   # hashtable splat (named binding) — KHÔNG dùng array splat.
        if ($Uat) { $pubArgs['Uat'] = $true }
        & $pub @pubArgs 2>&1 | ForEach-Object { Log ('publish: ' + $_) }
        if ($LASTEXITCODE -ne 0) { throw "publish-tobi.ps1 $postId failed (exit $LASTEXITCODE)" }
        Log "published $postId OK"
      }
    }
  }
}
catch {
  Log ("ERROR: " + $_.Exception.Message)
  Log '=== failed ==='
  exit 1
}

Log '=== complete ==='
exit 0
