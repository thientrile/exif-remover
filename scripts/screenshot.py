"""Windows only: run the GUI on demo files in C:\\demo\\photos and save PNGs of the metadata viewer and the
finished main window, the backups list and a "Chuyển sang JPG" run into the folder given as argument."""
import ctypes
import ctypes.wintypes
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import exif_remover as er  # noqa: E402
import exif_remover_gui as gui  # noqa: E402

DEMO = r"C:\demo\photos"
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
# Names cover the Vietnamese letters that break with a wrong font: ạ ả ấ ầ ẩ ẫ ậ ơ ư đ.
JPGS = ["Đà Lạt - hồ Xuân Hương.jpg", "bữa cơm gia đình.jpg", "cảnh ấm áp ở Huế.jpg", "quận 1 về đêm.jpg"]


def make_demo():
    os.makedirs(DEMO, exist_ok=True)
    gps = ["-q", "-overwrite_original", "-GPSLatitude=10.77", "-GPSLatitudeRef=N", "-GPSLongitude=106.70",
           "-GPSLongitudeRef=E", "-Make=Canon", "-Model=EOS R6", "-Artist=Demo", "-DateTimeOriginal=2026:01:01 08:00:00"]
    for name, color in zip(JPGS, ("skyblue", "orange", "gray", "navy")):
        f = os.path.join(DEMO, name)
        er.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"color={color}:s=640x480", "-frames:v", "1", "-y", f])
        er.run(["exiftool", *gps, f])
    png = os.path.join(DEMO, "nhãn cửa hàng Mẫu Tâm.png")
    er.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=green:s=64x64", "-frames:v", "1", "-y", png])
    er.run(["exiftool", "-q", "-overwrite_original", "-Software=Editor", "-Author=Demo", png])
    er.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=s=320x240", "-frames:v", "1", "-c:v", "libwebp", "-y",
            os.path.join(DEMO, "ảnh bìa sản phẩm.webp")])
    er.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=d=1:s=320x240", "-c:v", "mpeg4",
            "-metadata", "title=Holiday", "-metadata", "location=+10.77+106.70/", "-y",
            os.path.join(DEMO, "đầu năm - mẩu chuyện nhỏ.mp4")])


def capture(win, name):
    win.lift()
    win.attributes("-topmost", True)
    win.update()
    hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
    r = ctypes.wintypes.RECT()
    # Visible frame without the invisible resize border/shadow that GetWindowRect includes.
    ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(r), ctypes.sizeof(r))
    out = os.path.join(OUT, name)
    ps = (f"Add-Type -AssemblyName System.Drawing; $b = New-Object System.Drawing.Bitmap {r.right - r.left}, "
          f"{r.bottom - r.top}; $g = [System.Drawing.Graphics]::FromImage($b); "
          f"$g.CopyFromScreen({r.left}, {r.top}, 0, 0, $b.Size); $b.Save('{out}')")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    print("saved", out)


if __name__ == "__main__":
    make_demo()
    app = gui.App([DEMO], demo=True)
    root = app.root

    def show_metadata():
        first = app.tree.get_children()[0]
        app.tree.selection_set(first)
        win = app.view(app.rows[first][0])
        root.after(1500, lambda: (capture(win, "metadata.png"), win.destroy(), root.after(500, run)))

    def run():
        app.on_finish = lambda: root.after(1200, lambda: (app.tree.selection_set(()), capture(root, "screenshot.png"),
                                                          root.after(300, show_backups)))
        app.start()

    def show_backups():
        win = app.show_backups()
        root.after(1500, lambda: (capture(win, "backups.png"), win.destroy(), root.after(500, to_jpg)))

    def to_jpg():
        app.on_finish = lambda: root.after(1200, lambda: (capture(root, "jpg.png"), root.destroy()))
        app.start("jpg")

    root.after(3000, show_metadata)
    root.mainloop()
