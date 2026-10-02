import fitz
from pathlib import Path
from types import SimpleNamespace
from app.services.pdf_generator import generate_exam_pdf
from app.config import PDFS_DIR

def render_variations():
    # 1. 20-Question Exam (Split Layout)
    q20 = [
        SimpleNamespace(
            question_number=i,
            question_text=f"Sample Question #{i} prompt for testing layout and options wrapping?",
            options=[f"Choice A for Q{i}", f"Choice B for Q{i}", f"Choice C for Q{i}", f"Choice D for Q{i}"],
            correct_option=["A", "B", "C", "D"][i % 4],
            marks=1.0,
            negative_marks=0.25
        )
        for i in range(1, 21)
    ]
    exam20 = SimpleNamespace(
        id="EXAM20Q",
        title="Comprehensive Science Assessment (20 Questions)",
        subject="General Science",
        date_str="2026-10-02",
        roll_length=6,
        options_per_question=4,
        layout_type="split",
        positive_marks=1.0,
        negative_marks=0.25,
        questions=q20
    )
    pdf_20 = generate_exam_pdf(exam20)
    doc20 = fitz.open(pdf_20)
    pix20 = doc20[0].get_pixmap(dpi=150)
    out20 = Path(PDFS_DIR) / "test_render_20q.png"
    pix20.save(str(out20))
    print("Rendered 20Q to:", out20)

if __name__ == "__main__":
    render_variations()
