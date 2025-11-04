"""
Authentication Router - Firebase Version

Handles user authentication using Firebase Firestore only.
"""

from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from model import TypesOfCustomers, Token, TokenData, SignupData
from utils import verify_password, create_jwt, hash_password
from typing import Annotated
from datetime import datetime
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
import uuid

from firebase_db import get_firestore
from utils import add_user_to_default_servers

router = APIRouter(tags=["Authentication"])


@router.post("/login", response_model=Token)
def login(
    login_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    """
    Login endpoint - uses Firebase Firestore only
    """
    try:
        db = get_firestore()
        users_ref = db.collection('users')
        query = users_ref.where('username', '==', login_data.username).limit(1)
        user_docs = list(query.stream())
        
        if not user_docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "Invalid credentials", "message": "User not found"}
            )
        
        user_doc = user_docs[0]
        user_data = user_doc.to_dict()
        user_data['user_id'] = user_doc.id  # Document ID is user_id
        
        if verify_password(login_data.password, user_data["password"]):
            # Get type_of_customer (handle enum or string)
            type_of_customer = user_data.get("type_of_customer")
            if hasattr(type_of_customer, 'value'):
                type_of_customer = type_of_customer.value
            
            access_token_creation_data = TokenData(
                user_id=str(user_data["user_id"]),
                username=user_data["username"],
                type_of_customer=TypesOfCustomers(type_of_customer) if isinstance(type_of_customer, str) else type_of_customer,
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
def create_new_account(login_data: SignupData):
    """
    Create new account - saves to Firebase Firestore only
    """
    try:
        db = get_firestore()
        users_ref = db.collection('users')
        
        # Check username
        username_query = users_ref.where('username', '==', login_data.username).limit(1)
        if list(username_query.stream()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Username already exists", "message": "Please choose a different username"}
            )
        
        # Check email
        email_query = users_ref.where('email', '==', login_data.email).limit(1)
        if list(email_query.stream()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Email already exists", "message": "This email is already registered"}
            )
        
        # Create user in Firestore
        user_id = str(uuid.uuid4())
        user_data = {
            "username": login_data.username,
            "password": hash_password(login_data.password),
            "email": login_data.email,
            "type_of_customer": TypesOfCustomers.FREE.value,
            "created_at": SERVER_TIMESTAMP,
        }
        
        users_ref.document(user_id).set(user_data)
        
        # Automatically add new user to default servers
        try:
            add_user_to_default_servers(user_id)
        except Exception as e:
            # Don't fail signup if server addition fails
            print(f"⚠️ Warning: Could not add user to default servers: {e}")
        
        return {
            "message": "User created successfully",
            "user_id": user_id,
            "username": login_data.username,
            "email": login_data.email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Registration failed", "message": str(e)}
        )
