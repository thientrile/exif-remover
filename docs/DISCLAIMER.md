# Lưu ý quan trọng / Disclaimer

**Tinh Ảnh (StarVeil)** · Ngày hiệu lực / Effective date: **2026-11-17**

> Tiếng Việt ở trước, English below.

---

## Tiếng Việt

### 1. Ứng dụng xoá được gì

Tinh Ảnh xoá **metadata nằm trong tệp**: EXIF, vị trí GPS, XMP, IPTC, chú thích, ảnh thu nhỏ và dữ liệu nguồn gốc C2PA/JUMBF (Content Credentials). Ứng dụng giữ lại hướng xoay ảnh và hồ sơ màu (ICC) để ảnh hiển thị đúng.

### 2. Ứng dụng KHÔNG xoá được gì

- **Hình mờ vô hình nằm trong điểm ảnh** (ví dụ hình mờ C2PA `c2pa.watermarked`, Google **SynthID** và các dấu tương tự). Chúng là một phần của hình ảnh, không phải metadata, nên vẫn còn sau khi xử lý và vẫn có thể bị công cụ phát hiện.
- **Nội dung nhìn thấy trong ảnh/video**: khuôn mặt, biển số, chữ, địa danh, logo, phản chiếu... vẫn có thể tiết lộ bạn là ai hoặc bạn ở đâu.
- **Bản sao khác của tệp**: bản đã gửi qua mạng xã hội, đám mây, email, hay **thư mục sao lưu** do ứng dụng tạo vẫn còn metadata gốc.

### 3. Ảnh AI vẫn là ảnh AI

Xoá metadata **không** biến ảnh/video do AI tạo thành nội dung "thật". Nội dung vẫn có thể bị nhận diện là AI qua hình mờ vô hình hoặc công cụ phân tích.

**Quy định gắn nhãn vẫn áp dụng.** Nếu luật (ví dụ Điều 50 Đạo luật AI của EU, quy định của Việt Nam về nội dung do AI tạo) hoặc nền tảng (YouTube, TikTok, Facebook, Instagram...) yêu cầu bạn ghi rõ nội dung do AI tạo, bạn **vẫn phải ghi**, dù đã xoá metadata. Dùng ứng dụng để lừa dối hoặc né nhãn AI là vi phạm [TERMS](TERMS.md).

### 4. Luôn giữ bản sao lưu

- Ứng dụng **ghi đè tệp gốc**. Hãy bật **"Tạo bản sao lưu trước khi xoá"**.
- Tệp lẻ (không thuộc thư mục bạn chọn) **không** được sao lưu tự động. Hãy tự sao chép trước.
- Thư mục sao lưu chứa **toàn bộ metadata gốc**. Đừng chia sẻ nó, và hãy xoá khi không cần (trong ứng dụng: nút **Bản sao lưu**).
- Tính năng **Chuyển sang JPG** tạo tệp mới và không động tới tệp gốc; tệp gốc vẫn còn metadata.

### 5. Không phải lời khuyên pháp lý

Tài liệu này chỉ để thông tin, không phải tư vấn pháp lý. Nếu bạn cần chắc chắn về nghĩa vụ của mình, hãy hỏi luật sư.

---

## English

### 1. What the App removes

StarVeil removes **metadata stored in the file**: EXIF, GPS location, XMP, IPTC, comments, thumbnails and C2PA/JUMBF provenance data (Content Credentials). It keeps image orientation and the ICC colour profile so images still display correctly.

### 2. What the App can NOT remove

- **Invisible watermarks embedded in the pixels** (for example the C2PA `c2pa.watermarked` watermark, Google **SynthID** and similar marks). They are part of the image itself, not metadata, so they survive cleaning and can still be detected.
- **What can be seen or heard in the image/video**: faces, number plates, text, landmarks, logos, reflections, etc. can still reveal who you are or where you were.
- **Other copies of the file**: copies already sent to social media, cloud storage, email, or the **backup folders** the App creates still contain the original metadata.

### 3. AI images are still AI images

Removing metadata does **not** turn AI-generated images or videos into "real" content. They may still be identified as AI through invisible watermarks or detection tools.

**Labelling rules still apply.** If the law (for example Article 50 of the EU AI Act or Vietnam's rules on AI-generated content) or a platform (YouTube, TikTok, Facebook, Instagram, etc.) requires you to disclose AI-generated content, you **must still disclose it**, even after removing metadata. Using the App to deceive or to avoid AI labels breaks the [TERMS](TERMS.md).

### 4. Always keep backups

- The App **overwrites your original files**. Keep **"Make a backup before cleaning"** turned on.
- Single files (not inside a folder you chose) are **not** backed up automatically. Copy them yourself first.
- Backup folders hold **all of the original metadata**. Do not share them, and delete them when you no longer need them (in the App: the **Backups** button).
- **Convert to JPG** creates new files and leaves the originals untouched; the originals still contain their metadata.

### 5. Not legal advice

This page is for information only and is not legal advice. If you need certainty about your obligations, ask a lawyer.
