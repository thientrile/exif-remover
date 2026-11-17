"""Drives the real window (needs customtkinter, a display and the tools); skipped where those are missing."""
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
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
        p = mock.patch.object(gui.bk, "FILE", os.path.join(self.tmp.name, "cfg", "backups.json"))
        p.start()
        self.addCleanup(p.stop)
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

    def test_clean_run_backup_deletable_from_card_and_list(self):
        self.app.start()
        self.spin(lambda: not self.app.running)
        [backup] = [e["path"] for e in gui.bk.listed()]
        self.assertTrue(backup.startswith(os.path.realpath(self.d) + "_backup-"))  # realpath: Windows temp is an 8.3 short path
        self.assertEqual(self.app.card_del.cget("state"), "normal")
        win = self.app.show_backups()
        tree = [w for w in win.winfo_children() for w in w.winfo_children() if isinstance(w, gui.ttk.Treeview)][0]
        self.assertEqual(list(tree.get_children()), [backup])
        win.destroy()
        with mock.patch.object(gui.messagebox, "askyesno", return_value=False) as ask:
            self.app.card_del.invoke()
        self.assertIn("(5 tệp", ask.call_args[0][1])  # the whole folder is copied, incl. the old backup inside
        self.assertTrue(os.path.isdir(backup))  # said no: kept
        with mock.patch.object(gui.messagebox, "askyesno", return_value=True), \
                mock.patch.object(gui.bk, "_recycle", side_effect=shutil.rmtree):
            self.app.card_del.invoke()
        self.assertFalse(os.path.exists(backup))
        self.assertEqual(self.app.card_del.cget("state"), "disabled")
        self.assertEqual(gui.bk.listed(), [])

    def test_failed_run_keeps_backup_undeletable(self):
        with mock.patch.object(er, "clean_file", side_effect=RuntimeError("boom")):
            self.app.start()
            self.spin(lambda: not self.app.running)
        self.assertEqual(self.app.card_del.cget("state"), "disabled")

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

    def test_convert_to_jpg_makes_new_files_and_skips_jpegs(self):
        png = os.path.join(self.d, "p.png")
        er.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=blue:s=16x16", "-frames:v", "1", "-y", png])
        er.run(["exiftool", "-q", "-overwrite_original", "-XMP:Creator=Bob", png])
        self.app.add([png])
        before = {p: Path(p).read_bytes() for p, _ in self.app.rows.values()}
        self.app.backup.set(True)  # converting never backs up: originals are not touched
        self.app.jpg_btn.invoke()
        self.assertEqual(self.app.jpg_btn.cget("text"), "Dừng")
        self.assertEqual(self.app.run_btn.cget("state"), "disabled")
        self.spin(lambda: not self.app.running)
        status = self.col("status")
        self.assertEqual(status["p.png"], gui.CONVERTED)
        self.assertEqual({v for k, v in status.items() if k != "p.png"}, {gui.SKIPPED})  # JPEGs, one named .png
        self.assertEqual({p: Path(p).read_bytes() for p in before}, before)
        out = os.path.join(self.d, "p.jpg")
        self.assertEqual(er.file_type(er.read_tags(out)), "JPEG")
        self.assertEqual(er.leftovers(er.read_tags(out)), [])
        self.assertIn("1/5", self.app.card_title.cget("text"))
        self.assertIn("4 tệp bỏ qua", self.app.card_text.cget("text"))
        self.assertEqual(self.app.run_btn.cget("state"), "normal")
        self.assertEqual(gui.bk.listed(), [])
        self.assertFalse([n for n in os.listdir(self.tmp.name) if "_backup-" in n])

    def test_convert_stop_and_errors(self):
        real = er.convert_file
        calls = []

        def first_fails_then_stop(path):
            calls.append(path)
            self.app.stop.set()  # Stop pressed during the first file
            raise RuntimeError("bad pixels")

        with mock.patch.object(er, "convert_file", first_fails_then_stop):
            self.app.start("jpg")
            self.spin(lambda: not self.app.running)
        self.assertEqual(len(calls), 1)
        status = list(self.col("status").values())
        self.assertEqual((status.count(gui.ERR), status.count(gui.STOPPED)), (1, 3))
        self.assertIn("Đã dừng: đã chuyển 0/4", self.app.card_title.cget("text"))
        self.assertEqual(set(self.app.reasons.values()), {"bad pixels"})
        self.assertIs(er.convert_file, real)

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
        import ctypes.wintypes
        import threading
        u = ctypes.windll.user32
        u.FindWindowW.restype = ctypes.c_void_p
        start = os.path.join(self.tmp.name, "pick")  # holds only the two folders Ctrl+A will select
        for n in ("A", "B b"):
            os.makedirs(os.path.join(start, n))
        title = "Pick test"

        def child(parent, cls):  # first descendant window of a class
            found, buf = [], ctypes.create_unicode_buffer(64)

            def visit(h, _):
                u.GetClassNameW(ctypes.c_void_p(h), buf, 64)
                if buf.value == cls:
                    found.append(h)
                return not found

            u.EnumChildWindows(ctypes.c_void_p(parent),
                               ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(visit), None)
            return found[0] if found else None

        def key(vk, up=False):
            u.keybd_event(vk, 0, 2 if up else 0, 0)

        def drive():  # like a user: click the empty part of the folder list, Ctrl+A, then OK
            hwnd = None
            for _ in range(200):
                hwnd = u.FindWindowW(None, title)
                if hwnd:
                    break
                time.sleep(0.05)
            time.sleep(1.5)
            view = child(child(hwnd, "SHELLDLL_DefView"), "DirectUIHWND")
            r = ctypes.wintypes.RECT()
            u.GetWindowRect(ctypes.c_void_p(view), ctypes.byref(r))
            # the runner's own console window may sit on top with focus; a tap of Alt lets us take the foreground
            key(0x12), key(0x12, True)
            u.ShowWindow(ctypes.c_void_p(hwnd), 9)  # SW_RESTORE
            u.SetForegroundWindow(ctypes.c_void_p(hwnd))
            u.BringWindowToTop(ctypes.c_void_p(hwnd))
            time.sleep(0.3)
            u.SetCursorPos(r.right - 30, r.bottom - 30)
            u.mouse_event(2, 0, 0, 0, 0)
            u.mouse_event(4, 0, 0, 0, 0)
            time.sleep(0.5)
            key(0x11), key(0x41), key(0x41, True), key(0x11, True)  # Ctrl+A
            time.sleep(0.5)
            u.PostMessageW(ctypes.c_void_p(hwnd), 0x0111, 1, 0)  # WM_COMMAND IDOK = Select Folder

        threading.Thread(target=drive, daemon=True).start()
        got = gui.pick_folders_win(int(self.app.root.wm_frame(), 16), title, start=start)
        self.assertEqual(sorted(os.path.basename(p) for p in got), ["A", "B b"])


if __name__ == "__main__":
    unittest.main()
