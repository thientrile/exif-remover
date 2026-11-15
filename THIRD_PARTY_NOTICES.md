# Third-party notices

The MIT license in `LICENSE` covers only the Exif Remover code in this repository. The Windows
installer also ships these programs unmodified, as separate executables in `_internal\tools\`.
They are run as external processes; each keeps its own license. Versions and download URLs
(with SHA256) are pinned in `scripts/fetch_tools.py`.

## ExifTool 13.63

- Copyright (c) 2003-2026 Phil Harvey. https://exiftool.org/
- Free software; you can redistribute it and/or modify it under the same terms as Perl itself
  (the Artistic License or the GNU General Public License, version 1 or later).
- The Windows build includes a Strawberry Perl runtime; its license files are shipped in
  `_internal\tools\exiftool_files\` (`LICENSE`, `Licenses_Strawberry_Perl.zip`).
- Source: https://exiftool.org/ and https://github.com/exiftool/exiftool

## FFmpeg 8.1.3 (LGPL build)

- FFmpeg is a trademark of Fabrice Bellard. https://ffmpeg.org/
- Licensed under the GNU Lesser General Public License version 2.1 or later. This is an LGPL-only
  build (no GPL or nonfree components) made by the BtbN/FFmpeg-Builds project:
  `ffmpeg-n8.1.3-35-gf1acb0a266-win64-lgpl-8.1`. Full license text: `_internal\tools\licenses\ffmpeg-LICENSE.txt`.
- Corresponding source: FFmpeg commit `f1acb0a266` (https://github.com/FFmpeg/FFmpeg/commit/f1acb0a266),
  build scripts: https://github.com/BtbN/FFmpeg-Builds (release `autobuild-2026-11-14-12-37`).

## qpdf 12.4.2

- Copyright (c) 2005-2026 Jay Berkenbilt and contributors. https://qpdf.org/
- Licensed under the Apache License, Version 2.0: https://www.apache.org/licenses/LICENSE-2.0
  License text: `_internal\tools\licenses\qpdf-license.html`.
- The qpdf Windows build includes the Microsoft Visual C++ runtime DLLs, redistributed as permitted
  by Microsoft for applications that use them.
- Source: https://github.com/qpdf/qpdf/releases/tag/v12.4.2

## Python and PyInstaller

- The app is packaged with PyInstaller (GPL-2.0 with a bootloader exception that allows
  distributing packaged apps under any license) and includes the CPython runtime (PSF License)
  and Tcl/Tk (BSD-style license).
