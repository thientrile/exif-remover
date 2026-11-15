"""Write the release notes for TAG (its CHANGELOG.md section plus install hints) to OUT."""
import os
import re
import sys

tag, out = sys.argv[1], sys.argv[2]
text = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "CHANGELOG.md"), encoding="utf-8").read()
m = re.search(rf"^## {re.escape(tag)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
if not m:
    raise SystemExit(f"CHANGELOG.md has no section for {tag}")
with open(out, "w", encoding="utf-8") as f:
    f.write(m.group(1).strip() + f"""

Download ExifRemover-Setup-{tag[1:]}.exe and run it (installs for the current user, no admin).
The installer is not code-signed, so Windows SmartScreen may warn: click More info, then Run anyway.
Cleaning works offline; only the update check and the update download use the network.
""")
