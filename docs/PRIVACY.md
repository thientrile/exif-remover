# Chính sách quyền riêng tư / Privacy Policy

**Tinh Ảnh (StarVeil)** · Ngày hiệu lực / Effective date: **2026-11-17**

> Tiếng Việt ở trước, English below.

---

## Tiếng Việt

### 1. Tóm tắt

Tinh Ảnh xoá thông tin ẩn (metadata) khỏi ảnh, video và PDF **ngay trên máy tính của bạn**. Ứng dụng **không tải tệp của bạn lên mạng**, không có tài khoản, không có quảng cáo, không thu phí, không có phân tích hay theo dõi (analytics/telemetry). Chúng tôi **không nhận** bất kỳ dữ liệu cá nhân nào của bạn từ ứng dụng.

### 2. Ai chịu trách nhiệm

- Nhà phát triển: cá nhân, tài khoản GitHub **@thientrile** (ký tên "Ánh sao & Bầu trời").
- Họ tên pháp lý: [CẦN ĐIỀN: họ tên pháp lý của nhà phát triển]
- Địa chỉ liên hệ: [CẦN ĐIỀN: địa chỉ bưu chính, hoặc ghi "không công bố" nếu luật nơi bạn cư trú cho phép]
- Liên hệ về quyền riêng tư: GitHub Issues tại https://github.com/thientrile/exif-remover/issues hoặc email [CẦN ĐIỀN: email liên hệ riêng tư]

### 3. Tệp của bạn

Mọi việc xử lý (xoá metadata, xem metadata, chuyển sang JPG) chạy trên máy của bạn bằng các công cụ đi kèm (exiftool, ffmpeg, qpdf). Nội dung tệp, ảnh, vị trí GPS hay bất kỳ metadata nào **không bao giờ** được gửi đi đâu.

### 4. Kết nối mạng duy nhất: kiểm tra cập nhật

- **Bản cài từ Microsoft Store không kết nối mạng chút nào**: Store tự lo cập nhật, nên phần kiểm tra cập nhật bên dưới bị tắt hẳn. Mục này chỉ áp dụng cho bản cài từ GitHub (`StarVeil-Setup-x.y.z.exe`).
- Khi mở, ứng dụng hỏi GitHub (`api.github.com`) xem có bản mới không. Bạn **có thể tắt** việc này trong ứng dụng.
- Khi bạn bấm cập nhật, ứng dụng tải bộ cài từ trang phát hành (Releases) của dự án trên GitHub và kiểm tra mã SHA256 trước khi cài.
- Yêu cầu này chỉ gửi thông tin kỹ thuật thông thường: **địa chỉ IP** của bạn (bắt buộc với mọi kết nối Internet) và chuỗi nhận dạng chung `StarVeil/<phiên bản>`. Không gửi tên, tệp, đường dẫn hay mã định danh thiết bị.
- Yêu cầu này đi thẳng tới **GitHub, Inc.** (thuộc Microsoft). GitHub xử lý địa chỉ IP theo chính sách riêng của họ: https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement . Nhà phát triển **không nhận** địa chỉ IP của bạn; GitHub chỉ cho nhà phát triển xem tổng số lượt tải.

### 5. Dữ liệu chỉ lưu trên máy bạn

Ứng dụng lưu vài tệp nhỏ **trên máy bạn**, không gửi đi:

| Tệp | Nội dung | Mục đích |
|---|---|---|
| `%APPDATA%\ExifRemover\settings.json` | Lựa chọn của bạn (bật/tắt kiểm tra cập nhật, số ngày tự dọn bản sao lưu) | Nhớ cài đặt |
| `%APPDATA%\ExifRemover\backups.json` | Đường dẫn thư mục sao lưu do ứng dụng tạo, thư mục gốc, ngày tạo | Liệt kê và dọn bản sao lưu |
| `%LOCALAPPDATA%\ExifRemover\logs\app.log` | Thông báo lỗi và đường dẫn tệp (không có nội dung tệp) | Giúp bạn tìm nguyên nhân lỗi |

Tên thư mục `ExifRemover` là tên cũ của ứng dụng, được giữ nguyên để không mất cài đặt và danh sách sao lưu khi nâng cấp. Bản cài từ Microsoft Store được Windows lưu các tệp này trong vùng riêng của ứng dụng và tự xoá khi gỡ.

