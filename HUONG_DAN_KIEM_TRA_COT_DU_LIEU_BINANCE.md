# Hướng dẫn kiểm tra từng cột dữ liệu (đối chiếu Binance / nguồn chuẩn)

Tài liệu này dùng cho bot **`hd_update_all.py`** (sheet “100 mã”, cột **A → BF** trên mỗi dòng mã). Mục tiêu: biết **đối chiếu ở đâu** và **lưu ý gì** để kết luận đúng/sai hợp lý (không phải mọi cột đều có ô tương ứng 1–1 trên giao diện Binance).

---

## 0. Chuẩn bị chung

| Nội dung | Ghi chú |
|----------|---------|
| **Thị trường** | Bot dùng **USDT-M Futures** (mặc định CCXT `defaultType: future`). Đối chiếu chart/API phải chọn **Futures USDT-M**, đúng mã (ví dụ `BTCUSDT` perpetual). |
| **Mã trên sheet (cột A)** | Dạng `BASE/USDT` (không có `:USDT`). Trên web thường là `BASEUSDT` perpetual. |
| **Giờ nến** | Binance Futures Kline theo **UTC**. TradingView: chỉnh timezone biểu đồ cho khớp (UTC) nếu so từng nến. |
| **Độ trễ snapshot** | `% 24h` và **Volume 24h** (cột B, T) lấy từ **`fetch_tickers()`** một lần đầu vòng quét — có thể lệch vài phút so với nút refresh trên web nếu bạn so đúng thời điểm từng giây. |
| **Sai số làm tròn** | Web/API có thể hiển thị ít chữ số thập phân hơn sheet; so sánh nên dùng **cùng số chữ số** hoặc sai số tương đối (ví dụ &lt; 0,1%). |

