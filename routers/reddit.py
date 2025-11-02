"""
Reddit Router - Firebase Version

Handles Reddit community features using Firebase Firestore for real-time sync.
"""

from fastapi import APIRouter, Depends, status, HTTPException, Query, Request
from datetime import datetime
from typing import List, Optional
import uuid
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from model import (
    CountryResponse, PostCreate, PostResponse,
    CommentCreate, CommentResponse, VoteRequest, ReportRequest,
    TokenData
)
from firebase_db import get_firestore
from utils import TokenDep, oauth2_scheme

router = APIRouter(prefix="/reddit", tags=["Reddit"])


# ==================== HELPER FUNCTIONS ====================

def _get_current_user_optional(request: Request):
    """Helper function for optional authentication - returns TokenData if token is valid, None otherwise"""
    try:
        from utils import SECRET_KEY, ALGORITHM
        from model import TokenData
        import jwt
        from jwt.exceptions import InvalidTokenError
        
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return None
        
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload is None:
            return None
        
        return TokenData(
            user_id=payload["user_id"],
            username=payload["username"],
            type_of_customer=payload["type_of_customer"],
        )
    except (InvalidTokenError, KeyError, ValueError):
        return None
    except Exception:
        return None




def _get_username_from_user_id(db, user_id: str) -> str:
    """Get username from user_id"""
    try:
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        if user_doc.exists:
            return user_doc.to_dict().get('username', 'Unknown')
    except:
        pass
    return "Unknown"


def _get_usernames_batch(db, user_ids: List[str]) -> dict:
    """Get usernames for multiple user IDs"""
    username_map = {}
    for user_id in user_ids:
        try:
            user_ref = db.collection('users').document(user_id)
            user_doc = user_ref.get()
            if user_doc.exists:
                username_map[user_id] = user_doc.to_dict().get('username', 'Unknown')
        except:
            username_map[user_id] = "Unknown"
    return username_map


# ==================== COUNTRIES ====================

@router.get("/countries", response_model=List[CountryResponse])
async def get_countries():
    """Get all active countries"""
    try:
        db = get_firestore()
        countries_ref = db.collection('countries')
        # ONLY filter by is_active to avoid composite index requirement
        query = countries_ref.where('is_active', '==', True)
        all_docs = list(query.stream())
        
        # Sort by name in Python
        all_docs.sort(key=lambda x: x.to_dict().get('name', ''))
        
        countries = []
        for doc in all_docs:
            data = doc.to_dict()
            # Handle timestamp conversion
            created_at = data.get('created_at')
            if hasattr(created_at, 'timestamp'):
                created_at = datetime.fromtimestamp(created_at.timestamp())
            elif isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            elif created_at is None:
                created_at = datetime.utcnow()
            
            countries.append(CountryResponse(
                id=doc.id,
                iso_code=data.get('iso_code', ''),
                name=data.get('name', ''),
                flag_emoji=data.get('flag_emoji'),
                description=data.get('description'),
                is_active=data.get('is_active', True),
                created_at=created_at
            ))
        
        return countries
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/countries/{iso_code}", response_model=CountryResponse)
async def get_country(iso_code: str):
    """Get country by ISO code"""
    try:
        db = get_firestore()
        countries_ref = db.collection('countries')
        query = countries_ref.where('iso_code', '==', iso_code.upper()).limit(1)
        docs = list(query.stream())
        
        if not docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Country not found"
            )
        
        doc = docs[0]
        data = doc.to_dict()
        created_at = data.get('created_at')
        if hasattr(created_at, 'timestamp'):
            created_at = datetime.fromtimestamp(created_at.timestamp())
        elif isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        elif created_at is None:
            created_at = datetime.utcnow()
        
        return CountryResponse(
            id=doc.id,
            iso_code=data.get('iso_code', ''),
            name=data.get('name', ''),
            flag_emoji=data.get('flag_emoji'),
            description=data.get('description'),
            is_active=data.get('is_active', True),
            created_at=created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/countries/{iso_code}/subscribe")
async def subscribe_to_country(iso_code: str, token_data: TokenDep):
    """Subscribe to a country"""
    try:
        db = get_firestore()
        
        # Get country
        countries_ref = db.collection('countries')
        country_query = countries_ref.where('iso_code', '==', iso_code.upper()).limit(1)
        country_docs = list(country_query.stream())
        
        if not country_docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Country not found"
            )
        
        country_id = country_docs[0].id
        
        # Check if already subscribed
        subscriptions_ref = db.collection('country_subscriptions')
        existing_query = subscriptions_ref.where('user_id', '==', token_data.user_id)\
                                          .where('country_id', '==', country_id)\
                                          .limit(1)
        existing_docs = list(existing_query.stream())
        
        if existing_docs:
            return {"message": "Already subscribed", "subscribed": True}
        
        # Create subscription
        subscription_data = {
            "user_id": token_data.user_id,
            "country_id": country_id,
            "subscribed_at": SERVER_TIMESTAMP,
        }
        subscriptions_ref.add(subscription_data)
        
        return {"message": "Subscribed successfully", "subscribed": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/countries/{iso_code}/subscribe")
async def unsubscribe_from_country(iso_code: str, token_data: TokenDep):
    """Unsubscribe from a country"""
    try:
        db = get_firestore()
        
        # Get country
        countries_ref = db.collection('countries')
        country_query = countries_ref.where('iso_code', '==', iso_code.upper()).limit(1)
        country_docs = list(country_query.stream())
        
        if not country_docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Country not found"
            )
        
        country_id = country_docs[0].id
        
        # Find and delete subscription
        subscriptions_ref = db.collection('country_subscriptions')
        subscription_query = subscriptions_ref.where('user_id', '==', token_data.user_id)\
                                               .where('country_id', '==', country_id)\
                                               .limit(1)
        subscription_docs = list(subscription_query.stream())
        
        if not subscription_docs:
            return {"message": "Not subscribed", "subscribed": False}
        
        subscriptions_ref.document(subscription_docs[0].id).delete()
        
        return {"message": "Unsubscribed successfully", "subscribed": False}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== POSTS ====================

