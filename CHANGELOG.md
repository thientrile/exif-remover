# Changelog

The section for a version is used as its release notes and shown in the in-app update dialog.

## v1.0.0

- Ứng dụng đổi tên thành **Tinh Ảnh** (tiếng Anh: **StarVeil**) · *Xoá metadata ảnh*. Tệp chạy là `StarVeil.exe`, bộ cài `StarVeil-Setup-1.0.0.exe`, lối tắt menu Start **Tinh Ảnh (StarVeil)**.
- Bản cũ (Exif Remover 0.2.x) cập nhật thẳng lên 1.0.0 như mọi lần: cài đè vào cùng thư mục, gỡ `ExifRemover.exe` và lối tắt cũ, **giữ nguyên** cài đặt, danh sách bản sao lưu và log (`%APPDATA%\ExifRemover`, `%LOCALAPPDATA%\ExifRemover`).
- **Giới thiệu** có thêm nút **Quyền riêng tư** và **Điều khoản sử dụng**, mở các trang chính sách công khai trên GitHub Pages.
- Chuẩn bị cho Microsoft Store: gói MSIX `StarVeil-1.0.0.0-x64.msix` (chưa ký; Store sẽ ký). Bản Store không có trình tự cập nhật (Store lo việc đó) và không kết nối mạng.
- Dòng lệnh vẫn như cũ: `StarVeil.exe --no-backup C:\anh` (bản Store: `starveil.exe` hoặc `exif-remover.exe`).
- Sửa: dòng lệnh không còn báo lỗi nhầm với tệp tên tiếng Việt khi chuyển kết quả ra tệp (`> log.txt`) — tệp đã được làm sạch nhưng việc in tên tệp bị lỗi mã hoá.

## v0.2.6

- Nút **Giới thiệu** ở góc dưới bên phải: phiên bản, giấy phép, công cụ đi kèm, cam kết quyền riêng tư (mọi xử lý trên máy bạn), nút **Trang dự án**, **Báo lỗi / góp ý**, **Giấy phép & bên thứ ba**, **Mở thư mục log**, **Kiểm tra cập nhật**.
- Lỗi được ghi vào `%LOCALAPPDATA%\ExifRemover\logs\app.log` (chỉ đường dẫn và nội dung lỗi). Lỗi bất ngờ hiện hộp thoại có nút **Mở thư mục log** và **Báo lỗi** thay vì tắt im lặng.
- Chữ ký **Ánh sao & Bầu trời · by @thientrile** ở góc dưới, bấm để mở trang GitHub của tác giả.
- Bộ cài hiện giấy phép MIT; nhà phát hành "Ánh sao & Bầu trời (thientrile)"; tệp ExifRemover.exe có thông tin phiên bản và bản quyền.

## v0.2.5

- Nút mới **Chuyển sang JPG**: đổi ảnh WebP, PNG, GIF, BMP, TIFF, AVIF, HEIC trong danh sách sang JPG, chạy ngay trên máy, không tải ảnh lên mạng.
  - Tạo tệp `.jpg` mới cạnh ảnh gốc (`anh.jpg`, trùng tên thì `anh-1.jpg`, `anh-2.jpg`...). Ảnh gốc giữ nguyên.
  - Ảnh JPG mới không có metadata, đúng chiều xoay, đúng màu. Phần trong suốt thành nền trắng. Ảnh động lấy khung hình đầu tiên.
  - Tệp đã là JPEG (kể cả bị đặt sai đuôi), video và PDF được bỏ qua, có ghi lý do. Nút **Dừng** dùng được như khi xoá metadata.
- Nhận thêm ảnh BMP (xoá metadata và chuyển sang JPG).
- Dòng lệnh: `--to-jpg`.

## v0.2.4

- Nút **Xoá bản sao lưu** trên thẻ kết quả: chuyển bản sao lưu của lần chạy vào Thùng rác (khôi phục được), hỏi lại kèm đường dẫn, số tệp, dung lượng. Chỉ bấm được khi mọi tệp đều xoá thành công.
- Nút **Bản sao lưu** ở góc dưới: xem và xoá các bản sao lưu do ứng dụng tạo (ngày tạo, dung lượng, thư mục gốc còn không). Chỉ xoá thư mục ứng dụng đã tạo và còn đúng tên `..._backup-NĂM-THÁNG-NGÀY`.
- Tuỳ chọn (mặc định tắt): khi mở ứng dụng, đề nghị xoá bản sao lưu cũ hơn N ngày, luôn hỏi trước.

## v0.2.3

- **Chọn thư mục** chọn được nhiều thư mục một lần: giữ Ctrl (hoặc Shift) khi bấm. Mỗi lần chọn hay kéo thả đều cộng thêm vào danh sách, tệp trùng tự bỏ qua.

## v0.2.2

- Sửa lỗi: ảnh JPEG bị đặt đuôi .png (hay ngược lại) trước đây báo "✗ Lỗi" cho mọi tệp. Nay nhận đúng định dạng thật, xoá metadata và giữ nguyên tên tệp. Cột Loại ghi rõ, ví dụ "JPEG (đuôi .png)".
- Nút **Dừng** khi đang xoá: xử lý xong tệp hiện tại rồi dừng, các tệp còn lại giữ nguyên ("Đã dừng"). Dừng trong lúc sao lưu thì xoá bản sao lưu dở. Đóng cửa sổ khi đang chạy sẽ hỏi lại và dừng an toàn.
- Không bao giờ xoá metadata trong thư mục sao lưu (`..._backup-YYYY-MM-DD`): chọn thư mục đó sẽ được cảnh báo và bỏ qua.
- Rê chuột lên một dòng để xem đường dẫn đầy đủ và lý do lỗi. Tên tệp hiển thị theo thư mục đã chọn, rút gọn ở giữa.
- Đếm metadata nhanh hơn với thư mục nhiều tệp (đọc theo lô).
- Đóng cửa sổ đúng lúc vừa xoá xong không còn làm ứng dụng bị treo nút.
- Sửa lỗi hiếm: tệp sai đuôi nằm trong thư mục có tên chứa ".exifclean-".
- Sao lưu an toàn hơn khi hai lần chạy cùng lúc: không bao giờ xoá bản sao lưu của lần chạy khác.
- Không còn lỗi khi bấm xoá ngay lúc ứng dụng đang đọc metadata (tệp bị khoá tạm thời trên Windows: thử lại).

## v0.2.1

- Bản kiểm tra tự cập nhật: cài v0.2.0 rồi bấm **Cập nhật ngay** sẽ lên v0.2.1. Không đổi chức năng.

## v0.2.0

- Giao diện mới bằng tiếng Việt: kéo thả tệp/thư mục, bảng tệp có trạng thái, thanh tiến trình, thẻ kết quả.
- Xem metadata của từng tệp (có ô tìm kiếm), chỉ xem, không sửa.
- Hỗ trợ thêm ảnh GIF và AVIF.
- Giữ hồ sơ màu ICC để màu ảnh không bị lệch (không chứa thông tin cá nhân).
- Tự cập nhật: báo khi có bản mới, tải bộ cài từ GitHub, kiểm tra SHA256 rồi cài và mở lại.

## v0.1.0

- Bản đầu tiên: ứng dụng Windows, sao lưu thư mục, xoá metadata ảnh/video/PDF tại chỗ và kiểm tra lại.
