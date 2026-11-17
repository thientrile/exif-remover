"""Write the PyInstaller --version-file (ExifRemover.exe Properties > Details) from exif_remover.__version__."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import exif_remover as er  # noqa: E402

v = tuple(int(x) for x in er.__version__.split(".")) + (0,)
strings = {"CompanyName": "Ánh sao & Bầu trời (thientrile)", "FileDescription": "Exif Remover",
           "FileVersion": er.__version__, "InternalName": "ExifRemover", "LegalCopyright": "© 2026 thientrile",
           "OriginalFilename": "ExifRemover.exe", "ProductName": "Exif Remover", "ProductVersion": er.__version__}
text = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={v}, prodvers={v}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0,
                    date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [{", ".join(f"StringStruct({k!r}, {s!r})" for k, s in strings.items())}])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
with open(sys.argv[1] if len(sys.argv) > 1 else "version_info.txt", "w", encoding="utf-8") as f:
    f.write(text)
