"""Initial schema — all tables

Revision ID: 0001
Revises:
Create Date: 2026-10-02

Creates:
  schools, academic_years, classes, sections,
  users, teachers,
  students,
  cards, student_cards,
  question_sets, questions, quiz_sessions, responses, student_scores,
  audit_logs

All enum types created with IF NOT EXISTS / CREATE TYPE for idempotency.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enum types ─────────────────────────────────────────────────────────
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE user_role_enum AS ENUM (
                'SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER', 'STUDENT'
            );
        EXCEPTION WHEN duplicate_object THEN null; END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE school_status_enum AS ENUM (
                'active', 'inactive', 'suspended'
            );
        EXCEPTION WHEN duplicate_object THEN null; END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE student_status_enum AS ENUM (
                'active', 'inactive', 'transferred'
            );
        EXCEPTION WHEN duplicate_object THEN null; END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE card_status_enum AS ENUM (
                'available', 'assigned', 'lost', 'disabled'
            );
        EXCEPTION WHEN duplicate_object THEN null; END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE question_set_status_enum AS ENUM (
                'draft', 'published', 'archived'
            );
        EXCEPTION WHEN duplicate_object THEN null; END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE quiz_session_status_enum AS ENUM (
                'pending', 'active', 'paused', 'ended'
            );
        EXCEPTION WHEN duplicate_object THEN null; END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE answer_letter_enum AS ENUM (
                'A', 'B', 'C', 'D'
            );
        EXCEPTION WHEN duplicate_object THEN null; END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE audit_action_enum AS ENUM (
                'USER_LOGIN', 'USER_LOGIN_FAILED', 'USER_LOGOUT',
                'STUDENT_CREATED', 'STUDENT_UPDATED', 'STUDENT_DELETED',
                'STUDENTS_IMPORTED',
                'CARD_CREATED', 'CARD_ASSIGNED', 'CARD_UNASSIGNED',
                'CARD_DISABLED', 'CARD_REPLACED',
                'TEACHER_CREATED', 'TEACHER_UPDATED',
                'QUIZ_CREATED', 'QUIZ_STARTED', 'QUIZ_ENDED',
                'RESPONSE_SUBMITTED'
            );
        EXCEPTION WHEN duplicate_object THEN null; END $$;
    """)

    # ── schools ────────────────────────────────────────────────────────────
    op.create_table(
        "schools",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("school_code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("email", sa.String(254), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "inactive", "suspended", name="school_status_enum", create_type=False),
            nullable=False,
            server_default="active",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint("school_code", name="uq_school_code"),
    )
    op.create_index("ix_schools_school_code", "schools", ["school_code"])

    # ── academic_years ─────────────────────────────────────────────────────
    op.create_table(
        "academic_years",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("school_id", "name", name="uq_academic_year_school_name"),
    )
    op.create_index("ix_academic_year_school_id", "academic_years", ["school_id"])
    op.create_index("ix_academic_year_school_active", "academic_years", ["school_id", "is_active"])

    # ── classes ────────────────────────────────────────────────────────────
    op.create_table(
        "classes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_year_id", sa.Integer(), sa.ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("grade", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("school_id", "academic_year_id", "name", name="uq_class_school_year_name"),
    )
    op.create_index("ix_classes_school_id", "classes", ["school_id"])
    op.create_index("ix_classes_academic_year_id", "classes", ["academic_year_id"])

    # ── sections ───────────────────────────────────────────────────────────
    op.create_table(
        "sections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("class_id", "name", name="uq_section_class_name"),
    )
    op.create_index("ix_sections_class_id", "sections", ["class_id"])

    # ── users ──────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=True),
        sa.Column("username", sa.String(150), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column(
            "role",
            sa.Enum("SUPER_ADMIN", "SCHOOL_ADMIN", "TEACHER", "STUDENT", name="user_role_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint("school_id", "username", name="uq_user_school_username"),
        sa.UniqueConstraint("school_id", "email", name="uq_user_school_email"),
    )
    op.create_index("ix_users_school_id", "users", ["school_id"])
    op.create_index("ix_user_email", "users", ["email"])
    op.create_index("ix_user_school_role", "users", ["school_id", "role"])

    # ── teachers ───────────────────────────────────────────────────────────
    op.create_table(
        "teachers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.String(50), nullable=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("school_id", "employee_id", name="uq_teacher_school_employee_id"),
    )
    op.create_index("ix_teacher_school", "teachers", ["school_id"])

    # ── students ───────────────────────────────────────────────────────────
    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("section_id", sa.Integer(), sa.ForeignKey("sections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("student_code", sa.String(50), nullable=False),
        sa.Column("roll_number", sa.Integer(), nullable=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("parent_contact", sa.String(30), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "inactive", "transferred", name="student_status_enum", create_type=False),
            nullable=False,
            server_default="active",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint("school_id", "student_code", name="uq_student_school_code"),
    )
    op.create_index("ix_students_school_id", "students", ["school_id"])
    op.create_index("ix_students_class_id", "students", ["class_id"])
    op.create_index("ix_students_section_id", "students", ["section_id"])
    op.create_index("ix_students_student_code", "students", ["student_code"])

    # ── cards ──────────────────────────────────────────────────────────────
    op.create_table(
        "cards",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("card_number", sa.Integer(), nullable=False),
        sa.Column("marker_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("available", "assigned", "lost", "disabled", name="card_status_enum", create_type=False),
            nullable=False,
            server_default="available",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("school_id", "card_number", name="uq_card_school_number"),
        sa.UniqueConstraint("school_id", "marker_id", name="uq_card_school_marker"),
    )
    op.create_index("ix_cards_school_id", "cards", ["school_id"])
    op.create_index("ix_card_school_marker", "cards", ["school_id", "marker_id"])
    op.create_index("ix_card_school_number", "cards", ["school_id", "card_number"])

    # ── student_cards ──────────────────────────────────────────────────────
    op.create_table(
        "student_cards",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("card_id", sa.Integer(), sa.ForeignKey("cards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("unassigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index("ix_student_cards_student_id", "student_cards", ["student_id"])
    op.create_index("ix_student_cards_card_id", "student_cards", ["card_id"])
    op.create_index("ix_student_cards_is_active", "student_cards", ["is_active"])
    # Partial unique indexes for PostgreSQL
    op.execute("""
        CREATE UNIQUE INDEX uix_student_active_card
        ON student_cards (student_id)
        WHERE is_active = true;
    """)
    op.execute("""
        CREATE UNIQUE INDEX uix_card_active_student
        ON student_cards (card_id)
        WHERE is_active = true;
    """)

    # ── question_sets ──────────────────────────────────────────────────────
    op.create_table(
        "question_sets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("teacher_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("subject", sa.String(100), nullable=True),
        sa.Column("grade", sa.String(20), nullable=True),
        sa.Column(
            "status",
            sa.Enum("draft", "published", "archived", name="question_set_status_enum", create_type=False),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_question_sets_school_id", "question_sets", ["school_id"])
    op.create_index("ix_question_sets_teacher_id", "question_sets", ["teacher_id"])

    # ── questions ──────────────────────────────────────────────────────────
    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("question_set_id", sa.Integer(), sa.ForeignKey("question_sets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("option_a", sa.String(500), nullable=False),
        sa.Column("option_b", sa.String(500), nullable=False),
        sa.Column("option_c", sa.String(500), nullable=False),
        sa.Column("option_d", sa.String(500), nullable=False),
        sa.Column(
            "correct_answer",
            sa.Enum("A", "B", "C", "D", name="answer_letter_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("marks", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_questions_question_set_id", "questions", ["question_set_id"])

    # ── quiz_sessions ──────────────────────────────────────────────────────
    op.create_table(
        "quiz_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("question_set_id", sa.Integer(), sa.ForeignKey("question_sets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("teacher_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("section_id", sa.Integer(), sa.ForeignKey("sections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "active", "paused", "ended", name="quiz_session_status_enum", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_quiz_sessions_question_set_id", "quiz_sessions", ["question_set_id"])
    op.create_index("ix_quiz_sessions_teacher_id", "quiz_sessions", ["teacher_id"])
    op.create_index("ix_quiz_sessions_class_id", "quiz_sessions", ["class_id"])
    op.create_index("ix_quiz_sessions_section_id", "quiz_sessions", ["section_id"])
    op.create_index("ix_quiz_session_status", "quiz_sessions", ["status"])

    # ── responses ──────────────────────────────────────────────────────────
    op.create_table(
        "responses",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("quiz_session_id", sa.Integer(), sa.ForeignKey("quiz_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("card_id", sa.Integer(), sa.ForeignKey("cards.id", ondelete="RESTRICT"), nullable=False),
        sa.Column(
            "answer",
            sa.Enum("A", "B", "C", "D", name="answer_letter_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("marks_obtained", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rotation", sa.Integer(), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "quiz_session_id", "question_id", "student_id",
            name="uq_response_session_question_student",
        ),
    )
    op.create_index("ix_responses_quiz_session_id", "responses", ["quiz_session_id"])
    op.create_index("ix_responses_question_id", "responses", ["question_id"])
    op.create_index("ix_responses_student_id", "responses", ["student_id"])
    op.create_index("ix_response_session_student", "responses", ["quiz_session_id", "student_id"])

    # ── student_scores ─────────────────────────────────────────────────────
    op.create_table(
        "student_scores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("quiz_session_id", sa.Integer(), sa.ForeignKey("quiz_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("total_questions", sa.Integer(), nullable=False),
        sa.Column("correct_answers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("incorrect_answers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("percentage", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("quiz_session_id", "student_id", name="uq_score_session_student"),
    )
    op.create_index("ix_student_scores_quiz_session_id", "student_scores", ["quiz_session_id"])
    op.create_index("ix_student_scores_student_id", "student_scores", ["student_id"])

    # ── audit_logs ─────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "action",
            sa.Enum(
                "USER_LOGIN", "USER_LOGIN_FAILED", "USER_LOGOUT",
                "STUDENT_CREATED", "STUDENT_UPDATED", "STUDENT_DELETED", "STUDENTS_IMPORTED",
                "CARD_CREATED", "CARD_ASSIGNED", "CARD_UNASSIGNED", "CARD_DISABLED", "CARD_REPLACED",
                "TEACHER_CREATED", "TEACHER_UPDATED",
                "QUIZ_CREATED", "QUIZ_STARTED", "QUIZ_ENDED", "RESPONSE_SUBMITTED",
                name="audit_action_enum", create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
    )
    op.create_index("ix_audit_logs_school_id", "audit_logs", ["school_id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])
    op.create_index("ix_audit_school_timestamp", "audit_logs", ["school_id", "timestamp"])
    op.create_index("ix_audit_user_action", "audit_logs", ["user_id", "action"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("student_scores")
    op.drop_table("responses")
    op.drop_table("quiz_sessions")
    op.drop_table("questions")
    op.drop_table("question_sets")
    op.drop_table("student_cards")
    op.drop_table("cards")
    op.drop_table("students")
    op.drop_table("teachers")
    op.drop_table("users")
    op.drop_table("sections")
    op.drop_table("classes")
    op.drop_table("academic_years")
    op.drop_table("schools")

    # Drop enum types
    for enum_name in [
        "audit_action_enum", "answer_letter_enum", "quiz_session_status_enum",
        "question_set_status_enum", "card_status_enum", "student_status_enum",
        "school_status_enum", "user_role_enum",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name};")
