"""Render every job description into one PDF for visual review."""
import io, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, PageBreak

import app  # noqa: triggers font registration etc.
from job_descriptions import JOB_DESCRIPTIONS

buf = io.BytesIO()
doc = BaseDocTemplate(buf, pagesize=A4, leftMargin=22*mm, rightMargin=22*mm,
                      topMargin=32*mm, bottomMargin=20*mm)
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
doc.addPageTemplates([PageTemplate(id="main", frames=frame, onPage=app.on_page)])

story = []
for i, jd in enumerate(JOB_DESCRIPTIONS):
    if i:
        story.append(PageBreak())
    story += app.build_jd(jd["title"])

doc.build(story)
out = pathlib.Path(__file__).resolve().parent.parent / "_preview_job_descriptions.pdf"
out.write_bytes(buf.getvalue())
print(f"wrote {out} ({out.stat().st_size:,} bytes)")
