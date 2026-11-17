# Việc của chủ dự án để đưa Tinh Ảnh (StarVeil) lên Microsoft Store

Làm theo thứ tự. Phần lập trình đã xong; gói `StarVeil-1.0.0.0-x64.msix` nằm trong trang Release v1.0.0 trên GitHub.

## 1. Tạo tài khoản nhà phát triển (miễn phí, ~1 giờ + chờ xác minh)
1. Mở **https://storedeveloper.microsoft.com**, đăng nhập bằng tài khoản Microsoft **cá nhân** (Outlook/Hotmail), không dùng tài khoản công ty.
2. Chọn loại **Individual** (cá nhân). Không đổi sang Company được về sau.
3. Xác minh danh tính: giấy tờ tùy thân (CCCD hoặc hộ chiếu) và ảnh selfie bằng điện thoại.
4. Kiểm tra Việt Nam được chấp nhận khi đăng ký. Nếu bị từ chối, báo lại.

## 2. Giữ chỗ tên (~15 phút)
1. Partner Center → **Apps and games** → **New product** → **MSIX or PWA app**.
2. Giữ chỗ **Tinh Ảnh**, rồi thêm tên thứ hai **StarVeil** (Product management → Manage app name reservations). Giữ chỗ có hạn 3 tháng.
3. Mở **Product management → Product identity**, chép 3 giá trị:
   - `Package/Identity/Name` (dạng `12345TenBan.TinhAnh`)
   - `Package/Identity/Publisher` (dạng `CN=XXXXXXXX-XXXX-...`)
   - `Package/Properties/PublisherDisplayName`

## 3. Đưa identity vào GitHub (~5 phút)
GitHub → repo `thientrile/exif-remover` → **Settings → Secrets and variables → Actions → Variables** → New repository variable, tạo 3 biến:
- `MSIX_IDENTITY_NAME` = giá trị Name ở trên
- `MSIX_PUBLISHER` = giá trị Publisher (nguyên văn, kể cả `CN=`)
- `MSIX_PUBLISHER_DISPLAY_NAME` = giá trị PublisherDisplayName

Rồi chạy lại CI (hoặc nhờ dev phát hành bản 1.0.1) để có gói `.msix` mang đúng identity. Gói trong Release v1.0.0 dùng identity giữ chỗ (`CN=StarVeil-Placeholder`), **Store sẽ từ chối gói đó**.

## 4. Điền các chỗ `[CẦN ĐIỀN]` (~15 phút)
Trong `docs/PRIVACY.md`, `docs/TERMS.md`, `docs/SUPPORT.md` (sửa trực tiếp trên GitHub, trang công khai tự cập nhật sau vài phút):
- Họ tên pháp lý của bạn (PRIVACY mục 2, TERMS mục 1, tiếng Việt và tiếng Anh).
- Địa chỉ liên hệ, hoặc ghi "không công bố" (PRIVACY mục 2).
- Email liên hệ riêng tư (PRIVACY mục 2, TERMS mục 12, SUPPORT "Liên hệ riêng").
- Tỉnh/thành phố nơi bạn cư trú, để xác định toà án (TERMS mục 10).

## 5. Tạo bản nộp đầu tiên (~1–2 giờ)
Trong sản phẩm vừa tạo → **Start your submission**:
1. **Pricing and availability**: Free; thị trường: tất cả hoặc chọn.
2. **Properties**: danh mục **Photo & video**; Privacy policy URL: `https://thientrile.github.io/exif-remover/PRIVACY.html`; Website: `https://github.com/thientrile/exif-remover`; Support contact: email của bạn hoặc `https://thientrile.github.io/exif-remover/SUPPORT.html`.
3. **Age ratings**: trả lời bảng hỏi theo `AGE_RATING.md` (kết quả dự kiến 3+).
4. **Packages**: tải lên `StarVeil-1.0.x.0-x64.msix` (bản build sau bước 3).
5. **Store listings**: thêm tiếng Việt và tiếng Anh, dán nội dung từ `LISTING.md`; tải ảnh chụp màn hình trong `screenshots/` (PNG 1402x852, bản Store); tải biểu tượng 300x300.
6. **Submission options**: dán phần "Notes for certification" và "runFullTrust justification" từ `CERTIFICATION_NOTES.md`.
7. Bấm **Submit to the Store**. Chờ chứng nhận (thường 1–3 ngày làm việc). Nếu bị từ chối, gửi lại email/báo cáo cho dev.

## 6. Sau khi lên Store
- Bản GitHub vẫn chạy song song và tự cập nhật như cũ. Mỗi máy chỉ nên cài một bản.
- Muốn CI tự nộp bản mới lên Store: cần tạo Entra ID app trong Partner Center (không bắt buộc, làm sau).
- Đổi tên repo sang `thientrile/starveil`: **chưa làm**, vì bộ cập nhật của bản 0.2.x chỉ chấp nhận tệp từ `thientrile/exif-remover`. Có thể đổi khi hầu hết người dùng đã lên 1.0.0 (bản 1.0.0 chấp nhận cả hai tên). Lưu ý: đổi tên repo sẽ đổi địa chỉ GitHub Pages, phải sửa Privacy policy URL trên Store.