Đường dẫn tệp có thể chứa tên người dùng Windows của bạn. Các tệp này **không tự gỡ khi bạn gỡ ứng dụng**; muốn xoá hết, hãy xoá thủ công hai thư mục `%APPDATA%\ExifRemover` và `%LOCALAPPDATA%\ExifRemover`. Thư mục sao lưu (`..._backup-NĂM-THÁNG-NGÀY`) nằm cạnh thư mục gốc của bạn và chứa bản sao đầy đủ tệp gốc (còn nguyên metadata) cho tới khi bạn xoá.

Nhật ký lỗi chỉ được gửi cho nhà phát triển nếu **chính bạn** chủ động đính kèm khi báo lỗi.

### 6. Khi bạn liên hệ hỗ trợ

GitHub Issues là **công khai**. Những gì bạn đăng (tên tài khoản, nội dung, ảnh, nhật ký) ai cũng xem được. **Đừng đăng ảnh, đường dẫn hay thông tin cá nhân** không cần thiết; xoá tên người dùng khỏi nhật ký trước khi đính kèm. Nhà phát triển chỉ dùng thông tin đó để trả lời bạn. Bạn có thể tự sửa/xoá bình luận của mình, hoặc yêu cầu nhà phát triển xoá.

### 7. Microsoft Store và Windows

