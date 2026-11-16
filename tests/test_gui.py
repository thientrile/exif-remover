"""Drives the real window (needs customtkinter, a display and the tools); skipped where those are missing."""
import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import exif_remover as er  # noqa: E402

try:
    import exif_remover_gui as gui
    gui.ctk.CTk().destroy()
except Exception as e:  # no customtkinter/tkinter or no display
    gui = None
    why = str(e)


def jpg(path, **tags):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    real = os.path.join(os.path.dirname(path), ".tmp.jpg")
    er.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=red:s=16x16", "-frames:v", "1", "-y", real])
    er.run(["exiftool", "-q", "-overwrite_original", "-GPSLatitude=48.8", "-GPSLatitudeRef=N", real])
    os.replace(real, path)


@unittest.skipIf(gui is None, "GUI unavailable: " + ("" if gui else why))
class GuiTests(unittest.TestCase):
    def setUp(self):
        # the background tag counter may still hold a file open on Windows when a test ends
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.d = os.path.join(self.tmp.name, "photos")
        for name in ("a.jpg", "b.jpg", "c.jpg", "sub/jpeg named.png", "old_backup-2026-01-01/x.jpg"):
            jpg(os.path.join(self.d, name))
        self.app = gui.App([self.d], demo=True)

    def tearDown(self):
        try:
            self.app.root.destroy()
        except Exception:
            pass
        self.tmp.cleanup()

    def spin(self, until, timeout=60):
        end = time.time() + timeout
        while not until() and time.time() < end:
            self.app.root.update()
            time.sleep(0.02)
        self.assertTrue(until(), "timed out")

    def col(self, col):
        return {os.path.relpath(p, self.d): self.app.tree.set(iid, col) for iid, (p, _) in self.app.rows.items()}

    def test_list_skips_backups_shows_real_type_and_relative_names(self):
        self.assertEqual(sorted(self.col("name")), ["a.jpg", "b.jpg", "c.jpg", os.path.join("sub", "jpeg named.png")])
        self.assertEqual(sorted(self.col("name").values())[-1], os.path.join("sub", "jpeg named.png"))
        self.spin(lambda: "…" not in self.col("meta").values())
        self.assertEqual(self.col("kind")[os.path.join("sub", "jpeg named.png")], "JPEG (đuôi .png)")
        with mock.patch.object(gui.messagebox, "showwarning") as warn:
            self.app.add([os.path.join(self.d, "old_backup-2026-01-01")])
        warn.assert_called_once()
        self.assertEqual(len(self.app.rows), 4)

    def test_misnamed_jpeg_cleans(self):
        self.app.backup.set(False)
        self.app.start()
        self.spin(lambda: not self.app.running)
        self.assertEqual(set(self.col("status").values()), {gui.DONE})
        self.assertIn("4/4", self.app.card_title.cget("text"))

    def test_stop_finishes_current_file_then_stops(self):
        self.app.backup.set(False)
        real = er.clean_file

        def clean_then_press_stop(path):
            self.app.stop.set()  # Stop pressed while the first file is being cleaned
            return real(path)

        with mock.patch.object(er, "clean_file", clean_then_press_stop):
            self.app.start()
            self.spin(lambda: not self.app.running)
        status = list(self.col("status").values())
        self.assertEqual(status.count(gui.DONE), 1)
        self.assertEqual(status.count(gui.STOPPED), 3)
        self.assertIn("Đã dừng: đã xoá 1/4", self.app.card_title.cget("text"))
        self.assertEqual([n for n in os.listdir(self.d) if ".exifclean-" in n], [])

    def test_stop_during_backup_removes_it(self):
        self.app.stop.set()  # already stopping when the backup starts copying
        with mock.patch.object(self.app.stop, "clear"):
            self.app.start()
            self.spin(lambda: not self.app.running)
        self.assertEqual(set(self.col("status").values()), {gui.STOPPED})
        self.assertEqual(os.listdir(self.tmp.name), ["photos"])
        self.assertIn("Đã dừng: đã xoá 0/4", self.app.card_title.cget("text"))

    def test_failure_reason_kept_for_row(self):
        self.app.backup.set(False)
        with mock.patch.object(er, "clean_file", side_effect=RuntimeError("boom reason")):
            self.app.start()
            self.spin(lambda: not self.app.running)
        self.assertEqual(set(self.app.reasons.values()), {"boom reason"})
        self.assertIn("rê chuột", self.app.card_text.cget("text"))

    def test_close_during_run_asks_and_stops(self):
        self.app.backup.set(False)
        closed = []
        self.app.root.destroy = lambda: closed.append(True)
        with mock.patch.object(gui.messagebox, "askyesno", return_value=True) as ask:
            self.app.start()
            self.app.close()
            self.spin(lambda: closed)
        ask.assert_called_once()
        self.assertIn(gui.STOPPED, self.col("status").values())

    def test_several_folders_add_up_deduped(self):
        a, b, c = (os.path.join(self.tmp.name, n) for n in ("A", "B b", "C"))
        for d in (a, b, c):
            jpg(os.path.join(d, "x.jpg"))
        jpg(os.path.join(self.tmp.name, "old_backup-2026-01-01", "y.jpg"))
        base = len(self.app.rows)
        with mock.patch.object(gui, "pick_folders_win", side_effect=[[a, b], [b, c]]), \
                mock.patch.object(gui.filedialog, "askdirectory", side_effect=[a, c]):
            self.app.pick_folder()  # several at once (Windows dialog) or one (Tk dialog elsewhere)
            self.app.pick_folder()  # picking again adds to the list, repeats are skipped
        want = 3 if sys.platform == "win32" else 2
        self.assertEqual(len(self.app.rows), base + want)
        # dropping several folders from Explorer at once: one Tcl list, names with spaces in braces
        with mock.patch.object(gui.messagebox, "showwarning") as warn:
            self.app.drop("{%s} %s {%s}" % (b.replace("\\", "/"), c.replace("\\", "/"),
                                            os.path.join(self.tmp.name, "old_backup-2026-01-01").replace("\\", "/")))
        warn.assert_called_once()
        self.assertEqual(len(self.app.rows), base + 3)
        self.assertEqual(len({p for p, _ in self.app.rows.values()}), len(self.app.rows))

    @unittest.skipUnless(sys.platform == "win32", "Windows folder dialog")
    def test_windows_dialog_picks_several_folders(self):
        import ctypes
        import threading
        u = ctypes.windll.user32
        u.FindWindowW.restype = u.GetDlgItem.restype = u.FindWindowExW.restype = ctypes.c_void_p
        for n in ("A", "B b", "C"):
            os.makedirs(os.path.join(self.tmp.name, n))
        title = "Pick test"

        def drive():  # type two names into the dialog's file name box, then press OK
            for _ in range(200):
                hwnd = u.FindWindowW(None, title)
                if hwnd:
                    break
                time.sleep(0.05)
            time.sleep(0.5)
            combo = u.GetDlgItem(ctypes.c_void_p(hwnd), 1148)
            edit = u.FindWindowExW(ctypes.c_void_p(combo), None, "ComboBox", None)
            edit = u.FindWindowExW(ctypes.c_void_p(edit), None, "Edit", None) if edit else u.FindWindowExW(
                ctypes.c_void_p(combo), None, "Edit", None)
            u.SendMessageW(ctypes.c_void_p(edit), 0x000C, 0, ctypes.c_wchar_p('"A" "B b"'))  # WM_SETTEXT
            u.PostMessageW(ctypes.c_void_p(hwnd), 0x0111, 1, 0)  # WM_COMMAND IDOK

        threading.Thread(target=drive, daemon=True).start()
        got = gui.pick_folders_win(int(self.app.root.wm_frame(), 16), title, start=self.tmp.name)
        self.assertEqual(sorted(os.path.basename(p) for p in got), ["A", "B b"])


if __name__ == "__main__":
    unittest.main()
