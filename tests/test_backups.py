import os
import sys
import tempfile
import unittest
from datetime import date
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import backups  # noqa: E402

REAL_RECYCLE = backups._recycle


class BackupTrackingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        p = mock.patch.object(backups, "FILE", os.path.join(self.d, "cfg", "backups.json"))
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)
        # Recycle Bin is Windows-only; here "recycling" just removes the folder
        r = mock.patch.object(backups, "_recycle", side_effect=lambda path: __import__("shutil").rmtree(path))
        r.start()
        self.addCleanup(r.stop)

    def folder(self, name, files=1):
        path = os.path.join(self.d, name)
        os.makedirs(path)
        for i in range(files):
            with open(os.path.join(path, f"{i}.jpg"), "wb") as f:
                f.write(b"x" * 10)
        return path

    def test_lists_only_recorded_existing_and_matching(self):
        src = self.folder("photos")
        good = self.folder("photos_backup-2026-11-01", 3)
        good2 = self.folder("photos_backup-2026-11-01-2")
        renamed = self.folder("photos_renamed")  # recorded, but no longer our pattern
        self.folder("photos_backup-2026-10-01")  # matches, but never recorded
        for p in (good, good2, renamed, os.path.join(self.d, "gone_backup-2026-01-01")):
            backups.record(p, src)
        backups.record(good, src)  # recorded twice
        got = backups.listed()
        self.assertEqual([e["path"] for e in got], [good, good2])
        self.assertTrue(got[0]["src_exists"])
        self.assertEqual(backups.size(good), (3, 30))
        self.assertEqual(len(backups._load()), 2)  # missing/renamed entries dropped from the file

    def test_src_gone_reported(self):
        b = self.folder("x_backup-2026-11-01")
        backups.record(b, os.path.join(self.d, "x"))
        self.assertFalse(backups.listed()[0]["src_exists"])

    def test_delete_refuses_unrecorded_and_non_matching(self):
        src = self.folder("photos")
        good = self.folder("photos_backup-2026-11-01")
        stranger = self.folder("other_backup-2026-11-01")  # matches the pattern, but we never made it
        renamed = self.folder("keep_me")
        backups.record(good, src)
        backups.record(renamed, src)
        done, errors = backups.delete([good, stranger, renamed, src])
        self.assertEqual(done, [good])
        self.assertEqual({p for p, _ in errors}, {stranger, renamed, src})
        for p in (stranger, renamed, src):
            self.assertTrue(os.path.isdir(p))
        self.assertFalse(os.path.exists(good))
        self.assertEqual(backups.listed(), [])

    def test_older_than(self):
        old = self.folder("a_backup-2026-10-01")
        new = self.folder("a_backup-2026-11-10")
        with mock.patch.object(backups, "date", wraps=date) as d:
            d.today.return_value = date(2026, 10, 1)
            backups.record(old, "a")
            d.today.return_value = date(2026, 11, 10)
            backups.record(new, "a")
        self.assertEqual([e["path"] for e in backups.older_than(30, today=date(2026, 11, 16))], [old])

    def test_corrupt_file_is_empty_list(self):
        os.makedirs(os.path.dirname(backups.FILE))
        with open(backups.FILE, "w") as f:
            f.write("{not json")
        self.assertEqual(backups.listed(), [])

    @unittest.skipUnless(sys.platform == "win32", "Windows Recycle Bin")
    def test_real_recycle_bin(self):
        b = self.folder("r_backup-2026-11-01")
        REAL_RECYCLE(b)
        self.assertFalse(os.path.exists(b))

    def test_human(self):
        self.assertEqual(backups.human(512), "512 B")
        self.assertEqual(backups.human(1536 * 1024), "1.5 MB")


if __name__ == "__main__":
    unittest.main()
