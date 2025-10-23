from fastapi import APIRouter, Response, status
from sqlmodel import select
from datetime import datetime
from db import SessionDep
from model import DailyJournalData, DailyJournalDataInput
from utils import TokenDep


router = APIRouter(tags=["DailyJournal"])


@router.get("/daily_journal")
async def get_all_daily_journal(token_data: TokenDep, session: SessionDep):
    """Get all daily journal entries for the current user"""
    try:
        entries = session.exec(
            select(DailyJournalData)
            .where(DailyJournalData.user_id == token_data.user_id)
            .order_by(DailyJournalData.journal_date.desc())
        ).all()

        if not entries:
            return []

        return [
            {
                "id": str(entry.id),
                "journal_date": entry.journal_date.isoformat(),
                "study_mode": entry.study_mode,
                "mood": entry.mood,
                "stress_level": entry.stress_level,
                "notes": entry.notes,
                "data": entry.data,
                "created_at": entry.created_at.isoformat()
                if entry.created_at
                else None,
            }
            for entry in entries
        ]
    except Exception as e:
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


@router.get("/daily_journal/{date}")
async def get_daily_journal_by_date(
    date: str, token_data: TokenDep, session: SessionDep
):
    """Get daily journal entry for a specific date (format: YYYY-MM-DD)"""
    try:
        # Parse date
        journal_date = datetime.strptime(date, "%Y-%m-%d").date()

        entry = session.exec(
            select(DailyJournalData)
            .where(DailyJournalData.user_id == token_data.user_id)
            .where(DailyJournalData.journal_date == journal_date)
        ).first()

        if not entry:
            return Response(status_code=status.HTTP_404_NOT_FOUND)

        return {
            "id": str(entry.id),
            "journal_date": entry.journal_date.isoformat(),
            "study_mode": entry.study_mode,
            "mood": entry.mood,
            "stress_level": entry.stress_level,
            "notes": entry.notes,
            "data": entry.data,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        }
    except ValueError:
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST,
            content="Invalid date format. Use YYYY-MM-DD",
        )
    except Exception as e:
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


@router.post("/daily_journal", status_code=status.HTTP_201_CREATED)
async def create_daily_journal(
    data: DailyJournalDataInput, token_data: TokenDep, session: SessionDep
):
    """Create a new daily journal entry"""
    try:
        # Parse date
        journal_date = datetime.strptime(data.journal_date, "%Y-%m-%d").date()

        # Check if entry already exists for this date
        existing = session.exec(
            select(DailyJournalData)
            .where(DailyJournalData.user_id == token_data.user_id)
            .where(DailyJournalData.journal_date == journal_date)
        ).first()

        if existing:
            # Update existing entry
            existing.study_mode = data.study_mode
            if data.mood is not None:
                existing.mood = data.mood
            if data.stress_level is not None:
                existing.stress_level = data.stress_level
            if data.notes is not None:
                existing.notes = data.notes
            if data.data is not None:
                existing.data = data.data

            session.add(existing)
            session.commit()
            return Response(status_code=status.HTTP_200_OK)

        # Create new entry
        new_entry = DailyJournalData(
            user_id=token_data.user_id,
            journal_date=journal_date,
            study_mode=data.study_mode,
            mood=data.mood,
            stress_level=data.stress_level,
            notes=data.notes,
            data=data.data,
        )
        session.add(new_entry)
        session.commit()
        return Response(status_code=status.HTTP_201_CREATED)
    except ValueError:
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST,
            content="Invalid date format. Use YYYY-MM-DD",
        )
    except Exception as e:
        session.rollback()
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


@router.patch("/daily_journal/{date}")
async def update_daily_journal(
    date: str, data: DailyJournalDataInput, token_data: TokenDep, session: SessionDep
):
    """Update a daily journal entry for a specific date"""
    try:
        # Parse date
        journal_date = datetime.strptime(date, "%Y-%m-%d").date()

        entry = session.exec(
            select(DailyJournalData)
            .where(DailyJournalData.user_id == token_data.user_id)
            .where(DailyJournalData.journal_date == journal_date)
        ).first()

        if not entry:
            return Response(
                status_code=status.HTTP_404_NOT_FOUND,
                content="Journal entry not found for this date",
            )

        # Update fields
        entry.study_mode = data.study_mode
        if data.mood is not None:
            entry.mood = data.mood
        if data.stress_level is not None:
            entry.stress_level = data.stress_level
        if data.notes is not None:
            entry.notes = data.notes
        if data.data is not None:
            entry.data = data.data

        session.add(entry)
        session.commit()
        return Response(status_code=status.HTTP_200_OK)
    except ValueError:
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST,
            content="Invalid date format. Use YYYY-MM-DD",
        )
    except Exception as e:
        session.rollback()
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


@router.delete("/daily_journal/{date}")
async def delete_daily_journal(date: str, token_data: TokenDep, session: SessionDep):
    """Delete a daily journal entry for a specific date"""
    try:
        # Parse date
        journal_date = datetime.strptime(date, "%Y-%m-%d").date()

        entry = session.exec(
            select(DailyJournalData)
            .where(DailyJournalData.user_id == token_data.user_id)
            .where(DailyJournalData.journal_date == journal_date)
        ).first()

        if not entry:
            return Response(
                status_code=status.HTTP_404_NOT_FOUND,
                content="Journal entry not found for this date",
            )

        session.delete(entry)
        session.commit()
        return Response(status_code=status.HTTP_200_OK)
    except ValueError:
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST,
            content="Invalid date format. Use YYYY-MM-DD",
        )
    except Exception as e:
        session.rollback()
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )
