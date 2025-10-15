from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash
import jwt
from jwt.exceptions import InvalidTokenError
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import select
from model import TokenData, Users
import os
from typing import Annotated
from db import SessionDep
from fastapi import Depends, HTTPException, status

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password_gt: str) -> bool:
    return password_hash.verify(password, hashed_password_gt)


def create_jwt(data: TokenData):
    to_encode = data.model_dump()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, ALGORITHM)
    return encoded_jwt


def verify_access_token(token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload is None:
            raise CREDENTIALS_EXCEPTION
        token_data = TokenData(
            user_id=payload["user_id"],
            username=payload["username"],
            type_of_customer=payload["type_of_customer"],
        )
    except InvalidTokenError:
        raise CREDENTIALS_EXCEPTION

    user = token_data.username
    if user is None:
        raise CREDENTIALS_EXCEPTION

    return token_data


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], session: SessionDep
):
    token_data = verify_access_token(token)
    user_data = session.exec(
        select(Users).where(Users.user_id == token_data.user_id)
    ).first()

    if (
        user_data.username == token_data.username
        and user_data.type_of_customer == token_data.type_of_customer
    ):
        return token_data

    raise CREDENTIALS_EXCEPTION


TokenDep = Annotated[TokenData, Depends(get_current_user)]
