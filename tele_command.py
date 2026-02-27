"""
tele_command.py - Telegram Bot nhận lệnh điều khiển từ xa

Chạy song song với hd_order.py trong thread riêng (daemon thread).
Nhận lệnh từ Telegram → Ghi trạng thái vào Google Sheet B2
→ Bot chính (hd_order.py) đọc B2 và xử lý ở chu kỳ tiếp theo.

Cú pháp hỗ trợ:
    /stop        → B2 = STOP     (đóng tất cả vị thế + hủy lệnh)
    /pause       → B2 = CHỜ     (ngừng scan lệnh mới)
    /long        → B2 = LONG    (bật chế độ scan LONG)
    /short       → B2 = SHORT   (bật chế độ scan SHORT)
    /xoa_cho     → B2 = XÓA CHỜ    (hủy lệnh pending, giữ vị thế)
    /xoa_vi_the  → B2 = XÓA VỊ THẾ (đóng vị thế, giữ lệnh chờ)
    /status      → Báo cáo trạng thái hiện tại (không ghi sheet)
    /help        → Danh sách lệnh
"""

import asyncio
import threading
import logging
import time
import ccxt

import cst
import gg_sheet_factory

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Whitelist chat_id được phép gửi lệnh ─────────────────────────────────
ALLOWED_CHAT_IDS = {str(cst.chat_id)}


# ══════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════

def _write_b2(value: str) -> bool:
    """Ghi giá trị vào ô B2 của Google Sheet (synchronous)."""
    try:
        gg_sheet_factory.update_single_value(cst.tab_dat_lenh, "B2", value)
        logger.info(f"[TELE CMD] Đã ghi B2 = '{value}'")
        return True
    except Exception as e:
        logger.error(f"[TELE CMD] Lỗi ghi B2='{value}': {e}", exc_info=True)
        return False


