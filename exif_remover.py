#!/usr/bin/env python3
"""Strip metadata (EXIF/GPS/XMP/IPTC/C2PA) from images, video and PDF, in place, offline.

Needs exiftool, ffmpeg and qpdf: bundled in tools/ next to the app, else on PATH. Each file is cleaned into a temp file in the
same folder, verified, then atomically swapped over the original. On any failure the
original is left untouched.
"""
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import uuid
from datetime import date

__version__ = "0.2.0"  # single source: GUI, installer (CI reads it) and the release tag must match

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".avif", ".tif", ".tiff", ".gif"}
VIDEO_EXT = {".mp4", ".mov", ".m4v"}
PDF_EXT = {".pdf"}
SUPPORTED = IMAGE_EXT | VIDEO_EXT | PDF_EXT

# Groups that only describe the file itself, not who/where/what made it.
NEUTRAL_GROUPS = {"ExifTool", "System", "File", "Composite"}
# Any tag in these groups means metadata survived.
BAD_GROUP = re.compile(r"^(IFD\d|ExifIFD|SubIFD|GPS|InteropIFD|MakerNotes|XMP|IPTC|Photoshop|"
                       r"JUMBF|CBOR|C2PA|Jpeg2000|ItemList|UserData|Keys)", re.I)
BAD_NAME = re.compile(r"^(GPS.*|.*Location.*|Make|Model|.*Serial.*|Author|Artist|Creator|CreatorTool|"
                      r"Software|.*SoftwareAgent.*|Copyright|Owner.*|Lens.*|.*C2PA.*|JUMD.*|Claim.*|"
                      r".*Comment|Keywords|Producer|Encoder|Title|Subject|ImageDescription|"
                      r".*InstanceID|DocumentID|DateTimeOriginal|CreateDate|ModifyDate|MetadataDate)$", re.I)
# Rendering-only EXIF that exiftool writes back when we keep Orientation.
OK_NAMES = {"Orientation", "YCbCrPositioning", "XResolution", "YResolution", "ResolutionUnit", "ExifByteOrder"}
ZERO_DATE = re.compile(r"^[0: ]*$")
# PNG chunks that are allowed to remain: critical ones plus pure rendering hints (iCCP = colour profile).
PNG_KEEP = {b"IHDR", b"PLTE", b"IDAT", b"IEND", b"tRNS", b"gAMA", b"cHRM", b"sRGB", b"sBIT",
            b"bKGD", b"pHYs", b"iCCP", b"hIST", b"acTL", b"fcTL", b"fdAT"}


HERE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.realpath(__file__)))
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # no console flash per call from the Windows GUI


def tool(name):
    """Bundled tools/<name>[.exe] first, then PATH; None if missing."""
    return shutil.which(name, path=os.path.join(HERE, "tools")) or shutil.which(name)


def to_posix(path):
    """C:\\Users\\x -> /mnt/c/Users/x (WSL); unchanged on native Windows and for other paths."""
    m = os.name != "nt" and re.match(r"^([A-Za-z]):[\\/](.*)$", path)
    if m:
        return "/mnt/" + m.group(1).lower() + "/" + m.group(2).replace("\\", "/")
    return path


def to_windows(path):
    """/mnt/c/Users/x -> C:\\Users\\x for Explorer; other paths unchanged."""
    m = re.match(r"^/mnt/([a-z])(/.*)?$", path)
    return m.group(1).upper() + ":" + (m.group(2) or "/").replace("/", "\\") if m else path


BACKUP_DIR = re.compile(r"_backup-\d{4}-\d{2}-\d{2}(-\d+)?$")


def count_files(d):
    return sum(len(names) for _, _, names in os.walk(d))


def backup_dir(src):
    """cp -a src to a sibling <src>_backup-YYYY-MM-DD[-N]; raise if file counts differ."""
    src = os.path.normpath(os.path.realpath(src))
    base = f"{src}_backup-{date.today().isoformat()}"
    dst, n = base, 2
    while os.path.exists(dst):
        dst, n = f"{base}-{n}", n + 1
    shutil.copytree(src, dst, symlinks=True)
    got, want = count_files(dst), count_files(src)
    if got != want:
        raise RuntimeError(f"backup {dst} has {got} files, source has {want}")
    return dst


