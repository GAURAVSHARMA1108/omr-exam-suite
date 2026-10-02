import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from app.database import Base

def generate_exam_id():
    return uuid.uuid4().hex[:8].upper()

def generate_uuid():
    return uuid.uuid4().hex

class Exam(Base):
    __tablename__ = "exams"

    id = Column(String(32), primary_key=True, default=generate_exam_id)
    title = Column(String(200), nullable=False)
    subject = Column(String(100), nullable=False)
    date_str = Column(String(50), nullable=True)
    instructions = Column(Text, nullable=True)
    roll_length = Column(Integer, default=6)
    options_per_question = Column(Integer, default=4)
    layout_type = Column(String(20), default="split") # "split" or "duplex"
    positive_marks = Column(Float, default=1.0)
    negative_marks = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    questions = relationship("Question", back_populates="exam", cascade="all, delete-orphan", order_by="Question.question_number")
    submissions = relationship("Submission", back_populates="exam", cascade="all, delete-orphan", order_by="Submission.created_at.desc()")

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(String(32), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    question_number = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)  # list of strings e.g. ["Paris", "London", "Rome", "Berlin"]
    correct_option = Column(String(5), nullable=False) # "A", "B", "C", "D", etc.
    marks = Column(Float, default=1.0)
    negative_marks = Column(Float, default=0.0)

    exam = relationship("Exam", back_populates="questions")

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(String(32), primary_key=True, default=generate_uuid)
    exam_id = Column(String(32), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    student_roll = Column(String(50), default="UNKNOWN")
    student_name = Column(String(100), default="Student")
    total_score = Column(Float, default=0.0)
    max_score = Column(Float, default=0.0)
    percentage = Column(Float, default=0.0)
    correct_count = Column(Integer, default=0)
    incorrect_count = Column(Integer, default=0)
    unanswered_count = Column(Integer, default=0)
    status = Column(String(30), default="graded") # "graded", "flagged_review", "overridden"
    original_image_path = Column(String(300), nullable=True)
    overlay_image_path = Column(String(300), nullable=True)
    sheet_hash = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    exam = relationship("Exam", back_populates="submissions")
    answers = relationship("StudentAnswer", back_populates="submission", cascade="all, delete-orphan", order_by="StudentAnswer.question_number")

class StudentAnswer(Base):
    __tablename__ = "student_answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(String(32), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    question_number = Column(Integer, nullable=False)
    detected_option = Column(String(10), nullable=True) # "A", "B", "C", "D", "MULTIPLE", None
    correct_option = Column(String(10), nullable=False)
    is_correct = Column(Boolean, default=False)
    confidence = Column(Float, default=1.0)
    is_flagged = Column(Boolean, default=False)

    submission = relationship("Submission", back_populates="answers")
