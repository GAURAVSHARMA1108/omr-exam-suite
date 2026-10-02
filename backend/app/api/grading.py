import os
import uuid
import base64
import hashlib
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Exam, Submission, StudentAnswer
from app.schemas import SubmissionResponse
from app.services.omr_processor import process_omr_sheet, decode_qr_metadata
from app.config import UPLOADS_DIR
import cv2

router = APIRouter(prefix="/api/grading", tags=["Grading"])

class Base64GradeRequest(BaseModel):
    image_base64: str
    exam_id: Optional[str] = None
    student_name: Optional[str] = "Student"
    allow_overwrite: Optional[bool] = False

def compute_sheet_hash(exam_id: str, student_roll: str, answers: List[dict]) -> str:
    """Computes a deterministic content signature of an evaluated OMR sheet."""
    sorted_answers = sorted(answers, key=lambda x: x.get("question_number", 0))
    ans_str = ";".join(
        f"{a.get('question_number')}:{a.get('detected_option') or ''}"
        for a in sorted_answers
    )
    clean_roll = (student_roll or "").strip().upper()
    payload = f"{exam_id}:{clean_roll}:{ans_str}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

async def _grade_and_store_image(
    image_path: str,
    explicit_exam_id: Optional[str],
    student_name: str,
    db: AsyncSession,
    allow_overwrite: bool = False
) -> SubmissionResponse:
    # 1. Resolve Exam
    img = cv2.imread(image_path)
    if img is None:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid readable image")

    exam_id = explicit_exam_id
    if not exam_id:
        # Attempt QR code resolution
        qr_data = decode_qr_metadata(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
        if qr_data and "id" in qr_data:
            exam_id = qr_data["id"]

    if not exam_id:
        raise HTTPException(
            status_code=400, 
            detail="Could not detect Exam QR code on sheet. Please select the Exam manually."
        )

    # Fetch exam from DB
    result = await db.execute(
        select(Exam).options(selectinload(Exam.questions)).where(Exam.id == exam_id)
    )
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail=f"Exam with ID '{exam_id}' not found")

    # 2. Run Computer Vision Evaluation Pipeline
    omr_res = process_omr_sheet(image_path=image_path, exam_model=exam, save_overlay=True)
    current_hash = compute_sheet_hash(exam.id, omr_res.student_roll, omr_res.answers)

    # 3. Check for Duplicate Submission in this Exam
    res = await db.execute(
        select(Submission).options(selectinload(Submission.answers)).where(Submission.exam_id == exam.id)
    )
    existing_subs = res.scalars().all()

    clean_roll = (omr_res.student_roll or "").strip()
    is_known_roll = bool(clean_roll and clean_roll != "UNKNOWN" and not all(c in "? " for c in clean_roll))

    matching_sub: Optional[Submission] = None

    for es in existing_subs:
        # Match 1: Exact sheet content hash
        if es.sheet_hash and es.sheet_hash == current_hash:
            matching_sub = es
            break

        # Match 2: Same valid student roll number (each student only has 1 submission per test)
        if is_known_roll and es.student_roll and es.student_roll.strip() == clean_roll:
            matching_sub = es
            break

        # Match 3: Matching roll label AND identical question answer responses
        if es.student_roll == omr_res.student_roll:
            es_ans_map = {a.question_number: (a.detected_option or "") for a in es.answers}
            cur_ans_map = {a["question_number"]: (a.get("detected_option") or "") for a in omr_res.answers}
            if es_ans_map and es_ans_map == cur_ans_map:
                matching_sub = es
                break

    if matching_sub:
        if allow_overwrite:
            # Overwrite the existing submission with newly scanned data
            matching_sub.student_name = student_name
            matching_sub.total_score = omr_res.total_score
            matching_sub.max_score = omr_res.max_score
            matching_sub.percentage = omr_res.percentage
            matching_sub.correct_count = omr_res.correct_count
            matching_sub.incorrect_count = omr_res.incorrect_count
            matching_sub.unanswered_count = omr_res.unanswered_count
            matching_sub.status = omr_res.status
            matching_sub.original_image_path = image_path
            matching_sub.overlay_image_path = omr_res.overlay_path
            matching_sub.sheet_hash = current_hash

            # Delete old answers and replace with fresh answers
            for old_a in list(matching_sub.answers):
                await db.delete(old_a)
            await db.flush()

            for ans in omr_res.answers:
                sa = StudentAnswer(
                    submission_id=matching_sub.id,
                    question_number=ans["question_number"],
                    detected_option=ans["detected_option"],
                    correct_option=ans["correct_option"],
                    is_correct=ans["is_correct"],
                    confidence=ans["confidence"],
                    is_flagged=ans["is_flagged"],
                )
                db.add(sa)

            await db.commit()

            sub_res = await db.execute(
                select(Submission).options(selectinload(Submission.answers)).where(Submission.id == matching_sub.id)
            )
            saved_sub = sub_res.scalar_one()
            resp = SubmissionResponse.model_validate(saved_sub)
            resp.is_duplicate = True
            resp.duplicate_message = f"Duplicate sheet for Roll '{matching_sub.student_roll}' detected. Existing record was updated with the new scan."
            return resp
        else:
            # Duplicate blocked! Do NOT insert a new row in the database.
            resp = SubmissionResponse.model_validate(matching_sub)
            resp.is_duplicate = True
            resp.duplicate_message = (
                f"Duplicate sheet detected for Roll '{matching_sub.student_roll}'. "
                f"This sheet was already graded on {matching_sub.created_at.strftime('%H:%M:%S') if matching_sub.created_at else 'earlier'}. "
                f"Duplicate entry was blocked to prevent double-counting."
            )
            return resp

    # 4. Fresh Submission: Store Submission & Student Answers
    sub = Submission(
        id=uuid.uuid4().hex,
        exam_id=exam.id,
        student_roll=omr_res.student_roll,
        student_name=student_name,
        total_score=omr_res.total_score,
        max_score=omr_res.max_score,
        percentage=omr_res.percentage,
        correct_count=omr_res.correct_count,
        incorrect_count=omr_res.incorrect_count,
        unanswered_count=omr_res.unanswered_count,
        status=omr_res.status,
        original_image_path=image_path,
        overlay_image_path=omr_res.overlay_path,
        sheet_hash=current_hash,
    )
    db.add(sub)
    await db.flush()

    for ans in omr_res.answers:
        sa = StudentAnswer(
            submission_id=sub.id,
            question_number=ans["question_number"],
            detected_option=ans["detected_option"],
            correct_option=ans["correct_option"],
            is_correct=ans["is_correct"],
            confidence=ans["confidence"],
            is_flagged=ans["is_flagged"],
        )
        db.add(sa)

    await db.commit()

    # Re-query with answers eager loaded
    sub_res = await db.execute(
        select(Submission).options(selectinload(Submission.answers)).where(Submission.id == sub.id)
    )
    saved_sub = sub_res.scalar_one()
    resp = SubmissionResponse.model_validate(saved_sub)
    resp.is_duplicate = False
    return resp

