# 📌 HƯỚNG DẪN CÀI ĐẶT QBOT

---

I. BƯỚC 1: COPY SOURCE CODE

1. Tải file source code về máy (file .zip hoặc folder)
2. Giải nén (nếu là file .zip)
3. Copy toàn bộ folder `qbot` vào ổ đĩa

Ví dụ: Copy vào `C:\qbot` hoặc `D:\qbot`

---

II. BƯỚC 2: MỞ COMMAND PROMPT

-> Cách 1: Mở trực tiếp từ folder
1. Mở folder `qbot` (nơi vừa copy)
2. Click vào thanh địa chỉ (address bar)
3. Gõ: `cmd`
4. Nhấn Enter

-> Cách 2: Mở từ menu Start
1. Nhấn phím Windows
2. Gõ: `cmd`
3. Nhấn Enter
4. Gõ: `cd C:\qbot` (đường dẫn folder của bạn)
5. Nhấn Enter

---

III. BƯỚC 3: CHẠY CÀI ĐẶT TỰ ĐỘNG

Trong cửa sổ Command Prompt, gõ:

```
1_setup_install.bat
```

Nhấn Enter

Sau đó:
- Nhấn `Y` khi được hỏi cài Python
- Click `Yes` khi có cửa sổ UAC
- Đợi 5-10 phút
- ✅ Xong!

---

## 📝 BƯỚC 4: CẤU HÌNH (SAU KHI CÀI XONG)

1. Mở file `config.ini` (double-click)
2. Điền các thông tin:
   - `bot_token` = Token Telegram bot
   - `chat_id` = ID chat Telegram
   - `key_binance` = API key Binance
   - `secret_binance` = Secret key Binance
   - `spreadsheet_id` = ID Google Sheets
3. Lưu file (Ctrl+S)
4. Copy file `credentials.json` vào folder `qbot`

---

## 🚀 BƯỚC 5: CHẠY BOT

Double-click file: `4_qbot_manager.bat`

Trong menu:
- Nhấn `3` → Khởi động tất cả
- Nhấn `0` → Thoát (bot vẫn chạy)

---

## ❓ GẶP VẤN ĐỀ?

-> Lỗi: Python không cài được
Giải pháp: Chạy CMD với quyền Administrator
- Chuột phải vào `1_setup_install.bat`
- Chọn "Run as Administrator"

-> Lỗi: Không tìm thấy file
Giải pháp: Kiểm tra đã copy đúng folder chưa

-> Lỗi: Bot không chạy
Giải pháp: 
- Chạy `2_check_environment.bat` để kiểm tra
- Xem kết quả và làm theo hướng dẫn

---

## 📞 HỖ TRỢ

Nếu cần hỗ trợ, gửi screenshot cửa sổ lỗi cho admin.

---

QBot v2.1 - © DeepView JSC

