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
import time
import uuid
from datetime import date

__version__ = "0.2.6"  # single source: GUI, installer (CI reads it) and the release tag must match

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".avif", ".tif", ".tiff", ".gif", ".bmp"}
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


def in_backup(path):
    """True if path is, or lies inside, a <folder>_backup-YYYY-MM-DD folder: those hold the only originals."""
    return any(BACKUP_DIR.search(part) for part in os.path.normpath(os.path.abspath(path)).split(os.sep))


class Stopped(Exception):
    pass


def count_files(d):
    return sum(len(names) for _, _, names in os.walk(d))


def backup_dir(src, stop=None):
    """cp -a src to a sibling <src>_backup-YYYY-MM-DD[-N]; raise if file counts differ.
    stop: threading.Event; when set mid-copy the partial backup is removed and Stopped is raised."""
    src = os.path.normpath(os.path.realpath(src))
    base = f"{src}_backup-{date.today().isoformat()}"
    dst, n = base, 2
    while True:  # mkdir reserves the name atomically, so the cleanup below only ever removes our own copy
        try:
            os.mkdir(dst)
            break
        except FileExistsError:
            dst, n = f"{base}-{n}", n + 1

    def copy(s, d):
        if stop is not None and stop.is_set():
            raise Stopped()
        return shutil.copy2(s, d)

    try:
        shutil.copytree(src, dst, symlinks=True, copy_function=copy, dirs_exist_ok=True)
    except BaseException:
        shutil.rmtree(dst, ignore_errors=True)
        raise
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


def read_tags_many(paths):
    """One exiftool call for many files: [[(group, name, value), ...] per path], duplicates kept."""
    ee = ["-ee"] if any(os.path.splitext(p)[1].lower() in VIDEO_EXT for p in paths) else []
    p = call(["exiftool", "-j", "-G1", "-a", *ee, *paths])
    try:  # exit code 1 only means some file had an Error tag; that file's JSON still says why
        found = json.loads(p.stdout, object_pairs_hook=lambda kv: kv)
    except ValueError:
        raise RuntimeError(f"exiftool failed: {(p.stderr or p.stdout).strip()[:300]}")
    if len(found) != len(paths):
        raise RuntimeError(f"exiftool failed: {p.stderr.strip()[:300]}")
    return [[(*k.split(":", 1), v) for k, v in pairs if ":" in k] for pairs in found]


def read_tags(path):
    return read_tags_many([path])[0]


SAME_EXT = {".jpeg": ".jpg", ".tiff": ".tif", ".heif": ".heic"}


def real_ext(path, tags):
    """Extension the content really has (exiftool FileTypeExtension), e.g. .jpg for a JPEG named x.png.
    The name's own extension when they agree or the type is unknown."""
    ext = os.path.splitext(path)[1].lower()
    t = next((str(v).lower() for _, n, v in tags if n == "FileTypeExtension"), "")
    t = "." + t if t else ext
    return ext if SAME_EXT.get(t, t) == SAME_EXT.get(ext, ext) else t


def file_type(tags):
    return next((str(v) for _, n, v in tags if n == "FileType"), "")


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
    if path.lower().endswith(".png"):  # clean_file names the temp by real type, so this is a real PNG
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


def engine_for(ext):
    if ext == ".bmp":  # BMP has no metadata blocks and exiftool cannot write it: copy, then verify as usual
        return shutil.copyfile
    if ext in IMAGE_EXT:
        return clean_image
    if ext in VIDEO_EXT:
        return clean_video
    return clean_pdf


def replace(tmp, path, tries=25):
    """os.replace, retried while Windows reports the target open elsewhere (the GUI's tag counter,
    OneDrive sync, antivirus); a reader without FILE_SHARE_DELETE blocks the swap."""
    for i in range(tries):
        try:
            return os.replace(tmp, path)
        except PermissionError:
            if i == tries - 1:
                raise
            time.sleep(0.2)


