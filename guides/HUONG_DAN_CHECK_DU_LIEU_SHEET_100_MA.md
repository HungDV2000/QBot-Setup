# 📊 HƯỚNG DẪN CHECK DỮ LIỆU SHEET "100 MÃ"

> **Mục đích:** Hướng dẫn nhanh cách check/verify dữ liệu trong sheet "100 mã (50 tăng và 50 giảm)" với Binance.

---

## 📋 BẢNG GIẢI THÍCH CÁC CỘT

| Cột | Tên | Ý nghĩa | Cách check trên Binance |
|-----|-----|---------|------------------------|
| **A** | Mã | Symbol (VD: BTC/USDT) | Tìm trực tiếp trên Binance Futures |
| **B** | % 24h | % thay đổi giá 24h | Tab "24h Change" trên Binance |
| **C** | Giá trị hiện thời | Giá hiện tại | Giá Last/Mark Price trên chart |
| **D-E** | BB1h trên/dưới | Bollinger Bands khung 1h | TradingView: Chọn 1H + indicator "Bollinger Bands (20,2)" |
| **F-G** | BB1 ngày trên/dưới | Bollinger Bands khung 1D | TradingView: Chọn 1D + indicator "Bollinger Bands (20,2)" |
| **H-I** | Biên độ 1h max tăng/giảm tuần | Biên độ % lớn nhất trong 7 ngày (nến 1h) | Xem 168 nến 1h gần nhất, tìm nến có (High-Low)/Open lớn nhất |
| **J-K** | Max/Min 40 ngày | Giá cao/thấp nhất 40 ngày | Chart 1D, nhìn 40 nến gần nhất |
| **L-M** | Max tăng/giảm 4h/60 ngày | % thay đổi lớn nhất nến 4h trong 60 ngày | Xem nến 4h, tìm nến có (Close-Open)/Open lớn nhất |
| **N-O** | Giá Cao/Thấp Nhất | BB 1 tuần (upper/lower) | TradingView: Chọn 1W + indicator "Bollinger Bands (20,2)" |
| **P-Q** | Biên độ 30d tăng/giảm | Biên độ % lớn nhất nến 1D trong 30 ngày | Xem 30 nến 1D, tìm nến có (High-Low)/Open lớn nhất |
| **R** | Volume 24h | Tổng volume 24h (USDT) | Binance: Tab "Volume 24h" |
| **S** | RSI 14 | Chỉ số RSI (14 nến 1D) | TradingView: Chọn 1D + indicator "RSI (14)" |
| **U** | Min/Min40 | Tỷ lệ BB1w lower / Min 40 ngày | (Cột O) / (Cột K) |
| **V-W** | % đến BB1h trên/dưới | Khoảng cách từ giá hiện tại đến BB1h | ((BB1h - Giá) / Giá) * 100 |
| **X-Y** | Vol 1h/4h | Volume nến gần nhất khung 1h/4h | Binance: Chọn 1H hoặc 4H, xem volume nến cuối |
| **AB** | Biên độ giá ngày lớn nhất | Biên độ % lớn nhất 1 ngày trong 365 ngày | Xem 365 nến 1D, tìm nến có (High-Low)/Open lớn nhất |
| **AC** | Ngày biên độ lớn nhất | Ngày xảy ra biên độ lớn nhất | Timestamp của nến tại AB |

---

## 🔍 HƯỚNG DẪN CHECK CỤ THỂ

### **⚡ BƯỚC 0: BẬT INDICATORS TRÊN BINANCE (Chỉ làm 1 lần)**

**Hướng dẫn chi tiết có hình:**

