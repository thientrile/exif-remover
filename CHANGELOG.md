# Changelog

The section for a version is used as its release notes and shown in the in-app update dialog.

## v0.2.3

- Đóng cửa sổ đúng lúc vừa xoá xong không còn làm ứng dụng bị treo nút.
- Sửa lỗi hiếm: tệp sai đuôi nằm trong thư mục có tên chứa ".exifclean-".
- Sao lưu an toàn hơn khi hai lần chạy cùng lúc: không bao giờ xoá bản sao lưu của lần chạy khác.

## v0.2.2

- Sửa lỗi: ảnh JPEG bị đặt đuôi .png (hay ngược lại) trước đây báo "✗ Lỗi" cho mọi tệp. Nay nhận đúng định dạng thật, xoá metadata và giữ nguyên tên tệp. Cột Loại ghi rõ, ví dụ "JPEG (đuôi .png)".
- Nút **Dừng** khi đang xoá: xử lý xong tệp hiện tại rồi dừng, các tệp còn lại giữ nguyên ("Đã dừng"). Dừng trong lúc sao lưu thì xoá bản sao lưu dở. Đóng cửa sổ khi đang chạy sẽ hỏi lại và dừng an toàn.
- Không bao giờ xoá metadata trong thư mục sao lưu (`..._backup-YYYY-MM-DD`): chọn thư mục đó sẽ được cảnh báo và bỏ qua.
- Rê chuột lên một dòng để xem đường dẫn đầy đủ và lý do lỗi. Tên tệp hiển thị theo thư mục đã chọn, rút gọn ở giữa.
- Đếm metadata nhanh hơn với thư mục nhiều tệp (đọc theo lô).

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
