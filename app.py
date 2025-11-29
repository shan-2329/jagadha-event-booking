from flask import Flask, render_template, request, send_file, redirect, url_for, session, flash
import io
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Flowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import Image

app = Flask(__name__)
app.secret_key = "987654321"

# -------------------------------------------------------------
# LOGIN CREDENTIALS
# -------------------------------------------------------------
USERNAME = "admin"
PASSWORD = "Jagadha@123"


# -------------------------------------------------------------
# LOGIN PAGE
# -------------------------------------------------------------
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


# -------------------------------------------------------------
# PROTECT ROUTES
# -------------------------------------------------------------
@app.before_request
def require_login():
    if request.endpoint in ["static", "login"]:
        return

    protected = ["form_page", "generate_pdf", "download_last"]

    if request.endpoint in protected and not session.get("logged_in"):
        return redirect(url_for("login"))


# -------------------------------------------------------------
# COLORS
# -------------------------------------------------------------
PAGE_WIDTH, PAGE_HEIGHT = A4
PINK = colors.HexColor("#E91E63")
PINK_DARK = colors.HexColor("#d81b60")
LIGHT_PINK = colors.HexColor("#F8D7E8")
SOFT_PINK = colors.HexColor("#FFF1F6")
GREY_BG = colors.HexColor("#F2F2F2")
DARK_TEXT = colors.HexColor("#333333")


# -------------------------------------------------------------
# UTIL
# -------------------------------------------------------------
def safe_float(val):
    try:
        return float(str(val).replace(",", "").strip())
    except:
        return 0.0


# -------------------------------------------------------------
# BORDER STYLING
# -------------------------------------------------------------
def draw_border(canvas, doc):
    canvas.saveState()

    # Outer dark pink
    canvas.setLineWidth(3)
    canvas.setStrokeColor(PINK_DARK)
    canvas.rect(12 * mm, 12 * mm,
                PAGE_WIDTH - 24 * mm, PAGE_HEIGHT - 24 * mm)

    # Inner soft border
    canvas.setLineWidth(1)
    canvas.setStrokeColor(LIGHT_PINK)
    canvas.rect(16 * mm, 16 * mm,
                PAGE_WIDTH - 32 * mm, PAGE_HEIGHT - 32 * mm)

    canvas.restoreState()


# -------------------------------------------------------------
# HEADER BAR
# -------------------------------------------------------------
class HeaderBar(Flowable):
    def __init__(self, width, height=20):
        Flowable.__init__(self)
        self.width = width
        self.height = height

    def draw(self):
        self.canv.saveState()
        self.canv.setFillColor(PINK)
        self.canv.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        self.canv.restoreState()


# -------------------------------------------------------------
# SECTION TABLE BUILDER
# -------------------------------------------------------------
def build_section_table(title, rows, styles, total_manual=None):
    story = []
    story.append(Paragraph(f"<b>{title}</b>", styles["SectionHeading"]))
    story.append(Spacer(1, 6))

    if not rows:
        rows = [["(no items)", ""]]

    table_data = [
        [
            Paragraph("<b>Item Name</b>", styles["TableHeader"]),
            Paragraph("<b>Price</b>", styles["Right"])
        ]
    ]

    for it, qt in rows:
        table_data.append([
            it,
            Paragraph(qt, styles["Right"])
        ])

    if total_manual is not None:
        table_data.append([
            Paragraph("<b>TOTAL</b>", styles["Normal"]),
            Paragraph(f"<b>{total_manual:.2f}</b>", styles["Right"])
        ])

    tbl = Table(table_data, colWidths=[330, 110])

    style = TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, LIGHT_PINK),
        ("BACKGROUND", (0, 0), (-1, 0), SOFT_PINK),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
    ])

    # Highlight total row
    if total_manual is not None:
        last = len(table_data) - 1
        style.add("BACKGROUND", (0, last), (-1, last), GREY_BG)

    tbl.setStyle(style)
    story.append(tbl)
    story.append(Spacer(1, 12))
    return story