def clean_file(path):
    """Clean one file in place. Returns (tags_before, tags_after); raises on failure, original untouched."""
    path = os.path.realpath(path)
    tags = read_tags(path)
    errors = [v for _, n, v in tags if n == "Error"]
    if errors:
        raise RuntimeError(f"unreadable: {errors[0]}")
    before = meta_count(tags)
    # The tools pick the format from the extension: a JPEG named .png must be handled as .jpg (and keep its name).
    ext = real_ext(path, tags)
    if ext not in SUPPORTED:
        raise RuntimeError(f"content is {file_type(tags) or 'unknown'}, not {os.path.splitext(path)[1]}: unsupported")
    d, name = os.path.split(path)
    stem = os.path.splitext(name)[0]
    token = uuid.uuid4().hex[:8]
    tmp = os.path.join(d, f".{stem}.exifclean-{token}{ext}")
    # exiftool also reads the source type from its name, so a misnamed source is read via a correctly named copy.
    src = path if ext == os.path.splitext(name)[1].lower() else os.path.join(d, f".{stem}.exifclean-src-{token}{ext}")
    try:
        if src != path:
            shutil.copy2(path, src)
        engine_for(ext)(src, tmp)
        after = meta_count(verify(tmp))
        shutil.copymode(path, tmp)
        replace(tmp, path)
    finally:
        for f in {tmp, src} - {path}:
            if os.path.exists(f):
                os.remove(f)
    return before, after


CONVERT_EXT = {".png", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".avif", ".heic", ".heif"}
# EXIF Orientation (exiftool's text) -> ffmpeg filter that turns the pixels upright.
ORIENT = {"Mirror horizontal": "hflip", "Rotate 180": "hflip,vflip", "Mirror vertical": "vflip",
          "Mirror horizontal and rotate 270 CW": "transpose=0", "Rotate 90 CW": "transpose=1",
          "Rotate 270 CW": "transpose=2", "Mirror horizontal and rotate 90 CW": "transpose=3"}
FLATTEN = "format=rgba,split[a][b];[a]drawbox=c=white:t=fill[bg];[bg][b]overlay=format=rgb"  # transparency -> white


class Skipped(Exception):
    pass


