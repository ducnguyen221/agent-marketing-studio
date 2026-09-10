# run-approve-poller.ps1 — chiều NHẬN của cổng duyệt Telegram.
#
# ## Vì sao KHÔNG đi qua notify-run.ps1
#
# `notify-run.ps1` bọc mọi scheduled task và báo Telegram MỖI LƯỢT. Cái đó đúng cho việc
# chạy thưa (bản tin ngày, video tuần). Poller này chạy gần như liên tục — báo mỗi lượt là
# hàng nghìn tin một ngày, và tin báo mà nhiều tới mức đó thì không ai đọc nữa, tức là mất
# luôn tác dụng cảnh báo cho MỌI task khác. (Đức chốt 10/09/2026.)
#
# Đổi lại, nó tự có cách chứng minh còn sống: mỗi lượt `getUpdates` THÀNH CÔNG ghi một nhịp
# vào `logs/tg-poll-alive.json`. `approve_bus.py trang-thai` đọc nhịp đó và nói sống/chết.
#
# ## Vì sao SỐNG CÓ HẠN rồi thoát, thay vì chạy mãi
#
# Telegram chặn long-poll ở ~50 giây (ĐO ĐƯỢC 10/09/2026, xin 100s vẫn trả về sau 50,7s),
# nên phủ liên tục thì phải nối nhiều lượt trong một tiến trình. Nhưng tiến trình sống mãi
# là một thứ phải trông, và chết câm thì kẹt cổng duyệt.
#
# Cách dùng: Task Scheduler gọi MỖI PHÚT với `MultipleInstances = IgnoreNew`.
#   · Đang chạy  -> Windows bỏ qua lượt gọi mới, tiến trình cũ tiếp tục.
#   · Đã chết    -> phút sau dựng lại.
#   · Sống đủ lâu-> tự thoát, để lượt sau bắt đầu sạch.
# Phủ gần 100%, và tự lành trong vòng 60 giây. Không service nào phải trông.
param(
  [Parameter(Mandatory = $true)][string]$Campaign,
  [int]$SongGiay = 3300               # ~55 phút rồi thoát
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false } catch {}
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'

if (-not (Test-Path (Join-Path $Campaign 'campaign.md'))) {
  Write-Host ("run-approve-poller: " + $Campaign + " khong phai thu muc chien dich.")
  exit 2
}

$py = Join-Path $PSScriptRoot (Join-Path '..' (Join-Path 'pipeline' 'approve_bus.py'))
Write-Host ("=== poller cong duyet · " + (Split-Path $Campaign -Leaf) + " · song " + $SongGiay + "s ===")
& python $py nhan --campaign $Campaign --lien-tuc $SongGiay
exit $LASTEXITCODE
