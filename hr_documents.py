# -*- coding: utf-8 -*-
"""Browne St. HR document templates (data only — rendering lives in app.py).

Three records, drafted to NZ good-practice structure (Employment NZ guidance):

  1. informal-discussion  — Informal Management Discussion Record
  2. investigation        — Investigation Meeting Record
  3. written-warning      — Written Warning

These are TEMPLATES, not legal advice. They're designed to be either:
  - generated blank and filled in by hand during/after a meeting, or
  - pre-filled from a web form and printed/saved as a finished record.

Schema per document:
  key       stable id (used by routes/forms)
  title     display name
  kind      "record" (form-style, landscape header grid) or "letter" (addressed)
  intro     list of standard paragraphs shown under the title
  fields    header info captured in a grid (label/name/optional width)
  sections  body blocks. type:
              "long"  -> free-text area (entered value, else ruled blank space)
              "para"  -> fixed standard wording (not user-editable)
              "lines" -> a few blank ruled lines regardless of input
  signoff   signature blocks at the foot
  footer    small print at the very bottom

`{employee}` / `{manager}` etc. in para text are filled from field values.
"""

# Shared signature block builders ------------------------------------------
EMPLOYEE_ACK = {
    "label": "Employee",
    "note": "Signing acknowledges this discussion took place — it does not necessarily mean you agree with its content.",
    "rows": ["Name", "Signature", "Date"],
}
MANAGER_SIGN = {
    "label": "Manager / Supervisor",
    "note": "",
    "rows": ["Name", "Signature", "Date"],
}


