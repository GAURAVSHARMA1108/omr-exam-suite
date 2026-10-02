from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class QuestionCreate(BaseModel):
    question_number: int
    question_text: str
    options: List[str]
    correct_option: str # "A", "B", etc.
    marks: Optional[float] = 1.0
    negative_marks: Optional[float] = 0.0

class QuestionResponse(QuestionCreate):
    id: int
    exam_id: str

    class Config:
        from_attributes = True

class ExamCreate(BaseModel):
    title: str = Field(..., example="Mathematics Mid-Term Exam")
    subject: str = Field(..., example="Mathematics")
    date_str: Optional[str] = "2026-10-01"
    instructions: Optional[str] = "Use dark blue/black pen. Fill bubbles completely."
    roll_length: int = Field(6, ge=4, le=10)
    options_per_question: int = Field(4, ge=2, le=5)
    layout_type: str = Field("split", pattern="^(split|duplex)$")
    positive_marks: float = 1.0
    negative_marks: float = 0.0
    questions: List[QuestionCreate]

class ExamResponse(BaseModel):
    id: str
    title: str
    subject: str
    date_str: Optional[str]
    instructions: Optional[str]
    roll_length: int
    options_per_question: int
    layout_type: str
    positive_marks: float
    negative_marks: float
    created_at: datetime
    questions: List[QuestionResponse] = []
    submissions_count: Optional[int] = 0

    class Config:
        from_attributes = True

class BulkParseRequest(BaseModel):
    raw_text: str

class ParsedQuestion(BaseModel):
    question_number: int
    question_text: str
    options: List[str]
    correct_option: str

class BulkParseResponse(BaseModel):
    success: bool
    questions: List[ParsedQuestion]
    detected_count: int

class StudentAnswerResponse(BaseModel):
    question_number: int
    detected_option: Optional[str]
    correct_option: str
    is_correct: bool
    confidence: float
    is_flagged: bool

    class Config:
        from_attributes = True

class SubmissionResponse(BaseModel):
    id: str
    exam_id: str
    student_roll: str
    student_name: str
    total_score: float
    max_score: float
    percentage: float
    correct_count: int
    incorrect_count: int
    unanswered_count: int
    status: str
    original_image_path: Optional[str]
    overlay_image_path: Optional[str]
    created_at: datetime
    is_duplicate: Optional[bool] = False
    duplicate_message: Optional[str] = None
    answers: List[StudentAnswerResponse] = []

    class Config:
        from_attributes = True

class OverrideAnswerRequest(BaseModel):
    question_number: int
    new_option: str # "A", "B", "C", "D", or "" / "NONE"
