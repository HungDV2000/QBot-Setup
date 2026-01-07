# 🧹 HƯỚNG DẪN XÓA THỦ CÔNG THƯ VIỆN PYTHON

> **Sử dụng khi:** Script tự động không xóa hết thư viện, hoặc muốn xóa thủ công từng package

---

## 📋 MỤC LỤC

1. [Phương pháp 1: Xóa tất cả thư viện (Khuyến nghị)](#phương-pháp-1-xóa-tất-cả-thư-viện)
2. [Phương pháp 2: Xóa từng thư viện cụ thể](#phương-pháp-2-xóa-từng-thư-viện-cụ-thể)
3. [Phương pháp 3: Xóa theo requirements.txt](#phương-pháp-3-xóa-theo-requirementstxt)
4. [Kiểm tra kết quả](#kiểm-tra-kết-quả)
5. [Xử lý lỗi thường gặp](#xử-lý-lỗi-thường-gặp)

---

## 🚀 PHƯƠNG PHÁP 1: XÓA TẤT CẢ THƯ VIỆN (Khuyến nghị)

### Cách 1: Sử dụng pip freeze (Tốt nhất)

**Bước 1:** Mở Command Prompt

**Bước 2:** Chạy lệnh sau để xóa TOÀN BỘ packages:

```bash
pip freeze > packages_to_remove.txt
pip uninstall -r packages_to_remove.txt -y
del packages_to_remove.txt
```

**Giải thích:**
- `pip freeze` → Liệt kê tất cả packages đã cài
- `pip uninstall -r ... -y` → Xóa tất cả (-y = yes, không hỏi)
- `del ...` → Xóa file tạm

---

### Cách 2: Xóa từng package (Nếu Cách 1 lỗi)

**Bước 1:** Lấy danh sách packages:

```bash
pip list
```

**Bước 2:** Xóa từng package (trừ pip, setuptools, wheel):

```bash
pip uninstall ccxt -y
pip uninstall gspread -y
pip uninstall pandas -y
pip uninstall numpy -y
pip uninstall python-telegram-bot -y
pip uninstall requests -y
pip uninstall google-auth -y
pip uninstall google-auth-httplib2 -y
pip uninstall google-auth-oauthlib -y
pip uninstall google-api-python-client -y
pip uninstall pytz -y
pip uninstall python-dateutil -y
pip uninstall pyinstaller -y
```

⚠️ **Lưu ý:** KHÔNG xóa `pip`, `setuptools`, `wheel` (cần thiết cho Python)

---

### Cách 3: Xóa tất cả trừ system packages (An toàn nhất)

```bash
pip freeze | findstr /v /i "pip setuptools wheel" > temp_uninstall.txt
pip uninstall -r temp_uninstall.txt -y
del temp_uninstall.txt
```

---

## 🎯 PHƯƠNG PHÁP 2: XÓA TỪNG THƯ VIỆN CỤ THỂ

### Khi nào dùng?
- Chỉ muốn xóa 1 vài thư viện cụ thể
- Giữ lại một số thư viện khác

### Các thư viện của QBot:

#### 📦 **Core Trading Libraries**
```bash
pip uninstall ccxt -y
pip uninstall requests -y
```

#### 📊 **Data Processing**
```bash
pip uninstall pandas -y
pip uninstall numpy -y
pip uninstall pytz -y
pip uninstall python-dateutil -y
```

#### 💬 **Telegram Bot**
```bash
pip uninstall python-telegram-bot -y
pip uninstall telegram -y
```

#### 📑 **Google Sheets API** (5 packages)
```bash
pip uninstall gspread -y
pip uninstall google-auth -y
pip uninstall google-auth-httplib2 -y
pip uninstall google-auth-oauthlib -y
pip uninstall google-api-python-client -y
```

#### 🔧 **Build Tools**
```bash
pip uninstall pyinstaller -y
pip uninstall pyinstaller-hooks-contrib -y
```

#### 📚 **Dependencies** (tự động cài kèm)
```bash
pip uninstall urllib3 -y
pip uninstall charset-normalizer -y
pip uninstall idna -y
pip uninstall certifi -y
pip uninstall aiohttp -y
pip uninstall yarl -y
pip uninstall multidict -y
pip uninstall frozenlist -y
pip uninstall async-timeout -y
pip uninstall aiosignal -y
pip uninstall attrs -y
```

---

## 📝 PHƯƠNG PHÁP 3: XÓA THEO REQUIREMENTS.TXT

### Bước 1: Vào thư mục chứa requirements.txt

```bash
cd C:\qbot_setup
```

### Bước 2: Xóa packages trong requirements.txt

```bash
pip uninstall -r requirements.txt -y
```

⚠️ **Lưu ý:** Cách này có thể KHÔNG xóa hết dependencies đã cài kèm!

---

## ✅ KIỂM TRA KẾT QUẢ

### Kiểm tra packages còn lại:

```bash
pip list
```

**Kết quả mong đợi:** Chỉ còn lại:
```
Package    Version
---------- -------
pip        24.x.x
setuptools 65.x.x
wheel      0.x.x
```

### Kiểm tra chi tiết package cụ thể:

```bash
pip show ccxt
```

**Kết quả mong đợi:** `WARNING: Package(s) not found: ccxt`

---

## 🔧 XỬ LÝ LỖI THƯỜNG GẶP

### 🔴 Lỗi: "Permission denied"

**Nguyên nhân:** Thiếu quyền Administrator

**Giải pháp:**
1. Đóng Command Prompt
2. Chuột phải vào **Command Prompt**
3. Chọn **"Run as Administrator"**
4. Chạy lại lệnh

---

### 🔴 Lỗi: "Cannot uninstall ... because it is required by ..."

**Nguyên nhân:** Package là dependency của package khác

**Giải pháp 1:** Xóa cả 2 packages cùng lúc
```bash
pip uninstall package1 package2 -y
```

**Giải pháp 2:** Xóa package cha trước
```bash
pip uninstall ccxt -y
pip uninstall urllib3 -y
```

**Giải pháp 3:** Force uninstall (⚠️ Cẩn thận!)
```bash
pip uninstall package --yes --break-system-packages
```

---

### 🔴 Lỗi: "pip is not recognized"

**Nguyên nhân:** Python chưa được thêm vào PATH

**Giải pháp:**
```bash
python -m pip uninstall package -y
```

Hoặc thêm Python vào PATH:
1. Tìm đường dẫn Python: `where python`
2. Thêm vào PATH qua System Environment Variables

---

### 🔴 Lỗi: Package không xóa được (đang được sử dụng)

**Nguyên nhân:** Bot hoặc Python script đang chạy

**Giải pháp:**
1. Dừng tất cả bot: `stop_all_bots.bat`
2. Đóng tất cả Python processes:
   ```bash
   taskkill /f /im python.exe
   ```
3. Chạy lại lệnh uninstall

---

### 🟡 Cảnh báo: "Successfully uninstalled but cannot remove..."

**Nguyên nhân:** File đang bị lock hoặc không có quyền

**Giải pháp:**
1. Khởi động lại máy
2. Chạy lại lệnh với quyền Administrator
3. Xóa thủ công folder package trong:
   ```
   C:\Users\<User>\AppData\Local\Programs\Python\Python311\Lib\site-packages\
   ```

---

## 🧪 SCRIPT TỰ ĐỘNG XÓA THỦ CÔNG

Tạo file `manual_uninstall.bat` với nội dung:

```batch
@echo off
echo ========================================
echo XOA THU CONG THU VIEN PYTHON
echo ========================================
echo.

echo [1/3] Dang lay danh sach packages...
pip freeze > packages_temp.txt

echo [2/3] Dang xoa tat ca packages (tru pip, setuptools, wheel)...
pip freeze | findstr /v /i "pip setuptools wheel" > uninstall_temp.txt
pip uninstall -r uninstall_temp.txt -y

echo [3/3] Dang don dep...
del packages_temp.txt
del uninstall_temp.txt

echo.
echo ========================================
echo HOAN TAT!
echo ========================================
echo.

echo Kiem tra packages con lai:
pip list

pause
```

**Cách dùng:**
1. Copy nội dung trên vào file `manual_uninstall.bat`
2. Lưu vào folder `qbot_setup\setup`
3. Chuột phải → **Run as Administrator**

---

## 📌 KIỂM TRA TOÀN DIỆN

### Script kiểm tra packages QBot còn lại:

```bash
@echo off
echo Kiem tra cac package cua QBot...
echo.

set packages=ccxt gspread pandas numpy python-telegram-bot requests google-auth pytz pyinstaller

for %%p in (%packages%) do (
    pip show %%p >nul 2>&1
    if errorlevel 1 (
        echo [  OK  ] %%p - Da xoa
    ) else (
        echo [CANH BAO] %%p - VAN CON!
    )
)

echo.
pause
```

---

## 🔄 CÀI LẠI SAU KHI XÓA

### Sau khi xóa xong, cài lại:

```bash
cd qbot_setup
pip install -r requirements.txt
```

Hoặc dùng script tự động:

```bash
cd qbot_setup\setup
1_setup_install.bat
```

→ Chọn option **[3] CHỈ CÀI THƯ VIỆN PYTHON**

---

## 💡 TIPS & TRICKS

### 1. Tạo file danh sách packages trước khi xóa (backup)

```bash
pip freeze > packages_backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%.txt
```

### 2. So sánh packages trước và sau

```bash
pip list --format=freeze > before.txt
REM ... xóa packages ...
pip list --format=freeze > after.txt
fc before.txt after.txt
```

### 3. Xem dependencies của 1 package

```bash
pip show ccxt
```

→ Xem mục `Requires:` để biết dependencies

### 4. Xóa cache pip (tiết kiệm dung lượng)

```bash
pip cache purge
```

---

## ⚠️ CẢNH BÁO

### ❌ KHÔNG XÓA CÁC PACKAGES SAU:

| Package | Lý do |
|---------|-------|
| `pip` | Package manager, cần để cài packages |
| `setuptools` | Build tools, cần cho pip |
| `wheel` | Build format, cần cho pip |

### ❌ KHÔNG CHẠY:

```bash
pip uninstall pip -y  # ❌ KHÔNG BAO GIỜ LÀM!
```

→ Nếu xóa nhầm, phải cài lại Python!

---

## 🎯 TÓM TẮT NHANH

**Xóa tất cả packages nhanh nhất:**

```bash
pip freeze | findstr /v /i "pip setuptools wheel" > temp.txt && pip uninstall -r temp.txt -y && del temp.txt
```

**Kiểm tra đã xóa hết chưa:**

```bash
pip list
```

**Cài lại từ đầu:**

```bash
cd qbot_setup
pip install -r requirements.txt
```

---

<div align="center">

**QBot v2.1** - Manual Library Uninstall Guide  
📧 support@deepview.vn | 💬 @deepview_support

*Last Updated: January 2026*

</div>