**Tài liệu API Futures (tham chiếu kỹ thuật):**  
[Binance USDⓈ-M Futures API](https://binance-docs.github.io/apidocs/futures/en/)

---

## 1. Bảng tra cứu theo cột (A → BF)

Cột **V** trên sheet để trống (không kiểm tra).

| Cột | Tên trên sheet (tóm tắt) | Cách đối chiếu / nguồn so sánh |
|-----|--------------------------|--------------------------------|
| **A** | Mã | Đối chiếu trực tiếp tên cặp Futures USDT-M. |
| **B** | % 24h | Trang Futures Binance: cột **24h Change %** / thông tin ticker. Hoặc API ticker 24h (khớp `percentage` trong CCXT). Nhớ snapshot có thể trễ vài phút so với lúc bạn mở web. |
| **C** | Giá trị hiện tại | **Last price** trên ticker Futures (cùng thời điểm snapshot với B, T). Không bắt buộc bằng “close nến 1h” trên chart nếu nến 1h chưa đóng. |
| **D, E** | BB1h trên / dưới | Mở biểu đồ **1h Futures**, chỉ báo **Bollinger Bands (20, 2, mặc định SMA, độ lệch chuẩn population)** trên **Close**. Bot dùng **20 nến gần nhất gồm nến đang chạy** (logic `get_bb`). TradingView: kiểm tra cài đặt BB (SMA vs EMA, độ lệch chuẩn mẫu vs tổng thể) — nếu khác sẽ lệch với sheet. |
| **F, G** | BB4h trên / dưới | Giống D/E nhưng khung **4h**, cùng quy ước BB(20,2) trên 20 nến gần nhất. |
| **H, I** | BB1 ngày trên / dưới | Khung **1d**, BB(20,2) trên 20 nến ngày gần nhất (gồm nến ngày đang chạy). |
| **J, K** | Biên độ 1h max tăng/giảm (tuần) | **7 ngày × nến 1h**: với mỗi nến, biên độ % theo logic bot (high−low so với “mốc giá” theo hướng nến — xem `calculate_price_range` trong code). Cách kiểm tra chặt: xuất 168 nến 1h từ API `klines` và tái tính trong Excel/Python theo đúng công thức trong repo. |
| **L, M** | Max / Min 40 ngày | **40 nến 1d** gần nhất: **High** lớn nhất, **Low** nhỏ nhất (theo OHLCV ngày). Trên chart 1d: đo 40 cây gần nhất (hoặc dùng API `klines` interval `1d`, limit 40). Bot fetch theo **symbol futures** (`…/USDT:USDT`) cho đoạn này — nếu tự export bằng `pair` khác format, thống nhất một kiểu mã. |
| **N, O** | Max tăng / Max giảm (4h, ~60 ngày) | **Nến 4h**, số lượng theo `max_increase_decrease_4h_day_count` trong `config.ini` (mặc định 60 ngày). Mỗi nến: `(close − open) / open * 100` → lấy **max** và **min** toàn tập. Đối chiếu: export `klines` 4h đủ số nến và cột % body nến. |
| **P, Q** | BB tuần (header sheet: “Giá Cao Nhất / Giá Thấp Nhất”) | Thực tế là **BB(20,2) trên khung 1w** (trên / dưới), **không phải** đỉnh/đáy lịch sử thuần. So sánh: chart **1w Futures** + BB(20,2) như D–E. |
| **R, S** | Biên độ 30d tăng / giảm | **30 nến 1d** gần nhất, công thức biên độ trong `_amplitude_range_from_ohlcv_slice` (tách nến tăng/giảm theo close vs open). Kiểm tra: export 30 nến 1d và tái tính theo code. |
| **T** | Volume 24h | Ticker **Quote volume 24h** (USDT) trên Futures — cùng nguồn snapshot với B. |
| **U** | RSI 14 (ngày) | Bot dùng **RSI Wilder, chu kỳ 14**, trên **close 1d**; khi đủ dữ liệu thì **bỏ nến ngày đang chạy** rồi tính (`closes_1d[:-1]`). TradingView: **RSI(14)** khung **1d**, **Close**, smoothing **Wilder** (nếu có tùy chọn). |
| **W** | Min/Min40 (tỷ lệ) | **Q / M** (BB tuần dưới ÷ Min 40 ngày). Kiểm tra bằng cách lấy Q, M từ sheet hoặc tính lại P–Q, L–M. |
| **X, Y** | % đến BB1h trên / dưới | Công thức từ **giá cột C** và **D, E**: `(D−C)/C*100`, `(C−E)/C*100`. Tự tính lại từ C,D,E để xác minh. |
| **Z, AA** | Vol 1h / Vol 4h (USDT) | **Volume nến hiện tại × close** của nến đó (quy đổi “quote” kiểu USDT). Đối chiếu: lấy nến 1h và 4h mới nhất từ `klines`, nhân `volume × close`. |
| **AB** | Futures (trạng thái) | **exchangeInfo** USDT-M (metadata), không phải giá. So: API `GET /fapi/v1/exchangeInfo` tìm symbol, xem `status`, `contractType`, v.v. |
| **AC** | Spot (trạng thái) | Thông tin **Spot** cùng cặp `BASE/USDT` nếu có — từ CCXT spot `load_markets`. Có thể “Không có spot” nếu không niêm yết spot. |
| **AD, AE** | Biên độ ngày lớn nhất (%) + ngày | Trong cửa sổ ~365 ngày (theo code): **(High−Low)/Open*100** từng nến 1d → lấy max và **timestamp** ngày đó. Đối chiếu: export nến 1d và công thức tương tự. |
| **AF, AG** | BB width 1d (3 phiên trước / hiện tại) | Độ rộng dải BB ngày: **(Upper−Lower)/Middle**, có logic **bỏ nến ngày đang chạy** khi tính (xem `_bb_width_3d_and_now_from_ohlcv`). So với TradingView cần cùng quy ước “nến đóng” và std (population `ddof=0` trong code). |
| **AH** | RSI 14 (4h) | RSI Wilder 14 trên **close 4h**; khi đủ nến thì **bỏ nến 4h đang chạy** (`closes_4h[:-1]`). Chart TV: **4h**, RSI(14), Wilder. |
| **AI, AJ** | Vol 1h hiện tại / MA20 (USDT) | **20 nến 1h** gần nhất: volume×close từng nến; AI = nến cuối; AJ = trung bình 20 giá trị đó. |
| **AK** | Cảnh báo delist | **Không** có một ô trên chart. Nguồn: webhook n8n + catalog Support Binance (CMS). Kiểm tra thủ công: trang thông báo delist Binance và DB/API nội bộ. |
| **AL–AN** | MA7 / MA25 / MA99 (1h) | **SMA** trên **close** 1h (độ dài chuỗi theo code). TradingView: Moving Average **SMA** cùng period trên **1h Close**. |
| **AO–AQ** | MACD (1h) | Chuẩn **12/26/9 EMA** trên close 1h (theo hàm `_compute_macd`). TV: MACD(12,26,9), close. |
| **AR, AS** | Stoch RSI %K / %D (1h) | Stochastic của chuỗi **RSI Wilder 14** (tham số trong `_compute_stoch_rsi`). Khác **Stochastic cổ điển** (cột BE/BF). Trên TV cần chỉ báo “Stoch RSI” đúng tham số. |
| **AT** | Open Interest (USDT) | API dữ liệu công khai: **`/futures/data/openInterestHist`** — trường **tổng giá trị OI dạng USDT** (`sumOpenInterestValue`) tại mốc mới nhất (xem code `_fetch_oi_hist_delta_pct`). Không phải ô “OI” đơn giản trên web nếu web hiển thị đơn vị khác. |
| **AU** | OI Δ 24h (%) | So sánh **OI USDT** điểm đầu vs điểm cuối của **25 mốc 1h** trong API trên (≈ 24h). |
| **AV** | L/S Ratio (account) | **`/futures/data/globalLongShortAccountRatio`** (period 1h, 1 điểm mới nhất trong code). |
| **AW** | L/S Ratio (top traders) | **`/futures/data/topLongShortPositionRatio`**. |
| **AX** | Vol 1h / MA20 | Tỷ số **(volume×close nến 1h hiện tại) / (trung bình 20 nến volume×close)** — tự tính lại từ AI, AJ hoặc từ `klines`. |
| **AY–BA** | Score / Gợi ý / Lý do | **Nội bộ bot** (hàm `_compute_long_short_score`). Không có màn Binance tương ứng. Kiểm tra: đọc lại công thức trong code và tái tính từ các cột đầu vào (MA, MACD, Stoch RSI, L/S, OI delta). |
| **BB** | Open 1h | Nến **1h mới nhất**: giá **Open** (API `klines` 1h, cây cuối). |
| **BC, BD** | High / Low (24 nến 1h gần đây) | Trong **24 nến 1h** gần nhất: max **High**, min **Low**. |
| **BE, BF** | Stoch %K / %D (1h) | **Stochastic cổ điển** (14, 3) trên High/Low/Close 1h — khác Stoch RSI (AR/AS). TV: Stochastic (14,3,3) hoặc đúng định nghĩa trong `_compute_stochastic`. |

---

## 2. Quy trình kiểm tra nhanh (gợi ý)

1. Chọn **một mã** trên sheet (ví dụ BTC).
2. Mở **Binance Futures** đúng mã → đối chiếu **B, C, T** với ticker (chấp nhận lệch nhỏ do thời điểm).
3. Mở **TradingView** (hoặc chart Binance) **Futures 1h / 4h / 1d / 1w** → đối chiếu **D–I, P–Q** (BB cùng thông số 20,2 và cùng quy ước nến).
4. Với **N, O, J–M, R, S, AD–AE**: nên **export klines** (Python/CCXT hoặc API) và chạy lại công thức trong `hd_update_all.py` (hoặc so với file debug `logs/data/...` nếu bật `ENABLE_DEBUG_DATA`).
5. Với **AT–AW**: gọi đúng endpoint **Futures Data** trong tài liệu Binance và so tham số `symbol`, `period`, `limit`.
6. **AK**: chỉ kiểm tra tính **hợp lý** (có bài delist / API nội bộ), không đòi khớp số với chart.

---

## 3. File debug trong bot

Trong `hd_update_all.py`, nếu `ENABLE_DEBUG_DATA = True`, bot ghi **`logs/data/<SYMBOL>_<ngày>.txt`** — liệt kê từng cột theo chữ cái A…BF. Dùng file này để đối chiếu nhanh khi tái tính tay hoặc khi báo lỗi cho dev.

### 3.1 Audit JSON cho **một mã** (đối chiếu B/C/T + đuôi nến)

Trong `config.ini` (mục `[global]`):

```ini
debug_column_audit_symbol = MLN/USDT:USDT
```

- Để **trống** = không ghi file audit.
- Giá trị: đúng **symbol CCXT** như trong `fetch_tickers` (thường dạng `BASE/USDT:USDT`). Bot cũng khớp nếu bạn gõ `MLN/USDT` hoặc `MLNUSDT`.

Sau mỗi lần `get_row_result` **thành công** cho mã đó, bot ghi:

- `logs/column_audit_LAST.json` (ghi đè, mở nhanh)
- `logs/column_audit_<PAIR>_<YYYYMMDD_HHMMSS>.json` (bản theo thời điểm)

Nội dung gồm: **`columns_A_to_BF`** (tên cột + chữ cột + giá trị đã ghi sheet), **`ticker_audit`** (last, percentage, quoteVolume, …), **`ohlcv_tail`** (5 nến 1h + 3 nến 1d/4h cuối), **`exchange_milliseconds_after_build`** (mốc thời gian sau khi dựng xong dòng — đối chiếu ticker Binance).

---

## 4. Khi nào “lệch” vẫn là **đúng**

- TradingView để **EMA** trên BB hoặc **độ lệch chuẫn mẫu (sample)** → BB lệch với sheet.
- TV RSI không phải **Wilder** hoặc khác **nguồn giá** (Mark / Index) so với **Last futures**.
- Bạn so **Spot** nhưng sheet là **Futures**.

Trong các trường hợp đó cần ghi rõ trong báo cáo kiểm tra: *“Lệch do khác cài đặt chỉ báo / khác thị trường, không phải lỗi sheet.”*

---

*Tài liệu căn cứ mã nguồn `qbot_setup/hd_update_all.py` tại thời điểm tạo file. Nếu logic cột thay đổi, cập nhật lại bảng mục 1 cho khớp.*