@router.post("/countries/{iso_code}/posts", status_code=status.HTTP_201_CREATED)
async def create_post(
    iso_code: str, post_data: PostCreate, token_data: TokenDep
):
    """Create a new post in a country"""
    try:
        db = get_firestore()
        
        # Get country
        countries_ref = db.collection('countries')
        country_query = countries_ref.where('iso_code', '==', iso_code.upper()).limit(1)
        country_docs = list(country_query.stream())
        
        if not country_docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Country not found"
            )
        
        country_doc = country_docs[0]
        country_id = country_doc.id
        country_name = country_doc.to_dict().get('name', 'Unknown')
        
        # Create post
        posts_ref = db.collection('reddit_posts')
        now = datetime.utcnow().isoformat()
        
        post_data_dict = {
            "country_id": country_id,
            "user_id": token_data.user_id,
            "title": post_data.title,
            "content": post_data.content,
            "media_urls": post_data.media_urls or {},
            "score": 0,
            "comment_count": 0,
            "is_pinned": False,
            "is_hidden": False,
            "created_at": now,
            "updated_at": now,
        }
        
        post_ref = posts_ref.add(post_data_dict)[1]
        post_id = post_ref.id
        
        # Get username
        username = _get_username_from_user_id(db, token_data.user_id)
        
        return PostResponse(
            id=post_id,
            country_id=country_id,
            country_name=country_name,
            user_id=token_data.user_id,
            username=username,
            title=post_data.title,
            content=post_data.content,
            media_urls=post_data.media_urls,
            score=0,
            comment_count=0,
            is_pinned=False,
            is_hidden=False,
            user_vote=None,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/countries/{iso_code}/posts", response_model=List[PostResponse])
async def get_posts(
    iso_code: str,
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    sort: str = Query("hot", pattern="^(hot|new|top)$"),
):
    """Get posts for a country"""
    try:
        token_data = _get_current_user_optional(request)
        db = get_firestore()
        
        # Get country
        countries_ref = db.collection('countries')
        country_query = countries_ref.where('iso_code', '==', iso_code.upper()).limit(1)
        country_docs = list(country_query.stream())
        
        if not country_docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Country not found"
            )
        
        country_id = country_docs[0].id
        country_name = country_docs[0].to_dict().get('name', 'Unknown')
        
        # Query posts - ONLY filter by country_id to avoid composite index requirement
        posts_ref = db.collection('reddit_posts')
        query = posts_ref.where('country_id', '==', country_id)
        
        # Fetch all posts for this country
        all_docs = list(query.stream())
        
        # Filter is_hidden == False in Python
        visible_posts = [doc for doc in all_docs if not doc.to_dict().get('is_hidden', False)]
        
        # Sort in Python based on sort parameter
        if sort == "new":
            # Sort by created_at descending
            visible_posts.sort(
                key=lambda x: x.to_dict().get('created_at', datetime.min),
                reverse=True
            )
        elif sort == "top":
            # Sort by score descending, then created_at descending
            visible_posts.sort(
                key=lambda x: (
                    x.to_dict().get('score', 0),
                    x.to_dict().get('created_at', datetime.min)
                ),
                reverse=True
            )
        else:  # hot
            # Sort by score descending, then created_at descending (same as top for now)
            visible_posts.sort(
                key=lambda x: (
                    x.to_dict().get('score', 0),
                    x.to_dict().get('created_at', datetime.min)
                ),
                reverse=True
            )
        
        # Apply pagination in Python
        posts_docs = visible_posts[skip:skip+limit]
        
        # Get user votes if authenticated
        user_votes = {}
        if token_data:
            votes_ref = db.collection('reddit_votes')
            post_ids = [doc.id for doc in posts_docs]
            for post_id in post_ids:
                vote_query = votes_ref.where('user_id', '==', token_data.user_id)\
                                      .where('post_id', '==', post_id)\
                                      .where('comment_id', '==', None)\
                                      .limit(1)
                vote_docs = list(vote_query.stream())
                if vote_docs:
                    user_votes[post_id] = vote_docs[0].to_dict().get('vote_type', 0)
        
        # Get usernames
        user_ids = list(set([doc.to_dict().get('user_id') for doc in posts_docs]))
        username_map = _get_usernames_batch(db, user_ids)
        
        # Build response
        posts = []
        for doc in posts_docs:
            data = doc.to_dict()
            created_at = data.get('created_at')
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            elif hasattr(created_at, 'timestamp'):
                created_at = datetime.fromtimestamp(created_at.timestamp())
            else:
                created_at = datetime.utcnow()
            
            updated_at = data.get('updated_at')
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            elif hasattr(updated_at, 'timestamp'):
                updated_at = datetime.fromtimestamp(updated_at.timestamp())
            else:
                updated_at = created_at
            
            posts.append(PostResponse(
                id=doc.id,
                country_id=country_id,
                country_name=country_name,
                user_id=data.get('user_id', ''),
                username=username_map.get(data.get('user_id', ''), 'Unknown'),
                title=data.get('title', ''),
                content=data.get('content', ''),
                media_urls=data.get('media_urls'),
                score=data.get('score', 0),
                comment_count=data.get('comment_count', 0),
                is_pinned=data.get('is_pinned', False),
                is_hidden=data.get('is_hidden', False),
                user_vote=user_votes.get(doc.id),
                created_at=created_at,
                updated_at=updated_at
            ))
        
        return posts
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/posts/{post_id}", response_model=PostResponse)
async def get_post(post_id: str, request: Request):
    """Get a single post by ID"""
    try:
        token_data = _get_current_user_optional(request)
        db = get_firestore()
        
        post_ref = db.collection('reddit_posts').document(post_id)
        post_doc = post_ref.get()
        
        if not post_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        post_data = post_doc.to_dict()
        country_id = post_data.get('country_id')
        
        # Get country
        country_ref = db.collection('countries').document(country_id)
        country_doc = country_ref.get()
        country_name = country_doc.to_dict().get('name', 'Unknown') if country_doc.exists else "Unknown"
        
        # Get user vote
        user_vote = None
        if token_data:
            votes_ref = db.collection('reddit_votes')
            vote_query = votes_ref.where('user_id', '==', token_data.user_id)\
                                  .where('post_id', '==', post_id)\
                                  .where('comment_id', '==', None)\
                                  .limit(1)
            vote_docs = list(vote_query.stream())
            if vote_docs:
                user_vote = vote_docs[0].to_dict().get('vote_type')
        
        # Get username
        username = _get_username_from_user_id(db, post_data.get('user_id', ''))
        
        created_at = post_data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        elif hasattr(created_at, 'timestamp'):
            created_at = datetime.fromtimestamp(created_at.timestamp())
        else:
            created_at = datetime.utcnow()
        
        updated_at = post_data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        elif hasattr(updated_at, 'timestamp'):
            updated_at = datetime.fromtimestamp(updated_at.timestamp())
        else:
            updated_at = created_at
        
        return PostResponse(
            id=post_id,
            country_id=country_id,
            country_name=country_name,
            user_id=post_data.get('user_id', ''),
            username=username,
            title=post_data.get('title', ''),
            content=post_data.get('content', ''),
            media_urls=post_data.get('media_urls'),
            score=post_data.get('score', 0),
            comment_count=post_data.get('comment_count', 0),
            is_pinned=post_data.get('is_pinned', False),
            is_hidden=post_data.get('is_hidden', False),
            user_vote=user_vote,
            created_at=created_at,
            updated_at=updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== COMMENTS ====================

@router.post("/posts/{post_id}/comments", status_code=status.HTTP_201_CREATED)
async def create_comment(post_id: str, comment_data: CommentCreate, token_data: TokenDep):
    """Create a comment on a post"""
    try:
        db = get_firestore()
        
        # Verify post exists
        post_ref = db.collection('reddit_posts').document(post_id)
        post_doc = post_ref.get()
        
        if not post_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        # Calculate depth and path
        depth = 0
        path = str(uuid.uuid4())
        if comment_data.parent_id:
            parent_ref = db.collection('reddit_comments').document(comment_data.parent_id)
            parent_doc = parent_ref.get()
            if parent_doc.exists:
                parent_data = parent_doc.to_dict()
                depth = parent_data.get('depth', 0) + 1
                parent_path = parent_data.get('path', '')
                path = f"{parent_path}/{uuid.uuid4()}" if parent_path else str(uuid.uuid4())
        
        # Create comment
        comments_ref = db.collection('reddit_comments')
        now = datetime.utcnow().isoformat()
        
        comment_data_dict = {
            "post_id": post_id,
            "parent_id": comment_data.parent_id,
            "user_id": token_data.user_id,
            "content": comment_data.content,
            "depth": depth,
            "path": path,
            "score": 0,
            "is_hidden": False,
            "created_at": now,
            "updated_at": now,
        }
        
        comment_ref = comments_ref.add(comment_data_dict)[1]
        comment_id = comment_ref.id
        
        # Update post comment count
        post_data = post_doc.to_dict()
        post_ref.update({
            "comment_count": post_data.get('comment_count', 0) + 1,
            "updated_at": now
        })
        
        # Get username
        username = _get_username_from_user_id(db, token_data.user_id)
        
        return CommentResponse(
            id=comment_id,
            post_id=post_id,
            parent_id=comment_data.parent_id,
            user_id=token_data.user_id,
            username=username,
            content=comment_data.content,
            score=0,
            is_hidden=False,
            depth=depth,
            user_vote=None,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/posts/{post_id}/comments", response_model=List[CommentResponse])
async def get_comments(post_id: str, request: Request):
    """Get comments for a post (nested structure)"""
    try:
        token_data = _get_current_user_optional(request)
        db = get_firestore()
        
        # Verify post exists
        post_ref = db.collection('reddit_posts').document(post_id)
        if not post_ref.get().exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        # Get comments - ONLY filter by post_id to avoid composite index requirement
        comments_ref = db.collection('reddit_comments')
        query = comments_ref.where('post_id', '==', post_id)
        
        all_comment_docs = list(query.stream())
        
        # Filter is_hidden == False in Python
        visible_comments = [doc for doc in all_comment_docs if not doc.to_dict().get('is_hidden', False)]
        
        # Sort by path and created_at in Python
        visible_comments.sort(
            key=lambda x: (
                x.to_dict().get('path', ''),
                x.to_dict().get('created_at', datetime.min)
            )
        )
        
        comment_docs = visible_comments
        
        # Get user votes if authenticated
        user_votes = {}
        if token_data:
            votes_ref = db.collection('reddit_votes')
            comment_ids = [doc.id for doc in comment_docs]
            for comment_id in comment_ids:
                vote_query = votes_ref.where('user_id', '==', token_data.user_id)\
                                      .where('comment_id', '==', comment_id)\
                                      .where('post_id', '==', None)\
                                      .limit(1)
                vote_docs = list(vote_query.stream())
                if vote_docs:
                    user_votes[comment_id] = vote_docs[0].to_dict().get('vote_type', 0)
        
        # Get usernames
        user_ids = list(set([doc.to_dict().get('user_id') for doc in comment_docs]))
        username_map = _get_usernames_batch(db, user_ids)
        
        # Build response
        comments = []
        for doc in comment_docs:
            data = doc.to_dict()
            created_at = data.get('created_at')
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            elif hasattr(created_at, 'timestamp'):
                created_at = datetime.fromtimestamp(created_at.timestamp())
            else:
                created_at = datetime.utcnow()
            
            updated_at = data.get('updated_at')
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            elif hasattr(updated_at, 'timestamp'):
                updated_at = datetime.fromtimestamp(updated_at.timestamp())
            else:
                updated_at = created_at
            
            comments.append(CommentResponse(
                id=doc.id,
                post_id=post_id,
                parent_id=data.get('parent_id'),
                user_id=data.get('user_id', ''),
                username=username_map.get(data.get('user_id', ''), 'Unknown'),
                content=data.get('content', ''),
                score=data.get('score', 0),
                is_hidden=data.get('is_hidden', False),
                depth=data.get('depth', 0),
                user_vote=user_votes.get(doc.id),
                created_at=created_at,
                updated_at=updated_at
            ))
        
        return comments
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== VOTES ====================

@router.post("/posts/{post_id}/vote")
async def vote_on_post(post_id: str, vote_data: VoteRequest, token_data: TokenDep):
    """Vote on a post"""
    try:
        db = get_firestore()
        
        # Verify post exists
        post_ref = db.collection('reddit_posts').document(post_id)
        post_doc = post_ref.get()
        
        if not post_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        post_data = post_doc.to_dict()
        current_score = post_data.get('score', 0)
        
        # Check if vote exists
        votes_ref = db.collection('reddit_votes')
        vote_query = votes_ref.where('user_id', '==', token_data.user_id)\
                              .where('post_id', '==', post_id)\
                              .where('comment_id', '==', None)\
                              .limit(1)
        existing_votes = list(vote_query.stream())
        
        if existing_votes:
            # Update existing vote
            existing_vote_doc = existing_votes[0]
            existing_vote_data = existing_vote_doc.to_dict()
            old_vote_type = existing_vote_data.get('vote_type', 0)
            
            if old_vote_type == vote_data.vote_type:
                # Same vote - remove it
                new_score = current_score - old_vote_type
                votes_ref.document(existing_vote_doc.id).delete()
            else:
                # Different vote - update it
                new_score = current_score - old_vote_type + vote_data.vote_type
                votes_ref.document(existing_vote_doc.id).update({
                    'vote_type': vote_data.vote_type,
                    'updated_at': datetime.utcnow().isoformat()
                })
        else:
            # Create new vote
            new_score = current_score + vote_data.vote_type
            votes_ref.add({
                'user_id': token_data.user_id,
                'post_id': post_id,
                'comment_id': None,
                'vote_type': vote_data.vote_type,
                'created_at': datetime.utcnow().isoformat(),
            })
        
        # Update post score
        post_ref.update({
            'score': new_score,
            'updated_at': datetime.utcnow().isoformat()
        })
        
        return {"message": "Vote updated", "score": new_score}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/comments/{comment_id}/vote")
async def vote_on_comment(comment_id: str, vote_data: VoteRequest, token_data: TokenDep):
    """Vote on a comment"""
    try:
        db = get_firestore()
        
        # Verify comment exists
        comment_ref = db.collection('reddit_comments').document(comment_id)
        comment_doc = comment_ref.get()
        
        if not comment_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )
        
        comment_data = comment_doc.to_dict()
        current_score = comment_data.get('score', 0)
        
        # Check if vote exists
        votes_ref = db.collection('reddit_votes')
        vote_query = votes_ref.where('user_id', '==', token_data.user_id)\
                              .where('comment_id', '==', comment_id)\
                              .where('post_id', '==', None)\
                              .limit(1)
        existing_votes = list(vote_query.stream())
        
        if existing_votes:
            # Update existing vote
            existing_vote_doc = existing_votes[0]
            existing_vote_data = existing_vote_doc.to_dict()
            old_vote_type = existing_vote_data.get('vote_type', 0)
            
            if old_vote_type == vote_data.vote_type:
                # Same vote - remove it
                new_score = current_score - old_vote_type
                votes_ref.document(existing_vote_doc.id).delete()
            else:
                # Different vote - update it
                new_score = current_score - old_vote_type + vote_data.vote_type
                votes_ref.document(existing_vote_doc.id).update({
                    'vote_type': vote_data.vote_type,
                    'updated_at': datetime.utcnow().isoformat()
                })
        else:
            # Create new vote
            new_score = current_score + vote_data.vote_type
            votes_ref.add({
                'user_id': token_data.user_id,
                'comment_id': comment_id,
                'post_id': None,
                'vote_type': vote_data.vote_type,
                'created_at': datetime.utcnow().isoformat(),
            })
        
        # Update comment score
        comment_ref.update({
            'score': new_score,
            'updated_at': datetime.utcnow().isoformat()
        })
        
        return {"message": "Vote updated", "score": new_score}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/posts/{post_id}/vote")
async def remove_post_vote(post_id: str, token_data: TokenDep):
    """Remove vote on a post"""
    try:
        db = get_firestore()
        
        post_ref = db.collection('reddit_posts').document(post_id)
        post_doc = post_ref.get()
        
        if not post_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        post_data = post_doc.to_dict()
        current_score = post_data.get('score', 0)
        
        # Find and remove vote
        votes_ref = db.collection('reddit_votes')
        vote_query = votes_ref.where('user_id', '==', token_data.user_id)\
                              .where('post_id', '==', post_id)\
                              .where('comment_id', '==', None)\
                              .limit(1)
        vote_docs = list(vote_query.stream())
        
        if vote_docs:
            vote_data = vote_docs[0].to_dict()
            vote_type = vote_data.get('vote_type', 0)
            new_score = current_score - vote_type
            votes_ref.document(vote_docs[0].id).delete()
            
            post_ref.update({
                'score': new_score,
                'updated_at': datetime.utcnow().isoformat()
            })
        
        return {"message": "Vote removed", "score": post_data.get('score', 0)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/comments/{comment_id}/vote")
async def remove_comment_vote(comment_id: str, token_data: TokenDep):
    """Remove vote on a comment"""
    try:
        db = get_firestore()
        
        comment_ref = db.collection('reddit_comments').document(comment_id)
        comment_doc = comment_ref.get()
        
        if not comment_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )
        
        comment_data = comment_doc.to_dict()
        current_score = comment_data.get('score', 0)
        
        # Find and remove vote
        votes_ref = db.collection('reddit_votes')
        vote_query = votes_ref.where('user_id', '==', token_data.user_id)\
                              .where('comment_id', '==', comment_id)\
                              .where('post_id', '==', None)\
                              .limit(1)
        vote_docs = list(vote_query.stream())
        
        if vote_docs:
            vote_data = vote_docs[0].to_dict()
            vote_type = vote_data.get('vote_type', 0)
            new_score = current_score - vote_type
            votes_ref.document(vote_docs[0].id).delete()
            
            comment_ref.update({
                'score': new_score,
                'updated_at': datetime.utcnow().isoformat()
            })
        
        return {"message": "Vote removed", "score": comment_data.get('score', 0)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== REPORTS ====================

@router.post("/posts/{post_id}/report")
async def report_post(post_id: str, report_data: ReportRequest, token_data: TokenDep):
    """Report a post"""
    try:
        db = get_firestore()
        
        # Verify post exists
        post_ref = db.collection('reddit_posts').document(post_id)
        if not post_ref.get().exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        # Create report
        reports_ref = db.collection('reddit_reports')
        reports_ref.add({
            'reporter_id': token_data.user_id,
            'post_id': post_id,
            'comment_id': None,
            'reason': report_data.reason,
            'description': report_data.description,
            'created_at': datetime.utcnow().isoformat(),
        })
        
        return {"message": "Report submitted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/comments/{comment_id}/report")
async def report_comment(comment_id: str, report_data: ReportRequest, token_data: TokenDep):
    """Report a comment"""
    try:
        db = get_firestore()
        
        # Verify comment exists
        comment_ref = db.collection('reddit_comments').document(comment_id)
        if not comment_ref.get().exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )
        
        # Create report
        reports_ref = db.collection('reddit_reports')
        reports_ref.add({
            'reporter_id': token_data.user_id,
            'post_id': None,
            'comment_id': comment_id,
            'reason': report_data.reason,
            'description': report_data.description,
            'created_at': datetime.utcnow().isoformat(),
        })
        
        return {"message": "Report submitted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== USER ACTIVITY ====================

@router.get("/users/{user_id}/posts", response_model=List[PostResponse])
async def get_user_posts(
    user_id: str,
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get all posts by a specific user across all countries"""
    try:
        token_data = _get_current_user_optional(request)
        db = get_firestore()
        
        # Get posts - ONLY filter by user_id to avoid composite index requirement
        posts_ref = db.collection('reddit_posts')
        query = posts_ref.where('user_id', '==', user_id)
        
        all_docs = list(query.stream())
        
        # Filter is_hidden == False in Python
        visible_posts = [doc for doc in all_docs if not doc.to_dict().get('is_hidden', False)]
        
        # Sort by created_at descending in Python
        visible_posts.sort(
            key=lambda x: x.to_dict().get('created_at', datetime.min),
            reverse=True
        )
        
        # Apply pagination
        posts_docs = visible_posts[skip:skip+limit]
        
        # Get countries
        country_ids = list(set([doc.to_dict().get('country_id') for doc in posts_docs]))
        country_map = {}
        for country_id in country_ids:
            country_ref = db.collection('countries').document(country_id)
            country_doc = country_ref.get()
            if country_doc.exists:
                country_map[country_id] = country_doc.to_dict().get('name', 'Unknown')
            else:
                country_map[country_id] = "Unknown"
        
        # Get user votes if authenticated
        user_votes = {}
        if token_data:
            votes_ref = db.collection('reddit_votes')
            post_ids = [doc.id for doc in posts_docs]
            for post_id in post_ids:
                vote_query = votes_ref.where('user_id', '==', token_data.user_id)\
                                      .where('post_id', '==', post_id)\
                                      .where('comment_id', '==', None)\
                                      .limit(1)
                vote_docs = list(vote_query.stream())
                if vote_docs:
                    user_votes[post_id] = vote_docs[0].to_dict().get('vote_type', 0)
        
        # Get usernames
        user_ids = list(set([doc.to_dict().get('user_id') for doc in posts_docs]))
        username_map = _get_usernames_batch(db, user_ids)
        
        # Build response
        posts = []
        for doc in posts_docs:
            data = doc.to_dict()
            created_at = data.get('created_at')
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            elif hasattr(created_at, 'timestamp'):
                created_at = datetime.fromtimestamp(created_at.timestamp())
            else:
                created_at = datetime.utcnow()
            
            updated_at = data.get('updated_at')
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            elif hasattr(updated_at, 'timestamp'):
                updated_at = datetime.fromtimestamp(updated_at.timestamp())
            else:
                updated_at = created_at
            
            posts.append(PostResponse(
                id=doc.id,
                country_id=data.get('country_id', ''),
                country_name=country_map.get(data.get('country_id', ''), 'Unknown'),
                user_id=data.get('user_id', ''),
                username=username_map.get(data.get('user_id', ''), 'Unknown'),
                title=data.get('title', ''),
                content=data.get('content', ''),
                media_urls=data.get('media_urls'),
                score=data.get('score', 0),
                comment_count=data.get('comment_count', 0),
                is_pinned=data.get('is_pinned', False),
                is_hidden=data.get('is_hidden', False),
                user_vote=user_votes.get(doc.id),
                created_at=created_at,
                updated_at=updated_at
            ))
        
        return posts
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/users/{user_id}/comments", response_model=List[CommentResponse])
async def get_user_comments(
    user_id: str,
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get all comments by a specific user"""
    try:
        token_data = _get_current_user_optional(request)
        db = get_firestore()
        
        # Get comments - ONLY filter by user_id to avoid composite index requirement
        comments_ref = db.collection('reddit_comments')
        query = comments_ref.where('user_id', '==', user_id)
        
        all_docs = list(query.stream())
        
        # Filter is_hidden == False in Python
        visible_comments = [doc for doc in all_docs if not doc.to_dict().get('is_hidden', False)]
        
        # Sort by created_at descending in Python
        visible_comments.sort(
            key=lambda x: x.to_dict().get('created_at', datetime.min),
            reverse=True
        )
        
        # Apply pagination
        comment_docs = visible_comments[skip:skip+limit]
        
        # Get user votes if authenticated
        user_votes = {}
        if token_data:
            votes_ref = db.collection('reddit_votes')
            comment_ids = [doc.id for doc in comment_docs]
            for comment_id in comment_ids:
                vote_query = votes_ref.where('user_id', '==', token_data.user_id)\
                                      .where('comment_id', '==', comment_id)\
                                      .where('post_id', '==', None)\
                                      .limit(1)
                vote_docs = list(vote_query.stream())
                if vote_docs:
                    user_votes[comment_id] = vote_docs[0].to_dict().get('vote_type', 0)
        
        # Get usernames
        user_ids = list(set([doc.to_dict().get('user_id') for doc in comment_docs]))
        username_map = _get_usernames_batch(db, user_ids)
        
        # Build response
        comments = []
        for doc in comment_docs:
            data = doc.to_dict()
            created_at = data.get('created_at')
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            elif hasattr(created_at, 'timestamp'):
                created_at = datetime.fromtimestamp(created_at.timestamp())
            else:
                created_at = datetime.utcnow()
            
            updated_at = data.get('updated_at')
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            elif hasattr(updated_at, 'timestamp'):
                updated_at = datetime.fromtimestamp(updated_at.timestamp())
            else:
                updated_at = created_at
            
            comments.append(CommentResponse(
                id=doc.id,
                post_id=data.get('post_id', ''),
                parent_id=data.get('parent_id'),
                user_id=data.get('user_id', ''),
                username=username_map.get(data.get('user_id', ''), 'Unknown'),
                content=data.get('content', ''),
                score=data.get('score', 0),
                is_hidden=data.get('is_hidden', False),
                depth=data.get('depth', 0),
                user_vote=user_votes.get(doc.id),
                created_at=created_at,
                updated_at=updated_at
            ))
        
        return comments
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/users/me/posts", response_model=List[PostResponse])
async def get_my_posts(
    token_data: TokenDep,
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get all posts by the current authenticated user"""
    return await get_user_posts(token_data.user_id, request, skip, limit)


@router.get("/users/me/comments", response_model=List[CommentResponse])
async def get_my_comments(
    token_data: TokenDep,
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get all comments by the current authenticated user"""
    return await get_user_comments(token_data.user_id, request, skip, limit)