```
┌─────────────────────────────────────────────────────────────┐
│  BINANCE FUTURES                                    [Deposit]│
├─────────────────────────────────────────────────────────────┤
│  BTCUSDT     ↑ +2.5%     Last: 50,000   Vol: 1.25B         │
├─────────────────────────────────────────────────────────────┤
│  Chart Tools:  [📈] [⚙️] [🔍] [📊 Indicators] ← CLICK VÀO ĐÂY│
│                                                              │
│  ┌──────────────────────────────────────────────┐          │
│  │  Indicators Menu                             │          │
│  ├──────────────────────────────────────────────┤          │
│  │  Search: [Bollinger Bands________] 🔍       │          │
│  │                                               │          │
│  │  ✅ Bollinger Bands (BB)          [+ Add]    │← CLICK ADD│
│  │     Length: 20, StdDev: 2                    │          │
│  │                                               │          │
│  │  ✅ RSI (Relative Strength Index) [+ Add]    │← CLICK ADD│
│  │     Length: 14                               │          │
│  │                                               │          │
│  │  Moving Average (MA)                         │          │
│  │  MACD                                         │          │
│  │  ... (các indicators khác)                   │          │
│  └──────────────────────────────────────────────┘          │
│                                                              │
│  [CHART SẼ HIỂN THỊ 3 ĐƯỜNG BOLLINGER BANDS]               │
│  [RSI SẼ HIỂN THỊ Ở PHÍA DƯỚI CHART]                       │
└─────────────────────────────────────────────────────────────┘
```

**Các bước:**
1. Vào: https://www.binance.com/en/futures/BTCUSDT
2. Nhìn phía **trên chart**, tìm nút **"Indicators"** (hoặc biểu tượng 📊)
3. Click vào → Popup menu hiện ra
4. Tìm **"Bollinger Bands"** → Click **"+ Add"**
   - Nếu popup Settings, check: Length=20, StdDev=2 → OK
5. Tìm **"RSI"** → Click **"+ Add"**
   - Nếu popup Settings, check: Length=14 → OK
6. Đóng menu Indicators
7. **XONG!** Chart giờ sẽ hiển thị:
   - 3 đường BB (upper, middle, lower) trên chart
   - Biểu đồ RSI phía dưới chart

**💡 Mẹo:** Sau khi thêm lần đầu, Binance sẽ **LƯU CÀI ĐẶT**. Lần sau chỉ cần chuyển timeframe (1H, 1D, 1W) là xong!

---

### **1. Check Giá & % 24h (Cột B, C)**

**Trên Binance:**
```
1. Vào Binance Futures: https://www.binance.com/en/futures/BTCUSDT
2. Xem góc phải trên:
   - Last Price = Cột C
   - 24h Change % = Cột B
```

**Ví dụ:**
- Cột C (Giá hiện tại): `50,000 USDT`
- Cột B (% 24h): `+2.5%`
- ✅ Check: Giá trên Binance = 50,000 và % 24h = +2.5%

---

### **2. Check Bollinger Bands (Cột D-G, N-O)**

**✅ CÁCH 1: Trên Binance (KHUYÊN DÙNG)**
```
1. Vào: https://www.binance.com/en/futures/BTCUSDT
2. Chọn timeframe: 1H (cho cột D-E), 1D (cho F-G), hoặc 1W (cho N-O)
3. Nhìn chart, sẽ thấy 3 đường:
   - Đường TRÊN (màu xanh/đỏ nhạt) = Upper Band (BB trên)
   - Đường GIỮA = SMA(20)
   - Đường DƯỚI (màu xanh/đỏ nhạt) = Lower Band (BB dưới)
4. Di chuột qua nến cuối cùng, sẽ hiện giá trị BB upper/lower
```

**Ví dụ BB 1H (Cột D-E):**
- Cột D (BB1h trên): `51,000`
- Cột E (BB1h dưới): `49,000`
- ✅ Check: Binance chart 1H → Di chuột qua nến cuối → BB upper=51k, lower=49k

**🔄 CÁCH 2: TradingView (Dự phòng)**
```
1. Mở: https://www.tradingview.com/chart/
2. Nhập: BTCUSDT
3. Chọn timeframe: 1H, 1D, hoặc 1W
4. Click biểu tượng "fx" → Tìm "Bollinger Bands"
5. Settings: Length=20, StdDev=2
```

---

### **3. Check Max/Min 40 ngày (Cột J-K)**

**Trên Binance:**
```
1. Vào Binance Futures chart
2. Chọn timeframe: 1D
3. Zoom out để thấy 40 nến
4. Nhìn:
   - Giá cao nhất (đỉnh) = Cột J
   - Giá thấp nhất (đáy) = Cột K
```

