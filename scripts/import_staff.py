"""Bulk-import existing staff folders into the HR records store.

Drop one sub-folder per staff member into  _incoming/staff/  , where the folder
name is the person's name and it contains their files (PDFs, docs, scans, certs):

    _incoming/staff/
        Jordan Smith/
            Employment Agreement.pdf
            LCQ certificate.pdf
            Written warning 2025-06.pdf
        Aroha Ngata/
            Contract.pdf
            ...

Run:  ./.venv/bin/python scripts/import_staff.py            (preview — no changes)
      ./.venv/bin/python scripts/import_staff.py --commit   (actually import)

Each folder becomes a staff member; every file inside is filed into their record.
Document type is guessed from the filename; you can adjust roles/details in the UI
afterwards. Re-running skips staff who already exist (by name), so it's safe.
"""
import os, sys, argparse, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import store

_ap = argparse.ArgumentParser()
_ap.add_argument("src", nargs="?", default=str(pathlib.Path(__file__).resolve().parent.parent / "_incoming" / "staff"))
_ap.add_argument("--commit", action="store_true")
_ap.add_argument("--status", default="active", help="active | left (archived)")
_args = _ap.parse_args()
SRC = pathlib.Path(_args.src).expanduser()
COMMIT = _args.commit
STATUS = _args.status
# Folder names that are NOT staff members — skipped.
EXCLUDE = {"old staff", "other files", "job descriptions", "contract templates", "templates"}

# Map filename keywords -> document kind used by the app.
KIND_RULES = [
    (("agreement", "contract", "employment"), "contract"),
    (("onboarding", "pack"), "onboarding"),
    (("job description", "job-description", "jd", "position description"), "job-description"),
    (("written warning", "warning"), "written-warning"),
    (("investigation",), "investigation"),
    (("informal", "discussion", "coaching"), "informal-discussion"),
    (("lcq", "manager's cert", "managers cert", "certificate", "certification",
      "food", "first aid", "licence", "license", "cert"), "certification"),
]
DOC_EXTS = {".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg", ".heic", ".txt"}

def guess_kind(fname):
    low = fname.lower()
    for keys, kind in KIND_RULES:
        if any(k in low for k in keys):
            return kind
    return "other"

def main():
    store.init_db()
    if not SRC.exists():
        print(f"Intake folder not found: {SRC}")
        return
    existing = {s["full_name"].strip().lower() for s in store.list_staff()}
    folders = sorted([d for d in SRC.iterdir() if d.is_dir() and d.name.lower() not in EXCLUDE])
    if not folders:
        print(f"No staff folders in {SRC}. Add one folder per person and re-run.")
        return

    print(f"{'IMPORTING' if COMMIT else 'PREVIEW (no changes — pass --commit to import)'}  status={STATUS}\n")
    for folder in folders:
        name = folder.name.strip()
        files = [f for f in sorted(folder.iterdir()) if f.is_file() and f.suffix.lower() in DOC_EXTS
                 and not f.name.startswith(".")]
        if name.lower() in existing:
            print(f"• {name}: already exists — skipping ({len(files)} files not re-imported)")
            continue
        print(f"• {name}  ({len(files)} file{'s' if len(files)!=1 else ''})")
        for f in files:
            print(f"      {guess_kind(f.name):18} {f.name}")
        if COMMIT:
            sid = store.add_staff({"full_name": name, "status": STATUS})
            certs = 0
            for f in files:
                kind = guess_kind(f.name)
                store.save_file(sid, f.read_bytes(), f.name, kind=kind, title=f.stem, source="upload")
                if kind == "certification":
                    store.add_certification(sid, f.stem)  # add to cert list (no expiry — set in UI)
                    certs += 1
            print(f"      -> created, {len(files)} files filed, {certs} certifications")
    print("\nDone." + ("" if COMMIT else "  Re-run with --commit to import for real."))

if __name__ == "__main__":
    main()
