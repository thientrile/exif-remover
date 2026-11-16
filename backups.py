"""Backup folders the app made: remembered in %APPDATA%\\ExifRemover\\backups.json, listed and sent to the
Recycle Bin. Only folders recorded here AND still named <folder>_backup-YYYY-MM-DD[-N] are ever deleted."""
import json
import os
import shutil
import sys
from datetime import date, timedelta

import exif_remover as er
import updater

FILE = os.path.join(os.path.dirname(updater.SETTINGS), "backups.json")


def _key(path):
    return os.path.normcase(os.path.normpath(path))


def _load():
    try:
        with open(FILE, encoding="utf-8") as f:
            data = json.load(f)
        return [e for e in data if isinstance(e, dict) and isinstance(e.get("path"), str)]
    except (OSError, ValueError, TypeError):
        return []


def _save(entries):
    try:
        os.makedirs(os.path.dirname(FILE), exist_ok=True)
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=1)
    except OSError:
        pass  # read-only profile: the list is just not remembered


def record(path, src):
    _save(_load() + [{"path": path, "src": src, "created": date.today().isoformat()}])


def deletable(path):
    """Our own naming pattern, an absolute path, a real folder (not a link)."""
    return (os.path.isabs(path) and bool(er.BACKUP_DIR.search(os.path.basename(os.path.normpath(path))))
            and os.path.isdir(path) and not os.path.islink(path))


def size(path):
    files = total = 0
    for top, _, names in os.walk(path):
        for n in names:
            files += 1
            try:
                total += os.path.getsize(os.path.join(top, n))
            except OSError:
                pass
    return files, total


def listed():
    """Recorded backups that still exist and match the pattern; drops the rest from the file."""
    keep, seen = [], set()
    for e in _load():
        if deletable(e["path"]) and _key(e["path"]) not in seen:
            seen.add(_key(e["path"]))
            keep.append(e)
    _save(keep)
    return [{**e, "src_exists": os.path.isdir(e.get("src") or "")} for e in keep]


def older_than(days, today=None):
    cut = ((today or date.today()) - timedelta(days=days)).isoformat()
    return [e for e in listed() if str(e.get("created", "")) < cut]


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def _recycle(path):
    """Windows Recycle Bin via SHFileOperationW + FOF_ALLOWUNDO, so the user can restore it."""
    import ctypes
    from ctypes import wintypes

    class Op(ctypes.Structure):
        _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT), ("pFrom", wintypes.LPCWSTR),
                    ("pTo", wintypes.LPCWSTR), ("fFlags", ctypes.c_ushort), ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR)]

    # FO_DELETE; FOF_ALLOWUNDO | FOF_NOCONFIRMATION (we asked already) | FOF_WANTNUKEWARNING (Windows asks
    # again if this drive has no Recycle Bin and the delete would be permanent)
    op = Op(None, 3, os.path.abspath(path) + "\0", None, 0x40 | 0x10 | 0x4000, False, None, None)
    rc = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    if rc or op.fAnyOperationsAborted:
        raise OSError(f"Windows không chuyển được vào Thùng rác (mã {rc:#x})")


def delete(paths):
    """Recycle (Windows) or remove the given backups, but only ones recorded and still matching.
    Returns (deleted, errors) where errors is a list of (path, message)."""
    known = {_key(e["path"]) for e in listed()}
    done, errors = [], []
    for p in paths:
        if _key(p) not in known or not deletable(p):
            errors.append((p, "không phải bản sao lưu do ứng dụng tạo"))
            continue
        try:
            _recycle(p) if sys.platform == "win32" else shutil.rmtree(p)
            done.append(p)
        except OSError as e:
            errors.append((p, str(e)))
    gone = {_key(p) for p in done}
    _save([e for e in _load() if _key(e["path"]) not in gone])
    return done, errors
