# Danh Sách Các Bot Trading

Tài liệu này liệt kê các bot trong hệ thống trading, nhiệm vụ và quy trình cơ bản của từng bot.

---

## 1. hd_update_all.py

**Nhiệm vụ:** Cập nhật dữ liệu cho sheet "100 mã (50 tăng và 50 giảm)"

**Quy trình cơ bản:**
1. Lấy tất cả tickers từ Binance
2. Lọc symbols Futures USDT (theo whitelist từ sheet "list" nếu có)
3. Kiểm tra tính hợp lệ của symbols (loại bỏ mã mới listing/không đủ data)
4. Tính toán % thay đổi 24h và sắp xếp
5. Lấy top 50 giảm và top 50 tăng
6. Với mỗi symbol, tính toán 29 cột dữ liệu (A-AC):
   - Giá hiện tại, % 24h
   - Bollinger Bands (1h, 1d, 1 tuần)
   - Biên độ giá (1h, 4h, 30 ngày)
   - Giá cao/thấp (40 ngày)
   - Volume, RSI
   - Biên độ giá ngày lớn nhất
7. Cập nhật vào Google Sheet "100 mã (50 tăng và 50 giảm)"
8. Chạy theo lịch định kỳ (mỗi X giây từ `cst.delay_update_all`)

**Log file:** `logs/hd_update_all_dd_mm_yyyy_H_M_S.txt`

---

## 2. hd_order.py

**Nhiệm vụ:** Đặt lệnh TRAILING_STOP (lệnh 1 - Entry) dựa trên trạng thái B2

**Quy trình cơ bản:**
1. Đọc trạng thái từ B2 (LONG/SHORT/CHỜ/STOP)
2. Xử lý các lệnh đặc biệt:
   - **STOP**: Đóng tất cả positions và hủy tất cả orders
   - **XÓA CHỜ**: Hủy tất cả lệnh pending, giữ vị thế
   - **XÓA VỊ THẾ**: Đóng tất cả positions, giữ lệnh chờ
3. Nếu trạng thái = LONG/SHORT:
   - Đọc danh sách symbols từ sheet "Đặt lệnh 100 mã" (hàng 4-53 cho SHORT, 55-104 cho LONG)
   - Với mỗi symbol có Leverage ≠ 0 và ≠ "N":
     - Kiểm tra symbol có cho phép giao dịch không
     - Kiểm tra đã có vị thế chưa (tránh trùng lặp)
     - Kiểm tra đã có lệnh TRAILING_STOP pending chưa
     - Tính toán vốn từ cột H hoặc E2
     - Đặt lệnh TRAILING_STOP với activation price và callback rate
4. Chạy theo lịch định kỳ (mỗi X giây từ `cst.delay_vao_lenh`)

**Log file:** `logs/hd_order_dd_mm_yyyy_H_M_S.txt`

---

## 3. hd_order_123.py

**Nhiệm vụ:** Đặt lệnh SL/TP (lệnh 2 và 3) cho các positions đã khớp

**Quy trình cơ bản:**
1. Đọc sheet "Chờ và khớp" (cột A-K, hàng 4-1000)
2. Với mỗi dòng có "Đã khớp/Mở vị thế" = "Y":
   - Kiểm tra cột G (SL) và H (TP) - nếu đã có cả 2 thì bỏ qua
   - Lấy rate SL/TP từ cột J, K (ưu tiên) hoặc config (fallback)
   - Lấy position amount từ Binance
   - Đặt lệnh SL và/hoặc TP lẻ (có thể chỉ SL hoặc chỉ TP)
3. Gửi thông báo Telegram khi tạo lệnh thành công
4. Chạy theo lịch định kỳ (mỗi X giây từ `cst.delay_vao_lenh_123`)

**Log file:** `logs/hd_order_123_dd_mm_yyyy_H_M_S.txt`

---

## 4. hd_update_cho_va_khop.py

**Nhiệm vụ:** Cập nhật trạng thái "Chờ và khớp" vào Google Sheet

