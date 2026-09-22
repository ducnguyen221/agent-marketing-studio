# Dựng lại index.html + feed.xml cho repo web của MỘT kênh, bằng cách quét
# YYYY/Www/YYYY-MM-DD.html. Kèm thẻ OG + favicon, RSS feed.xml, khối video mới nhất,
# và form đăng ký hiện ra khi cấu hình email có `script_url`.
#
# File LƯU DẠNG UTF-8 CÓ BOM: nó chứa tiếng Việt và emoji, mà PowerShell 5.1 đọc .ps1
# không BOM sẽ parse-fail IM LẶNG — task "chạy" mà không làm gì.
#
# MỌI thứ thuộc nhận diện kênh (tên, tagline, tác giả, tên miền, pixel) đến từ bản chụp
# `-Config`. Không có thì script DỪNG chứ không tự bịa — xem khối NHẬN DIỆN bên dưới.
#
# Dùng: build-index.ps1 -Repo <thư-mục-repo-web> -Config <bản-chụp.json>
param(
  [Parameter(Mandatory=$true)][string]$Repo,
  # Bản chụp cấu hình do campaign_cfg.py sinh. PowerShell 5.1 không đọc được channel.yml
  # (không có powershell-yaml), nên cấu hình kênh tới đây qua JSON.
  [string]$Config = ''
)
# ─────────────────────────────────────────────────────────────────────────────
# NHẬN DIỆN KÊNH — chỗ DUY NHẤT cần sửa khi dựng kênh mới.
#
# Đọc từ bản chụp `-Config` (sinh từ channel.yml + brand.md); không có thì dùng mặc định
# ngay dưới. Kênh cũ vì thế chạy y như trước, kênh mới chỉ cần điền `channel.yml:theme`.
#
# rgba() SUY RA từ hex chứ không khai tay: khai hai chỗ là sớm muộn màu nền lệch màu chữ
# mà mắt thường không thấy, chỉ lộ sau khi đăng.
$cfgNd = $null
if ($Config -and (Test-Path $Config)) {
  try { $cfgNd = Get-Content $Config -Raw -Encoding UTF8 | ConvertFrom-Json } catch {}
}
function _v($ten, $macDinh) {
  if ($cfgNd -and $cfgNd.PSObject.Properties.Name -contains $ten -and $cfgNd.$ten) { return [string]$cfgNd.$ten }
  return $macDinh
}
function _rgba([string]$hex, [string]$alpha) {
  $h = $hex.TrimStart('#')
  $r = [Convert]::ToInt32($h.Substring(0,2),16); $g = [Convert]::ToInt32($h.Substring(2,2),16); $b = [Convert]::ToInt32($h.Substring(4,2),16)
  return "rgba($r,$g,$b,$alpha)"
}

# `_req` = khoá BẮT BUỘC. Thiếu thì DỪNG, không có mặc định.
#
# Vì sao khác `_v`: màu thiếu thì trang vẫn đúng nội dung, chỉ khác diện mạo. Còn tên kênh,
# tác giả và tên miền thiếu thì trang sẽ mang nhận diện của người viết ra script này — đúng
# thứ một bản mẫu công khai KHÔNG được phép làm. Mặc định im lặng ở đây nghĩa là ai clone
# về cũng xuất bản dưới danh nghĩa người khác mà không hề biết.
function _req($ten) {
  $g = _v $ten ''
  if (-not $g) {
    throw "build-index: thieu khoa nhan dien '$ten' trong -Config. Dien vao channel.yml:brand (hoac brand.md) roi chay lai."
  }
  return $g
}

$NDsiteBase = _req 'site_base'          # URL gốc, KHÔNG dấu / cuối
$NDbrandA   = _req 'a'                  # nửa đầu tên hiển thị, vd "AI"
$NDbrandB   = _req 'b'                  # nửa sau, vd "News"
$NDtagline  = _req 'tagline'            # câu định vị một dòng — brand.md
$NDauthor   = _req 'author'             # ai tuyển chọn/biên tập, hiện ở chân trang
$NDhome     = _req 'home_url'           # trang chủ của tác giả/tổ chức
$NDdesc     = _v 'site_description' $NDtagline
$NDedition  = _v 'edition_word' 'Tuần'  # đơn vị một kỳ: Tuần / Số / Tập…
$NDogImage  = _v 'og_image' ($NDsiteBase.TrimEnd('/') + '/assets/og-banner.png')
$NDpixel    = _v 'fb_pixel_id' ''       # để trống = KHÔNG nhúng pixel nào
# Hai câu chữ dưới đây từng ghi cứng chủ đề của kênh đầu tiên. Mặc định nay
# suy từ chính tên kênh, nên kênh nào cũng đọc xuôi mà không phải sửa mã.
$NDrssDesc  = _v 'rss_description' ($NDbrandA + ' ' + $NDbrandB + ' — ' + $NDtagline + '.')
$NDhotLabel = _v 'hot_label' 'Hot Today'
$NDhotDesc  = _v 'hot_tagline' 'Mỗi ngày một câu chuyện lớn nhất, giải thích dễ hiểu.'
# Thẻ OG và tiêu đề kỳ tách riêng khỏi `tagline`: mạng xã hội cắt tiêu đề theo cách khác
# trang web, còn tiêu đề kỳ thì đã có sẵn chữ chỉ đơn vị ("tuần 36") nên ghép thẳng
# tagline vào là ra "… hàng tuần tuần 36".
$NDogTitle  = _v 'og_title' ($NDbrandA + ' ' + $NDbrandB + ' – ' + $NDtagline)
$NDogDesc   = _v 'og_description' $NDdesc
$NDheroPre  = _v 'edition_title' ($NDbrandA + ' ' + $NDbrandB)
$NDleadName = _v 'pixel_lead_name' 'newsletter'

