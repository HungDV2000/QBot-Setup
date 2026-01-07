📌 HƯỚNG DẪN CÀI ĐẶT QBOT V2.1

> **Phiên bản:** 2.1 (Cập nhật: Jan 2026)  
> **Thời gian cài đặt:** 5-10 phút  
> **Yêu cầu:** Windows 10/11, Internet

---

📦 I. BƯỚC 1: COPY SOURCE CODE

Chuẩn bị:
1. ✅ Tải file source code về máy (file `.zip` hoặc folder)
2. ✅ Giải nén (nếu là file `.zip`)
3. ✅ Copy toàn bộ folder `qbot_setup` vào ổ đĩa

**Ví dụ vị trí:**
```
C:\qbot_setup
hoặc
D:\Projects\qbot_setup
```

⚠️ **Lưu ý:** Không đặt trong folder có tên dấu tiếng Việt hoặc ký tự đặc biệt!

---

💻 II. BƯỚC 2: MỞ COMMAND PROMPT

→ Cách 1: Mở trực tiếp từ folder (Khuyến nghị)
1. Mở folder `qbot_setup\setup`
2. Click vào thanh địa chỉ (address bar) trên cùng
3. Gõ: `cmd`
4. Nhấn **Enter**

→ Cách 2: Mở từ menu Start
1. Nhấn phím **Windows**
2. Gõ: `cmd`
3. Nhấn **Enter**
4. Gõ: `cd C:\qbot_setup\setup` (thay đường dẫn của bạn)
5. Nhấn **Enter**

---

🚀 III. BƯỚC 3: CHẠY CÀI ĐẶT TỰ ĐỘNG

3.1. Khởi động script cài đặt

Trong cửa sổ Command Prompt, gõ:

```bash
1_setup_install.bat
```

Nhấn **Enter**

3.2. Chọn tác vụ từ menu

Bạn sẽ thấy menu như sau:

```
═══════════════════════════════════════════════════════════════════════
📋 MENU CÀI ĐẶT - Vui lòng chọn tác vụ:
═══════════════════════════════════════════════════════════════════════

   [1] 🚀 CÀI ĐẶT TOÀN BỘ (Khuyến nghị)
       └─ Cài Python + Thư viện + Config + Kiểm tra files

   [2] 🐍 CHỈ CÀI PYTHON
   [3] 📦 CHỈ CÀI THƯ VIỆN PYTHON
   [4] 📝 CHỈ TẠO FILE CONFIG
   [5] 🔍 CHỈ KIỂM TRA FILES
   [6] ✅ KIỂM TRA MÔI TRƯỜNG
   [0] ❌ THOÁT

👉 Nhập lựa chọn của bạn (0-6):
```

3.3. Cài đặt lần đầu (khuyến nghị)

1. **Nhấn** `1` (Cài đặt toàn bộ)
2. **Nhấn** `Y` để xác nhận
3. **Chờ đợi:**
   - Script sẽ tự động tải và cài Python 3.11
   - Click `Yes` khi có cửa sổ UAC (User Account Control)
   - Đợi 5-10 phút để cài thư viện
4. ✅ **Hoàn tất!**

3.4. Các option khác (tùy chọn)

| Option | Khi nào dùng |
|--------|--------------|
| **[2]** CHỈ CÀI PYTHON | Khi đã có thư viện, chỉ thiếu Python |
| **[3]** CHỈ CÀI THƯ VIỆN | Đã có Python, cần cài/cài lại thư viện |
| **[4]** CHỈ TẠO CONFIG | Tạo lại file config.ini mẫu |
| **[5]** CHỈ KIỂM TRA FILES | Kiểm tra source code đầy đủ chưa |
| **[6]** KIỂM TRA MÔI TRƯỜNG | Xem đã cài đủ chưa |

---

⚙️ IV. BƯỚC 4: CẤU HÌNH (SAU KHI CÀI XONG)

4.1. Mở file config

1. Vào folder `qbot_setup`
2. Mở file `config.ini` bằng Notepad (hoặc text editor khác)

4.2. Điền thông tin

🔹 **[TELEGRAM]** - Thông báo
```ini
bot_token = YOUR_TELEGRAM_BOT_TOKEN
chat_id = YOUR_TELEGRAM_CHAT_ID
prefix_channel = TEST BOT
```

