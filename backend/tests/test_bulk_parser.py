import pytest
from app.services.bulk_parser import parse_bulk_questions

def test_parse_standard_questions():
    sample = """
    1. What is the capital of France?
    A) Paris
    B) London
    C) Rome
    D) Berlin
    Ans: A

    2. Which planet is known as the Red Planet?
    (A) Venus
    (B) Mars
    (C) Jupiter
    (D) Saturn
    Answer: B

    3. Solve: 5 * 6 = ?
    A. 20
    B. 25
    C. 30
    D. 35
    Correct: C
    """
    questions = parse_bulk_questions(sample)
    assert len(questions) == 3

    assert questions[0]["question_number"] == 1
    assert "capital of France" in questions[0]["question_text"]
    assert questions[0]["correct_option"] == "A"
    assert len(questions[0]["options"]) == 4
    assert questions[0]["options"][0] == "Paris"

    assert questions[1]["question_number"] == 2
    assert "Red Planet" in questions[1]["question_text"]
    assert questions[1]["correct_option"] == "B"
    assert questions[1]["options"][1] == "Mars"

    assert questions[2]["question_number"] == 3
    assert questions[2]["correct_option"] == "C"
    assert questions[2]["options"][2] == "30"
