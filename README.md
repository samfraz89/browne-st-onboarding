# Browne St. — HR & Onboarding

A self-contained HR document platform for Browne St. (Pulse 2012 Ltd). It
generates branded PDFs (employment agreements, job descriptions, warnings and
other HR records) and keeps a **folder per staff member** holding all of their
contracts, records, certifications and uploaded files.

Everything is one small Flask app plus a SQLite database — no external services
required beyond the host itself.

---

## What's inside

| Path | What it is |
|------|------------|
| `app.py` | The whole web app (routes, PDF rendering, staff records). |
| `store.py` | Data layer — SQLite + file storage for staff records. |
| `job_descriptions.py` | The 7 job descriptions (edit/add roles here). |
| `hr_documents.py` | The HR record templates (Informal Discussion, Investigation, Written Warning). |
| `templates/` | Source documents: the employment agreement, H&S guide, IR330 & KS10 govt forms. |
| `assets/` | Brand fonts (Inter), logos. |
| `scripts/smoke.py` | Runs every route end-to-end to check nothing is broken. |
| `_incoming/` | Drop-zone for new source files (JDs, contracts) to be wired in. |

**Documents available:** onboarding pack, standalone employment agreement,
job description (7 roles), Informal Management Discussion Record, Investigation
Meeting Record, Written Warning.

---

## Run it locally

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python app.py          # serves on http://localhost:8765
```

Default login password is `browne` (change via `HR_PASSWORD`, see below).
Local data is written to `./data/` (git-ignored).

Check everything works: `./.venv/bin/python scripts/smoke.py`

---

## Deploy on Railway

The app already runs on Railway (`Procfile` → gunicorn). Two things **must** be
configured for production:

### 1. Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `HR_PASSWORD` | **Yes** | The password to sign in. Set a strong value — this protects all staff data. |
| `SECRET_KEY` | **Yes** | Signs login sessions. Use a long random string (e.g. `python -c "import secrets;print(secrets.token_hex(32))"`). |
| `DATA_DIR` | **Yes** | Where records + files are stored. Set to your volume mount path, e.g. `/data`. |
| `RESEND_API_KEY` | Optional | If set, onboarding packs are emailed to sam@brownestreet.co.nz. |

The app prints a startup warning if `HR_PASSWORD` or `SECRET_KEY` are unset.

### 2. Persistent volume (critical)

Railway's normal filesystem is **wiped on every redeploy**. To keep staff records:

1. In the Railway service → **Settings → Volumes**, add a volume mounted at `/data`.
2. Set the `DATA_DIR` variable to that same path (`/data`).

Everything (the `hr.db` database and all uploaded/generated files) then lives on
the volume and survives restarts and redeploys.

### Backups / handoff

All data is under `DATA_DIR`:

```
$DATA_DIR/
├── hr.db            ← SQLite database (staff, documents, certifications)
└── files/<staff>/   ← every uploaded & generated PDF
```

To back up or hand the whole system over, copy that one folder. To restore,
put it back and point `DATA_DIR` at it.

---

## Extending it

- **Add a job description:** append an entry to `JOB_DESCRIPTIONS` in
  `job_descriptions.py`. It appears in the picker automatically.
- **Add / edit an HR record template:** edit `hr_documents.py`.
- **Add a new employment agreement template:** drop the `.docx` in
  `templates/contracts/` (wiring a picker is a small code change).

After any change, run `scripts/smoke.py` to confirm all routes still work.

---

## Notes

- HR/contract wording is standard NZ good-practice **but is not legal advice** —
  have it reviewed by an employment adviser.
- Brand: Inter typeface, orange `#FE5000`, cream `#F7F4EC`, ink `#16120D`
  (matches brownestreet.co.nz).