HR_DOCUMENTS = [
    # ---------------------------------------------------------------- 1
    {
        "key": "informal-discussion",
        "title": "Informal Management Discussion Record",
        "kind": "record",
        "intro": [
            "This is a record of an informal management discussion. It is intended to support and coach the employee and to clearly set out expectations. It is <b>not</b> part of a formal disciplinary process, and no formal action results from this conversation.",
            "A copy may be kept on the employee's file for reference.",
        ],
        "fields": [
            {"name": "employee", "label": "Employee name"},
            {"name": "role", "label": "Role"},
            {"name": "manager", "label": "Manager / Supervisor"},
            {"name": "date", "label": "Date of discussion"},
            {"name": "location", "label": "Location"},
        ],
        "sections": [
            {"name": "matters", "label": "Matters discussed", "type": "long",
             "hint": "Summarise the conversation — the behaviour, performance or expectation discussed, and any relevant context."},
            {"name": "expectations", "label": "Expectations & agreed actions going forward", "type": "long",
             "hint": "What does good look like from here? Note any specific, reasonable and achievable actions agreed."},
            {"name": "support", "label": "Support offered", "type": "long",
             "hint": "Training, resources, mentoring or other support the business will provide."},
            {"name": "review", "label": "Follow-up / review date", "type": "lines", "lines": 1},
            {"name": "employee_comments", "label": "Employee comments", "type": "long",
             "hint": "Anything the employee would like recorded."},
        ],
        "signoff": [MANAGER_SIGN, EMPLOYEE_ACK],
        "footer": "Browne St. — Pulse 2012 Ltd · Informal record · Private & Confidential",
    },

    # ---------------------------------------------------------------- 2
    {
        "key": "investigation",
        "title": "Investigation Meeting Record",
        "kind": "record",
        "intro": [
            "This record documents an investigation meeting held to understand a concern and to give the employee a fair and reasonable opportunity to respond before any decision is made.",
            "No decision or outcome is reached at this meeting. The employer will fully consider the employee's response before deciding whether any further action is warranted.",
            "The employee has the right to seek advice and to be supported or represented at this meeting.",
        ],
        "fields": [
            {"name": "employee", "label": "Employee name"},
            {"name": "role", "label": "Role"},
            {"name": "manager", "label": "Meeting conducted by"},
            {"name": "date", "label": "Date"},
            {"name": "time", "label": "Time"},
            {"name": "location", "label": "Location"},
            {"name": "support_person", "label": "Support person / representative present", "width": "50%"},
            {"name": "notetaker", "label": "Note-taker", "width": "50%"},
        ],
        "sections": [
            {"name": "concern", "label": "Concern / matter being investigated", "type": "long",
             "hint": "Set out clearly and factually the concern being looked into, including dates and specifics where known."},
            {"name": "info", "label": "Information & evidence considered", "type": "long",
             "hint": "Documents, observations, statements or other information relevant to the concern."},
            {"name": "questions", "label": "Questions asked & employee's responses", "type": "long",
             "hint": "Record the key questions put to the employee and their answers as closely as possible.",
             "min_height": 34},
            {"name": "response", "label": "Employee's explanation / response", "type": "long",
             "hint": "The employee's account, in their own words where possible."},
            {"name": "next_steps", "label": "Next steps", "type": "para",
             "text": "The meeting was adjourned so that the employer can consider the information and the employee's response before deciding whether any further action is appropriate. The employee will be advised of the outcome and of any next steps in due course."},
            {"name": "employee_comments", "label": "Employee comments", "type": "long",
             "hint": "Anything the employee would like recorded, including whether they felt the process was fair."},
        ],
        "signoff": [MANAGER_SIGN, EMPLOYEE_ACK],
        "footer": "Browne St. — Pulse 2012 Ltd · Investigation record · Private & Confidential",
    },

    # ---------------------------------------------------------------- 3
    {
        "key": "written-warning",
        "title": "Written Warning",
        "kind": "letter",
        "intro": [],  # letter handles its own salutation/body
        "fields": [
            {"name": "employee", "label": "Employee name"},
            {"name": "role", "label": "Role"},
            {"name": "manager", "label": "Issued by"},
            {"name": "date", "label": "Date"},
            {"name": "meeting_date", "label": "Disciplinary meeting held on"},
            {"name": "support_person", "label": "Support person present"},
            {"name": "review_months", "label": "Warning active for"},
        ],
        # Letter body — labelled blocks. "para" = standard wording, "long" = entered detail.
        "sections": [
            {"name": "salutation", "type": "para",
             "text": "Dear {employee_first},"},
            {"name": "intro", "type": "para",
             "text": "This letter confirms the outcome of the disciplinary meeting held on {meeting_date} regarding a concern about your conduct / performance. Following that meeting, and having considered your response, the Company has decided to issue you with a <b>formal written warning</b>."},
            {"name": "concern", "label": "The concern", "type": "long",
             "hint": "Describe clearly the conduct or performance issue, including relevant dates, facts and the standard expected."},
            {"name": "background", "label": "Background & prior discussions", "type": "long",
             "hint": "Note any earlier conversations, coaching or warnings about the same or similar matter."},
            {"name": "response", "label": "Your response, as considered", "type": "long",
             "hint": "Summarise the explanation the employee gave and confirm it was considered."},
            {"name": "expectations", "label": "Required improvement", "type": "long",
             "hint": "Set out the specific, reasonable improvements or changes required, and by when."},
            {"name": "consequences", "type": "para",
             "text": "This written warning will remain active on your file for <b>{review_months}</b>. If there is no sufficient improvement, or if further concerns of a similar nature arise during this period, this may lead to further disciplinary action, which could include further warnings or, ultimately, the termination of your employment."},
            {"name": "support", "type": "para",
             "text": "We want to support you to meet the required standard. Please speak with your manager if there is any training, resource or support that would help."},
            {"name": "rights", "type": "para",
             "text": "You are entitled to seek independent advice about this matter. If you believe this warning is unjustified, you may raise that with the Company, and you retain your right to pursue a personal grievance under the Employment Relations Act 2000."},
            {"name": "closing", "type": "para",
             "text": "Yours sincerely,"},
        ],
        "signoff": [MANAGER_SIGN, {
            "label": "Acknowledgement of receipt",
            "note": "Signing confirms you have received this written warning. It does not mean you agree with it.",
            "rows": ["Name", "Signature", "Date"],
        }],
        "footer": "Browne St. — Pulse 2012 Ltd · 50 Rosebank Rd, Avondale, Auckland 1026 · Private & Confidential",
    },
]

HR_BY_KEY = {d["key"]: d for d in HR_DOCUMENTS}
