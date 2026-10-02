import cv2
import numpy as np
import json
import base64
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from PIL import Image

from app.services.pdf_generator import OMRLayoutSpec, CANONICAL_OMR_WIDTH, CANONICAL_OMR_HEIGHT
from app.config import OVERLAYS_DIR

def decode_qr_metadata(image: np.ndarray) -> Optional[Dict[str, Any]]:
    """Attempts to find and decode the QR code from the input image."""
    detector = cv2.QRCodeDetector()
    data, bbox, _ = detector.detectAndDecode(image)
    if data:
        try:
            return json.loads(data)
        except Exception:
            return None
    return None

def order_points(pts: np.ndarray) -> np.ndarray:
    """Orders 4 points as: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)] # TL
    rect[2] = pts[np.argmax(s)] # BR

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)] # TR
    rect[3] = pts[np.argmax(diff)] # BL
    return rect

def find_omr_corners(gray_img: np.ndarray) -> Optional[np.ndarray]:
    """
    Locates the 4 corner fiducial markers of the OMR section.
    Returns ordered 4 corner coordinates (TL, TR, BR, BL) or None if not found.
    """
    H, W = gray_img.shape
    blurred = cv2.GaussianBlur(gray_img, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 21, 5
    )

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Fiducials are solid black squares (in inverted thresh they are solid white squares)
    candidate_squares = []
    min_area = (W * H) * 0.0001
    max_area = (W * H) * 0.05

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if min_area < area < max_area:
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                aspect_ratio = float(w) / max(h, 1)
                if 0.7 <= aspect_ratio <= 1.4:
                    M = cv2.moments(cnt)
                    if M["m00"] > 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        candidate_squares.append((cx, cy, area))

    if len(candidate_squares) >= 4:
        # Pick the 4 candidates closest to the 4 corners of the image
        corners_target = [(0, 0), (W, 0), (W, H), (0, H)]
        chosen = []
        for tx, ty in corners_target:
            best = min(candidate_squares, key=lambda p: (p[0] - tx)**2 + (p[1] - ty)**2)
            chosen.append([best[0], best[1]])
        
        # Verify they are reasonably separated
        chosen_pts = np.array(chosen, dtype="float32")
        return order_points(chosen_pts)

    # Secondary heuristic: look for large rectangular contour bounding the OMR zone
    for cnt in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.03 * peri, True)
        if len(approx) == 4 and cv2.contourArea(approx) > (W * H * 0.25):
            pts = approx.reshape(4, 2).astype("float32")
            return order_points(pts)

    return None

def warp_to_canonical(
    color_img: np.ndarray, 
    corners: Optional[np.ndarray] = None
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Warps the OMR region to canonical (CANONICAL_OMR_WIDTH, CANONICAL_OMR_HEIGHT).
    The 4 fiducials are centered at (65, 65), (W-65, 65), (W-65, H-65), (65, H-65).
    """
    W, H = CANONICAL_OMR_WIDTH, CANONICAL_OMR_HEIGHT
    
    # Fiducials: offset 30 + size 60 -> center is 60
    cx_tl, cy_tl = 60, 60
    cx_tr, cy_tr = W - 60, 60
    cx_br, cy_br = W - 60, H - 60
    cx_bl, cy_bl = 60, H - 60

    dst_pts = np.array([
        [cx_tl, cy_tl],
        [cx_tr, cy_tr],
        [cx_br, cy_br],
        [cx_bl, cy_bl]
    ], dtype="float32")

    if corners is not None:
        M = cv2.getPerspectiveTransform(corners, dst_pts)
        warped_color = cv2.warpPerspective(color_img, M, (W, H))
    else:
        # Fallback: direct resize if no fiducials extracted
        warped_color = cv2.resize(color_img, (W, H))

    warped_gray = cv2.cvtColor(warped_color, cv2.COLOR_BGR2GRAY)
    return warped_color, warped_gray

def measure_bubble_fill(thresh_img: np.ndarray, cx: int, cy: int, r: int) -> float:
    """
    Calculates fill ratio of a circular bubble at (cx, cy) with radius r.
    Uses an inner circular mask to ignore the printed border ring.
    """
    inner_r = max(1, int(r * 0.75))
    mask = np.zeros(thresh_img.shape, dtype="uint8")
    cv2.circle(mask, (int(cx), int(cy)), inner_r, 255, -1)

    total_pixels = np.count_nonzero(mask)
    if total_pixels == 0:
        return 0.0

    filled_pixels = cv2.countNonZero(cv2.bitwise_and(thresh_img, mask))
    return float(filled_pixels) / float(total_pixels)

