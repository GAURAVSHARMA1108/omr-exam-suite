import os
import json
import io
import qrcode
from pathlib import Path
from typing import Dict, Any, List, Tuple
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from PIL import Image

from app.config import PDFS_DIR

# Canonical dimensions for OMR layout & OpenCV image warping
CANONICAL_OMR_WIDTH = 1200
CANONICAL_OMR_HEIGHT = 1600

def generate_qr_image(data: dict) -> Image.Image:
    """Generates a PIL QR code image from a dictionary payload."""
    payload_str = json.dumps(data, separators=(',', ':'))
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=1,
    )
    qr.add_data(payload_str)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").get_image()

class OMRLayoutSpec:
    """
    Defines the exact geometric layout contract inside CANONICAL_OMR_WIDTH x CANONICAL_OMR_HEIGHT.
    Shared identically between the ReportLab PDF generator and the OpenCV evaluation engine.
    """
    @staticmethod
    def get_layout(
        question_count: int, 
        options_count: int = 4, 
        roll_length: int = 6
    ) -> Dict[str, Any]:
        W, H = CANONICAL_OMR_WIDTH, CANONICAL_OMR_HEIGHT
        
        # Fiducial square size: 60x60 px at offset 30 px
        fid_size = 60
        fid_offset = 30
        
        fiducials = {
            "top_left": [fid_offset, fid_offset, fid_size, fid_size],
            "top_right": [W - fid_offset - fid_size, fid_offset, fid_size, fid_size],
            "bottom_left": [fid_offset, H - fid_offset - fid_size, fid_size, fid_size],
            "bottom_right": [W - fid_offset - fid_size, H - fid_offset - fid_size, fid_size, fid_size],
        }

        # Fiducial centers (used for homography perspective transform)
        fid_centers = {
            "top_left": [fid_offset + fid_size / 2, fid_offset + fid_size / 2], # [60, 60]
            "top_right": [W - fid_offset - fid_size / 2, fid_offset + fid_size / 2], # [1140, 60]
            "bottom_left": [fid_offset + fid_size / 2, H - fid_offset - fid_size / 2], # [60, 1540]
            "bottom_right": [W - fid_offset - fid_size / 2, H - fid_offset - fid_size / 2], # [1140, 1540]
        }

        # Roll Number Section (Right box of Candidate Area)
        # Box bounds: x: 590, y: 200, w: 550, h: 360
        roll_box_start_x = 615
        roll_box_start_y = 250
        col_spacing = 75
        roll_bubble_r = 11

        roll_bubbles: List[List[Dict[str, Any]]] = []
        for col in range(roll_length):
            col_bubbles = []
            cx = roll_box_start_x + col * col_spacing + 30
            for digit in range(10):
                cy = 315 + digit * 22
                col_bubbles.append({
                    "digit": digit,
                    "x": cx,
                    "y": cy,
                    "r": roll_bubble_r
                })
            roll_bubbles.append(col_bubbles)

        # Question Response Section (y: 620 to 1500)
        # Multi-column layout based on question count
        q_cols = 1 if question_count <= 12 else (2 if question_count <= 30 else (3 if question_count <= 60 else 4))
        questions_per_col = (question_count + q_cols - 1) // q_cols
        
        q_start_y = 625
        available_w = W - 140 # 1060 px
        q_col_w = available_w // q_cols
        row_height = min(54, max(24, int(850 / max(questions_per_col, 5))))
        q_bubble_r = min(14, max(9, int(row_height * 0.32)))
        opt_spacing = min(58, max(36, int(q_bubble_r * 3.4)))

        question_bubbles: Dict[int, List[Dict[str, Any]]] = {}
        for q_idx in range(1, question_count + 1):
            col_idx = (q_idx - 1) // questions_per_col
            row_idx = (q_idx - 1) % questions_per_col

            base_x = 70 + col_idx * q_col_w
            base_y = q_start_y + row_idx * row_height

            q_bubbles = []
            for opt_idx in range(options_count):
                letter = chr(65 + opt_idx)
                bx = base_x + 95 + opt_idx * opt_spacing
                by = base_y + int(row_height / 2)
                q_bubbles.append({
                    "option": letter,
                    "x": bx,
                    "y": by,
                    "r": q_bubble_r
                })
            question_bubbles[q_idx] = q_bubbles

        return {
            "canonical_width": W,
            "canonical_height": H,
            "fiducials": fiducials,
            "fid_centers": fid_centers,
            "roll_bubbles": roll_bubbles,
            "question_bubbles": question_bubbles,
            "roll_length": roll_length,
            "options_count": options_count,
            "question_count": question_count,
            "q_cols": q_cols,
            "questions_per_col": questions_per_col,
            "row_height": row_height,
        }