**Ví dụ:**
- Cột J (Max 40 ngày): `55,000`
- Cột K (Min 40 ngày): `45,000`
- ✅ Check: Trong 40 ngày qua, đỉnh là 55k, đáy là 45k

---

### **4. Check Volume 24h (Cột R)**

**Trên Binance:**
```
1. Vào Binance Futures
2. Xem "Volume 24h (USDT)" ở góc phải trên
3. So sánh với Cột R
```

**Ví dụ:**
- Cột R (Volume 24h): `1,250,000,000` (1.25 tỷ USDT)
- ✅ Check: Binance hiển thị "Vol 24h: 1.25B USDT"

---

### **5. Check RSI 14 (Cột S)**

**✅ CÁCH 1: Trên Binance (KHUYÊN DÙNG)**
```
1. Vào: https://www.binance.com/en/futures/BTCUSDT
2. Chọn timeframe: 1D (cho RSI tính theo ngày)
3. Nhìn phần DƯỚI chart → Sẽ thấy biểu đồ RSI (đường màu tím/vàng)
4. Xem giá trị ở nến cuối cùng (thường có số hiển thị)
5. Hoặc di chuột qua nến cuối → Popup sẽ hiện "RSI: 65.5"
```

**Ví dụ:**
- Cột S (RSI 14): `65.5`
- ✅ Check: Binance chart 1D → RSI ở nến cuối = 65.5

**🔄 CÁCH 2: TradingView (Dự phòng)**
```
1. Mở: https://www.tradingview.com/chart/
2. Nhập: BTCUSDT
3. Chọn timeframe: 1D
4. Click "fx" → Tìm "RSI"
5. Settings: Length=14
```

---

### **6. Check Volume 1h/4h (Cột X-Y)**

**Trên Binance:**
```
1. Vào Binance Futures chart
2. Chọn timeframe: 1H (hoặc 4H)
3. Nhìn nến cuối cùng (đang chạy)
4. Xem con số volume dưới nến (màu xanh/đỏ)
```

**Ví dụ:**
- Cột X (Vol 1h): `25,000,000` (25 triệu)
- Cột Y (Vol 4h): `95,000,000` (95 triệu)
- ✅ Check: Nến 1H cuối = 25M, nến 4H cuối = 95M

---

### **7. Check Biên độ giá ngày lớn nhất (Cột AB-AC)**

**Trên TradingView hoặc Binance:**
```
1. Chọn timeframe: 1D
2. Zoom out để thấy 365 nến (1 năm)
3. Tìm nến có (High - Low) / Open lớn nhất
4. Tính % biên độ: ((High - Low) / Open) * 100
5. Ghi nhận ngày của nến đó
```

**Ví dụ:**
- Cột AB (Biên độ max): `25.8%`
- Cột AC (Ngày): `2025-11-15`
- ✅ Check: Ngày 15/11/2025, nến 1D có biên độ 25.8%

---

## 📌 MẸO KIỂM TRA NHANH

### **⚡ Kiểm tra TẤT CẢ trên Binance (KHUYÊN DÙNG):**
```
1. Vào Binance Futures → Chọn symbol (VD: BTCUSDT)
2. Thêm indicators (1 lần duy nhất):
   - Bollinger Bands (20,2)
   - RSI (14)
3. Chuyển timeframe (1H, 1D, 1W) để check từng loại data
4. Di chuột qua nến cuối → Xem tất cả giá trị
```
**→ Tất cả data đều có trên Binance, không cần dùng TradingView!**

### **Kiểm tra tổng quan:**
1. **Giá & % 24h:** Góc phải trên Binance
2. **BB & RSI:** Chart Binance (sau khi bật indicators)
3. **Volume:** Chart Binance (cột dưới mỗi nến)
4. **Max/Min 40d:** Zoom out chart 1D

### **Kiểm tra độ chính xác:**
- ✅ **Sai số cho phép:** ±1% (do làm tròn và thời điểm lấy data)
- ✅ **Nếu sai số > 2%:** Kiểm tra lại hoặc report bug

### **Lưu ý:**
- Dữ liệu sheet **CẬP NHẬT mỗi 2-5 phút** (config: `delay_update_all`)
- Binance data **realtime**, có thể chênh lệch vài giây
- Timestamp ở **cột A1** của sheet = thời điểm cập nhật

