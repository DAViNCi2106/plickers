"""
scripts/seed.py
===============
Development seed data — creates clearly fake data for testing.
Maps to the existing 50 student names from output/cards.json.

Run:
    python scripts/seed.py

Requirements: .env must be configured with DATABASE_URL_SYNC.
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.models.enums import (
    AnswerLetter, CardStatus, QuestionSetStatus,
    QuizSessionStatus, SchoolStatus, StudentStatus, UserRole,
)
from app.models.school import AcademicYear, Class, School, Section
from app.models.user import Teacher, User
from app.models.student import Student
from app.models.card import Card, StudentCard
from app.models.quiz import Question, QuestionSet, QuizSession

# ── Existing 50 students from cards.json / README ────────────────────────
STUDENTS_50 = [
    (1,  "Arun Kumar"),       (2,  "Priya Sharma"),     (3,  "Rahul Verma"),
    (4,  "Sneha Iyer"),       (5,  "Karthik Raj"),      (6,  "Ananya Rao"),
    (7,  "Vikram Singh"),     (8,  "Divya Nair"),        (9,  "Aditya Menon"),
    (10, "Meera Krishnan"),   (11, "Rohit Patel"),       (12, "Kavya S"),
    (13, "Sanjay Prakash"),   (14, "Nisha Reddy"),       (15, "Akash Gupta"),
    (16, "Pooja Das"),        (17, "Harish Babu"),       (18, "Aishwarya M"),
    (19, "Naveen Kumar"),     (20, "Keerthana R"),       (21, "Siddharth Jain"),
    (22, "Swathi Narayanan"), (23, "Vishal Anand"),      (24, "Janani S"),
    (25, "Mohammed Irfan"),   (26, "Lakshmi Priya"),     (27, "Aravind S"),
    (28, "Shreya Kapoor"),    (29, "Pranav N"),          (30, "Deepika V"),
    (31, "Ajay Krishnan"),    (32, "Bhavana R"),         (33, "Surya Prakash"),
    (34, "Neha Agarwal"),     (35, "Ramesh K"),          (36, "Sanjana Devi"),
    (37, "Abhishek T"),       (38, "Gayathri M"),        (39, "Varun Raj"),
    (40, "Rithika S"),        (41, "Yash Shah"),         (42, "Pavithra N"),
    (43, "Manoj Kumar"),      (44, "Ishita Mehta"),      (45, "Dinesh R"),
    (46, "Harini B"),         (47, "Sathish Kumar"),     (48, "Tanya Bose"),
    (49, "Gokul Nath"),       (50, "Anjali Menon"),
]


def seed(db: Session) -> None:
    print("=" * 60)
    print("  Plickers School Response System — Dev Seed")
    print("=" * 60)

    # ── School ─────────────────────────────────────────────────────────
    print("\n[1/8] Creating school...")
    school = School(
        school_code="DEMO-HS",
        name="Demo High School",
        address="123 Education Lane, Knowledge City — 600001",
        email="admin@demohighschool.edu",
        phone="+91-44-12345678",
        status=SchoolStatus.ACTIVE,
    )
    db.add(school)
    db.flush()
    print(f"      School ID={school.id}  code={school.school_code}")

    # ── Academic Year ──────────────────────────────────────────────────
    print("\n[2/8] Creating academic year...")
    ay = AcademicYear(
        school_id=school.id,
        name="2026-2027",
        start_date=date(2026, 6, 1),
        end_date=date(2027, 3, 31),
        is_active=True,
    )
    db.add(ay)
    db.flush()
    print(f"      AcademicYear ID={ay.id}  name={ay.name}")

    # ── Classes ────────────────────────────────────────────────────────
    print("\n[3/8] Creating 2 classes...")
    class10 = Class(school_id=school.id, academic_year_id=ay.id, name="Grade 10", grade="10")
    class11 = Class(school_id=school.id, academic_year_id=ay.id, name="Grade 11", grade="11")
    db.add_all([class10, class11])
    db.flush()
    print(f"      Class A: ID={class10.id}  Class B: ID={class11.id}")

    # ── Sections ───────────────────────────────────────────────────────
    print("\n[4/8] Creating 2 sections...")
    sec_a = Section(class_id=class10.id, name="A")
    sec_b = Section(class_id=class10.id, name="B")
    db.add_all([sec_a, sec_b])
    db.flush()
    print(f"      Section A: ID={sec_a.id}  Section B: ID={sec_b.id}")

    # ── Users (SUPER_ADMIN + SCHOOL_ADMIN + 2 TEACHERS) ───────────────
    print("\n[5/8] Creating users and teachers...")
    super_admin = User(
        school_id=None,
        username="superadmin",
        email="superadmin@platform.dev",
        password_hash=hash_password("SuperAdmin@1234"),  # DEV ONLY
        role=UserRole.SUPER_ADMIN,
    )
    school_admin = User(
        school_id=school.id,
        username="schooladmin",
        email="admin@demohighschool.edu",
        password_hash=hash_password("SchoolAdmin@1234"),  # DEV ONLY
        role=UserRole.SCHOOL_ADMIN,
    )
    teacher1_user = User(
        school_id=school.id,
        username="teacher_anil",
        email="anil.kumar@demohighschool.edu",
        password_hash=hash_password("Teacher@1234"),  # DEV ONLY
        role=UserRole.TEACHER,
    )
    teacher2_user = User(
        school_id=school.id,
        username="teacher_maya",
        email="maya.devi@demohighschool.edu",
        password_hash=hash_password("Teacher@1234"),  # DEV ONLY
        role=UserRole.TEACHER,
    )
    db.add_all([super_admin, school_admin, teacher1_user, teacher2_user])
    db.flush()

    teacher1 = Teacher(
        user_id=teacher1_user.id, school_id=school.id,
        employee_id="EMP001", first_name="Anil", last_name="Kumar", phone="+91-9000000001",
    )
    teacher2 = Teacher(
        user_id=teacher2_user.id, school_id=school.id,
        employee_id="EMP002", first_name="Maya", last_name="Devi", phone="+91-9000000002",
    )
    db.add_all([teacher1, teacher2])
    db.flush()
    print(f"      Teachers: {teacher1.first_name} {teacher1.last_name}, {teacher2.first_name} {teacher2.last_name}")

    # ── Students + Cards (50 each — from existing cards.json names) ────
    print("\n[6/8] Creating 50 students and 50 cards (from existing roster)...")
    students = []
    cards = []
    assignments = []

    for card_num, full_name in STUDENTS_50:
        parts = full_name.split()
        first = parts[0]
        last = " ".join(parts[1:]) if len(parts) > 1 else "."
        student_code = f"STU{card_num:03d}"

        # First 25 → Section A, next 25 → Section B
        section_id = sec_a.id if card_num <= 25 else sec_b.id

        student = Student(
            school_id=school.id,
            class_id=class10.id,
            section_id=section_id,
            student_code=student_code,
            roll_number=card_num,
            first_name=first,
            last_name=last,
            status=StudentStatus.ACTIVE,
        )
        db.add(student)
        db.flush()

        card = Card(
            school_id=school.id,
            card_number=card_num,
            marker_id=card_num,       # marker_id == card_number (DICT_6X6_250)
            status=CardStatus.ASSIGNED,
        )
        db.add(card)
        db.flush()

        assignment = StudentCard(student_id=student.id, card_id=card.id)
        db.add(assignment)
        db.flush()

        students.append(student)
        cards.append(card)
        assignments.append(assignment)

    print(f"      Created {len(students)} students, {len(cards)} cards, {len(assignments)} assignments")

    # ── Question Set ───────────────────────────────────────────────────
    print("\n[7/8] Creating sample question set...")
    qs = QuestionSet(
        school_id=school.id,
        teacher_id=teacher1_user.id,
        title="Science Quiz — Chapter 5: Forces and Motion",
        description="A 5-question multiple-choice quiz on Newton's Laws of Motion.",
        subject="Physics",
        grade="10",
        status=QuestionSetStatus.PUBLISHED,
    )
    db.add(qs)
    db.flush()

    sample_questions = [
        ("What is Newton's First Law of Motion?",
         "An object at rest stays at rest unless acted upon by a net force",
         "F = ma",
         "Every action has an equal and opposite reaction",
         "Force equals mass times acceleration",
         AnswerLetter.A, 2),

        ("What does F = ma represent?",
         "Newton's First Law",
         "Newton's Second Law",
         "Newton's Third Law",
         "The law of gravitation",
         AnswerLetter.B, 2),

        ("Which unit is used to measure force?",
         "Joule",
         "Watt",
         "Newton",
         "Pascal",
         AnswerLetter.C, 1),

        ("If a 5 kg object accelerates at 3 m/s², what is the net force?",
         "8 N",
         "2 N",
         "15 N",
         "30 N",
         AnswerLetter.C, 2),

        ("Action and reaction forces act on:",
         "The same object",
         "Two different objects",
         "Only massive objects",
         "Objects in contact only",
         AnswerLetter.B, 1),
    ]

    question_objs = []
    for q_text, a, b, c, d, correct, marks in sample_questions:
        q = Question(
            question_set_id=qs.id,
            question_text=q_text,
            option_a=a, option_b=b, option_c=c, option_d=d,
            correct_answer=correct,
            marks=marks,
        )
        db.add(q)
        question_objs.append(q)
    db.flush()
    print(f"      QuestionSet ID={qs.id}  Questions: {len(question_objs)}")

    # ── Sample Quiz Session ────────────────────────────────────────────
    print("\n[8/8] Creating sample quiz session...")
    quiz = QuizSession(
        question_set_id=qs.id,
        teacher_id=teacher1_user.id,
        class_id=class10.id,
        section_id=sec_a.id,
        status=QuizSessionStatus.PENDING,
    )
    db.add(quiz)
    db.flush()
    print(f"      QuizSession ID={quiz.id}  status={quiz.status.value}")

    db.commit()
    print("\n" + "=" * 60)
    print("  [OK]  Seed complete!")
    print("=" * 60)
    print("\nDev credentials (CHANGE IN PRODUCTION):")
    print("  superadmin   / SuperAdmin@1234  (SUPER_ADMIN)")
    print("  schooladmin  / SchoolAdmin@1234 (SCHOOL_ADMIN)")
    print("  teacher_anil / Teacher@1234     (TEACHER)")
    print("  teacher_maya / Teacher@1234     (TEACHER)")
    print(f"\n  School ID: {school.id}  |  school_code: {school.school_code}")
    print(f"  QuizSession ID: {quiz.id}  (status: PENDING)")
    print(f"  QuestionSet ID: {qs.id}")


if __name__ == "__main__":
    db_url = settings.DATABASE_URL_SYNC or settings.DATABASE_URL.replace("+asyncpg", "")
    engine = create_engine(db_url, echo=False)

    # Create tables if they don't exist (dev shortcut — use Alembic in production)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        seed(session)