def draw_omr_sheet_canvas(
    c: canvas.Canvas, 
    x_offset: float, 
    y_offset: float, 
    target_w: float, 
    target_h: float, 
    exam: Any, 
    qr_data: dict
):
    """
    Renders a mathematically exact vector OMR Answer Sheet into a target rectangular box on canvas.
    Uses canonical coordinates [0..1200, 0..1600] to ensure 0% overlap and 100% CV alignment.
    """
    W_CANON = CANONICAL_OMR_WIDTH
    H_CANON = CANONICAL_OMR_HEIGHT

    scale_x = target_w / W_CANON
    scale_y = target_h / H_CANON
    scale_min = min(scale_x, scale_y)

    # Coordinate transformation functions: top-down canonical (cx, cy) -> ReportLab bottom-up
    def pt_x(cx: float) -> float:
        return x_offset + cx * scale_x

    def pt_y(cy: float) -> float:
        return y_offset + (H_CANON - cy) * scale_y

    def pt_w(w: float) -> float:
        return w * scale_x

    def pt_h(h: float) -> float:
        return h * scale_y

    def pt_r(r: float) -> float:
        return r * scale_min

    def pt_f(f: float) -> float:
        return max(4.0, f * scale_min)

    def draw_canon_rect(cx, cy, cw, ch, stroke=1, fill=0, s_col=None, f_col=None):
        if s_col: c.setStrokeColor(s_col)
        if f_col: c.setFillColor(f_col)
        c.rect(pt_x(cx), pt_y(cy + ch), pt_w(cw), pt_h(ch), stroke=stroke, fill=fill)

    c.saveState()

    # 1. Outer Border Box
    c.setLineWidth(1.2 * scale_min)
    draw_canon_rect(30, 30, 1140, 1540, stroke=1, fill=0, s_col=colors.HexColor("#1E293B"))

    # 2. Four Corner Solid Black Fiducial Squares (60x60 px)
    fid_sz = 60
    # TL
    draw_canon_rect(30, 30, fid_sz, fid_sz, stroke=0, fill=1, f_col=colors.black)
    # TR
    draw_canon_rect(W_CANON - 30 - fid_sz, 30, fid_sz, fid_sz, stroke=0, fill=1, f_col=colors.black)
    # BL
    draw_canon_rect(30, H_CANON - 30 - fid_sz, fid_sz, fid_sz, stroke=0, fill=1, f_col=colors.black)
    # BR
    draw_canon_rect(W_CANON - 30 - fid_sz, H_CANON - 30 - fid_sz, fid_sz, fid_sz, stroke=0, fill=1, f_col=colors.black)

    # 3. Header Text Information (Top Left of OMR)
    c.setFont("Helvetica-Bold", pt_f(22))
    c.setFillColor(colors.HexColor("#0F172A"))
    c.drawString(pt_x(110), pt_y(68), f"{exam.title} - OMR ANSWER SHEET")

    c.setFont("Helvetica-Bold", pt_f(11))
    c.setFillColor(colors.HexColor("#334155"))
    c.drawString(pt_x(110), pt_y(98), f"Subject: {exam.subject}   |   Exam Code: {exam.id}   |   Date: {exam.date_str or 'N/A'}")

    c.setFont("Helvetica-Oblique", pt_f(9.5))
    c.setFillColor(colors.HexColor("#64748B"))
    c.drawString(pt_x(110), pt_y(124), "Fill circles completely using dark blue/black ballpoint pen. Do not fold or tear this sheet.")

    # 4. QR Code (Top Right of OMR)
    qr_img = generate_qr_image(qr_data)
    qr_temp = Path(PDFS_DIR) / f"qr_{exam.id}.png"
    qr_img.save(str(qr_temp))
    qr_w = 110
    c.drawImage(
        str(qr_temp), 
        pt_x(W_CANON - 30 - fid_sz - qr_w - 15), 
        pt_y(40 + qr_w), 
        width=pt_w(qr_w), 
        height=pt_h(qr_w)
    )
    try:
        qr_temp.unlink(missing_ok=True)
    except Exception:
        pass

    # Horizontal Divider Line below Header
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(1 * scale_min)
    c.line(pt_x(30), pt_y(175), pt_x(W_CANON - 30), pt_y(175))

    # 5. Candidate Info Box (Left Box: x: 60, y: 195, w: 505, h: 360)
    c.setLineWidth(1 * scale_min)
    draw_canon_rect(60, 195, 505, 360, stroke=1, fill=1, s_col=colors.HexColor("#CBD5E1"), f_col=colors.HexColor("#F8FAFC"))
    
    # Header bar of candidate box
    draw_canon_rect(60, 195, 505, 32, stroke=1, fill=1, s_col=colors.HexColor("#CBD5E1"), f_col=colors.HexColor("#E2E8F0"))
    c.setFont("Helvetica-Bold", pt_f(11))
    c.setFillColor(colors.HexColor("#1E293B"))
    c.drawCentredString(pt_x(60 + 505 / 2), pt_y(217), "CANDIDATE DETAILS & MARKING INSTRUCTIONS")

    # Name and Signature fill-in lines
    c.setFont("Helvetica-Bold", pt_f(10))
    c.setFillColor(colors.HexColor("#334155"))
    c.drawString(pt_x(80), pt_y(260), "CANDIDATE NAME:")
    c.setStrokeColor(colors.HexColor("#64748B"))
    c.line(pt_x(230), pt_y(260), pt_x(545), pt_y(260))

    c.drawString(pt_x(80), pt_y(310), "SIGNATURE:")
    c.line(pt_x(185), pt_y(310), pt_x(545), pt_y(310))

    # Visual Marking Guide Inside Candidate Box
    draw_canon_rect(80, 345, 465, 185, stroke=1, fill=1, s_col=colors.HexColor("#CBD5E1"), f_col=colors.HexColor("#F1F5F9"))
    c.setFont("Helvetica-Bold", pt_f(9.5))
    c.setFillColor(colors.HexColor("#0F172A"))
    c.drawString(pt_x(95), pt_y(370), "MARKING RULES:")

    # Correct bubble illustration
    c.setFillColor(colors.black)
    c.circle(pt_x(120), pt_y(415), pt_r(11), stroke=0, fill=1)
    c.setFont("Helvetica-Bold", pt_f(9))
    c.drawString(pt_x(145), pt_y(418), "CORRECT (Dark & Full)")

    # Incorrect bubble illustrations
    c.setStrokeColor(colors.HexColor("#EF4444"))
    c.setLineWidth(1.5 * scale_min)
    # Crossed
    c.circle(pt_x(120), pt_y(465), pt_r(11), stroke=1, fill=0)
    c.line(pt_x(112), pt_y(473), pt_x(128), pt_y(457))
    c.line(pt_x(112), pt_y(457), pt_x(128), pt_y(473))
    c.setFont("Helvetica", pt_f(8.5))
    c.setFillColor(colors.HexColor("#64748B"))
    c.drawString(pt_x(145), pt_y(468), "WRONG (Crossed / Check)")

    # Half filled
    c.circle(pt_x(330), pt_y(465), pt_r(11), stroke=1, fill=0)
    c.setFillColor(colors.black)
    c.wedge(pt_x(319), pt_y(476), pt_x(341), pt_y(454), 0, 180, stroke=0, fill=1)
    c.drawString(pt_x(355), pt_y(468), "WRONG (Half filled)")

    c.setFont("Helvetica-Oblique", pt_f(8))
    c.setFillColor(colors.HexColor("#475569"))
    c.drawString(pt_x(95), pt_y(512), "Use only black or blue pen. Marks with pencil will be rejected.")

    # 6. Roll Number Section (Right Box: x: 585, y: 195, w: 555, h: 360)
    draw_canon_rect(585, 195, 555, 360, stroke=1, fill=1, s_col=colors.HexColor("#CBD5E1"), f_col=colors.HexColor("#F8FAFC"))

    # Header bar of roll box
    draw_canon_rect(585, 195, 555, 32, stroke=1, fill=1, s_col=colors.HexColor("#CBD5E1"), f_col=colors.HexColor("#E2E8F0"))
    c.setFont("Helvetica-Bold", pt_f(11))
    c.setFillColor(colors.HexColor("#1E293B"))
    c.drawCentredString(pt_x(585 + 555 / 2), pt_y(217), "STUDENT ROLL NUMBER")

    # Layout roll bubbles
    roll_len = exam.roll_length or 6
    layout = OMRLayoutSpec.get_layout(
        question_count=len(exam.questions),
        options_count=exam.options_per_question or 4,
        roll_length=roll_len
    )

    # Roll write-in boxes at top of columns
    c.setFont("Helvetica-Bold", pt_f(9))
    c.setFillColor(colors.HexColor("#475569"))
    for col_idx in range(roll_len):
        first_b = layout["roll_bubbles"][col_idx][0]
        bx = first_b["x"]
        draw_canon_rect(bx - 18, 250, 36, 26, stroke=1, fill=1, s_col=colors.HexColor("#334155"), f_col=colors.white)

    # Draw Roll Bubbles 0 to 9
    c.setLineWidth(1 * scale_min)
    for col in layout["roll_bubbles"]:
        for b in col:
            c.setStrokeColor(colors.HexColor("#334155"))
            c.setFillColor(colors.white)
            c.circle(pt_x(b["x"]), pt_y(b["y"]), pt_r(b["r"]), stroke=1, fill=1)
            
            # Digit text centered inside circle
            c.setFont("Helvetica", pt_f(10.5))
            c.setFillColor(colors.HexColor("#1E293B"))
            c.drawCentredString(pt_x(b["x"]), pt_y(b["y"] + 3.5), str(b["digit"]))

    # 7. Divider Line with Section Title for Questions
    draw_canon_rect(60, 575, 1080, 28, stroke=0, fill=1, f_col=colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", pt_f(12))
    c.setFillColor(colors.white)
    c.drawCentredString(pt_x(W_CANON / 2), pt_y(594), "CANDIDATE RESPONSES / ANSWER BUBBLES")

    # 8. Question Response Bubbles
    q_bubbles_map = layout["question_bubbles"]
    row_h = layout["row_height"]
    q_count = len(exam.questions)

    for q_idx in range(1, q_count + 1):
        bubbles = q_bubbles_map.get(q_idx, [])
        if not bubbles:
            continue

        first_b = bubbles[0]
        cy = first_b["y"]

        # Alternate light background tint on every even row
        if q_idx % 2 == 0:
            c.setFillColor(colors.HexColor("#F8FAFC"))
            col_idx = (q_idx - 1) // layout["questions_per_col"]
            base_x = 70 + col_idx * (1060 // layout["q_cols"])
            col_w = (1060 // layout["q_cols"]) - 20
            c.rect(pt_x(base_x), pt_y(cy + row_h / 2 - 2), pt_w(col_w), pt_h(row_h - 2), stroke=0, fill=1)

        # Question number badge: e.g. [ 01 ]
        q_label_x = first_b["x"] - 55
        c.setFillColor(colors.HexColor("#1E293B"))
        c.setFont("Helvetica-Bold", pt_f(13))
        c.drawRightString(pt_x(q_label_x), pt_y(cy + 4), f"Q{q_idx:02d}")

        # Option bubbles (A, B, C, D)
        for b in bubbles:
            # Circle
            c.setStrokeColor(colors.HexColor("#1E293B"))
            c.setLineWidth(1.2 * scale_min)
            c.setFillColor(colors.white)
            c.circle(pt_x(b["x"]), pt_y(b["y"]), pt_r(b["r"]), stroke=1, fill=1)

            # Option letter centered inside circle
            c.setFont("Helvetica-Bold", pt_f(11))
            c.setFillColor(colors.HexColor("#1E293B"))
            c.drawCentredString(pt_x(b["x"]), pt_y(b["y"] + 3.8), b["option"])

    c.restoreState()

def generate_exam_pdf(exam: Any) -> str:
    """
    Generates a high-precision, ready-to-print vector PDF for the exam.
    Auto-adapts between Split (Side-by-Side on A4 Landscape) and Duplex (Multi-page A4 Portrait).
    """
    pdf_filename = f"exam_{exam.id}.pdf"
    pdf_path = PDFS_DIR / pdf_filename

    qr_payload = {
        "id": exam.id,
        "title": exam.title,
        "q": len(exam.questions),
        "opt": exam.options_per_question,
        "roll": exam.roll_length,
        "layout": exam.layout_type
    }

    layout_mode = exam.layout_type or ("split" if len(exam.questions) <= 25 else "duplex")

    if layout_mode == "split":
        # A4 Landscape: 841.89 x 595.27 points
        w, h = landscape(A4)
        c = canvas.Canvas(str(pdf_path), pagesize=(w, h))

        # Vertical Dotted Divider with Scissor Cut Guide
        center_x = 425
        c.setDash(4, 4)
        c.setStrokeColor(colors.HexColor("#94A3B8"))
        c.setLineWidth(1)
        c.line(center_x, 15, center_x, h - 15)
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(colors.HexColor("#64748B"))
        c.drawCentredString(center_x, h - 12, "✂  TEAR OR CUT OFF OMR SHEET HERE  ✂")
        c.setDash()

        # ==========================================
        # LEFT HALF: QUESTION PAPER
        # ==========================================
        left_margin = 28
        left_w = center_x - left_margin - 18 # approx 380 points

        # Question Paper Header
        c.setFillColor(colors.HexColor("#0F172A"))
        c.setFont("Helvetica-Bold", 15)
        c.drawString(left_margin, h - 35, exam.title)

        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#475569"))
        total_marks = len(exam.questions) * (exam.positive_marks or 1.0)
        c.drawString(
            left_margin, 
            h - 50, 
            f"Subject: {exam.subject}   |   Total Marks: {total_marks:.0f}   |   Date: {exam.date_str or 'N/A'}"
        )

        c.setStrokeColor(colors.HexColor("#0F172A"))
        c.setLineWidth(1.2)
        c.line(left_margin, h - 56, left_margin + left_w, h - 56)

        # Questions Formatting
        styles = getSampleStyleSheet()
        q_title_style = ParagraphStyle(
            'QTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#0F172A")
        )
        opt_style = ParagraphStyle(
            'QOpt',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#334155")
        )

        curr_y = h - 75
        opt_labels = ["A", "B", "C", "D", "E"]

        for q in exam.questions:
            if curr_y < 40:
                break # Safeguard

            # Question Text
            q_p = Paragraph(f"<b>Q{q.question_number}.</b> {q.question_text}", q_title_style)
            pw, ph = q_p.wrap(left_w, 200)
            q_p.drawOn(c, left_margin, curr_y - ph)
            curr_y -= (ph + 5)

            # Options Table (clean 2-column or 4-column layout)
            opts = q.options[:exam.options_per_question or 4]
            # Determine if options are short enough for 4-in-a-row
            max_opt_len = max([len(str(o)) for o in opts]) if opts else 0

            if max_opt_len <= 14 and len(opts) == 4:
                # 4 in a row
                table_data = [[
                    Paragraph(f"<b>({opt_labels[i]})</b> {opts[i]}", opt_style) for i in range(4)
                ]]
                col_widths = [left_w / 4] * 4
            else:
                # 2 rows of 2 options
                row1 = [Paragraph(f"<b>({opt_labels[i]})</b> {opts[i]}", opt_style) for i in range(min(2, len(opts)))]
                row2 = [Paragraph(f"<b>({opt_labels[i]})</b> {opts[i]}", opt_style) for i in range(2, len(opts))]
                table_data = [row1, row2] if row2 else [row1]
                col_widths = [left_w / 2] * 2

            t = Table(table_data, colWidths=col_widths)
            t.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            tw, th = t.wrap(left_w, 200)
            t.drawOn(c, left_margin, curr_y - th)
            curr_y -= (th + 12)

        # ==========================================
        # RIGHT HALF: PRECISION OMR SHEET
        # ==========================================
        right_x = center_x + 15
        right_w = w - right_x - 18 # approx 384 points
        right_h = h - 36           # approx 559 points
        draw_omr_sheet_canvas(c, right_x, 18, right_w, right_h, exam, qr_payload)

        c.showPage()
        c.save()

    else:
        # Duplex / Multi-Page Format: Page 1..N Questions, Final Page Full A4 OMR
        w, h = A4 # 595.27 x 841.89 points
        c = canvas.Canvas(str(pdf_path), pagesize=A4)

        # Page 1: Questions Booklet
        styles = getSampleStyleSheet()
        q_title_style = ParagraphStyle(
            'QTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#0F172A")
        )
        opt_style = ParagraphStyle(
            'QOpt',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#334155")
        )

        margin = 35
        content_w = w - 2 * margin

        c.setFont("Helvetica-Bold", 17)
        c.drawString(margin, h - 45, exam.title)
        c.setFont("Helvetica", 10)
        c.drawString(
            margin, 
            h - 62, 
            f"Subject: {exam.subject}   |   Total Marks: {len(exam.questions) * exam.positive_marks:.0f}   |   Date: {exam.date_str or 'N/A'}"
        )
        c.setStrokeColor(colors.HexColor("#0F172A"))
        c.setLineWidth(1.2)
        c.line(margin, h - 70, margin + content_w, h - 70)

        curr_y = h - 90
        opt_labels = ["A", "B", "C", "D", "E"]

        for q in exam.questions:
            if curr_y < 60:
                c.showPage()
                curr_y = h - 50

            q_p = Paragraph(f"<b>Q{q.question_number}.</b> {q.question_text}", q_title_style)
            pw, ph = q_p.wrap(content_w, 300)
            q_p.drawOn(c, margin, curr_y - ph)
            curr_y -= (ph + 6)

            opts = q.options[:exam.options_per_question or 4]
            # 2 rows of 2 options
            row1 = [Paragraph(f"<b>({opt_labels[i]})</b> {opts[i]}", opt_style) for i in range(min(2, len(opts)))]
            row2 = [Paragraph(f"<b>({opt_labels[i]})</b> {opts[i]}", opt_style) for i in range(2, len(opts))]
            table_data = [row1, row2] if row2 else [row1]
            t = Table(table_data, colWidths=[content_w / 2] * 2)
            t.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            tw, th = t.wrap(content_w, 200)
            t.drawOn(c, margin, curr_y - th)
            curr_y -= (th + 14)

        # Dedicated Final Page: Full-Page OMR Sheet
        c.showPage()
        draw_omr_sheet_canvas(c, margin, margin, w - 2 * margin, h - 2 * margin, exam, qr_payload)
        c.showPage()
        c.save()

    return str(pdf_path)
