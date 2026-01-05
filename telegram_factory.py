import asyncio
from telegram import Bot
from telegram.constants import ParseMode
import cst
import time



bot = Bot(token=cst.bot_token)

async def send_telegram_message(chat_id, text, is_html, show_web_preview):
    try:
        if is_html:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML, disable_web_page_preview = not show_web_preview)
        else:
            await bot.send_message(chat_id=chat_id, text=text)

        print("Message sent successfully")
    except Exception as e:
        print(f"Error sending message: {e}")
        
def send(chat_id, text, is_html, show_web_preview):
    # Fix: Python 3.10+ yêu cầu dùng asyncio.run() thay vì get_event_loop()
    # asyncio.run() tự động tạo và dọn dẹp event loop
    try:
        asyncio.run(send_telegram_message(chat_id, text, is_html, show_web_preview))
    except RuntimeError as e:
        # Fallback: Nếu đã có event loop đang chạy
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(send_telegram_message(chat_id, text, is_html, show_web_preview))
        else:
            raise
    




sent_messages_all = set()
def send_tele(msg, chat_id,is_html, show_web_preview):
    print(f"msg======================={msg}")
    
    send(str(chat_id), msg, is_html, show_web_preview)
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

        
        send(str(chat_id), msg, is_html, show_web_preview)
    else:
        
        print(f"--> Same mess")
            
            


    

