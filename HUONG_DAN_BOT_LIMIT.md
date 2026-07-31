# 📘 Hướng dẫn dùng Bot LIMIT (bản đơn giản)

> Đọc file này là dùng được ngay. Không cần biết lập trình.

---

## 1. Bot này làm gì?

Bot tự động **đặt lệnh mua/bán trên Binance Futures** dựa theo bảng Google Sheet của bạn.

Với mỗi mã coin, bot làm 2 việc:

1. **Lệnh vào (Lệnh 1):** đặt một lệnh **LIMIT** chờ khớp ở mức giá bạn điền.
2. **Lệnh ngược (chốt lời):** sau khi lệnh vào đã khớp (đã có vị thế), bot tự đặt tiếp một lệnh **LIMIT chốt lời** ở mức giá bạn điền.

Bot quét bảng liên tục, vài giây một lần. Bạn chỉ cần **điền số vào bảng cho đúng**, bot lo phần còn lại.

---

## 2. Điền cấu hình vào Google Sheet

### 🧭 Làm theo đúng thứ tự này

1. **Mở file Google Sheet** của bot.
2. **Chọn đúng trang (tab)** tên **`ĐẶT LỆNH (100 MÃ)`** (nằm ở hàng tab phía dưới màn hình). Mọi thao tác đều làm trên trang này.
3. Điền **các ô điều khiển ở góc trên** (mục 2.1): **B2** (trạng thái), **D1** (% vốn), **D2** (vốn/lệnh), **E2** (tổng vốn).
4. Điền **bảng danh sách coin** bên dưới (mục 2.2): cột **A** (mã), **B** (đòn bẩy), **D** (giá vào), **G** (giá chốt lời).
5. Kiểm tra lại **giá đúng chiều** (mục 2.3) rồi mới chạy bot.

> 📍 Hình dung nhanh: **góc trên trái** là bảng điều khiển (bot chạy hay nghỉ, vốn bao nhiêu). **Phần thân bảng** là danh sách coin và giá.

### 2.1. Ô điều khiển chung (góc trên bảng)

Cột C là **nhãn tên** (chữ có sẵn), bạn chỉ điền **số vào cột D và E**:

| Ô cần điền | Ý nghĩa | Ví dụ |
|----|---------|-------|
| **B2** | Trạng thái bot. Gõ đúng 1 trong các chữ ở bảng dưới | `LONG` |
| **D1** | % vốn cho mỗi lệnh (nhãn C1 = "Tỷ lệ vốn") | `1%` |
| **D2** | Vốn mỗi lệnh, tối thiểu 10 USDT (nhãn C2 = "Mức vốn/lệnh") | `10` |
| **E2** | Tổng vốn dùng để tính theo % | `10` |

**Các trạng thái gõ vào ô B2:**

| Gõ vào B2 | Bot sẽ làm |
|-----------|-----------|
| `LONG` | Chạy đặt lệnh MUA (theo danh sách LONG) |
| `SHORT` | Chạy đặt lệnh BÁN (theo danh sách SHORT) |
| `CHỜ` | Không làm gì (nghỉ) |
| `XÓA CHỜ` | Hủy hết lệnh đang chờ, giữ vị thế |
| `XÓA VỊ THẾ` | Đóng hết vị thế, giữ lệnh chờ |
| `STOP` | Đóng hết vị thế **và** hủy hết lệnh chờ |

> 💡 Muốn bot tạm nghỉ: gõ `CHỜ` vào B2.

### 2.2. Bảng danh sách coin

- Danh sách **LONG (mua):** điền vào **các dòng 4 → 53**
- Danh sách **SHORT (bán):** điền vào **các dòng 55 → 104**

Mỗi dòng điền như sau:

| Cột | Tên | Điền gì | Ví dụ |
|-----|-----|---------|-------|
| **A** | Mã coin | Tên coin | `ATOM/USDT` |
| **B** | Đòn bẩy | Số đòn bẩy. Gõ `N` để **tắt** dòng này | `10` |
| **D** | 💵 **Giá vào lệnh** | Giá muốn đặt lệnh LIMIT vào (Lệnh 1) | `2.083` |
| **G** | 🎯 **Giá chốt lời (TP)** | Giá đặt lệnh ngược chốt lời. **Để trống = không chốt lời tự động** | `2.5` |
| **H** | Vốn riêng (tùy chọn) | Vốn riêng cho dòng này (bỏ trống = dùng D1/D2/E2) | `10` |

> ⚠️ Cột **C** (callback cũ) và cột **F** (SL) **không dùng** với bot LIMIT — để trống cũng được.

**🔑 Bật/tắt lệnh chốt lời cho từng mã:**

| Cột G (TP) | Bot sẽ làm |
|------------|-----------|
| **Có điền giá** | Sau khi Lệnh 1 khớp → tự đặt **lệnh chốt lời** ở giá đó |
| **Để trống** | **Chỉ giữ Lệnh 1** (vào lệnh), **không** tự chốt lời — bạn tự chốt tay |

> 💡 Đây chính là công tắc: muốn bot lo cả chốt lời thì điền giá vào cột **G**; muốn tự tay chốt lời thì để **G trống**. Đổi lúc nào cũng được, không cần khởi động lại bot.

### 2.3. Quy tắc điền GIÁ cho đúng

