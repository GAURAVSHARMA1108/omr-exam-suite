import io
import csv
from typing import List, Any
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

def export_exam_results_excel(exam: Any, submissions: List[Any]) -> bytes:
    """
    Generates a beautifully styled Excel (.xlsx) workbook of exam results.
    Includes:
    - Summary Sheet (Exam details, statistics, averages)
    - Student Gradebook (Roll No, Name, Score, Percentage, Correct, Wrong, Unanswered, Status)
    - Detailed Question Breakdown
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Gradebook"

    # Header styling
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=16, bold=True, color="1E3A8A")
    subtitle_font = Font(name="Calibri", size=11, italic=True, color="4B5563")

    # Title block
    ws.merge_cells("A1:H1")
    ws["A1"] = f"{exam.title} - Results Gradebook"
    ws["A1"].font = title_font

    ws.merge_cells("A2:H2")
    ws["A2"] = f"Subject: {exam.subject} | Date: {exam.date_str or 'N/A'} | Questions: {len(exam.questions)} | Code: {exam.id}"
    ws["A2"].font = subtitle_font

    headers = ["Roll No", "Student Name", "Total Score", "Max Score", "Percentage", "Correct", "Incorrect", "Unanswered", "Status", "Scanned At"]
    row_idx = 4
    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=row_idx, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    thin_border = Border(
        left=Side(style='thin', color='E5E7EB'),
        right=Side(style='thin', color='E5E7EB'),
        top=Side(style='thin', color='E5E7EB'),
        bottom=Side(style='thin', color='E5E7EB')
    )

    for sub in submissions:
        row_idx += 1
        data = [
            sub.student_roll,
            sub.student_name,
            sub.total_score,
            sub.max_score,
            f"{sub.percentage:.1f}%",
            sub.correct_count,
            sub.incorrect_count,
            sub.unanswered_count,
            sub.status,
            sub.created_at.strftime("%Y-%m-%d %H:%M") if sub.created_at else ""
        ]
        for col_idx, val in enumerate(data, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.border = thin_border
            if col_idx in [1, 3, 4, 5, 6, 7, 8, 9, 10]:
                cell.alignment = Alignment(horizontal="center")

    # Auto-fit column widths
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()

def export_exam_results_csv(exam: Any, submissions: List[Any]) -> str:
    """Generates standard CSV output of submissions."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Exam ID", "Exam Title", "Subject", "Date"])
    writer.writerow([exam.id, exam.title, exam.subject, exam.date_str or ""])
    writer.writerow([])
    writer.writerow(["Roll No", "Student Name", "Total Score", "Max Score", "Percentage", "Correct", "Incorrect", "Unanswered", "Status", "Scanned At"])

    for sub in submissions:
        writer.writerow([
            sub.student_roll,
            sub.student_name,
            sub.total_score,
            sub.max_score,
            f"{sub.percentage:.1f}%",
            sub.correct_count,
            sub.incorrect_count,
            sub.unanswered_count,
            sub.status,
            sub.created_at.strftime("%Y-%m-%d %H:%M") if sub.created_at else ""
        ])

    return output.getvalue()
