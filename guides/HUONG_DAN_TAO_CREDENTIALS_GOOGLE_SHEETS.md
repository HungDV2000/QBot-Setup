# 📝 HƯỚNG DẪN TẠO CREDENTIALS.JSON VÀ CẤP QUYỀN GOOGLE SHEETS

> **Mục đích:** Hướng dẫn chi tiết cách tạo file `credentials.json` từ Google Cloud Console và cấp quyền truy cập Google Sheets cho bot.
> 
> **Thời gian:** 10-15 phút
> 
> **Yêu cầu:** Tài khoản Google, Google Sheet đã tạo sẵn

---

## 📚 MỤC LỤC

1. [Tổng Quan](#1-tổng-quan)
2. [Tạo Google Cloud Project](#2-tạo-google-cloud-project)
3. [Bật Google Sheets API](#3-bật-google-sheets-api)
4. [Tạo Service Account](#4-tạo-service-account)
5. [Download Credentials.json](#5-download-credentialsjson)
6. [Chia Sẻ Google Sheet](#6-chia-sẻ-google-sheet)
7. [Kiểm Tra Kết Nối](#7-kiểm-tra-kết-nối)
8. [Xử Lý Lỗi Thường Gặp](#8-xử-lý-lỗi-thường-gặp)

---

## 1. TỔNG QUAN

### ❓ **Credentials.json là gì?**

`credentials.json` là file chứa thông tin xác thực (API credentials) cho phép bot của bạn truy cập vào Google Sheets API mà không cần đăng nhập thủ công.

### 🔑 **Thông tin trong file:**

```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "your-service-account@your-project.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
```

### 🎯 **Flow hoạt động:**

```
Bot → credentials.json → Google Sheets API → Your Google Sheet
```

---

## 2. TẠO GOOGLE CLOUD PROJECT

### **Bước 1: Truy cập Google Cloud Console**

1. Mở trình duyệt và truy cập:
   ```
   https://console.cloud.google.com/
   ```

2. Đăng nhập bằng tài khoản Google của bạn.

### **Bước 2: Tạo Project mới**

1. Click vào dropdown **"Select a project"** ở góc trên bên trái (bên cạnh logo Google Cloud).

2. Click nút **"NEW PROJECT"** (hoặc "TẠO DỰ ÁN MỚI").

3. Điền thông tin:
   ```
   Project name:  QBot Trading (hoặc tên bạn muốn)
   Organization:  No organization (hoặc chọn organization nếu có)
   Location:      No organization (hoặc chọn location nếu có)
   ```

4. Click **"CREATE"** (hoặc "TẠO").

5. Đợi 10-20 giây để Google tạo project.

6. **Chọn project vừa tạo** từ dropdown "Select a project".

### 📌 **Lưu ý:**
- Bạn có thể tạo nhiều projects cho các mục đích khác nhau.
- Mỗi project có giới hạn API calls riêng (Free tier: 100 requests/100 seconds).

---

## 3. BẬT GOOGLE SHEETS API

### **Bước 1: Vào API Library**

1. Ở menu bên trái (☰), chọn:
   ```
   APIs & Services → Library
   ```

2. Hoặc tìm kiếm "API Library" trong thanh search phía trên.

### **Bước 2: Tìm Google Sheets API**

1. Trong ô search của API Library, gõ:
   ```
   Google Sheets API
   ```

2. Click vào **"Google Sheets API"** trong kết quả.

### **Bước 3: Enable API**

1. Click nút **"ENABLE"** (hoặc "BẬT").

2. Đợi vài giây để API được kích hoạt.

3. Bạn sẽ thấy màn hình **"API/Service details"** với trạng thái **"API enabled"**.

### 📌 **Lưu ý:**
- Nếu bạn thấy nút **"MANAGE"** thay vì "ENABLE", nghĩa là API đã được bật sẵn.
- Nếu cần, bạn cũng có thể bật **Google Drive API** (không bắt buộc cho bot này).

---

## 4. TẠO SERVICE ACCOUNT

### ❓ **Service Account là gì?**

Service Account là một "tài khoản máy" (không phải tài khoản người dùng) được sử dụng để cho ứng dụng truy cập Google APIs một cách tự động.

### **Bước 1: Vào Credentials**

1. Ở menu bên trái (☰), chọn:
   ```
   APIs & Services → Credentials
   ```

### **Bước 2: Tạo Service Account**

1. Click nút **"+ CREATE CREDENTIALS"** ở phía trên.

2. Chọn **"Service account"** từ dropdown.

### **Bước 3: Điền thông tin Service Account**

**3.1. Service account details (Bước 1/3):**

```
Service account name:    QBot Service Account
Service account ID:      qbot-service-account (tự động tạo)
Service account description: Service account for QBot trading bot (tùy chọn)
```

Click **"CREATE AND CONTINUE"**.

**3.2. Grant this service account access to project (Bước 2/3):**

```
Select a role: (Không cần chọn, bỏ qua)
```

Click **"CONTINUE"**.

**3.3. Grant users access to this service account (Bước 3/3):**

```
(Bỏ qua, không cần điền gì)
```

Click **"DONE"**.

### **Bước 4: Xác nhận Service Account đã được tạo**

Bạn sẽ thấy Service Account vừa tạo trong danh sách **"Service Accounts"** với định dạng email:

```
qbot-service-account@your-project-id.iam.gserviceaccount.com
```

📌 **LƯU LẠI EMAIL NÀY!** Bạn sẽ cần nó để chia sẻ Google Sheet ở bước 6.

---

## 5. DOWNLOAD CREDENTIALS.JSON

### **Bước 1: Vào Service Account vừa tạo**

1. Trong trang **"Credentials"**, tìm Service Account bạn vừa tạo trong phần **"Service Accounts"**.

2. Click vào **email** của Service Account (VD: `qbot-service-account@...`).

### **Bước 2: Tạo Key**

1. Chọn tab **"KEYS"** ở phía trên.

2. Click **"ADD KEY"** → Chọn **"Create new key"**.

3. Chọn key type: **JSON** (mặc định).

4. Click **"CREATE"**.

### **Bước 3: Download file JSON**

1. File `credentials.json` sẽ **tự động được tải xuống** vào máy tính của bạn.

2. Tên file mặc định sẽ giống như:
   ```
   your-project-id-1234567890ab.json
   ```

3. **ĐỔI TÊN** file này thành:
   ```
   credentials.json
   ```

### **Bước 4: Copy file vào thư mục bot**

1. Copy file `credentials.json` vào thư mục gốc của bot:
   ```
   qbot_setup/
   ├── credentials.json  ← Đặt file vào đây!
   ├── hd_order.py
   ├── hd_order_123.py
   ├── config.ini
   └── ...
   ```

2. **QUAN TRỌNG:** File `credentials.json` phải nằm **cùng cấp** với các file `.py` của bot.

### 🔒 **Bảo mật:**

- **KHÔNG CHIA SẺ** file `credentials.json` với bất kỳ ai!
- **KHÔNG COMMIT** file này lên Git/GitHub (đã có trong `.gitignore`).
- Nếu bị lộ, hãy **XÓA KEY** trong Google Cloud Console và tạo key mới.

---

## 6. CHIA SẺ GOOGLE SHEET

### ❓ **Tại sao cần chia sẻ?**

Service Account là một "tài khoản máy" riêng biệt, nó **không tự động có quyền** truy cập vào Google Sheets của bạn. Bạn phải chia sẻ Sheet cho Service Account giống như chia sẻ cho một người dùng khác.

### **Bước 1: Mở Google Sheet của bạn**

1. Truy cập Google Sheets:
   ```
   https://sheets.google.com/
   ```

2. Mở Google Sheet mà bot sẽ sử dụng (VD: "ĐẶT LỆNH (100 MÃ)").

### **Bước 2: Lấy Spreadsheet ID**

1. Nhìn vào URL của Google Sheet:
   ```
   https://docs.google.com/spreadsheets/d/1abc2xyz3def4ghi5jkl6mno7pqr8stu9vwx0/edit
                                          └────────────────────────────┘
                                               ↑ Đây là Spreadsheet ID
   ```

2. **COPY Spreadsheet ID** này, bạn sẽ cần điền vào `config.ini` sau.

### **Bước 3: Chia sẻ Sheet với Service Account**

1. Click nút **"Share"** (hoặc "Chia sẻ") ở góc trên bên phải của Google Sheet.

2. Trong ô **"Add people and groups"**, paste **email của Service Account** (lấy từ Bước 4):
   ```
   qbot-service-account@your-project-id.iam.gserviceaccount.com
   ```

3. Chọn quyền: **"Editor"** (Người chỉnh sửa).
   - **Editor**: Bot có thể đọc và ghi dữ liệu vào Sheet (KHUYẾN NGHỊ).
   - **Viewer**: Bot chỉ có thể đọc, không ghi được (nếu bot chỉ đọc data).

4. **BỎ TICK** ô **"Notify people"** (không cần thông báo).

5. Click **"Share"** (hoặc "Chia sẻ") hoặc **"Send"**.

### **Bước 4: Xác nhận quyền**

1. Vào phần **"People with access"** trong Google Sheet.

2. Bạn sẽ thấy email Service Account với quyền **"Editor"**.

### 📌 **Lưu ý:**
- Nếu bot cần truy cập **nhiều Sheets**, bạn phải chia sẻ **TẤT CẢ** các Sheets đó với Service Account.
- Nếu bot báo lỗi **"Permission denied"**, kiểm tra lại xem đã chia sẻ Sheet chưa.

---

## 7. KIỂM TRA KẾT NỐI

### **Bước 1: Cấu hình config.ini**

Mở file `config.ini` và điền Spreadsheet ID:

```ini
[global]
...
; === GOOGLE SHEETS ===
spreadsheet_id = 1abc2xyz3def4ghi5jkl6mno7pqr8stu9vwx0
tab_dat_lenh = ĐẶT LỆNH (100 MÃ)
```

### **Bước 2: Chạy script kiểm tra**

**Cách 1: Dùng Python console**

```bash
cd qbot_setup
python
```

```python
import gspread
from google.oauth2.service_account import Credentials

# Load credentials
scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
creds = Credentials.from_service_account_file('credentials.json', scopes=scopes)
client = gspread.authorize(creds)

# Test connection
spreadsheet_id = '1abc2xyz3def4ghi5jkl6mno7pqr8stu9vwx0'  # Thay bằng ID của bạn
sheet = client.open_by_key(spreadsheet_id)
print(f"✅ Kết nối thành công! Sheet: {sheet.title}")

# Test read
worksheet = sheet.worksheet('ĐẶT LỆNH (100 MÃ)')
cell_value = worksheet.acell('A1').value
print(f"✅ Đọc được cell A1: {cell_value}")
```

**Cách 2: Dùng bot (nhanh hơn)**

```bash
cd qbot_setup
python -c "import gg_sheet_factory; print(gg_sheet_factory.get_dat_lenh('A1:A1'))"
```

### **Kết quả mong đợi:**

```
✅ Kết nối thành công! Sheet: ĐẶT LỆNH (100 MÃ)
✅ Đọc được cell A1: [['Symbol']]
```

### ❌ **Nếu gặp lỗi:**

Xem phần [8. Xử Lý Lỗi Thường Gặp](#8-xử-lý-lỗi-thường-gặp).

---

## 8. XỬ LÝ LỖI THƯỜNG GẶP

### 🔴 **Lỗi 1: "FileNotFoundError: credentials.json not found"**

**Nguyên nhân:** File `credentials.json` không ở đúng vị trí.

**Giải pháp:**
1. Kiểm tra file có trong thư mục `qbot_setup/` không.
2. Đảm bảo tên file là **đúng chính xác**: `credentials.json` (không phải `credentials.json.txt` hay tên khác).
3. Chạy lệnh để kiểm tra:
   ```bash
   cd qbot_setup
   dir | findstr credentials.json   # Windows
   ls | grep credentials.json        # Mac/Linux
   ```

---

### 🔴 **Lỗi 2: "gspread.exceptions.APIError: API has not been used in project"**

**Nguyên nhân:** Google Sheets API chưa được bật trong project.

**Giải pháp:**
1. Quay lại [Bước 3: Bật Google Sheets API](#3-bật-google-sheets-api).
2. Đảm bảo bạn đang ở **đúng project** khi enable API.
3. Đợi 1-2 phút sau khi enable rồi thử lại.

---

### 🔴 **Lỗi 3: "gspread.exceptions.SpreadsheetNotFound"**

**Nguyên nhân:** Spreadsheet ID sai hoặc chưa chia sẻ với Service Account.

**Giải pháp:**
1. Kiểm tra lại **Spreadsheet ID** trong `config.ini` có đúng không.
2. Kiểm tra đã chia sẻ Sheet với Service Account chưa (xem [Bước 6](#6-chia-sẻ-google-sheet)).
3. Thử copy lại Spreadsheet ID từ URL của Google Sheet.

---

### 🔴 **Lỗi 4: "gspread.exceptions.APIError: PERMISSION_DENIED"**

**Nguyên nhân:** Service Account chưa có quyền truy cập vào Sheet.

**Giải pháp:**
1. Mở Google Sheet, click **"Share"**.
2. Kiểm tra email Service Account có trong danh sách **"People with access"** không.
3. Nếu chưa có, thêm email Service Account với quyền **"Editor"**.
4. Nếu đã có nhưng vẫn lỗi, thử **xóa và thêm lại**.

---

### 🔴 **Lỗi 5: "gspread.exceptions.WorksheetNotFound"**

**Nguyên nhân:** Tên tab (worksheet) trong Sheet không đúng.

**Giải pháp:**
1. Mở Google Sheet, kiểm tra tên tab có đúng không.
2. Kiểm tra `tab_dat_lenh` trong `config.ini`:
   ```ini
   tab_dat_lenh = ĐẶT LỆNH (100 MÃ)
   ```
3. **Lưu ý:** Tên tab phải **chính xác 100%**, bao gồm dấu cách, dấu ngoặc, chữ hoa/thường.

---

### 🔴 **Lỗi 6: "Invalid JSON in credentials.json"**

**Nguyên nhân:** File `credentials.json` bị lỗi định dạng hoặc không phải file JSON hợp lệ.

**Giải pháp:**
1. Mở file `credentials.json` bằng Notepad, kiểm tra xem có bị lỗi format không.
2. Nếu file bị lỗi, **xóa** và **download lại** từ Google Cloud Console.
3. Không được **chỉnh sửa** nội dung file `credentials.json` bằng tay.

---

### 🔴 **Lỗi 7: "Rate limit exceeded"**

**Nguyên nhân:** Bot gọi Google Sheets API quá nhiều lần trong thời gian ngắn.

**Giải pháp:**
1. Google Sheets API Free tier có giới hạn: **100 requests / 100 seconds / user**.
2. Tăng `delay_*` trong `config.ini` để giảm tần suất gọi API:
   ```ini
   delay_vao_lenh = 120          ; Tăng từ 60 lên 120 giây
   delay_update_price = 180      ; Tăng từ 120 lên 180 giây
   ```
3. Hoặc nâng cấp lên **Google Workspace** để có quota cao hơn.

---

### 🔴 **Lỗi 8: "This service account has been deleted"**

**Nguyên nhân:** Service Account đã bị xóa trong Google Cloud Console.

**Giải pháp:**
1. Quay lại Google Cloud Console → **Credentials**.
2. Tạo lại Service Account mới (xem [Bước 4](#4-tạo-service-account)).
3. Download `credentials.json` mới và thay thế file cũ.
4. **Chia sẻ lại** Google Sheet với Service Account mới.

---

## 📚 TÀI LIỆU THAM KHẢO

### 🌐 **Official Documentation:**

- [Google Sheets API Overview](https://developers.google.com/sheets/api)
- [Service Accounts - Google Cloud](https://cloud.google.com/iam/docs/service-accounts)
- [gspread Documentation](https://docs.gspread.org/)

### 🎥 **Video Hướng Dẫn:**

- [Google Sheets API - Python Tutorial (English)](https://www.youtube.com/watch?v=vISRn5qFrkM)
- [How to Create Google Service Account (English)](https://www.youtube.com/watch?v=VIWkeKZF3M0)

### 💡 **Tips & Tricks:**

1. **Đặt tên Service Account có ý nghĩa** để dễ quản lý khi có nhiều projects.
2. **Backup credentials.json** vào nơi an toàn (USB, cloud storage riêng tư).
3. **Kiểm tra quyền định kỳ** nếu bot đột ngột không truy cập được Sheet.
4. **Tạo Service Account riêng** cho mỗi bot/project để dễ thu hồi quyền khi cần.

---

## 📞 HỖ TRỢ

Nếu bạn gặp vấn đề không có trong hướng dẫn này, vui lòng:

1. **Kiểm tra lại từng bước** trong hướng dẫn.
2. **Đọc phần "Xử Lý Lỗi Thường Gặp"** ở trên.
3. **Liên hệ support** với các thông tin sau:
   - Screenshot lỗi (che thông tin nhạy cảm như Project ID, email)
   - Bước nào bạn đang gặp lỗi
   - Nội dung file log (nếu có)

📧 **Email:** support@deepview.vn  
💬 **Telegram:** @DeepViewJSC_Support  
🌐 **Website:** www.deepview.vn

---

## ✅ CHECKLIST HOÀN THÀNH

Sau khi hoàn thành tất cả các bước, hãy kiểm tra:

- [ ] ✅ Đã tạo Google Cloud Project
- [ ] ✅ Đã bật Google Sheets API
- [ ] ✅ Đã tạo Service Account
- [ ] ✅ Đã download `credentials.json` và đặt vào thư mục `qbot_setup/`
- [ ] ✅ Đã chia sẻ Google Sheet với Service Account (quyền Editor)
- [ ] ✅ Đã điền Spreadsheet ID vào `config.ini`
- [ ] ✅ Đã test kết nối thành công
- [ ] ✅ Bot có thể đọc dữ liệu từ Google Sheet

**Nếu tất cả đều ✅, bạn đã sẵn sàng chạy bot!** 🎉

---

© 2026 DeepView JSC. All rights reserved.

