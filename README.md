# QBOT V2.0 - BINANCE FUTURES TRADING BOT 🤖

**Phiên bản:** 2.0  
**Ngày cập nhật:** 16/12/2025  
**Trạng thái:** ✅ Production Ready (Core Features 100%)

---

## 📋 MỤC LỤC

1. [Giới thiệu](#giới-thiệu)
2. [Tính năng chính](#tính-năng-chính)
3. [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
4. [Cài đặt](#cài-đặt)
5. [Cấu hình](#cấu-hình)
6. [Hướng dẫn chi tiết](#hướng-dẫn-chi-tiết)
7. [Cách sử dụng](#cách-sử-dụng)
8. [Cấu trúc dự án](#cấu-trúc-dự-án)
9. [Modules](#modules)
10. [Troubleshooting](#troubleshooting)
11. [Changelog](#changelog)

---

## 🎯 GIỚI THIỆU

QBot v2.0 là trading bot tự động cho **Binance Futures** với khả năng:
- ✅ Đặt lệnh tự động theo tín hiệu từ Google Sheets
- ✅ Quản lý vị thế đa lớp với logic cascade (1a→1b+1c+2a→...)
- ✅ Thu thập dữ liệu thị trường mở rộng (47+ cột dữ liệu)
- ✅ Thông báo Telegram real-time với 8 loại messages
- ✅ Tracking 30 mức giá gần nhất cho mỗi lệnh
- ✅ Báo cáo số dư định kỳ (1h hoặc PNL > 5%)

---

## ✨ TÍNH NĂNG CHÍNH

### **Phase 1: Critical Fixes** ✅
- 🔧 Fix lỗi API -4120 (Algo Order API cho Trailing Stop)
- 🔧 Retry mechanism cho cancel orders với exponential backoff
- 🔧 Lệnh hệ thống: XÓA CHỜ, XÓA VỊ THẾ, STOP
- 🔧 Centralized error handler với logging levels (INFO/WARNING/ERROR/CRITICAL)
- 🔧 Backward compatible column mapping (J,K,L,O + B,C,D,H)

### **Phase 2: Core Features** ✅
- 🎯 **Cascade Logic đa lớp:**
  - 1a khớp → tự động tạo 1b (SL) + 1c (TP) + 2a (Entry lớp 2)
  - TP khớp → hủy SL cùng lớp + Entry lớp sau
  - SL khớp → hủy TP cùng lớp, giữ Entry lớp sau
  
- 📝 **Loại lệnh hỗ trợ:**
  - ✅ TRAILING_STOP_MARKET (entry + TP)
  - ✅ STOP_LIMIT (SL)
  - ✅ LIMIT
  - ✅ MARKET
  
- 📊 **State Tracking vào Google Sheet:**
  - Cột C: Lệnh vừa khớp (timestamp + Order ID)
  - Cột D: Mã lệnh hiện tại (1a, 1b, 1c...)
  - Cột E: Loại lệnh
  - Cột F: Leverage
  - Cột G: Entry Price

### **Phase 3: Data Collection** ✅
- 📈 **Thông tin tài khoản:**
  - Funding Rate (Ô A2)
  - Margin/Wallet Balance
  - Unrealized PNL
  
- 📊 **47+ cột dữ liệu:**
  - Volume 5 khung (15m, 1h, 4h, 1d, 1w)
  - Bollinger Bands 6 khung (15m, 1h, 4h, 1d, 1w, 1M)
  - Giá cao/thấp 3, 7, 30 ngày + timestamp
  - Biên độ tăng/giảm theo timeframe
  
- 🎯 **Tính năng đặc biệt:**
  - Đánh dấu Top 50 mã gần đỉnh/đáy 30 ngày (🔴/🟢)
  - Tracking 30 mức giá gần nhất (mỗi phút)

### **Phase 4: Notifications** ✅
- 📱 **8 loại thông báo Telegram:**
  - ✅ Lệnh khớp (full info + lệnh tiếp theo)
  - 🚨 Lỗi đặt lệnh (code + message + action)
  - ⛔ API bị chặn
  - 📊 Báo cáo số dư định kỳ
  - 🛑 Kích hoạt STOP
  - ✅ Hoàn tất STOP
  - ⚠️ Reduce Only sót
  - 🔴 Cảnh báo nghiêm trọng

---

## 💻 YÊU CẦU HỆ THỐNG

### Phần mềm:
- Python 3.8+
- pip (Python package manager)
- Git (optional, cho version control)

### API Keys:
- Binance API Key + Secret (Futures Trading enabled)
- Google Sheets API credentials (`credentials.json`)
- Telegram Bot Token + Chat ID

### Khác:
- Internet connection ổn định
- RAM tối thiểu: 2GB
- Disk space: ~100MB

---

## 🚀 CÀI ĐẶT

### Bước 1: Clone/Download source code
```bash
cd "/Users/kcode/Documents/Sources/DeepViewJSC/Trade Bot"
# Source đã có sẵn tại: source04062025/
```

### Bước 2: Cài đặt dependencies
```bash
cd source04062025
pip3 install -r requirements.txt
```

**Dependencies:**
- ccxt (Binance API)
- gspread (Google Sheets)
- oauth2client (Google Auth)
- pandas, numpy (Data processing)
- python-telegram-bot (Notifications)

### Bước 3: Setup Google Sheets API
1. Tạo project tại [Google Cloud Console](https://console.cloud.google.com)
2. Enable Google Sheets API
3. Tạo Service Account và download `credentials.json`
4. Đặt file `credentials.json` vào thư mục `source04062025/`
5. Share Google Sheet với email của Service Account

### Bước 4: Setup Telegram Bot
1. Tạo bot mới với [@BotFather](https://t.me/botfather)
2. Lấy Bot Token
3. Lấy Chat ID bằng cách:
   - Gửi message cho bot
   - Truy cập: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Copy `chat.id`

---

## ⚙️ CẤU HÌNH

### File `config.ini`

```ini
[global]
# Binance API
key_name = YourKeyName
key_binance = YOUR_BINANCE_API_KEY
secret_binance = YOUR_BINANCE_SECRET_KEY

# Google Sheets
spreadsheet_id = YOUR_SPREADSHEET_ID
tab_dat_lenh = ĐẶT LỆNH (100 MÃ)

# Telegram
bot_token = YOUR_BOT_TOKEN
chat_id = YOUR_CHAT_ID

# Trading Parameters
lenh2_rate_long = 0.3      # Stop Loss %
lenh2_rate_short = 0.3
lenh3_rate_long = 0.6      # Take Profit %
lenh3_rate_short = 0.6
lenh3_callback_rate = 1    # Trailing callback %

# Delays (seconds)
delay_vao_lenh = 60
delay_vao_lenh_123 = 300
delay_cho_va_khop = 600
delay_calert_possition_and_open_order = 120
delay_update_price = 120
delay_update_all = 120
delay_track_30_prices = 60
delay_periodic_report = 300

# Test Mode
test_mode = false   # true = không đặt lệnh thật
top_count = 50
```

**⚠️ QUAN TRỌNG:**
- Đổi `test_mode = true` khi test lần đầu
- Kiểm tra kỹ API keys trước khi chạy
- Backup config gốc trước khi chỉnh sửa

---

## 📚 HƯỚNG DẪN CHI TIẾT

Bot cung cấp hướng dẫn chi tiết trong thư mục `guides/`:

### **🔑 Tạo credentials.json & Cấp quyền Google Sheets**

**Chọn hướng dẫn phù hợp với bạn:**

| File | Mô tả | Thời gian | Độ chi tiết |
|------|-------|-----------|-------------|
| **[HUONG_DAN_TAO_CREDENTIALS_GOOGLE_SHEETS.md](./guides/HUONG_DAN_TAO_CREDENTIALS_GOOGLE_SHEETS.md)** | Hướng dẫn chi tiết từng bước | 10-15 phút | ⭐⭐⭐⭐⭐ |
| **[QUICK_START_CREDENTIALS.md](./guides/QUICK_START_CREDENTIALS.md)** | Hướng dẫn nhanh dạng checklist | 5-7 phút | ⭐⭐⭐ |
| **[VISUAL_GUIDE_CREDENTIALS.md](./guides/VISUAL_GUIDE_CREDENTIALS.md)** | Hướng dẫn trực quan với ASCII screenshots | 10 phút | ⭐⭐⭐⭐ |

**Nội dung bao gồm:**
- ✅ Cách tạo Google Cloud Project
- ✅ Bật Google Sheets API
- ✅ Tạo Service Account
- ✅ Download credentials.json
- ✅ Chia sẻ Google Sheet với bot
- ✅ Test kết nối
- ✅ Xử lý 8 lỗi thường gặp

**📌 Lưu ý:** File `credentials.json` là **BẮT BUỘC** để bot có thể đọc/ghi dữ liệu từ Google Sheets.

### **📂 Xem tất cả hướng dẫn**

```bash
cd guides
```

Hoặc truy cập: [`guides/README.md`](./guides/README.md)

---

## 🧪 TEST DỮ LIỆU

### **Test HD Update All (Sheet 100 mã)**

Test dữ liệu lấy từ Binance cho sheet "100 mã (50 tăng và 50 giảm)":

```bash
python test_hd_update_all.py
```

**Kết quả:**
- ✅ Log lưu trong: `logs/test_hd_update_all_TIMESTAMP.txt`
- ✅ Test: Top 50 tăng/giảm, Dữ liệu 29 cột (A-AC), Validation
- ✅ **Bổ sung cột mới:** Biên độ giá ngày lớn nhất (%) và Ngày
- ✅ **KHÔNG ghi vào sheet** - chỉ test và log kết quả

---

## 📖 CÁCH SỬ DỤNG

### Chạy tất cả modules (Production)

**Windows:**
```bash
start_all_bots.bat
```

**Mac/Linux:**
```bash
chmod +x start_all_bots.sh
./start_all_bots.sh
```

### Chạy từng module riêng lẻ

```bash
# 1. Đặt lệnh entry (Lệnh 1a)
python3 hd_order.py

# 2. Tạo SL + TP tự động (Lệnh 1b, 1c)
python3 hd_order_123.py

# 3. Monitor positions và orders
python3 hd_alert_possition_and_open_order.py

# 4. Cập nhật dữ liệu thị trường
python3 hd_update_all.py

# 5. Track 30 mức giá
python3 hd_track_30_prices.py

# 6. Báo cáo định kỳ
python3 hd_periodic_report.py
```

### Test nhanh Phase 3
```bash
python3 test_phase3.py
```

### Dừng tất cả modules

**Windows:**
```bash
stop_all_bots.bat
```

**Mac/Linux:**
```bash
./stop_all_bots.sh
```

---

## 📁 CẤU TRÚC DỰ ÁN

```
qbot/
├── 📄 Core Trading Modules
│   ├── hd_order.py                    # Đặt lệnh entry (1a)
│   ├── hd_order_123.py                # Tạo SL + TP (1b, 1c, 2a)
│   ├── hd_alert_possition_and_open_order.py  # Monitor positions
│   ├── hd_cancel_orders_schedule.py   # Hủy lệnh theo lịch
│   └── hd_isolated_crossed_converter.py      # Convert margin mode
│
├── 📊 Data Collection Modules
│   ├── data_collector.py              # Thu thập dữ liệu mở rộng
│   ├── hd_update_all.py               # Cập nhật sheet Data
│   ├── hd_update_price.py             # Cập nhật giá real-time
│   ├── hd_update_cho_va_khop.py       # Cập nhật trạng thái
│   ├── hd_update_danhmuc.py           # Cập nhật danh mục
│   └── hd_track_30_prices.py          # Track 30 giá gần nhất
│
├── 🔧 Helper Modules
│   ├── binance_order_helper.py        # Binance order utilities
│   ├── cascade_manager.py             # Quản lý logic cascade
│   ├── order_state_tracker.py         # Track state vào sheet
│   ├── notification_manager.py        # Quản lý Telegram
│   ├── error_handler.py               # Centralized error handling
│   ├── binance_utils.py               # Binance utilities
│   ├── utils.py                       # General utilities
│   ├── gg_sheet_factory.py            # Google Sheets API
│   └── telegram_factory.py            # Telegram API
│
├── ⚙️ Configuration
│   ├── config.ini                     # Main config
│   ├── config.ini.example             # Config template
│   ├── cst.py                         # Load config constants
│   └── credentials.json               # Google Sheets credentials
│
├── 🧪 Testing
│   ├── test_phase3.py                 # Phase 3 quick test
│   └── check_status.py                # Check bot status
│
├── 📚 Documentation
│   ├── README.md                      # This file
│   ├── QUICK_CHECKLIST.md             # Progress tracking
│   ├── PHASE3_READINESS.md            # Phase 3 guide
│   ├── QBot.md                        # Requirements (v2.0)
│   ├── FEATURE_COMPARISON.md          # Feature matrix
│   └── UPGRADE_CHECKLIST.md           # Detailed checklist
│
└── 🚀 Scripts
    ├── start_all_bots.sh/.bat         # Start all modules
    ├── stop_all_bots.sh/.bat          # Stop all modules
    └── requirements.txt                # Python dependencies
```

---

## 🔧 MODULES CHI TIẾT

### 1. **hd_order.py** - Entry Order Module
- Đọc tín hiệu từ Google Sheet "ĐẶT LỆNH"
- Đặt lệnh entry (1a, 2a, 3a...)
- Hỗ trợ 4 loại lệnh: TRAILING_STOP, STOP_LIMIT, LIMIT, MARKET
- Xử lý lệnh hệ thống: XÓA CHỜ, XÓA VỊ THẾ, STOP

### 2. **hd_order_123.py** - SL/TP Auto Creator
- Monitor positions mới khớp
- Tự động tạo Stop Loss (1b) + Take Profit (1c)
- Sử dụng Cascade Manager để quản lý đa lớp

### 3. **cascade_manager.py** - Cascade Logic Manager
- Quản lý flow: 1a → 1b+1c+2a → 2b+2c+3a
- Xử lý TP khớp trước: hủy SL + Entry lớp sau
- Xử lý SL khớp trước: hủy TP, giữ Entry lớp sau

### 4. **data_collector.py** - Market Data Collector
- Funding Rate
- Volume multi-timeframe (5 khung)
- Bollinger Bands (6 khung)
- High/Low với timestamp (3, 7, 30 ngày)
- Top 50 mã gần đỉnh/đáy

### 5. **notification_manager.py** - Telegram Notifications
- 8 loại thông báo formatted
- Auto-send khi có sự kiện
- Rate limiting để tránh spam

### 6. **order_state_tracker.py** - State Tracking
- Ghi trạng thái lệnh vào Google Sheet
- Cột C-G: Tracking thông tin entry
- Cột H-I: Lệnh tiếp theo

---

## 🛠️ TROUBLESHOOTING

### Lỗi thường gặp:

#### 1. **ImportError: No module named 'ccxt'**
```bash
pip3 install -r requirements.txt
```

#### 2. **Google Sheets API Error**
- Kiểm tra file `credentials.json` có đúng thư mục
- Share sheet với Service Account email
- Enable Google Sheets API trong Cloud Console

#### 3. **Binance API -4120 Error**
- ✅ Đã fix trong v2.0 với Algo Order API
- Kiểm tra API key có quyền Futures Trading

#### 4. **Telegram không nhận message**
- Kiểm tra bot_token đúng
- Kiểm tra chat_id đúng (số âm cho group)
- Test với: `python3 -c "import telegram_factory, cst; telegram_factory.send_tele('Test', cst.chat_id, True, True)"`

#### 5. **Reduce Only Orders không xóa được**
- ✅ Đã fix trong v2.0 với retry mechanism
- Sẽ retry 3 lần với exponential backoff
- Gửi cảnh báo Telegram nếu fail

### Logs:
- `hd_order_123.log` - Logs cho SL/TP module
- `hd_alert_possition_and_open_order.log` - Logs cho monitoring
- `hd_track_30_prices.log` - Logs cho price tracking
- `hd_periodic_report.log` - Logs cho báo cáo
- `error_pumb_dump.log` - Logs cho data collection

---

## 📈 CHANGELOG

### Version 2.0 (16/12/2025) ✅
**Phase 1: Critical Fixes**
- Fix API -4120 error với Algo Order API
- Improve cancel orders với retry mechanism
- Add XÓA CHỜ, XÓA VỊ THẾ commands
- Centralized error handler

**Phase 2: Core Features**
- Cascade logic đa lớp (1a→1b+1c+2a)
- Support STOP_LIMIT, LIMIT orders
- State tracking vào Google Sheet (C,D,E,F,G)
- TP/SL filled handler

**Phase 3: Data Collection**
- Funding Rate
- Volume 5 khung
- Bollinger Bands 6 khung
- High/Low với timestamp (3, 7, 30 ngày)
- Top 50 markers (🔴/🟢)
- Tracking 30 mức giá

**Phase 4: Notifications**
- 8 loại Telegram messages formatted
- Báo cáo định kỳ (1h hoặc PNL>5%)
- Real-time alerts

### Version 1.0 (trước đây)
- Basic order placement
- Simple monitoring
- Limited data collection

---

## 📞 HỖ TRỢ

**Tài liệu:**
- `QUICK_CHECKLIST.md` - Progress tracking
- `PHASE3_READINESS.md` - Phase 3 setup guide
- `QBot.md` - Full requirements document
- `FEATURE_COMPARISON.md` - Feature matrix

**Known Issues:**
- Thời điểm niêm yết: Binance không có API (skipped)
- Chênh lệch giá kích hoạt: Yêu cầu chưa rõ (skipped)

**Future Enhancements:**
- Bot commands (/status, /balance, /positions...)
- Unit tests
- Web dashboard
- Backtesting module

---

## ⚠️ DISCLAIMER

- Đây là bot trading tự động với tiền thật
- Luôn test trên Testnet trước (set `test_mode = true`)
- Không đảm bảo lợi nhuận
- Tự chịu trách nhiệm với các quyết định trading
- Luôn có kill switch (lệnh STOP)
- Monitor 24/7 trong giai đoạn đầu
- Backup config và logs thường xuyên

---

## 📄 LICENSE

Proprietary - For internal use only

---

## 🎯 ROADMAP

- [ ] Phase 5: Polish & Testing
- [ ] Bot commands (optional)
- [ ] Web dashboard (optional)
- [ ] Backtesting module (optional)
- [ ] Multi-account support (optional)

---

**QBot v2.0 - Automated Trading Made Simple** 🚀

*Cập nhật lần cuối: 16/12/2025*

