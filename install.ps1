<#
.SYNOPSIS
    Dựng một TRẠM (station) agent-marketing-studio: hỏi chỗ đặt, tạo khung, chỉ bước tiếp.

.DESCRIPTION
    Repo này chỉ chứa engine: script, cổng kiểm, quy trình và template.
    Nội dung của bạn sống ở một TRẠM nằm ngoài git.

    Cấu trúc trạm:
        <trạm>/CHANNELS.md          sổ kênh — kênh nào ở đâu
        <trạm>/<kênh>/channel.yml   hồ sơ kênh: nền tảng, trụ nội dung, mức tự trị
        <trạm>/<kênh>/profile.md    giọng, tác phong, chính kiến
        <trạm>/<kênh>/<chiến dịch>/campaign.md   brief + bảng danh sách bài
        <trạm>/<kênh>/<chiến dịch>/<bài>/        research.md · content.md · publish.json

    Markdown là NGUỒN SỰ THẬT. Excel chỉ là bản xuất (export_excel.py), đi một chiều.

    Script này CỐ TÌNH không tạo kênh hộ bạn: chỗ lưu kênh là quyết định của bạn, và
    new_channel.py sẽ hỏi. Nó chỉ dựng trạm rỗng rồi chỉ đúng lệnh tiếp theo.

.EXAMPLE
    .\install.ps1
    .\install.ps1 -Station "D:\noi-dung" -NonInteractive

.NOTES
    File này phải giữ BOM UTF-8 để PowerShell 5.1 đọc đúng tiếng Việt.
    PowerShell 5.1 không có '&&' và toán tử ba ngôi — đừng thêm vào.
#>
[CmdletBinding()]
param(
    [string] $Station,
    [switch] $NonInteractive
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Say($t, $c = 'Gray') { Write-Host $t -ForegroundColor $c }

Say ""
Say "=== agent-marketing-studio - dung tram noi dung ===" Green
Say ""

# ── 1. Python và phụ thuộc ───────────────────────────────────────────────────
# Kiểm TRƯỚC khi tạo thư mục: dựng xong khung rồi mới báo thiếu Python là bắt người
# dùng đi dọn một thứ họ chưa dùng được.
$py = $null
foreach ($ten in @('python', 'py')) {
    $c = Get-Command $ten -ErrorAction SilentlyContinue
    if ($c) { $py = $c.Source; break }
}
if (-not $py) {
    Say "Khong tim thay Python. Cai Python 3.10+ roi chay lai." Red
    exit 1
}
$ver = & $py -c "import sys;print('%d.%d' % sys.version_info[:2])"
Say ("Python  : {0} ({1})" -f $ver, $py)

$thieu = & $py -c @"
import importlib.util as u
print(' '.join(n for m, n in (('yaml','pyyaml'),('openpyxl','openpyxl'),('requests','requests'))
               if u.find_spec(m) is None))
"@
if ($thieu.Trim()) {
    Say ("Thieu goi: {0}" -f $thieu.Trim()) Yellow
    Say "  Cai bang: pip install -r requirements.txt" Yellow
    Say ""
} else {
    Say "Phu thuoc: du"
}

# ── 2. Chỗ đặt trạm ──────────────────────────────────────────────────────────
$macDinh = Join-Path $env:USERPROFILE ".marketing"
if (-not $Station) {
    if ($NonInteractive) {
        $Station = $macDinh
    } else {
        Say ""
        Say "Dat TRAM o dau? (noi dung cua ban song o day, khong vao git)" Cyan
        Say ("  Enter = {0}" -f $macDinh)
        $tra = Read-Host "  Duong dan"
        if ([string]::IsNullOrWhiteSpace($tra)) { $Station = $macDinh } else { $Station = $tra }
    }
}
$Station = [System.IO.Path]::GetFullPath($Station)

if (Test-Path (Join-Path $Station "CHANNELS.md")) {
    Say ""
    Say ("Da co tram o {0} - khong ghi de." -f $Station) Yellow
} else {
    New-Item -ItemType Directory -Force -Path $Station | Out-Null
    Copy-Item (Join-Path $RepoRoot "templates\CHANNELS.md") (Join-Path $Station "CHANNELS.md")
    Say ""
    Say ("Tram    : {0}" -f $Station) Green
}

# ── 3. Bước tiếp theo ────────────────────────────────────────────────────────
# In ra lệnh THẬT, chạy dán được. Hướng dẫn mà phải sửa mới chạy là hướng dẫn hỏng.
Say ""
Say "Buoc tiep theo:" Cyan
Say ""
Say ("  # 1. Tao kenh dau tien (--path la BAT BUOC: cho luu la quyet dinh cua ban)")
Say ("  python scripts\pipeline\new_channel.py --id ten-kenh --label ""Ten kenh"" ``")
Say ("      --path ""{0}\ten-kenh"" --station ""{1}""" -f $Station, $Station)
Say ""
Say ("  # 2. Tao chien dich")
Say ("  python scripts\pipeline\new_campaign.py --channel ten-kenh --id CMP-2609-abc ``")
Say ("      --name ""Ten chien dich"" --prefix ABC --station ""{0}""" -f $Station)
Say ""
Say ("  # 3. Dien du campaign.md, roi tao bai (buoc nay CHAN neu campaign.md con chu mau)")
Say ("  python scripts\pipeline\new_post.py --campaign CMP-2609-abc --id ABC-001 ``")
Say ("      --slug bai-dau-tien --title ""Tieu de"" --station ""{0}""" -f $Station)
Say ""
Say ("  # Xem truoc mot tram da dien san:")
Say ("  python scripts\pipeline\check_tree.py --station .\examples")
Say ("  (roi mo examples\index.html bang cach bam dup)")
Say ""
