# Firmware ESP32: quy ước riêng

- Logic quyết định (trạng thái, đầu ra, ACK, bản tin) đặt trong `lib/alert_core/`, không include `Arduino.h`, nhận thời gian qua tham số `nowMs`. Có test trong `test/test_core/` chạy bằng `pio test -e native` (từ PowerShell, cần `C:\msys64\ucrt64\bin` trong PATH).
- `src/` chỉ chứa phần dính phần cứng/mạng. Không `delay()` dài, không `String`, không cấp phát động trong `loop()`.
- Mạng ở task riêng (core 0); `loop()` (core 1) chỉ chạm `AlertModel` khi giữ mutex.
- Payload sai không bao giờ được coi là NORMAL. Mất `state` quá 5 giây là UNKNOWN (đèn vàng nháy).
- Bản tin theo `contracts/mqtt/`; không tự thêm trường. `secrets.h` không commit.
- Đổi chân GPIO chỉ sửa `include/config.h` và bảng trong README.
