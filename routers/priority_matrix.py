import select
from typing import Optional
from fastapi import APIRouter, Response, status
from datetime import date
from sqlmodel import select

from db import SessionDep
from model import PriorityMatrix

router = APIRouter()


@router.post("/priority_matrix")
async def add_task(session: SessionDep, data: PriorityMatrix):
    try:
        new_row = PriorityMatrix(
            id=data.id,
            user_name=data.user_name,
            quadrant=data.quadrant,
            title=data.title,
            description=data.description,
        )
        session.add(new_row)
        session.commit()
        return Response(status_code=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


@router.get("/priority_matrix")
async def get_priority_matrix(
    session: SessionDep, user_name: Optional[str] = None, day: Optional[str] = None
):
    """Getting information of the users priority matrix

    Args:
        session (SessionDep)
        user_name (Optional[str], optional): User Name of the user. Defaults to None.
        date (Optional[str], optional): The date of the priority matrix. Accepts date in the format "yyyy-mm-dd" Defaults to None.
    """
    try:
        if day is not None:
            day = day.split("-")
            day = date(int(day[0]), int(day[1]), int(day[2]))
            results = session.exec(
                select(PriorityMatrix)
                .where(PriorityMatrix.user_name == user_name)
                .where(PriorityMatrix.created_at == day)
            ).all()
        else:
            results = session.exec(
                select(PriorityMatrix).where(PriorityMatrix.user_name == user_name)
            ).all()
        if results == None:
            return Response(status_code=status.HTTP_404_NOT_FOUND)
        return results
    except Exception as e:
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


@router.delete("/priority_matrix")
async def delete_task(session: SessionDep, id: str):
    try:
        result = session.exec(
            select(PriorityMatrix).where(PriorityMatrix.id == id)
        ).one()
        if result is not None:
            session.delete(result)
            session.commit()
        return Response(status_code=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )


@router.patch("/priority_matrix")
async def update_task(session: SessionDep, changed_data: PriorityMatrix):
    try:
        result = session.exec(
            select(PriorityMatrix).where(PriorityMatrix.id == changed_data.id)
        ).one()
        if result is None:
            return Response(status_code=status.HTTP_404_NOT_FOUND)
        result.quadrant = changed_data.quadrant
        result.title = changed_data.title
        result.description = changed_data.description
        session.add(result)
        session.commit()
        return Response(status_code=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )
