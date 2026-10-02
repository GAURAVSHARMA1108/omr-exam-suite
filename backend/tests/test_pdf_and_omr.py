import pytest
import os
import cv2
import numpy as np
from types import SimpleNamespace
from app.services.pdf_generator import generate_exam_pdf, OMRLayoutSpec
from app.services.omr_processor import process_omr_sheet, warp_to_canonical

def test_pdf_generation():
    questions = [
        SimpleNamespace(
            question_number=i,
            question_text=f"Sample Question #{i} text",
            options=["Option Alpha", "Option Beta", "Option Gamma", "Option Delta"],
            correct_option=["A", "B", "C", "D"][i % 4],
            marks=1.0,
            negative_marks=0.0
        )
        for i in range(1, 11)
    ]
    exam = SimpleNamespace(
        id="TEST101",
        title="Physics Midterm Quiz",
        subject="Physics",
        date_str="2026-10-01",
        roll_length=6,
        options_per_question=4,
        layout_type="split",
        positive_marks=1.0,
        negative_marks=0.0,
        questions=questions
    )

    # 1. Test Split PDF generation
    pdf_split_path = generate_exam_pdf(exam)
    assert os.path.exists(pdf_split_path)
    assert os.path.getsize(pdf_split_path) > 1000

    # 2. Test Duplex PDF generation
    exam.layout_type = "duplex"
    pdf_duplex_path = generate_exam_pdf(exam)
    assert os.path.exists(pdf_duplex_path)
    assert os.path.getsize(pdf_duplex_path) > 1000

def test_omr_cv_processing(tmp_path):
    # Construct a synthetic filled sheet matching canonical dimensions (1200 x 1600)
    questions = [
        SimpleNamespace(
            question_number=i,
            question_text=f"Question {i}",
            options=["A", "B", "C", "D"],
            correct_option="A" if i % 2 == 1 else "B",
            marks=1.0,
            negative_marks=0.25
        )
        for i in range(1, 11)
    ]
    exam = SimpleNamespace(
        id="TEST102",
        title="Chemistry Quiz",
        subject="Chemistry",
        date_str="2026-10-01",
        roll_length=6,
        options_per_question=4,
        positive_marks=1.0,
        negative_marks=0.25,
        questions=questions
    )

    layout = OMRLayoutSpec.get_layout(question_count=10, options_count=4, roll_length=6)
    W, H = layout["canonical_width"], layout["canonical_height"]
    img = np.ones((H, W, 3), dtype=np.uint8) * 255

    # Draw corner fiducials
    m, sz = 40, 50
    cv2.rectangle(img, (m, m), (m + sz, m + sz), (0, 0, 0), -1)
    cv2.rectangle(img, (W - m - sz, m), (W - m, m + sz), (0, 0, 0), -1)
    cv2.rectangle(img, (m, H - m - sz), (m + sz, H - m), (0, 0, 0), -1)
    cv2.rectangle(img, (W - m - sz, H - m - sz), (W - m, H - m), (0, 0, 0), -1)

    # Fill Roll Number: 4 2 0 1 9 5
    target_roll = [4, 2, 0, 1, 9, 5]
    for col_idx, col in enumerate(layout["roll_bubbles"]):
        d = target_roll[col_idx]
        b = col[d]
        cv2.circle(img, (int(b["x"]), int(b["y"])), int(b["r"]), (10, 10, 10), -1)

    # Fill Questions:
    # Q1..Q8 correct, Q9 wrong, Q10 unanswered
    for q_idx in range(1, 9):
        q_ans = exam.questions[q_idx - 1].correct_option # "A" or "B"
        b = next(x for x in layout["question_bubbles"][q_idx] if x["option"] == q_ans)
        cv2.circle(img, (int(b["x"]), int(b["y"])), int(b["r"]), (15, 15, 15), -1)

    # Q9: wrong answer (filled 'D')
    b9 = next(x for x in layout["question_bubbles"][9] if x["option"] == "D")
    cv2.circle(img, (int(b9["x"]), int(b9["y"])), int(b9["r"]), (15, 15, 15), -1)

    # Save synthetic image
    test_img_path = str(tmp_path / "synthetic_test.jpg")
    cv2.imwrite(test_img_path, img)

    # Run OMR processor
    result = process_omr_sheet(test_img_path, exam, save_overlay=False)

    assert result.student_roll == "420195"
    assert result.correct_count == 8
    assert result.incorrect_count == 1
    assert result.unanswered_count == 1
    # 8 correct * 1.0 - 1 wrong * 0.25 = 7.75
    assert result.total_score == 7.75
    assert result.overlay_base64.startswith("data:image/jpeg;base64,")
