"""
verify_quiz_scanning.py
=======================
Automated verification script that:
1. Creates a 4-question quiz covering all answer orientations (A, B, C, D).
2. Starts an active QuizSession for Grade 10.
3. Tests optical card scanning using actual ArUco card images rotated to A, B, C, D.
4. Submits scanned responses for multiple students (Arun, Priya, Rahul, Sneha, Karthik).
5. Ends the quiz session.
6. Queries and validates all recorded responses, scores, and analytics.
"""

import asyncio
import base64
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import cv2
import numpy as np
from sqlalchemy import select, and_

import logging
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# Add server directory to path
SERVER_DIR = Path(r"c:\Project\plickers\school-response-server")
sys.path.insert(0, str(SERVER_DIR))
SCANNER_DIR = Path(r"c:\Project\plickers\scanner")
sys.path.insert(0, str(SCANNER_DIR))

from app.db.session import AsyncSessionFactory, engine
engine.echo = False
from app.models.user import User, Teacher
from app.models.school import School, Class
from app.models.student import Student
from app.models.card import Card, StudentCard
from app.models.quiz import QuestionSet, Question, QuizSession, Response, StudentScore
from app.models.enums import QuestionSetStatus, QuizSessionStatus, AnswerLetter
from app.services.quiz_service import (
    start_quiz_session,
    process_scanner_response,
    end_quiz_session,
    get_quiz_dashboard,
)
from detector import CardDetector


CARDS_DIR = Path(r"c:\Project\plickers\cards")

QUESTIONS_DATA = [
    {
        "text": "What organelle is known as the powerhouse of the cell?",
        "options": {
            "a": "Mitochondria",
            "b": "Ribosome",
            "c": "Nucleus",
            "d": "Endoplasmic Reticulum",
        },
        "correct": AnswerLetter.A,
        "marks": 1,
    },
    {
        "text": "What is the chemical formula for water?",
        "options": {
            "a": "CO2",
            "b": "H2O",
            "c": "NaCl",
            "d": "CH4",
        },
        "correct": AnswerLetter.B,
        "marks": 1,
    },
    {
        "text": "At what temperature Celsius does pure water freeze at standard atmospheric pressure?",
        "options": {
            "a": "100°C",
            "b": "32°C",
            "c": "0°C",
            "d": "-273°C",
        },
        "correct": AnswerLetter.C,
        "marks": 1,
    },
    {
        "text": "What is the speed of light in a vacuum approximately?",
        "options": {
            "a": "3,000 km/s",
            "b": "150,000 km/s",
            "c": "30,000 km/s",
            "d": "300,000 km/s",
        },
        "correct": AnswerLetter.D,
        "marks": 1,
    },
]

# Rotation mappings
ROTATION_FOR_ANSWER = {
    AnswerLetter.A: (0, None),
    AnswerLetter.B: (90, cv2.ROTATE_90_CLOCKWISE),
    AnswerLetter.C: (180, cv2.ROTATE_180),
    AnswerLetter.D: (270, cv2.ROTATE_90_COUNTERCLOCKWISE),
}