def _get_status_text() -> str:
    """Lấy thông tin trạng thái hiện tại từ Sheet + Binance (synchronous)."""
    try:
        # Đọc B2 từ Sheet
        b2_result = gg_sheet_factory.get_dat_lenh("B2:B2")
        b2_value = b2_result[0][0] if (b2_result and b2_result[0]) else "N/A"

        # Kết nối Binance để lấy positions + open orders
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'apiKey': cst.key_binance,
            'secret': cst.secret_binance,
            'options': {'defaultType': 'future'}
        })
        exchange.setSandboxMode(False)

        balance = exchange.fetch_balance()
        positions = balance['info'].get('positions', [])
        active_positions = [
            (p['symbol'], p['positionAmt'])
            for p in positions
            if float(p.get('positionAmt', 0)) != 0
        ]

        open_orders = exchange.fetch_open_orders()

        lines = [
            "📊 <b>TRẠNG THÁI BOT</b>",
            "",
            f"<b>B2 (Trạng thái):</b> <code>{b2_value}</code>",
            f"<b>Vị thế đang mở:</b> {len(active_positions)}",
        ]
        for sym, amt in active_positions[:15]:
            lines.append(f"  • {sym}: {amt}")
        if len(active_positions) > 15:
            lines.append(f"  ... và {len(active_positions) - 15} vị thế khác")

        lines.append(f"<b>Lệnh chờ (open orders):</b> {len(open_orders)}")
        lines.append(f"<b>Thời gian:</b> {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"[TELE CMD] Lỗi _get_status_text: {e}", exc_info=True)
        return f"❌ Lỗi lấy trạng thái: {e}"


def _is_authorized(update: Update) -> bool:
    """Kiểm tra chat_id có trong whitelist không."""
    chat_id = str(update.effective_chat.id)
    if chat_id not in ALLOWED_CHAT_IDS:
        logger.warning(f"[TELE CMD] Lệnh từ chat_id KHÔNG được phép: {chat_id}")
        return False
    return True


# ══════════════════════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ══════════════════════════════════════════════════════════════════════════

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    logger.info(f"[TELE CMD] /stop từ chat_id={update.effective_chat.id}")
    loop = asyncio.get_running_loop()
    success = await loop.run_in_executor(None, _write_b2, "STOP")
    if success:
        await update.message.reply_text(
            "🛑 <b>ĐÃ GHI B2 = STOP</b>\n\n"
            "Bot sẽ đóng tất cả vị thế và hủy lệnh chờ ở chu kỳ tiếp theo (~60s).\n\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text("❌ Lỗi ghi Sheet. Vui lòng kiểm tra lại.")


async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    logger.info(f"[TELE CMD] /pause từ chat_id={update.effective_chat.id}")
    loop = asyncio.get_running_loop()
    success = await loop.run_in_executor(None, _write_b2, "CHỜ")
    if success:
        await update.message.reply_text(
            "💤 <b>ĐÃ GHI B2 = CHỜ</b>\n\n"
            "Bot sẽ ngừng scan lệnh mới ở chu kỳ tiếp theo (~60s).\n"
            "Vị thế và lệnh hiện tại được giữ nguyên.\n\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text("❌ Lỗi ghi Sheet.")


async def cmd_long(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    logger.info(f"[TELE CMD] /long từ chat_id={update.effective_chat.id}")
    loop = asyncio.get_running_loop()
    success = await loop.run_in_executor(None, _write_b2, "LONG")
    if success:
        await update.message.reply_text(
            "📈 <b>ĐÃ GHI B2 = LONG</b>\n\n"
            "Bot sẽ scan và đặt lệnh LONG ở chu kỳ tiếp theo.\n\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text("❌ Lỗi ghi Sheet.")


async def cmd_short(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    logger.info(f"[TELE CMD] /short từ chat_id={update.effective_chat.id}")
    loop = asyncio.get_running_loop()
    success = await loop.run_in_executor(None, _write_b2, "SHORT")
    if success:
        await update.message.reply_text(
            "📉 <b>ĐÃ GHI B2 = SHORT</b>\n\n"
            "Bot sẽ scan và đặt lệnh SHORT ở chu kỳ tiếp theo.\n\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text("❌ Lỗi ghi Sheet.")


async def cmd_xoa_cho(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    logger.info(f"[TELE CMD] /xoa_cho từ chat_id={update.effective_chat.id}")
    loop = asyncio.get_running_loop()
    success = await loop.run_in_executor(None, _write_b2, "XÓA CHỜ")
    if success:
        await update.message.reply_text(
            "🗑️ <b>ĐÃ GHI B2 = XÓA CHỜ</b>\n\n"
            "Bot sẽ hủy tất cả lệnh chờ (pending), giữ nguyên vị thế.\n\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text("❌ Lỗi ghi Sheet.")


async def cmd_xoa_vi_the(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    logger.info(f"[TELE CMD] /xoa_vi_the từ chat_id={update.effective_chat.id}")
    loop = asyncio.get_running_loop()
    success = await loop.run_in_executor(None, _write_b2, "XÓA VỊ THẾ")
    if success:
        await update.message.reply_text(
            "🗑️ <b>ĐÃ GHI B2 = XÓA VỊ THẾ</b>\n\n"
            "Bot sẽ đóng tất cả vị thế, giữ nguyên lệnh chờ.\n\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text("❌ Lỗi ghi Sheet.")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    logger.info(f"[TELE CMD] /status từ chat_id={update.effective_chat.id}")
    await update.message.reply_text("⏳ Đang lấy thông tin, vui lòng chờ...")
    try:
        loop = asyncio.get_running_loop()
        status_text = await loop.run_in_executor(None, _get_status_text)
        await update.message.reply_text(status_text, parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi lấy trạng thái: {e}")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    help_text = (
        "🤖 <b>LỆNH ĐIỀU KHIỂN BOT</b>\n\n"
        "/stop        - Đóng tất cả vị thế + hủy lệnh chờ\n"
        "/pause       - Dừng scan (B2=CHỜ), giữ nguyên lệnh\n"
        "/long        - Bật chế độ scan LONG\n"
        "/short       - Bật chế độ scan SHORT\n"
        "/xoa_cho     - Hủy lệnh chờ, giữ vị thế\n"
        "/xoa_vi_the  - Đóng vị thế, giữ lệnh chờ\n"
        "/status      - Xem trạng thái hiện tại\n"
        "/help        - Xem danh sách lệnh này\n\n"
        "⚠️ <i>Lệnh ghi vào Google Sheet, bot xử lý sau ~60s.</i>"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')


# ══════════════════════════════════════════════════════════════════════════
# RUNNER
# ══════════════════════════════════════════════════════════════════════════

def _run_bot():
    """
    Hàm chạy trong thread riêng.
    Tạo event loop mới, khởi động Application và polling.
    """
    logger.info("[TELE CMD] Thread bắt đầu, đang khởi tạo Application...")
    try:
        # Khởi tạo Google Sheets API cho thread này
        gg_sheet_factory.init_sheet_api()

        # Tạo event loop riêng cho thread (bắt buộc vì asyncio không share loop giữa threads)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        application = Application.builder().token(cst.bot_token).build()

        application.add_handler(CommandHandler("stop",       cmd_stop))
        application.add_handler(CommandHandler("pause",      cmd_pause))
        application.add_handler(CommandHandler("long",       cmd_long))
        application.add_handler(CommandHandler("short",      cmd_short))
        application.add_handler(CommandHandler("xoa_cho",    cmd_xoa_cho))
        application.add_handler(CommandHandler("xoa_vi_the", cmd_xoa_vi_the))
        application.add_handler(CommandHandler("status",     cmd_status))
        application.add_handler(CommandHandler("help",       cmd_help))

        logger.info(f"[TELE CMD] Đang lắng nghe lệnh - Authorized: {ALLOWED_CHAT_IDS}")
        print(f"✅ [TELE CMD] Telegram command bot đang lắng nghe lệnh...", flush=True)

        # Gửi thông báo khởi động (không bắt buộc, có thể tắt nếu spam)
        async def _notify_start():
            try:
                await application.bot.send_message(
                    chat_id=cst.chat_id,
                    text=(
                        f"🤖 <b>Bot lệnh đã sẵn sàng</b>\n\n"
                        f"Gõ /help để xem danh sách lệnh.\n"
                        f"⏰ {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"
                    ),
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.warning(f"[TELE CMD] Không gửi được tin khởi động: {e}")

        loop.run_until_complete(_notify_start())

        # Bắt đầu polling (blocking - chiếm thread này)
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"[TELE CMD] Lỗi nghiêm trọng trong thread: {e}", exc_info=True)
        print(f"❌ [TELE CMD] Lỗi thread: {e}", flush=True)


def start_tele_command_thread() -> threading.Thread:
    """
    Khởi động Telegram command bot trong daemon thread.
    Gọi hàm này một lần duy nhất khi khởi động hd_order.py.

    Returns:
        Thread đã được khởi động
    """
    thread = threading.Thread(
        target=_run_bot,
        name="TeleCommandBot",
        daemon=True  # Tự dừng khi main thread kết thúc
    )
    thread.start()
    logger.info(f"[TELE CMD] Thread '{thread.name}' đã khởi động (daemon=True)")
    return thread
