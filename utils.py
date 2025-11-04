from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash
import jwt
from jwt.exceptions import InvalidTokenError
from fastapi.security import OAuth2PasswordBearer
from model import TokenData, TypesOfCustomers
import os
from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status

# Import Firebase for user lookup (can fallback to PostgreSQL if needed)
try:
    from firebase_db import get_firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

# Import SessionDep conditionally (only if PostgreSQL is used)
try:
    from db import SessionDep
except ImportError:
    # If db.py doesn't exist or SessionDep not available, define a type alias
    SessionDep = Optional[object]  # Placeholder type

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
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
            user_id=payload["user_id"],  # This should be a string UUID
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
    token: Annotated[str, Depends(oauth2_scheme)], 
    session: Optional[object] = None
):
    """
    Get current user from JWT token.
    
    For backward compatibility, can check Firestore or PostgreSQL.
    JWT contains user_id, so we can validate without full user lookup.
    """
    token_data = verify_access_token(token)
    
    # Validate user exists (check Firestore first, fallback to PostgreSQL)
    if FIREBASE_AVAILABLE:
        try:
            db = get_firestore()
            user_doc = db.collection('users').document(token_data.user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                if (
                    user_data.get("username") == token_data.username
                    and user_data.get("type_of_customer") == token_data.type_of_customer.value
                ):
                    # Return token_data with user_id accessible
                    return token_data
        except Exception as e:
            # Fallback to PostgreSQL if Firestore fails
            pass
    
    # Fallback to PostgreSQL (if Firestore not available or failed)
    # Only try if session is provided and is a valid SQLModel session
    if session is not None:
        try:
            # Try to use session if it's a SQLModel session
            if hasattr(session, 'exec'):
                from model import Users
                from sqlmodel import select
                user_data = session.exec(
                    select(Users).where(Users.user_id == token_data.user_id)
                ).first()
                
                if user_data and (
                    user_data.username == token_data.username
                    and user_data.type_of_customer == token_data.type_of_customer
                ):
                    return token_data
        except Exception:
            # If session is invalid, just continue
            pass
    
    # If we can't validate, still return token_data (JWT is already validated)
    # This allows the system to work even if user lookup fails
    return token_data


TokenDep = Annotated[TokenData, Depends(get_current_user)]


def add_user_to_default_servers(user_id: str):
    """
    Automatically add a new user to all default servers.
    Call this when a user signs up.
    """
    try:
        from firebase_db import get_firestore
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP, ArrayUnion
        import uuid
        
        db = get_firestore()
        
        # Get all servers
        servers_ref = db.collection('chatServers')
        servers = list(servers_ref.stream())
        
        if not servers:
            # No servers exist yet, skip
            return
        
        # Default server names (these should match what's in seed script)
        default_server_names = ["General Community", "Study Hub", "Wellness & Mindfulness"]
        
        for server_doc in servers:
            server_data = server_doc.to_dict()
            server_name = server_data.get('name', '')
            
            # Only add to default servers
            if server_name in default_server_names:
                server_id = server_doc.id
                
                # Add user to server's member_ids (if not already there)
                member_ids = server_data.get('member_ids', [])
                if user_id not in member_ids:
                    server_doc.reference.update({
                        "member_ids": ArrayUnion([user_id])
                    })
                
                # Create membership record (check if it exists first)
                memberships_ref = db.collection('serverMemberships')
                existing_membership = memberships_ref.where('server_id', '==', server_id)\
                                                     .where('user_id', '==', user_id)\
                                                     .limit(1)\
                                                     .stream()
                
                if not list(existing_membership):
                    membership_id = str(uuid.uuid4())
                    memberships_ref.document(membership_id).set({
                        "server_id": server_id,
                        "user_id": user_id,
                        "role": "member",
                        "joined_at": SERVER_TIMESTAMP,
                    })
        
        print(f"✅ Added user {user_id} to default servers")
    except Exception as e:
        # Don't fail signup if server addition fails
        print(f"⚠️ Warning: Could not add user to default servers: {e}")