---

## 🔗 LINKS HỮU ÍCH

- **Binance Futures:** https://www.binance.com/en/futures/
- **TradingView:** https://www.tradingview.com/chart/
- **Binance API Docs:** https://binance-docs.github.io/apidocs/futures/en/

---

## 📝 VÍ DỤ ĐẦY ĐỦ: CHECK BTC/USDT (100% TRÊN BINANCE)

### **Dữ liệu trên Sheet:**
```
A: BTC/USDT
B: +2.5%
C: 50,000
D: 51,000 (BB1h trên)
E: 49,000 (BB1h dưới)
J: 55,000 (Max 40d)
K: 45,000 (Min 40d)
R: 1,250,000,000 (Vol 24h)
S: 65.5 (RSI 14)
```

### **Cách check (TẤT CẢ trên Binance):**

**Bước 0: Setup (chỉ làm 1 lần)**
```
1. Vào: https://www.binance.com/en/futures/BTCUSDT
2. Click nút "Indicators" phía trên chart
3. Thêm: Bollinger Bands (20,2) và RSI (14)
4. Xong! Giờ chỉ cần chuyển timeframe
```

**Bước 1: Check Giá & % 24h**
- Nhìn góc phải trên:
  - Last Price = **50,000** ✅ (Cột C)
  - 24h Change = **+2.5%** ✅ (Cột B)

**Bước 2: Check BB 1H**
- Chuyển timeframe sang **1H**
- Di chuột qua nến cuối cùng:
  - BB Upper = **51,000** ✅ (Cột D)
  - BB Lower = **49,000** ✅ (Cột E)

**Bước 3: Check Max/Min 40d**
- Chuyển timeframe sang **1D**
- Zoom out để thấy 40 nến
- Nhìn:
  - Đỉnh cao nhất = **55,000** ✅ (Cột J)
  - Đáy thấp nhất = **45,000** ✅ (Cột K)

**Bước 4: Check Volume 24h**
- Nhìn góc phải trên:
  - Vol 24h = **1.25B USDT** ✅ (Cột R)

**Bước 5: Check RSI 14**
- Timeframe vẫn ở **1D**
- Nhìn phần dưới chart (biểu đồ RSI):
  - RSI = **65.5** ✅ (Cột S)

**⏱️ Tổng thời gian: 2-3 phút cho tất cả các cột!**

---

## ❓ TROUBLESHOOTING

### **Q1: Không thấy Bollinger Bands / RSI trên Binance chart?**
- **A:** Phải thêm indicators thủ công:
  1. Click nút **"Indicators"** (biểu tượng fx/zigzag) phía trên chart
  2. Tìm "Bollinger Bands" → Click "Add"
  3. Tìm "RSI" → Click "Add"
  4. Settings: BB (20,2), RSI (14)

### **Q2: Dữ liệu sheet khác Binance vài %?**
- **A:** Bình thường! Sheet cập nhật mỗi 2-5 phút, chênh lệch ±1% là OK.

### **Q3: BB trên Binance khác sheet nhiều?**
- **A:** Kiểm tra:
  - ✅ Timeframe đúng chưa? (1H cho D-E, 1D cho F-G, 1W cho N-O)
  - ✅ Settings BB: Length=20, StdDev=2?
  - ✅ Đang di chuột qua nến cuối cùng?

### **Q4: Volume khác nhiều?**
- **A:** Volume thay đổi **mỗi giây**. Check timestamp ở A1 để biết thời điểm bot lấy data.

### **Q5: RSI không hiển thị số?**
- **A:** Di chuột qua nến cuối cùng trên chart, popup sẽ hiện giá trị RSI.

### **Q6: Làm sao biết data đúng hay sai?**
- **A:** Nếu **>80% cột đúng** = Bot hoạt động tốt. Nếu **>50% sai** = Bug, cần fix.

### **Q7: Binance chart có thể thay thế TradingView không?**
- **A:** **HOÀN TOÀN ĐƯỢC!** Binance có đầy đủ tất cả indicators cần thiết. TradingView chỉ là phương án dự phòng.

---

**📅 Last Updated:** 2026-01-12  
**🤖 Bot Version:** hd_update_all.py v2.0
