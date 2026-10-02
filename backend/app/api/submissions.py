from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Exam, Submission, StudentAnswer
from app.schemas import SubmissionResponse, OverrideAnswerRequest
from app.services.export_service import export_exam_results_excel, export_exam_results_csv

router = APIRouter(prefix="/api/submissions", tags=["Submissions"])

@router.get("/exam/{exam_id}", response_model=List[SubmissionResponse])
async def list_exam_submissions(exam_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves all student submissions for a specific exam."""
    result = await db.execute(
        select(Submission)
        .options(selectinload(Submission.answers))
        .where(Submission.exam_id == exam_id)
        .order_by(Submission.created_at.desc())
    )
    return result.scalars().all()

@router.get("/{sub_id}", response_model=SubmissionResponse)
async def get_submission(sub_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves a single submission with answers and overlay image path."""
    result = await db.execute(
        select(Submission)
        .options(selectinload(Submission.answers))
        .where(Submission.id == sub_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    return sub

@router.post("/{sub_id}/override", response_model=SubmissionResponse)
async def override_student_answer(
    sub_id: str,
    payload: OverrideAnswerRequest,
    db: AsyncSession = Depends(get_db)
):
    """Allows teacher to manually override or correct an evaluated answer."""
    sub_result = await db.execute(
        select(Submission)
        .options(selectinload(Submission.answers), selectinload(Submission.exam).selectinload(Exam.questions))
        .where(Submission.id == sub_id)
    )
    sub = sub_result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    target_ans = next((a for a in sub.answers if a.question_number == payload.question_number), None)
    if not target_ans:
        raise HTTPException(status_code=404, detail=f"Question #{payload.question_number} answer not found")

    new_opt = payload.new_option.strip().upper() if payload.new_option else None
    target_ans.detected_option = new_opt
    target_ans.is_correct = (new_opt == target_ans.correct_option)
    target_ans.is_flagged = False
    target_ans.confidence = 1.0

    # Recalculate score
    exam = sub.exam
    total_score = 0.0
    correct_count = 0
    incorrect_count = 0
    unanswered_count = 0

    q_map = {q.question_number: q for q in exam.questions}
    for ans in sub.answers:
        q_m = q_map.get(ans.question_number)
        pos = q_m.marks if (q_m and q_m.marks) else exam.positive_marks
        neg = q_m.negative_marks if (q_m and q_m.negative_marks) else exam.negative_marks

        if ans.detected_option is None or ans.detected_option == "":
            unanswered_count += 1
        elif ans.is_correct:
            correct_count += 1
            total_score += pos
        else:
            incorrect_count += 1
            total_score -= neg

    sub.total_score = max(0.0, round(total_score, 2))
    sub.correct_count = correct_count
    sub.incorrect_count = incorrect_count
    sub.unanswered_count = unanswered_count
    sub.percentage = round((sub.total_score / max(sub.max_score, 1.0)) * 100, 1)
    sub.status = "overridden"

    await db.commit()
    await db.refresh(sub)
    return sub

@router.get("/exam/{exam_id}/export/excel")
async def export_excel(exam_id: str, db: AsyncSession = Depends(get_db)):
    """Exports exam results to a formatted Excel spreadsheet."""
    exam_res = await db.execute(
        select(Exam).options(selectinload(Exam.questions)).where(Exam.id == exam_id)
    )
    exam = exam_res.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    subs_res = await db.execute(
        select(Submission).options(selectinload(Submission.answers)).where(Submission.exam_id == exam_id)
    )
    submissions = subs_res.scalars().all()

    excel_bytes = export_exam_results_excel(exam, submissions)
    filename = f"Results_{exam.title.replace(' ', '_')}_{exam.id}.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/exam/{exam_id}/export/csv")
async def export_csv(exam_id: str, db: AsyncSession = Depends(get_db)):
    """Exports exam results to CSV."""
    exam_res = await db.execute(
        select(Exam).options(selectinload(Exam.questions)).where(Exam.id == exam_id)
    )
    exam = exam_res.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    subs_res = await db.execute(
        select(Submission).options(selectinload(Submission.answers)).where(Submission.exam_id == exam_id)
    )
    submissions = subs_res.scalars().all()

    csv_data = export_exam_results_csv(exam, submissions)
    filename = f"Results_{exam.title.replace(' ', '_')}_{exam.id}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.delete("/{sub_id}", status_code=status.HTTP_200_OK)
async def delete_submission(sub_id: str, db: AsyncSession = Depends(get_db)):
    """Deletes a student submission."""
    result = await db.execute(
        select(Submission).where(Submission.id == sub_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    await db.delete(sub)
    await db.commit()
    return {"status": "deleted", "id": sub_id}