**Hướng dẫn lấy:**
- `bot_token`: Nhắn `/newbot` cho **@BotFather** trên Telegram
- `chat_id`: Nhắn `/start` cho **@userinfobot** trên Telegram
- `prefix_channel`: Tên phân biệt bot (VD: "BOT TEST", "BOT LIVE")

🔹 **[BINANCE]** - Giao dịch
```ini
key_binance = YOUR_BINANCE_API_KEY
secret_binance = YOUR_BINANCE_SECRET_KEY
```

**Hướng dẫn lấy:**
1. Đăng nhập Binance Futures
2. Vào **API Management**
3. Tạo **New API Key**
4. Copy **API Key** và **Secret Key**

⚠️ **Quan trọng:** Bật quyền **Futures Trading** cho API!

🔹 **[GOOGLE SHEETS]** - Dữ liệu
```ini
spreadsheet_id = YOUR_GOOGLE_SPREADSHEET_ID
```

**Hướng dẫn lấy:**
- Mở Google Sheets
- Copy phần ID trong URL:
  ```
  https://docs.google.com/spreadsheets/d/[ID_Ở_ĐÂY]/edit
  ```

4.3. Lưu file

1. Nhấn **Ctrl + S** (hoặc File → Save)
2. Đóng Notepad

4.4. Copy credentials.json

1. Tải `credentials.json` từ **Google Cloud Console**
2. Copy vào folder `qbot_setup` (cùng cấp với `config.ini`)

---

🏃 V. BƯỚC 5: CHẠY BOT

5.1. Khởi động Bot Manager

1. Vào folder `qbot_setup`
2. Double-click: `3_qbot_manager.bat`

5.2. Sử dụng menu

```
═══════════════════════════════════════════════════════════════════════
📋 QBOT MANAGER - Chọn tác vụ:
═══════════════════════════════════════════════════════════════════════

   [1] 📊 KIỂM TRA TRẠNG THÁI
   [2] 🚀 KHỞI ĐỘNG TỪNG BOT
   [3] ▶️  KHỞI ĐỘNG TẤT CẢ
   [4] ⏸️  DỪNG TẤT CẢ
   [0] ❌ THOÁT
```

**Lần đầu chạy:**
1. Nhấn `3` → Khởi động tất cả
2. Chờ các bot khởi động (khoảng 30 giây)
3. Nhấn `1` → Kiểm tra trạng thái (đảm bảo đều ✅ RUNNING)
4. Nhấn `0` → Thoát (bot vẫn chạy nền)

⚠️ **Lưu ý:** Bot sẽ chạy nền, không cần giữ cửa sổ mở!

---

🧹 VI. GỠ CÀI ĐẶT (NẾU CẦN)

Khi nào cần gỡ?
- ❌ Cài lỗi, muốn cài lại từ đầu
- ❌ Xung đột thư viện
- ❌ Reset về trạng thái ban đầu

Cách gỡ:

1. Vào folder `qbot_setup\setup`
2. Chạy: `5_clear_setup.bat`
3. Gõ `YES` để xác nhận
4. Chọn có gỡ Python không (Y/N)
5. Chờ script xóa (2-3 phút)

**Script sẽ xóa:**
- ✅ Thư viện Python
- ✅ config.ini (backup trước khi xóa)
- ✅ Cache, temp files
- ✅ Log files (tùy chọn)
- ❌ **KHÔNG xóa:** Source code, credentials.json

---

❓ VII. GẶP VẤN ĐỀ - TROUBLESHOOTING

🔴 Lỗi: "Python không cài được"

**Nguyên nhân:** Thiếu quyền Administrator

**Giải pháp:**
1. Chuột phải vào `1_setup_install.bat`
2. Chọn **"Run as Administrator"**
3. Click **Yes** khi có UAC
4. Chạy lại

---

🔴 Lỗi: "Cannot write to info.txt"

**Nguyên nhân:** Không có quyền ghi file log

**Giải pháp:** Script sẽ tự động xử lý
- Log sẽ được tạo trong folder cha
- Hoặc disable logging nếu không được
- **Không ảnh hưởng** đến quá trình cài đặt

---

🔴 Lỗi: "requirements.txt not found"

**Nguyên nhân:** Đang ở sai thư mục

