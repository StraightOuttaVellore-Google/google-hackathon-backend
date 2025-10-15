from fastapi import APIRouter, Depends, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select
from db import SessionDep
from model import TypesOfCustomers, Users, Token, TokenData, SignupData
from utils import verify_password, create_jwt, hash_password
from typing import Annotated


router = APIRouter(tags=["Authentication"])


@router.post("/login", response_model=Token)
def login(
    login_data: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep
):
    try:
        user_data_table_result = session.exec(
            select(Users).where(Users.username == login_data.username)
        ).first()
        if user_data_table_result is None:
            return Response(
                status_code=status.HTTP_404_NOT_FOUND, content="Invalid credentials"
            )
        if verify_password(login_data.password, user_data_table_result.password):
            access_token_creation_data = TokenData(
                user_id=str(user_data_table_result.user_id),
                username=user_data_table_result.username,
                type_of_customer=user_data_table_result.type_of_customer,
            )
            access_token = create_jwt(access_token_creation_data)
            return Token(access_token=access_token, token_type="bearer")
        return Response(
            status_code=status.HTTP_404_NOT_FOUND, content="Invalid credentials"
        )
    except Exception as e:
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST, content=f"Exception {e} occured"
        )


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def create_new_account(login_data: SignupData, session: SessionDep):
    try:
        new_user = Users(
            username=login_data.username,
            password=hash_password(login_data.password),
            email=login_data.email,
            type_of_customer=TypesOfCustomers.FREE,
        )
        session.add(new_user)
        session.commit()
        return Response(status_code=status.HTTP_201_CREATED, content="New user added")
    except Exception as e:
        session.rollback()
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST, content=f"Exception {e} occured"
        )
