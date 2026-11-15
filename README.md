# exif-remover

Strips metadata (EXIF, GPS, XMP, IPTC, comments, C2PA content credentials) from images, video and PDF, like exifremover.com but offline: runs on your computer, nothing is uploaded.

## Windows app

1. Download `ExifRemover-Setup-<version>.exe` from [Releases](https://github.com/thientrile/exif-remover/releases/latest).
2. Run it. It installs for your user only (no admin) and adds a Start menu entry; uninstall from Settings → Apps.
3. The installer is not code-signed, so Windows SmartScreen will warn "Windows protected your PC": click **More info** → **Run anyway**.

In the app: **Add folder** / **Add files** (several allowed), keep **Make backup** ticked, press **Run**. The log shows one line per file and the last line says `OK` or `FAILED`. exiftool, ffmpeg and qpdf are bundled; nothing else to install.

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
