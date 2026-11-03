# exif-remover

Local script that strips metadata (EXIF, GPS, XMP, IPTC, comments) from images, video and PDF, like exifremover.com but offline.

## Usage

Needs `exiftool`, `ffmpeg` and `qpdf` (`sudo apt install libimage-exiftool-perl ffmpeg qpdf`). Python 3 stdlib only.

```sh
python3 exif_remover.py PHOTO.jpg 'C:\Users\me\Pictures' ~/videos   # files and/or folders (recursive)
python3 -m unittest discover -s tests                                # tests
```

- **Cleans in place**: same folder, same filename. Each file is written to a hidden temp file next to it, re-checked with `exiftool`, and only then swapped over the original. If cleaning or the check fails, the original is left untouched, the file is listed as `FAIL`, and the exit code is 1.
- Formats: JPEG, PNG, WebP, HEIC, TIFF (`exiftool -all=`, orientation kept), MP4/MOV (`ffmpeg -map_metadata -1 -c copy`, no re-encode; data/telemetry tracks dropped), PDF (`exiftool -all:all=` then a full `qpdf` rewrite so the old metadata can't be recovered).
- Removes EXIF, GPS, XMP, IPTC, ICC profiles, comments, thumbnails and C2PA/JUMBF content credentials (e.g. the ChatGPT `caBX` chunk in PNGs).
- Not removable this way: invisible watermarks embedded in the pixels themselves (C2PA `c2pa.watermarked`, SynthID-style marks).