class OMRResult:
    def __init__(self):
        self.exam_id: Optional[str] = None
        self.student_roll: str = "UNKNOWN"
        self.total_score: float = 0.0
        self.max_score: float = 0.0
        self.percentage: float = 0.0
        self.correct_count: int = 0
        self.incorrect_count: int = 0
        self.unanswered_count: int = 0
        self.answers: List[Dict[str, Any]] = []
        self.overlay_base64: str = ""
        self.overlay_path: Optional[str] = None
        self.status: str = "graded"

def process_omr_sheet(
    image_path: str,
    exam_model: Any, # SQLAlchemy Exam model
    save_overlay: bool = True
) -> OMRResult:
    """
    Full computer vision evaluation pipeline:
    1. Loads image
    2. Identifies QR or uses exam_model
    3. Finds fiducials & warps to canonical reference
    4. Evaluates Roll Number & Question Bubbles
    5. Calculates score and creates color-coded visual overlay
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image file at {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Attempt QR reading for zero-config exam detection
    qr_data = decode_qr_metadata(gray)
    
    # 1. Perspective Transform
    corners = find_omr_corners(gray)
    warped_color, warped_gray = warp_to_canonical(img, corners)

    # 2. Illumination Normalization & Inverted Thresholding
    # Subtract background to normalize uneven shadows
    background = cv2.GaussianBlur(warped_gray, (51, 51), 0)
    diff = cv2.absdiff(warped_gray, background)
    norm = cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)

    # Adaptive thresholding: filled markings become pure white (255)
    thresh = cv2.adaptiveThreshold(
        warped_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 25, 10
    )

    # Also Otsu threshold for strong fill confirmation
    _, otsu = cv2.threshold(warped_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    combined_thresh = cv2.bitwise_or(thresh, otsu)

    # 3. Retrieve Layout Spec
    question_count = len(exam_model.questions)
    opt_count = exam_model.options_per_question or 4
    roll_len = exam_model.roll_length or 6

    layout = OMRLayoutSpec.get_layout(
        question_count=question_count,
        options_count=opt_count,
        roll_length=roll_len
    )

    result = OMRResult()
    result.exam_id = exam_model.id

    overlay_img = warped_color.copy()

    # 4. Decode Roll Number
    roll_digits: List[str] = []
    roll_bubbles = layout["roll_bubbles"]
    for col_idx, col in enumerate(roll_bubbles):
        best_digit = None
        best_fill = 0.0
        second_best_fill = 0.0

        for b in col:
            fill = measure_bubble_fill(combined_thresh, b["x"], b["y"], b["r"])
            if fill > best_fill:
                second_best_fill = best_fill
                best_fill = fill
                best_digit = b["digit"]
            elif fill > second_best_fill:
                second_best_fill = fill

        # Threshold for marked bubble: > 0.32
        if best_fill >= 0.32 and (best_fill - second_best_fill) > 0.08:
            roll_digits.append(str(best_digit))
            # Draw green ring on chosen roll bubble
            chosen_b = col[best_digit]
            cv2.circle(overlay_img, (int(chosen_b["x"]), int(chosen_b["y"])), int(chosen_b["r"] + 3), (0, 200, 0), 2)
        else:
            roll_digits.append("?")

    result.student_roll = "".join(roll_digits)

    # 5. Evaluate Questions
    correct_count = 0
    incorrect_count = 0
    unanswered_count = 0
    total_score = 0.0
    needs_review = False

    answers_map = {q.question_number: q for q in exam_model.questions}
    question_bubbles = layout["question_bubbles"]

    for q_idx in range(1, question_count + 1):
        q_model = answers_map.get(q_idx)
        if not q_model:
            continue

        q_key = q_model.correct_option.strip().upper()
        bubbles = question_bubbles.get(q_idx, [])

        filled_options = []
        bubble_stats = []

        for b in bubbles:
            fill = measure_bubble_fill(combined_thresh, b["x"], b["y"], b["r"])
            bubble_stats.append((b["option"], fill, b))
            if fill >= 0.32:
                filled_options.append((b["option"], fill, b))

        # Sort filled options by fill ratio descending
        filled_options.sort(key=lambda x: x[1], reverse=True)

        detected_opt = None
        is_correct = False
        confidence = 1.0
        is_flagged = False

        if len(filled_options) == 0:
            # Unanswered
            unanswered_count += 1
            # Outline correct answer in dashed blue/grey
            correct_bubble = next((b for b in bubbles if b["option"] == q_key), None)
            if correct_bubble:
                cv2.circle(overlay_img, (int(correct_bubble["x"]), int(correct_bubble["y"])), int(correct_bubble["r"] + 3), (180, 180, 180), 2)

        elif len(filled_options) == 1:
            detected_opt = filled_options[0][0]
            detected_bubble = filled_options[0][2]
            confidence = min(1.0, filled_options[0][1] * 2)

            if detected_opt == q_key:
                is_correct = True
                correct_count += 1
                total_score += (q_model.marks or exam_model.positive_marks or 1.0)
                # 🟢 GREEN circle for correct
                cv2.circle(overlay_img, (int(detected_bubble["x"]), int(detected_bubble["y"])), int(detected_bubble["r"] + 3), (0, 220, 0), 3)
            else:
                is_correct = False
                incorrect_count += 1
                total_score -= (q_model.negative_marks or exam_model.negative_marks or 0.0)
                # 🔴 RED circle for wrong answer
                cv2.circle(overlay_img, (int(detected_bubble["x"]), int(detected_bubble["y"])), int(detected_bubble["r"] + 3), (0, 0, 240), 3)
                # 🟢 Highlight the correct answer as a guide
                correct_bubble = next((b for b in bubbles if b["option"] == q_key), None)
                if correct_bubble:
                    cv2.circle(overlay_img, (int(correct_bubble["x"]), int(correct_bubble["y"])), int(correct_bubble["r"] + 3), (0, 200, 0), 2)

        else:
            # Multiple fills detected!
            detected_opt = "MULTIPLE"
            is_correct = False
            incorrect_count += 1
            is_flagged = True
            needs_review = True
            confidence = 0.4
            total_score -= (q_model.negative_marks or exam_model.negative_marks or 0.0)

            # 🟡 YELLOW circles for multiple fills
            for opt, _, b in filled_options:
                cv2.circle(overlay_img, (int(b["x"]), int(b["y"])), int(b["r"] + 3), (0, 215, 255), 3)

        result.answers.append({
            "question_number": q_idx,
            "detected_option": detected_opt,
            "correct_option": q_key,
            "is_correct": is_correct,
            "confidence": round(confidence, 2),
            "is_flagged": is_flagged
        })

    max_possible = sum([q.marks or exam_model.positive_marks or 1.0 for q in exam_model.questions])
    result.total_score = max(0.0, round(total_score, 2))
    result.max_score = round(max_possible, 2)
    result.percentage = round((result.total_score / max(max_possible, 1.0)) * 100, 1)
    result.correct_count = correct_count
    result.incorrect_count = incorrect_count
    result.unanswered_count = unanswered_count
    result.status = "flagged_review" if needs_review or "?" in result.student_roll else "graded"

    # Draw score badge in header of overlay image (placed in header whitespace between title and QR code)
    score_text = f"Roll: {result.student_roll} | Score: {result.total_score:.1f}/{result.max_score:.1f} ({result.percentage:.0f}%)"
    cv2.rectangle(overlay_img, (490, 40), (895, 92), (245, 255, 245), -1)
    cv2.rectangle(overlay_img, (490, 40), (895, 92), (0, 150, 0), 2)
    cv2.putText(overlay_img, score_text, (502, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (10, 80, 10), 2)

    # Save overlay image
    if save_overlay:
        overlay_name = f"overlay_{Path(image_path).stem}.jpg"
        overlay_dest = OVERLAYS_DIR / overlay_name
        cv2.imwrite(str(overlay_dest), overlay_img)
        result.overlay_path = str(overlay_dest)

    # Encode to base64 for direct browser transmission
    _, buffer = cv2.imencode(".jpg", overlay_img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    result.overlay_base64 = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"

    return result
