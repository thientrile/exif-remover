#!/usr/bin/env python3
"""Strip metadata (EXIF/GPS/XMP/IPTC/C2PA) from images, video and PDF, in place, offline.

Needs exiftool, ffmpeg and qpdf on PATH. Each file is cleaned into a temp file in the
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

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".tif", ".tiff"}
VIDEO_EXT = {".mp4", ".mov", ".m4v"}
PDF_EXT = {".pdf"}
SUPPORTED = IMAGE_EXT | VIDEO_EXT | PDF_EXT

# Groups that only describe the file itself, not who/where/what made it.
NEUTRAL_GROUPS = {"ExifTool", "System", "File", "Composite"}
# Any tag in these groups means metadata survived.
BAD_GROUP = re.compile(r"^(IFD\d|ExifIFD|SubIFD|GPS|InteropIFD|MakerNotes|XMP|IPTC|Photoshop|"
                       r"ICC|JUMBF|CBOR|C2PA|Jpeg2000|ItemList|UserData|Keys)", re.I)
BAD_NAME = re.compile(r"^(GPS.*|.*Location.*|Make|Model|.*Serial.*|Author|Artist|Creator|CreatorTool|"
                      r"Software|.*SoftwareAgent.*|Copyright|Owner.*|Lens.*|.*C2PA.*|JUMD.*|Claim.*|"
                      r".*Comment|Keywords|Producer|Encoder|Title|Subject|ImageDescription|"
                      r".*InstanceID|DocumentID|DateTimeOriginal|CreateDate|ModifyDate|MetadataDate)$", re.I)
# Rendering-only EXIF that exiftool writes back when we keep Orientation.
OK_NAMES = {"Orientation", "YCbCrPositioning", "XResolution", "YResolution", "ResolutionUnit", "ExifByteOrder"}
ZERO_DATE = re.compile(r"^[0: ]*$")
# PNG chunks that are allowed to remain: critical ones plus pure rendering hints.
PNG_KEEP = {b"IHDR", b"PLTE", b"IDAT", b"IEND", b"tRNS", b"gAMA", b"cHRM", b"sRGB", b"sBIT",
            b"bKGD", b"pHYs", b"hIST", b"acTL", b"fcTL", b"fdAT"}


def to_posix(path):
    """C:\\Users\\x -> /mnt/c/Users/x (WSL); other paths unchanged."""
    m = re.match(r"^([A-Za-z]):[\\/](.*)$", path)
    if m:
        return "/mnt/" + m.group(1).lower() + "/" + m.group(2).replace("\\", "/")
    return path


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
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
        if g in ("ExifTool", "System", "File") or name in OK_NAMES:
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
    run(["exiftool", "-q", "-q", "-all=", "-tagsfromfile", "@", "-Orientation", "-o", dst, src])


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
        p = subprocess.run(["qpdf", "--object-streams=generate", mid, dst], capture_output=True, text=True)
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
                dirs.sort()
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
        print("usage: exif_remover.py FILE_OR_DIR...   (cleans in place, recursive)")
        return 0 if argv else 2
    for tool in ("exiftool", "ffmpeg", "qpdf"):
        if not shutil.which(tool):
            print(f"missing tool: {tool}", file=sys.stderr)
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
    print(f"\n{ok} cleaned, {failed} failed, {len(skipped)} skipped; metadata tags {tb} -> {ta} "
          f"(remaining tags are structural: size, codec, page count)")
    return 1 if failed or skipped else 0


if __name__ == "__main__":
    sys.exit(main())
