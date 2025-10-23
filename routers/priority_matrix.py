import select
from typing import Optional
import uuid
from fastapi import APIRouter, HTTPException, Response, status
from datetime import date
from sqlmodel import select
from db import SessionDep
from model import PriorityMatrix, TaskData, DeleteTaskData, TaskStatus
from utils import TokenDep

router = APIRouter(tags=["PriorityMatrix"])


@router.post(
    "/priority_matrix",
    status_code=status.HTTP_201_CREATED,
    response_model=PriorityMatrix,
)
async def add_task(session: SessionDep, token_data: TokenDep, data: TaskData):
    try:
        new_row = PriorityMatrix(
            user_id=uuid.UUID(token_data.user_id),  # Convert string UUID to UUID object
            quadrant=data.quadrant,
            title=data.title,
            description=data.description,
            status=data.status if data.status else TaskStatus.TODO,
            due_date=data.due_date,
        )
        session.add(new_row)
        session.commit()
        session.refresh(new_row)  # Refresh to get any server-generated fields
        return new_row
    except Exception as e:
        # Log the actual error for debugging
        print(f"Database error in add_task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error:\n{e}",
        )


@router.get("/priority_matrix")
async def get_priority_matrix(
    session: SessionDep, token_data: TokenDep, day: Optional[str] = None, due: Optional[str] = None
):
    """Getting information of the users priority matrix

    Args:
        session (SessionDep)
        username (Optional[str], optional): User Name of the user. Defaults to None.
        date (Optional[str], optional): The date of the priority matrix. Accepts date in the format "yyyy-mm-dd" Defaults to None.
    """
    try:
        if due is not None:
            # Filter by due_date
            due_parts = due.split("-")
            due_dt = date(int(due_parts[0]), int(due_parts[1]), int(due_parts[2]))
            results = session.exec(
                select(PriorityMatrix)
                .where(PriorityMatrix.user_id == uuid.UUID(token_data.user_id))
                .where(PriorityMatrix.due_date == due_dt)
            ).all()
        elif day is not None:
            day = day.split("-")
            day = date(int(day[0]), int(day[1]), int(day[2]))
            results = session.exec(
                select(PriorityMatrix)
                .where(PriorityMatrix.user_id == uuid.UUID(token_data.user_id))
                .where(PriorityMatrix.created_at == day)
            ).all()
        else:
            results = session.exec(
                select(PriorityMatrix).where(
                    PriorityMatrix.user_id == uuid.UUID(token_data.user_id)
                )
            ).all()
        if results == None:
            return Response(status_code=status.HTTP_404_NOT_FOUND)
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error:\n{e}",
        )


@router.delete("/priority_matrix", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    session: SessionDep, token_data: TokenDep, task_data: DeleteTaskData
):
    try:
        try:
            task_uuid = uuid.UUID(task_data.id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid task ID format",
            )

        result = session.exec(
            select(PriorityMatrix)
            .where(PriorityMatrix.id == task_uuid)
            .where(PriorityMatrix.user_id == uuid.UUID(token_data.user_id))
        ).one()
        if result is not None:
            session.delete(result)
            session.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error:\n{e}",
        )


@router.patch("/priority_matrix", response_model=PriorityMatrix)
async def update_task(
    session: SessionDep, token_data: TokenDep, changed_data: TaskData
):
    try:
        task_uuid = uuid.UUID(changed_data.id)
        result = session.exec(
            select(PriorityMatrix)
            .where(PriorityMatrix.id == task_uuid)
            .where(PriorityMatrix.user_id == uuid.UUID(token_data.user_id))
        ).one()
        if result is None:
            return Response(status_code=status.HTTP_404_NOT_FOUND)
        result.quadrant = changed_data.quadrant
        result.title = changed_data.title
        result.description = changed_data.description
        result.status = changed_data.status if changed_data.status else result.status
        if changed_data.due_date is not None:
            result.due_date = changed_data.due_date
        session.add(result)
        session.commit()
        session.refresh(result)
        return result
    except Exception as e:
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Internal Server Error:\n{e}",
        )
