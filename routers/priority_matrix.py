import select
from typing import Optional
import uuid
from fastapi import APIRouter, Response, status
from datetime import date
from sqlmodel import select
from db import SessionDep
from model import PriorityMatrix, TaskData, DeleteTaskData
from utils import TokenDep

router = APIRouter(tags=["PriorityMatrix"])


@router.post("/priority_matrix", status_code=status.HTTP_200_OK)
async def add_task(session: SessionDep, token_data: TokenDep, data: TaskData):
    try:
        new_row = PriorityMatrix(
            user_id=token_data.user_id,
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
    session: SessionDep, token_data: TokenDep, day: Optional[str] = None
):
    """Getting information of the users priority matrix

    Args:
        session (SessionDep)
        username (Optional[str], optional): User Name of the user. Defaults to None.
        date (Optional[str], optional): The date of the priority matrix. Accepts date in the format "yyyy-mm-dd" Defaults to None.
    """
    try:
        if day is not None:
            day = day.split("-")
            day = date(int(day[0]), int(day[1]), int(day[2]))
            results = session.exec(
                select(PriorityMatrix)
                .where(PriorityMatrix.user_id == token_data.user_id)
                .where(PriorityMatrix.created_at == day)
            ).all()
        else:
            results = session.exec(
                select(PriorityMatrix).where(
                    PriorityMatrix.user_id == token_data.user_id
                )
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
async def delete_task(session: SessionDep, task_data: DeleteTaskData):
    try:
        result = session.exec(
            select(PriorityMatrix).where(PriorityMatrix.id == uuid.UUID(task_data.id))
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
async def update_task(
    session: SessionDep, token_data: TokenDep, changed_data: TaskData
):
    try:
        result = session.exec(
            select(PriorityMatrix).where(
                PriorityMatrix.id == uuid.UUID(changed_data.id)
            )
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
