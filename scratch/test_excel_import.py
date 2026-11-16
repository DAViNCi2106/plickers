import asyncio
import io
import os
import sys
from pathlib import Path

sys.path.insert(0, r"c:\Project\plickers\school-response-server")

import pandas as pd
from sqlalchemy import select

from app.db.session import AsyncSessionFactory
from app.models.student import Student
from app.models.card import Card, StudentCard
from app.services.card_service import import_students_from_file

async def run_test():
    async with AsyncSessionFactory() as db:
        # Create a sample DataFrame without Card ID column
        df = pd.DataFrame([
            {"Student Name": "Ananya Roy", "Roll No": 101},
            {"Student Name": "Vikram Sethi", "Roll No": 102},
            {"Student Name": "Meera Nair", "Roll No": 103},
        ])
        
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_bytes = excel_buffer.getvalue()
        
        school_id = 1
        summary = await import_students_from_file(
            db=db,
            school_id=school_id,
            class_id=None,
            section_id=None,
            file_bytes=excel_bytes,
            filename="new_students.xlsx",
            user_id=1,
        )
        await db.commit()
        
        print("Import Summary:")
        print(f"Total: {summary.total_records}, Success: {summary.successful}, Failed: {summary.failed}")
        if summary.errors:
            for err in summary.errors:
                print(f"  Error on row {err.row}: {err.reason}")
                
        # Check newly assigned cards
        result = await db.execute(
            select(Student.first_name, Student.student_code, Card.card_number)
            .join(StudentCard, StudentCard.student_id == Student.id)
            .join(Card, StudentCard.card_id == Card.id)
            .where(Student.first_name.in_(["Ananya", "Vikram", "Meera"]))
        )
        rows = result.all()
        print("\nAssigned Students & Unique Cards:")
        for first_name, code, card_num in rows:
            print(f"Student: {first_name} | Code: {code} | Card #{card_num}")

if __name__ == "__main__":
    asyncio.run(run_test())