@router.post("/upload", response_model=SubmissionResponse)
async def grade_uploaded_file(
    file: UploadFile = File(...),
    exam_id: Optional[str] = Form(None),
    student_name: Optional[str] = Form("Student"),
    allow_overwrite: Optional[bool] = Form(False),
    db: AsyncSession = Depends(get_db)
):
    """Evaluates an uploaded OMR sheet photo or scan with duplicate protection."""
    file_ext = Path(file.filename or "sheet.jpg").suffix or ".jpg"
    unique_name = f"scan_{uuid.uuid4().hex}{file_ext}"
    dest_path = UPLOADS_DIR / unique_name

    contents = await file.read()
    with open(dest_path, "wb") as f:
        f.write(contents)

    return await _grade_and_store_image(
        str(dest_path), 
        exam_id, 
        student_name or "Student", 
        db, 
        allow_overwrite=allow_overwrite or False
    )

@router.post("/base64", response_model=SubmissionResponse)
async def grade_base64_image(
    payload: Base64GradeRequest,
    db: AsyncSession = Depends(get_db)
):
    """Evaluates a Base64 encoded image (from webcam or scanner bridge) with duplicate protection."""
    raw_data = payload.image_base64
    if "," in raw_data:
        raw_data = raw_data.split(",", 1)[1]

    img_bytes = base64.b64decode(raw_data)
    dest_path = UPLOADS_DIR / f"scanner_{uuid.uuid4().hex}.jpg"
    with open(dest_path, "wb") as f:
        f.write(img_bytes)

    return await _grade_and_store_image(
        str(dest_path), 
        payload.exam_id, 
        payload.student_name or "Student", 
        db, 
        allow_overwrite=payload.allow_overwrite or False
    )

@router.post("/batch", response_model=List[SubmissionResponse])
async def grade_batch_files(
    files: List[UploadFile] = File(...),
    exam_id: Optional[str] = Form(None),
    allow_overwrite: Optional[bool] = Form(False),
    db: AsyncSession = Depends(get_db)
):
    """Evaluates multiple uploaded OMR sheet photos/scans in a batch with duplicate protection."""
    results = []
    for file in files:
        try:
            file_ext = Path(file.filename or "sheet.jpg").suffix or ".jpg"
            dest_path = UPLOADS_DIR / f"batch_{uuid.uuid4().hex}{file_ext}"
            contents = await file.read()
            with open(dest_path, "wb") as f:
                f.write(contents)

            resp = await _grade_and_store_image(
                str(dest_path), 
                exam_id, 
                "Student", 
                db, 
                allow_overwrite=allow_overwrite or False
            )
            results.append(resp)
        except Exception as e:
            print(f"Error grading batch item {file.filename}: {e}")
            continue

    return results
