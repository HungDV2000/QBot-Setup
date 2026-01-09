# 🚀 HƯỚNG DẪN NHANH: TẠO CREDENTIALS.JSON

> **Thời gian:** 5-7 phút  
> **Yêu cầu:** Tài khoản Google

---

## 📋 TÓM TẮT 5 BƯỚC CHÍNH

```
1. Tạo Google Cloud Project
2. Bật Google Sheets API
3. Tạo Service Account & Download credentials.json
4. Chia sẻ Google Sheet với Service Account
5. Test kết nối
```

---

## 🎯 BƯỚC 1: TẠO PROJECT

1. Truy cập: https://console.cloud.google.com/
2. Click **"Select a project"** → **"NEW PROJECT"**
3. Đặt tên: `QBot Trading`
4. Click **"CREATE"**

---

## 🎯 BƯỚC 2: BẬT API

1. Menu (☰) → **APIs & Services** → **Library**
2. Tìm: `Google Sheets API`
3. Click **"ENABLE"**

---

## 🎯 BƯỚC 3: TẠO SERVICE ACCOUNT

1. Menu (☰) → **APIs & Services** → **Credentials**
2. Click **"+ CREATE CREDENTIALS"** → **"Service account"**
3. Điền tên: `QBot Service Account`
4. Click **"CREATE AND CONTINUE"** → **"CONTINUE"** → **"DONE"**
5. Click vào **email Service Account** vừa tạo
6. Tab **"KEYS"** → **"ADD KEY"** → **"Create new key"** → **JSON**
7. Click **"CREATE"** → File sẽ tự động tải xuống
8. **Đổi tên** file thành `credentials.json`
9. **Copy** vào thư mục `qbot_setup/`

**📌 LƯU LẠI EMAIL NÀY:**
```
qbot-service-account@your-project.iam.gserviceaccount.com
```

---

## 🎯 BƯỚC 4: CHIA SẺ GOOGLE SHEET

1. Mở Google Sheet của bạn
2. Copy **Spreadsheet ID** từ URL:
   ```
   https://docs.google.com/spreadsheets/d/[SPREADSHEET_ID]/edit
   ```
3. Click **"Share"** ở góc phải
4. Paste **email Service Account** (từ bước 3)
5. Chọn quyền: **"Editor"**
6. **Bỏ tick** "Notify people"
7. Click **"Share"**

---

## 🎯 BƯỚC 5: CẤU HÌNH & TEST

1. Mở `config.ini`, điền Spreadsheet ID:
   ```ini
   [global]
   spreadsheet_id = YOUR_SPREADSHEET_ID_HERE
   tab_dat_lenh = ĐẶT LỆNH (100 MÃ)
   ```

2. Test kết nối:
   ```bash
   cd qbot_setup
   python -c "import gg_sheet_factory; print(gg_sheet_factory.get_dat_lenh('A1:A1'))"
   ```

3. Kết quả mong đợi:
   ```
   [['Symbol']]
   ```

---

## ❌ LỖI THƯỜNG GẶP

| Lỗi | Giải pháp |
|-----|-----------|
| **FileNotFoundError** | Kiểm tra `credentials.json` có trong thư mục `qbot_setup/` |
| **API has not been used** | Bật Google Sheets API trong Cloud Console |
| **SpreadsheetNotFound** | Kiểm tra Spreadsheet ID trong `config.ini` |
| **PERMISSION_DENIED** | Chia sẻ Sheet với email Service Account |
| **WorksheetNotFound** | Kiểm tra tên tab trong `tab_dat_lenh` |

---

## 📚 TÀI LIỆU CHI TIẾT

Xem hướng dẫn đầy đủ: [`HUONG_DAN_TAO_CREDENTIALS_GOOGLE_SHEETS.md`](./HUONG_DAN_TAO_CREDENTIALS_GOOGLE_SHEETS.md)

---

## ✅ CHECKLIST

- [ ] Đã tạo Google Cloud Project
- [ ] Đã bật Google Sheets API
- [ ] Đã download `credentials.json` vào `qbot_setup/`
- [ ] Đã chia sẻ Sheet với Service Account
- [ ] Đã điền Spreadsheet ID vào `config.ini`
- [ ] Test kết nối thành công ✅

---

© 2026 DeepView JSC

