"""Add a single document to a staff member's record (creating the person if new).

Used when adding existing staff files one at a time.

  ./.venv/bin/python scripts/add_doc.py "Aroha Ngata" "/path/to/Contract.pdf" \
        --kind contract --role "Barista" --rate 28.00 --start 2024-03-01 \
        --email aroha@example.com --phone 021234567 \
        --address "12 Rosebank Rd" --suburb "Avondale" --citypost "Auckland 1026" \
        --emp-type part-time

Only "name" and "file" are required. --kind is guessed from the filename if omitted.
Any staff detail flags provided update that person's record (blank = leave as-is).
If a certification, it's also added to their cert list (use --expires YYYY-MM-DD).
"""
import argparse, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import store

KIND_RULES = [
    (("agreement", "contract", "employment"), "contract"),
    (("onboarding", "pack"), "onboarding"),
    (("job description", "job-description", "jd", "position description"), "job-description"),
    (("written warning", "warning"), "written-warning"),
    (("investigation",), "investigation"),
    (("informal", "discussion", "coaching"), "informal-discussion"),
    (("lcq", "manager", "certificate", "certification", "food", "first aid",
      "licence", "license", "cert"), "certification"),
]

def guess_kind(fname):
    low = fname.lower()
    for keys, kind in KIND_RULES:
        if any(k in low for k in keys):
            return kind
    return "other"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("file")
    ap.add_argument("--kind")
    ap.add_argument("--title")
    ap.add_argument("--expires", default="")
    for f in ["role", "rate", "start", "email", "phone", "address", "suburb",
              "citypost", "pronouns", "emp-type", "status", "notes"]:
        ap.add_argument("--" + f)
    a = ap.parse_args()

    store.init_db()
    path = pathlib.Path(a.file).expanduser()
    if not path.exists():
        print(f"File not found: {path}"); return

    # find existing staff by name (case-insensitive) or create
    match = next((s for s in store.list_staff() if s["full_name"].strip().lower() == a.name.strip().lower()), None)
    detail_map = {"role": a.role, "pay_rate": a.rate, "start_date": a.start, "email": a.email,
                  "phone": a.phone, "address": a.address, "suburb": a.suburb, "citypost": a.citypost,
                  "pronouns": a.pronouns, "emp_type": getattr(a, "emp_type"), "status": a.status, "notes": a.notes}
    details = {k: v for k, v in detail_map.items() if v}

    if match:
        sid = match["id"]
        if details:
            store.update_staff(sid, details)
        print(f"↺ {a.name} (existing)")
    else:
        sid = store.add_staff({"full_name": a.name, **details})
        print(f"＋ {a.name} (new)")

    kind = a.kind or guess_kind(path.name)
    store.save_file(sid, path.read_bytes(), path.name, kind=kind,
                    title=a.title or path.stem, source="upload")
    print(f"   filed: {path.name}  [{kind}]")
    if kind == "certification":
        store.add_certification(sid, a.title or path.stem, expires=a.expires)
        print(f"   certification added" + (f" (expires {a.expires})" if a.expires else ""))
    if details:
        print(f"   updated details: {', '.join(details)}")

if __name__ == "__main__":
    main()
