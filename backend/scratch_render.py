import os
import json
import fitz # PyMuPDF
from pathlib import Path
from types import SimpleNamespace
from app.services.pdf_generator import generate_exam_pdf
from app.config import PDFS_DIR

def render_sample():
    questions = [
        SimpleNamespace(
            question_number=1,
            question_text="How many type of tenses are there?",
            options=["5", "9", "6", "3"],
            correct_option="C",
            marks=1.0,
            negative_marks=0.25
        ),
        SimpleNamespace(
            question_number=2,
            question_text="How many type of tenses are there according to work?",
            options=["8", "4", "6", "1"],
            correct_option="B",
            marks=1.0,
            negative_marks=0.25
        ),
        SimpleNamespace(
            question_number=3,
            question_text="What is the acceleration due to gravity on Earth?",
            options=["8.9 m/s²", "9.8 m/s²", "10.8 m/s²", "12.0 m/s²"],
            correct_option="B",
            marks=1.0,
            negative_marks=0.25
        ),
        SimpleNamespace(
            question_number=4,
            question_text="Which of the following is a renewable source of energy?",
            options=["Coal", "Petroleum", "Solar Energy", "Natural Gas"],
            correct_option="C",
            marks=1.0,
            negative_marks=0.25
        )
    ]

    exam = SimpleNamespace(
        id="8578301E",
        title="English Test",
        subject="English",
        date_str="2026-10-02",
        roll_length=6,
        options_per_question=4,
        layout_type="split",
        positive_marks=1.0,
        negative_marks=0.25,
        questions=questions
    )

    pdf_path = generate_exam_pdf(exam)
    print("Generated PDF at:", pdf_path)

    # Render first page as PNG using PyMuPDF
    doc = fitz.open(pdf_path)
    page = doc[0]
    pix = page.get_pixmap(dpi=150)
    out_png = Path(PDFS_DIR) / "test_render_page1.png"
    pix.save(str(out_png))
    print("Rendered PNG at:", out_png)

if __name__ == "__main__":
    render_sample()
