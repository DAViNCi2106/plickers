"""
setup_local.py
==============
One-shot local dev setup using SQLite (no Docker / PostgreSQL needed).

Run:
    python setup_local.py

This will:
  1. Create the SQLite database with all tables
  2. Seed demo data (school, 2 teachers, 50 students, cards, quiz session)
  3. Print login credentials
"""
from __future__ import annotations

import os
import sys

# Load .env first
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import Base

# Ensure all models are registered with Base.metadata
import app.models  # noqa: F401

def main() -> None:
    db_url = settings.DATABASE_URL_SYNC or settings.DATABASE_URL.replace("+aiosqlite", "").replace("+asyncpg", "")
    print(f"Using database: {db_url}")

    engine = create_engine(db_url, echo=False)

    print("\n[1/2] Creating all tables...")
    Base.metadata.create_all(engine)
    print("      Tables created OK.")

    print("\n[2/2] Seeding demo data...")
    from scripts.seed import seed
    with Session(engine) as session:
        try:
            seed(session)
        except Exception as e:
            # If already seeded, just warn
            if "UNIQUE constraint failed" in str(e) or "already exists" in str(e).lower():
                print(f"\n  [WARN] Data may already be seeded (duplicate key): {e}")
                print("     Delete 'plickers_dev.db' and re-run to reset.\n")
            else:
                raise

    print("\n[DONE] Local setup complete!")
    print("    Run the server with:")
    print("      python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    print("    Then open: http://localhost:8000/docs\n")


if __name__ == "__main__":
    main()
