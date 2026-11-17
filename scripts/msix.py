"""Lay out the Microsoft Store (MSIX) package from PyInstaller's dist\\StarVeil: copy the app, write
AppxManifest.xml (packaging/AppxManifest.xml with the {TOKENS} filled) and the logos made from assets/icon.png.
Usage: python scripts/msix.py <layout dir>. Pack it with makeappx afterwards (see .github/workflows/build.yml).
Identity comes from env MSIX_IDENTITY_NAME / MSIX_PUBLISHER / MSIX_PUBLISHER_DISPLAY_NAME (Partner Center >
Product identity); the defaults are placeholders that build and install for tests but are not Store-valid."""
import os
import shutil
import subprocess
import sys
from xml.sax.saxutils import escape

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
import exif_remover as er  # noqa: E402

PLACEHOLDER = {"IDENTITY_NAME": "thientrile.StarVeil", "PUBLISHER": "CN=StarVeil-Placeholder",
               "PUBLISHER_DISPLAY_NAME": "Ánh sao & Bầu trời"}
LOGOS = {"StoreLogo.png": 50, "Square44x44Logo.png": 44, "Square150x150Logo.png": 150, "StoreTile300.png": 300}


def msix_version(v):
    """'1.0.0' -> '1.0.0.0'. MSIX: first field must not be 0, the fourth is reserved for the Store (0)."""
    parts = [int(x) for x in v.split(".")]
    if len(parts) != 3 or parts[0] < 1:
        raise ValueError(f"MSIX needs a version 1.x.y or higher, got {v}")
    return ".".join(map(str, parts)) + ".0"


def manifest(env=os.environ):
    tokens = {k: env.get("MSIX_" + k) or default for k, default in PLACEHOLDER.items()}
    tokens.update(VERSION=msix_version(er.__version__), DISPLAY_NAME="Tinh Ảnh")
    text = open(os.path.join(ROOT, "packaging", "AppxManifest.xml"), encoding="utf-8").read()
    for k, v in tokens.items():
        text = text.replace("{" + k + "}", escape(v, {'"': "&quot;"}))
    return text


def main(out):
    shutil.copytree(os.path.join(ROOT, "dist", "StarVeil"), out)
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):  # the About dialog reads them next to the exe
        shutil.copy(os.path.join(ROOT, name), out)
    os.makedirs(os.path.join(out, "Assets"))
    ffmpeg = os.path.join(ROOT, "tools", "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
    for name, px in LOGOS.items():
        subprocess.run([ffmpeg if os.path.exists(ffmpeg) else "ffmpeg", "-v", "error", "-y", "-i",
                        os.path.join(ROOT, "assets", "icon.png"), "-vf", f"scale={px}:{px}:flags=lanczos",
                        os.path.join(out, "Assets", name)], check=True)
    with open(os.path.join(out, "AppxManifest.xml"), "w", encoding="utf-8") as f:
        f.write(manifest())
    print("MSIX layout ready:", out, msix_version(er.__version__))


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]))