def call(cmd):
    exe, args, stdin = tool(cmd[0]) or cmd[0], cmd[1:], None
    if cmd[0] == "exiftool":
        # Args via a UTF-8 argfile: Windows exiftool reads its command line in the ANSI codepage,
        # which mangles non-ASCII file names. shortcut: file names containing newlines unsupported.
        args, stdin = ["-charset", "filename=utf8", "-@", "-"], "\n".join(args) + "\n"
    return subprocess.run([exe, *args], input=stdin, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", creationflags=NO_WINDOW)


def run(cmd):
    p = call(cmd)
    if p.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {(p.stderr or p.stdout).strip()[:300]}")
    return p.stdout


def read_tags(path):
    """[(group, name, value), ...] from exiftool, duplicates kept."""
    ee = ["-ee"] if os.path.splitext(path)[1].lower() in VIDEO_EXT else []
    out = run(["exiftool", "-j", "-G1", "-a", *ee, path])
    pairs = json.loads(out, object_pairs_hook=lambda kv: kv)[0]
    return [(*k.split(":", 1), v) for k, v in pairs if ":" in k]


def meta_count(tags):
    return sum(1 for g, _, _ in tags if g not in NEUTRAL_GROUPS)


def leftovers(tags):
    bad = []
    for g, name, v in tags:
        # ICC colour profile is kept on purpose: needed for correct colours, holds no personal data.
        if g in ("ExifTool", "System", "File") or g.startswith("ICC") or name in OK_NAMES:
            continue
        if BAD_GROUP.match(g) or (BAD_NAME.match(name) and not (name.endswith("Date") and ZERO_DATE.match(str(v)))):
            bad.append(f"{g}:{name}")
    return bad


def png_extra_chunks(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return ["not a PNG"]
    extra, i = [], 8
    while i + 8 <= len(data):
        n, t = struct.unpack(">I4s", data[i:i + 8])
        if t not in PNG_KEEP:
            extra.append("PNG chunk " + t.decode("latin-1"))
        i += 12 + n
    return extra


def verify(path):
    """Raise if any identifying metadata survived."""
    tags = read_tags(path)
    errors = [v for g, n, v in tags if n == "Error"]
    if errors:
        raise RuntimeError(f"unreadable output: {errors[0]}")
    bad = leftovers(tags)
    if path.lower().endswith(".png"):
        bad += png_extra_chunks(path)
    if bad:
        raise RuntimeError("metadata left: " + ", ".join(sorted(set(bad))[:10]))
    return tags


def clean_image(src, dst):
    run(["exiftool", "-q", "-q", "-all=", "-tagsfromfile", "@", "-Orientation", "-ICC_Profile", "-o", dst, src])


def clean_video(src, dst):
    # Data streams are dropped: they carry timed GPS/telemetry (GoPro gpmd, iPhone mebx).
    run(["ffmpeg", "-nostdin", "-v", "error", "-i", src, "-map", "0", "-map", "-0:d?",
         "-map_metadata", "-1", "-map_chapters", "-1", "-c", "copy",
         "-fflags", "+bitexact", "-flags:v", "+bitexact", "-flags:a", "+bitexact", "-y", dst])


def clean_pdf(src, dst):
    mid = dst + ".mid.pdf"
    try:
        run(["exiftool", "-q", "-q", "-all:all=", "-o", mid, src])
        # Full rewrite drops the old objects exiftool's incremental update left behind.
        p = call(["qpdf", "--object-streams=generate", mid, dst])
        if p.returncode not in (0, 3):  # 3 = succeeded with warnings
            raise RuntimeError(f"qpdf failed: {p.stderr.strip()[:300]}")
    finally:
        if os.path.exists(mid):
            os.remove(mid)


def engine_for(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in IMAGE_EXT:
        return clean_image
    if ext in VIDEO_EXT:
        return clean_video
    return clean_pdf


def clean_file(path):
    """Clean one file in place. Returns (tags_before, tags_after); raises on failure, original untouched."""
    path = os.path.realpath(path)
    before = meta_count(read_tags(path))
    d, name = os.path.split(path)
    stem, ext = os.path.splitext(name)
    tmp = os.path.join(d, f".{stem}.exifclean-{uuid.uuid4().hex[:8]}{ext}")
    try:
        engine_for(path)(path, tmp)
        after = meta_count(verify(tmp))
        shutil.copymode(path, tmp)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return before, after


def collect(args):
    files, skipped = [], []
    for a in args:
        p = to_posix(a)
        if os.path.isdir(p):
            for root, dirs, names in os.walk(p):
                dirs[:] = sorted(x for x in dirs if not BACKUP_DIR.search(x))
                for n in sorted(names):
                    if os.path.splitext(n)[1].lower() in SUPPORTED and ".exifclean-" not in n:
                        files.append(os.path.join(root, n))
        elif os.path.isfile(p) and os.path.splitext(p)[1].lower() in SUPPORTED:
            files.append(p)
        else:
            skipped.append(a)
    return files, skipped


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        print("usage: exif-remover [--no-backup] FILE_OR_DIR...\n"
              "  cleans in place, recursive; each folder is first copied to <folder>_backup-YYYY-MM-DD")
        return 0 if argv else 2
    no_backup = "--no-backup" in argv
    argv = [a for a in argv if a != "--no-backup"]
    for t in ("exiftool", "ffmpeg", "qpdf"):
        if not tool(t):
            print(f"missing tool: {t}", file=sys.stderr)
            return 2
    backups = []
    if not no_backup:  # shortcut: single-file inputs get no backup, only folders do
        try:
            for a in argv:
                if os.path.isdir(to_posix(a)):
                    backups.append(backup_dir(to_posix(a)))
                    print(f"BACKUP {to_windows(backups[-1])}  ({count_files(backups[-1])} files)")
        except Exception as e:
            print(f"FAILED: backup failed, nothing was cleaned: {e}", file=sys.stderr)
            return 2
    files, skipped = collect(argv)
    for s in skipped:
        print(f"SKIP   {s} (not found or unsupported type)")
    ok = failed = tb = ta = 0
    for f in files:
        try:
            b, a = clean_file(f)
            ok, tb, ta = ok + 1, tb + b, ta + a
            print(f"OK     {b:4d} -> {a:3d} tags  {f}")
        except Exception as e:
            failed += 1
            print(f"FAIL   {f}: {e}", file=sys.stderr)
    print(f"\nmetadata tags {tb} -> {ta} (remaining tags are structural: size, codec, page count)")
    where = "; ".join(to_windows(b) for b in backups) or "none"
    status = "FAILED" if failed or skipped else "OK"
    print(f"{status}: {ok} cleaned, {failed} failed, {len(skipped)} skipped. Backup: {where}")
    return 1 if failed or skipped else 0


if __name__ == "__main__":
    sys.exit(main())
