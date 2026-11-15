"""Self-update from GitHub Releases: check, download the installer, verify SHA256, run it silently.

Only this module touches the network, and it only sends a GET for the release info and the
installer; no user file or personal data is ever sent.
"""
import hashlib
import json
import os
import re
import subprocess
import tempfile
import urllib.parse
import urllib.request

from exif_remover import __version__

REPO = "thientrile/exif-remover"
API = f"https://api.github.com/repos/{REPO}/releases/latest"
UA = {"User-Agent": f"ExifRemover/{__version__}"}
ASSET_PATH = f"/{REPO}/releases/download/"
# Release assets redirect from github.com to GitHub's asset CDN; anything else is refused.
HOSTS = {"github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"}
SETTINGS = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~/.config"), "ExifRemover", "settings.json")


def parse_version(v):
    """'v0.2.10' -> (0, 2, 10); raises ValueError on anything else."""
    m = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", v.strip())
    if not m:
        raise ValueError(f"bad version: {v!r}")
    return tuple(int(x) for x in m.groups())


def is_newer(tag, current=__version__):
    return parse_version(tag) > parse_version(current)


def check_url(url):
    u = urllib.parse.urlsplit(url)
    if u.scheme != "https" or u.hostname not in HOSTS:
        raise ValueError(f"refusing download from {url}")
    if u.hostname == "github.com" and not u.path.startswith(ASSET_PATH):
        raise ValueError(f"not an asset of {REPO}: {url}")
    return url


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, check_url(newurl))


def _open(url, timeout):
    opener = urllib.request.build_opener(SafeRedirect)
    return opener.open(urllib.request.Request(url, headers=UA), timeout=timeout)


def latest(timeout=8):
    """Release info: {'tag', 'notes', 'installer': (name, url), 'sums': url}; raises on any problem."""
    with urllib.request.urlopen(urllib.request.Request(API, headers=UA), timeout=timeout) as r:
        rel = json.load(r)
    tag = rel["tag_name"]
    parse_version(tag)
    name = f"ExifRemover-Setup-{tag.lstrip('v')}.exe"
    urls = {a["name"]: a["browser_download_url"] for a in rel.get("assets", [])}
    if name not in urls or "SHA256SUMS.txt" not in urls:
        raise ValueError(f"release {tag} lacks {name} or SHA256SUMS.txt")
    return {"tag": tag, "notes": (rel.get("body") or "").strip(),
            "installer": (name, check_url(urls[name])), "sums": check_url(urls["SHA256SUMS.txt"])}


def sha_for(sums_text, name):
    """Hash for `name` from a sha256sum-style file ('<hex>  <name>' per line)."""
    for line in sums_text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == name and re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]):
            return parts[0].lower()
    raise ValueError(f"{name} not listed in SHA256SUMS.txt")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def download(info, progress=lambda pct: None, timeout=30):
    """Download and verify the installer; returns its path. Raises (and deletes it) on any mismatch."""
    name, url = info["installer"]
    with _open(info["sums"], timeout) as r:
        want = sha_for(r.read(65536).decode("utf-8", "replace"), name)
    path = os.path.join(tempfile.mkdtemp(prefix="exifremover-update-"), name)
    try:
        with _open(url, timeout) as r, open(path, "wb") as f:
            total, done = int(r.headers.get("Content-Length") or 0), 0
            for block in iter(lambda: r.read(1 << 16), b""):
                f.write(block)
                done += len(block)
                if total:
                    progress(done * 100 // total)
        got = sha256_file(path)
        if got != want:
            raise ValueError(f"SHA256 mismatch: got {got}, expected {want}")
    except BaseException:
        os.remove(path)
        raise
    return path


def run_installer(path, relaunch=True):
    """Start the per-user installer silently, detached; the caller must exit right after."""
    args = [path, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"]
    if relaunch:
        args.append("/RELAUNCH")  # installer.iss starts the app again when it sees this
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    return subprocess.Popen(args, creationflags=flags, close_fds=True)


def self_update():
    """CLI `--self-update`: install the latest release if newer, no window. Exit code 0 = started or up to date."""
    info = latest()
    if not is_newer(info["tag"]):
        return 0
    run_installer(download(info), relaunch=False)  # not waited on: the installer closes this exe
    return 0


def load_settings():
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            return {"check_updates": True, **json.load(f)}
    except (OSError, ValueError):
        return {"check_updates": True}


def save_settings(settings):
    try:
        os.makedirs(os.path.dirname(SETTINGS), exist_ok=True)
        with open(SETTINGS, "w", encoding="utf-8") as f:
            json.dump(settings, f)
    except OSError:
        pass  # a read-only profile just means the choice is not remembered
