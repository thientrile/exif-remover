# exif-remover

Strips metadata (EXIF, GPS, XMP, IPTC, comments, C2PA content credentials) from images, video and PDF, like exifremover.com but offline: runs on your computer, nothing is uploaded.

## Hướng dẫn cho Windows (tiếng Việt)

Ứng dụng xoá thông tin ẩn (vị trí GPS, máy chụp, tác giả, phần mềm, dấu C2PA của ảnh AI...) khỏi ảnh, video và PDF. Chạy hoàn toàn trên máy bạn, không cần mạng, không tải file lên đâu cả.

<img src="docs/screenshot.png" alt="Cửa sổ Exif Remover sau khi chạy xong" width="560" align="right">

1. **Tải bộ cài**: mở trang [Releases mới nhất](https://github.com/thientrile/exif-remover/releases/latest), bấm vào file `ExifRemover-Setup-x.y.z.exe` (x.y.z là số phiên bản, ví dụ `0.1.0`) để tải về.
2. **Chạy bộ cài**: mở file vừa tải. Windows có thể hiện cảnh báo xanh *"Windows protected your PC"* vì bộ cài chưa được ký số: bấm **More info** rồi bấm **Run anyway**.
3. **Cài đặt**: bấm **Next** / **Install** đến khi xong (không cần quyền admin). Sau đó mở ứng dụng từ menu **Start**, tìm **Exif Remover**.
4. **Chọn file**: bấm **Add folder** để chọn cả thư mục (gồm các thư mục con), hoặc **Add files** để chọn từng file. Có thể thêm nhiều lần. Chọn nhầm thì bấm vào dòng đó rồi bấm **Remove**.
5. **Giữ ô "Make backup" được tích** (mặc định đã tích). Trước khi xoá, ứng dụng sao chép nguyên thư mục ra một bản dự phòng bên cạnh.
6. **Bấm Run**. Mỗi file hiện một dòng trong khung nhật ký. File được làm sạch ngay tại chỗ (giữ nguyên tên và vị trí).
7. **Xem kết quả** ở dòng cuối:
   - `OK: all files cleaned and verified` (chữ xanh): tất cả đã sạch và đã được kiểm tra lại.
   - `FAILED: see the log` (chữ đỏ): có file lỗi, xem dòng `FAIL` trong nhật ký. File lỗi được giữ nguyên như cũ.
   - Bản dự phòng nằm cạnh thư mục gốc, tên dạng `<tên thư mục>_backup-NĂM-THÁNG-NGÀY`, đường dẫn in ở dòng `BACKUP` đầu nhật ký và cuối dòng `OK: ... Backup: ...`. Ví dụ chọn `C:\demo\photos` thì bản dự phòng là `C:\demo\photos_backup-2026-11-15`. Kiểm tra ảnh đã ổn thì có thể xoá thư mục dự phòng này cho nhẹ máy.
8. **Gỡ cài đặt**: **Settings** → **Apps** → **Installed apps**, tìm **Exif Remover**, bấm **...** → **Uninstall**. Các file bạn đã làm sạch và bản dự phòng không bị xoá.

Lưu ý: chỉ thư mục thêm bằng **Add folder** (khi ô **Make backup** được tích) mới được sao lưu; file thêm riêng bằng **Add files** thì không.

<br clear="right">

## Windows app (English)

1. Download `ExifRemover-Setup-<version>.exe` from [Releases](https://github.com/thientrile/exif-remover/releases/latest) and run it. It installs for your user only (no admin) and adds a Start menu entry; uninstall from Settings → Apps.
2. The installer is not code-signed, so Windows SmartScreen will warn "Windows protected your PC": click **More info** → **Run anyway**.
3. In the app: **Add folder** / **Add files** (several allowed), keep **Make backup** ticked, press **Run**. The log shows one line per file and the last line says `OK` or `FAILED`. exiftool, ffmpeg and qpdf are bundled; nothing else to install.

## CLI (Linux / WSL)

Needs `exiftool`, `ffmpeg` and `qpdf` (`sudo apt install libimage-exiftool-perl ffmpeg qpdf`). Python 3 stdlib only.

```sh
exif-remover "C:\path\to\folder"      # backup + clean + verify + summary (WSL maps C:\ to /mnt/c)
exif-remover --no-backup PHOTO.jpg ~/videos
python3 -m unittest discover -s tests   # tests
```

Install (no sudo): `chmod +x exif_remover.py && ln -s "$PWD/exif_remover.py" ~/.local/bin/exif-remover`.
The Windows app takes the same arguments: `ExifRemover.exe --no-backup C:\photos` runs without a window (exit code 0 = OK).

## What it does

- **Backup first**: each folder given is copied to a sibling `<folder>_backup-YYYY-MM-DD` (`-2`, `-3`… if it exists). If the file count does not match, it stops before cleaning anything. Folders named `*_backup-*` are skipped while scanning. Single files are not backed up; `--no-backup` (or unticking **Make backup**) turns backups off.
- **Cleans in place**: same folder, same filename. Each file is written to a hidden temp file next to it, re-checked with `exiftool`, and only then swapped over the original. If cleaning or the check fails, the original is left untouched, the file is listed as `FAIL`, and the exit code is 1.
- The last line is `OK: N cleaned, 0 failed, 0 skipped. Backup: ...` or `FAILED: ...`.
- Formats: JPEG, PNG, WebP, HEIC, TIFF (`exiftool -all=`, orientation kept), MP4/MOV (`ffmpeg -map_metadata -1 -c copy`, no re-encode; data/telemetry tracks dropped), PDF (`exiftool -all:all=` then a full `qpdf` rewrite so the old metadata can't be recovered).
- Removes EXIF, GPS, XMP, IPTC, ICC profiles, comments, thumbnails and C2PA/JUMBF content credentials (e.g. the ChatGPT `caBX` chunk in PNGs).
- Not removable this way: invisible watermarks embedded in the pixels themselves (C2PA `c2pa.watermarked`, SynthID-style marks).

## Building

GitHub Actions (`.github/workflows/build.yml`, `windows-latest`) downloads pinned, SHA256-checked builds of the tools (`scripts/fetch_tools.py`), runs the tests on Windows, packages with PyInstaller and builds the installer with Inno Setup (`installer.iss`), installs it and smoke-tests it. A `v*` tag publishes the installer to Releases.

## License

MIT (`LICENSE`). The bundled tools keep their own licenses: see `THIRD_PARTY_NOTICES.md`.
