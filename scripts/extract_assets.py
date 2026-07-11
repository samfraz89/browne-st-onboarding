"""One-off: extract the base64-embedded assets in app.py to real files on disk.

These are currently inlined as huge constants in app.py. Pulling them out lets us
read/edit them as normal files and move toward a file-based template system.
"""
import base64, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = (ROOT / "app.py").read_text()

# name -> output path (relative to repo root)
TARGETS = {
    "FONT_REGULAR_B64": "assets/fonts/Poppins-Regular.ttf",
    "FONT_BOLD_B64":    "assets/fonts/Poppins-Bold.ttf",
    "FONT_ITALIC_B64":  "assets/fonts/Poppins-Italic.ttf",
    "FONT_MEDIUM_B64":  "assets/fonts/Poppins-Medium.ttf",
    "FONT_LIGHT_B64":   "assets/fonts/Poppins-Light.ttf",
    "TEMPLATE_B64":     "templates/contracts/employment-agreement-default.docx",
    "HS_DOCX_B64":      "templates/health-safety/health-safety-guide.docx",
    "IR330_PDF_B64":    "templates/govt-forms/IR330.pdf",
    "KS10_PDF_B64":     "templates/govt-forms/KS10.pdf",
    "LOGO_B64":         "assets/logo.png",
}

for name, out in TARGETS.items():
    m = re.search(rf'^{name}\s*=\s*"([A-Za-z0-9+/=]+)"', SRC, re.MULTILINE)
    if not m:
        print(f"!! {name}: not found")
        continue
    data = base64.b64decode(m.group(1))
    dest = ROOT / out
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    print(f"ok {name:18} -> {out} ({len(data):,} bytes)")