def webp_first_frame(path, out):
    """ffmpeg cannot decode animated WebP: write its first frame as a still WebP to out.
    Returns the pad filter that places it on the canvas, or None if path is not animated."""
    with open(path, "rb") as f:
        data = f.read()
    chunks, i = {}, 12
    while i + 8 <= len(data):
        kind, n = data[i:i + 4], struct.unpack("<I", data[i + 4:i + 8])[0]
        chunks.setdefault(kind, data[i + 8:i + 8 + n])
        i += 8 + n + (n & 1)
    if b"ANIM" not in chunks or b"ANMF" not in chunks:
        return None
    u24 = lambda b, o: int.from_bytes(b[o:o + 3], "little")  # noqa: E731
    canvas, frame = chunks[b"VP8X"], chunks[b"ANMF"]
    x, y, w, h = 2 * u24(frame, 0), 2 * u24(frame, 3), u24(frame, 6) + 1, u24(frame, 9) + 1
    body = frame[16:]  # ALPH (optional) then VP8/VP8L, already padded RIFF sub-chunks
    vp8x = struct.pack("<I", 0x10 if b"ALPH" in body[:4] or b"VP8L" in body[:4] else 0)
    vp8x += (w - 1).to_bytes(3, "little") + (h - 1).to_bytes(3, "little")
    payload = b"WEBP" + b"VP8X" + struct.pack("<I", 10) + vp8x + body
    with open(out, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", len(payload)) + payload)
    return f"pad={u24(canvas, 4) + 1}:{u24(canvas, 7) + 1}:{x}:{y}:color=white"


def reserve_jpg(path):
    """Create an empty name.jpg (else name-1.jpg, name-2.jpg...) next to path; exclusive create, so never an existing file."""
    stem, n = os.path.splitext(path)[0], 0
    while True:
        out = f"{stem}-{n}.jpg" if n else stem + ".jpg"
        try:
            open(out, "x").close()
            return out
        except FileExistsError:
            n += 1


def convert_file(path):
    """Write a metadata-free JPEG copy next to path; the original is never changed.
    Returns (jpg_path, note); note says when only the first frame of an animation was used.
    Raises Skipped (already a JPEG, not an image) or RuntimeError (nothing is left behind)."""
    path = os.path.realpath(path)
    tags = read_tags(path)
    errors = [v for _, n, v in tags if n == "Error"]
    if errors:
        raise RuntimeError(f"unreadable: {errors[0]}")
    ext = real_ext(path, tags)
    if ext in (".jpg", ".jpeg"):
        raise Skipped("already a JPEG")
    if ext not in CONVERT_EXT:
        raise Skipped(f"not a convertible image ({file_type(tags) or ext})")
    get = lambda name: next((str(v) for _, n, v in tags if n == name), "")  # noqa: E731
    d, name = os.path.split(path)
    stem, token = os.path.splitext(name)[0], uuid.uuid4().hex[:8]
    part = lambda kind, e: os.path.join(d, f".{stem}.exifclean-{kind}{token}{e}")  # noqa: E731
    src, mid, frame, tmp = part("src-", ext), part("mid-", ".jpg"), part("frame-", ".webp"), part("", ".jpg")
    out = None
    try:
        if ext == os.path.splitext(name)[1].lower():
            src = path
        else:  # exiftool reads the type from the name: a misnamed source is read via a correctly named copy
            shutil.copy2(path, src)
        flt = [FLATTEN]
        # HEIF/AVIF rotation lives in the container (irot/imir): ffmpeg applies it while decoding. For the others
        # ffmpeg's handling of EXIF Orientation differs between versions, so it is off and applied here.
        auto = ext in (".heic", ".heif", ".avif")
        if not auto and get("Orientation") in ORIENT:
            flt.insert(0, ORIENT[get("Orientation")])
        animated = (int(get("FrameCount") or 1) > 1 or int(get("AnimationFrames") or 1) > 1
                    or "Animation" in get("WebP_Flags"))
        pad = webp_first_frame(src, frame) if ext == ".webp" else None
        if pad:  # rebuild the canvas first, so the orientation below turns the whole frame
            flt.insert(0, pad)
        if auto:  # ffmpeg 8.1 assembles HEIF grids/alpha in its own filtergraph, which -vf cannot extend: decode first
            frame = part("frame-", ".png")
            run(["ffmpeg", "-nostdin", "-v", "error", "-i", src, "-frames:v", "1", "-y", frame])
        run(["ffmpeg", "-nostdin", "-v", "error", "-noautorotate", "-i", frame if pad or auto else src,
             "-vf", ",".join(flt),
             "-frames:v", "1", "-q:v", "2", "-pix_fmt", "yuvj420p", "-fflags", "+bitexact", "-flags:v", "+bitexact",
             "-y", mid])
        # Keep an RGB colour profile so colours do not shift; a CMYK/grey one would not match the RGB pixels.
        icc = ["-tagsfromfile", src, "-ICC_Profile"] if get("ColorSpaceData").strip() == "RGB" else []
        run(["exiftool", "-q", "-q", "-all=", *icc, "-o", tmp, mid])
        verify(tmp)
        out = reserve_jpg(path)
        replace(tmp, out)
    except BaseException:
        if out and os.path.exists(out) and os.path.getsize(out) == 0:
            os.remove(out)
        raise
    finally:
        for f in {src, mid, frame, tmp} - {path}:
            if os.path.exists(f):
                os.remove(f)
    return out, "first frame only (animated)" if animated else ""


def collect(args):
    files, skipped = [], []
    for a in args:
        p = to_posix(a)
        if in_backup(p):
            skipped.append(a)
        elif os.path.isdir(p):
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


def to_jpg_main(argv):
    for t in ("exiftool", "ffmpeg"):
        if not tool(t):
            print(f"missing tool: {t}", file=sys.stderr)
            return 2
    files, missing = collect(argv)
    ok = skipped = failed = 0
    for f in files:
        try:
            out, note = convert_file(f)
            ok += 1
            print(f"OK     {f} -> {os.path.basename(out)}" + (f"  ({note})" if note else ""))
        except Skipped as e:
            skipped += 1
            print(f"SKIP   {f}: {e}")
        except Exception as e:
            failed += 1
            print(f"FAIL   {f}: {e}", file=sys.stderr)
    for m in missing:
        print(f"SKIP   {m} (not found, unsupported type, or a _backup- folder)")
    print(f"\n{'FAILED' if failed or missing else 'OK'}: {ok} converted, {skipped} skipped, {failed} failed")
    return 1 if failed or missing else 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        print("usage: exif-remover [--no-backup] FILE_OR_DIR...\n"
              "  cleans in place, recursive; each folder is first copied to <folder>_backup-YYYY-MM-DD\n"
              "       exif-remover --to-jpg FILE_OR_DIR...\n"
              "  writes a metadata-free name.jpg (or name-1.jpg...) next to each image; originals untouched")
        return 0 if argv else 2
    if argv[0] == "--to-jpg":
        return to_jpg_main(argv[1:])
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
                if os.path.isdir(to_posix(a)) and not in_backup(to_posix(a)):
                    backups.append(backup_dir(to_posix(a)))
                    print(f"BACKUP {to_windows(backups[-1])}  ({count_files(backups[-1])} files)")
        except Exception as e:
            print(f"FAILED: backup failed, nothing was cleaned: {e}", file=sys.stderr)
            return 2
    files, skipped = collect(argv)
    for s in skipped:
        print(f"SKIP   {s} (not found, unsupported type, or a _backup- folder)")
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
