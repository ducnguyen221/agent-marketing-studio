<#
.SYNOPSIS
    Cài đặt một instance marketing-agent: hỏi cấu hình, dựng khung thư mục, ghi instance.yml.

.DESCRIPTION
    Repo marketing-agent chỉ chứa engine (AGENTS, template, output-style, script).
    Nội dung của bạn nằm ở "instance" do script này tạo ra: một thư mục content với
    instance.yml + 02_campaigns/. Mỗi campaign là 1 folder + 1 file .md + 1 file .xlsx
    (5 sheet). Báo cáo nằm trong hồ sơ .md; số liệu nền tảng nằm trong Sheet Engagement —
    KHÔNG có cây data/reports riêng.

.EXAMPLE
    .\install.ps1
    .\install.ps1 -Name my-channel -ContentRoot "C:\path\toi\content\my-channel"

.NOTES
    File này phải giữ BOM UTF-8 để PowerShell 5.1 đọc đúng tiếng Việt.
#>
[CmdletBinding()]
param(
    [string] $Name,
    [string] $ContentRoot,
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
    $display = Ask "1) Tên kênh hoặc thương hiệu bạn muốn triển khai" "my-channel"
    $Name = Slugify $display
} else {
    $display = $Name
    $Name = Slugify $Name
}
if ($Name -eq 'kpim') {
    throw "Tên 'KPIM' dành riêng cho bộ mẫu demo đi kèm repo. Chọn tên khác."
}
Write-Host "   → slug: $Name" -ForegroundColor DarkGray

# ── 2. Nơi đặt content ──────────────────────────────────────────────────────
if (-not $ContentRoot) {
    $defaultContent = Join-Path $RepoRoot "content\$Name"
    Write-Host ""
    Write-Host "2) Nơi đặt CONTENT của instance (hồ sơ + workbook + asset các campaign)." -ForegroundColor Cyan
    Write-Host "   Enter = mặc định trong repo. Hoặc dán đường dẫn khác (vd một thư mục riêng của bạn)."
    $ContentRoot = Ask "   Đường dẫn" $defaultContent
}

# ── 3. Kênh ─────────────────────────────────────────────────────────────────
$channelPick = AskChoice "3) Kênh triển khai:" @('youtube','facebook','youtube + facebook') 'youtube + facebook'
$channels = @()
if ($channelPick -like '*youtube*')  { $channels += 'youtube' }
if ($channelPick -like '*facebook*') { $channels += 'facebook' }

# ── 4. Mức tự trị ───────────────────────────────────────────────────────────
if (-not $NonInteractive) {
    Write-Host ""
    Write-Host "4) Mức tự trị. 'full' cho phép ĐĂNG THẬT lên kênh của bạn." -ForegroundColor Yellow
    $Autonomy = AskChoice "   Chọn:" @('suggest','auto_safe','full') 'suggest'
    if ($Autonomy -eq 'full') {
        $confirm = Read-Host "   Gõ đúng chữ 'DONG Y' để bật full (bất kỳ giá trị khác = suggest)"
        if ($confirm -ne 'DONG Y') {
            $Autonomy = 'suggest'
            Write-Host "   → đã hạ về suggest." -ForegroundColor DarkGray
        }
    }
}

# ── 5. Ngôn ngữ + pillar ────────────────────────────────────────────────────
$language = Ask "5) Ngôn ngữ nội dung" "vi"
$pillars  = Ask "   Các trụ nội dung (pillar), phân cách dấu phẩy (Enter để điền sau)" ""

# ── Dựng khung instance ─────────────────────────────────────────────────────
$campDir = Join-Path $ContentRoot '02_campaigns'
if (-not (Test-Path $campDir)) { New-Item -ItemType Directory -Path $campDir -Force | Out-Null }

$instanceFile = Join-Path $ContentRoot 'instance.yml'
if (Test-Path $instanceFile) {
    Write-Host ""
    Write-Host "instance.yml đã tồn tại — GIỮ NGUYÊN, không ghi đè: $instanceFile" -ForegroundColor Yellow
} else {
    $pillarLine = if ([string]::IsNullOrWhiteSpace($pillars)) { "[]" } else { "[$pillars]" }
    $chFb = if ($channels -contains 'facebook') { "  - platform: facebook`n    handle: `"`"`n    page_id: `"`"`n    token_env: `"`"" } else { "" }
    $chYt = if ($channels -contains 'youtube')  { "  - platform: youtube`n    handle: `"`"`n    channel_id: `"`"`n    token_env: `"`"" } else { "" }
    $yml = @"
## instance.yml — sinh bởi install.ps1
## Đặc tả workbook 5 sheet: schema/workbook_spec.yml (KHÔNG copy vào đây)
name: $Name
label: "$display"
autonomy: $Autonomy          # suggest | auto_safe | full — chỉ 'full' mới được đăng thật
language: $language
created: $(Get-Date -Format 'yyyy-MM-dd')

## Trụ nội dung của instance (CAMPAIGN_TEMPLATE Mục 6)
pillars: $pillarLine

## Kênh phân phối. Token đọc từ .env qua token_env; KHÔNG đặt token ở đây.
## Cách lấy token + quyền: agent/knowledge/PLATFORM_SETUP.md
channels:
$chFb
$chYt
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
$entry = @{ content = $ContentRoot; autonomy = $Autonomy }
$registry | Add-Member -NotePropertyName $Name -NotePropertyValue $entry -Force
$registry | ConvertTo-Json -Depth 5 | Set-Content -Path $registryFile -Encoding UTF8

Write-Host ""
Write-Host "✅ Xong. Instance '$Name' đã sẵn sàng." -ForegroundColor Green
Write-Host "   content : $ContentRoot"
Write-Host "   autonomy: $Autonomy"
Write-Host ""
Write-Host "Bước tiếp theo:" -ForegroundColor Cyan
Write-Host "  1. Xem bộ mẫu content\KPIM\02_campaigns\01_Tobi_Posts\ để biết một campaign hoàn chỉnh trông thế nào."
Write-Host "  2. Tạo campaign đầu tiên: đọc AGENTS.md (Bước 1-3) hoặc bảo agent 'tạo campaign mới'."
Write-Host "  3. Điền pillar + kênh vào $instanceFile nếu chưa xong."
Write-Host ""
