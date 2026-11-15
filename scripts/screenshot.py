"""Windows only: run the GUI on demo files in C:\\demo\\photos and save a PNG of the finished window."""
import ctypes
import ctypes.wintypes
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import exif_remover as er  # noqa: E402
import exif_remover_gui as gui  # noqa: E402

DEMO = r"C:\demo\photos"
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "screenshot.png")


def make_demo():
    os.makedirs(DEMO, exist_ok=True)
    gps = ["-q", "-overwrite_original", "-GPSLatitude=10.77", "-GPSLatitudeRef=N", "-GPSLongitude=106.70",
           "-GPSLongitudeRef=E", "-Make=Canon", "-Model=EOS R6", "-Artist=Demo"]
    for name, color in (("beach.jpg", "skyblue"), ("family.jpg", "orange"), ("street.jpg", "gray")):
        f = os.path.join(DEMO, name)
        er.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"color={color}:s=640x480", "-frames:v", "1", "-y", f])
        er.run(["exiftool", *gps, f])
    png = os.path.join(DEMO, "logo.png")
    er.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=green:s=64x64", "-frames:v", "1", "-y", png])
    er.run(["exiftool", "-q", "-overwrite_original", "-Software=Editor", "-Author=Demo", png])
    er.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=d=1:s=320x240", "-c:v", "mpeg4",
            "-metadata", "title=Holiday", "-metadata", "location=+10.77+106.70/", "-y", os.path.join(DEMO, "clip.mp4")])


def capture(root):
    root.lift()
    root.attributes("-topmost", True)
    root.update()
    hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
    r = ctypes.wintypes.RECT()
    # Visible frame without the invisible resize border/shadow that GetWindowRect includes.
    ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(r), ctypes.sizeof(r))
    ps = (f"Add-Type -AssemblyName System.Drawing; $b = New-Object System.Drawing.Bitmap {r.right - r.left}, "
          f"{r.bottom - r.top}; $g = [System.Drawing.Graphics]::FromImage($b); "
          f"$g.CopyFromScreen({r.left}, {r.top}, 0, 0, $b.Size); $b.Save('{OUT}')")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    print("saved", OUT)
    root.destroy()


if __name__ == "__main__":
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # real pixel coordinates for CopyFromScreen
    make_demo()
    gui.app([DEMO], on_done=lambda root: root.after(800, capture, root))
