import os
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


def sh(*cmd):
    subprocess.run(cmd, check=True, capture_output=True)


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
        with mock.patch.object(er, "clean_image", lambda s, d: sh("cp", s, d)):  # engine that strips nothing
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
        self.assertEqual(er.main([self.d]), 0)
        self.assertEqual(er.png_extra_chunks(f), [])
        broken = self.p("broken.png")
        with open(broken, "wb") as fh:
            fh.write(b"not a png")
        self.assertEqual(er.main([broken]), 1)
        self.assertEqual(Path(broken).read_bytes(), b"not a png")

    def test_windows_path(self):
        self.assertEqual(er.to_posix(r"C:\Users\me\a b.png"), "/mnt/c/Users/me/a b.png")
        self.assertEqual(er.to_posix("/tmp/x"), "/tmp/x")


if __name__ == "__main__":
    unittest.main()
