"""Windows only: run the GUI on demo files in C:\\demo\\photos and save PNGs of the metadata viewer and the
finished main window, the backups list, a "Chuyển sang JPG" run and the About dialog into the folder given as argument.
With a second folder argument it first sets the screen to 1920x1080, makes the main window 1400x820 and also saves,
for each shot, the main window area (with any dialog on top) there for the Microsoft Store (it needs >= 1366x768)."""
import ctypes
import ctypes.wintypes
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import exif_remover as er  # noqa: E402
import updater  # noqa: E402

if len(sys.argv) > 2:  # Store shots show the Store build (no update controls); set before the GUI module reads it
    updater.is_packaged = lambda: True
import exif_remover_gui as gui  # noqa: E402

DEMO = r"C:\demo\photos"
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
STORE = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else None
STORE_NAMES = {"screenshot.png": "1-main.png", "metadata.png": "2-metadata.png", "jpg.png": "3-jpg.png",
               "backups.png": "4-backups.png", "about.png": "5-about.png"}
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


class DEVMODEW(ctypes.Structure):
    _fields_ = [("dmDeviceName", ctypes.c_wchar * 32), ("dmSpecVersion", ctypes.c_ushort),
                ("dmDriverVersion", ctypes.c_ushort), ("dmSize", ctypes.c_ushort), ("dmDriverExtra", ctypes.c_ushort),
                ("dmFields", ctypes.c_ulong), ("dmPosition", ctypes.c_long * 2), ("dmDisplayOrientation", ctypes.c_ulong),
                ("dmDisplayFixedOutput", ctypes.c_ulong), ("dmColor", ctypes.c_short), ("dmDuplex", ctypes.c_short),
                ("dmYResolution", ctypes.c_short), ("dmTTOption", ctypes.c_short), ("dmCollate", ctypes.c_short),
                ("dmFormName", ctypes.c_wchar * 32), ("dmLogPixels", ctypes.c_ushort), ("dmBitsPerPel", ctypes.c_ulong),
                ("dmPelsWidth", ctypes.c_ulong), ("dmPelsHeight", ctypes.c_ulong), ("dmDisplayFlags", ctypes.c_ulong),
                ("dmDisplayFrequency", ctypes.c_ulong), ("dmICM", ctypes.c_ulong * 8)]


def set_screen(w, h):
    """Change the primary display mode (CI runners start at 1024x768); returns the resulting size."""
    dm = DEVMODEW()
    dm.dmSize = ctypes.sizeof(DEVMODEW)
    ctypes.windll.user32.EnumDisplaySettingsW(None, -1, ctypes.byref(dm))  # ENUM_CURRENT_SETTINGS
    dm.dmPelsWidth, dm.dmPelsHeight, dm.dmFields = w, h, 0x80000 | 0x100000  # DM_PELSWIDTH | DM_PELSHEIGHT
    rc = ctypes.windll.user32.ChangeDisplaySettingsW(ctypes.byref(dm), 0)
    size = ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1)
    print(f"ChangeDisplaySettings({w}x{h}) = {rc}; screen is now {size[0]}x{size[1]}")
    return size


def grab(left, top, w, h, out):
    ps = (f"Add-Type -AssemblyName System.Drawing; $b = New-Object System.Drawing.Bitmap {w}, {h}; "
          f"$g = [System.Drawing.Graphics]::FromImage($b); $g.CopyFromScreen({left}, {top}, 0, 0, $b.Size); $b.Save('{out}')")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    print("saved", out)


def frame(win):
    """Visible frame (left, top, width, height) without the invisible resize border/shadow GetWindowRect includes."""
    r = ctypes.wintypes.RECT()
    hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
    ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(r), ctypes.sizeof(r))
    return r.left, r.top, r.right - r.left, r.bottom - r.top


def capture(win, name):
    win.lift()
    win.attributes("-topmost", True)
    win.update()
    grab(*frame(win), os.path.join(OUT, name))
    if STORE:
        grab(*frame(app.root), os.path.join(STORE, STORE_NAMES[name]))


if __name__ == "__main__":
    make_demo()
    if STORE and any(got < need for got, need in zip(set_screen(1920, 1080), (1366, 768))):
        print("screen smaller than 1366x768: no Store screenshots")
        STORE = None
    app = gui.App([DEMO], demo=True)
    root = app.root
    if STORE:
        root.geometry("1400x820+0+0")

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
        app.on_finish = lambda: root.after(1200, lambda: (capture(root, "jpg.png"), root.after(300, about)))
        app.start("jpg")

    def about():
        win = app.show_about()
        root.after(1500, lambda: (capture(win, "about.png"), root.destroy()))

    root.after(3000, show_metadata)
    root.mainloop()
