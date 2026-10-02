import urllib.request
import json
import time

def test():
    print("--- 1. Testing Backend Health ---")
    req = urllib.request.urlopen("http://127.0.0.1:8000/api/health")
    data = json.loads(req.read().decode())
    print("Backend Health:", data)
    assert data["status"] == "healthy"

    print("--- 2. Testing Scanner Bridge Status ---")
    req = urllib.request.urlopen("http://127.0.0.1:8765/status")
    bridge_data = json.loads(req.read().decode())
    print("Scanner Bridge Status:", bridge_data)
    assert bridge_data["online"] is True

    print("--- 3. Testing Exam Creation ---")
    exam_payload = {
        "title": "Mathematics Quick Assessment",
        "subject": "Mathematics",
        "date_str": "2026-10-01",
        "instructions": "Darken bubbles completely using black ballpoint pen.",
        "roll_length": 6,
        "options_per_question": 4,
        "layout_type": "split",
        "positive_marks": 1.0,
        "negative_marks": 0.25,
        "questions": [
            {
                "question_number": 1,
                "question_text": "What is 15 * 12?",
                "options": ["160", "180", "190", "200"],
                "correct_option": "B",
                "marks": 1.0,
                "negative_marks": 0.25
            },
            {
                "question_number": 2,
                "question_text": "Solve for x: 2x + 6 = 20",
                "options": ["5", "6", "7", "8"],
                "correct_option": "C",
                "marks": 1.0,
                "negative_marks": 0.25
            },
            {
                "question_number": 3,
                "question_text": "What is the square root of 144?",
                "options": ["10", "11", "12", "14"],
                "correct_option": "C",
                "marks": 1.0,
                "negative_marks": 0.25
            }
        ]
    }
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/exams",
        data=json.dumps(exam_payload).encode(),
        headers={"Content-Type": "application/json"}
    )
    res = urllib.request.urlopen(req)
    created_exam = json.loads(res.read().decode())
    exam_id = created_exam["id"]
    print(f"Created Exam: ID={exam_id}, Title='{created_exam['title']}', Questions={len(created_exam['questions'])}")

    print("--- 4. Testing Ready-to-Print PDF Generation ---")
    pdf_req = urllib.request.urlopen(f"http://127.0.0.1:8000/api/exams/{exam_id}/pdf")
    pdf_bytes = pdf_req.read()
    print(f"Downloaded PDF: {len(pdf_bytes)} bytes")
    assert len(pdf_bytes) > 2000

    print("--- 5. Testing Scanner Acquisition & OMR Grading ---")
    scan_req = urllib.request.Request(
        "http://127.0.0.1:8765/scan",
        data=json.dumps({"device_id": "EMULATED_SCANNER", "source": "flatbed", "dpi": 200, "use_emulated": True}).encode(),
        headers={"Content-Type": "application/json"}
    )
    scan_res = urllib.request.urlopen(scan_req)
    scan_data = json.loads(scan_res.read().decode())
    print(f"Acquired Scanned Pages: {len(scan_data['pages'])} from {scan_data['device']}")

    grade_payload = {
        "image_base64": scan_data["pages"][0],
        "exam_id": exam_id,
        "student_name": "Jordan Smith"
    }
    grade_req = urllib.request.Request(
        "http://127.0.0.1:8000/api/grading/base64",
        data=json.dumps(grade_payload).encode(),
        headers={"Content-Type": "application/json"}
    )
    grade_res = urllib.request.urlopen(grade_req)
    sub = json.loads(grade_res.read().decode())
    print(f"OMR Evaluation Succeeded!")
    print(f"Student Roll: {sub['student_roll']}")
    print(f"Score: {sub['total_score']} / {sub['max_score']} ({sub['percentage']}%)")
    print(f"Correct: {sub['correct_count']} | Incorrect: {sub['incorrect_count']} | Blank: {sub['unanswered_count']}")
    print(f"Visual Overlay Created: {bool(sub.get('overlay_image_path'))}")

    print("--- 6. Testing Excel Export ---")
    excel_req = urllib.request.urlopen(f"http://127.0.0.1:8000/api/submissions/exam/{exam_id}/export/excel")
    excel_bytes = excel_req.read()
    print(f"Excel Gradebook Exported: {len(excel_bytes)} bytes")
    assert len(excel_bytes) > 1000

    print("\nSUCCESS! ALL 6 END-TO-END VERIFICATIONS PASSED CLEANLY!")

if __name__ == "__main__":
    test()
