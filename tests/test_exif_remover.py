import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import exif_remover as er  # noqa: E402


def sh(name, *args):
    subprocess.run([er.tool(name) or name, *args], check=True, capture_output=True)


def png_chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def c2pa_jumbf():
    """Minimal JUMBF superbox labelled c2pa, like ChatGPT's caBX payload."""
    jumd_body = bytes.fromhex("6332706100110010800000aa00389b71") + b"\x03" + b"c2pa\x00"
    jumd = struct.pack(">I", 8 + len(jumd_body)) + b"jumd" + jumd_body
    return struct.pack(">I", 8 + len(jumd)) + b"jumb" + jumd


def insert_after_ihdr(path, *chunks):
    with open(path, "rb") as f:
        data = f.read()
    cut = 8 + 25  # signature + IHDR chunk
    with open(path, "wb") as f:
        f.write(data[:cut] + b"".join(chunks) + data[cut:])


def names(path):
    return {n for _, n, _ in er.read_tags(path)}


class CleanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def p(self, name):
        return os.path.join(self.d, name)

    def assert_no_temp_left(self):
        self.assertEqual([n for n in os.listdir(self.d) if ".exifclean-" in n], [])

    def test_jpeg_gps_removed_orientation_kept(self):
        f = self.p("a.jpg")
        sh("ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=red:s=16x16", "-frames:v", "1", f)
        sh("exiftool", "-q", "-overwrite_original", "-GPSLatitude=48.8", "-GPSLatitudeRef=N",
           "-GPSLongitude=2.3", "-GPSLongitudeRef=E", "-Make=Canon", "-Model=EOS", "-SerialNumber=123",
           "-Artist=Bob", "-Orientation#=6", f)
        u = self.p("ảnh GPS.jpg")  # non-ASCII name: exiftool on Windows needs the UTF-8 argfile path
        os.rename(f, u)
        f = u
        self.assertIn("GPSLatitude", names(f))
        before, after = er.clean_file(f)
        self.assertGreater(before, after)
        left = names(f)
        for t in ("GPSLatitude", "Make", "Model", "SerialNumber", "Artist"):
            self.assertNotIn(t, left)
        self.assertIn("Orientation", left)
        self.assert_no_temp_left()

    def test_png_c2pa_and_text_chunks_removed(self):
        f = self.p("a.png")
        sh("ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=blue:s=16x16", "-frames:v", "1", f)
        insert_after_ihdr(f, png_chunk(b"caBX", c2pa_jumbf()),
                          png_chunk(b"tEXt", b"Software\x00ChatGPT"))
        self.assertTrue(er.png_extra_chunks(f))
        self.assertIn("JUMBF", {g for g, _, _ in er.read_tags(f)})
        er.clean_file(f)
        self.assertEqual(er.png_extra_chunks(f), [])
        self.assertNotIn("JUMBF", {g for g, _, _ in er.read_tags(f)})

    def test_mp4_metadata_removed(self):
        f = self.p("a.mp4")
        sh("ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=d=1:s=32x32", "-c:v", "mpeg4",
           "-metadata", "title=Secret", "-metadata", "artist=Bob", "-metadata", "location=+48.85+002.35/", f)
        self.assertIn("GPSLatitude", names(f))
        er.clean_file(f)
        left = names(f)
        for t in ("GPSLatitude", "Title", "Artist", "Encoder", "LocationInformation"):
            self.assertNotIn(t, left)
        self.assertIn("ImageWidth", left)

    def test_pdf_author_removed_and_not_recoverable(self):
        f = self.p("a.pdf")
        sh("qpdf", "--empty", f)
        sh("exiftool", "-q", "-overwrite_original", "-Author=BobSecret", "-Title=Plan", f)
        sh("qpdf", "--replace-input", f)  # bake into base objects, else exiftool just undoes its own edit
        er.clean_file(f)
        self.assertNotIn("Author", names(f))
        self.assertNotIn(b"BobSecret", Path(f).read_bytes())  # old revision really gone

    def test_failed_verify_leaves_original_intact(self):
        f = self.p("a.jpg")
        sh("ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=red:s=16x16", "-frames:v", "1", f)
        sh("exiftool", "-q", "-overwrite_original", "-GPSLatitude=48.8", "-GPSLatitudeRef=N", f)
        original = Path(f).read_bytes()
        with mock.patch.object(er, "clean_image", shutil.copy):  # engine that strips nothing
            with self.assertRaisesRegex(RuntimeError, "metadata left"):
                er.clean_file(f)
        self.assertEqual(Path(f).read_bytes(), original)
        self.assert_no_temp_left()

    def test_cli_recursive_and_exit_code(self):
        os.makedirs(self.p("sub"))
        f = self.p("sub/x.png")
        sh("ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=blue:s=16x16", "-frames:v", "1", f)
        insert_after_ihdr(f, png_chunk(b"tEXt", b"Author\x00Bob"))
        with open(self.p("notes.txt"), "w") as fh:
            fh.write("ignored")
        self.assertEqual(er.main(["--no-backup", self.d]), 0)
        self.assertEqual(er.png_extra_chunks(f), [])
        broken = self.p("broken.png")
        with open(broken, "wb") as fh:
            fh.write(b"not a png")
        self.assertEqual(er.main([broken]), 1)
        self.assertEqual(Path(broken).read_bytes(), b"not a png")

    def make_tagged_png(self, rel):
        f = self.p(rel)
        os.makedirs(os.path.dirname(f), exist_ok=True)
        sh("ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=blue:s=16x16", "-frames:v", "1", f)
        insert_after_ihdr(f, png_chunk(b"tEXt", b"Author\x00Bob"))
        return f

    def test_auto_backup_of_folder(self):
        f = self.make_tagged_png("in/sub/x.png")
        tagged = Path(f).read_bytes()
        today = er.date.today().isoformat()
        self.assertEqual(er.main([self.p("in")]), 0)
        bak = self.p(f"in_backup-{today}/sub/x.png")
        self.assertEqual(Path(bak).read_bytes(), tagged)  # backup holds the original
        self.assertEqual(er.png_extra_chunks(f), [])
        # second run: new -2 backup, and an old backup inside the folder is never cleaned
        inner = self.make_tagged_png(f"in/old_backup-{today}/y.png")
        self.assertEqual(er.main([self.p("in")]), 0)
        self.assertTrue(os.path.isfile(self.p(f"in_backup-{today}-2/sub/x.png")))
        self.assertTrue(er.png_extra_chunks(inner))

    def test_no_backup_flag(self):
        self.make_tagged_png("in/x.png")
        self.assertEqual(er.main(["--no-backup", self.p("in")]), 0)
        self.assertEqual(sorted(os.listdir(self.d)), ["in"])

    def test_backup_count_mismatch_aborts_untouched(self):
        f = self.make_tagged_png("in/x.png")
        tagged = Path(f).read_bytes()
        with mock.patch.object(er, "count_files", side_effect=[1, 2]):
            self.assertEqual(er.main([self.p("in")]), 2)
        self.assertEqual(Path(f).read_bytes(), tagged)

    def test_bundled_tool_preferred_over_path(self):
        os.makedirs(self.p("tools"))
        exe = self.p("tools/qpdf.exe" if os.name == "nt" else "tools/qpdf")
        Path(exe).write_text("")
        os.chmod(exe, 0o755)
        with mock.patch.object(er, "HERE", self.d):
            self.assertEqual(os.path.normcase(er.tool("qpdf")), os.path.normcase(exe))
        self.assertIsNone(er.tool("no-such-tool-xyz"))

    @unittest.skipIf(os.name == "nt", "WSL path mapping is off on native Windows")
    def test_windows_path(self):
        self.assertEqual(er.to_posix(r"C:\Users\me\a b.png"), "/mnt/c/Users/me/a b.png")
        self.assertEqual(er.to_posix("/tmp/x"), "/tmp/x")
        self.assertEqual(er.to_windows("/mnt/c/Users/me/a_backup-2026-11-03"), r"C:\Users\me\a_backup-2026-11-03")


if __name__ == "__main__":
    unittest.main()
