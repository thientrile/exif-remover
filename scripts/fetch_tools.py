"""Download pinned Windows builds of exiftool, ffmpeg (LGPL) and qpdf into tools/, checking SHA256."""
import hashlib
import io
import os
import sys
import urllib.request
import zipfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools")
# (name, mirrors, sha256, {path inside zip minus top folder: path under tools/}); a trailing "/" copies a folder.
TOOLS = [
    ("exiftool 13.63",
     # exiftool.org links its Windows zip to this SourceForge mirror, where old versions stay.
     ["https://sourceforge.net/projects/exiftool/files/exiftool-13.63_64.zip/download"],
     "7a4bff4b1d6ee15adef882837847f76c0ed23228d294feed285939b6c9b293bd",
     {"exiftool(-k).exe": "exiftool.exe", "exiftool_files/": "exiftool_files/"}),
    ("ffmpeg 8.1.3 LGPL (BtbN)",
     ["https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-11-14-12-37/"
      "ffmpeg-n8.1.3-35-gf1acb0a266-win64-lgpl-8.1.zip"],
     "9a1c8c9f389281749b8d93bfcfaf2164cf95fb74101560ba93a0ec92e1f9e56c",
     {"bin/ffmpeg.exe": "ffmpeg.exe", "LICENSE.txt": "licenses/ffmpeg-LICENSE.txt"}),
    ("qpdf 12.4.2",
     ["https://github.com/qpdf/qpdf/releases/download/v12.4.2/qpdf-12.4.2-msvc64.zip"],
     "db87077e683630c1217e0e8f9a20a9749d952ab676e881c3689187763a5de25d",
     {"bin/": "", "share/doc/qpdf/manual-html/license.html": "licenses/qpdf-license.html"}),
]


def download(urls, sha):
    for url in urls:
        try:
            # SourceForge answers browser-like user agents with an HTML page instead of the file.
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8.5.0"})
            data = urllib.request.urlopen(req, timeout=120).read()
        except OSError as e:
            print(f"  {url}: {e}")
            continue
        got = hashlib.sha256(data).hexdigest()
        if got == sha:
            return data
        print(f"  {url}: SHA256 {got} != {sha}")
    raise SystemExit("download failed or checksum mismatch")


def target(rel, rules):
    for src, dst in rules.items():
        if rel == src:
            return dst
        if src.endswith("/") and rel.startswith(src):
            return dst + rel[len(src):]
    return None


def main():
    for name, urls, sha, rules in TOOLS:
        print(f"{name}")
        with zipfile.ZipFile(io.BytesIO(download(urls, sha))) as z:
            for info in z.infolist():
                rel = info.filename.split("/", 1)[-1]
                dst = None if info.is_dir() else target(rel, rules)
                if dst:
                    out = os.path.join(ROOT, dst)
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                    with z.open(info) as f, open(out, "wb") as o:
                        o.write(f.read())
    return 0


if __name__ == "__main__":
    sys.exit(main())
