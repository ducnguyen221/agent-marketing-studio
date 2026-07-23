<#
.SYNOPSIS
    Cài đặt một instance marketing-agent: hỏi cấu hình, dựng khung thư mục, ghi instance.yml.

.DESCRIPTION
    Repo marketing-agent chỉ chứa engine (skill/agent/workflow/script/template).
    Toàn bộ nội dung, dữ liệu và báo cáo nằm ở "instance" do script này tạo ra.
    Instance có 3 gốc tách rời — content (markdown, có thể để nơi khác như Brain),
    data (số liệu đo, đổi hằng ngày) và reports.

.EXAMPLE
    .\install.ps1
    .\install.ps1 -Name ducnguyen-ai -ContentRoot "<HOME>\Brain\50_CONTENT\52_IDEAS\ducnguyen-ai"

.NOTES
    File này phải giữ BOM UTF-8 để PowerShell 5.1 đọc đúng tiếng Việt.
#>
[CmdletBinding()]
param(
    [string] $Name,
    [string] $ContentRoot,
    [string] $DataRoot,
    [string] $ReportRoot,
    [ValidateSet('suggest','auto_safe','full')]
    [string] $Autonomy = 'suggest',
    [switch] $NonInteractive
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Ask([string]$Prompt, [string]$Default) {
    if ($NonInteractive) { return $Default }
    if ([string]::IsNullOrWhiteSpace($Default)) {
        $answer = Read-Host $Prompt
    } else {
        $answer = Read-Host "$Prompt [$Default]"
    }
    if ([string]::IsNullOrWhiteSpace($answer)) { return $Default }
    return $answer.Trim()
}

function AskChoice([string]$Prompt, [string[]]$Options, [string]$Default) {
    if ($NonInteractive) { return $Default }
    Write-Host ""
    Write-Host $Prompt -ForegroundColor Cyan
    for ($i = 0; $i -lt $Options.Count; $i++) {
        Write-Host ("  [{0}] {1}" -f ($i + 1), $Options[$i])
    }
    $raw = Read-Host "Chọn số [mặc định: $Default]"
    if ([string]::IsNullOrWhiteSpace($raw)) { return $Default }
    $idx = 0
    if ([int]::TryParse($raw, [ref]$idx) -and $idx -ge 1 -and $idx -le $Options.Count) {
        return $Options[$idx - 1]
    }
    return $Default
}

function Slugify([string]$Text) {
    $s = $Text.ToLowerInvariant()
    $s = $s -replace '[àáạảãâầấậẩẫăằắặẳẵ]', 'a'
    $s = $s -replace '[èéẹẻẽêềếệểễ]',        'e'
    $s = $s -replace '[ìíịỉĩ]',              'i'
    $s = $s -replace '[òóọỏõôồốộổỗơờớợởỡ]',  'o'
    $s = $s -replace '[ùúụủũưừứựửữ]',        'u'
    $s = $s -replace '[ỳýỵỷỹ]',              'y'
    $s = $s -replace 'đ',                    'd'
    $s = $s -replace '[^a-z0-9]+',           '-'
    return $s.Trim('-')
}

Write-Host ""
Write-Host "═══ marketing-agent · cài đặt instance ═══" -ForegroundColor Green
Write-Host "Repo (engine): $RepoRoot"
Write-Host ""

# ── 1. Tên instance ─────────────────────────────────────────────────────────
if (-not $Name) {
    $display = Ask "1) Tên kênh hoặc chủ đề nội dung bạn muốn triển khai" "my-channel"
    $Name = Slugify $display
} else {
    $display = $Name
    $Name = Slugify $Name
}
if ($Name -eq 'kpim') {
    throw "Tên 'KPIM' dành riêng cho bộ mẫu khoá học đi kèm repo. Chọn tên khác."
}
Write-Host "   → slug: $Name" -ForegroundColor DarkGray

# ── 2. Nơi đặt content ──────────────────────────────────────────────────────
if (-not $ContentRoot) {
    $defaultContent = Join-Path $RepoRoot "content\$Name"
    Write-Host ""
    Write-Host "2) Nơi đặt CONTENT (brief, calendar, nội dung nháp, log duyệt)." -ForegroundColor Cyan
    Write-Host "   Enter = mặc định trong repo. Hoặc dán đường dẫn khác (vd thư mục Brain của bạn)."
    $ContentRoot = Ask "   Đường dẫn" $defaultContent
}

# ── 3. Nơi đặt data + report ────────────────────────────────────────────────
if (-not $DataRoot)   { $DataRoot   = Join-Path $RepoRoot "data\$Name" }
if (-not $ReportRoot) { $ReportRoot = Join-Path $RepoRoot "reports\$Name" }
Write-Host ""
Write-Host "3) Số liệu đo và báo cáo (KHÔNG lên GitHub):" -ForegroundColor Cyan
Write-Host "   data   : $DataRoot"
Write-Host "   reports: $ReportRoot"

# ── 4. Kênh ─────────────────────────────────────────────────────────────────
$channelPick = AskChoice "4) Kênh triển khai:" @('youtube','facebook','youtube + facebook') 'youtube + facebook'
$channels = @()
if ($channelPick -like '*youtube*')  { $channels += 'youtube' }
if ($channelPick -like '*facebook*') { $channels += 'facebook' }

# ── 5. Nguồn số liệu ────────────────────────────────────────────────────────
$sourcePick = AskChoice "5) Nguồn số liệu:" @('manual_export','api','manual_export + api') 'manual_export + api'
$sources = @()
if ($sourcePick -like '*manual_export*') { $sources += 'manual_export' }
if ($sourcePick -like '*api*')           { $sources += 'api' }

# ── 6. Mức tự trị ───────────────────────────────────────────────────────────
if (-not $NonInteractive) {
    Write-Host ""
    Write-Host "6) Mức tự trị. 'full' cho phép ĐĂNG THẬT lên kênh của bạn." -ForegroundColor Yellow
    $Autonomy = AskChoice "   Chọn:" @('suggest','auto_safe','full') 'suggest'
    if ($Autonomy -eq 'full') {
        $confirm = Read-Host "   Gõ đúng chữ 'DONG Y' để bật full (bất kỳ giá trị khác = suggest)"
        if ($confirm -ne 'DONG Y') {
            $Autonomy = 'suggest'
            Write-Host "   → đã hạ về suggest." -ForegroundColor DarkGray
        }
    }
}

# ── 7. Brand voice ──────────────────────────────────────────────────────────
$language   = Ask "7) Ngôn ngữ nội dung" "vi"
$voiceNote  = Ask "   Ghi chú brand voice (Enter để bỏ qua)" ""

# ── Dựng khung ──────────────────────────────────────────────────────────────
$folders = @(
    (Join-Path $ContentRoot '01_brand'),
    (Join-Path $ContentRoot '02_campaigns'),
    (Join-Path $ContentRoot '03_approvals'),
    (Join-Path $ContentRoot '04_published'),
    (Join-Path $DataRoot    'raw'),
    (Join-Path $DataRoot    'star'),
    (Join-Path $DataRoot    'dashboard'),
    $ReportRoot
)
foreach ($f in $folders) {
    if (-not (Test-Path $f)) { New-Item -ItemType Directory -Path $f -Force | Out-Null }
}

$instanceFile = Join-Path $ContentRoot 'instance.yml'
if (Test-Path $instanceFile) {
    Write-Host ""
    Write-Host "instance.yml đã tồn tại — GIỮ NGUYÊN, không ghi đè: $instanceFile" -ForegroundColor Yellow
} else {
    $yml = @"
# instance.yml — sinh bởi install.ps1
# Đặc tả workbook 5 sheet: schema/workbook_spec.yml (KHÔNG copy vào đây)
name: $Name
display_name: "$display"
created: $(Get-Date -Format 'yyyy-MM-dd')

roots:
  content: '$ContentRoot'
  data:    '$DataRoot'
  reports: '$ReportRoot'

channels: [$($channels -join ', ')]

metrics_sources: [$($sources -join ', ')]

autonomy: $Autonomy   # suggest | auto_safe | full — chỉ 'full' mới được đăng thật

content:
  language: $language
  brand_voice_note: "$voiceNote"
  forbidden_terms: []   # tên tool nội bộ không được lộ ra output công khai

# Điền sau khi có quyền API. KHÔNG đặt token ở đây — token đọc từ .env
platform_ids:
  youtube_channel_id: ""
  facebook_page_id: ""
"@
    Set-Content -Path $instanceFile -Value $yml -Encoding UTF8
}

# ── Đăng ký vào registry cục bộ (gitignored) ────────────────────────────────
$registryFile = Join-Path $RepoRoot 'instances.json'
if (Test-Path $registryFile) {
    $registry = Get-Content $registryFile -Raw | ConvertFrom-Json
} else {
    $registry = @{}
}
$entry = @{ content = $ContentRoot; data = $DataRoot; reports = $ReportRoot; autonomy = $Autonomy }
$registry | Add-Member -NotePropertyName $Name -NotePropertyValue $entry -Force
$registry | ConvertTo-Json -Depth 5 | Set-Content -Path $registryFile -Encoding UTF8

Write-Host ""
Write-Host "✅ Xong. Instance '$Name' đã sẵn sàng." -ForegroundColor Green
Write-Host "   content : $ContentRoot"
Write-Host "   data    : $DataRoot"
Write-Host "   reports : $ReportRoot"
Write-Host "   autonomy: $Autonomy"
Write-Host ""
Write-Host "Bước tiếp theo:" -ForegroundColor Cyan
Write-Host "  1. Điền $ContentRoot\01_brand\pillars.csv (xem content\KPIM\01_brand\pillars.csv làm mẫu)"
Write-Host "  2. Tạo campaign đầu tiên trong $ContentRoot\02_campaigns\"
Write-Host "  3. Xem bộ mẫu chạy sẵn ở content\KPIM\ để biết một campaign hoàn chỉnh trông thế nào"
Write-Host ""
