# Backup trước khi bỏ tab "100 mã (50 tăng và 50 giảm)"

Ngày: 2026-09-05
Mốc git trước khi sửa: 7f62f69

## Vì sao có thư mục này

Khách bỏ hẳn tab "100 mã" khỏi Google Sheet cho nhẹ bot. Từ nay:

- `hd_update_all.py` chạy chế độ **balance_only**: chỉ lấy SỐ DƯ, ghi vào
  **J1:M2 của tab ĐẶT LỆNH**. 1 lượt gọi Binance + 1 lượt ghi Google, ~1 giây.
- `hd_update_price.py` **nghỉ hẳn** — việc duy nhất của nó là ghi giá vào tab
  đã bỏ. Chạy lên sẽ in thông báo rồi tự thoát.
- `hd_track_30_prices.py` ghi 18 mốc giá vào cột I:Z tab ĐẶT LỆNH. KHÔNG liên
  quan tab 100 mã, nhưng không bot nào đọc lại vùng đó nên có thể tắt để nhẹ máy.
  Đây cũng là bot DUY NHẤT kéo theo pandas + numpy.

## Các file ở đây

| File | Là gì |
|---|---|
| `hd_update_all.py.bak_full100ma` | Bản ĐẦY ĐỦ: dựng bảng 58 cột, Bollinger, Stoch, cảnh báo delist. 8 lượt gọi Binance MỖI MÃ. |
| `hd_update_price.py.bak_cot_gia` | Bản ghi giá vào tab 100 mã |
| `hd_track_30_prices.py.bak_30moc` | Bản 18 mốc giá (chưa sửa gì) |
| `config.ini.example.bak_truoc_bo_tab` | Config trước khi thêm update_all_mode |

## Muốn quay lại bản cũ

KHÔNG cần chép file từ đây. Chỉ cần tạo lại tab "100 mã" trên sheet rồi đặt
trong `[global]`:

    update_all_mode = full

Toàn bộ code cũ vẫn nằm trong `hd_update_all.py`, chỉ là không chạy ở chế độ
mặc định. `hd_update_price.py` cũng tự chạy lại khi thấy `full`.

Thư mục này giữ để đối chiếu khi cần, không phải để chép đè.

## Lưu ý an toàn

⚠️ Sửa code TRƯỚC, xoá tab SAU. Xoá tab trước khi cập nhật code thì bot sẽ gọi
tới vùng không tồn tại và báo lỗi mỗi vòng.

⚠️ KHÔNG tắt `hd_update_cho_va_khop.py`. Nó không liên quan tab 100 mã — nó là
nguồn cấp SL/TP cho `hd_order_multi` (leg2/leg3 đọc tab "Chờ và khớp").
Tắt nó = vị thế mở mà không có cắt lỗ.
