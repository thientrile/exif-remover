# Notes for certification (paste into Partner Center → Submission options → Notes for certification)

StarVeil (Vietnamese name: Tinh Ảnh) is a free, offline Win32 desktop app (Python, packaged with PyInstaller) that removes metadata (EXIF, GPS, XMP, IPTC, C2PA) from images, videos and PDFs. The user interface is in Vietnamese only. It needs no account, no sign-in and no network connection; the Store build has its built-in updater switched off and makes no network requests.

How to test (about 2 minutes):
1. Prepare a folder with a JPEG photo that has GPS data (any phone photo works).
2. Start the app. Drag the folder onto the dashed drop area, or click "Chọn thư mục" (Choose folder) and pick it.
3. The row shows status "Chờ" (Waiting) and a tag count in the "Metadata" column. Optional: select the row and click "Xem metadata" (View metadata) to see the tags, including GPS.
4. Keep the switch "Tạo bản sao lưu trước khi xoá" (Make a backup before cleaning) on and click the blue "Xoá metadata" (Remove metadata) button.
5. Expected: the row changes to "✓ Đã xoá" (Removed), the tag count drops (for example 25 → 3, only file-structure tags remain), and a green card says "✓ Đã xoá metadata 1/1 tệp". A backup copy of the folder appears next to it, named "<folder>_backup-YYYY-MM-DD". "Mở thư mục sao lưu" opens it.
6. Optional: add a PNG or WebP image and click "Chuyển sang JPG" (Convert to JPG): a new JPG without metadata is written next to it; the original is unchanged.
7. "Giới thiệu" (About), bottom right, shows the version, licenses, privacy policy and terms.

Expected behaviour worth knowing:
- Files are changed in place (that is the purpose of the app); a backup is made first when a folder is added.
- Backup folders are next to the user's own folders, not in the package, so they remain after uninstall by design. The listing says so.
- The app starts bundled command-line tools as child processes (exiftool.exe with its Perl runtime, ffmpeg.exe, qpdf.exe) from its install folder. They are open-source, unmodified, and their licenses are shown under "Giới thiệu" → "Giấy phép & bên thứ ba".
- Command-line use: `starveil.exe --no-backup <file or folder>` runs without a window.

## runFullTrust justification (Submission options → Restricted capabilities)

StarVeil is a classic Win32 desktop app (Python/PyInstaller) packaged as MSIX. It needs runFullTrust to read and rewrite files and folders that the user selects (anywhere on their disks, cleaned in place, with a backup copy next to them) and to run its bundled, unmodified command-line tools (exiftool, ffmpeg, qpdf) as child processes. It does not request elevation, install services or drivers, or change system settings, and it makes no network connections in the Store build.
