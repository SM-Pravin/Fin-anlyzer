"""
cert_service.py
Generates a professional VaultVerify certificate PDF using reportlab.
Returns raw bytes so the caller can stream them directly.
"""
import io
from datetime import datetime
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph


# ── Colour palette (matches the minimalist UI) ────────────────────────────────
BLACK      = colors.HexColor("#111827")
WHITE      = colors.white
LIGHT_GRAY = colors.HexColor("#F9FAFB")
BORDER     = colors.HexColor("#E5E7EB")
MID_GRAY   = colors.HexColor("#6B7280")
ACCENT     = colors.HexColor("#000000")


def _fmt(dt: Optional[datetime]) -> str:
    if not dt:
        return "—"
    return dt.strftime("%d %b %Y, %H:%M UTC")


def _draw_header(c: canvas.Canvas, width: float, height: float) -> float:
    """Draw top header bar. Returns the y cursor after the header."""
    # Black header bar
    c.setFillColor(ACCENT)
    c.rect(0, height - 60 * mm, width, 60 * mm, fill=1, stroke=0)

    # Brand name
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(18 * mm, height - 24 * mm, "VaultVerify")

    # Tagline
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#D1D5DB"))
    c.drawString(18 * mm, height - 34 * mm, "Enterprise Collateral Verification System")

    # CERTIFIED badge on the right
    badge_x = width - 60 * mm
    badge_y = height - 42 * mm
    c.setFillColor(WHITE)
    c.roundRect(badge_x, badge_y, 48 * mm, 14 * mm, 3 * mm, fill=1, stroke=0)
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(badge_x + 24 * mm, badge_y + 4.5 * mm, "CERTIFIED")

    return height - 68 * mm   # y cursor


def _draw_section_title(c: canvas.Canvas, x: float, y: float, title: str) -> float:
    """Draw a small uppercase section label. Returns new y."""
    c.setFillColor(MID_GRAY)
    c.setFont("Helvetica", 8)
    c.drawString(x, y, title.upper())
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.4)
    c.line(x, y - 2, x + 174 * mm, y - 2)
    return y - 8 * mm


def _draw_field(
    c: canvas.Canvas,
    x: float, y: float,
    label: str, value: str,
    col_width: float = 85 * mm,
) -> None:
    """Draw a label+value pair in a soft box."""
    box_h = 14 * mm
    c.setFillColor(LIGHT_GRAY)
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.5)
    c.roundRect(x, y - box_h + 3 * mm, col_width - 4 * mm, box_h, 2 * mm,
                fill=1, stroke=1)

    c.setFillColor(MID_GRAY)
    c.setFont("Helvetica", 7)
    c.drawString(x + 3 * mm, y - 1 * mm, label.upper())

    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x + 3 * mm, y - 7 * mm, str(value))


