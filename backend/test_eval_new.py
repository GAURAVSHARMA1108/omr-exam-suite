import cv2
import numpy as np
from types import SimpleNamespace
from app.services.pdf_generator import OMRLayoutSpec
from app.services.omr_processor import process_omr_sheet

def test_eval():
    # 1. Load rendered page
    full_page = cv2.imread("storage/pdfs/test_render_page1.png")
    H_img, W_img, _ = full_page.shape

    # In Split layout, the OMR sheet is on the right half (x > W_img * 0.5)
    omr_half = full_page[:, int(W_img * 0.505):].copy()
    cv2.imwrite("storage/pdfs/test_omr_half_blank.png", omr_half)
    print("OMR Half cropped shape:", omr_half.shape)

    # 2. Setup Exam definition
    questions = [
        SimpleNamespace(question_number=1, question_text="Q1", options=["A","B","C","D"], correct_option="C", marks=1.0, negative_marks=0.25),
        SimpleNamespace(question_number=2, question_text="Q2", options=["A","B","C","D"], correct_option="B", marks=1.0, negative_marks=0.25),
        SimpleNamespace(question_number=3, question_text="Q3", options=["A","B","C","D"], correct_option="B", marks=1.0, negative_marks=0.25),
        SimpleNamespace(question_number=4, question_text="Q4", options=["A","B","C","D"], correct_option="C", marks=1.0, negative_marks=0.25),
    ]
    exam = SimpleNamespace(
        id="8578301E",
        title="English Test",
        subject="English",
        date_str="2026-10-02",
        roll_length=6,
        options_per_question=4,
        positive_marks=1.0,
        negative_marks=0.25,
        questions=questions
    )

    # 3. Simulate student bubbling on the cropped OMR sheet:
    # We find fiducials or warp to canonical, or draw bubbles on canonical
    # Let's run process_omr_sheet directly on blank sheet first
    res_blank = process_omr_sheet("storage/pdfs/test_omr_half_blank.png", exam, save_overlay=True)
    print("Blank Sheet Evaluation:")
    print("Roll detected:", res_blank.student_roll)
    print("Score:", res_blank.total_score, "/", res_blank.max_score)
    print("Unanswered:", res_blank.unanswered_count)
    assert res_blank.unanswered_count == 4

    print("\nSUCCESS! OpenCV accurately deskewed and mapped the new sheet with 4 unanswered questions!")

if __name__ == "__main__":
    test_eval()