# -------------------------------------------------------------
# PDF CREATOR
# -------------------------------------------------------------
def create_quotation_pdf(customer, event_date, mandabam,
                         stage_rows, stage_total_manual,
                         stall_rows, stall_total_manual,
                         stall_all_total, stall_advance,
                         stall_final_balance,
                         other_rows, other_total_manual):

    buffer = io.BytesIO()
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(name="TitleCentered", parent=styles["Title"], alignment=1))
    styles.add(ParagraphStyle(name="SectionHeading", parent=styles["Heading3"],
                              alignment=0, fontSize=12, textColor=DARK_TEXT))
    styles.add(ParagraphStyle(name="TableHeader", parent=styles["Normal"], alignment=0, fontSize=10))
    styles.add(ParagraphStyle(name="Right", parent=styles["Normal"], alignment=2, fontSize=10))

    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm)

    story = []

    # Header title bar
    # story.append(HeaderBar(PAGE_WIDTH - 40 * mm))
    # story.append(Spacer(1, 8))

    # ------------------ LOGO ADD HERE -------------------
    logo_path = "static/images/logo.jpg"
    try:
        logo = Image(logo_path, width=90 * mm, height=50 * mm)
        logo.hAlign = "CENTER"
        story.append(logo)
        story.append(Spacer(1, 8))
    except:
        pass

    # story.append(Paragraph(
    #     "<para align='center'><b>JAGADHA 💗 A to Z 💗 Event Management</b></para>",
    #     styles["TitleCentered"]
    # ))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<para align='center'><b><u>QUOTATION</u></b></para>", styles["Heading2"]))
    story.append(Spacer(1, 14))

    # Customer Details Box
    cust = Table([
        [
            Paragraph(f"<b>Customer Name:</b> {customer}", styles["Normal"]),
            Paragraph(f"<b>Event Date:</b> {event_date}", styles["Normal"])
        ],
        [
            Paragraph(f"<b>Mandabam Name:</b> {mandabam}", styles["Normal"]),
            ""
        ]
    ], colWidths=[270, 170])

    cust.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT_PINK),
        ("BOX", (0, 0), (-1, -1), 0.8, LIGHT_PINK),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, LIGHT_PINK)
    ]))

    story.append(cust)
    story.append(Spacer(1, 14))

    # Sections
    story.extend(build_section_table("STAGE DECORATION", stage_rows, styles, stage_total_manual))
    story.extend(build_section_table("STALL ITEMS", stall_rows, styles, stall_total_manual))
    story.extend(build_section_table("OTHER ITEMS", other_rows, styles, other_total_manual))

    # Summary Table
    # AMOUNT SUMMARY Header
    story.append(Paragraph("<b>AMOUNT SUMMARY</b>", styles["SectionHeading"]))
    story.append(Spacer(1, 6))

    # Summary Table
    summary = Table([
        ["ALL TOTAL", Paragraph(f"<b>{stall_all_total:.2f}</b>", styles["Right"])],
        ["ADVANCE", Paragraph(f"<b>{stall_advance:.2f}</b>", styles["Right"])],
        ["BALANCE", Paragraph(f"<b>{stall_final_balance:.2f}</b>", styles["Right"])],
    ], colWidths=[320, 110])

    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GREY_BG),
        ("BOX", (0, 0), (-1, -1), 1, LIGHT_PINK),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold")
    ]))

    story.append(summary)
    story.append(Spacer(1, 20))

    story.append(Paragraph(
        "<para align='center'><b>*** THANK YOU ***</b></para>",
        styles["Heading2"]
    ))

    # Build PDF with border
    doc.build(story, onFirstPage=draw_border, onLaterPages=draw_border)

    buffer.seek(0)
    return buffer


# -------------------------------------------------------------
# FORM PAGE
# -------------------------------------------------------------
@app.route("/")
def form_page():
    success = session.pop("pdf_success", None)
    return render_template("form.html", success=success)


# -------------------------------------------------------------
# GENERATE PDF
# -------------------------------------------------------------
@app.route("/generate_pdf", methods=["POST"])
def generate_pdf():
    customer = request.form.get("customer", "")
    event_date = request.form.get("event_date", "")
    mandabam = request.form.get("mandabam", "")

    stage_rows = list(zip(request.form.getlist("stage_item[]"),
                          request.form.getlist("stage_price[]")))
    stage_total_manual = safe_float(request.form.get("stage_total"))

    stall_rows = list(zip(request.form.getlist("stall_item[]"),
                          request.form.getlist("stall_price[]")))
    stall_total_manual = safe_float(request.form.get("stall_total"))

    other_rows = list(zip(request.form.getlist("other_item[]"),
                          request.form.getlist("other_price[]")))
    other_total_manual = safe_float(request.form.get("other_total"))

    stall_advance = safe_float(request.form.get("stall_advance"))
    stall_final_balance = safe_float(request.form.get("stall_final_balance"))

    stall_all_total = stage_total_manual + stall_total_manual + other_total_manual

    pdf_buffer = create_quotation_pdf(
        customer, event_date, mandabam,
        stage_rows, stage_total_manual,
        stall_rows, stall_total_manual,
        stall_all_total, stall_advance,
        stall_final_balance,
        other_rows, other_total_manual
    )


    session["last_pdf"] = pdf_buffer.getvalue()
    session["pdf_success"] = True

    filename = f"{customer.replace(' ', '_')}_Event_Quotation_  {event_date.replace (' ', '_')}.pdf"
    return send_file(pdf_buffer, as_attachment=True, download_name=filename)


# -------------------------------------------------------------
# DOWNLOAD LAST PDF
# -------------------------------------------------------------
@app.route("/download_last")
def download_last():
    if not session.get("last_pdf"):
        return "No PDF generated yet."

    return send_file(
        io.BytesIO(session["last_pdf"]),
        as_attachment=True,
        download_name="Last_Generated_Quotation.pdf",
        mimetype="application/pdf"
    )

@app.route("/ping")
def ping():
    return "pong"

# -------------------------------------------------------------
# RUN
# -------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="172.16.2.26", port=5000)
