import hashlib
import io
import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import updater as up  # noqa: E402

GOOD = "https://github.com/thientrile/exif-remover/releases/download/v9.9.9/"


class FakeResp(io.BytesIO):
    def __init__(self, data):
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data))}


class UpdaterTests(unittest.TestCase):
    def test_version_compare(self):
        self.assertEqual(up.parse_version("v0.2.10"), (0, 2, 10))
        self.assertTrue(up.is_newer("v0.2.10", "0.2.9"))
        self.assertTrue(up.is_newer("v1.0.0", "0.9.9"))
        self.assertFalse(up.is_newer("v0.2.0", "0.2.0"))
        self.assertFalse(up.is_newer("0.1.9", "0.2.0"))
        for bad in ("latest", "v1.2", "v1.2.3-beta", ""):
            with self.assertRaises(ValueError):
                up.parse_version(bad)

    def test_only_this_repo_and_github_hosts(self):
        up.check_url(GOOD + "x.exe")
        up.check_url("https://objects.githubusercontent.com/abc")
        up.check_url("https://github.com/thientrile/starveil/releases/download/v1/x.exe")  # future repo name
        for bad in ("http://github.com/thientrile/exif-remover/releases/download/v1/x.exe",
                    "https://github.com/evil/exif-remover/releases/download/v1/x.exe",
                    "https://github.com.evil.com/thientrile/exif-remover/releases/download/v1/x.exe",
                    "https://example.com/x.exe"):
            with self.assertRaises(ValueError):
                up.check_url(bad)

    def test_sha_for(self):
        h = "ab" * 32
        self.assertEqual(up.sha_for(f"{h.upper()}  ExifRemover-Setup-1.0.0.exe\n", "ExifRemover-Setup-1.0.0.exe"), h)
        with self.assertRaises(ValueError):
            up.sha_for(f"{h}  other.exe\n", "ExifRemover-Setup-1.0.0.exe")

    def download_with(self, payload, listed_hash):
        name = "ExifRemover-Setup-9.9.9.exe"
        info = {"tag": "v9.9.9", "installer": (name, GOOD + name), "sums": GOOD + "SHA256SUMS.txt"}
        responses = {GOOD + "SHA256SUMS.txt": f"{listed_hash}  {name}\n".encode(), GOOD + name: payload}
        with mock.patch.object(up, "_open", lambda url, timeout: FakeResp(responses[url])):
            return up.download(info)

    def test_download_verified(self):
        data = b"installer bytes"
        path = self.download_with(data, hashlib.sha256(data).hexdigest())
        with open(path, "rb") as f:
            self.assertEqual(f.read(), data)
        os.remove(path)

    def test_download_mismatch_refused_and_deleted(self):
        with mock.patch.object(up.tempfile, "mkdtemp", return_value=self.tmp):
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                self.download_with(b"tampered", "00" * 32)
        self.assertEqual(os.listdir(self.tmp), [])

    def setUp(self):
        import tempfile
        self._t = tempfile.TemporaryDirectory()
        self.tmp = self._t.name

    def tearDown(self):
        self._t.cleanup()

    def test_settings_roundtrip(self):
        with mock.patch.object(up, "SETTINGS", os.path.join(self.tmp, "a", "settings.json")):
            self.assertEqual(up.load_settings(), {"check_updates": True})
            up.save_settings({"check_updates": False})
            self.assertEqual(up.load_settings(), {"check_updates": False})


    def test_latest_picks_starveil_installer(self):
        base = GOOD.replace("v9.9.9", "v1.0.0")
        rel = {"tag_name": "v1.0.0", "body": "notes", "assets": [
            {"name": n, "browser_download_url": base + n}
            for n in ("ExifRemover-Setup-1.0.0.exe", "StarVeil-Setup-1.0.0.exe", "SHA256SUMS.txt")]}
        with mock.patch.object(up.urllib.request, "urlopen", lambda req, timeout: FakeResp(json.dumps(rel).encode())):
            info = up.latest()
        self.assertEqual(info["installer"], ("StarVeil-Setup-1.0.0.exe", base + "StarVeil-Setup-1.0.0.exe"))

    def test_packaged_build_never_updates(self):
        self.assertIs(up.is_packaged(), False)  # tests never run inside an MSIX package
        with mock.patch.object(up, "is_packaged", return_value=True), \
                mock.patch.object(up, "latest", side_effect=AssertionError("network used")):
            self.assertEqual(up.self_update(), 0)


if __name__ == "__main__":
    unittest.main()
