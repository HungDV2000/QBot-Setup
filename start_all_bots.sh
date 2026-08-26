#!/bin/bash
# ==============================================================================
# QBot - Khởi động bot (HỖ TRỢ ĐA TÀI KHOẢN)
#
#   ./start_all_bots.sh              → chạy TẤT CẢ tài khoản khai trong config
#   ./start_all_bots.sh kh_a         → chỉ chạy tài khoản kh_a
#   ./start_all_bots.sh kh_a kh_b    → chạy 2 tài khoản
#
#   ORDER_BOT_MODE=multi ./start_all_bots.sh     → chọn bot đặt lệnh
#   QBOT_CONFIG=khac.ini ./start_all_bots.sh     → dùng file config khác
# ==============================================================================
cd "$(dirname "$0")" || exit 1

CONFIG_FILE="${QBOT_CONFIG:-config.ini}"
FORCE=0
SKIPPED=0
ARGS=()
for a in "$@"; do
    case "$a" in
        --force|-f) FORCE=1 ;;
        *) ARGS+=("$a") ;;
    esac
done
set -- "${ARGS[@]}"

echo "========================================"
echo "QBot - Khởi động"
echo "========================================"

command -v python3 >/dev/null 2>&1 || { echo "❌ Không tìm thấy Python3"; exit 1; }
[ -f "$CONFIG_FILE" ] || { echo "❌ Không tìm thấy $CONFIG_FILE"; exit 1; }

# ── Chọn bot đặt lệnh (Module 1) ─────────────────────────────────────────────
#   trailing = hd_order.py | limit = hd_order_limit.py | multi = hd_order_multi.py
# ⚠️ CHỈ 1 trong 3 — chạy nhiều sẽ đặt lệnh TRÙNG!
ORDER_BOT_MODE="${ORDER_BOT_MODE:-limit}"
case "$ORDER_BOT_MODE" in
    trailing) ORDER_BOT_FILE="hd_order.py" ;;
    limit)    ORDER_BOT_FILE="hd_order_limit.py" ;;
    multi)    ORDER_BOT_FILE="hd_order_multi.py" ;;
    *) echo "❌ ORDER_BOT_MODE='$ORDER_BOT_MODE' không hợp lệ (trailing|limit|multi)"; exit 1 ;;
esac

# ── Danh sách tài khoản ──────────────────────────────────────────────────────
read_accounts() {
    python3 - "$CONFIG_FILE" <<'PY'
import configparser, sys
c = configparser.ConfigParser()
c.read(sys.argv[1], encoding='utf-8')
print(' '.join(a.strip() for a in c.get('global','accounts',fallback='').split(',') if a.strip()))
PY
}

if [ $# -gt 0 ]; then
    ACCOUNTS="$*"                       # chạy tài khoản chỉ định
else
    ACCOUNTS="$(read_accounts)"         # chạy tất cả tài khoản trong config
fi

# ── Kiểm tra tài khoản đã chạy chưa (chống khởi động TRÙNG) ──────────────────
is_running() {
    local PIDDIR="$1" f PID
    [ -d "$PIDDIR" ] || return 1
    for f in "$PIDDIR"/*.pid; do
        [ -f "$f" ] || continue
        PID="$(cat "$f" 2>/dev/null)"
        [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null && return 0
    done
    return 1
}

# ── Khởi động 1 tài khoản ────────────────────────────────────────────────────
start_account() {
    local ACC="$1"
    local LABEL LOGDIR PIDDIR
    if [ -z "$ACC" ]; then
        LABEL="(1 tài khoản)"; LOGDIR="logs"; PIDDIR="pids"
        unset QBOT_ACCOUNT
    else
        LABEL="[$ACC]"; LOGDIR="logs/$ACC"; PIDDIR="pids/$ACC"
        export QBOT_ACCOUNT="$ACC"
    fi
    mkdir -p "$LOGDIR" "$PIDDIR"

    # ⚠️ CHẶN TRÙNG: đang chạy rồi mà khởi động lại sẽ có 2 bộ bot → ĐẶT LỆNH TRÙNG
    if is_running "$PIDDIR" && [ "$FORCE" != "1" ]; then
        echo ""
        echo "⛔ $LABEL ĐANG CHẠY — bỏ qua để tránh đặt lệnh TRÙNG."
        echo "   Muốn khởi động lại:  ./stop_all_bots.sh ${ACC:--y}  rồi chạy lại"
        echo "   (hoặc thêm --force nếu chắc chắn tiến trình cũ đã chết)"
        SKIPPED=$((SKIPPED+1))
        return
    fi

    echo ""
    echo "──────────────────────────────────────"
    echo "▶ Khởi động $LABEL  (mode=$ORDER_BOT_MODE)"
    echo "──────────────────────────────────────"

    run_bot() {   # run_bot <file.py> <mô tả>
        local FILE="$1" DESC="$2" NAME
        NAME="$(basename "$FILE" .py)"
        nohup python3 "$FILE" > "$LOGDIR/$NAME.log" 2>> "$LOGDIR/error.log" &
        echo $! > "$PIDDIR/$NAME.pid"
        echo "  ✔ $DESC (PID $!)"
        sleep 1
    }

    run_bot "$ORDER_BOT_FILE" "Đặt lệnh vào"

    # Mode multi đã tự đặt SL/TP → không chạy hd_order_123 (tránh lệnh TRÙNG)
    if [ "$ORDER_BOT_MODE" = "multi" ]; then
        echo "  ⏭️  Bỏ qua hd_order_123.py (mode=multi đã tự lo SL/TP)"
    else
        run_bot hd_order_123.py "SL/TP"
    fi

    run_bot hd_update_all.py                      "Dữ liệu thị trường"
    run_bot hd_update_price.py                    "Cập nhật giá"
    run_bot hd_update_cho_va_khop.py              "Trạng thái Chờ và khớp"
    run_bot hd_alert_possition_and_open_order.py  "Cảnh báo"
    run_bot hd_cancel_orders_schedule.py          "Hủy lệnh theo lịch"
    run_bot hd_track_30_prices.py                 "Theo dõi 30 mốc giá"
    run_bot hd_periodic_report.py                 "Báo cáo định kỳ"
}

# ── Chạy ─────────────────────────────────────────────────────────────────────
if [ -z "$ACCOUNTS" ]; then
    echo "ℹ️  Config không khai 'accounts' → chế độ 1 tài khoản"
    start_account ""
    TOTAL=1
else
    echo "📋 Tài khoản sẽ chạy: $ACCOUNTS"
    TOTAL=0
    for ACC in $ACCOUNTS; do
        start_account "$ACC"
        TOTAL=$((TOTAL+1))
    done
fi

echo ""
echo "========================================"
if [ "$SKIPPED" -gt 0 ]; then
    echo "✅ Đã khởi động $((TOTAL-SKIPPED))/$TOTAL tài khoản  (bỏ qua $SKIPPED vì đang chạy)"
else
    echo "✅ Đã khởi động $TOTAL tài khoản"
fi
echo "========================================"
echo "Xem trạng thái:  ./status.sh"
echo "Xem log:         tail -f logs/<tài_khoản>/${ORDER_BOT_FILE%.py}.log"
echo "Dừng:            ./stop_all_bots.sh [tài_khoản]"
echo "========================================"