**Giải pháp:**
```bash
cd qbot_setup\setup
1_setup_install.bat
```

Đảm bảo đang ở folder `qbot_setup\setup`!

---

🔴 Lỗi: "pip install failed"

**Nguyên nhân:** Mất kết nối internet hoặc proxy

**Giải pháp:**
1. Kiểm tra internet
2. Tắt VPN/Proxy (nếu có)
3. Thử cài thủ công:
   ```bash
   cd qbot_setup
   pip install -r requirements.txt
   ```

---

🔴 Lỗi: "Bot không chạy"

**Bước 1:** Kiểm tra môi trường
```bash
cd qbot_setup\setup
1_setup_install.bat
```
→ Chọn `6` (Kiểm tra môi trường)

**Bước 2:** Xem kết quả
- ✅ **TẤT CẢ OK** → Kiểm tra config.ini
- ❌ **THIẾU GÌ** → Cài lại phần thiếu (chọn option tương ứng)

**Bước 3:** Kiểm tra config
- Đảm bảo đã điền đầy đủ: `bot_token`, `chat_id`, `key_binance`, `secret_binance`, `spreadsheet_id`
- Không có dấu nháy `'` hoặc `"` quanh giá trị

---

🔴 Lỗi: "Module not found: ccxt"

**Nguyên nhân:** Thư viện chưa cài hoặc bị lỗi

**Giải pháp:**
```bash
cd qbot_setup\setup
1_setup_install.bat
```
→ Chọn `3` (Chỉ cài thư viện)

---

🔴 Lỗi: "Google Sheets API credentials"

**Nguyên nhân:** Thiếu hoặc sai `credentials.json`

**Giải pháp:**
1. Tải lại `credentials.json` từ Google Cloud Console
2. Copy vào `qbot_setup` (cùng cấp với `config.ini`)
3. Chạy lại bot

---

🟡 Cảnh báo: "Python đã cài nhưng chưa thấy trong PATH"

**Giải pháp:**
1. **ĐÓNG** cửa sổ CMD hiện tại
2. **MỞ LẠI** CMD mới
3. **CHẠY LẠI** `1_setup_install.bat`

---

🟡 Muốn cài lại từ đầu?

**Bước 1:** Gỡ cài đặt cũ
```bash
cd qbot_setup\setup
5_clear_setup.bat
```
→ Gõ `YES` để xác nhận

**Bước 2:** Cài lại
```bash
1_setup_install.bat
```
→ Chọn `1` (Cài đặt toàn bộ)

---

📝 VIII. CHECKLIST TRƯỚC KHI CHẠY BOT

- [ ] ✅ Python đã cài (check bằng `python --version`)
- [ ] ✅ Thư viện đã cài (check bằng option 6)
- [ ] ✅ `config.ini` đã điền đầy đủ
- [ ] ✅ `credentials.json` đã copy vào folder
- [ ] ✅ Binance API có quyền Futures Trading
- [ ] ✅ Google Sheets đã share với Service Account
- [ ] ✅ Telegram bot đã tạo và lấy token

**Nếu tất cả ✅** → Sẵn sàng chạy bot! 🚀

---

📞 IX. HỖ TRỢ

Khi cần hỗ trợ, gửi cho admin:

1. **Screenshot** cửa sổ lỗi (toàn bộ)
2. **Log files:**
   - `qbot_setup\setup_info.txt`
   - `qbot_setup\setup_error.txt`
3. **Thông tin:**
   - Windows version (Win 10/11)
   - Python version (nếu đã cài)

Liên hệ:

📧 **Email:** support@deepview.vn  
💬 **Telegram:** @deepview_support  
🌐 **Website:** https://deepview.vn

---

📚 X. TÀI LIỆU THAM KHẢO

- [📖 Hướng dẫn chi tiết](./README.md)
- [🔧 Cấu hình nâng cao](./CONFIG_GUIDE.md)
- [🐛 Xử lý lỗi thường gặp](./TROUBLESHOOTING.md)
- [🔄 Cập nhật phiên bản](./UPDATE_GUIDE.md)

---

<div align="center">

**QBot v2.1** - Trading Bot Automation  
© 2026 DeepView JSC - All Rights Reserved

*Last Updated: January 2026*

</div>