import asyncio
import concurrent.futures
from telegram import Bot
from telegram.constants import ParseMode
import cst
import time


async def send_telegram_message(chat_id, text, is_html, show_web_preview):
    """
    Mỗi lần gửi tạo Bot mới + async with — tránh 'Event loop is closed'
    khi gọi send_tele nhiều lần trong cùng một scan (asyncio.run đóng loop cũ).
    """
    try:
        async with Bot(token=cst.bot_token) as bot:
            if is_html:
                await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=not show_web_preview,
                )
            else:
                await bot.send_message(chat_id=chat_id, text=text)
        print("Message sent successfully")
    except Exception as e:
        print(f"Error sending message: {e}")


def send(chat_id, text, is_html, show_web_preview):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(send_telegram_message(chat_id, text, is_html, show_web_preview))
    else:
        # Đã có event loop (vd. tele_command) → chạy asyncio.run trong thread riêng
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(
                asyncio.run,
                send_telegram_message(chat_id, text, is_html, show_web_preview),
            ).result()
    




def format_telegram_message(msg, is_html):
    """
    Thêm prefix_channel vào đầu message nếu có
    """
    if cst.prefix_channel and cst.prefix_channel.strip():
        prefix = cst.prefix_channel.strip()
        # Nếu message đã có HTML tags hoặc emoji, thêm prefix vào đầu với HTML format
        if is_html and (msg.startswith('<b>') or msg.startswith('✅') or msg.startswith('🛑') or msg.startswith('🚨') or msg.startswith('⚠️')):
            return f"<b>[{prefix}]</b>\n\n{msg}"
        elif is_html:
            return f"<b>[{prefix}]</b>\n\n{msg}"
        else:
            return f"[{prefix}]\n\n{msg}"
    return msg

sent_messages_all = set()
def send_tele(msg, chat_id,is_html, show_web_preview):
    print(f"msg======================={msg}")
    
    # ✅ Tự động thêm prefix_channel vào message
    formatted_msg = format_telegram_message(msg, is_html)
    
    send(str(chat_id), formatted_msg, is_html, show_web_preview)
    sent_messages_all.add(msg)
    
    
    
            
            
sent_messages  = {}

            
def send_tele_with_limit_per_hour(msg, chat_id,is_html, show_web_preview, count_mess_per_hour):
    print(f"msg======================={msg}")
    if msg not in sent_messages_all:
        sent_messages_all.add(msg)

        
        user_id = msg.split('\n', 1)[0]
        print(f"-------------> ID: {user_id}")
        current_time = int(time.time())  

        if user_id not in sent_messages:
            sent_messages[user_id] = {'count': 1, 'last_sent_time': current_time}
        else:
            user_info = sent_messages[user_id]
            sent_count = user_info['count']
            last_sent_time = user_info['last_sent_time']

            
            if sent_count >= count_mess_per_hour and current_time - last_sent_time < 3600:  
                # Đã vượt quá giới hạn số lượng tin nhắn trong 1 giờ
                return 
            
            if current_time - last_sent_time >= 3600:
                user_info['count'] = 1
            else:
                user_info['count'] += 1
            user_info['last_sent_time'] = current_time

        
        # ✅ Tự động thêm prefix_channel vào message
        formatted_msg = format_telegram_message(msg, is_html)
        send(str(chat_id), formatted_msg, is_html, show_web_preview)
    else:
        
        print(f"--> Same mess")
            
            


    