**Quy trình cơ bản:**
1. Lấy positions đang mở từ Binance (dùng `fetch_positions()` để có entryPrice)
2. Với mỗi position:
   - Xác định LONG/SHORT
   - Lấy entry price, leverage, unrealized PnL
   - Kiểm tra SL/TP orders (quét cả algo orders và open orders)
   - Ghi vào sheet: Symbol, Side, Chờ khớp (N), Đã khớp (Y), Entry, Leverage, SL (Y/N), TP (Y/N)
3. Lấy orders chờ khớp (entry orders - chỉ có 1 order pending)
4. Với mỗi order chờ khớp:
   - Ghi vào sheet: Symbol, Side, Chờ khớp (Y), Đã khớp (N), Price, Leverage (N)
5. Cập nhật timestamp vào A2
6. Chạy theo lịch định kỳ (mỗi X giây từ `cst.delay_cho_va_khop`)

**Log file:** `logs/cho_va_khop_dd_mm_yyyy_H_M_S_error.txt` và `cho_va_khop_dd_mm_yyyy_H_M_S_info.txt`

---

## 5. hd_alert_possition_and_open_order.py

**Nhiệm vụ:** Monitor positions và xử lý cascade khi TP/SL khớp

**Quy trình cơ bản:**
1. So sánh positions hiện tại với lần scan trước
2. Phát hiện position mới mở:
   - Gửi thông báo Telegram
3. Phát hiện position đã đóng:
   - Phân biệt TP/SL dựa trên PnL (profit = TP, loss = SL)
   - Lấy layer hiện tại từ sheet
   - Gọi cascade manager: `on_tp_filled()` hoặc `on_sl_filled()`
   - Gửi thông báo đóng position
   - Hủy tất cả lệnh chờ còn lại
4. Chạy theo lịch định kỳ (mỗi X giây từ `cst.delay_calert_possition_and_open_order`)

**Log file:** `logs/hd_alert_possition_and_open_order_dd_mm_yyyy_H_M_S.txt`

---

## 6. hd_cancel_orders_schedule.py

**Nhiệm vụ:** Hủy tất cả orders theo lịch định kỳ

**Quy trình cơ bản:**
1. Đọc danh sách symbols từ sheet "Chờ và khớp" (cột A, hàng 3-100)
2. Với mỗi symbol:
   - Hủy tất cả algo orders (TRAILING_STOP, STOP_MARKET, etc.) qua API trực tiếp
   - Hủy tất cả open orders thông thường
3. Gửi thông báo Telegram với kết quả
4. Chạy theo lịch định kỳ (mỗi X phút từ `cst.cancel_orders_minutes`)

**Log file:** `logs/hd_cancel_dd_mm_yyyy_H_M_S.txt`

---

## 7. hd_isolated_crossed_converter.py

**Nhiệm vụ:** Chuyển đổi margin type (ISOLATED ↔ CROSSED) cho USDT futures pairs

**Quy trình cơ bản:**
1. Menu lựa chọn:
   - Option 1: Chuyển TẤT CẢ symbols sang CROSS
   - Option 2: Chuyển TẤT CẢ symbols sang ISOLATED
   - Option 3: Chuyển symbols từ SHEET sang CROSS
   - Option 4: Chuyển symbols từ SHEET sang ISOLATED
2. Với mỗi symbol:
   - Kiểm tra có positions/orders đang mở không (bỏ qua nếu có)
   - Chuyển đổi margin type qua Binance API
3. Gửi thông báo Telegram với kết quả
4. Chạy một lần (interactive - yêu cầu input từ user)

**Log file:** `logs/hd_isolated_crossed_converter_dd_mm_yyyy_H_M_S.txt`

---

## 8. hd_update_danhmuc.py

**Nhiệm vụ:** Cập nhật danh mục active USDT futures pairs vào Google Sheet "Danhmuc"

