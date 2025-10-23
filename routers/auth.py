from fastapi import APIRouter, Depends, status, HTTPException
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "Invalid credentials", "message": "User not found"}
            )
        if verify_password(login_data.password, user_data_table_result.password):
            access_token_creation_data = TokenData(
                user_id=str(user_data_table_result.user_id),
                username=user_data_table_result.username,
                type_of_customer=user_data_table_result.type_of_customer,
            )
            access_token = create_jwt(access_token_creation_data)
            return Token(access_token=access_token, token_type="bearer")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Invalid credentials", "message": "Incorrect password"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Bad Request", "message": str(e)}
        )


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def create_new_account(login_data: SignupData, session: SessionDep):
    try:
        # Check if username already exists
        existing_user = session.exec(
            select(Users).where(Users.username == login_data.username)
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Username already exists", "message": "Please choose a different username"}
            )
        
        # Check if email already exists
        existing_email = session.exec(
            select(Users).where(Users.email == login_data.email)
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Email already exists", "message": "This email is already registered"}
            )
        
        new_user = Users(
            username=login_data.username,
            password=hash_password(login_data.password),
            email=login_data.email,
            type_of_customer=TypesOfCustomers.FREE,
        )
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        
        return {
            "message": "User created successfully",
            "user_id": str(new_user.user_id),
            "username": new_user.username,
            "email": new_user.email
        }
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Registration failed", "message": str(e)}
        )