**Giá vào lệnh (cột D):**
- Lệnh **MUA (LONG):** giá vào phải **THẤP HƠN** giá hiện tại (chờ giá xuống để mua).
- Lệnh **BÁN (SHORT):** giá vào phải **CAO HƠN** giá hiện tại (chờ giá lên để bán).
- Nếu điền sai chiều, bot sẽ **bỏ qua** dòng đó (không đặt lệnh) để an toàn.

**Giá chốt lời — TP (cột G):**
- Lệnh **MUA (LONG):** giá chốt lời nên **CAO HƠN** giá vào (mua thấp, bán cao).
- Lệnh **BÁN (SHORT):** giá chốt lời nên **THẤP HƠN** giá vào (bán cao, mua lại thấp).
- Lệnh chốt lời chỉ được đặt **sau khi Lệnh 1 đã khớp** (đã có vị thế).

### 2.4. Vốn được tính thế nào?

Bot chọn vốn cho mỗi lệnh theo thứ tự ưu tiên:

1. Nếu **cột H** có số → dùng số đó.
2. Nếu không, và **E2** có số → vốn = **D1 × E2** (tối thiểu 10 USDT).
3. Nếu không → dùng **D2**.

> 💵 Vốn mỗi lệnh tối thiểu là **10 USDT**. Dưới mức này bot bỏ qua.

### 2.5. Ví dụ điền mẫu (LONG)

**Ô điều khiển:**

| B2 | D1 | D2 | E2 |
|----|----|----|----|
| `LONG` | `1%` | `10` | `10` |

**Dòng coin (điền vào dòng 4):**

| A (Mã) | B (Đòn bẩy) | D (Giá vào) | G (Giá TP) | H (Vốn) |
|--------|-------------|-------------|------------|---------|
| `ATOM/USDT` | `1` | `2.083` | `2.5` | `10` |

**Bot sẽ hiểu:** mua ATOM/USDT bằng lệnh LIMIT ở giá `2.083`, vốn `10 USDT`, đòn bẩy `1`. Khi khớp xong sẽ tự đặt lệnh chốt lời ở giá `2.5`. Nếu muốn **tự chốt lời tay** thì để trống ô G.

---

## 3. Chạy bot

### 🪟 Trên Windows

1. Mở thư mục chứa bot.
2. Kiểm tra: bot đang để chế độ **LIMIT** sẵn rồi (không cần chỉnh gì).
3. Nhấp đúp vào file **`start_all_bots.bat`**.
4. Các cửa sổ đen sẽ hiện lên — đó là bot đang chạy. **Đừng tắt** các cửa sổ này.

> ✅ Để chắc chắn đang chạy bot LIMIT: khi mở `start_all_bots.bat` bằng Notepad, tìm dòng
> `set ORDER_BOT_MODE=limit` — chữ **limit** là đúng.

### 🍎 Trên Mac / Linux

Mở Terminal tại thư mục bot rồi gõ:

```bash
./start_all_bots.sh
```

---

## 4. Dừng bot

### 🪟 Windows
- Đóng tất cả cửa sổ đen có chữ **"QBot"** trên thanh tiêu đề.

### 🍎 Mac / Linux
```bash
./stop_all_bots.sh
```
Rồi gõ `y` và Enter.

---

## 5. Muốn quay lại bot cũ (Trailing Stop)?

Bot cũ và bot mới **không được chạy cùng lúc** (sẽ đặt lệnh trùng).

1. **Dừng bot** trước (mục 4).
2. Mở file khởi động bằng Notepad:
   - Windows: `start_all_bots.bat`, đổi `set ORDER_BOT_MODE=limit` thành `set ORDER_BOT_MODE=trailing`
   - Mac/Linux: `start_all_bots.sh`, đổi dòng `ORDER_BOT_MODE=...` phần `limit` thành `trailing`
3. Lưu lại và chạy bot như mục 3.

Muốn quay lại bot LIMIT thì làm ngược lại (đổi về `limit`).

---

## 6. Lưu ý an toàn ⚠️

- **Luôn dừng bot cũ trước khi bật bot mới** (và ngược lại). Không chạy 2 bot đặt lệnh cùng lúc.
- Điền số **không có dấu phẩy nghìn** (gõ `60000`, không gõ `60,000`).
- Sau khi bot chốt lời xong, nếu **cột D vẫn còn giá**, bot sẽ **tự vào lệnh lại**. Muốn dừng hẳn 1 mã: gõ `N` vào cột B của dòng đó.
- Khi thử nghiệm, nên để **vốn nhỏ** (ví dụ D2 = 10–20 USDT) cho an toàn.
- Muốn bot ngừng đặt lệnh ngay: gõ `CHỜ` vào ô **B2**.

---

## 7. Kiểm tra nhanh khi có sự cố

| Hiện tượng | Kiểm tra |
|------------|----------|
| Bot không đặt lệnh | Ô B2 có phải `LONG`/`SHORT` không? Cột B có bị `N` không? |
| Không vào lệnh 1 mã | Giá cột D có đúng chiều không (mục 2.3)? Vốn có ≥ 10 USDT không? |
| Không thấy lệnh chốt lời | Lệnh 1 đã khớp (đã có vị thế) chưa? **Cột G (TP)** đã điền giá chưa? (G trống = không chốt lời) |
| Báo lỗi liên tục | Xem file `error.log` trong thư mục bot, hoặc báo kỹ thuật. |

---

*Nếu chưa rõ chỗ nào, chụp màn hình bảng Google Sheet và hỏi bộ phận kỹ thuật.*
