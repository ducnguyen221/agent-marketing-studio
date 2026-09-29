#!/bin/sh
# Gỡ phần bộ cài agent-marketing-studio sở hữu trên macOS / Linux — GIỮ trạm, .env và repo.
#
# Vỏ mỏng như `install.sh`: tìm Python rồi giao việc cho `scripts/pipeline/studio.py
# uninstall`. Bản Windows (`uninstall.ps1`) gọi đúng lõi đó.
#
# Dùng:
#   ./uninstall.sh --dry-run     # xem trước, chưa gỡ gì
#   ./uninstall.sh               # gỡ
set -eu

REPO="$(cd "$(dirname "$0")" && pwd)"

chay_duoc() {
  [ -n "${1:-}" ] || return 1
  v="$("$1" -c 'import sys;print("%d.%d" % sys.version_info[:2])' 2>/dev/null)" || return 1
  case "$v" in
    3.1[0-9]|3.[2-9][0-9]|[4-9].*) return 0 ;;
    *) return 1 ;;
  esac
}

PY=""
if [ -n "${MARKETING_STUDIO_PY:-}" ]; then
  if chay_duoc "$MARKETING_STUDIO_PY"; then
    PY="$MARKETING_STUDIO_PY"
  else
    printf '%s\n' "MARKETING_STUDIO_PY=$MARKETING_STUDIO_PY khong chay duoc Python 3.10+ -> DUNG."
    exit 1
  fi
else
  for ung in "$REPO/.venv/bin/python" "$REPO/.venv/bin/python3" python3 python; do
    if chay_duoc "$ung"; then PY="$ung"; break; fi
  done
fi
if [ -z "$PY" ]; then
  printf '%s\n' "Khong tim thay Python 3.10+. Cai Python roi chay lai (hoac dat MARKETING_STUDIO_PY)."
  exit 1
fi

exec "$PY" "$REPO/scripts/pipeline/studio.py" uninstall "$@"