$NDac1      = _v 'web_accent'  '#00f0ff'
$NDac2      = _v 'web_accent2' '#bd00ff'
$NDac3      = _v 'web_accent3' '#ff5a3c'

# Khối Meta Pixel chỉ sinh ra khi kênh KHAI id. Nhúng sẵn id của người khác là lặng lẽ gửi
# dữ liệu người đọc tới một tài khoản quảng cáo mà chủ trang không hề biết.
$NDpixelHtml = ''
if ($NDpixel) {
  $NDpixelHtml = '<!-- Meta Pixel (ID ' + $NDpixel + ') - do tuong tac tu Facebook. Cong bo tai /privacy/ -->' + "`n" +
    '<script>!function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version=''2.0'';n.queue=[];t=b.createElement(e);t.async=!0;t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,document,''script'',''https://connect.facebook.net/en_US/fbevents.js'');fbq(''init'',''' + $NDpixel + ''');fbq(''track'',''PageView'');</script>' + "`n" +
    '<noscript><img height="1" width="1" style="display:none" alt="" src="https://www.facebook.com/tr?id=' + $NDpixel + '&amp;ev=PageView&amp;noscript=1"/></noscript>'
}

# Bảng thay token. CSS dùng {{...}} vì here-string nháy đơn không nội suy biến.
$NDtoken = @{
  '{{AC1}}'    = $NDac1
  '{{AC2}}'    = $NDac2
  '{{AC3}}'    = $NDac3
  '{{AC1_40}}' = (_rgba $NDac1 '.4')
  '{{AC1_05}}' = (_rgba $NDac1 '.05')
  '{{AC2_04}}' = (_rgba $NDac2 '.04')
  '{{AC3_40}}' = (_rgba $NDac3 '.4')
  '{{BRAND_A}}'   = $NDbrandA
  '{{BRAND_B}}'   = $NDbrandB
  '{{BRAND}}'     = ($NDbrandA + ' ' + $NDbrandB)
  '{{TAGLINE}}'   = $NDtagline
  '{{DESC}}'      = $NDdesc
  '{{AUTHOR}}'    = $NDauthor
  '{{HOME_URL}}'  = $NDhome
  '{{HOME_TEXT}}' = ($NDhome -replace '^https?://', '' -replace '/$', '')
  '{{SITE_BASE}}' = $NDsiteBase.TrimEnd('/')
  '{{OG_IMAGE}}'  = $NDogImage
  '{{EDITION}}'   = $NDedition
  '{{PIXEL}}'     = $NDpixelHtml
  '{{OG_TITLE}}'  = $NDogTitle
  '{{OG_DESC}}'   = $NDogDesc
}
function _thay([string]$s) {
  foreach ($k in $NDtoken.Keys) { $s = $s.Replace($k, $NDtoken[$k]) }
  # Token sót lại = có chỗ khai token mà quên thêm vào bảng. Dừng, đừng đăng trang lỗi.
  if ($s -match '\{\{[A-Z0-9_]+\}\}') {
    throw "build-index: con token chua thay: $($Matches[0])"
  }
  return $s
}
# ─────────────────────────────────────────────────────────────────────────────


$utf8 = New-Object System.Text.UTF8Encoding $false
$vi = [System.Globalization.CultureInfo]::GetCultureInfo('vi-VN')
$inv = [System.Globalization.CultureInfo]::InvariantCulture
$siteBase = $NDsiteBase

# subscriber form is rendered only once the email backend is configured
$scriptUrl = ''
# `script_url` KHÔNG phải bí mật — 05/09/2026 nó về brand.json cùng kênh; chỉ SMTP
# và token còn ở ~/.secret. Đọc brand.json trước, lùi về email-config.json cũ.
$thuMuc = Split-Path -Parent $MyInvocation.MyCommand.Path
# Thứ tự: bản chụp (-Config) -> brand.json (đã nghỉ hưu 07/09, giữ để lùi) -> email-config.json.
# `script_url` KHÔNG có ở đây thì FORM ĐĂNG KÝ BIẾN MẤT KHỎI TRANG mà không lỗi gì —
# đúng kiểu hỏng đã dính 05/09/2026. Vì vậy cuối file có dòng log nói rõ form bật hay tắt.
if ($Config -and (Test-Path $Config)) {
  try {
    $sn = Get-Content $Config -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($sn.script_url -and $sn.script_url -notmatch 'CHANGE_ME') { $scriptUrl = $sn.script_url }
  } catch {}
}
$brandCfg = Join-Path $thuMuc 'brand.json'
if ((-not $scriptUrl) -and (Test-Path $brandCfg)) {
  try {
    $bj = Get-Content $brandCfg -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($bj.script_url -and $bj.script_url -notmatch 'CHANGE_ME') { $scriptUrl = $bj.script_url }
  } catch {}
}
$cfgPath = Join-Path $thuMuc 'email-config.json'
if (Test-Path $cfgPath) {
  try {
    $cfg = Get-Content $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($cfg.script_url -and $cfg.script_url -notmatch 'CHANGE_ME') { $scriptUrl = $cfg.script_url }
  } catch {}
}

# ---- scan editions -----------------------------------------------------------
$entries = Get-ChildItem -Path $Repo -Recurse -Filter '*.html' |
  Where-Object { $_.FullName -match '[\\/](\d{4})[\\/](\d{2})[\\/]((\d{4}-\d{2}-\d{2})|(w\d{2}))\.html$' } |
  ForEach-Object {
    $null = $_.FullName -match '[\\/](\d{4})[\\/](\d{2})[\\/]((\d{4}-\d{2}-\d{2})|(w\d{2}))\.html$'
    # capture NOW: later -match/-notmatch operators overwrite $Matches (PS 5.1)
    $yy = [int]$Matches[1]; $mm = [int]$Matches[2]; $dateStr = $Matches[3]
    $html = [System.IO.File]::ReadAllText($_.FullName, $utf8)
    $items = ([regex]::Matches($html, 'class="card"')).Count
    $hasAudio = $html.Contains('new Audio(')
    $vm = [regex]::Match($html, '<video[^>]+src="([^"]+\.mp4)"')
    $videoSrc = ''
    if ($vm.Success) {
      $videoSrc = $vm.Groups[1].Value
      if ($videoSrc -notmatch '^https?://') {
        $videoSrc = $videoSrc -replace '^(\.\./)+', ''   # ../../video/x.mp4 -> video/x.mp4
      }
    }
    $ym = [regex]::Match($html, 'youtube\.com/embed/([A-Za-z0-9_-]{6,})')
    $videoYT = ''
    if ($ym.Success) { $videoYT = $ym.Groups[1].Value }
    $tldr = ''
    $m = [regex]::Match($html, '(?s)class="tldr"[^>]*>(.*?)</div>')
    if ($m.Success) {
      $tldr = [regex]::Replace($m.Groups[1].Value, '<[^>]+>', ' ')
      $tldr = [regex]::Replace($tldr, '\s+', ' ').Trim()
    }
    if ($dateStr -match '^w(\d{2})$') {
      # weekly file: publish date = that ISO week's Friday
      $wkNum = [int]$dateStr.Substring(1)
      $jan4 = [datetime]($yy.ToString() + '-01-04')
      $week1Mon = $jan4.AddDays(-((([int]$jan4.DayOfWeek) + 6) % 7))
      $d = $week1Mon.AddDays(($wkNum - 1) * 7 + 4)
      $isoW = $wkNum
    } else {
      $d = [datetime]$dateStr
      $thu = $d.AddDays(3 - ((([int]$d.DayOfWeek) + 6) % 7))
      $isoW = [int]([math]::Floor(($thu.DayOfYear - 1) / 7) + 1)
    }
    [pscustomobject]@{
      Year = $yy; Week = $isoW; Date = $d.ToString('yyyy-MM-dd')
      Dt = $d; Dow = $d.ToString('dddd', $vi)
      Rel = ('{0}/{1:D2}/{2}.html' -f $yy, $mm, $dateStr)
      Items = $items; Audio = $hasAudio; Video = (($videoSrc -ne '') -or ($videoYT -ne ''))
      VideoSrc = $videoSrc; VideoYT = $videoYT
      Tldr = $tldr
    }
  } | Sort-Object Date -Descending

$totalEditions = @($entries).Count
$totalItems = (@($entries) | Measure-Object -Property Items -Sum).Sum
if (-not $totalItems) { $totalItems = 0 }

function WeekRange([datetime]$d) {
  $thu = $d.AddDays(3 - ((([int]$d.DayOfWeek) + 6) % 7))
  $mon = $thu.AddDays(-3); $sun = $thu.AddDays(3)
  return $mon.ToString('dd/MM') + ' – ' + $sun.ToString('dd/MM')
}

function Badges($e) {
  $b = '<span class="badge">🗞 ' + $e.Items + ' tin</span>'
  if ($e.Audio) { $b += '<span class="badge">🎧 audio</span>' }
  if ($e.Video) { $b += '<span class="badge">🎬 video</span>' }
  return $b
}

function EscXml($s) {
  return $s.Replace('&', '&amp;').Replace('<', '&lt;').Replace('>', '&gt;').Replace('"', '&quot;')
}

function Snip($s, $n) {
  if ($s.Length -gt $n) { return $s.Substring(0, $n).TrimEnd() + '…' }
  return $s
}

# dấu thương hiệu động — cùng ngôn ngữ chuyển động với trang chủ của kênh
$logo = '<span class="brand-mark"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#00f0ff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 5h12v14H6a2 2 0 0 1-2-2z"/><path d="M16 8h2.5a1.5 1.5 0 0 1 1.5 1.5V17a2 2 0 0 1-2 2"/><path d="M7 9h6M7 12.5h6M7 16h4"/></svg></span>'

# ---- HTML --------------------------------------------------------------------
$sb = New-Object System.Text.StringBuilder
[void]$sb.Append(@'
<!DOCTYPE html>
<html lang="vi"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="{{DESC}}">
<title>{{BRAND}} – {{TAGLINE}}</title>
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<link rel="alternate" type="application/rss+xml" title="{{BRAND}}" href="feed.xml">
<meta property="og:type" content="website">
<meta property="og:title" content="{{OG_TITLE}}">
<meta property="og:description" content="{{OG_DESC}}">
<meta property="og:image" content="{{OG_IMAGE}}">
<meta property="og:url" content="{{SITE_BASE}}/">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{color-scheme:dark;--bg:#04060a;--ink:#f8fafc;--muted:#94a3b8;--line:rgba(255,255,255,.08);
--cyan:{{AC1}};--cyan-glow:{{AC1_40}};--purple:{{AC2}};--panel:rgba(10,15,26,.93);
--hot:{{AC3}};--hot-glow:{{AC3_40}};
--radius:12px;--font-body:'Be Vietnam Pro',system-ui,sans-serif;--font-heading:'Plus Jakarta Sans',system-ui,sans-serif;--font-mono:'JetBrains Mono',Consolas,monospace}
*{box-sizing:border-box;margin:0;padding:0}
html{background:var(--bg);scroll-behavior:smooth}
body{min-height:100vh;color:var(--ink);font-family:var(--font-body);line-height:1.65;letter-spacing:-.01em;
background:radial-gradient(circle at 10% 20%,{{AC1_05}},transparent 40rem),
radial-gradient(circle at 90% 10%,{{AC2_04}},transparent 35rem),
linear-gradient(180deg,#04060a 0%,#080d1a 60%,#030508 100%);padding-bottom:40px}
a{color:inherit;text-decoration:none}
.site{position:relative;z-index:1;width:min(1100px,calc(100% - 40px));margin:0 auto}
.topbar{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:14px 20px;margin-top:14px;
border:1px solid var(--line);border-radius:var(--radius);background:rgba(6,9,16,.92);backdrop-filter:blur(20px)}
.brand{display:inline-flex;align-items:center;gap:13px}
.brand-mark{width:44px;height:44px;display:grid;place-items:center;flex:0 0 auto;border:1px solid rgba(0,240,255,.4);border-radius:50%;
background:radial-gradient(circle,rgba(0,240,255,.22),rgba(189,0,255,.06) 55%,rgba(4,6,10,.95) 78%);
box-shadow:0 0 18px rgba(0,240,255,.35);animation:brandPulse 3.2s ease-in-out infinite;
transition:transform .45s cubic-bezier(.175,.885,.32,1.275)}
.brand:hover .brand-mark{transform:rotate(180deg) scale(1.06);border-color:#00f0ff}
@keyframes brandPulse{0%,100%{box-shadow:0 0 10px rgba(0,240,255,.22)}50%{box-shadow:0 0 26px rgba(0,240,255,.55)}}
.brand-name{font-family:var(--font-heading);font-size:1.25rem;font-weight:800;letter-spacing:-.02em}
.brand-name b{color:var(--cyan);font-weight:800}
.brand-sub{display:block;color:var(--muted);font-size:.68rem;font-family:var(--font-mono);letter-spacing:.12em;text-transform:uppercase}
.nav{display:flex;gap:8px}
.nav a{padding:8px 14px;border:1px solid var(--line);border-radius:8px;font-size:.85rem;color:var(--muted);transition:.2s}
.nav a:hover{color:var(--cyan);border-color:var(--cyan-glow)}
.nav .sub-cta{color:#04060a;font-weight:800;border:0;background:linear-gradient(90deg,#00f0ff,#39ff7a);animation:ctaPulse 2.2s ease-in-out infinite}
.nav .sub-cta:hover{color:#04060a;filter:brightness(1.12)}
@keyframes ctaPulse{0%,100%{box-shadow:0 0 0 0 rgba(0,240,255,.45)}55%{box-shadow:0 0 0 8px rgba(0,240,255,0)}}
.subscribe{scroll-margin-top:20px}
.hero{margin-top:34px}
.label{font-family:var(--font-mono);font-size:.72rem;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:var(--cyan);margin-bottom:10px}
.hero-card{display:block;position:relative;border:1px solid rgba(0,240,255,.25);border-radius:16px;padding:26px 28px;
background:linear-gradient(135deg,rgba(0,240,255,.07),rgba(189,0,255,.05) 60%,var(--panel));transition:.25s}
.hero-card:hover{border-color:var(--cyan);box-shadow:0 0 34px rgba(0,240,255,.12);transform:translateY(-2px)}
.hero-week{font-family:var(--font-mono);color:var(--cyan);font-size:.85rem;letter-spacing:.08em}
.hero-title{font-family:var(--font-heading);font-size:1.65rem;font-weight:800;margin:6px 0 4px}
.hero-range{color:var(--muted);font-size:.92rem}
.hero-tldr{color:#cbd5e1;font-size:.95rem;margin-top:12px;max-width:62rem}
.badges{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.badge{font-family:var(--font-mono);font-size:.74rem;color:#a5f3fc;border:1px solid rgba(0,240,255,.25);border-radius:99px;padding:3px 11px;background:rgba(0,240,255,.06)}
.cta{display:inline-block;margin-top:16px;font-weight:700;color:var(--cyan);font-size:.95rem}
.video-panel{border:1px solid var(--line);border-radius:16px;background:var(--panel);padding:18px 20px;margin-top:16px}
.video-panel video{width:100%;border-radius:10px;margin-top:10px;background:#000}
.stats{display:flex;flex-wrap:wrap;gap:12px;margin-top:22px}
.stat{flex:1;min-width:140px;border:1px solid var(--line);border-radius:var(--radius);background:var(--panel);padding:14px 18px;text-align:center}
.stat .n{font-family:var(--font-heading);font-size:1.5rem;font-weight:800;color:var(--cyan)}
.stat .t{color:var(--muted);font-size:.78rem;font-family:var(--font-mono);letter-spacing:.08em;text-transform:uppercase}
.subscribe{margin-top:34px}
.sub-box{display:flex;flex-wrap:wrap;gap:10px;align-items:center;border:1px solid rgba(189,0,255,.3);border-radius:16px;
background:linear-gradient(135deg,rgba(189,0,255,.07),var(--panel));padding:18px 20px}
.sub-box input{flex:1;min-width:220px;background:#0a0f1c;border:1px solid var(--line);border-radius:9px;
padding:11px 14px;color:var(--ink);font-family:var(--font-body);font-size:.95rem;outline:none}
.sub-box input:focus{border-color:var(--cyan-glow)}
.sub-box button{background:linear-gradient(90deg,#00f0ff,#39ff7a);color:#04060a;font-weight:800;border:0;
border-radius:9px;padding:11px 22px;font-size:.95rem;cursor:pointer}
.sub-box button:hover{filter:brightness(1.1)}
#subMsg{font-size:.88rem;color:#39ff7a;font-weight:600}
.sub-note{color:var(--muted);font-size:.82rem;margin-top:8px}
.archive{margin-top:40px}
.year-h{font-family:var(--font-heading);font-size:1.15rem;font-weight:800;color:#fff;margin:26px 0 12px;display:flex;align-items:center;gap:10px}
.year-h::after{content:"";flex:1;height:1px;background:linear-gradient(90deg,var(--line),transparent)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:14px}
.card{display:block;border:1px solid var(--line);border-radius:var(--radius);background:var(--panel);padding:16px 18px;transition:.2s}
.card:hover{border-color:var(--cyan-glow);box-shadow:0 0 22px rgba(0,240,255,.08);transform:translateY(-2px)}
.card .wk{font-family:var(--font-mono);font-size:.76rem;color:var(--purple);letter-spacing:.08em}
.card .d{font-family:var(--font-heading);font-weight:700;font-size:1.02rem;margin-top:3px}
.card .dow{color:var(--muted);font-size:.82rem;text-transform:capitalize}
.card .badges{margin-top:10px}
.footer{margin-top:52px;text-align:center;font-size:.8rem;color:#4b5563}
.footer a{color:#818cf8}
.nav .hot-cta{color:#fff;border-color:rgba(255,90,60,.5);background:rgba(255,90,60,.12);font-weight:700}
.nav .hot-cta:hover{color:var(--hot);border-color:var(--hot)}
.hottoday{margin-top:40px}
.hot-head{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin:6px 0 14px}
.hot-head p{color:#cbd5e1;font-size:.95rem}
.hot-all{color:var(--hot);font-weight:700;font-size:.9rem;white-space:nowrap}
.hot-all:hover{filter:brightness(1.2)}
.hot-list{display:grid;grid-template-columns:repeat(auto-fill,minmax(225px,1fr));gap:14px}
.hot-card{display:block;border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;background:var(--panel);transition:.2s}
.hot-card:hover{border-color:var(--hot-glow);box-shadow:0 0 22px rgba(255,90,60,.1);transform:translateY(-2px)}
.hot-card .thumb{position:relative;width:100%;aspect-ratio:16/9;background:#000}
.hot-card .thumb img{width:100%;height:100%;object-fit:cover;display:block}
.hot-card .thumb::after{content:"▶";position:absolute;inset:0;display:grid;place-items:center;color:#fff;font-size:1.4rem;opacity:.85;text-shadow:0 2px 10px rgba(0,0,0,.6)}
.hc-body{padding:12px 14px}
.hc-date{font-family:var(--font-mono);font-size:.74rem;color:var(--hot);letter-spacing:.06em}
.hc-title{font-family:var(--font-heading);font-weight:700;font-size:.98rem;margin-top:4px;line-height:1.3}
.hot-empty{color:var(--muted);font-family:var(--font-mono);font-size:.85rem;padding:8px 0}
@media (max-width:640px){
.topbar{flex-wrap:wrap;padding:10px 12px}
.brand-sub{display:none}
.nav{width:100%;justify-content:stretch}
.nav a{flex:1 1 auto;text-align:center;white-space:nowrap;padding:8px 6px;font-size:.8rem}
.stats{gap:8px}
.stat{min-width:0;flex:1;padding:10px 6px}
.stat .n{font-size:1.05rem}
.stat .t{font-size:.62rem}
.hero-title{font-size:1.3rem}
.hero-card{padding:18px 16px}}
</style>{{PIXEL}}
<!-- End Meta Pixel -->
</head><body>
<div class="site">
'@)

# topbar — thứ tự nav: trang chủ -> RSS -> Đăng ký (nhấn màu, cuộn tới #subscribe)
$navSub = ''
if ($scriptUrl) { $navSub = '<a class="sub-cta" href="#subscribe">Đăng ký ✉</a>' }
[void]$sb.Append('<header class="topbar"><a class="brand" href="../" title="Về trang chủ">' + $logo + '<span><span class="brand-name">{{BRAND_A}} <b>{{BRAND_B}}</b></span><span class="brand-sub">{{TAGLINE}} · by {{AUTHOR}}</span></span></a><nav class="nav"><a class="hot-cta" href="hot-today/" title="Tin AI nóng nhất mỗi ngày">🔥 Hot Today</a><a href="{{HOME_URL}}">{{HOME_TEXT}}</a><a href="rss.html" title="Theo dõi qua RSS">RSS</a>' + $navSub + '</nav></header>')

if ($entries) {
  $latest = $entries[0]
  # stats first (above the hero), then the latest-edition card
  [void]$sb.Append('<section class="hero">')
  [void]$sb.Append('<div class="stats" style="margin-top:0;margin-bottom:26px">')
  [void]$sb.Append('<div class="stat"><div class="n">' + $totalEditions + '</div><div class="t">bản tin</div></div>')
  [void]$sb.Append('<div class="stat"><div class="n">' + $totalItems + '</div><div class="t">tin đã tổng hợp</div></div>')
  [void]$sb.Append('<div class="stat"><div class="n">W' + ('{0:D2}' -f $latest.Week) + '</div><div class="t">tuần mới nhất</div></div>')
  [void]$sb.Append('</div>')
  [void]$sb.Append('<div class="label">▍Số mới nhất</div>')
  [void]$sb.Append('<a class="hero-card" href="' + $latest.Rel + '">')
  [void]$sb.Append('<div class="hero-week">' + $latest.Year + ' · TUẦN ' + ('{0:D2}' -f $latest.Week) + '</div>')
  [void]$sb.Append('<div class="hero-title">' + $NDheroPre + ' ' + $NDedition.ToLower() + ' ' + ('{0:D2}' -f $latest.Week) + '</div>')
  [void]$sb.Append('<div class="hero-range">📅 ' + (WeekRange $latest.Dt) + ' · phát hành ' + $latest.Dt.ToString('dd/MM/yyyy') + '</div>')
  if ($latest.Tldr) { [void]$sb.Append('<p class="hero-tldr">' + (Snip $latest.Tldr 220) + '</p>') }
  [void]$sb.Append('<div class="badges">' + (Badges $latest) + '</div>')
  [void]$sb.Append('<span class="cta">Đọc bản tin →</span></a>')
  # video hero (recap of the latest edition) — YouTube embed preferred
  if ($latest.VideoYT) {
    [void]$sb.Append('<div class="video-panel"><div class="label" style="margin-bottom:0">▍🎬 Video recap tuần ' + ('{0:D2}' -f $latest.Week) + '</div>')
    [void]$sb.Append('<div style="position:relative;width:100%;padding-top:56.25%;border-radius:10px;overflow:hidden;margin-top:10px"><iframe src="https://www.youtube.com/embed/' + $latest.VideoYT + '" title="' + $NDbrandA + ' ' + $NDbrandB + ' recap" style="position:absolute;inset:0;width:100%;height:100%;border:0" allow="accelerometer;autoplay;clipboard-write;encrypted-media;gyroscope;picture-in-picture;web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe></div></div>')
  } elseif ($latest.VideoSrc) {
    [void]$sb.Append('<div class="video-panel"><div class="label" style="margin-bottom:0">▍🎬 Video recap tuần ' + ('{0:D2}' -f $latest.Week) + '</div>')
    [void]$sb.Append('<video controls preload="none" poster="assets/og-banner.png" src="' + $latest.VideoSrc + '"></video></div>')
  }
  [void]$sb.Append('</section>')

  # Dải tin nóng hằng ngày — nạp hot-today/hot-news.json phía trình duyệt để
  # nó luôn mới giữa hai lần dựng lại; script đăng tin nóng cập nhật chính JSON đó.
  [void]$sb.Append('<section class="hottoday"><div class="label">▍🔥 ' + $NDhotLabel + '</div>')
  [void]$sb.Append('<div class="hot-head"><p>' + $NDhotDesc + '</p><a class="hot-all" href="hot-today/">Xem tất cả →</a></div>')
  [void]$sb.Append('<div id="hotList" class="hot-list"><div class="hot-empty">Đang tải tin nóng…</div></div></section>')
  [void]$sb.Append('<script>fetch("hot-today/hot-news.json?v="+Date.now()).then(function(r){return r.json();}).then(function(d){var es=(d.entries||[]).filter(function(e){return e.video_id||e.short_id;}).slice(0,4);var el=document.getElementById("hotList");if(!es.length){el.innerHTML=''<div class="hot-empty">Chưa có tin nóng. Quay lại sau nhé!</div>'';return;}el.innerHTML=es.map(function(e){var id=e.video_id||e.short_id;var dd=(e.date||"").slice(5).split("-").reverse().join("/");var t=(e.title||"").replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c];});return ''<a class="hot-card" href="hot-today/"><div class="thumb"><img loading="lazy" src="https://i.ytimg.com/vi/''+id+''/mqdefault.jpg" alt=""></div><div class="hc-body"><div class="hc-date">🔥 ''+dd+''</div><div class="hc-title">''+t+''</div></div></a>'';}).join("");}).catch(function(){document.getElementById("hotList").innerHTML=''<div class="hot-empty">Không tải được tin nóng.</div>'';});</script>')

  # subscribe (only when the email backend is configured)
  if ($scriptUrl) {
    [void]$sb.Append('<section class="subscribe" id="subscribe"><div class="label">▍Nhận bản tin qua email</div>')
    [void]$sb.Append('<form id="subForm" class="sub-box"><input type="email" id="subEmail" placeholder="email-cua-ban@example.com" required autocomplete="email"><button type="submit">Đăng ký</button><span id="subMsg"></span></form>')
    [void]$sb.Append('<p class="sub-note">Mỗi tuần đúng 1 email: tổng quan + top 5 tin nóng + link bản tin và video. Hủy đăng ký bất cứ lúc nào bằng link trong email.</p></section>')
    [void]$sb.Append('<script>document.getElementById("subForm").addEventListener("submit",function(ev){ev.preventDefault();var em=document.getElementById("subEmail").value.trim();var ms=document.getElementById("subMsg");if(!em)return;ms.style.color="#94a3b8";ms.textContent="Đang gửi…";fetch("' + $scriptUrl + '",{method:"POST",mode:"no-cors",body:new URLSearchParams({email:em})}).then(function(){ms.style.color="#39ff7a";ms.textContent="✓ Đã đăng ký! Hẹn thứ 6 này.";document.getElementById("subEmail").value="";if(window.fbq)fbq("track","Lead",{content_name:"' + $NDleadName + '",content_category:"' + $NDbrandA + ' ' + $NDbrandB + '"});}).catch(function(){ms.style.color="#ff4757";ms.textContent="Lỗi mạng, thử lại nhé.";});});</script>')
  }

  # archive grid grouped by year
  [void]$sb.Append('<section class="archive"><div class="label">▍Lưu trữ</div>')
  foreach ($yg in ($entries | Group-Object Year | Sort-Object Name -Descending)) {
    [void]$sb.Append('<div class="year-h">' + $yg.Name + '</div><div class="grid">')
    foreach ($e in ($yg.Group | Sort-Object Date -Descending)) {
      [void]$sb.Append('<a class="card" href="' + $e.Rel + '">')
      [void]$sb.Append('<div class="wk">TUẦN ' + ('{0:D2}' -f $e.Week) + ' · ' + (WeekRange $e.Dt) + '</div>')
      [void]$sb.Append('<div class="d">' + $e.Dt.ToString('dd/MM/yyyy') + '</div>')
      [void]$sb.Append('<div class="dow">' + $e.Dow + '</div>')
      [void]$sb.Append('<div class="badges">' + (Badges $e) + '</div></a>')
    }
    [void]$sb.Append('</div>')
  }
  [void]$sb.Append('</section>')
} else {
  [void]$sb.Append('<p style="margin-top:40px;color:#94a3b8">Chưa có bản tin nào.</p>')
}

[void]$sb.Append(@'
<div class="footer">{{TAGLINE}} · Tuyển chọn &amp; đọc bởi {{AUTHOR}} · <a href="rss.html">RSS</a> · <a href="{{HOME_URL}}">{{HOME_TEXT}}</a></div>
</div><script src="assets/bg.js" defer></script></body></html>
'@)

[System.IO.File]::WriteAllText((Join-Path $Repo 'index.html'), (_thay $sb.ToString()), $utf8)

# ---- feed.xml (RSS 2.0, latest 20 editions) -----------------------------------
$rss = New-Object System.Text.StringBuilder
[void]$rss.Append('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>')
[void]$rss.Append('<title>{{BRAND}} – {{TAGLINE}}</title>')
[void]$rss.Append('<link>' + $siteBase + '/</link>')
[void]$rss.Append('<description>' + (EscXml $NDrssDesc) + '</description>')
[void]$rss.Append('<language>vi</language>')
foreach ($e in (@($entries) | Select-Object -First 20)) {
  $u = $siteBase + '/' + $e.Rel
  $pub = $e.Dt.AddHours(21).ToString('ddd, dd MMM yyyy HH:mm:ss', $inv) + ' +0700'
  [void]$rss.Append('<item><title>' + (EscXml ('{0} – {1} W{2:D2} ({3})' -f ($NDbrandA + ' ' + $NDbrandB), $NDedition, $e.Week, $e.Dt.ToString('dd/MM/yyyy'))) + '</title>')
  [void]$rss.Append('<link>' + $u + '</link><guid isPermaLink="true">' + $u + '</guid>')
  [void]$rss.Append('<pubDate>' + $pub + '</pubDate>')
  if ($e.Tldr) { [void]$rss.Append('<description>' + (EscXml (Snip $e.Tldr 400)) + '</description>') }
  [void]$rss.Append('</item>')
}
[void]$rss.Append('</channel></rss>')
[System.IO.File]::WriteAllText((Join-Path $Repo 'feed.xml'), (_thay $rss.ToString()), $utf8)

# ---- rss.html (human-friendly page; raw feed.xml is for RSS readers) -----------
$feedUrl = $siteBase + '/feed.xml'
$rh = New-Object System.Text.StringBuilder
[void]$rh.Append(@'
<!DOCTYPE html>
<html lang="vi"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Theo dõi {{BRAND}} qua RSS</title>
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<link rel="alternate" type="application/rss+xml" title="{{BRAND}}" href="feed.xml">
<style>
:root{color-scheme:dark}
*{box-sizing:border-box;margin:0;padding:0}
body{min-height:100vh;color:#f8fafc;font-family:'Be Vietnam Pro',system-ui,sans-serif;line-height:1.65;
background:linear-gradient(180deg,#04060a 0%,#080d1a 60%,#030508 100%);padding:40px 20px}
.box{position:relative;z-index:1;max-width:680px;margin:0 auto}
h1{font-size:1.5rem;font-weight:800}
h1 span{color:#00f0ff}
p{color:#94a3b8;margin-top:10px}
.url{display:flex;gap:10px;margin-top:18px}
.url input{flex:1;background:#0a0f1c;border:1px solid rgba(255,255,255,.12);border-radius:9px;padding:11px 14px;color:#a5f3fc;font-family:Consolas,monospace;font-size:.9rem}
.url button{background:linear-gradient(90deg,#00f0ff,#39ff7a);color:#04060a;font-weight:800;border:0;border-radius:9px;padding:11px 18px;cursor:pointer}
.readers{margin-top:16px;display:flex;flex-wrap:wrap;gap:10px}
.readers a{border:1px solid rgba(255,255,255,.12);border-radius:99px;padding:6px 16px;color:#cbd5e1;text-decoration:none;font-size:.88rem}
.readers a:hover{border-color:rgba(0,240,255,.4);color:#00f0ff}
.back{display:inline-block;margin-top:28px;color:#00f0ff;text-decoration:none;font-weight:700}
</style>{{PIXEL}}
<!-- End Meta Pixel -->
</head><body><div class="box">
<h1>Theo dõi <span>{{BRAND}}</span> qua RSS</h1>
<p>RSS cho phép app đọc tin (Feedly, Inoreader, NetNewsWire…) tự nhận bản tin mới mỗi thứ Sáu. Copy địa chỉ feed dưới đây và dán vào app của bạn — file <code>feed.xml</code> là dữ liệu cho máy đọc nên mở trực tiếp sẽ thấy mã XML, đó là điều bình thường.</p>
'@)
[void]$rh.Append('<div class="url"><input id="feedUrl" readonly value="' + $feedUrl + '"><button onclick="navigator.clipboard.writeText(document.getElementById(''feedUrl'').value);this.textContent=''Đã copy ✓'';">Copy</button></div>')
[void]$rh.Append('<div class="readers"><a href="https://feedly.com/i/subscription/feed/' + [uri]::EscapeDataString($feedUrl) + '" target="_blank" rel="noopener">Mở trong Feedly</a><a href="https://www.inoreader.com/feed/' + [uri]::EscapeDataString($feedUrl) + '" target="_blank" rel="noopener">Mở trong Inoreader</a><a href="feed.xml">Xem feed thô (XML)</a></div>')
[void]$rh.Append('<a class="back" href="./">← Về trang ' + $NDbrandA + ' ' + $NDbrandB + '</a>')
[void]$rh.Append('</div><script src="assets/bg.js" defer></script></body></html>')
[System.IO.File]::WriteAllText((Join-Path $Repo 'rss.html'), (_thay $rh.ToString()), $utf8)

Write-Output ('index.html + feed.xml rebuilt: ' + $totalEditions + ' edition(s), ' + $totalItems + ' items' + $(if ($scriptUrl) { ', subscribe form ON' } else { ', subscribe form off (no email-config)' }))
