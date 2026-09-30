# Dựng `sections.json` của repo web tin bằng cách QUÉT thư mục con có `index.html` (mỗi
# thư mục = một chuyên mục). Trang chủ tin đọc file này để vẽ thẻ chuyên mục — thêm một thư
# mục mới rồi chạy lại là nó tự vào danh sách. Chạy tay sau khi thêm/bớt chuyên mục.
#
# Dùng:  pwsh -File build-news-home.ps1 [-Repo <thư mục repo web>]
# Repo web: -Repo -> WEB_REPO_DIR. Không có -> DỪNG (mã 2): không đoán thư mục chứa repo.
# Thông tin tuyển chọn của từng chuyên mục (tên, thẻ, màu, thứ tự, mô tả) nằm trong
# `<repo web>/sections-meta.json` — `{ "<slug>": { "name", "tag", "accent", "order", "desc" } }`.
# Chuyên mục không khai thì lấy tên/mô tả từ <title> và og:description của trang.
param([string]$Repo = '')
if (-not $Repo) { $Repo = [Environment]::GetEnvironmentVariable('WEB_REPO_DIR') }
if (-not $Repo) { Write-Output 'build-news-home: dat -Repo hoac WEB_REPO_DIR (thu muc repo web tin).'; exit 2 }
if ($Repo.StartsWith('~')) { $Repo = Join-Path $HOME $Repo.Substring(1).TrimStart('/', [char]92) }

$utf8 = New-Object System.Text.UTF8Encoding $false

$meta = @{}
$metaFile = Join-Path $Repo 'sections-meta.json'
if (Test-Path -LiteralPath $metaFile) {
  $mj = Get-Content -LiteralPath $metaFile -Raw -Encoding UTF8 | ConvertFrom-Json
  foreach ($p in $mj.PSObject.Properties) {
    $v = $p.Value
    $meta[$p.Name] = @{ name = [string]$v.name; tag = [string]$v.tag; accent = [string]$v.accent; order = [int]$v.order; desc = [string]$v.desc }
  }
}
$accents = @('cyan','emerald','amber','purple')

$sections = @()
Get-ChildItem $Repo -Directory -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -ne 'assets' -and $_.Name -notlike '.*' -and (Test-Path (Join-Path $_.FullName 'index.html')) } |
  ForEach-Object {
    $slug = $_.Name
    if ($meta.ContainsKey($slug)) {
      $m = $meta[$slug]
      $name=$m.name; $tag=$m.tag; $accent=$m.accent; $order=$m.order; $desc=$m.desc
    } else {
      # derive name from <title> (strip after – or |); default accent rotating
      $html = [System.IO.File]::ReadAllText((Join-Path $_.FullName 'index.html'), $utf8)
      $tm = [regex]::Match($html, '<title>([^<]+)</title>')
      $name = if ($tm.Success) { ($tm.Groups[1].Value -split '[–|]')[0].Trim() } else { $slug }
      $dm = [regex]::Match($html, 'og:description"\s+content="([^"]+)"')
      $desc = if ($dm.Success) { $dm.Groups[1].Value } else { "Bản tin $name." }
      $tag = $name; $order = 99; $accent = $accents[($sections.Count) % $accents.Count]
    }
    $hot = Test-Path (Join-Path (Join-Path $_.FullName 'hot-today') 'index.html')
    $sections += [pscustomobject]@{ slug=$slug; name=$name; tag=$tag; accent=$accent; desc=$desc; hot=$hot; order=$order }
  }

$sections = $sections | Sort-Object order, slug
$out = [pscustomobject]@{ generated = (Get-Date).ToString('s'); sections = @($sections) }
$json = $out | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText((Join-Path $Repo 'sections.json'), $json, $utf8)
Write-Output ("sections.json written: " + (@($sections).Count) + " section(s) -> " + (@($sections | ForEach-Object { $_.slug }) -join ', '))
