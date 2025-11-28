from flask import Flask, render_template, request, send_file
import io
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Flowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from flask import Flask, render_template, request, redirect, url_for, session, flash


app = Flask(__name__)

app.secret_key = "987654321"

# Simple credentials (for demo)
USERNAME = "admin"
PASSWORD = "Jagadha@123"

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == USERNAME and password == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("form_page"))
        else:
            flash("Invalid username or password!", "danger")
            return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

# Protect form page
@app.before_request
def require_login():
    if request.endpoint in ["form_page", "generate_pdf"] and not session.get("logged_in"):
        return redirect(url_for("login"))

# ------------------------ Colors & Page ------------------------
PAGE_WIDTH, PAGE_HEIGHT = A4
PINK = colors.HexColor("#E91E63")
PINK_STRONG = colors.HexColor("#ff007f")
LIGHT_PINK = colors.HexColor("#F8BBDA")
SOFT_PINK = colors.HexColor("#FFE6F0")
DARK_GREY = colors.HexColor("#333333")


# ------------------------ Utilities ------------------------
def safe_float(val):
    try:
        return float(str(val).replace(",", "").strip())
    except Exception:
        return 0.0


# ------------------------ Canvas border ------------------------
def draw_border(canvas, doc):
    border_margin = 10 * mm
    canvas.saveState()
    canvas.setLineWidth(3)
    canvas.setStrokeColor(PINK)
    canvas.rect(border_margin, border_margin,
                PAGE_WIDTH - 2 * border_margin,
                PAGE_HEIGHT - 2 * border_margin)
    canvas.setLineWidth(0.8)
    canvas.setStrokeColor(LIGHT_PINK)
    canvas.rect(border_margin + 6, border_margin + 6,
                PAGE_WIDTH - 2 * (border_margin + 6),
                PAGE_HEIGHT - 2 * (border_margin + 6))
    canvas.restoreState()


# ------------------------ Header bar flowable ------------------------
class HeaderBar(Flowable):
    def __init__(self, width, height=18):
        Flowable.__init__(self)
        self.width = width
        self.height = height

    def draw(self):
        self.canv.saveState()
        self.canv.setFillColor(PINK)
        self.canv.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        self.canv.restoreState()


# ------------------------ Section header (Option C: thick pink bar above text) ------------------------
def section_header(title, styles, width=430):
    """
    Returns a Table that displays a thick pink bar above the section title.
    This achieves the 'Thick Pink Header Bar' look (Option C).
    """
    # Use a single-cell table for heading; LINEABOVE draws the thick bar above.
    data = [[Paragraph(f"<b>{title}</b>", styles["SectionHeading"])]]
    tbl = Table(data, colWidths=[width])
    tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        # Thick pink bar above the title (Option C)
        ("LINEABOVE", (0, 0), (-1, 0), 8, PINK_STRONG),
    ]))
    return tbl


# ------------------------ Section table builder ------------------------
def build_section_table(title, rows, styles, total_manual=None):
    story = []
    # Title paragraph (we still include the title text here in case someone wants it)
    story.append(Paragraph(f'<b>{title}</b>', styles["SectionHeading"]))
    story.append(Spacer(1, 6))

    if not rows:
        rows = [["(no items)", ""]]

    table_data = [
        [Paragraph("<b>Name of Item</b>", styles["TableHeader"]),
         Paragraph("<b>Quantity (numbers)</b>", styles["TableHeader"])]
    ]

    for item, qty in rows:
        left = item if item else ""
        right = qty if qty else ""
        table_data.append([left, Paragraph(right, styles["Right"])])

    if total_manual is not None:
        # Ensure total_manual is numeric (float) for consistent formatting
        try:
            tval = float(total_manual)
        except Exception:
            tval = safe_float(total_manual)
        table_data.append([
            Paragraph("<b>TOTAL</b>", styles["Normal"]),
            Paragraph(f"<b>{tval:.2f}</b>", styles["Right"])
        ])

    tbl_style = TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#F0D0E0")),
        ("BACKGROUND", (0, 0), (-1, 0), SOFT_PINK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
    ])

    if total_manual is not None:
        last_row = len(table_data) - 1
        tbl_style.add("BACKGROUND", (0, last_row), (-1, last_row), LIGHT_PINK)
        tbl_style.add("TEXTCOLOR", (0, last_row), (-1, last_row), DARK_GREY)

    table = Table(table_data, colWidths=[320, 110], hAlign="CENTER")
    table.setStyle(tbl_style)

    story.append(table)
    story.append(Spacer(1, 12))
    return story