**Quy trình cơ bản:**
1. Lấy danh sách active futures từ Binance (exchangeInfo)
2. Lọc các pairs đang TRADING và có giá hợp lệ
3. Loại bỏ các pairs đã delisted hoặc không trading
4. Sắp xếp danh sách
5. Cập nhật vào sheet "Danhmuc"
6. Gửi thông báo Telegram với kết quả
7. Chạy một lần (có thể tích hợp vào scheduler)

**Log file:** `logs/hd_update_danhmuc_dd_mm_yyyy_H_M_S.txt`

---

## 9. hd_order_market_price.py

**Nhiệm vụ:** Đặt lệnh TRAILING_STOP theo giá thị trường (không dùng activation price từ sheet)

**Quy trình cơ bản:**
1. Tương tự `hd_order.py` nhưng:
   - Không đọc activation price từ sheet
   - Dùng `lastPrice` (giá thị trường) làm activation price
2. Chạy theo lịch định kỳ (mỗi X giây từ `cst.delay_vao_lenh`)

**Log file:** `logs/hd_order_market_price_dd_mm_yyyy_H_M_S.txt`

---

## 10. hd_update_price.py

**Nhiệm vụ:** Cập nhật giá cho các symbols trong sheet

**Quy trình cơ bản:**
1. Đọc danh sách symbols từ sheet
2. Lấy giá hiện tại từ Binance
3. Cập nhật vào sheet
4. Chạy theo lịch định kỳ (mỗi X giây từ `cst.delay_update_price`)

**Log file:** `logs/hd_update_price_dd_mm_yyyy_H_M_S.txt`

---

## 11. hd_track_30_prices.py

**Nhiệm vụ:** Track 30 mức giá gần nhất cho các mã có Leverage ≠ 0

**Quy trình cơ bản:**
1. Quét sheet "Đặt lệnh 100 mã" (hàng 4-53 SHORT, 55-104 LONG)
2. Với mỗi mã có Leverage ≠ 0 và ≠ "N":
   - Lấy 19 mức giá gần nhất (nến 1m) từ Binance
   - Ghi vào cột I:Z (18 cột) của cùng hàng
3. Chạy theo lịch định kỳ (mỗi 1 phút)

**Log file:** `logs/hd_track_30_prices_dd_mm_yyyy_H_M_S.txt`

---

## 12. hd_periodic_report.py

**Nhiệm vụ:** Gửi báo cáo định kỳ về số dư và trạng thái

**Quy trình cơ bản:**
1. Kiểm tra số dư và positions
2. Gửi báo cáo qua Telegram khi cần
3. Chạy theo lịch định kỳ (mỗi 5 phút)

**Log file:** `logs/hd_periodic_report_dd_mm_yyyy_H_M_S.txt`

---

## Lưu ý về Log Format

Tất cả các bot đều lưu log vào thư mục `logs/` với định dạng:
- `ten_file_dd_mm_yyyy_H_M_S.txt` (ví dụ: `hd_order_16_01_2026_14_30_45.txt`)

Một số bot có log riêng cho ERROR và INFO:
- `hd_update_cho_va_khop.py`: `cho_va_khop_dd_mm_yyyy_error.txt` và `cho_va_khop_dd_mm_yyyy_info.txt`

---

## Tổng Quan Hệ Thống

**Luồng hoạt động chính:**
1. `hd_update_all.py` → Cập nhật dữ liệu 100 mã
2. `hd_order.py` → Đặt lệnh entry (TRAILING_STOP)
3. `hd_update_cho_va_khop.py` → Cập nhật trạng thái "Chờ và khớp"
4. `hd_order_123.py` → Đặt lệnh SL/TP cho positions đã khớp
5. `hd_alert_possition_and_open_order.py` → Monitor và xử lý cascade khi TP/SL khớp
6. `hd_cancel_orders_schedule.py` → Hủy orders theo lịch
7. Các bot hỗ trợ: `hd_update_danhmuc.py`, `hd_isolated_crossed_converter.py`, `hd_update_price.py`, `hd_track_30_prices.py`, `hd_periodic_report.py`