Nếu bạn cài qua Microsoft Store, Microsoft có thể thu thập dữ liệu về việc tải, cài đặt và lỗi hệ thống theo Tuyên bố quyền riêng tư của Microsoft (https://privacy.microsoft.com/privacystatement). Nhà phát triển có thể xem số liệu tổng hợp, không định danh mà Microsoft cung cấp trong Partner Center; việc này nằm ngoài ứng dụng và do Microsoft kiểm soát.

### 8. Cơ sở pháp lý và quyền của bạn

- **Việt Nam** (Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15 và văn bản hướng dẫn; trước đây Nghị định 13/2023/NĐ-CP): nhà phát triển không thu thập dữ liệu cá nhân qua ứng dụng. Với thông tin bạn tự gửi khi liên hệ, bạn có quyền được biết, đồng ý, truy cập, chỉnh sửa, xoá, rút lại sự đồng ý, phản đối và khiếu nại.
- **EU/EEA/UK (GDPR)**: nhà phát triển không nhận dữ liệu từ ứng dụng. Thông tin bạn gửi khi liên hệ được xử lý dựa trên lợi ích hợp pháp để trả lời bạn (Điều 6(1)(f)). Bạn có quyền truy cập, chỉnh sửa, xoá, hạn chế, phản đối, di chuyển dữ liệu và khiếu nại tới cơ quan bảo vệ dữ liệu nơi bạn sống.
- **California (CCPA/CPRA)**: chúng tôi **không bán và không chia sẻ** dữ liệu cá nhân, không dùng cho quảng cáo nhắm mục tiêu.
- Để thực hiện quyền, liên hệ theo Mục 2. Chúng tôi trả lời trong vòng 30 ngày.

### 9. Trẻ em

Ứng dụng không thu thập dữ liệu của bất kỳ ai, kể cả trẻ em.

### 10. Bảo mật

Không có máy chủ lưu dữ liệu của bạn. Bản cập nhật chỉ được tải từ GitHub qua HTTPS và bị từ chối nếu mã SHA256 không khớp. Mã nguồn công khai để ai cũng kiểm tra được.

### 11. Thay đổi chính sách

Nếu ứng dụng bắt đầu thu thập dữ liệu mới, chính sách này sẽ được cập nhật **trước** khi thay đổi có hiệu lực, kèm ngày hiệu lực mới. Lịch sử thay đổi có trên GitHub.

---

## English

### 1. Summary

StarVeil removes hidden information (metadata) from images, videos and PDFs **on your own computer**. It **never uploads your files**, has no accounts, no ads, no payments and no analytics or telemetry. We **do not receive** any personal data about you from the app.

### 2. Who is responsible

- Developer: an individual, GitHub account **@thientrile** (signing as "Ánh sao & Bầu trời").
- Legal name: [CẦN ĐIỀN: developer's legal name]
- Contact address: [CẦN ĐIỀN: postal address, or "not published" if the law where you live allows it]
- Privacy contact: GitHub Issues at https://github.com/thientrile/exif-remover/issues or email [CẦN ĐIỀN: privacy contact email]

### 3. Your files

All processing (removing metadata, viewing metadata, converting to JPG) runs on your computer with bundled tools (exiftool, ffmpeg, qpdf). File contents, images, GPS locations and other metadata are **never** sent anywhere.

### 4. The only network use: update checks

- **The Microsoft Store version makes no network requests at all**: the Store handles updates, so the update check below is switched off. This section applies only to the version installed from GitHub (`StarVeil-Setup-x.y.z.exe`).
- When it starts, the app asks GitHub (`api.github.com`) whether a newer version exists. You **can turn this off** in the app.
- When you click update, the app downloads the installer from the project's GitHub Releases page and checks its SHA256 hash before installing.
- These requests carry only standard technical data: your **IP address** (needed for any internet connection) and a generic user agent `StarVeil/<version>`. No name, files, file paths or device identifiers are sent.
- The requests go directly to **GitHub, Inc.** (a Microsoft company), which handles your IP address under its own policy: https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement . The developer **does not receive** your IP address; GitHub only shows the developer total download counts.

### 5. Data kept only on your computer

The app keeps a few small files **on your computer** and never sends them:

| File | Contents | Purpose |
|---|---|---|
| `%APPDATA%\ExifRemover\settings.json` | Your choices (update check on/off, days before auto-cleaning backups) | Remember settings |
| `%APPDATA%\ExifRemover\backups.json` | Paths of backup folders the app created, their source folders, creation date | List and clean up backups |
| `%LOCALAPPDATA%\ExifRemover\logs\app.log` | Error messages and file paths (no file contents) | Help you find out what went wrong |

The folder name `ExifRemover` is the app's former name, kept so settings and the backup list survive upgrades. For the Microsoft Store version, Windows keeps these files in the app's private storage and removes them on uninstall.

File paths may include your Windows user name. These files **are not removed when you uninstall**; to remove everything, delete the `%APPDATA%\ExifRemover` and `%LOCALAPPDATA%\ExifRemover` folders by hand. Backup folders (`..._backup-YYYY-MM-DD`) sit next to your original folders and hold full copies of your original files (metadata included) until you delete them.

The log reaches the developer only if **you** choose to attach it to a bug report.

### 6. When you contact support

GitHub Issues are **public**. Anything you post (account name, text, images, logs) can be seen by anyone. **Do not post photos, file paths or personal details** you don't need to; remove your user name from logs before attaching them. The developer uses this information only to answer you. You can edit or delete your own comments, or ask the developer to delete them.

### 7. Microsoft Store and Windows

If you install through the Microsoft Store, Microsoft may collect data about downloads, installs and crashes under the Microsoft Privacy Statement (https://privacy.microsoft.com/privacystatement). The developer may see aggregated, non-identifying statistics that Microsoft provides in Partner Center; this happens outside the app and is controlled by Microsoft.

### 8. Legal basis and your rights

- **Vietnam** (Personal Data Protection Law No. 91/2025/QH15 and its guiding regulations; formerly Decree 13/2023/NĐ-CP): the developer collects no personal data through the app. For information you send when you contact us, you have the right to be informed, to consent, access, correct, delete, withdraw consent, object and complain.
- **EU/EEA/UK (GDPR)**: the developer receives no data from the app. Information you send when contacting us is processed on the basis of legitimate interest in answering you (Art. 6(1)(f)). You have the right to access, rectify, erase, restrict, object, data portability, and to complain to your local data protection authority.
- **California (CCPA/CPRA)**: we **do not sell or share** personal information and do not use it for targeted advertising.
- To use your rights, contact us as in Section 2. We answer within 30 days.

### 9. Children

The app collects no data from anyone, including children.

### 10. Security

There is no server holding your data. Updates are downloaded only from GitHub over HTTPS and rejected if the SHA256 hash does not match. The source code is public so anyone can check it.

### 11. Changes

If the app ever starts collecting new data, this policy will be updated **before** the change takes effect, with a new effective date. The change history is on GitHub.
