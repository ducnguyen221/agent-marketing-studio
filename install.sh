#!/bin/sh
# Dựng một TRẠM agent-marketing-studio trên macOS / Linux.
#
# Đây là VỎ, không phải bộ cài: nó chỉ tìm Python rồi giao việc cho
# `scripts/pipeline/init_station.py`. Bản Windows (`install.ps1`) cũng chỉ làm đúng thế.
# Mọi quyết định — hỏi chế độ nào, nhận diện máy đã có trạm, dựng cây gì, ghi
# `studio.local.json` ra sao — nằm ở lõi Python, MỘT chỗ. Hai vỏ tự quyết là hai vỏ sớm
# muộn trôi khỏi nhau, và người dùng macOS nhận một bộ cài khác người dùng Windows.
#
# Dùng:
#   ./install.sh                          # hỏi bạn chọn chế độ cài
#   ./install.sh --yes                    # nhận khuyến nghị: embedded
#   ./install.sh --non-interactive        # không hỏi; không ai trả lời -> mã 2
#   ./install.sh --station ~/noi-dung     # trạm ngoài repo, không hỏi
#   ./install.sh --mode separate
#
# `sh` chứ không phải `bash`: máy mới chưa chắc có bash 4+, và file này không cần gì hơn.
set -eu

REPO="$(cd "$(dirname "$0")" && pwd)"

noi() { printf '%s\n' "$*"; }

# ── 1. Python ────────────────────────────────────────────────────────────────
# Cùng thứ tự với `Find-Python` trong các .ps1 (xem tests/test_find_python.py): biến khai
# rõ → venv của repo → python3 → python. Ứng viên phải CHẠY được và tự khai 3.10+: một
# `python3` có trên PATH mà nổ lúc khởi động là bẫy quen thuộc (shim pyenv/conda cũ).
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
  # Khai mà hỏng thì DỪNG, không lặng lẽ đổi sang Python khác: chạy bằng một Python không
  # phải cái bạn nghĩ là kiểu hỏng mất nhiều giờ mới thấy.
  if chay_duoc "$MARKETING_STUDIO_PY"; then
    PY="$MARKETING_STUDIO_PY"
  else
    noi "MARKETING_STUDIO_PY=$MARKETING_STUDIO_PY khong chay duoc Python 3.10+ -> DUNG."
    exit 1
  fi
else
  for ung in "$REPO/.venv/bin/python" "$REPO/.venv/bin/python3" python3 python; do
    if chay_duoc "$ung"; then PY="$ung"; break; fi
  done
fi
if [ -z "$PY" ]; then
  noi "Khong tim thay Python 3.10+. Cai Python roi chay lai (hoac dat MARKETING_STUDIO_PY)."
  noi "  macOS: brew install python@3.12"
  exit 1
fi
noi ""
noi "=== agent-marketing-studio - dung tram noi dung ==="
noi "Python  : $("$PY" -c 'import sys;print("%d.%d" % sys.version_info[:2])') ($PY)"

# ── 2. Phụ thuộc ─────────────────────────────────────────────────────────────
thieu="$("$PY" - <<'PYEOF'
import importlib.util as u
print(' '.join(n for m, n in (('yaml', 'pyyaml'), ('openpyxl', 'openpyxl'),
                              ('requests', 'requests')) if u.find_spec(m) is None))
PYEOF
)"
if [ -n "$thieu" ]; then
  noi "Thieu goi: $thieu"
  noi "  Cai bang: $PY -m pip install -r requirements.txt"
  noi ""
else
  noi "Phu thuoc: du"
fi

# ── 3. Dựng trạm ─────────────────────────────────────────────────────────────
noi ""
exec "$PY" "$REPO/scripts/pipeline/init_station.py" "$@"