def generate_certificate_pdf(asset: dict) -> bytes:
    """
    Build a certificate PDF for the given asset document (already _id-stripped).
    Returns the PDF as raw bytes.
    """
    buf    = io.BytesIO()
    width, height = A4          # 210 x 297 mm
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"VaultVerify Certificate – {asset.get('certificate_id', '')}")

    # ── Header ────────────────────────────────────────────────────────────────
    y = _draw_header(c, width, height)
    y -= 8 * mm

    # ── Certificate ID banner ─────────────────────────────────────────────────
    c.setFillColor(LIGHT_GRAY)
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.5)
    c.roundRect(18 * mm, y - 14 * mm, width - 36 * mm, 14 * mm, 2 * mm,
                fill=1, stroke=1)

    c.setFillColor(MID_GRAY)
    c.setFont("Helvetica", 8)
    c.drawString(22 * mm, y - 5 * mm, "CERTIFICATE ID")
    c.setFillColor(BLACK)
    c.setFont("Courier-Bold", 10)
    c.drawString(22 * mm, y - 11 * mm, asset.get("certificate_id", "—"))

    y -= 22 * mm

    # ── Applicant section ─────────────────────────────────────────────────────
    y = _draw_section_title(c, 18 * mm, y, "Applicant Information")
    _draw_field(c, 18 * mm, y, "Applicant Name",
                asset.get("applicant_name", "—"))
    _draw_field(c, 18 * mm + 87 * mm, y, "PAN Number",
                asset.get("pan_number", "—"))
    y -= 18 * mm

    # ── Certificate dates ─────────────────────────────────────────────────────
    _draw_field(c, 18 * mm, y, "Submitted On",
                _fmt(asset.get("submitted_at")))
    _draw_field(c, 18 * mm + 87 * mm, y, "Certified On",
                _fmt(asset.get("certified_on")))
    y -= 22 * mm

    # ── Asset-specific details ─────────────────────────────────────────────────
    asset_type = asset.get("asset_type", "gold")

    if asset_type == "gold":
        y = _draw_section_title(c, 18 * mm, y, "Gold Asset Details")

        _draw_field(c, 18 * mm,             y, "Declared Weight",
                    f"{asset.get('declared_weight', '—')} g")
        _draw_field(c, 18 * mm + 87 * mm,   y, "Measured Weight",
                    f"{asset.get('measured_weight', '—')} g")
        y -= 18 * mm

        _draw_field(c, 18 * mm,             y, "Declared Purity",
                    str(asset.get("declared_purity", "—")))
        _draw_field(c, 18 * mm + 87 * mm,   y, "Tested Purity",
                    str(asset.get("tested_purity", "—")))
        y -= 18 * mm

        _draw_field(c, 18 * mm,             y, "Form / Structure",
                    str(asset.get("structure", "—")))
        y -= 22 * mm

    else:  # land
        y = _draw_section_title(c, 18 * mm, y, "Land Asset Details")

        # Full-width address box
        addr = str(asset.get("property_address", "—"))
        box_h = 14 * mm
        c.setFillColor(LIGHT_GRAY)
        c.setStrokeColor(BORDER)
        c.setLineWidth(0.5)
        c.roundRect(18 * mm, y - box_h + 3 * mm,
                    width - 36 * mm, box_h, 2 * mm, fill=1, stroke=1)
        c.setFillColor(MID_GRAY)
        c.setFont("Helvetica", 7)
        c.drawString(21 * mm, y - 1 * mm, "PROPERTY ADDRESS")
        c.setFillColor(BLACK)
        c.setFont("Helvetica-Bold", 10)
        # Truncate long addresses to fit one line
        if len(addr) > 70:
            addr = addr[:67] + "..."
        c.drawString(21 * mm, y - 7 * mm, addr)
        y -= 18 * mm

        _draw_field(c, 18 * mm,           y, "GPS Latitude",
                    str(asset.get("gps_lat", "—")))
        _draw_field(c, 18 * mm + 87 * mm, y, "GPS Longitude",
                    str(asset.get("gps_long", "—")))
        y -= 18 * mm

        _draw_field(c, 18 * mm,           y, "Declared Size",
                    f"{asset.get('declared_size', '—')} sq. ft.")
        _draw_field(c, 18 * mm + 87 * mm, y, "Land Use Type",
                    str(asset.get("land_use_type", "—")))
        y -= 22 * mm

    # ── Verification status box ────────────────────────────────────────────────
    y = _draw_section_title(c, 18 * mm, y, "Verification Status")

    c.setFillColor(ACCENT)
    c.setStrokeColor(ACCENT)
    c.roundRect(18 * mm, y - 18 * mm, width - 36 * mm, 18 * mm, 2 * mm,
                fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(width / 2,
                        y - 11 * mm,
                        "This asset has been verified and certified by VaultVerify.")
    y -= 26 * mm

    # ── Footer ─────────────────────────────────────────────────────────────────
    footer_y = 18 * mm
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.4)
    c.line(18 * mm, footer_y + 8 * mm, width - 18 * mm, footer_y + 8 * mm)

    c.setFillColor(MID_GRAY)
    c.setFont("Helvetica", 7.5)
    c.drawString(18 * mm, footer_y + 3 * mm,
                 "VaultVerify Enterprise Collateral Verification System  ·  "
                 "This certificate is digitally generated and is valid without a physical signature.")
    c.drawRightString(width - 18 * mm, footer_y + 3 * mm,
                      f"Generated: {datetime.utcnow().strftime('%d %b %Y')}")

    c.save()
    buf.seek(0)
    return buf.read()