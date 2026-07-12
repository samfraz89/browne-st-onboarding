"""Exercise every route via the Flask test client (with login + staff records)."""
import sys, pathlib, re
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import app

c = app.app.test_client()

def show(label, resp):
    ok = resp.status_code in (200, 302)
    print(f"{'OK ' if ok else 'ERR'} {label:38} {resp.status_code}  {len(resp.data):,}b")
    if not ok:
        print("    ", resp.data[:300])
    return resp

# --- auth gate ---
show("GET / (no auth -> redirect)", c.get("/"))            # expect 302 -> /login
show("POST /login", c.post("/login", data={"password": "browne"}))

# --- public doc pages ---
for path in ["/", "/onboarding", "/contract", "/job-description",
             "/hr/informal-discussion", "/hr/investigation", "/hr/written-warning"]:
    show("GET " + path, c.get(path))

# --- staff CRUD ---
show("GET /staff", c.get("/staff"))
show("GET /staff/new", c.get("/staff/new"))
r = c.post("/staff/new", data={"full_name": "Jordan Smith", "role": "Barista",
           "emp_type": "part-time", "pay_rate": "28.00", "pronouns": "they",
           "address": "14 Main Street", "suburb": "Grey Lynn", "citypost": "Auckland 1021",
           "start_date": "2026-07-07", "status": "active"})
show("POST /staff/new", r)
sid = r.headers["Location"].rstrip("/").split("/")[-1]
print("   -> staff id:", sid)
show("GET /staff/<id> profile", c.get(f"/staff/{sid}"))

# --- generate a doc FOR the staff member (should file into their folder + redirect) ---
show("POST /generate-jd for staff", c.post("/generate-jd", data={"role": "Barista", "staff_id": sid}))
show("POST /generate-hr for staff", c.post("/generate-hr", data={
    "_key": "written-warning", "staff_id": sid, "employee": "Jordan Smith",
    "role": "Barista", "concern": "Lateness."}))
form = {"fullName": "Jordan Smith", "addr1": "14 Main Street", "suburb": "Grey Lynn",
        "citypost": "Auckland 1021", "pronouns": "they", "role": "Barista", "rate": "28.00",
        "startDate": "2026-07-07", "signDate": "2026-07-04", "empType": "part-time",
        "hMin": "20", "hMax": "30", "signature": "", "staff_id": sid}
show("POST /generate-contract for staff", c.post("/generate-contract", data=form))
show("POST /generate (pack) for staff", c.post("/generate", data=form))

# --- verify docs landed in the folder ---
docs = app.store.list_documents(sid)
print(f"   -> {len(docs)} documents filed:", [d["kind"] for d in docs])

# --- upload a file + add a certification ---
import io
show("POST /staff/<id>/upload", c.post(f"/staff/{sid}/upload",
     data={"file": (io.BytesIO(b"%PDF-1.4 fake"), "cert.pdf"), "kind": "certification"},
     content_type="multipart/form-data"))
show("POST /staff/<id>/cert", c.post(f"/staff/{sid}/cert",
     data={"name": "LCQ / Manager's Certificate", "expires": "2026-09-01"}))

# --- download the first filed doc ---
did = app.store.list_documents(sid)[0]["id"]
show("GET /staff/doc/<id> download", c.get(f"/staff/doc/{did}"))

# --- expiring certs ---
print("   -> expiring certs:", [(e["full_name"], e["days_left"]) for e in app.store.expiring_certifications(120)])

# --- doc generation without staff still works (ready page) ---
show("POST /generate-jd (no staff)", c.post("/generate-jd", data={"role": "Head Chef"}))

print("\nall routes exercised")
