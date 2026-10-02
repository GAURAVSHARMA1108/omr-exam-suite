import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Exam, Question, Submission
from app.schemas import ExamCreate, ExamResponse, BulkParseRequest, BulkParseResponse
from app.services.bulk_parser import parse_bulk_questions
from app.services.pdf_generator import generate_exam_pdf
from app.config import PDFS_DIR

router = APIRouter(prefix="/api/exams", tags=["Exams"])

@router.post("/bulk-parse", response_model=BulkParseResponse)
async def bulk_parse_endpoint(payload: BulkParseRequest):
    """Parses pasted raw questions text into structured questions and answers."""
    parsed = parse_bulk_questions(payload.raw_text)
    return BulkParseResponse(
        success=True,
        questions=parsed,
        detected_count=len(parsed)
    )

@router.post("", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
async def create_exam(payload: ExamCreate, db: AsyncSession = Depends(get_db)):
    """Creates a new exam with questions and answer keys."""
    exam = Exam(
        title=payload.title,
        subject=payload.subject,
        date_str=payload.date_str,
        instructions=payload.instructions,
        roll_length=payload.roll_length,
        options_per_question=payload.options_per_question,
        layout_type=payload.layout_type,
        positive_marks=payload.positive_marks,
        negative_marks=payload.negative_marks,
    )
    db.add(exam)
    await db.flush()

    for q in payload.questions:
        question_obj = Question(
            exam_id=exam.id,
            question_number=q.question_number,
            question_text=q.question_text,
            options=q.options,
            correct_option=q.correct_option.strip().upper(),
            marks=q.marks if q.marks is not None else payload.positive_marks,
            negative_marks=q.negative_marks if q.negative_marks is not None else payload.negative_marks,
        )
        db.add(question_obj)

    await db.commit()

    # Re-query with eager load
    result = await db.execute(
        select(Exam).options(selectinload(Exam.questions)).where(Exam.id == exam.id)
    )
    saved_exam = result.scalar_one()

    # Pre-generate printable PDF
    try:
        generate_exam_pdf(saved_exam)
    except Exception as e:
        print(f"Warning: PDF pre-generation error: {e}")

    return saved_exam

@router.get("", response_model=List[ExamResponse])
async def list_exams(db: AsyncSession = Depends(get_db)):
    """Lists all created exams with submission count."""
    result = await db.execute(
        select(Exam)
        .options(selectinload(Exam.questions), selectinload(Exam.submissions))
        .order_by(Exam.created_at.desc())
    )
    exams = result.scalars().all()
    out = []
    for ex in exams:
        ex_resp = ExamResponse.model_validate(ex)
        ex_resp.submissions_count = len(ex.submissions)
        out.append(ex_resp)
    return out

@router.get("/{exam_id}", response_model=ExamResponse)
async def get_exam(exam_id: str, db: AsyncSession = Depends(get_db)):
    """Fetches full details of a specific exam."""
    result = await db.execute(
        select(Exam)
        .options(selectinload(Exam.questions), selectinload(Exam.submissions))
        .where(Exam.id == exam_id)
    )
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    ex_resp = ExamResponse.model_validate(exam)
    ex_resp.submissions_count = len(exam.submissions)
    return ex_resp

@router.get("/{exam_id}/pdf")
async def download_exam_pdf(exam_id: str, db: AsyncSession = Depends(get_db)):
    """Generates and serves the ready-to-print vector PDF for an exam."""
    result = await db.execute(
        select(Exam).options(selectinload(Exam.questions)).where(Exam.id == exam_id)
    )
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    pdf_path = generate_exam_pdf(exam)
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"OMR_{exam.title.replace(' ', '_')}_{exam.id}.pdf"
    )

@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exam(exam_id: str, db: AsyncSession = Depends(get_db)):
    """Deletes an exam and its associated questions/submissions."""
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    await db.delete(exam)
    await db.commit()
    return None
