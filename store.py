# -*- coding: utf-8 -*-
"""Persistence layer for Browne St. HR — staff records, documents, certifications.

Deliberately simple and self-contained so the whole system hands over as one
folder: a SQLite database plus an uploaded-files directory, both under DATA_DIR.

  DATA_DIR (env)   where everything lives.
                   Prod: a Railway persistent volume, e.g. /data
                   Local: ./data (git-ignored)
    ├── hr.db          SQLite database (staff, documents, certifications)
    └── files/<staff>/ uploaded + generated PDFs for that staff member

Uses only the standard library (sqlite3) — no extra dependencies.
"""
import os, sqlite3, uuid, datetime, re

DATA_DIR  = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
FILES_DIR = os.path.join(DATA_DIR, "files")
DB_PATH   = os.path.join(DATA_DIR, "hr.db")


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _uid():
    return uuid.uuid4().hex[:12]

def _conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c

def init_db():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS staff (
            id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            preferred_name TEXT,
            role TEXT,
            emp_type TEXT,
            pay_rate TEXT,
            pronouns TEXT,
            email TEXT,
            phone TEXT,
            address TEXT,
            suburb TEXT,
            citypost TEXT,
            start_date TEXT,
            status TEXT DEFAULT 'active',
            notes TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            staff_id TEXT NOT NULL,
            kind TEXT,            -- onboarding|contract|job-description|written-warning|investigation|informal-discussion|certification|other
            title TEXT,
            filename TEXT,
            path TEXT,            -- relative to DATA_DIR
            source TEXT,          -- generated|upload
            created_at TEXT,
            FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS certifications (
            id TEXT PRIMARY KEY,
            staff_id TEXT NOT NULL,
            name TEXT,
            issued TEXT,
            expires TEXT,         -- YYYY-MM-DD (nullable)
            document_id TEXT,     -- optional linked file
            created_at TEXT,
            FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_docs_staff ON documents(staff_id);
        CREATE INDEX IF NOT EXISTS idx_certs_staff ON certifications(staff_id);
        """)

# --- staff -----------------------------------------------------------------
STAFF_FIELDS = ["full_name","preferred_name","role","emp_type","pay_rate","pronouns",
                "email","phone","address","suburb","citypost","start_date","status","notes"]

def add_staff(data):
    sid = _uid()
    vals = {k: (data.get(k) or "").strip() for k in STAFF_FIELDS}
    vals["status"] = vals["status"] or "active"
    with _conn() as c:
        cols = ["id"] + STAFF_FIELDS + ["created_at"]
        c.execute(f"INSERT INTO staff ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})",
                  [sid] + [vals[k] for k in STAFF_FIELDS] + [_now()])
    return sid

def update_staff(sid, data):
    vals = {k: (data.get(k) or "").strip() for k in STAFF_FIELDS if k in data}
    if not vals:
        return
    with _conn() as c:
        c.execute(f"UPDATE staff SET {','.join(k+'=?' for k in vals)} WHERE id=?",
                  list(vals.values()) + [sid])

def list_staff(include_left=True):
    with _conn() as c:
        q = "SELECT * FROM staff"
        if not include_left:
            q += " WHERE status != 'left'"
        q += " ORDER BY (status='left'), full_name COLLATE NOCASE"
        return [dict(r) for r in c.execute(q)]

def get_staff(sid):
    with _conn() as c:
        r = c.execute("SELECT * FROM staff WHERE id=?", (sid,)).fetchone()
        return dict(r) if r else None

def delete_staff(sid):
    with _conn() as c:
        c.execute("DELETE FROM staff WHERE id=?", (sid,))

# --- documents / files -----------------------------------------------------
def _safe_name(name):
    name = os.path.basename(name or "file")
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_") or "file"

def save_file(staff_id, pdf_bytes, filename, kind="other", title=None, source="generated"):
    """Write bytes into the staff member's folder and record the document."""
    folder = os.path.join(FILES_DIR, staff_id)
    os.makedirs(folder, exist_ok=True)
    did = _uid()
    stored = f"{did}_{_safe_name(filename)}"
    abspath = os.path.join(folder, stored)
    with open(abspath, "wb") as f:
        f.write(pdf_bytes)
    relpath = os.path.relpath(abspath, DATA_DIR)
    with _conn() as c:
        c.execute("INSERT INTO documents (id,staff_id,kind,title,filename,path,source,created_at) "
                  "VALUES (?,?,?,?,?,?,?,?)",
                  (did, staff_id, kind, title or filename, filename, relpath, source, _now()))
    return did

def list_documents(staff_id):
    with _conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM documents WHERE staff_id=? ORDER BY created_at DESC", (staff_id,))]

def get_document(did):
    with _conn() as c:
        r = c.execute("SELECT * FROM documents WHERE id=?", (did,)).fetchone()
        return dict(r) if r else None

def document_bytes(did):
    doc = get_document(did)
    if not doc:
        return None, None
    abspath = os.path.join(DATA_DIR, doc["path"])
    if not os.path.exists(abspath):
        return None, doc
    with open(abspath, "rb") as f:
        return f.read(), doc

def delete_document(did):
    doc = get_document(did)
    if doc:
        abspath = os.path.join(DATA_DIR, doc["path"])
        try:
            if os.path.exists(abspath):
                os.remove(abspath)
        except OSError:
            pass
    with _conn() as c:
        c.execute("DELETE FROM documents WHERE id=?", (did,))

# --- certifications --------------------------------------------------------
def add_certification(staff_id, name, issued="", expires="", document_id=None):
    cid = _uid()
    with _conn() as c:
        c.execute("INSERT INTO certifications (id,staff_id,name,issued,expires,document_id,created_at) "
                  "VALUES (?,?,?,?,?,?,?)",
                  (cid, staff_id, name.strip(), issued.strip(), expires.strip(), document_id, _now()))
    return cid

def list_certifications(staff_id):
    with _conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM certifications WHERE staff_id=? ORDER BY (expires=''), expires", (staff_id,))]

def delete_certification(cid):
    with _conn() as c:
        c.execute("DELETE FROM certifications WHERE id=?", (cid,))

def expiring_certifications(within_days=60):
    """Certs expiring within N days (or already expired), across all staff."""
    today = datetime.date.today()
    horizon = today + datetime.timedelta(days=within_days)
    out = []
    with _conn() as c:
        rows = c.execute("SELECT c.*, s.full_name FROM certifications c "
                         "JOIN staff s ON s.id=c.staff_id WHERE c.expires != ''")
        for r in rows:
            try:
                exp = datetime.datetime.strptime(r["expires"], "%Y-%m-%d").date()
            except ValueError:
                continue
            if exp <= horizon:
                d = dict(r); d["days_left"] = (exp - today).days
                out.append(d)
    out.sort(key=lambda d: d["days_left"])
    return out

def counts():
    with _conn() as c:
        s = c.execute("SELECT COUNT(*) FROM staff WHERE status!='left'").fetchone()[0]
        d = c.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    return {"staff": s, "documents": d}