# ------------------------ PDF generator ------------------------
def create_quotation_pdf(customer, event_date, mandabam,
                         stage_rows, stage_total_manual,
                         stall_rows, stall_total_manual,
                         stall_all_total, stall_advance,
                         stall_final_balance,
                         other_rows, other_total_manual):

    buffer = io.BytesIO()
    styles = getSampleStyleSheet()

    # Title and section styles
    styles.add(ParagraphStyle(name="TitleCentered", parent=styles["Title"], alignment=1))
    styles.add(ParagraphStyle(name="SectionHeading", parent=styles["Heading3"],
                              alignment=0, fontSize=12, textColor=DARK_GREY, spaceAfter=4))
    styles.add(ParagraphStyle(name="TableHeader", parent=styles["Normal"], alignment=0, fontSize=10))
    styles.add(ParagraphStyle(name="Right", parent=styles["Normal"], alignment=2))

    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=24 * mm, bottomMargin=18 * mm)

    story = []

    # Header bar
    story.append(HeaderBar(PAGE_WIDTH - 36 * mm, 18))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f'<para align="center"><font color="{DARK_GREY}"><b>JAGADHA 💗 A to Z 💗 Event Management</b></font></para>',
        styles["TitleCentered"]
    ))
    story.append(Spacer(1, 8))
    story.append(Paragraph('<para align="center"><font size="14"><b><u>QUOTATION</u></b></font></para>', styles["Heading2"]))
    story.append(Spacer(1, 10))

    # Customer details box
    cust_table = Table([
        [Paragraph(f"<b>Customer Name:</b> {customer}", styles["Normal"]),
         Paragraph(f"<b>Event Date:</b> {event_date}", styles["Normal"])],
        [Paragraph(f"<b>Mandabam Name:</b> {mandabam}", styles["Normal"]), ""]
    ], colWidths=[250, 180], hAlign="CENTER")

    cust_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT_PINK),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#F0D0E0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))

    story.append(cust_table)
    story.append(Spacer(1, 12))

    # STAGE section (thick pink bar above)
    story.extend(build_section_table("STAGE DECORATION", stage_rows, styles, total_manual=stage_total_manual))
    story.extend(build_section_table("STALL ITEMS", stall_rows, styles, total_manual=stall_total_manual))
    story.extend(build_section_table("OTHER ITEMS", other_rows, styles, total_manual=other_total_manual))

    # Summary table (ALL TOTAL / ADVANCE / BALANCE) with pink top border like header
    summary_table = Table([
        ["ALL TOTAL", Paragraph(f"<b>{stall_all_total:.2f}</b>", styles["Right"])],
        ["ADVANCE", Paragraph(f"<b>{stall_advance:.2f}</b>", styles["Right"])],
        ["BALANCE", Paragraph(f"<b>{stall_final_balance:.2f}</b>", styles["Right"])],
    ], colWidths=[320, 110], hAlign="CENTER")

    summary_table.setStyle(TableStyle([
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.white),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#F0D0E0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (1, 0), (1, -1), "RIGHT")
    ]))

    story.append(summary_table)

    # Footer
    story.append(Spacer(1, 18))
    story.append(Paragraph('<para align="center"><b>*** THANK YOU ***</b></para>', styles["Heading2"]))

    doc.build(story, onFirstPage=draw_border, onLaterPages=draw_border)
    buffer.seek(0)
    return buffer


# ------------------------ Routes ------------------------
@app.route("/")
def form_page():
    return render_template("form.html")


@app.route("/generate_pdf", methods=["POST"])
def generate_pdf():
    # Read basic fields
    customer = request.form.get("customer") or ""
    event_date = request.form.get("event_date") or ""
    mandabam = request.form.get("mandabam") or ""

    # STAGE rows & manual total
    stage_rows = [
        [it.strip(), pr.strip()]
        for it, pr in zip(request.form.getlist("stage_item[]"),
                          request.form.getlist("stage_price[]"))
        if it.strip() or pr.strip()
    ]
    stage_total_manual = safe_float(request.form.get("stage_total") or "0")

    # STALL rows & manual total
    stall_rows = [
        [it.strip(), pr.strip()]
        for it, pr in zip(request.form.getlist("stall_item[]"),
                          request.form.getlist("stall_price[]"))
        if it.strip() or pr.strip()
    ]
    stall_total_manual = safe_float(request.form.get("stall_total") or "0")

    # OTHER rows & manual total
    other_rows = [
        [it.strip(), pr.strip()]
        for it, pr in zip(request.form.getlist("other_item[]"),
                          request.form.getlist("other_price[]"))
        if it.strip() or pr.strip()
    ]
    other_total_manual = safe_float(request.form.get("other_total") or "0")

    # Summary fields
    stall_advance = safe_float(request.form.get("stall_advance") or "0")
    stall_final_balance = safe_float(request.form.get("stall_final_balance") or "0")

    # ALL TOTAL = Stage + Stall + Other
    stall_all_total = stage_total_manual + stall_total_manual + other_total_manual

    # Generate PDF
    pdf_buffer = create_quotation_pdf(
        customer, event_date, mandabam,
        stage_rows, stage_total_manual,
        stall_rows, stall_total_manual,
        stall_all_total, stall_advance,
        stall_final_balance,
        other_rows, other_total_manual
    )

    filename = f"{(customer or 'quotation').replace(' ', '_')}_Quotation.pdf"
    return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype="application/pdf")


if __name__ == "__main__":
    app.run(debug=True, host="172.16.2.26", port=5000)
