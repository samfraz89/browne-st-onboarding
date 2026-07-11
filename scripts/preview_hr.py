"""Render the three HR templates (blank + filled sample) into one PDF."""
import io, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, PageBreak

import app
from hr_documents import HR_DOCUMENTS

SAMPLES = {
    "informal-discussion": {
        "employee": "Jordan Smith", "role": "Barista", "manager": "Sam Fraser",
        "date": "30 June 2026", "location": "Browne St., Avondale",
        "matters": "Discussed punctuality over the last fortnight — Jordan has been 10–15 minutes late to three opening shifts, which delayed the coffee station being ready for service.",
        "expectations": "Arrive 10 minutes before rostered start so the station is set up by open. Let the duty manager know as early as possible if running late.",
        "support": "Offered to review the roster so Jordan's start aligns with public transport times.",
        "review": "Check in again on 14 July 2026.",
        "employee_comments": "Agreed the timing has slipped; will sort transport and be set up before open.",
    },
    "investigation": {
        "employee": "Jordan Smith", "role": "Barista", "manager": "Sam Fraser",
        "date": "30 June 2026", "time": "3:00pm", "location": "Office, Browne St.",
        "support_person": "Alex Lee (colleague)", "notetaker": "Sam Fraser",
        "concern": "A till discrepancy of $40 was recorded on the evening of 27 June 2026 during Jordan's shift.",
        "info": "Till reconciliation report for 27 June; EFTPOS settlement; roster confirming Jordan was on till.",
        "questions": "Q: Can you talk us through the close on the 27th?  A: ...\nQ: Were you the only person on the till?  A: ...",
        "response": "Jordan explained the float may not have been counted in at the start of the shift.",
    },
    "written-warning": {
        "employee": "Jordan Smith", "role": "Barista", "manager": "Sam Fraser",
        "date": "30 June 2026", "meeting_date": "28 June 2026",
        "support_person": "Alex Lee", "review_months": "6 months",
        "concern": "Repeated lateness to opening shifts despite an earlier informal discussion on 14 June 2026.",
        "background": "An informal management discussion was held on 14 June 2026 about the same issue.",
        "response": "Jordan acknowledged the lateness and explained ongoing transport difficulties.",
        "expectations": "Arrive and be ready for service by your rostered start time, every shift, effective immediately.",
    },
}

def render(story_parts):
    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4, leftMargin=22*mm, rightMargin=22*mm,
                          topMargin=32*mm, bottomMargin=20*mm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="main", frames=frame, onPage=app.on_page)])
    doc.build(story_parts)
    return buf.getvalue()

story = []
for variant, label in (("blank", {}), ("filled", None)):
    for d in HR_DOCUMENTS:
        if story:
            story.append(PageBreak())
        data = {} if variant == "blank" else SAMPLES[d["key"]]
        story += app.build_hr_doc(d["key"], data)

out = pathlib.Path(__file__).resolve().parent.parent / "_preview_hr_documents.pdf"
out.write_bytes(render(story))
print(f"wrote {out} ({out.stat().st_size:,} bytes)")
