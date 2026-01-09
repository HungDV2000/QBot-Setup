# 📚 QBOT GUIDES - HƯỚNG DẪN SỬ DỤNG

> Thư mục này chứa các hướng dẫn chi tiết để cài đặt và sử dụng QBot Trading Bot.

---

## 📖 DANH SÁCH HƯỚNG DẪN

### 🔑 **1. Google Sheets & Credentials**

- **[HUONG_DAN_TAO_CREDENTIALS_GOOGLE_SHEETS.md](./HUONG_DAN_TAO_CREDENTIALS_GOOGLE_SHEETS.md)**
  - Hướng dẫn chi tiết từng bước tạo `credentials.json`
  - Cách cấp quyền truy cập Google Sheets
  - Xử lý lỗi thường gặp
  - ⏱️ **Thời gian:** 10-15 phút
  - 📊 **Độ chi tiết:** ⭐⭐⭐⭐⭐

- **[QUICK_START_CREDENTIALS.md](./QUICK_START_CREDENTIALS.md)**
  - Hướng dẫn nhanh dạng checklist
  - Chỉ 5 bước cơ bản
  - ⏱️ **Thời gian:** 5-7 phút
  - 📊 **Độ chi tiết:** ⭐⭐⭐

---

## 🎯 HƯỚNG DẪN SỬ DỤNG

### **Bước 1: Cài đặt môi trường**

Xem hướng dẫn trong thư mục `setup/`:
```
qbot_setup/setup/0_HUONG_DAN_CAI_DAT_NHANH.md
```

### **Bước 2: Tạo credentials.json**

Làm theo một trong hai file:
- **Người mới:** `HUONG_DAN_TAO_CREDENTIALS_GOOGLE_SHEETS.md` (chi tiết)
- **Người có kinh nghiệm:** `QUICK_START_CREDENTIALS.md` (nhanh)

### **Bước 3: Cấu hình bot**

Mở file `config.ini` và điền:
```ini
[global]
; === TELEGRAM ===
bot_token = YOUR_TELEGRAM_BOT_TOKEN
chat_id = YOUR_TELEGRAM_CHAT_ID
prefix_channel = TEST BOT

; === BINANCE API ===
key_binance = YOUR_BINANCE_API_KEY
secret_binance = YOUR_BINANCE_SECRET_KEY

; === GOOGLE SHEETS ===
spreadsheet_id = YOUR_GOOGLE_SPREADSHEET_ID
tab_dat_lenh = ĐẶT LỆNH (100 MÃ)
```

### **Bước 4: Chạy bot**

```bash
cd qbot_setup
python hd_order.py
```

---

## 🆘 HỖ TRỢ

### **Khi gặp vấn đề:**

1. ✅ Đọc lại hướng dẫn từ đầu
2. ✅ Kiểm tra phần "Xử lý lỗi thường gặp"
3. ✅ Xem log files trong `qbot_setup/logs/`
4. ✅ Liên hệ support với thông tin chi tiết

### **Thông tin liên hệ:**

📧 **Email:** support@deepview.vn  
💬 **Telegram:** @DeepViewJSC_Support  
🌐 **Website:** www.deepview.vn

---

## 📂 CẤU TRÚC THƯ MỤC

```
qbot_setup/
├── guides/                                    ← BẠN ĐANG Ở ĐÂY
│   ├── README.md                             ← File này
│   ├── HUONG_DAN_TAO_CREDENTIALS_GOOGLE_SHEETS.md
│   └── QUICK_START_CREDENTIALS.md
├── setup/
│   ├── 0_HUONG_DAN_CAI_DAT_NHANH.md
│   ├── 1_setup_install.bat
│   └── 5_clear_setup.bat
├── credentials.json                          ← Đặt file vào đây
├── config.ini                                ← Cấu hình bot
├── hd_order.py                               ← Bot chính
├── hd_order_123.py
├── hd_order_market_price.py
└── ...
```

---

## 🔗 LIÊN KẾT HỮU ÍCH

### **Official Documentation:**
- [Google Sheets API](https://developers.google.com/sheets/api)
- [Binance API](https://binance-docs.github.io/apidocs/spot/en/)
- [Telegram Bot API](https://core.telegram.org/bots/api)

### **Python Libraries:**
- [ccxt](https://github.com/ccxt/ccxt) - Cryptocurrency Exchange Trading Library
- [gspread](https://docs.gspread.org/) - Google Sheets Python API
- [python-telegram-bot](https://python-telegram-bot.readthedocs.io/)

---

## 📝 GHI CHÚ

- ⚠️ **Bảo mật:** KHÔNG chia sẻ `credentials.json` với bất kỳ ai!
- ⚠️ **Git:** File `credentials.json` đã được thêm vào `.gitignore`.
- 💡 **Backup:** Lưu trữ `credentials.json` ở nơi an toàn.
- 🔄 **Update:** Kiểm tra hướng dẫn mới khi có phiên bản mới.

---

© 2026 DeepView JSC. All rights reserved.