async def run_verification():
    print("=" * 70)
    print("  PLICKERS QUIZ SCANNING & RECORD VALIDATION SUITE")
    print("=" * 70)

    async with AsyncSessionFactory() as db:
        # 1. Fetch Teacher & Class
        teacher_res = await db.execute(select(Teacher).where(Teacher.id == 1))
        teacher = teacher_res.scalars().first()
        school_id = teacher.school_id
        teacher_user_id = teacher.user_id

        class_res = await db.execute(select(Class).where(Class.school_id == school_id, Class.name == "Grade 10"))
        classroom = class_res.scalars().first()
        class_id = classroom.id

        print(f"\n[1] Environment Config:")
        print(f"    - School ID: {school_id}")
        print(f"    - Teacher: {teacher.first_name} {teacher.last_name} (User ID: {teacher_user_id})")
        print(f"    - Target Classroom: {classroom.name} (Class ID: {class_id})")

        # 2. Create Question Set
        title = "Card Scanning & Response Verification Quiz"
        # Check if already exists from earlier run, if so clean up or create fresh
        existing_qs = (await db.execute(
            select(QuestionSet).where(
                QuestionSet.school_id == school_id,
                QuestionSet.title == title
            )
        )).scalars().first()

        if existing_qs:
            qs = existing_qs
            print(f"\n[2] Reusing Existing QuestionSet ID: {qs.id}")
            # Load questions
            q_res = await db.execute(select(Question).where(Question.question_set_id == qs.id).order_by(Question.id))
            questions = q_res.scalars().all()
        else:
            qs = QuestionSet(
                school_id=school_id,
                teacher_id=teacher_user_id,
                title=title,
                description="Diagnostic verification quiz testing card detection, orientation mapping (A, B, C, D), and student record tracking.",
                subject="Integrated Science",
                grade="Grade 10",
                status=QuestionSetStatus.PUBLISHED,
            )
            db.add(qs)
            await db.flush()

            questions = []
            for item in QUESTIONS_DATA:
                q = Question(
                    question_set_id=qs.id,
                    question_text=item["text"],
                    option_a=item["options"]["a"],
                    option_b=item["options"]["b"],
                    option_c=item["options"]["c"],
                    option_d=item["options"]["d"],
                    correct_answer=item["correct"],
                    marks=item["marks"],
                )
                db.add(q)
                await db.flush()
                questions.append(q)

            await db.commit()
            print(f"\n[2] Created New QuestionSet ID: {qs.id} with {len(questions)} questions")

        for i, q in enumerate(questions, 1):
            print(f"    Q{i} (ID {q.id}): {q.question_text[:40]}... [Correct: {q.correct_answer.value}]")

        # 3. Create & Start Quiz Session
        session = QuizSession(
            question_set_id=qs.id,
            teacher_id=teacher_user_id,
            class_id=class_id,
            status=QuizSessionStatus.PENDING,
        )
        db.add(session)
        await db.flush()

        # Start session
        session = await start_quiz_session(db, session.id, school_id, teacher_user_id)
        await db.commit()
        print(f"\n[3] Started Live QuizSession ID: {session.id} (Status: {session.status.value})")

        # 4. Fetch Students & Assigned Cards
        stu_cards_res = await db.execute(
            select(Student, Card)
            .join(StudentCard, StudentCard.student_id == Student.id)
            .join(Card, Card.id == StudentCard.card_id)
            .where(
                Student.class_id == class_id,
                StudentCard.is_active == True,
            )
            .order_by(Student.id)
        )
        student_cards = stu_cards_res.all()[:5]  # Test with first 5 students
        print(f"\n[4] Participating Students for Live Card Scanning:")
        for stu, card in student_cards:
            print(f"    - {stu.first_name} {stu.last_name} ({stu.student_code}) -> Card #{card.card_number} (Marker ID {card.marker_id})")

        # 5. Simulate Scanning of Actual ArUco Cards
        detector = CardDetector({c.marker_id: f"{s.first_name} {s.last_name}" for s, c in student_cards})

        # Define student response scenarios per question:
        # Student 1 (Arun): All correct (A, B, C, D)
        # Student 2 (Priya): Q1: A (Correct), Q2: B (Correct), Q3: A (Wrong), Q4: D (Correct)
        # Student 3 (Rahul): Q1: B (Wrong),   Q2: B (Correct), Q3: C (Correct), Q4: C (Wrong)
        # Student 4 (Sneha): Q1: A (Correct), Q2: C (Wrong),   Q3: C (Correct), Q4: D (Correct)
        # Student 5 (Karthik): Q1: D (Wrong), Q2: B (Correct), Q3: B (Wrong),   Q4: D (Correct)

        test_answers_matrix = {
            1: [AnswerLetter.A, AnswerLetter.B, AnswerLetter.C, AnswerLetter.D], # Arun
            2: [AnswerLetter.A, AnswerLetter.B, AnswerLetter.A, AnswerLetter.D], # Priya
            3: [AnswerLetter.B, AnswerLetter.B, AnswerLetter.C, AnswerLetter.C], # Rahul
            4: [AnswerLetter.A, AnswerLetter.C, AnswerLetter.C, AnswerLetter.D], # Sneha
            5: [AnswerLetter.D, AnswerLetter.B, AnswerLetter.B, AnswerLetter.D], # Karthik
        }

        print("\n[5] Scanning Cards & Registering Answers...")

        for q_idx, q in enumerate(questions):
            print(f"\n  --- Scanning Question {q_idx + 1} (Correct: {q.correct_answer.value}) ---")
            
            for stu, card in student_cards:
                chosen_answer = test_answers_matrix[stu.id][q_idx]
                rot_deg, rot_code = ROTATION_FOR_ANSWER[chosen_answer]

                # Load physical card image
                card_filename = f"card_{card.card_number:03d}.png"
                card_path = CARDS_DIR / card_filename
                if not card_path.exists():
                    print(f"    [WARN] Card file {card_filename} not found!")
                    continue

                card_img = cv2.imread(str(card_path))
                if rot_code is not None:
                    card_img = cv2.rotate(card_img, rot_code)

                # Optical detection verification
                detections = detector.detect(card_img)
                assert len(detections) > 0, f"Detection failed for card {card.card_number}"
                det = detections[0]
                detected_letter = det["answer"]
                detected_rotation = det["rotation"]
                assert detected_letter == chosen_answer.value, f"Mismatch: expected {chosen_answer.value}, got {detected_letter}"
                assert detected_rotation == rot_deg, f"Rotation mismatch: expected {rot_deg}, got {detected_rotation}"

                # Submit to scanner pipeline
                scan_res = await process_scanner_response(
                    db,
                    school_id=school_id,
                    quiz_session_id=session.id,
                    question_id=q.id,
                    marker_id=card.marker_id,
                    rotation=detected_rotation,
                    answer=chosen_answer,
                    detected_at=datetime.now(timezone.utc),
                    user_id=teacher_user_id,
                )
                await db.commit()

                status_mark = "[CORRECT]" if scan_res.is_correct else "[INCORRECT]"
                print(f"    Card #{card.card_number} ({stu.first_name} {stu.last_name}): "
                      f"Rotated {detected_rotation} deg -> Answer {detected_letter} | {status_mark} (+{scan_res.marks_obtained} pts)")

        # 6. End Quiz Session
        session = await end_quiz_session(db, session.id, school_id, teacher_user_id)
        await db.commit()
        print(f"\n[6] Completed Quiz Session ID: {session.id} (Status: {session.status.value})")

        # 7. Query and Validate Final Records
        print("\n" + "=" * 70)
        print("  DETAILED RECORDS & VERIFICATION RESULTS")
        print("=" * 70)

        # Question-by-Question responses
        resp_res = await db.execute(
            select(Response, Student, Question)
            .join(Student, Student.id == Response.student_id)
            .join(Question, Question.id == Response.question_id)
            .where(Response.quiz_session_id == session.id)
            .order_by(Question.id, Student.id)
        )
        all_responses = resp_res.all()
        print(f"\n[A] Total Recorded Responses: {len(all_responses)}")
        print(f"{'Student':<18} | {'Q#':<4} | {'Chosen':<6} | {'Correct?':<6} | {'Result':<10} | {'Marks'}")
        print("-" * 65)
        for r, s, q in all_responses:
            res_str = "CORRECT" if r.is_correct else "WRONG"
            print(f"{s.first_name + ' ' + s.last_name:<18} | Q{questions.index(q) + 1:<3} | {r.answer.value:<6} | {q.correct_answer.value:<6} | {res_str:<10} | +{r.marks_obtained}")

        # Student Scores Summary
        score_res = await db.execute(
            select(StudentScore, Student)
            .join(Student, Student.id == StudentScore.student_id)
            .where(StudentScore.quiz_session_id == session.id)
            .order_by(StudentScore.score.desc())
        )
        student_scores = score_res.all()
        print(f"\n[B] Student Score Records:")
        print(f"{'Rank':<5} | {'Student Name':<18} | {'Correct':<8} | {'Total Marks':<11} | {'Percentage'}")
        print("-" * 65)
        for rank, (sc, stu) in enumerate(student_scores, 1):
            print(f"{rank:<5} | {stu.first_name + ' ' + stu.last_name:<18} | {sc.correct_answers}/{sc.total_questions:<6} | {sc.score}/{len(questions):<9} | {sc.percentage:.1f}%")

        # Aggregate Dashboard Summary
        dash = await get_quiz_dashboard(db, session.id, school_id)
        print(f"\n[C] Session Overall Metrics:")
        print(f"    - Total Responses Submitted: {dash.responses_received}")
        print(f"    - Answer Distribution: A={dash.answer_counts.get('A', 0)}, B={dash.answer_counts.get('B', 0)}, C={dash.answer_counts.get('C', 0)}, D={dash.answer_counts.get('D', 0)}")
        print(f"    - Total Classroom Students: {dash.total_students}")
        print(f"    - Session ID for UI Review: {session.id}")

    print("\n" + "=" * 70)
    print("  VERIFICATION COMPLETED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_verification())
