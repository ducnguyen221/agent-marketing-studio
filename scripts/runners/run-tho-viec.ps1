# run-tho-viec.ps1 — THỢ: nhặt MỘT việc khỏi hàng chờ, làm, rồi thoát.
#
# ## Vì sao một việc rồi thoát, không phải vòng lặp
#
# Task Scheduler gọi mỗi phút với `MultipleInstances = IgnoreNew`. Thợ chạy 10 phút thì 10
# lượt gọi kế tiếp bị Windows chặn — ĐÓ CHÍNH LÀ giới hạn một-agent-một-lúc, và nó đến từ
# hệ điều hành chứ không từ code ta tự viết.
#
# Duyệt cả lô 10 bài thì 10 việc xếp hàng, không phải 10 agent cùng sống. Ngày 11/09/2026
# đúng chỗ này đã thành 335 tiến trình và 16,4 GB RAM, và máy sập.
#
# Hàng rỗng thì thoát ngay và êm — đường chạy bình thường, không phải lỗi.
#
# ## Vì sao KHÔNG đi qua notify-run.ps1
#
# Cùng lý do với poller: gọi mỗi phút mà báo Telegram mỗi lượt là hàng nghìn tin một ngày.
# Thợ tự báo khi CÓ CHUYỆN (xong bước, chạm trần, hỏng hẳn), còn lượt rỗng thì im lặng.
param(
  [Parameter(Mandatory = $true)][string]$Campaign
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false } catch {}
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'

if (-not (Test-Path (Join-Path $Campaign 'campaign.md'))) {
  Write-Host ("run-tho-viec: " + $Campaign + " khong phai thu muc chien dich.")
  exit 2
}

$py = Join-Path $PSScriptRoot (Join-Path '..' (Join-Path 'pipeline' 'tho_viec.py'))

# Ghi log ra file: task chay `-WindowStyle Hidden` nen moi thu in ra la BIEN MAT.
$logDir = Join-Path $Campaign 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ('tho-viec-' + (Get-Date -Format 'yyyy-MM-dd') + '.log')

function Ghi($m) {
  $d = (Get-Date -Format 'HH:mm:ss') + '  ' + $m
  [IO.File]::AppendAllText($log, $d + "`r`n", (New-Object System.Text.UTF8Encoding $false))
  Write-Host $m
}

$ra = & python $py $Campaign 2>&1
$ma = $LASTEXITCODE

# Luot RONG thi KHONG ghi log — moi phut mot dong "hang rong" la 1.440 dong/ngay rac.
if ($ra -notmatch 'hang rong|hàng rỗng') {
  foreach ($d in $ra) { Ghi ("  " + $d) }
  Ghi ("=== tho thoat, ma " + $ma + " ===")
}
exit $ma
