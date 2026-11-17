import os
import sys
import unittest
import xml.dom.minidom

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import msix  # noqa: E402


class MsixTests(unittest.TestCase):
    def test_version_mapping(self):
        self.assertEqual(msix.msix_version("1.0.0"), "1.0.0.0")
        self.assertEqual(msix.msix_version("1.2.10"), "1.2.10.0")
        for bad in ("0.2.6", "1.0"):
            with self.assertRaises(ValueError):
                msix.msix_version(bad)

    def test_manifest_identity_from_env(self):
        env = {"MSIX_IDENTITY_NAME": "12345Owner.StarVeil", "MSIX_PUBLISHER": 'CN=ABCD-1234, O="A & B"'}
        dom = xml.dom.minidom.parseString(msix.manifest(env).encode())
        ident = dom.getElementsByTagName("Identity")[0]
        self.assertEqual(ident.getAttribute("Name"), "12345Owner.StarVeil")
        self.assertEqual(ident.getAttribute("Publisher"), 'CN=ABCD-1234, O="A & B"')
        self.assertEqual(dom.getElementsByTagName("PublisherDisplayName")[0].firstChild.data, "Ánh sao & Bầu trời")
        self.assertNotIn("{", msix.manifest(env).split("-->", 1)[1])  # every token filled


if __name__ == "__main__":
    unittest.main()
