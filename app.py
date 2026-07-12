import base64, zipfile, io, re, os, tempfile
from datetime import datetime
from flask import Flask, request, send_file, render_template_string
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.platypus import Paragraph, Spacer, PageBreak, HRFlowable, Image, Table, TableStyle
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from pypdf import PdfWriter, PdfReader
from flask import session, redirect, url_for, abort
import store

app = Flask(__name__)
# Session secret: set SECRET_KEY in production. Fall back to a random per-boot
# key (works, but logs everyone out on restart) rather than a shared hardcoded one.
import secrets as _secrets
app.secret_key = os.environ.get("SECRET_KEY") or _secrets.token_hex(32)
store.init_db()

# Shared-password gate. Set HR_PASSWORD in the environment in production.
HR_PASSWORD = os.environ.get("HR_PASSWORD", "browne")
if not os.environ.get("SECRET_KEY"):
    print("WARNING: SECRET_KEY not set — using a random key (sessions reset on restart). Set it in production.")
if HR_PASSWORD == "browne":
    print("WARNING: HR_PASSWORD is the default 'browne'. Set HR_PASSWORD in production to protect staff data.")
_PUBLIC_PREFIXES = ("/login", "/brand", "/static", "/logo")

@app.before_request
def _require_login():
    if request.path == "/login" or any(request.path.startswith(p) for p in _PUBLIC_PREFIXES):
        return None
    if not session.get("auth"):
        return redirect(url_for("login", next=request.path))



# Register Inter (the Browne St. brand typeface) from assets/fonts/.
import os as _os
_FONT_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "assets", "fonts")
def _reg(name, filename):
    pdfmetrics.registerFont(TTFont(name, _os.path.join(_FONT_DIR, filename)))
_reg("Inter",          "Inter-Regular.ttf")
_reg("Inter-Bold",     "Inter-Bold.ttf")
_reg("Inter-Medium",   "Inter-Medium.ttf")
_reg("Inter-Light",    "Inter-Light.ttf")
_reg("Inter-Italic",   "Inter-Italic.ttf")
_reg("Inter-SemiBold", "Inter-SemiBold.ttf")
registerFontFamily("Inter", normal="Inter", bold="Inter-Bold", italic="Inter-Italic", boldItalic="Inter-Bold")

# Browne St. brand palette (from brownestreet.co.nz)
ORANGE = HexColor("#FE5000"); BLACK = HexColor("#16120D"); GREY = HexColor("#8C7F6B")
LGREY = HexColor("#F7F4EC"); MGREY = HexColor("#E3D9C8"); DGREY = HexColor("#3B342A")
GREEN = HexColor("#1A7A30"); RED = HexColor("#A11C1C")


_ROOT = _os.path.dirname(_os.path.abspath(__file__))
TEMPLATE_BYTES  = open(_os.path.join(_ROOT, "templates/contracts/employment-agreement-default.docx"), "rb").read()
HS_DOCX_BYTES   = open(_os.path.join(_ROOT, "templates/health-safety/health-safety-guide.docx"), "rb").read()
IR330_PDF_BYTES = open(_os.path.join(_ROOT, "templates/govt-forms/IR330.pdf"), "rb").read()
KS10_PDF_BYTES  = open(_os.path.join(_ROOT, "templates/govt-forms/KS10.pdf"), "rb").read()
LOGO_PATH       = _os.path.join(_ROOT, "assets", "logo.png")

HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Browne St. Onboarding</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{--bg:#F3EFE6;--surface:#FFFFFF;--surface-2:#FBF8F2;--ink:#16120D;--ink-soft:#3B342A;--muted:#8C7F6B;--faint:#ADA189;--line:#EBE3D5;--line-2:#E1D7C6;--orange:#FE5000;--orange-ink:#C43C00;--orange-tint:#FFF2EB;--orange-soft:#FFDECE;--radius:18px;--radius-sm:11px;--shadow:0 1px 2px rgba(22,18,13,.04),0 18px 40px -22px rgba(22,18,13,.18);--ease:180ms cubic-bezier(.2,.65,.2,1)}
*{box-sizing:border-box;margin:0;padding:0}
html{-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--ink);line-height:1.5;min-height:100vh;padding:44px 18px 60px;background:radial-gradient(1100px 460px at 50% -8%,#FCF9F2,rgba(252,249,242,0) 62%),var(--bg)}
.card{position:relative;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);max-width:600px;margin:0 auto;padding:34px 34px 30px;overflow:hidden}
.card::before{content:"";position:absolute;inset:0 0 auto 0;height:3px;background:linear-gradient(90deg,var(--orange),#FF7A3D)}
.top-bar{display:none}
.brand{font-size:10.5px;font-weight:600;letter-spacing:.16em;color:var(--faint);text-transform:uppercase;margin-bottom:13px}
h1{font-size:25px;font-weight:700;letter-spacing:-.021em;color:var(--ink);line-height:1.12;margin-bottom:6px}
.sub{font-size:13.5px;color:var(--muted);margin-bottom:22px;line-height:1.55;max-width:48ch}
.lbl{font-size:10.5px;font-weight:600;letter-spacing:.14em;color:var(--faint);text-transform:uppercase;margin:24px 0 12px}
.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.f{margin-bottom:13px}
.f label{display:block;font-size:12.5px;color:var(--ink-soft);margin-bottom:6px;font-weight:550}
.f input,.f select{width:100%;height:46px;padding:0 13px;border:1px solid var(--line-2);border-radius:var(--radius-sm);background:var(--surface-2);color:var(--ink);font-size:15px;font-family:inherit;transition:border var(--ease),box-shadow var(--ease),background var(--ease)}
.f input::placeholder{color:var(--faint)}
.f input:focus,.f select:focus{outline:none;border-color:var(--orange);background:#fff;box-shadow:0 0 0 4px var(--orange-tint)}
hr{border:none;border-top:1px solid var(--line);margin:22px 0}
.back{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:var(--muted);text-decoration:none;margin-bottom:16px}
.back:hover{color:var(--orange)}
.types{display:grid;grid-template-columns:repeat(3,1fr);gap:9px}
.tb{padding:13px 8px;border:1px solid var(--line-2);border-radius:var(--radius-sm);background:var(--surface-2);color:var(--ink-soft);font-size:13.5px;font-family:inherit;cursor:pointer;text-align:center;font-weight:550;transition:all var(--ease)}
.tb:hover{border-color:var(--orange-soft)}
.tb.on{border-color:var(--orange);color:var(--orange-ink);background:var(--orange-tint);box-shadow:0 0 0 3px var(--orange-tint)}
.hrs{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}
.hint{font-size:12px;color:var(--faint);margin-top:7px}
.btn{width:100%;height:52px;background:var(--orange);color:#fff;border:none;border-radius:12px;font-size:15px;font-weight:600;letter-spacing:.01em;font-family:inherit;cursor:pointer;margin-top:24px;box-shadow:0 12px 26px -12px rgba(254,80,0,.55);transition:transform var(--ease),background var(--ease),box-shadow var(--ease)}
.btn:hover{background:var(--orange-ink);transform:translateY(-1px)}
.btn:active{transform:translateY(0)}
.pack-info{margin-top:22px;padding:14px 16px;border-radius:13px;font-size:12.5px;background:var(--orange-tint);color:var(--orange-ink);line-height:1.85;border:1px solid var(--orange-soft)}
.note{margin-top:22px;padding:13px 16px;border-radius:12px;font-size:12.5px;background:var(--orange-tint);color:var(--orange-ink);line-height:1.6;border:1px solid var(--orange-soft)}
.note.filing{display:flex;align-items:center;gap:14px;justify-content:space-between}
.note .ntx{flex:1;min-width:0}
.note .ntx-cancel{flex-shrink:0;white-space:nowrap;font-weight:600;color:var(--orange-ink);text-decoration:underline;text-underline-offset:2px}
.msg{margin-top:16px;padding:12px 14px;border-radius:11px;font-size:13px}
.err{background:#FCEBE7;color:#9a2b1a;border:1px solid #F1C6BB}
@media(max-width:520px){.card{padding:26px 20px}.row,.hrs,.types{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="card">
  <div class="top-bar"></div>
  <div class="brand">Browne St. &mdash; Pulse 2012 Ltd</div>
  <a class="back" href="/">&#8592;&nbsp; All documents</a>
  <h1>{{ page_title }}</h1>
  <p class="sub">{{ page_sub }}</p>
  <form method="POST" action="{{ action }}">
    {{ staff_control|safe }}
    <div class="lbl">Employee details</div>
    <div class="f"><label>Full name</label><input name="fullName" placeholder="e.g. Jordan Smith" value="{{ pf.fullName }}" required></div>
    <div class="f"><label>Street address</label><input name="addr1" placeholder="e.g. 14 Main Street" value="{{ pf.addr1 }}" required></div>
    <div class="row">
      <div class="f"><label>Suburb</label><input name="suburb" placeholder="e.g. Grey Lynn" value="{{ pf.suburb }}" required></div>
      <div class="f"><label>City &amp; postcode</label><input name="citypost" placeholder="e.g. Auckland 1021" value="{{ pf.citypost }}" required></div>
    </div>
    <div class="f"><label>Pronouns</label>
      <select name="pronouns">
        <option value="they"{% if pf.pronouns=='they' %} selected{% endif %}>They / them</option>
        <option value="she"{% if pf.pronouns=='she' or not pf.pronouns %} selected{% endif %}>She / her</option>
        <option value="he"{% if pf.pronouns=='he' %} selected{% endif %}>He / him</option>
      </select>
    </div>
    <hr>
    <div class="lbl">Role &amp; pay</div>
    <div class="row">
      <div class="f"><label>Job title / role</label><input name="role" placeholder="e.g. Front of House" value="{{ pf.role }}" required></div>
      <div class="f"><label>Hourly rate ($NZD)</label><input name="rate" type="number" step="any" min="0" placeholder="e.g. 28.00" value="{{ pf.rate }}" required></div>
    </div>
    <div class="row">
      <div class="f"><label>Start date</label><input name="startDate" type="date" required></div>
      <div class="f"><label>Sign-by date</label><input name="signDate" type="date"></div>
    </div>
    <hr>
    <div class="lbl">Employment type</div>
    <div class="types">
      <button type="button" class="tb on" onclick="setType(this,\'part-time\')">Part-time</button>
      <button type="button" class="tb" onclick="setType(this,\'full-time\')">Full-time</button>
      <button type="button" class="tb" onclick="setType(this,\'casual\')">Casual</button>
    </div>
    <input type="hidden" name="empType" id="empType" value="part-time">
    <div id="hrsWrap" class="hrs">
      <div class="f"><label>Min hrs / week</label><input name="hMin" id="hMin" type="number" placeholder="e.g. 20" min="1" max="60"></div>
      <div class="f"><label>Max hrs / week</label><input name="hMax" id="hMax" type="number" placeholder="e.g. 30" min="1" max="60"></div>
    </div>
    <div class="hint" id="hint">Guaranteed minimum hours for the roster</div>
    <hr>
    <div class="lbl">Employer signature</div>
    <p style="font-size:13px;color:#8C7F6B;margin-bottom:10px;line-height:1.5">Draw your signature below. This will be added to the agreement as Sam Fraser, Director.</p>
    <canvas id="sigCanvas" width="556" height="140" style="border:1px solid #E3D9C8;border-radius:8px;background:#fff;touch-action:none;width:100%;cursor:crosshair;display:block"></canvas>
    <div style="display:flex;gap:8px;margin-top:8px">
      <button type="button" onclick="clearSig()" style="padding:8px 16px;border:1px solid #E3D9C8;border-radius:7px;background:#fff;font-family:inherit;font-size:13px;cursor:pointer;color:#5F574A">Clear</button>
      <span id="sigStatus" style="font-size:12px;color:#B8AD97;align-self:center;margin-left:4px">Sign above with your finger or mouse</span>
    </div>
    <input type="hidden" name="signature" id="sigData">
    <button class="btn" type="submit" onclick="return captureSig()">{{ submit_label }}</button>
  </form>
  {% if show_pack %}<div class="pack-info">
    <strong>Pack includes:</strong><br>
    1. Employment agreement + job description (personalised)<br>
    2. Health &amp; Safety guide + Do\'s &amp; Don\'ts<br>
    3. IR330 &mdash; Tax code declaration<br>
    4. KS10 &mdash; KiwiSaver opt-out form<br><br>
    <strong>After generating:</strong> PDF downloads automatically + a copy is emailed to sam@brownestreet.co.nz
  </div>{% endif %}
  {% if error %}<div class="msg err">{{ error }}</div>{% endif %}
</div>
<script>
function setType(btn,t){
  document.querySelectorAll(".tb").forEach(function(b){b.classList.remove("on");});
  btn.classList.add("on"); document.getElementById("empType").value=t;
  var w=document.getElementById("hrsWrap"),h=document.getElementById("hint");
  if(t==="casual"){w.style.display="none";h.textContent="Casual: no guaranteed hours";}
  else if(t==="full-time"){w.style.display="grid";h.textContent="Full-time is typically 38-40 hours per week";document.getElementById("hMin").value="38";document.getElementById("hMax").value="40";}
  else{w.style.display="grid";h.textContent="Guaranteed minimum hours for the roster";document.getElementById("hMin").value="";document.getElementById("hMax").value="";}
}
var td=new Date(),d5=new Date(td),d3=new Date(td);
d5.setDate(td.getDate()+5);d3.setDate(td.getDate()+3);
document.querySelector("[name=startDate]").value=d5.toISOString().split("T")[0];
document.querySelector("[name=signDate]").value=d3.toISOString().split("T")[0];

// Signature pad
var canvas=document.getElementById("sigCanvas");
var ctx=canvas.getContext("2d");
var drawing=false;
var hasSig=false;
function getPos(e){
  var r=canvas.getBoundingClientRect();
  var scaleX=canvas.width/r.width, scaleY=canvas.height/r.height;
  if(e.touches){return{x:(e.touches[0].clientX-r.left)*scaleX,y:(e.touches[0].clientY-r.top)*scaleY};}
  return{x:(e.clientX-r.left)*scaleX,y:(e.clientY-r.top)*scaleY};
}
ctx.strokeStyle="#16120D"; ctx.lineWidth=2.5; ctx.lineCap="round"; ctx.lineJoin="round";
canvas.addEventListener("mousedown",function(e){drawing=true;var p=getPos(e);ctx.beginPath();ctx.moveTo(p.x,p.y);e.preventDefault();});
canvas.addEventListener("mousemove",function(e){if(!drawing)return;var p=getPos(e);ctx.lineTo(p.x,p.y);ctx.stroke();hasSig=true;document.getElementById("sigStatus").textContent="Signature captured";e.preventDefault();});
canvas.addEventListener("mouseup",function(){drawing=false;});
canvas.addEventListener("touchstart",function(e){drawing=true;var p=getPos(e);ctx.beginPath();ctx.moveTo(p.x,p.y);e.preventDefault();},{passive:false});
canvas.addEventListener("touchmove",function(e){if(!drawing)return;var p=getPos(e);ctx.lineTo(p.x,p.y);ctx.stroke();hasSig=true;document.getElementById("sigStatus").textContent="Signature captured";e.preventDefault();},{passive:false});
canvas.addEventListener("touchend",function(){drawing=false;});
function clearSig(){ctx.clearRect(0,0,canvas.width,canvas.height);hasSig=false;document.getElementById("sigStatus").textContent="Sign above with your finger or mouse";}
function captureSig(){
  if(hasSig){document.getElementById("sigData").value=canvas.toDataURL("image/png");}
  return true;
}
</script>
</body></html>"""

def on_page(canvas, doc):
    canvas.saveState()
    w, h = A4; hh = 26*mm; ls = 20*mm; ly = h - hh + (hh - ls) / 2
    if canvas.getPageNumber() > 1:
        canvas.drawImage(LOGO_PATH, 20*mm, ly, width=ls, height=ls, preserveAspectRatio=True, mask="auto")
    canvas.setFillColor(GREY); canvas.setFont("Inter", 7.5)
    canvas.drawRightString(w-20*mm, h-hh+(hh/2)+2*mm,  "Browne St. — Pulse 2012 Ltd")
    canvas.drawRightString(w-20*mm, h-hh+(hh/2)-4*mm,  "50 Rosebank Rd, Avondale, Auckland 1026")
    canvas.setFillColor(ORANGE); canvas.rect(0, h-hh-2, w, 2.5, fill=1, stroke=0)
    canvas.setFillColor(MGREY);  canvas.rect(0, 12*mm, w, 0.5, fill=1, stroke=0)
    canvas.setFillColor(GREY);   canvas.setFont("Inter", 7.5)
    canvas.drawCentredString(w/2, 7*mm, str(canvas.getPageNumber()))
    canvas.restoreState()

def extract_paragraphs(docx_bytes):
    zin = zipfile.ZipFile(io.BytesIO(docx_bytes))
    xml = zin.read("word/document.xml").decode("utf-8")
    paras = []
    for pm in re.finditer(r"<w:p[ >].*?</w:p>", xml, re.DOTALL):
        px = pm.group()
        bold = "<w:b/>" in px
        szm = re.search(r"<w:sz w:val=\"(\d+)\"", px)
        fsz = int(szm.group(1))/2 if szm else 10
        inm = re.search(r"<w:ind w:left=\"(\d+)\"", px)
        ind = int(inm.group(1)) if inm else 0
        cm  = re.search(r"<w:color w:val=\"([^\"]+)\"", px)
        col = cm.group(1) if cm else None
        brk = "<w:sectPr>" in px
        txts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", px)
        txt = "".join(txts).replace("&amp;","&").replace("&lt;","<").replace("&gt;",">").replace("&quot;",'"').strip()
        paras.append({"text":txt,"bold":bold,"size":fsz,"indent":ind,"color":col,"page_break":brk})
    return paras

def safe(t): return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def title_block(title):
    return [Spacer(1,4*mm),
            Paragraph(title, ParagraphStyle("dt", fontName="Inter-Bold", fontSize=17, textColor=BLACK, spaceAfter=5*mm)),
            HRFlowable(width="100%", thickness=2, color=ORANGE, spaceAfter=7*mm)]

def render_para(p, tight=False):
    leading = 13 if tight else 16; spc = 2 if tight else 5
    txt = p["text"]
    if not txt: return Spacer(1, (2 if tight else 4)*mm)
    s = safe(txt); c, sz, bold = p["color"], p["size"], p["bold"]
    if c == "1A7A30" and txt == "DO":
        return [Spacer(1,5*mm), Paragraph("DO", ParagraphStyle("do_lbl", fontName="Inter-Bold", fontSize=11, leading=16, textColor=GREEN, alignment=TA_LEFT, spaceAfter=3*mm))]
    if c == "A11C1C" and txt == "DON\'T":
        return [Spacer(1,5*mm), Paragraph("DON\'T", ParagraphStyle("dn_lbl", fontName="Inter-Bold", fontSize=11, leading=16, textColor=RED, alignment=TA_LEFT, spaceAfter=3*mm))]
    if c == "1A7A30" and txt == "\u2713": return None
    if c == "A11C1C" and txt == "\u2717": return None
    if c == "1A7A30": return Paragraph("\u2713   "+s, ParagraphStyle("ti", fontName="Inter", fontSize=9, leading=13, spaceAfter=2, textColor=BLACK, leftIndent=4*mm))
    if c == "A11C1C": return Paragraph("\u2717   "+s, ParagraphStyle("xi", fontName="Inter", fontSize=9, leading=13, spaceAfter=2, textColor=BLACK, leftIndent=4*mm))
    if sz >= 14 and bold:
        return [Paragraph(s, ParagraphStyle("h1", fontName="Inter-Bold", fontSize=12, leading=16, spaceBefore=6*mm, spaceAfter=1*mm, textColor=ORANGE)),
                HRFlowable(width="100%", thickness=0.5, color=MGREY, spaceAfter=3*mm)]
    if bold and sz >= 10: return Paragraph(s, ParagraphStyle("h2", fontName="Inter-Medium", fontSize=10, leading=14, spaceBefore=3*mm, spaceAfter=2*mm, textColor=DGREY))
    if c == "555555": return Paragraph(s, ParagraphStyle("su", fontName="Inter", fontSize=9, leading=leading, spaceAfter=spc, textColor=HexColor("#555555")))
    if c == "777777": return Paragraph(s, ParagraphStyle("gr", fontName="Inter", fontSize=9, leading=leading, spaceAfter=spc, textColor=GREY))
    if p["indent"] > 0: return Paragraph(s, ParagraphStyle("ind", fontName="Inter", fontSize=9, leading=leading, spaceAfter=spc, leftIndent=p["indent"]/1440*inch, alignment=TA_JUSTIFY, textColor=BLACK))
    if sz >= 18 and bold: return Paragraph(s, ParagraphStyle("big", fontName="Inter-Bold", fontSize=sz, leading=sz+4, spaceAfter=4*mm, textColor=BLACK))
    if bold: return Paragraph(s, ParagraphStyle("b", fontName="Inter-Bold", fontSize=9, leading=leading, spaceAfter=spc, textColor=BLACK))
    return Paragraph(s, ParagraphStyle("n", fontName="Inter", fontSize=9, leading=leading, spaceAfter=spc, textColor=BLACK, alignment=TA_JUSTIFY))

def add(story, f):
    if f is None: return
    if isinstance(f, list): story.extend([x for x in f if x is not None])
    else: story.append(f)


from hr_documents import HR_DOCUMENTS, HR_BY_KEY

class _SafeDict(dict):
    def __missing__(self, k): return "________"

def _hr_fill(text, data):
    """Fill {field} placeholders with escaped values; blanks for empties."""
    import string
    d = _SafeDict()
    for k, v in (data or {}).items():
        d[k] = safe(v) if v else "________"
    emp = (data or {}).get("employee", "").strip()
    d["employee_first"] = safe(emp.split()[0]) if emp else "________"
    try:
        return string.Formatter().vformat(text, (), d)
    except Exception:
        return text

def _hr_field_grid(doc, data):
    """Header info as a two-column label/value grid."""
    lbl = ParagraphStyle("hf_l", fontName="Inter-Bold", fontSize=6.5, textColor=GREY, leading=9, spaceAfter=1)
    val = ParagraphStyle("hf_v", fontName="Inter-Bold", fontSize=9.5, textColor=BLACK, leading=13)
    cells = []
    for f in doc["fields"]:
        v = (data or {}).get(f["name"], "").strip()
        cells.append([Paragraph(f["label"].upper(), lbl),
                      Paragraph(safe(v) if v else "&nbsp;", val)])
    # pair up two fields per row
    rows = []
    for i in range(0, len(cells), 2):
        left = cells[i]
        right = cells[i+1] if i+1 < len(cells) else [Paragraph("", lbl), Paragraph("", val)]
        rows.append([left[0], right[0]])
        rows.append([left[1], right[1]])
    tbl = Table(rows, colWidths=["50%", "50%"])
    tbl.setStyle(TableStyle([
        ("TOPPADDING", (0,0), (-1,-1), 1), ("BOTTOMPADDING", (0,0), (-1,-1), 1),
        ("LEFTPADDING", (0,0), (-1,-1), 0), ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    # add a bit of breathing room after each value row
    return tbl

def _hr_longbox(value, hint, min_height=30):
    """A 'form field' box. When filled it grows to fit the text (no clipping);
    when blank it stays a compact fixed height so the template fits on one page."""
    body = ParagraphStyle("lb", fontName="Inter", fontSize=9, leading=13, textColor=BLACK, alignment=TA_LEFT)
    hint_s = ParagraphStyle("lh", fontName="Inter-Italic", fontSize=8, leading=11, textColor=HexColor("#9A9A9A"))
    has = bool(value and value.strip())
    content = Paragraph(safe(value).replace("\n", "<br/>"), body) if has else Paragraph(hint or "", hint_s)
    kwargs = {} if has else {"rowHeights": [min_height]}
    tbl = Table([[content]], colWidths=["100%"], **kwargs)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), LGREY),
        ("BOX", (0,0), (-1,-1), 0.5, MGREY),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 8), ("RIGHTPADDING", (0,0), (-1,-1), 8),
    ]))
    return tbl

def _hr_signoff(blocks):
    """Signature blocks side by side at the foot of the doc."""
    name_l = ParagraphStyle("sg_t", fontName="Inter-Bold", fontSize=8, textColor=ORANGE, leading=12, spaceAfter=1.5*mm)
    row_l  = ParagraphStyle("sg_r", fontName="Inter", fontSize=8, textColor=DGREY, leading=15)
    note_s = ParagraphStyle("sg_n", fontName="Inter-Italic", fontSize=6.5, textColor=GREY, leading=9, spaceBefore=2)
    cols = []
    for b in blocks:
        flow = [Paragraph(b["label"].upper(), name_l)]
        for r in b["rows"]:
            flow.append(Paragraph(f"{r}:  " + "_"*26, row_l))
        if b.get("note"):
            flow.append(Paragraph(b["note"], note_s))
        cols.append(flow)
    while len(cols) < 2:
        cols.append([Paragraph("", row_l)])
    tbl = Table([cols], colWidths=["50%", "50%"])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (0,0), 0), ("RIGHTPADDING", (0,0), (0,0), 14),
        ("LEFTPADDING", (1,0), (1,0), 14),
    ]))
    return tbl

def build_hr_doc(key, data=None):
    """Render an HR template (record or letter) to a reportlab story."""
    data = data or {}
    doc = HR_BY_KEY.get(key)
    if not doc:
        return [Paragraph("Unknown document.", ParagraphStyle("e", fontName="Inter"))]
    story = []
    sec   = ParagraphStyle("hr_sec", fontName="Inter-Bold", fontSize=9.5, textColor=ORANGE, spaceBefore=2.5*mm, spaceAfter=1.5*mm, leading=12)
    para  = ParagraphStyle("hr_p", fontName="Inter", fontSize=9, leading=12.5, spaceAfter=1.5*mm, textColor=BLACK, alignment=TA_JUSTIFY)

    # Logo + title header
    img = Image(LOGO_PATH, width=18*mm, height=18*mm); img.hAlign = "LEFT"
    story.append(img); story.append(Spacer(1, 1.5*mm))
    story.append(Paragraph(doc["title"], ParagraphStyle("hr_t", fontName="Inter-Bold", fontSize=16, textColor=BLACK, spaceAfter=3*mm)))
    story.append(HRFlowable(width="100%", thickness=2, color=ORANGE, spaceAfter=4*mm))

    if doc["kind"] == "letter":
        # Letter-style: P&C + addressee + date, then body
        meta_s = ParagraphStyle("hr_meta", fontName="Inter", fontSize=8.5, leading=12.5, textColor=BLACK)
        story.append(Paragraph("<b>Private &amp; Confidential</b>", meta_s))
        story.append(Spacer(1, 2*mm))
        story.append(Paragraph(safe(data.get("employee","________")), meta_s))
        if data.get("role"): story.append(Paragraph(safe(data["role"]), meta_s))
        story.append(Spacer(1, 1*mm))
        story.append(Paragraph(safe(data.get("date","________")), ParagraphStyle("hr_d", fontName="Inter-Light", fontSize=8.5, textColor=GREY, leading=12)))
        story.append(Spacer(1, 4*mm))
    else:
        # Record-style: intro then header grid
        for p in doc.get("intro", []):
            story.append(Paragraph(_hr_fill(p, data), para))
        story.append(Spacer(1, 0.5*mm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=MGREY, spaceAfter=2.5*mm))
        story.append(_hr_field_grid(doc, data))
        story.append(HRFlowable(width="100%", thickness=0.5, color=MGREY, spaceBefore=2.5*mm, spaceAfter=1.5*mm))

    # Body sections
    for s in doc["sections"]:
        t = s.get("type")
        if t == "para":
            story.append(Paragraph(_hr_fill(s["text"], data), para))
        elif t == "lines":
            if s.get("label"): story.append(Paragraph(s["label"], sec))
            story.append(_hr_longbox(data.get(s["name"], ""), "", min_height=8*(s.get("lines",1))+6))
            story.append(Spacer(1, 0.8*mm))
        else:  # long
            if s.get("label"): story.append(Paragraph(s["label"], sec))
            story.append(_hr_longbox(data.get(s["name"], ""), s.get("hint",""), min_height=s.get("min_height", 22)))
            story.append(Spacer(1, 0.8*mm))

    # Keep the rule + signature block together so it never orphans onto a near-empty page.
    from reportlab.platypus import KeepTogether
    story.append(Spacer(1, 1.5*mm))
    story.append(KeepTogether([
        HRFlowable(width="100%", thickness=0.5, color=MGREY, spaceAfter=2*mm),
        _hr_signoff(doc["signoff"]),
    ]))
    return story

def generate_hr_pdf(key, data=None):
    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4, leftMargin=22*mm, rightMargin=22*mm, topMargin=32*mm, bottomMargin=20*mm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="main", frames=frame, onPage=on_page)])
    doc.build(build_hr_doc(key, data))
    buf.seek(0)
    return buf


from job_descriptions import get_jd, GENERAL_DUTIES, JD_BY_KEY, JOB_DESCRIPTIONS

def build_jd(role="Front of House"):
    s = lambda t: t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    # Resolve the role to a normalised JD entry; fall back to Front of House
    # content (original behaviour) for any free-typed role we don't have.
    jd = get_jd(role) or JD_BY_KEY.get("front-of-house")
    title   = jd["title"] if get_jd(role) else (role or jd["title"])
    purpose = jd["purpose"]
    duties  = jd["duties"]
    skills  = jd.get("skills") or []
    story = []
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("Job Description", ParagraphStyle("dt_jd", fontName="Inter-Bold", fontSize=17, textColor=BLACK, spaceAfter=4*mm)))
    story.append(HRFlowable(width="100%", thickness=2, color=ORANGE, spaceAfter=5*mm))
    sec      = ParagraphStyle("sec", fontName="Inter-Bold",  fontSize=10, textColor=ORANGE, spaceBefore=4*mm, spaceAfter=1*mm, leading=14)
    rule_hr  = lambda: HRFlowable(width="100%", thickness=0.5, color=MGREY, spaceAfter=3*mm)
    lbl      = ParagraphStyle("lbl", fontName="Inter-Bold",  fontSize=9,  textColor=BLACK, spaceAfter=2*mm, leading=13)
    bul      = ParagraphStyle("bul", fontName="Inter",       fontSize=8.5,textColor=BLACK, spaceAfter=1, leading=12, leftIndent=4*mm)
    bold_bul = ParagraphStyle("bbl", fontName="Inter-Bold",  fontSize=8.5,textColor=BLACK, spaceAfter=2, leading=12, leftIndent=4*mm)
    story.append(Paragraph("Job title", sec)); story.append(rule_hr())
    story.append(Paragraph(s(title), lbl))
    story.append(Paragraph("Purpose", sec)); story.append(rule_hr())
    story.append(Paragraph(s(purpose), bold_bul))
    story.append(Paragraph("Specific duties &amp; responsibilities", sec)); story.append(rule_hr())
    for item in duties:
        story.append(Paragraph("\u2713   "+s(item), bul))
    story.append(Paragraph("General duties &amp; responsibilities", sec)); story.append(rule_hr())
    for item in GENERAL_DUTIES:
        story.append(Paragraph("\u2713   "+s(item), bul))
    if skills:
        story.append(Paragraph("Skills, experience &amp; education", sec)); story.append(rule_hr())
        for item in skills:
            story.append(Paragraph("\u2713   "+s(item), bul))
    return story

def build_cover(full_name, role, start_fmt, emp_type, paras):
    story = []
    img = Image(LOGO_PATH, width=28*mm, height=28*mm); img.hAlign="LEFT"
    story.append(img); story.append(Spacer(1,3*mm))
    story.append(HRFlowable(width="100%", thickness=2.5, color=ORANGE, spaceAfter=0))
    lbl = ParagraphStyle("lbl", fontName="Inter-Bold", fontSize=6.5, textColor=GREY, leading=9)
    val = ParagraphStyle("val", fontName="Inter-Bold", fontSize=10,  textColor=BLACK, leading=14)
    def cell(l,v): return [Paragraph(l,lbl), Paragraph(safe(v),val)]
    data = [[cell("EMPLOYEE",full_name), cell("ROLE",role), cell("START DATE",start_fmt), cell("TYPE",emp_type.title())]]
    tbl = Table(data, colWidths=["25%","25%","25%","25%"])
    tbl.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),LGREY),("TOPPADDING",(0,0),(-1,-1),6),
        ("BOTTOMPADDING",(0,0),(-1,-1),6),("LEFTPADDING",(0,0),(-1,-1),8),
        ("RIGHTPADDING",(0,0),(-1,-1),4),("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(tbl)
    story.append(HRFlowable(width="100%", thickness=0.5, color=MGREY, spaceAfter=4*mm))
    addr_s = ParagraphStyle("ad", fontName="Inter",       fontSize=8,   leading=12, spaceAfter=1, textColor=BLACK)
    date_s = ParagraphStyle("da", fontName="Inter-Light", fontSize=8,   leading=12, spaceAfter=0, textColor=GREY)
    body_s = ParagraphStyle("bo", fontName="Inter",       fontSize=8.5, leading=13.5, spaceAfter=3, textColor=BLACK, alignment=TA_JUSTIFY)
    bold_s = ParagraphStyle("bh", fontName="Inter-Bold",  fontSize=9,   leading=13, spaceBefore=2*mm, spaceAfter=2, textColor=BLACK)
    sig_s  = ParagraphStyle("sg", fontName="Inter",       fontSize=8.5, leading=13, spaceAfter=1, textColor=BLACK)
    employer_addr=[]; letter_date=[]; employee_addr=[]; body_lines=[]
    state="employer"; done=False
    for p in paras:
        if done: break
        txt = p["text"]
        if not txt: continue
        if state=="employer":
            if any(x in txt for x in ["Pulse 2012","Browne St","Rosebank","Avondale","Auckland 1026","New Zealand"]): employer_addr.append(txt)
            elif re.match(r"\d{1,2} \w+ \d{4}", txt): letter_date.append(txt); state="employee"
        elif state=="employee":
            if txt.startswith("Dear "): state="body"; body_lines.append(("dear",txt,False))
            else: employee_addr.append(txt)
        elif state=="body":
            if "Sam Fraser" in txt or txt=="Director":
                body_lines.append(("sig",txt,False)); body_lines.append(("sig","Pulse 2012 Ltd t/a Browne St.",False)); done=True
            elif "Yours faithfully" in txt: body_lines.append(("space","",False)); body_lines.append(("body",txt,False))
            else: body_lines.append(("body",txt,p["bold"]))
    for l in employer_addr: story.append(Paragraph(safe(l), addr_s))
    story.append(Spacer(1,2*mm))
    for l in letter_date: story.append(Paragraph(safe(l), date_s))
    story.append(Spacer(1,2*mm))
    for l in employee_addr: story.append(Paragraph(safe(l), addr_s))
    story.append(Spacer(1,3*mm))
    for kind,txt,bold in body_lines:
        s=safe(txt)
        if kind=="dear": story.append(Paragraph(s,body_s))
        elif bold or kind=="bold": story.append(Paragraph(s,bold_s))
        elif kind=="sig": story.append(Paragraph(s,sig_s))
        elif kind=="space": story.append(Spacer(1,2*mm))
        else: story.append(Paragraph(s,body_s))
    story.append(PageBreak())
    return story

def build_agreement(paras):
    start_idx = None
    for i,p in enumerate(paras):
        if p["text"] == "Individual Employment Agreement" and p["bold"] and p["size"] >= 14:
            start_idx = i; break
    if start_idx is None:
        for i,p in enumerate(paras):
            if p["text"] == "- Private and Confidential -" and i > 20: start_idx = i; break
    story = title_block("Employment Agreement")
    prev_empty = False
    for p in paras[start_idx:]:
        if p["page_break"]: continue
        if not p["text"]:
            if not prev_empty: story.append(Spacer(1,4*mm))
            prev_empty = True; continue
        prev_empty = False
        add(story, render_para(p, tight=False))
    return story

def build_hs(paras):
    story = title_block("Health &amp; Safety Guide")
    prev_empty = False; i = 0
    while i < len(paras):
        p = paras[i]; txt = p["text"]; c = p["color"]
        if p["page_break"]:
            story.append(PageBreak()); story.extend(title_block("Health &amp; Safety Guide")); i+=1; continue
        if not txt:
            if not prev_empty: story.append(Spacer(1,2*mm))
            prev_empty = True; i+=1; continue
        prev_empty = False
        if c == "1A7A30" and txt == "\u2713":
            if i+1 < len(paras) and paras[i+1]["text"]:
                story.append(Paragraph("\u2713   "+safe(paras[i+1]["text"]), ParagraphStyle("ti", fontName="Inter", fontSize=9, leading=13, spaceAfter=2, textColor=BLACK, leftIndent=4*mm)))
                i+=2; continue
        if c == "A11C1C" and txt == "\u2717":
            if i+1 < len(paras) and paras[i+1]["text"]:
                story.append(Paragraph("\u2717   "+safe(paras[i+1]["text"]), ParagraphStyle("xi", fontName="Inter", fontSize=9, leading=13, spaceAfter=2, textColor=BLACK, leftIndent=4*mm)))
                i+=2; continue
        add(story, render_para(p, tight=True)); i+=1
    return story

def make_docx(form):
    full_name  = form.get("fullName","").strip()
    sig_data   = form.get("signature","").strip()  # base64 PNG from canvas
    addr1      = form.get("addr1","").strip()
    suburb     = form.get("suburb","").strip()
    citypost   = form.get("citypost","").strip()
    pronouns   = form.get("pronouns","they")
    role       = form.get("role","").strip()
    rate       = float(form.get("rate","0"))
    start_date = form.get("startDate","")
    sign_date  = form.get("signDate","")
    emp_type   = form.get("empType","part-time")
    h_min      = form.get("hMin","20").strip() or "20"
    h_max      = form.get("hMax","30").strip() or "30"
    first_name = full_name.split()[0] if full_name else full_name
    def fmt(d):
        try: return datetime.strptime(d,"%Y-%m-%d").strftime("%-d %B %Y")
        except: return d
    start_fmt = fmt(start_date); sign_fmt = fmt(sign_date) if sign_date else "[sign-by date]"
    today_fmt = datetime.today().strftime("%-d %B %Y")
    p = {"she":("she","her","her"),"he":("he","him","his"),"they":("they","them","their")}
    psub,pobj,ppos = p.get(pronouns,("they","them","their"))
    if emp_type=="casual":
        h63  = "6.3. This is a casual agreement. There are no guaranteed hours of work. Hours are offered as required by the Employer and the Employee may accept or decline shifts offered."
        h131 = "13.1. This is a casual position. There are no guaranteed hours of work. Hours will be offered as required by the Employer, and the Employee may accept or decline each shift as offered."
    elif emp_type=="full-time":
        h63  = "6.3. This is a full-time agreement. The Employee\'s hours of work are set out in clause 13 of this agreement."
        h131 = f"13.1. This is a full-time position. The Employee\'s hours of work shall be {h_min} to {h_max} hours per week, worked across Monday to Sunday as rostered by the Employer."
    else:
        h63  = "6.3. This is a part-time agreement. The Employee\'s hours of work are set out in clause 13 of this agreement."
        h131 = f"13.1. This is a part-time position. The Employee\'s guaranteed minimum hours of work shall be {h_min} to {h_max} hours per week, worked across Monday to Sunday as rostered by the Employer."
    replacements = [
        ("Emily Drage",full_name),("Dear Emily,",f"Dear {first_name},"),
        ("1/10 Tirimoana Road",addr1),("Te Atatu South",suburb),("Auckland 0602",citypost),
        ("23 March 2026",today_fmt),
        ("If we have not heard from you by 26 March 2026",f"If we have not heard from you by {sign_fmt}"),
        ("26 March 2026",start_fmt),("24 March 2026",sign_fmt),
        ("role of Front of House.",f"role of {role}."),
        ("2.1. The Employee is employed in the role of Front of House.",f"2.1. The Employee is employed in the role of {role}."),
        ("$28.00 per hour. This rate is above the current adult minimum wage of $23.50 per hour (effective 1 April 2025), and will remain above the minimum wage of $23.95 per hour effective from 1 April 2026.",f"{rate:.2f} per hour. This rate is above the current adult minimum wage of $23.95 per hour effective from 1 April 2026."),
        ("6.3. This is a part-time agreement. The Employee\'s hours of work are set out in clause 13 of this agreement.",h63),
        ("13.1. This is a part-time position. The Employee\'s guaranteed minimum hours of work shall be 20 to 30 hours per week, worked across Monday to Sunday as rostered by the Employer.",h131),
        ("Emily Drage acknowledges and declares that she:",f"{full_name} acknowledges and declares that {psub}:"),
        ("Emily Drage also declares that she:",f"{full_name} also declares that {psub}:"),
        ("has been advised of her right to seek independent advice on the terms of this agreement;",f"has been advised of {ppos} right to seek independent advice on the terms of this agreement;"),
        ("has not failed to disclose any matter that may have materially influenced the Employer\'s decision to employ her;",f"has not failed to disclose any matter that may have materially influenced the Employer\'s decision to employ {pobj};"),
        ("has not failed to disclose any medical conditions or injuries that may affect her ability to perform the job adequately and/or safely; and",f"has not failed to disclose any medical conditions or injuries that may affect {ppos} ability to perform the job adequately and/or safely; and"),
        ("Name: Emily Drage",f"Name: {full_name}"),
        ("Pulse 2012 Ltd t/a Browne St. is pleased to offer this Individual Employment Agreement to Emily Drage.",f"Pulse 2012 Ltd t/a Browne St. is pleased to offer this Individual Employment Agreement to {full_name}."),
        ("Front of House",role),
    ]
    zin = zipfile.ZipFile(io.BytesIO(TEMPLATE_BYTES))
    xml = zin.read("word/document.xml").decode("utf-8")
    for old,new in replacements: xml = xml.replace(old,new)
    out = io.BytesIO()
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename=="word/document.xml": zout.writestr(item,xml.encode("utf-8"))
            else: zout.writestr(item,zin.read(item.filename))
    zin.close(); out.seek(0)
    return out.read(), first_name, start_fmt, emp_type, sig_data


def create_sig_overlay(sig_data, today_fmt, page_pdf_bytes):
    """Create overlay PDF with signature placed dynamically at the exact Signature line position."""
    import base64 as _b64
    from reportlab.pdfgen import canvas as _canvas
    from pdfminer.high_level import extract_pages as _ep
    from pdfminer.layout import LTTextBox as _LTB

    if not sig_data or not sig_data.startswith("data:image"):
        return None

    header, b64str = sig_data.split(",", 1)
    sig_bytes = _b64.b64decode(b64str)
    sig_tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    sig_tmp.write(sig_bytes); sig_tmp.flush()

    # Find exact coordinates of "Signature:" and "Date:" lines using pdfminer
    sig_y = None
    date_y = None
    sig_x = 68.4  # default left margin

    try:
        pages = list(_ep(io.BytesIO(page_pdf_bytes)))
        page = pages[0]
        sig_boxes = []
        date_boxes = []
        for element in page:
            if isinstance(element, _LTB):
                txt = element.get_text().strip()
                if txt.startswith("Signature:"):
                    sig_boxes.append(element.y0)
                if txt.startswith("Date:") and element.x0 < 100:
                    date_boxes.append(element.y0)
        # First Signature box = employer signature line
        if sig_boxes:
            sig_y = sorted(sig_boxes, reverse=True)[0]  # highest = employer sig
        if date_boxes:
            date_y = sorted(date_boxes, reverse=True)[0]  # highest = employer date
    except Exception as e:
        print(f"pdfminer error: {e}")

    if sig_y is None:
        return None

    # Get page dimensions from the PDF
    from pypdf import PdfReader as _PR
    reader = _PR(io.BytesIO(page_pdf_bytes))
    page_obj = reader.pages[0]
    pw = float(page_obj.mediabox.width)
    ph = float(page_obj.mediabox.height)

    buf = io.BytesIO()
    c = _canvas.Canvas(buf, pagesize=(pw, ph))

    # Place signature image ON the signature line
    # x: after "Signature: " label (~56pts at 9pt Inter)
    # y: bottom of image = y0 of signature line, height = 18pts upward
    c.drawImage(sig_tmp.name, 125.0, sig_y, width=180.0, height=18.0,
                preserveAspectRatio=True, mask="auto")

    # Place date on the Date line
    if date_y is not None:
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0.1, 0.1, 0.1)
        c.drawString(103.0, date_y + 1.5, today_fmt)

    c.save()
    buf.seek(0)
    return buf.read()

def generate_pdf(docx_bytes, full_name, role, start_fmt, emp_type, sig_data="",
                 include_jd=True, include_hs=True, include_govt=True):
    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4, leftMargin=22*mm, rightMargin=22*mm, topMargin=32*mm, bottomMargin=20*mm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="main", frames=frame, onPage=on_page)])
    tmpl_paras = extract_paragraphs(docx_bytes)
    story  = build_cover(full_name, role, start_fmt, emp_type, tmpl_paras)
    story += build_agreement(tmpl_paras)
    if include_jd:
        story.append(PageBreak())
        story += build_jd(role)
    if include_hs:
        story.append(PageBreak())
        story += build_hs(extract_paragraphs(HS_DOCX_BYTES))
    doc.build(story)
    buf.seek(0); main_pdf = buf.read()

    # Apply signature overlay if provided
    if sig_data and sig_data.startswith("data:image"):
        try:
            from pypdf import PdfWriter as _W, PdfReader as _R
            reader_main = _R(io.BytesIO(main_pdf))
            # Find the page with "Name: Sam Fraser" — typically the last agreement page
            sig_page_idx = None
            for idx in range(len(reader_main.pages)):
                txt = reader_main.pages[idx].extract_text() or ""
                if "Sam Fraser" in txt and "Signature" in txt:
                    sig_page_idx = idx
                    break
            if sig_page_idx is not None:
                today_fmt = datetime.today().strftime("%-d %B %Y")
                # Extract just the signature page as its own PDF for pdfminer analysis
                single_writer = _W()
                single_writer.add_page(reader_main.pages[sig_page_idx])
                single_buf = io.BytesIO()
                single_writer.write(single_buf)
                single_buf.seek(0)
                overlay_pdf = create_sig_overlay(sig_data, today_fmt, single_buf.read())
                if overlay_pdf:
                    overlay_page = _R(io.BytesIO(overlay_pdf)).pages[0]
                    reader_main.pages[sig_page_idx].merge_page(overlay_page)
            # Rebuild the PDF with the overlaid page
            writer_sig = _W()
            for page in reader_main.pages:
                writer_sig.add_page(page)
            sig_buf = io.BytesIO()
            writer_sig.write(sig_buf)
            sig_buf.seek(0)
            main_pdf = sig_buf.read()
        except Exception as sig_err:
            print(f"Signature overlay error: {sig_err}")

    writer = PdfWriter()
    parts = [main_pdf] + ([IR330_PDF_BYTES, KS10_PDF_BYTES] if include_govt else [])
    for pdf_bytes in parts:
        for page in PdfReader(io.BytesIO(pdf_bytes)).pages:
            writer.add_page(page)
    out = io.BytesIO(); writer.write(out); out.seek(0)
    return out

# ---------------------------------------------------------------------------
# Shared chrome for the lighter pages (landing / JD / HR forms)
# ---------------------------------------------------------------------------
_BASE_CSS = """
:root{
  --bg:#F3EFE6;--surface:#FFFFFF;--surface-2:#FBF8F2;
  --ink:#16120D;--ink-soft:#3B342A;--muted:#8C7F6B;--faint:#ADA189;
  --line:#EBE3D5;--line-2:#E1D7C6;
  --orange:#FE5000;--orange-ink:#C43C00;--orange-tint:#FFF2EB;--orange-soft:#FFDECE;
  --radius:18px;--radius-sm:11px;
  --shadow:0 1px 2px rgba(22,18,13,.04),0 18px 40px -22px rgba(22,18,13,.18);
  --ease:180ms cubic-bezier(.2,.65,.2,1);
}
*{box-sizing:border-box;margin:0;padding:0}
html{-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--ink);line-height:1.5;
  min-height:100vh;padding:44px 18px 60px;
  background:radial-gradient(1100px 460px at 50% -8%,#FCF9F2,rgba(252,249,242,0) 62%),var(--bg)}
.card{position:relative;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
  box-shadow:var(--shadow);max-width:600px;margin:0 auto;padding:34px 34px 30px;overflow:hidden}
.card::before{content:"";position:absolute;inset:0 0 auto 0;height:3px;
  background:linear-gradient(90deg,var(--orange),#FF7A3D)}
.top-bar{display:none}
.mast{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:24px}
.mast img{height:21px;width:auto;display:block}
.mast .tag{font-size:10.5px;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:var(--faint)}
.brand{font-size:10.5px;font-weight:600;letter-spacing:.16em;color:var(--faint);text-transform:uppercase;margin-bottom:14px}
h1{font-size:25px;font-weight:700;letter-spacing:-.021em;color:var(--ink);line-height:1.12;margin-bottom:6px}
.sub{font-size:13.5px;color:var(--muted);margin-bottom:24px;line-height:1.55;max-width:48ch}
.lbl{font-size:10.5px;font-weight:600;letter-spacing:.14em;color:var(--faint);text-transform:uppercase;margin:26px 0 12px}
.f{margin-bottom:13px}
.f label{display:block;font-size:12.5px;color:var(--ink-soft);margin-bottom:6px;font-weight:550}
.f input,.f select,.f textarea{width:100%;padding:12px 13px;border:1px solid var(--line-2);border-radius:var(--radius-sm);
  background:var(--surface-2);color:var(--ink);font-size:15px;font-family:inherit;
  transition:border var(--ease),box-shadow var(--ease),background var(--ease)}
.f input::placeholder,.f textarea::placeholder{color:var(--faint)}
.f textarea{min-height:86px;resize:vertical;line-height:1.55}
.f input:focus,.f select:focus,.f textarea:focus{outline:none;border-color:var(--orange);background:#fff;box-shadow:0 0 0 4px var(--orange-tint)}
.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.hint{font-size:12px;color:var(--faint);margin-top:7px}
.btn{width:100%;height:52px;background:var(--orange);color:#fff;border:none;border-radius:12px;font-size:15px;
  font-weight:600;letter-spacing:.01em;font-family:inherit;cursor:pointer;margin-top:24px;
  box-shadow:0 12px 26px -12px rgba(254,80,0,.55);transition:transform var(--ease),background var(--ease),box-shadow var(--ease)}
.btn:hover{background:var(--orange-ink);transform:translateY(-1px);box-shadow:0 16px 30px -14px rgba(254,80,0,.6)}
.btn:active{transform:translateY(0)}
.back{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:var(--muted);text-decoration:none;margin-bottom:18px;transition:color var(--ease)}
.back:hover{color:var(--orange)}
.docs{display:flex;flex-direction:column;gap:9px}
.doc{display:flex;align-items:center;gap:15px;padding:15px 16px;border:1px solid var(--line);border-radius:14px;
  text-decoration:none;background:var(--surface);transition:border var(--ease),box-shadow var(--ease),transform var(--ease)}
.doc:hover{border-color:var(--orange-soft);box-shadow:0 14px 30px -20px rgba(22,18,13,.4);transform:translateY(-1px)}
.doc .ic{width:42px;height:42px;border-radius:12px;background:var(--orange-tint);color:var(--orange);
  display:flex;align-items:center;justify-content:center;flex-shrink:0;border:1px solid var(--orange-soft)}
.doc .ic svg{width:20px;height:20px}
.doc .tx{flex:1;min-width:0;display:flex;flex-direction:column;gap:3px}
.doc .tt{font-size:14.5px;font-weight:600;color:var(--ink);letter-spacing:-.01em;line-height:1.25}
.doc .dd{font-size:12.5px;color:var(--muted);line-height:1.45}
.doc .chev{color:var(--faint);flex-shrink:0;display:flex;transition:transform var(--ease),color var(--ease)}
.doc:hover .chev{color:var(--orange);transform:translateX(3px)}
.note{margin-top:22px;padding:13px 16px;border-radius:12px;font-size:12.5px;background:var(--orange-tint);
  color:var(--orange-ink);line-height:1.6;border:1px solid var(--orange-soft)}
.note.filing{display:flex;align-items:center;gap:14px;justify-content:space-between}
.note .ntx{flex:1;min-width:0}
.note .ntx-cancel{flex-shrink:0;white-space:nowrap;font-weight:600;color:var(--orange-ink);text-decoration:underline;text-underline-offset:2px}
.msg{margin-top:16px;padding:12px 14px;border-radius:11px;font-size:13px}
.err{background:#FCEBE7;color:#9a2b1a;border:1px solid #F1C6BB}
.foot{margin-top:28px;padding-top:16px;border-top:1px solid var(--line);font-size:10.5px;color:var(--faint);
  letter-spacing:.03em;display:flex;justify-content:space-between;align-items:center;gap:12px}
.foot a{color:var(--muted);text-decoration:none}.foot a:hover{color:var(--orange)}
.ai-panel{border:1px solid var(--line);border-radius:15px;background:var(--surface-2);padding:16px 17px;margin-bottom:8px}
.ai-head{display:flex;align-items:center;gap:8px;font-size:13.5px;font-weight:700;color:var(--ink)}
.ai-head svg{color:var(--orange)}
.ai-tag{font-size:10px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--faint);border:1px solid var(--line-2);border-radius:20px;padding:2px 8px}
.ai-sub{font-size:12px;color:var(--muted);line-height:1.55;margin:6px 0 12px}
.ai-consent{display:flex;gap:9px;align-items:flex-start;font-size:12.5px;color:var(--ink-soft);line-height:1.45;cursor:pointer;margin-bottom:12px}
.ai-consent input{margin-top:2px;flex-shrink:0}
.ai-row{display:flex;align-items:center;gap:12px;margin-bottom:10px}
.ai-status{font-size:12px;color:var(--muted)}
.mini.rec-on{border-color:#C6402B;color:#C6402B;background:#FCEBE7}
.ai-transcript{width:100%;min-height:96px;resize:vertical;padding:11px 13px;border:1px solid var(--line-2);border-radius:var(--radius-sm);background:#fff;font-family:inherit;font-size:14px;line-height:1.5;color:var(--ink)}
.ai-transcript:focus{outline:none;border-color:var(--orange);box-shadow:0 0 0 4px var(--orange-tint)}
.ai-draft{height:46px;margin-top:12px}
.ai-result{margin-top:14px}
.ai-err{background:#FCEBE7;color:#9a2b1a;border:1px solid #F1C6BB;border-radius:11px;padding:11px 13px;font-size:12.5px}
.ai-done{font-size:12.5px;font-weight:600;color:#2E6B33;background:#E7F0E1;border:1px solid #BBD9B4;border-radius:10px;padding:9px 12px}
.ai-summary{font-size:13px;color:var(--ink-soft);line-height:1.55;margin-top:10px;padding:0 2px}
.ai-flags-h{font-size:11px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--ink);margin:14px 0 8px}
.ai-flag{border-radius:11px;padding:10px 13px;margin-bottom:8px;border:1px solid var(--line-2);background:#fff}
.ai-flag.caution{border-color:#F1C79A;background:#FFF6EC}
.ai-flag.serious{border-color:#F1C6BB;background:#FDEEEA}
.ai-flag-t{font-size:13px;font-weight:600;color:var(--ink)}
.ai-flag-s{font-size:12.5px;color:var(--muted);margin-top:3px;line-height:1.5}
.ai-disc{font-size:11px;font-style:italic;color:var(--faint);margin-top:12px;line-height:1.5}
@media(max-width:520px){.card{padding:26px 20px}.row{grid-template-columns:1fr}}
"""

# --- line-icon set (stroke, currentColor) ----------------------------------
_ICON_PATHS = {
 "users":'<path d="M16 19v-1a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v1"/><circle cx="9" cy="7.2" r="3.1"/><path d="M22 19v-1a4 4 0 0 0-3-3.85"/><path d="M15.5 3.6a4 4 0 0 1 0 7"/>',
 "box":'<path d="M12 3 3 7.5v9L12 21l9-4.5v-9L12 3Z"/><path d="m3 7.5 9 4.5 9-4.5"/><path d="M12 12v9"/>',
 "agreement":'<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5Z"/><path d="M14 3v5h5"/><path d="M8.5 15c1.4-1.3 2.6 1.3 4 .2"/>',
 "jd":'<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5Z"/><path d="M14 3v5h5"/><path d="M9 12.5h6M9 16h4"/>',
 "chat":'<path d="M21 11.5a8 8 0 0 1-11.6 7.1L3 21l2.4-6.4A8 8 0 1 1 21 11.5Z"/>',
 "search":'<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
 "alert":'<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4.5"/><path d="M12 17.5h.01"/>',
 "chevron":'<path d="m9 6 6 6-6 6"/>',
 "plus":'<path d="M12 5v14M5 12h14"/>',
 "edit":'<path d="M12 20h9"/><path d="M16.5 3.5a2.05 2.05 0 0 1 3 3L7.5 18.5 3 20l1.5-4.5Z"/>',
 "upload":'<path d="M12 15V3"/><path d="m7.5 7.5 4.5-4.5 4.5 4.5"/><path d="M20 16.5V19a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-2.5"/>',
 "download":'<path d="M12 3v12"/><path d="m7.5 10.5 4.5 4.5 4.5-4.5"/><path d="M20 16.5V19a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-2.5"/>',
 "logout":'<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 16 5-4-5-4"/><path d="M21 12H9"/>',
 "lock":'<rect x="4.5" y="10.5" width="15" height="9.5" rx="2.2"/><path d="M8 10.5V7a4 4 0 0 1 8 0v3.5"/>',
 "trash":'<path d="M3.5 6h17"/><path d="M8 6V4.2A1.2 1.2 0 0 1 9.2 3h5.6A1.2 1.2 0 0 1 16 4.2V6"/><path d="M6.5 6l.9 13.1A2 2 0 0 0 9.4 21h5.2a2 2 0 0 0 2-1.9L17.5 6"/>',
 "arrow-left":'<path d="M15 6l-6 6 6 6"/>',
 "shield":'<path d="M12 3l7 2.5V11c0 4.4-3 7.9-7 9-4-1.1-7-4.6-7-9V5.5L12 3Z"/><path d="m9 12 2 2 4-4"/>',
 "archive":'<rect x="3" y="4.5" width="18" height="4" rx="1"/><path d="M5 8.5V19a1.5 1.5 0 0 0 1.5 1.5h11A1.5 1.5 0 0 0 19 19V8.5"/><path d="M10 12h4"/>',
}
def _ic(name, size=20, sw=1.6):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">' + _ICON_PATHS.get(name, "") + '</svg>')
_CHEV = '<span class="chev">' + _ic("chevron", 18, 1.8) + '</span>'

_LANDING_TMPL = """<!DOCTYPE html><html><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Browne St. — HR</title><style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');""" + _BASE_CSS + """</style></head><body>
<div class="card">
  <div class="mast">
    <img src="/brand/logo-wordmark.svg" alt="Browne St.">
    <span class="tag">HR &amp; Onboarding</span>
  </div>
  <h1>Documents &amp; staff</h1>
  <p class="sub">Generate branded HR documents, or open a team member's folder. Everything downloads as a PDF.</p>
  <div class="lbl">Staff</div>
  <div class="docs">
    <a class="doc" href="/staff"><span class="ic">""" + _ic("users") + """</span><span class="tx"><span class="tt">Staff records</span><span class="dd">Each team member's folder &mdash; contracts, warnings, certifications and uploads.</span></span>""" + _CHEV + """</a>
  </div>
  <div class="lbl">Onboarding &amp; contracts</div>
  <div class="docs">
    <a class="doc" href="/onboarding"><span class="ic">""" + _ic("box") + """</span><span class="tx"><span class="tt">New staff onboarding pack</span><span class="dd">Agreement, job description, H&amp;S guide, IR330 &amp; KS10 &mdash; personalised.</span></span>""" + _CHEV + """</a>
    <a class="doc" href="/contract"><span class="ic">""" + _ic("agreement") + """</span><span class="tx"><span class="tt">Employment agreement</span><span class="dd">Standalone offer letter + individual employment agreement.</span></span>""" + _CHEV + """</a>
    <a class="doc" href="/job-description"><span class="ic">""" + _ic("jd") + """</span><span class="tx"><span class="tt">Job description</span><span class="dd">Branded JD for any of {{ jd_count }} roles.</span></span>""" + _CHEV + """</a>
  </div>
  <div class="lbl">HR records</div>
  <div class="docs">
    {% for d in hr_docs %}
    <a class="doc" href="/hr/{{ d.key }}"><span class="ic">{{ d.icon|safe }}</span><span class="tx"><span class="tt">{{ d.title }}</span><span class="dd">{{ d.desc }}</span></span>""" + _CHEV + """</a>
    {% endfor %}
  </div>
  <div class="foot"><span>Browne St. &mdash; Pulse 2012 Ltd &middot; Avondale</span><span><a href="/settings">Settings &amp; backup</a> &middot; <a href="/logout">Sign out</a></span></div>
</div></body></html>"""

_HR_ICONS = {"informal-discussion": "chat", "investigation": "search", "written-warning": "alert"}
_HR_DESCS = {
    "informal-discussion": "Record a coaching conversation and set expectations.",
    "investigation": "Document a concern and the employee's response.",
    "written-warning": "Issue a formal written warning.",
}

@app.route("/brand/<path:name>")
def brand_asset(name):
    from flask import send_from_directory
    return send_from_directory(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "assets"), name)

@app.route("/", methods=["GET"])
def index():
    hr_docs = [{"key": d["key"], "title": d["title"], "icon": _ic(_HR_ICONS.get(d["key"], "jd")),
                "desc": _HR_DESCS.get(d["key"], "")} for d in HR_DOCUMENTS]
    return render_template_string(_LANDING_TMPL, hr_docs=hr_docs, jd_count=len(JOB_DESCRIPTIONS))

def _prefill_from_staff(staff):
    if not staff:
        return {"fullName":"","addr1":"","suburb":"","citypost":"","pronouns":"","role":"","rate":""}
    return {"fullName": staff.get("full_name",""), "addr1": staff.get("address",""),
            "suburb": staff.get("suburb",""), "citypost": staff.get("citypost",""),
            "pronouns": staff.get("pronouns",""), "role": staff.get("role",""),
            "rate": staff.get("pay_rate","")}

def _render_form(staff=None, **kw):
    defaults = dict(page_title="New staff onboarding",
                    page_sub="Fill in the details and tap Generate. Downloads as a single branded PDF.",
                    action="/generate", submit_label="Generate onboarding pack",
                    show_pack=True, error=None, pf=_prefill_from_staff(staff))
    defaults.update(_staff_ctx(staff))
    defaults.update(kw)
    return render_template_string(HTML, **defaults)

@app.route("/onboarding", methods=["GET"])
def onboarding():
    return _render_form(staff=store.get_staff(request.args.get("staff","")))

@app.route("/contract", methods=["GET"])
def contract():
    return _render_form(staff=store.get_staff(request.args.get("staff","")),
                        page_title="Employment agreement",
                        page_sub="Generate a standalone, personalised agreement (offer letter + individual employment agreement).",
                        action="/generate-contract", submit_label="Generate agreement", show_pack=False)

# ---- Job description generator --------------------------------------------
_JD_TMPL = """<!DOCTYPE html><html><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Job description</title><style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');""" + _BASE_CSS + """</style></head><body>
<div class="card">
  <div class="top-bar"></div>
  <a class="back" href="/">&#8592; All documents</a>
  <h1>Job description</h1>
  <p class="sub">Pick a role and generate the branded Browne St. job description.</p>
  <form method="POST" action="/generate-jd">
    {{ staff_control|safe }}
    <div class="f"><label>Role</label>
      <select name="role">{% for jd in jds %}<option value="{{ jd.title }}"{% if jd.title==sel_role %} selected{% endif %}>{{ jd.title }}</option>{% endfor %}</select>
    </div>
    <button class="btn" type="submit">Generate job description</button>
  </form>
  {% if error %}<div class="msg err">{{ error }}</div>{% endif %}
</div></body></html>"""

@app.route("/job-description", methods=["GET"])
def job_description():
    staff = store.get_staff(request.args.get("staff",""))
    return render_template_string(_JD_TMPL, jds=JOB_DESCRIPTIONS, error=None,
                                  sel_role=(staff or {}).get("role",""), **_staff_ctx(staff))

def generate_jd_pdf(role):
    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4, leftMargin=22*mm, rightMargin=22*mm, topMargin=32*mm, bottomMargin=20*mm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="main", frames=frame, onPage=on_page)])
    doc.build(build_jd(role))
    buf.seek(0)
    return buf

@app.route("/generate-jd", methods=["POST"])
def generate_jd():
    try:
        role = request.form.get("role", "").strip()
        pdf = generate_jd_pdf(role).read()
        jd = get_jd(role)
        slug = (jd["key"] if jd else (role or "job-description")).replace(" ", "-")
        fname = f"{slug}-JD.pdf"
        sid = _maybe_file_to_staff(pdf, fname, "job-description")
        if sid:
            return redirect(f"/staff/{sid}")
        token = _store_pdf(pdf, fname)
        return _ready_page("Job description ready", f"<span class='name'>{role}</span> job description is ready.", token)
    except Exception as e:
        import traceback
        return render_template_string(_JD_TMPL, jds=JOB_DESCRIPTIONS, error=str(e) + " | " + traceback.format_exc()[-300:], sel_role="", staff_control="")

# ---- HR records generator -------------------------------------------------
_HR_TMPL = """<!DOCTYPE html><html><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ doc.title }}</title><style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');""" + _BASE_CSS + """</style></head><body>
<div class="card">
  <div class="top-bar"></div>
  <a class="back" href="/">&#8592; All documents</a>
  <h1>{{ doc.title }}</h1>
  <p class="sub">Fill in what you can &mdash; leave fields blank to generate a printable template.</p>

  <div class="ai-panel">
    <div class="ai-head">""" + _ic("chat", 17) + """ AI meeting assistant <span class="ai-tag">optional</span></div>
    <p class="ai-sub">Record or type the meeting, then let AI draft the notes below and run a New Zealand employment-law process check. Review and edit everything before you generate &mdash; this is guidance, not legal advice.</p>
    <label class="ai-consent"><input type="checkbox" id="aiConsent"> I confirm the employee has been told this meeting is being recorded / noted and is aware.</label>
    <div class="ai-row">
      <button type="button" class="mini" id="aiRecBtn" onclick="aiToggleRec()">&#9679; Record</button>
      <span class="ai-status" id="aiRecStatus">Not recording</span>
    </div>
    <textarea id="aiTranscript" class="ai-transcript" placeholder="The transcript appears here as you speak (Chrome/Edge), or type / paste your notes&hellip;"></textarea>
    <button type="button" class="btn ai-draft" id="aiDraftBtn" onclick="aiDraft()">Draft notes + compliance check</button>
    <div id="aiResult" class="ai-result" style="display:none"></div>
  </div>

  <form method="POST" action="/generate-hr">
    <input type="hidden" name="_key" value="{{ doc.key }}">
    {{ staff_control|safe }}
    <div class="lbl">Details</div>
    <div class="row">
      {% for f in doc.fields %}<div class="f"><label>{{ f.label }}</label><input name="{{ f.name }}" value="{{ prefill.get(f.name,'') }}"></div>{% endfor %}
    </div>
    <div class="lbl">Content</div>
    {% for s in doc.sections %}{% if s.type != 'para' %}
    <div class="f"><label>{{ s.label }}</label>
      {% if s.type == 'lines' %}<input name="{{ s.name }}">{% else %}<textarea name="{{ s.name }}" placeholder="{{ s.hint }}"></textarea>{% endif %}
    </div>{% endif %}{% endfor %}
    <button class="btn" type="submit">Generate document</button>
  </form>
  {% if error %}<div class="msg err">{{ error }}</div>{% endif %}
</div>
<script>
const AI_KEY = "{{ doc.key }}";
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let aiRec=null, aiListening=false, aiFinal="";
function aiConsentOk(){ if(!document.getElementById('aiConsent').checked){ alert('Please confirm the employee has been informed before recording.'); return false; } return true; }
function aiUpd(){ const b=document.getElementById('aiRecBtn'), s=document.getElementById('aiRecStatus');
  if(aiListening){ b.innerHTML='&#9632; Stop'; b.classList.add('rec-on'); s.textContent='Recording\\u2026 speak naturally'; }
  else { b.innerHTML='&#9679; Record'; b.classList.remove('rec-on'); s.textContent='Not recording'; } }
function aiToggleRec(){
  if(!SR){ alert('Voice capture needs Chrome or Edge. You can type or paste notes instead.'); return; }
  if(aiListening){ aiRec.stop(); return; }
  if(!aiConsentOk()) return;
  aiRec=new SR(); aiRec.continuous=true; aiRec.interimResults=true; aiRec.lang='en-NZ';
  const ta=document.getElementById('aiTranscript'); aiFinal = ta.value ? ta.value.trim()+' ' : '';
  aiRec.onresult=(e)=>{ let interim=''; for(let i=e.resultIndex;i<e.results.length;i++){ const t=e.results[i][0].transcript; if(e.results[i].isFinal) aiFinal+=t+' '; else interim+=t; } ta.value=aiFinal+interim; };
  aiRec.onend=()=>{ aiListening=false; aiUpd(); };
  aiRec.onerror=(e)=>{ aiListening=false; aiUpd(); if(e.error!=='no-speech' && e.error!=='aborted') document.getElementById('aiRecStatus').textContent='Mic issue: '+e.error; };
  aiRec.start(); aiListening=true; aiUpd();
}
function aiEsc(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
async function aiDraft(){
  if(!aiConsentOk()) return;
  const ta=document.getElementById('aiTranscript'); if(!ta.value.trim()){ alert('Record or type the meeting first.'); return; }
  const btn=document.getElementById('aiDraftBtn'); btn.disabled=true; btn.textContent='Drafting\\u2026';
  const emp=(document.querySelector('[name=employee]')||{}).value||'';
  const role=(document.querySelector('[name=role]')||{}).value||'';
  let data;
  try{ const r=await fetch('/ai/meeting-notes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:AI_KEY,transcript:ta.value,employee:emp,role:role})}); data=await r.json(); }
  catch(err){ data={error:'Network error: '+err}; }
  btn.disabled=false; btn.textContent='Draft notes + compliance check';
  const res=document.getElementById('aiResult'); res.style.display='block';
  if(data.error){ res.innerHTML='<div class="ai-err">'+aiEsc(data.error)+'</div>'; return; }
  for(const k in (data.fields||{})){ const el=document.querySelector('[name="'+k+'"]'); if(el && data.fields[k]) el.value=data.fields[k]; }
  let html='<div class="ai-done">&#10003; Draft filled into the fields below &mdash; please review and edit.</div>';
  if(data.summary) html+='<div class="ai-summary">'+aiEsc(data.summary)+'</div>';
  const flags=data.flags||[];
  if(flags.length){ html+='<div class="ai-flags-h">Employment-law process check</div>';
    for(const f of flags){ const sev=(f.severity||'info'); html+='<div class="ai-flag '+sev+'"><div class="ai-flag-t">'+aiEsc(f.issue||'')+'</div><div class="ai-flag-s">'+aiEsc(f.suggestion||'')+'</div></div>'; } }
  else { html+='<div class="ai-flag info"><div class="ai-flag-t">No obvious process issues flagged.</div></div>'; }
  if(data.disclaimer) html+='<div class="ai-disc">'+aiEsc(data.disclaimer)+'</div>';
  res.innerHTML=html;
}
</script>
</body></html>"""

# ---- AI meeting assistant (transcript -> structured notes + NZ-law check) --
_AI_SYSTEM = """You are an HR documentation assistant for Browne St., a café in Auckland, New Zealand (legal entity Pulse 2012 Ltd). You turn a manager's rough notes or a meeting transcript into a clear, professional, factual written record, and you flag possible New Zealand employment-law process issues.

You are NOT a lawyer and must NOT give definitive legal advice. Frame every compliance point as something to check, and recommend seeking advice from an employment adviser or Employment New Zealand for anything serious.

Check the process against New Zealand fair-process principles (Employment Relations Act 2000):
- Good faith (s4): parties are responsive, communicative, and do not mislead.
- The "fair and reasonable employer" test (s103A): was this a process a fair and reasonable employer could have followed?
- Procedural fairness in a disciplinary/investigation meeting: a genuine concern clearly put to the employee; a real opportunity for them to respond and be heard; their explanation genuinely considered with an open mind (no predetermined outcome); the right to be supported or represented (a support person); reasonable notice and timeframes; confidentiality.

Write in New Zealand English — plain, factual, neutral. Never invent facts that are not in the notes; if a field is not covered, return an empty string for it rather than fabricating.

Return ONLY a JSON object (no markdown, no preamble) of exactly this shape:
{
  "fields": { "<field_name>": "<text drawn from the notes>", ... },
  "summary": "<one or two neutral sentences>",
  "flags": [ { "issue": "<short process concern>", "severity": "info|caution|serious", "suggestion": "<what to check or do>" } ],
  "disclaimer": "<one sentence reminding this is guidance, not legal advice>"
}
"""

def _extract_json(text):
    import json, re
    if not text:
        return None
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n?", "", t)
        t = re.sub(r"\n?```$", "", t).strip()
    try:
        return json.loads(t)
    except Exception:
        pass
    i, j = t.find("{"), t.rfind("}")
    if i != -1 and j > i:
        try:
            return json.loads(t[i:j+1])
        except Exception:
            return None
    return None

def _ai_meeting_notes(key, transcript, employee="", role=""):
    if not (transcript or "").strip():
        return {"error": "Nothing to analyse yet — record or type the meeting first."}
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return {"error": "AI notes need an Anthropic API key. Add ANTHROPIC_API_KEY in Railway → Variables, then redeploy."}
    doc = HR_BY_KEY.get(key)
    if not doc:
        return {"error": "Unknown document type."}
    try:
        import anthropic
    except Exception:
        return {"error": "The 'anthropic' package isn't installed on the server yet (redeploy after adding it)."}
    fields = [(s["name"], s.get("label", s["name"])) for s in doc["sections"] if s.get("type") in ("long", "lines")]
    field_lines = "\n".join(f"  - {name}: {label}" for name, label in fields)
    user = (f"Document type: {doc['title']}\n"
            f"Staff member: {employee or '(unnamed)'}" + (f", role {role}" if role else "") + "\n\n"
            f"Fill these fields from the notes (empty string if not covered — never invent facts):\n{field_lines}\n\n"
            f"Meeting notes / transcript:\n\"\"\"\n{transcript.strip()}\n\"\"\"\n\nReturn only the JSON object.")
    try:
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-opus-4-8", max_tokens=6000,
            thinking={"type": "disabled"}, system=_AI_SYSTEM,
            messages=[{"role": "user", "content": user}],
        )
    except Exception as e:
        return {"error": f"AI request failed: {e}"}
    text = "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", None) == "text")
    data = _extract_json(text)
    if data is None:
        return {"error": "Couldn't parse the AI response — please try again."}
    known = {name for name, _ in fields}
    data["fields"] = {k: v for k, v in (data.get("fields") or {}).items() if k in known}
    return data

@app.route("/ai/meeting-notes", methods=["POST"])
def ai_meeting_notes():
    from flask import jsonify
    d = request.get_json(silent=True) or {}
    return jsonify(_ai_meeting_notes(d.get("key", ""), d.get("transcript", ""),
                                     d.get("employee", ""), d.get("role", "")))

@app.route("/hr/<key>", methods=["GET"])
def hr_form(key):
    doc = HR_BY_KEY.get(key)
    if not doc:
        return "Unknown document.", 404
    staff = store.get_staff(request.args.get("staff",""))
    prefill = {"employee": staff["full_name"], "role": staff.get("role","")} if staff else {}
    return render_template_string(_HR_TMPL, doc=doc, error=None, prefill=prefill, **_staff_ctx(staff))

@app.route("/generate-hr", methods=["POST"])
def generate_hr():
    key = request.form.get("_key", "")
    doc = HR_BY_KEY.get(key)
    if not doc:
        return "Unknown document.", 404
    try:
        data = {k: v.strip() for k, v in request.form.items() if k not in ("_key", "staff_id")}
        pdf = generate_hr_pdf(key, data).read()
        who = (data.get("employee") or "").strip()
        fname = f"{key}{('-' + who.replace(' ', '-')) if who else ''}.pdf"
        sid = _maybe_file_to_staff(pdf, fname, key)
        if sid:
            return redirect(f"/staff/{sid}")
        token = _store_pdf(pdf, fname)
        sub = (f"<span class='name'>{doc['title']}</span> for {who} is ready." if who
               else f"<span class='name'>{doc['title']}</span> (blank template) is ready.")
        return _ready_page(f"{doc['title']} ready", sub, token)
    except Exception as e:
        import traceback
        return render_template_string(_HR_TMPL, doc=doc, error=str(e) + " | " + traceback.format_exc()[-300:], prefill={}, staff_control="")

# Store generated PDF in memory keyed by a token
_pdf_store = {}

def _store_pdf(pdf_bytes, filename):
    import uuid
    token = str(uuid.uuid4())
    _pdf_store[token] = {"pdf": pdf_bytes, "filename": filename}
    if len(_pdf_store) > 20:
        del _pdf_store[next(iter(_pdf_store))]
    return token

def _ready_page(heading, sub_html, token):
    return """<!DOCTYPE html><html><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ready</title><style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#F7F4EC;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:2rem 1rem}
.card{background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.08);max-width:420px;width:100%;padding:2rem;text-align:center}
.top-bar{height:4px;background:#FE5000;border-radius:12px 12px 0 0;margin:-2rem -2rem 2rem}
.icon{width:64px;height:64px;background:#EAF3DE;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 1.5rem;font-size:28px}
h2{font-size:20px;font-weight:600;color:#16120D;margin-bottom:8px}
.sub{font-size:14px;color:#5F574A;margin-bottom:2rem;line-height:1.5}
.name{font-weight:600;color:#16120D}
.dl-btn{display:block;width:100%;padding:16px;background:#FE5000;color:#fff;text-decoration:none;border-radius:10px;font-size:17px;font-weight:600;margin-bottom:12px}
.dl-btn:active{opacity:.85}
.back{display:block;font-size:14px;color:#8C7F6B;text-decoration:none;margin-top:16px}
.tip{margin-top:1.5rem;padding:12px 14px;background:#F3EEE3;border-radius:8px;font-size:12px;color:#8C7F6B;line-height:1.7;text-align:left}
.tip strong{color:#3B342A}
</style></head><body>
<div class="card">
  <div class="top-bar"></div>
  <div class="icon">&#10003;</div>
  <h2>""" + heading + """</h2>
  <p class="sub">""" + sub_html + """</p>
  <a href="/download/""" + token + """" class="dl-btn">&#8595; Download PDF</a>
  <div class="tip"><strong>On iPhone:</strong> Tap Download PDF &mdash; it will appear in <strong>Files &rarr; Downloads</strong>.</div>
  <a href="/" class="back">&#8592; Back to all documents</a>
</div></body></html>"""

@app.route("/download/<token>")
def download(token):
    if token not in _pdf_store:
        return "File not found or expired.", 404
    data = _pdf_store[token]
    fname = data["filename"]
    from flask import Response
    response = Response(
        data["pdf"],
        mimetype="application/octet-stream",
        headers={
            "Content-Disposition": "attachment; filename=" + fname,
            "Content-Length": str(len(data["pdf"])),
            "X-Content-Type-Options": "nosniff",
        }
    )
    return response

@app.route("/generate", methods=["POST"])
def generate():
    try:
        docx_bytes, first_name, start_fmt, emp_type, sig_data = make_docx(request.form)
        full_name = request.form.get("fullName","").strip()
        role      = request.form.get("role","").strip()
        combined  = generate_pdf(docx_bytes, full_name, role, start_fmt, emp_type, sig_data)
        filename  = f"{first_name}_Onboarding_Pack.pdf"

        # Store PDF with a simple token
        import uuid
        token = str(uuid.uuid4())
        pdf_all = combined.read()
        _pdf_store[token] = {"pdf": pdf_all, "filename": filename}
        # Keep store small — remove old entries if more than 20
        if len(_pdf_store) > 20:
            oldest = next(iter(_pdf_store))
            del _pdf_store[oldest]

        # If generating for a staff member, file the pack into their folder
        if _maybe_file_to_staff(pdf_all, filename, "onboarding"):
            return redirect(f"/staff/{request.form.get('staff_id')}")

        # Send email via Resend if API key is configured
        resend_key = os.environ.get("RESEND_API_KEY", "")
        if resend_key:
            try:
                import urllib.request, json
                pdf_bytes = _pdf_store[token]["pdf"]
                combined = io.BytesIO(pdf_bytes)  # reset for email
                email_payload = {
                    "from": "Browne St. Onboarding <onboarding@brownestreet.co.nz>",
                    "to": ["sam@brownestreet.co.nz"],
                    "subject": f"Onboarding pack — {full_name}",
                    "html": f"""
                        <div style="font-family:-apple-system,sans-serif;max-width:600px;margin:0 auto">
                          <div style="background:#FE5000;height:4px;border-radius:4px 4px 0 0"></div>
                          <div style="padding:2rem;background:#fff;border:1px solid #EDE5D6;border-top:none">
                            <img src="https://web-production-60f95.up.railway.app/logo" width="60" style="margin-bottom:1rem">
                            <h2 style="color:#16120D;margin:0 0 0.5rem">New onboarding pack ready</h2>
                            <p style="color:#5F574A;margin:0 0 1.5rem">The onboarding pack for <strong>{full_name}</strong> has been generated and is attached to this email.</p>
                            <table style="width:100%;border-collapse:collapse;font-size:14px">
                              <tr><td style="padding:8px 0;color:#8C7F6B;border-bottom:1px solid #EDE5D6">Employee</td><td style="padding:8px 0;font-weight:600;border-bottom:1px solid #EDE5D6">{full_name}</td></tr>
                              <tr><td style="padding:8px 0;color:#8C7F6B;border-bottom:1px solid #EDE5D6">Role</td><td style="padding:8px 0;font-weight:600;border-bottom:1px solid #EDE5D6">{role}</td></tr>
                              <tr><td style="padding:8px 0;color:#8C7F6B;border-bottom:1px solid #EDE5D6">Start date</td><td style="padding:8px 0;font-weight:600;border-bottom:1px solid #EDE5D6">{start_fmt}</td></tr>
                              <tr><td style="padding:8px 0;color:#8C7F6B">Employment type</td><td style="padding:8px 0;font-weight:600">{emp_type.title()}</td></tr>
                            </table>
                            <p style="color:#B8AD97;font-size:12px;margin:1.5rem 0 0">Browne St. — Pulse 2012 Ltd &bull; 50 Rosebank Rd, Avondale, Auckland 1026</p>
                          </div>
                        </div>
                    """,
                    "attachments": [{
                        "filename": filename,
                        "content": __import__("base64").b64encode(pdf_bytes).decode()
                    }]
                }
                req = urllib.request.Request(
                    "https://api.resend.com/emails",
                    data=json.dumps(email_payload).encode(),
                    headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
                    method="POST"
                )
                urllib.request.urlopen(req, timeout=10)
            except Exception as email_err:
                # Email failure shouldn't block the download
                print(f"Email error: {email_err}")

        # Return a page that auto-downloads the PDF immediately
        ready_html = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pack Ready</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#F7F4EC;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:2rem 1rem}
.card{background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.08);max-width:420px;width:100%;padding:2rem;text-align:center}
.top-bar{height:4px;background:#FE5000;border-radius:12px 12px 0 0;margin:-2rem -2rem 2rem}
.icon{width:64px;height:64px;background:#EAF3DE;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 1.5rem;font-size:28px}
h2{font-size:20px;font-weight:600;color:#16120D;margin-bottom:8px}
.sub{font-size:14px;color:#5F574A;margin-bottom:2rem;line-height:1.5}
.name{font-weight:600;color:#16120D}
.dl-btn{display:block;width:100%;padding:16px;background:#FE5000;color:#fff;text-decoration:none;border-radius:10px;font-size:17px;font-weight:600;margin-bottom:12px}
.dl-btn:active{opacity:.85}
.back{display:block;font-size:14px;color:#8C7F6B;text-decoration:none;margin-top:16px}
.tip{margin-top:1.5rem;padding:12px 14px;background:#F3EEE3;border-radius:8px;font-size:12px;color:#8C7F6B;line-height:1.7;text-align:left}
.tip strong{color:#3B342A}
</style>
</head>
<body>
<div class="card">
  <div class="top-bar"></div>
  <div class="icon">&#10003;</div>
  <h2>Pack ready!</h2>
  <p class="sub">Onboarding pack for <span class="name">""" + full_name + """</span> is ready.</p>
  <a href="/download/""" + token + """" class="dl-btn">&#8595; Download PDF</a>
  <div class="tip">
    <strong>On iPhone:</strong> Tap Download PDF &mdash; your browser will ask where to save it, or it will appear automatically in <strong>Files &rarr; Downloads</strong>.
  </div>
  <a href="/" class="back">&#8592; Generate another pack</a>
</div>
</body>
</html>"""
        return ready_html
    except Exception as e:
        import traceback
        return _render_form(error=str(e)+" | "+traceback.format_exc()[-400:])

@app.route("/generate-contract", methods=["POST"])
def generate_contract():
    try:
        docx_bytes, first_name, start_fmt, emp_type, sig_data = make_docx(request.form)
        full_name = request.form.get("fullName","").strip()
        role      = request.form.get("role","").strip()
        combined  = generate_pdf(docx_bytes, full_name, role, start_fmt, emp_type, sig_data,
                                 include_jd=False, include_hs=False, include_govt=False)
        fname = f"{first_name}_Employment_Agreement.pdf"
        pdf_all = combined.read()
        if _maybe_file_to_staff(pdf_all, fname, "contract"):
            return redirect(f"/staff/{request.form.get('staff_id')}")
        token = _store_pdf(pdf_all, fname)
        return _ready_page("Agreement ready", f"Employment agreement for <span class='name'>{full_name}</span> is ready.", token)
    except Exception as e:
        import traceback
        return _render_form(page_title="Employment agreement",
                            page_sub="Generate a standalone, personalised agreement (offer letter + individual employment agreement).",
                            action="/generate-contract", submit_label="Generate agreement", show_pack=False,
                            error=str(e)+" | "+traceback.format_exc()[-400:])

# ===========================================================================
# Staff records — directory, profiles, uploads, certifications
# ===========================================================================
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200MB (allows full backup restore)

_STAFF_CSS = """
.bar{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:6px}
.badge{display:inline-flex;align-items:center;font-size:10.5px;font-weight:600;padding:3px 10px;border-radius:20px;letter-spacing:.03em;text-transform:capitalize}
.badge.active{background:var(--green-bg,#E7F0E1);color:#2E6B33}
.badge.left{background:#EDE5D6;color:#8C7F6B}
.badge.leave{background:#FBEAD3;color:#9A6B12}
.stitem{display:flex;align-items:center;gap:13px;padding:14px 16px;border:1px solid var(--line);border-radius:14px;text-decoration:none;margin-bottom:9px;background:var(--surface);transition:border var(--ease),box-shadow var(--ease),transform var(--ease)}
.stitem:hover{border-color:var(--orange-soft);box-shadow:0 14px 30px -20px rgba(22,18,13,.4);transform:translateY(-1px)}
.av{width:40px;height:40px;border-radius:50%;background:var(--orange-tint);color:var(--orange);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;flex-shrink:0;border:1px solid var(--orange-soft);letter-spacing:.02em}
.stitem .nm{font-weight:600;color:var(--ink);font-size:14.5px;letter-spacing:-.01em}
.stitem .ro{font-size:12.5px;color:var(--muted);margin-top:1px}
.meta{font-size:12px;color:var(--faint)}
.doc-row{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px 0;border-bottom:1px solid var(--line)}
.doc-row:last-child{border-bottom:none}
.doc-row:first-child{padding-top:2px}
.dk{font-size:10px;font-weight:600;color:var(--orange);text-transform:uppercase;letter-spacing:.08em}
.dt{font-size:13.5px;color:var(--ink);font-weight:550;margin-top:2px}
.mini{display:inline-flex;align-items:center;gap:5px;font-size:12px;font-weight:550;color:var(--ink-soft);text-decoration:none;border:1px solid var(--line-2);border-radius:9px;padding:7px 12px;background:var(--surface);cursor:pointer;font-family:inherit;transition:all var(--ease)}
.mini:hover{border-color:var(--orange);color:var(--orange);background:var(--orange-tint)}
.mini svg{width:14px;height:14px}
.mini.danger:hover{border-color:#C6402B;color:#C6402B;background:#FCEBE7}
.mini.solid{background:var(--ink);color:#fff;border-color:var(--ink)}
.mini.solid:hover{background:#000;color:#fff}
.gen-grid{display:grid;grid-template-columns:1fr 1fr;gap:9px}
.gen{display:flex;align-items:center;gap:10px;padding:12px 13px;border:1px solid var(--line-2);border-radius:12px;text-decoration:none;color:var(--ink);font-size:13px;font-weight:550;background:var(--surface-2);transition:all var(--ease)}
.gen:hover{border-color:var(--orange-soft);background:var(--orange-tint);color:var(--orange-ink);transform:translateY(-1px)}
.gen .gi{width:30px;height:30px;border-radius:9px;background:var(--surface);border:1px solid var(--line);display:flex;align-items:center;justify-content:center;color:var(--orange);flex-shrink:0}
.gen .gi svg{width:17px;height:17px}
.sec-card{border:1px solid var(--line);border-radius:15px;padding:18px 19px;margin-top:15px;background:var(--surface)}
.sec-card h3{font-size:12px;font-weight:700;color:var(--ink);margin-bottom:14px;letter-spacing:.02em;text-transform:uppercase}
.sec-card h3 .ct{color:var(--faint);font-weight:600}
.warn-cert{background:#FFF3E9;border:1px solid #F1C79A;border-radius:13px;padding:13px 15px;font-size:12.5px;color:#8A4B08;margin-bottom:16px;line-height:1.65}
.warn-cert .wh{display:flex;align-items:center;gap:8px;font-weight:700;margin-bottom:4px}
.warn-cert .wh svg{width:16px;height:16px}
details.arch{margin-top:16px}
details.arch>summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:9px;padding:13px 16px;border:1px solid var(--line);border-radius:14px;background:var(--surface-2);font-size:13.5px;font-weight:600;color:var(--ink-soft);transition:all var(--ease)}
details.arch>summary::-webkit-details-marker{display:none}
details.arch>summary:hover{border-color:var(--orange-soft);color:var(--orange-ink)}
details.arch>summary .ct{color:var(--faint);font-weight:600}
details.arch>summary .chevi{margin-left:auto;display:flex;color:var(--faint);transition:transform var(--ease)}
details.arch[open]>summary .chevi{transform:rotate(90deg)}
details.arch[open]>summary{margin-bottom:10px;border-color:var(--line-2)}
.dgrid{display:grid;grid-template-columns:1fr 1fr;gap:2px 24px}
.drow{display:flex;justify-content:space-between;gap:12px;padding:9px 0;border-bottom:1px solid var(--line);font-size:13px}
.drow.full{grid-column:1 / -1}
.drow .dl{color:var(--muted)}
.drow .dv{color:var(--ink);font-weight:550;text-align:right}
@media(max-width:520px){.gen-grid,.dgrid{grid-template-columns:1fr}}
"""

def _page(body, title="Browne St. HR", extra_css=""):
    return ("""<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>""" + title +
    """</title><style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');""" + _BASE_CSS + _STAFF_CSS + extra_css + """</style></head><body>
<div class="card">""" + body + """</div></body></html>""")

_KIND_LABEL = {"onboarding":"Onboarding pack","contract":"Employment agreement","job-description":"Job description",
               "written-warning":"Written warning","investigation":"Investigation record",
               "informal-discussion":"Informal discussion","certification":"Certification","other":"Document"}

def _esc(t):
    return (t or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def _maybe_file_to_staff(pdf_bytes, filename, kind):
    """If the form carried a staff_id, save the generated PDF into that folder.
    Returns the staff id if filed, else None."""
    sid = (request.form.get("staff_id") or "").strip()
    if sid and store.get_staff(sid):
        store.save_file(sid, pdf_bytes, filename, kind=kind, title=filename, source="generated")
        return sid
    return None

def _staff_control(staff):
    """The staff-filing control shown on every document form.
    - If a staff member is preset (form opened from their profile): a banner + hidden field.
    - Otherwise: a dropdown to optionally file the document into someone's folder."""
    if staff:
        return (f'<div class="note filing">'
                f'<span class="ntx">Filing into <strong>{_esc(staff["full_name"])}\'s</strong> folder — '
                f'the finished PDF will be saved to their records.</span>'
                f'<a class="ntx-cancel" href="/staff/{staff["id"]}">Cancel</a></div>'
                f'<input type="hidden" name="staff_id" value="{staff["id"]}">')
    people = store.list_staff(include_left=False)
    if not people:
        return '<input type="hidden" name="staff_id" value="">'
    opts = '<option value="">— Just download (don\'t save to a file) —</option>' + "".join(
        f'<option value="{p["id"]}">{_esc(p["full_name"])}{(" · " + _esc(p["role"])) if p["role"] else ""}</option>'
        for p in people)
    return (f'<div class="f"><label>Save under staff member</label><select name="staff_id">{opts}</select>'
            f'<div class="hint">Pick a team member to file this document into their folder, or leave as &ldquo;just download&rdquo;.</div></div>')

def _staff_ctx(staff):
    """Template context — the filing control for a document form."""
    return {"staff_control": _staff_control(staff)}

# --- auth ------------------------------------------------------------------
@app.route("/login", methods=["GET","POST"])
def login():
    err = ""
    if request.method == "POST":
        if request.form.get("password","") == HR_PASSWORD:
            session["auth"] = True
            nxt = request.args.get("next") or "/"
            return redirect(nxt if nxt.startswith("/") else "/")
        err = "Incorrect password."
    body = """
  <div class="mast">
    <img src="/brand/logo-wordmark.svg" alt="Browne St.">
    <span class="tag">HR &amp; Onboarding</span>
  </div>
  <div style="width:46px;height:46px;border-radius:13px;background:var(--orange-tint);border:1px solid var(--orange-soft);color:var(--orange);display:flex;align-items:center;justify-content:center;margin-bottom:16px">""" + _ic("shield", 24) + """</div>
  <h1>Staff &amp; HR</h1>
  <p class="sub">This area holds staff records and HR documents. Enter the password to continue.</p>
  <form method="POST">
    <div class="f"><label>Password</label><input type="password" name="password" autofocus></div>
    <button class="btn" type="submit">Sign in</button>
  </form>""" + ('<div class="msg err">'+err+'</div>' if err else '')
    return _page(body, "Sign in — Browne St. HR")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# --- staff directory -------------------------------------------------------
@app.route("/staff")
def staff_list():
    people = store.list_staff()
    alerts = store.attention()
    rows = ""
    if alerts:
        def _when(a):
            if a["days_left"] < 0:  return f'expired {abs(a["days_left"])} days ago'
            if a["days_left"] == 0: return 'due today'
            return f'in {a["days_left"]} days'
        items = "".join(
            f'<div><a href="/staff/{a["staff_id"]}" style="color:inherit;text-decoration:underline">{_esc(a["full_name"])}</a>'
            f' &mdash; {_esc(a["label"])}: {_when(a)} ({_esc(a["date"])})</div>' for a in alerts)
        rows += f'<div class="warn-cert"><div class="wh">{_ic("alert",16)} Needs attention</div>{items}</div>'

    def render_row(p):
        initials = "".join(w[0] for w in (p["full_name"] or "?").split()[:2]).upper()
        st = p["status"] or "active"; badge = {"active":"active","left":"left","on-leave":"leave"}.get(st,"active")
        label = "Archived" if st == "left" else st
        return (f'<a class="stitem" href="/staff/{p["id"]}">'
                f'<div class="av">{_esc(initials)}</div>'
                f'<div style="flex:1;min-width:0"><div class="nm">{_esc(p["full_name"])}</div>'
                f'<div class="ro">{_esc(p["role"] or "—")}</div></div>'
                f'<span class="badge {badge}">{_esc(label)}</span>{_CHEV}</a>')

    active   = [p for p in people if (p["status"] or "active") != "left"]
    archived = [p for p in people if (p["status"] or "active") == "left"]

    if not people:
        rows += '<p class="meta" style="padding:8px 2px">No staff yet — add your first team member above.</p>'
    rows += '<div class="docs">' + "".join(render_row(p) for p in active) + '</div>'
    if archived:
        arch_rows = "".join(render_row(p) for p in archived)
        rows += (f'<details class="arch"><summary>{_ic("archive",16)} Archived staff '
                 f'<span class="ct">· {len(archived)}</span><span class="chevi">{_ic("chevron",17)}</span></summary>'
                 f'<div class="docs">{arch_rows}</div></details>')

    body = f"""
  <a class="back" href="/">{_ic("arrow-left",15)} All documents</a>
  <div class="bar"><h1 style="margin:0">Staff</h1><a class="mini solid" href="/staff/new">{_ic("plus",14)} Add staff</a></div>
  <p class="sub">Each person's folder holds their contracts, records, warnings and certifications.</p>
  {rows}
  <div class="foot"><span>{len(active)} current &middot; {len(archived)} archived</span><span><a href="/settings">Settings &amp; backup</a> &middot; <a href="/logout">Sign out</a></span></div>"""
    return _page(body, "Staff — Browne St. HR")

def _staff_form_page(staff=None, error=""):
    v = lambda k: _esc((staff or {}).get(k, ""))
    heading = "Edit staff member" if staff else "Add staff member"
    action = f"/staff/{staff['id']}/edit" if staff else "/staff/new"
    def sel(field, val, label):
        s = " selected" if (staff or {}).get(field) == val else ""
        return f'<option value="{val}"{s}>{label}</option>'
    body = f"""
  <a class="back" href="{('/staff/'+staff['id']) if staff else '/staff'}">{_ic("arrow-left",15)} Back</a>
  <h1>{heading}</h1>
  <form method="POST" action="{action}">
    <div class="lbl">Person</div>
    <div class="f"><label>Full name</label><input name="full_name" value="{v('full_name')}" required></div>
    <div class="row">
      <div class="f"><label>Preferred name</label><input name="preferred_name" value="{v('preferred_name')}"></div>
      <div class="f"><label>Pronouns</label><select name="pronouns">
        {sel('pronouns','they','They / them')}{sel('pronouns','she','She / her')}{sel('pronouns','he','He / him')}
      </select></div>
    </div>
    <div class="row">
      <div class="f"><label>Email</label><input name="email" type="email" value="{v('email')}"></div>
      <div class="f"><label>Phone</label><input name="phone" value="{v('phone')}"></div>
    </div>
    <div class="f"><label>Street address</label><input name="address" value="{v('address')}"></div>
    <div class="row">
      <div class="f"><label>Suburb</label><input name="suburb" value="{v('suburb')}"></div>
      <div class="f"><label>City &amp; postcode</label><input name="citypost" value="{v('citypost')}"></div>
    </div>
    <div class="lbl">Role &amp; employment</div>
    <div class="row">
      <div class="f"><label>Role</label><input name="role" value="{v('role')}" placeholder="e.g. Barista"></div>
      <div class="f"><label>Hourly rate ($)</label><input name="pay_rate" value="{v('pay_rate')}" placeholder="e.g. 28.00"></div>
    </div>
    <div class="row">
      <div class="f"><label>Employment type</label><select name="emp_type">
        {sel('emp_type','part-time','Part-time')}{sel('emp_type','full-time','Full-time')}{sel('emp_type','casual','Casual')}
      </select></div>
      <div class="f"><label>Start date</label><input name="start_date" type="date" value="{v('start_date')}"></div>
    </div>
    <div class="row">
      <div class="f"><label>Status</label><select name="status">
        {sel('status','active','Active')}{sel('status','on-leave','On leave')}{sel('status','left','Left')}
      </select></div>
      <div class="f"><label>90-day trial ends</label><input name="trial_end" type="date" value="{v('trial_end')}"></div>
    </div>
    <div class="lbl">Work eligibility</div>
    <div class="row">
      <div class="f"><label>Visa / work status</label><input name="visa_status" value="{v('visa_status')}" placeholder="e.g. Citizen, Resident, Work Visa"></div>
      <div class="f"><label>Visa expiry <span style="color:var(--faint);font-weight:400">(if applicable)</span></label><input name="visa_expiry" type="date" value="{v('visa_expiry')}"></div>
    </div>
    <div class="f"><label>Notes</label><textarea name="notes">{v('notes')}</textarea></div>
    <button class="btn" type="submit">{'Save changes' if staff else 'Add staff member'}</button>
  </form>""" + (f'<div class="msg err">{error}</div>' if error else '')
    return _page(body, heading + " — Browne St. HR")

@app.route("/staff/new", methods=["GET","POST"])
def staff_new():
    if request.method == "POST":
        sid = store.add_staff(request.form)
        return redirect(f"/staff/{sid}")
    return _staff_form_page()

@app.route("/staff/<sid>/edit", methods=["GET","POST"])
def staff_edit(sid):
    staff = store.get_staff(sid)
    if not staff: abort(404)
    if request.method == "POST":
        store.update_staff(sid, request.form)
        return redirect(f"/staff/{sid}")
    return _staff_form_page(staff)

@app.route("/staff/<sid>/delete", methods=["POST"])
def staff_delete(sid):
    store.delete_staff(sid)
    return redirect("/staff")

@app.route("/staff/<sid>")
def staff_profile(sid):
    staff = store.get_staff(sid)
    if not staff: abort(404)
    docs = store.list_documents(sid)
    certs = store.list_certifications(sid)
    initials = "".join(w[0] for w in (staff["full_name"] or "?").split()[:2]).upper()
    st = staff["status"] or "active"; badge = {"active":"active","left":"left","on-leave":"leave"}.get(st,"active")

    # Details panel — only fields that have values
    def _fmt_date(d):
        try:
            return datetime.strptime(d, "%Y-%m-%d").strftime("%-d %B %Y")
        except Exception:
            return d
    def _date_days(d):
        try:
            dt = datetime.strptime(d, "%Y-%m-%d").date()
            days = (dt - datetime.today().date()).days
            base = dt.strftime("%-d %B %Y")
            if days < 0:   return f"{base} · expired {abs(days)}d ago"
            if days <= 60: return f"{base} · in {days}d"
            return base
        except Exception:
            return d
    drows_d = []
    if staff.get("emp_type"):    drows_d.append(("Employment", staff["emp_type"].title()))
    if staff.get("pay_rate"):    drows_d.append(("Starting rate", f"${staff['pay_rate']} / hr"))
    if staff.get("start_date"):  drows_d.append(("Start date", _fmt_date(staff["start_date"])))
    if staff.get("trial_end"):   drows_d.append(("90-day trial ends", _date_days(staff["trial_end"])))
    if staff.get("pronouns"):    drows_d.append(("Pronouns", staff["pronouns"]))
    if staff.get("email"):       drows_d.append(("Email", staff["email"]))
    if staff.get("phone"):       drows_d.append(("Phone", staff["phone"]))
    if staff.get("visa_status"): drows_d.append(("Work status", staff["visa_status"]))
    if staff.get("visa_expiry"): drows_d.append(("Visa expiry", _date_days(staff["visa_expiry"])))
    _addr = ", ".join(x for x in [staff.get("address"), staff.get("suburb"), staff.get("citypost")] if x)
    details_html = ""
    if drows_d or _addr or staff.get("notes"):
        cells = "".join(f'<div class="drow"><span class="dl">{_esc(l)}</span><span class="dv">{_esc(v)}</span></div>' for l, v in drows_d)
        grid = f'<div class="dgrid">{cells}</div>' if cells else ""
        extra = ""
        if _addr:
            extra += f'<div class="drow full"><span class="dl">Address</span><span class="dv">{_esc(_addr)}</span></div>'
        if staff.get("notes"):
            extra += f'<div class="drow full"><span class="dl">Notes</span><span class="dv">{_esc(staff["notes"])}</span></div>'
        details_html = f'<div class="sec-card"><h3>Details</h3>{grid}{extra}</div>'

    gen = "".join(f'<a class="gen" href="{href}?staff={sid}"><span class="gi">{_ic(icon,17)}</span>{label}</a>' for href,icon,label in [
        ("/onboarding","box","Onboarding pack"), ("/contract","agreement","Employment agreement"),
        ("/job-description","jd","Job description"), ("/hr/informal-discussion","chat","Informal discussion"),
        ("/hr/investigation","search","Investigation record"), ("/hr/written-warning","alert","Written warning"),
    ])

    if docs:
        drows = ""
        for d in docs:
            drows += (f'<div class="doc-row"><div><div class="dk">{_esc(_KIND_LABEL.get(d["kind"],"Document"))}'
                      f'{" · uploaded" if d["source"]=="upload" else ""}</div>'
                      f'<div class="dt">{_esc(d["title"])}</div>'
                      f'<div class="meta">{_esc(d["created_at"][:10])}</div></div>'
                      f'<div style="display:flex;gap:6px">'
                      f'<a class="mini" href="/staff/doc/{d["id"]}">{_ic("download",14)} Download</a>'
                      f'<form method="POST" action="/staff/doc/{d["id"]}/delete" onsubmit="return confirm(\'Delete this document?\')" style="margin:0">'
                      f'<button class="mini danger" type="submit">{_ic("trash",14)} Delete</button></form></div></div>')
    else:
        drows = '<p class="meta">No documents yet. Generate one above, or upload a file.</p>'

    if certs:
        crows = ""
        for c in certs:
            exp = f' · expires {_esc(c["expires"])}' if c["expires"] else ""
            crows += (f'<div class="doc-row"><div><div class="dt">{_esc(c["name"])}</div>'
                      f'<div class="meta">{_esc(c["issued"] or "")}{exp}</div></div>'
                      f'<form method="POST" action="/staff/cert/{c["id"]}/delete" style="margin:0">'
                      f'<button class="mini danger" type="submit">{_ic("trash",14)} Remove</button></form></div>')
    else:
        crows = '<p class="meta">No certifications recorded.</p>'

    body = f"""
  <a class="back" href="/staff">{_ic("arrow-left",15)} All staff</a>
  <div class="bar">
    <div style="display:flex;align-items:center;gap:13px;min-width:0">
      <div class="av" style="width:48px;height:48px;font-size:16px">{_esc(initials)}</div>
      <div style="min-width:0"><h1 style="margin:0;font-size:22px">{_esc(staff['full_name'])}</h1>
      <div class="ro" style="display:flex;align-items:center;gap:8px;margin-top:3px">{_esc(staff['role'] or '—')} <span class="badge {badge}">{_esc(st)}</span></div></div>
    </div>
    <a class="mini" href="/staff/{sid}/edit">{_ic("edit",14)} Edit</a>
  </div>
  {details_html}
  <div class="sec-card"><h3>Generate a document</h3>
    <p class="meta" style="margin:-6px 0 12px">Their details pre-fill the form; the finished PDF files straight into this folder.</p>
    <div class="gen-grid">{gen}</div>
  </div>

  <div class="sec-card"><h3>Documents <span class="ct">· {len(docs)}</span></h3>
    {drows}
    <form method="POST" action="/staff/{sid}/upload" enctype="multipart/form-data" style="margin-top:15px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
      <input type="file" name="file" required style="font-size:13px;flex:1;min-width:170px">
      <select name="kind" class="mini" style="padding:7px 10px"><option value="other">Other</option><option value="certification">Certification</option><option value="contract">Contract</option><option value="written-warning">Warning</option></select>
      <button class="mini" type="submit">{_ic("upload",14)} Upload</button>
    </form>
  </div>

  <div class="sec-card"><h3>Certifications <span class="ct">· {len(certs)}</span></h3>
    {crows}
    <form method="POST" action="/staff/{sid}/cert" style="margin-top:15px;display:grid;grid-template-columns:2fr 1fr auto;gap:8px;align-items:end">
      <div class="f" style="margin:0"><label>Name</label><input name="name" placeholder="e.g. LCQ / Manager's Cert" required></div>
      <div class="f" style="margin:0"><label>Expires</label><input name="expires" type="date"></div>
      <button class="mini solid" type="submit" style="height:42px">{_ic("plus",14)} Add</button>
    </form>
  </div>

  <div style="margin-top:22px;display:flex;justify-content:space-between;align-items:center">
    <a class="mini" href="/logout">{_ic("logout",14)} Sign out</a>
    <form method="POST" action="/staff/{sid}/delete" onsubmit="return confirm('Delete this staff member and all their records? This cannot be undone.')" style="margin:0">
      <button class="mini danger" type="submit">{_ic("trash",14)} Delete staff member</button>
    </form>
  </div>"""
    return _page(body, _esc(staff['full_name']) + " — Browne St. HR")

@app.route("/staff/<sid>/upload", methods=["POST"])
def staff_upload(sid):
    if not store.get_staff(sid): abort(404)
    f = request.files.get("file")
    if f and f.filename:
        store.save_file(sid, f.read(), f.filename, kind=request.form.get("kind","other"),
                        title=f.filename, source="upload")
    return redirect(f"/staff/{sid}")

@app.route("/staff/<sid>/cert", methods=["POST"])
def staff_cert(sid):
    if not store.get_staff(sid): abort(404)
    if request.form.get("name","").strip():
        store.add_certification(sid, request.form.get("name",""), request.form.get("issued",""), request.form.get("expires",""))
    return redirect(f"/staff/{sid}")

@app.route("/staff/cert/<cid>/delete", methods=["POST"])
def staff_cert_delete(cid):
    cert = None
    for s in store.list_staff():
        for c in store.list_certifications(s["id"]):
            if c["id"] == cid: cert = c; break
    store.delete_certification(cid)
    return redirect(f"/staff/{cert['staff_id']}" if cert else "/staff")

@app.route("/staff/doc/<did>")
def staff_doc_download(did):
    data, doc = store.document_bytes(did)
    if data is None: abort(404)
    from flask import Response
    return Response(data, mimetype="application/octet-stream",
                    headers={"Content-Disposition": "attachment; filename=" + store._safe_name(doc["filename"])})

@app.route("/staff/doc/<did>/delete", methods=["POST"])
def staff_doc_delete(did):
    doc = store.get_document(did)
    store.delete_document(did)
    return redirect(f"/staff/{doc['staff_id']}" if doc else "/staff")

# ===========================================================================
# Backup & restore — move the whole data store between machines / to the cloud
# ===========================================================================
import zipfile as _zip

@app.route("/settings")
def settings():
    c = store.counts()
    ok = request.args.get("ok", ""); err = request.args.get("err", "")
    banner = ""
    if ok:  banner += f'<div class="msg okmsg">{_esc(ok)}</div>'
    if err: banner += f'<div class="msg err">{_esc(err)}</div>'
    body = f"""
  <a class="back" href="/">{_ic("arrow-left",15)} All documents</a>
  <h1>Settings &amp; backup</h1>
  <p class="sub">Back up every staff record and file as a single archive, or restore one — the way to move your data onto the live site or hand it over.</p>
  {banner}
  <div class="sec-card"><h3>Download backup</h3>
    <p class="meta" style="margin:-6px 0 14px">{c['staff']} staff &middot; {c['documents']} documents currently stored.</p>
    <a class="btn" href="/backup" style="display:flex;align-items:center;justify-content:center;gap:9px;text-decoration:none;margin-top:0">{_ic("download",18)} Download backup (.zip)</a>
  </div>
  <div class="sec-card"><h3>Restore from backup</h3>
    <div class="warn-cert" style="margin-bottom:14px"><div class="wh">{_ic("alert",16)} Heads up</div>Restoring <strong>replaces</strong> the current staff records and files with the contents of the backup. Use this on a fresh/live site to load your data in.</div>
    <form method="POST" action="/restore" enctype="multipart/form-data" onsubmit="return confirm('Restore will replace all current records with this backup. Continue?')" style="display:flex;gap:9px;align-items:center;flex-wrap:wrap">
      <input type="file" name="backup" accept=".zip" required style="font-size:13px;flex:1;min-width:180px">
      <button class="mini solid" type="submit" style="height:40px">{_ic("upload",14)} Restore</button>
    </form>
  </div>
  <div class="sec-card"><h3>How to move your data to the live site</h3>
    <ol style="font-size:13px;color:var(--ink-soft);line-height:1.9;margin:0;padding-left:18px">
      <li>On the machine that <em>has</em> your data, click <strong>Download backup</strong>.</li>
      <li>Open the live site and sign in.</li>
      <li>Come to this Settings page and <strong>Restore</strong> the downloaded file.</li>
    </ol>
  </div>
  <div class="foot"><span>Browne St. &mdash; Pulse 2012 Ltd</span><a href="/logout">Sign out</a></div>"""
    return _page(body, "Settings — Browne St. HR", extra_css=".okmsg{background:#E7F0E1;color:#2E6B33;border:1px solid #BBD9B4}")

@app.route("/backup")
def backup():
    import io as _io
    from datetime import datetime as _dt
    buf = _io.BytesIO()
    with _zip.ZipFile(buf, "w", _zip.ZIP_DEFLATED) as z:
        if os.path.exists(store.DB_PATH):
            z.write(store.DB_PATH, "hr.db")
        for root, _dirs, files in os.walk(store.FILES_DIR):
            for fn in files:
                full = os.path.join(root, fn)
                z.write(full, os.path.relpath(full, store.DATA_DIR))  # files/<staff>/<file>
    buf.seek(0)
    from flask import Response
    fname = "browne-st-hr-backup-" + _dt.now().strftime("%Y-%m-%d") + ".zip"
    return Response(buf.read(), mimetype="application/zip",
                    headers={"Content-Disposition": "attachment; filename=" + fname})

@app.route("/restore", methods=["POST"])
def restore():
    import io as _io
    f = request.files.get("backup")
    if not f or not (f.filename or "").lower().endswith(".zip"):
        return redirect("/settings?err=Please choose a .zip backup file.")
    try:
        z = _zip.ZipFile(_io.BytesIO(f.read()))
    except Exception:
        return redirect("/settings?err=That file is not a valid .zip archive.")
    if "hr.db" not in z.namelist():
        return redirect("/settings?err=This zip doesn't look like a Browne St. backup (no hr.db).")
    os.makedirs(store.DATA_DIR, exist_ok=True)
    dest_root = os.path.realpath(store.DATA_DIR)
    written = 0
    for member in z.namelist():
        if member.endswith("/"):
            continue
        if member != "hr.db" and not member.startswith("files/"):
            continue
        target = os.path.realpath(os.path.join(store.DATA_DIR, member))
        if os.path.commonpath([dest_root, target]) != dest_root:   # zip-slip guard
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with z.open(member) as src, open(target, "wb") as out:
            out.write(src.read())
        written += 1
    store.init_db()  # ensure schema exists
    return redirect(f"/settings?ok=Backup restored — {written} items loaded.")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8765))
    app.run(host="0.0.0.0", port=port)
