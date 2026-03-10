import io
from datetime import datetime
from decimal import Decimal
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# Brand colors
BRAND_PRIMARY = colors.HexColor("#1a56db")
BRAND_DARK = colors.HexColor("#0f172a")
BRAND_GRAY = colors.HexColor("#64748b")
BRAND_LIGHT = colors.HexColor("#f8fafc")
BRAND_GREEN = colors.HexColor("#10b981")
BRAND_RED = colors.HexColor("#ef4444")


def _build_styles():
    styles = getSampleStyleSheet()
    custom = {
        "bank_title": ParagraphStyle("bank_title", parent=styles["Heading1"],
                                      fontSize=22, textColor=BRAND_PRIMARY, spaceAfter=2, alignment=TA_CENTER),
        "bank_subtitle": ParagraphStyle("bank_subtitle", parent=styles["Normal"],
                                         fontSize=9, textColor=BRAND_GRAY, alignment=TA_CENTER, spaceAfter=14),
        "section_header": ParagraphStyle("section_header", parent=styles["Normal"],
                                          fontSize=10, textColor=BRAND_PRIMARY, fontName="Helvetica-Bold",
                                          spaceBefore=10, spaceAfter=4),
        "normal_sm": ParagraphStyle("normal_sm", parent=styles["Normal"],
                                     fontSize=9, textColor=BRAND_DARK),
        "amount_big": ParagraphStyle("amount_big", parent=styles["Normal"],
                                      fontSize=28, textColor=BRAND_GREEN, fontName="Helvetica-Bold",
                                      alignment=TA_CENTER, spaceBefore=8, spaceAfter=8),
        "status_badge": ParagraphStyle("status_badge", parent=styles["Normal"],
                                        fontSize=9, textColor=BRAND_GREEN, fontName="Helvetica-Bold",
                                        alignment=TA_CENTER),
        "footer_text": ParagraphStyle("footer_text", parent=styles["Normal"],
                                       fontSize=7, textColor=BRAND_GRAY, alignment=TA_CENTER),
    }
    return {**{k: styles[k] for k in styles.byName}, **custom}


def generate_receipt_pdf(transaction: dict, sender_name: str, receiver_name: str,
                          balance_after: float) -> bytes:
    """Generate a PDF receipt for a transaction."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                             topMargin=20*mm, bottomMargin=20*mm,
                             leftMargin=25*mm, rightMargin=25*mm)
    styles = _build_styles()
    story = []

    # Header
    story.append(Paragraph("NexaBank", styles["bank_title"]))
    story.append(Paragraph("Your trusted digital banking partner", styles["bank_subtitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=BRAND_PRIMARY, spaceAfter=12))

    # Title
    title_style = ParagraphStyle("receipt_title", parent=styles["Heading2"],
                                  fontSize=14, textColor=BRAND_DARK, alignment=TA_CENTER,
                                  spaceBefore=0, spaceAfter=6)
    story.append(Paragraph("TRANSACTION RECEIPT", title_style))

    # Amount
    amount = float(transaction.get("amount", 0))
    tx_type = transaction.get("transaction_type", "transfer")
    story.append(Paragraph(f"{'+ ' if tx_type == 'deposit' else '- '}${amount:,.2f}", styles["amount_big"]))
    story.append(Paragraph(f"● {transaction.get('status', 'COMPLETED').upper()}", styles["status_badge"]))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceAfter=10))

    # Details table
    ts = transaction.get("timestamp", datetime.now())
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts)
        except Exception:
            ts = datetime.now()
    details = [
        ["Transaction Reference", transaction.get("transaction_reference", "N/A")],
        ["Transaction Type", tx_type.capitalize()],
        ["Date & Time", ts.strftime("%B %d, %Y at %I:%M %p")],
        ["Sender", f"{sender_name}"],
        ["Receiver", f"{receiver_name}"],
        ["Balance After", f"${float(balance_after):,.2f}"],
    ]
    if transaction.get("description"):
        details.append(["Description", transaction["description"]])

    tbl = Table(details, colWidths=[60*mm, 100*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), BRAND_LIGHT),
        ("TEXTCOLOR", (0, 0), (0, -1), BRAND_GRAY),
        ("TEXTCOLOR", (1, 0), (1, -1), BRAND_DARK),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, BRAND_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(tbl)

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceAfter=8))
    story.append(Paragraph(
        "This is an automatically generated receipt. NexaBank is a simulated banking platform. "
        "For support, contact support@nexabank.io",
        styles["footer_text"]
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def generate_statement_pdf(user: dict, account: dict, transactions: list,
                            date_from: str = None, date_to: str = None) -> bytes:
    """Generate a full account statement PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                             topMargin=20*mm, bottomMargin=20*mm,
                             leftMargin=20*mm, rightMargin=20*mm)
    styles = _build_styles()
    story = []

    # Header
    story.append(Paragraph("NexaBank", styles["bank_title"]))
    story.append(Paragraph("Account Statement", styles["bank_subtitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=BRAND_PRIMARY, spaceAfter=12))

    # Account info
    info_data = [
        ["Account Holder", user.get("name", "")],
        ["Account Number", account.get("account_number", "")],
        ["Statement Period", f"{date_from or 'All time'} — {date_to or 'Present'}"],
        ["Current Balance", f"${float(account.get('balance', 0)):,.2f}"],
        ["Generated On", datetime.now().strftime("%B %d, %Y at %I:%M %p")],
    ]
    info_tbl = Table(info_data, colWidths=[55*mm, 120*mm])
    info_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), BRAND_LIGHT),
        ("TEXTCOLOR", (0, 0), (0, -1), BRAND_GRAY),
        ("TEXTCOLOR", (1, 0), (1, -1), BRAND_DARK),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, BRAND_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 16))

    # Transactions table
    story.append(Paragraph("Transaction History", styles["section_header"]))

    headers = ["Date", "Reference", "Type", "From / To", "Amount", "Status"]
    rows = [headers]
    running_balance = 0.0
    for tx in transactions:
        ts = tx.get("timestamp", "")
        if hasattr(ts, "strftime"):
            ts_str = ts.strftime("%d %b %Y")
        else:
            ts_str = str(ts)[:10]
        amt = float(tx.get("amount", 0))
        tx_type = tx.get("transaction_type", "transfer")
        from_to = tx.get("counterpart", "")
        amt_str = f"+${amt:,.2f}" if tx_type == "deposit" else f"-${amt:,.2f}"
        rows.append([
            ts_str,
            tx.get("transaction_reference", "")[:16],
            tx_type.capitalize(),
            from_to,
            amt_str,
            tx.get("status", "completed").upper(),
        ])

    tx_tbl = Table(rows, colWidths=[22*mm, 36*mm, 22*mm, 40*mm, 28*mm, 22*mm])
    tx_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (4, 0), (4, -1), "RIGHT"),
    ]))
    story.append(tx_tbl)

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceAfter=8))
    story.append(Paragraph(
        "NexaBank — Simulated banking platform. Not a real financial institution. "
        "This statement is generated for demonstration purposes only.",
        styles["footer_text"]
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
