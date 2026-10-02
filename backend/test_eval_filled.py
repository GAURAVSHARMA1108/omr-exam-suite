import cv2
import numpy as np
from types import SimpleNamespace
from app.services.pdf_generator import OMRLayoutSpec, CANONICAL_OMR_WIDTH, CANONICAL_OMR_HEIGHT
from app.services.omr_processor import process_omr_sheet, warp_to_canonical, find_omr_corners

def test_eval_filled():
    # 1. Load rendered OMR half
    omr_half = cv2.imread("storage/pdfs/test_omr_half_blank.png")
    gray = cv2.cvtColor(omr_half, cv2.COLOR_BGR2GRAY)

    # 2. Warp to canonical so we can bubble in canonical coordinates
    corners = find_omr_corners(gray)
    warped_color, _ = warp_to_canonical(omr_half, corners)

    # 3. Setup Layout
    layout = OMRLayoutSpec.get_layout(question_count=4, options_count=4, roll_length=6)

    # Fill Roll Number: 3, 5, 0, 9, 2, 7
    target_roll = [3, 5, 0, 9, 2, 7]
    for col_idx, d in enumerate(target_roll):
        b = layout["roll_bubbles"][col_idx][d]
        cv2.circle(warped_color, (int(b["x"]), int(b["y"])), int(b["r"] - 1), (15, 15, 15), -1)

    # Fill Questions:
    # Q1: C (Correct)
    b1 = next(x for x in layout["question_bubbles"][1] if x["option"] == "C")
    cv2.circle(warped_color, (int(b1["x"]), int(b1["y"])), int(b1["r"] - 1), (20, 20, 20), -1)

    # Q2: B (Correct)
    b2 = next(x for x in layout["question_bubbles"][2] if x["option"] == "B")
    cv2.circle(warped_color, (int(b2["x"]), int(b2["y"])), int(b2["r"] - 1), (20, 20, 20), -1)

    # Q3: A (Wrong - Key was B)
    b3 = next(x for x in layout["question_bubbles"][3] if x["option"] == "A")
    cv2.circle(warped_color, (int(b3["x"]), int(b3["y"])), int(b3["r"] - 1), (20, 20, 20), -1)

    # Q4: C (Correct)
    b4 = next(x for x in layout["question_bubbles"][4] if x["option"] == "C")
    cv2.circle(warped_color, (int(b4["x"]), int(b4["y"])), int(b4["r"] - 1), (20, 20, 20), -1)

    # Save filled sheet
    cv2.imwrite("storage/pdfs/test_omr_filled.png", warped_color)

    # 4. Setup Exam definition
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

    # 5. Run Evaluation
    res = process_omr_sheet("storage/pdfs/test_omr_filled.png", exam, save_overlay=True)

    print("Evaluated Filled Sheet Results:")
    print("Detected Roll:", res.student_roll)
    print("Correct Count:", res.correct_count)
    print("Incorrect Count:", res.incorrect_count)
    print("Unanswered Count:", res.unanswered_count)
    print(f"Total Score: {res.total_score} / {res.max_score} ({res.percentage}%)")
    print("Overlay saved at:", res.overlay_path)

    assert res.student_roll == "350927"
    assert res.correct_count == 3
    assert res.incorrect_count == 1
    assert res.unanswered_count == 0
    # 3 correct * 1.0 - 1 incorrect * 0.25 = 2.75
    assert res.total_score == 2.75

    print("\nALL EVALUATION CHECKS PASSED WITH 100% ACCURACY!")

if __name__ == "__main__":
    test_eval_filled()
