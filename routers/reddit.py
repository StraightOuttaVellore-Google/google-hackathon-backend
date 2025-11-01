from fastapi import APIRouter, Depends, status, HTTPException, Query, Security, Request
from sqlmodel import select, func, or_
from datetime import datetime
from typing import List, Optional
import uuid
from db import SessionDep
from model import (
    Country, RedditPost, RedditComment, RedditVote, CountrySubscription,
    RedditCountryRole, RedditReport, CountryRole,
    CountryCreate, CountryResponse, PostCreate, PostResponse,
    CommentCreate, CommentResponse, VoteRequest, ReportRequest,
    Users, TokenData
)
from utils import TokenDep, oauth2_scheme

router = APIRouter(prefix="/reddit", tags=["Reddit"])


# ==================== COUNTRIES ====================

@router.get("/countries", response_model=List[CountryResponse])
async def get_countries(session: SessionDep):
    """Get all active countries"""
    try:
        countries = session.exec(
            select(Country).where(Country.is_active == True).order_by(Country.name)
        ).all()
        return [
            CountryResponse(
                id=str(c.id),
                iso_code=c.iso_code,
                name=c.name,
                flag_emoji=c.flag_emoji,
                description=c.description,
                is_active=c.is_active,
                created_at=c.created_at
            )
            for c in countries
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/countries/{iso_code}", response_model=CountryResponse)
async def get_country(iso_code: str, session: SessionDep):
    """Get country by ISO code"""
    try:
        country = session.exec(
            select(Country).where(Country.iso_code == iso_code.upper())
        ).first()
        if not country:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Country not found"
            )
        return CountryResponse(
            id=str(country.id),
            iso_code=country.iso_code,
            name=country.name,
            flag_emoji=country.flag_emoji,
            description=country.description,
            is_active=country.is_active,
            created_at=country.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/countries/{iso_code}/subscribe")
async def subscribe_to_country(
    iso_code: str, token_data: TokenDep, session: SessionDep
):
    """Subscribe to a country"""
    try:
        country = session.exec(
            select(Country).where(Country.iso_code == iso_code.upper())
        ).first()
        if not country:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Country not found"
            )
        
        # Check if already subscribed
        existing = session.exec(
            select(CountrySubscription).where(
                CountrySubscription.user_id == uuid.UUID(token_data.user_id),
                CountrySubscription.country_id == country.id
            )
        ).first()
        
        if existing:
            return {"message": "Already subscribed", "subscribed": True}
        
        subscription = CountrySubscription(
            user_id=uuid.UUID(token_data.user_id),
            country_id=country.id
        )
        session.add(subscription)
        session.commit()
        return {"message": "Subscribed successfully", "subscribed": True}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/countries/{iso_code}/subscribe")
async def unsubscribe_from_country(
    iso_code: str, token_data: TokenDep, session: SessionDep
):
    """Unsubscribe from a country"""
    try:
        country = session.exec(
            select(Country).where(Country.iso_code == iso_code.upper())
        ).first()
        if not country:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Country not found"
            )
        
        subscription = session.exec(
            select(CountrySubscription).where(
                CountrySubscription.user_id == uuid.UUID(token_data.user_id),
                CountrySubscription.country_id == country.id
            )
        ).first()
        
        if not subscription:
            return {"message": "Not subscribed", "subscribed": False}
        
        session.delete(subscription)
        session.commit()
        return {"message": "Unsubscribed successfully", "subscribed": False}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== POSTS ====================

@router.post("/countries/{iso_code}/posts", status_code=status.HTTP_201_CREATED)
async def create_post(
    iso_code: str, post_data: PostCreate, token_data: TokenDep, session: SessionDep
):
    """Create a new post in a country"""
    try:
        country = session.exec(
            select(Country).where(Country.iso_code == iso_code.upper())
        ).first()
        if not country:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Country not found"
            )
        
        post = RedditPost(
            country_id=country.id,
            user_id=uuid.UUID(token_data.user_id),
            title=post_data.title,
            content=post_data.content,
            media_urls=post_data.media_urls
        )
        session.add(post)
        session.commit()
        session.refresh(post)
        
        # Get username
        user = session.exec(
            select(Users).where(Users.user_id == uuid.UUID(token_data.user_id))
        ).first()
        
        return PostResponse(
            id=str(post.id),
            country_id=str(post.country_id),
            country_name=country.name,
            user_id=str(post.user_id),
            username=user.username if user else "Unknown",
            title=post.title,
            content=post.content,
            media_urls=post.media_urls,
            score=post.score,
            comment_count=post.comment_count,
            is_pinned=post.is_pinned,
            is_hidden=post.is_hidden,
            user_vote=None,
            created_at=post.created_at,
            updated_at=post.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


async def get_current_user_optional(
    request: Request,
    session: SessionDep
):
    """Optional authentication - returns TokenData if token is valid, None otherwise"""
    try:
        from utils import SECRET_KEY, ALGORITHM
        from model import TokenData
        import jwt
        from jwt.exceptions import InvalidTokenError
        
        # Extract token from Authorization header
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return None
        
        token = authorization.replace("Bearer ", "")
        
        # Verify and decode token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload is None:
            return None
        
        token_data = TokenData(
            user_id=payload["user_id"],
            username=payload["username"],
            type_of_customer=payload["type_of_customer"],
        )
        return token_data
    except (InvalidTokenError, KeyError, ValueError):
        return None
    except Exception:
        return None


@router.get("/countries/{iso_code}/posts", response_model=List[PostResponse])
async def get_posts(
    iso_code: str,
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    sort: str = Query("hot", regex="^(hot|new|top)$"),
    token_data: Optional[TokenData] = Depends(get_current_user_optional)
):
    """Get posts for a country"""
    try:
        country = session.exec(
            select(Country).where(Country.iso_code == iso_code.upper())
        ).first()
        if not country:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Country not found"
            )
        
        query = select(RedditPost).where(
            RedditPost.country_id == country.id,
            RedditPost.is_hidden == False
        )
        
        # Sort posts
        if sort == "new":
            query = query.order_by(RedditPost.created_at.desc())
        elif sort == "top":
            query = query.order_by(RedditPost.score.desc(), RedditPost.created_at.desc())
        else:  # hot (default) - simple time-weighted score
            query = query.order_by(
                func.abs(RedditPost.score).desc(),
                RedditPost.created_at.desc()
            )
        
        posts = session.exec(query.offset(skip).limit(limit)).all()
        
        # Get user votes if authenticated
        user_id = uuid.UUID(token_data.user_id) if token_data and hasattr(token_data, 'user_id') else None
        user_votes = {}
        if user_id:
            votes = session.exec(
                select(RedditVote).where(
                    RedditVote.user_id == user_id,
                    RedditVote.post_id.in_([p.id for p in posts]),
                    RedditVote.comment_id.is_(None)
                )
            ).all()
            user_votes = {str(v.post_id): v.vote_type for v in votes}
        
        # Get usernames
        user_ids = [p.user_id for p in posts]
        users = session.exec(
            select(Users).where(Users.user_id.in_(user_ids))
        ).all()
        username_map = {str(u.user_id): u.username for u in users}
        
        return [
            PostResponse(
                id=str(p.id),
                country_id=str(p.country_id),
                country_name=country.name,
                user_id=str(p.user_id),
                username=username_map.get(str(p.user_id), "Unknown"),
                title=p.title,
                content=p.content,
                media_urls=p.media_urls,
                score=p.score,
                comment_count=p.comment_count,
                is_pinned=p.is_pinned,
                is_hidden=p.is_hidden,
                user_vote=user_votes.get(str(p.id)),
                created_at=p.created_at,
                updated_at=p.updated_at
            )
            for p in posts
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/posts/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: str,
    session: SessionDep,
    token_data: Optional[TokenData] = Depends(get_current_user_optional)
):
    """Get a single post by ID"""
    try:
        post = session.exec(
            select(RedditPost).where(RedditPost.id == uuid.UUID(post_id))
        ).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        country = session.exec(
            select(Country).where(Country.id == post.country_id)
        ).first()
        
        user = session.exec(
            select(Users).where(Users.user_id == post.user_id)
        ).first()
        
        user_vote = None
        if token_data and hasattr(token_data, 'user_id'):
            vote = session.exec(
                select(RedditVote).where(
                    RedditVote.user_id == uuid.UUID(token_data.user_id),
                    RedditVote.post_id == post.id,
                    RedditVote.comment_id.is_(None)
                )
            ).first()
            if vote:
                user_vote = vote.vote_type
        
        return PostResponse(
            id=str(post.id),
            country_id=str(post.country_id),
            country_name=country.name if country else "Unknown",
            user_id=str(post.user_id),
            username=user.username if user else "Unknown",
            title=post.title,
            content=post.content,
            media_urls=post.media_urls,
            score=post.score,
            comment_count=post.comment_count,
            is_pinned=post.is_pinned,
            is_hidden=post.is_hidden,
            user_vote=user_vote,
            created_at=post.created_at,
            updated_at=post.updated_at
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
async def create_comment(
    post_id: str, comment_data: CommentCreate, token_data: TokenDep, session: SessionDep
):
    """Create a comment on a post"""
    try:
        post = session.exec(
            select(RedditPost).where(RedditPost.id == uuid.UUID(post_id))
        ).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        # Calculate depth and path
        depth = 0
        path = str(uuid.uuid4())
        if comment_data.parent_id:
            parent = session.exec(
                select(RedditComment).where(
                    RedditComment.id == uuid.UUID(comment_data.parent_id)
                )
            ).first()
            if parent:
                depth = parent.depth + 1
                path = f"{parent.path}/{uuid.uuid4()}" if parent.path else str(uuid.uuid4())
        
        comment = RedditComment(
            post_id=post.id,
            parent_id=uuid.UUID(comment_data.parent_id) if comment_data.parent_id else None,
            user_id=uuid.UUID(token_data.user_id),
            content=comment_data.content,
            depth=depth,
            path=path
        )
        session.add(comment)
        
        # Update post comment count
        post.comment_count += 1
        session.add(post)
        
        session.commit()
        session.refresh(comment)
        
        user = session.exec(
            select(Users).where(Users.user_id == uuid.UUID(token_data.user_id))
        ).first()
        
        return CommentResponse(
            id=str(comment.id),
            post_id=str(comment.post_id),
            parent_id=str(comment.parent_id) if comment.parent_id else None,
            user_id=str(comment.user_id),
            username=user.username if user else "Unknown",
            content=comment.content,
            score=comment.score,
            is_hidden=comment.is_hidden,
            depth=comment.depth,
            user_vote=None,
            created_at=comment.created_at,
            updated_at=comment.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/posts/{post_id}/comments", response_model=List[CommentResponse])
async def get_comments(
    post_id: str,
    session: SessionDep,
    token_data: Optional[TokenData] = Depends(get_current_user_optional)
):
    """Get comments for a post (nested structure)"""
    try:
        post = session.exec(
            select(RedditPost).where(RedditPost.id == uuid.UUID(post_id))
        ).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        comments = session.exec(
            select(RedditComment)
            .where(RedditComment.post_id == post.id, RedditComment.is_hidden == False)
            .order_by(RedditComment.path, RedditComment.created_at)
        ).all()
        
        # Get user votes if authenticated
        user_id = uuid.UUID(token_data.user_id) if token_data and hasattr(token_data, 'user_id') else None
        user_votes = {}
        if user_id:
            votes = session.exec(
                select(RedditVote).where(
                    RedditVote.user_id == user_id,
                    RedditVote.comment_id.in_([c.id for c in comments]),
                    RedditVote.post_id.is_(None)
                )
            ).all()
            user_votes = {str(v.comment_id): v.vote_type for v in votes}
        
        # Get usernames
        user_ids = [c.user_id for c in comments]
        users = session.exec(
            select(Users).where(Users.user_id.in_(user_ids))
        ).all()
        username_map = {str(u.user_id): u.username for u in users}
        
        return [
            CommentResponse(
                id=str(c.id),
                post_id=str(c.post_id),
                parent_id=str(c.parent_id) if c.parent_id else None,
                user_id=str(c.user_id),
                username=username_map.get(str(c.user_id), "Unknown"),
                content=c.content,
                score=c.score,
                is_hidden=c.is_hidden,
                depth=c.depth,
                user_vote=user_votes.get(str(c.id)),
                created_at=c.created_at,
                updated_at=c.updated_at
            )
            for c in comments
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== VOTES ====================

@router.post("/posts/{post_id}/vote")
async def vote_on_post(
    post_id: str, vote_data: VoteRequest, token_data: TokenDep, session: SessionDep
):
    """Vote on a post"""
    try:
        post = session.exec(
            select(RedditPost).where(RedditPost.id == uuid.UUID(post_id))
        ).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        user_id = uuid.UUID(token_data.user_id)
        
        # Check if vote exists
        existing_vote = session.exec(
            select(RedditVote).where(
                RedditVote.user_id == user_id,
                RedditVote.post_id == post.id,
                RedditVote.comment_id.is_(None)
            )
        ).first()
        
        if existing_vote:
            # Update existing vote
            if existing_vote.vote_type == vote_data.vote_type:
                # Same vote - remove it
                post.score -= existing_vote.vote_type
                session.delete(existing_vote)
            else:
                # Different vote - update it
                post.score -= existing_vote.vote_type
                post.score += vote_data.vote_type
                existing_vote.vote_type = vote_data.vote_type
                session.add(existing_vote)
        else:
            # Create new vote
            vote = RedditVote(
                user_id=user_id,
                post_id=post.id,
                vote_type=vote_data.vote_type
            )
            post.score += vote_data.vote_type
            session.add(vote)
        
        session.add(post)
        session.commit()
        
        return {"message": "Vote updated", "score": post.score}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/comments/{comment_id}/vote")
async def vote_on_comment(
    comment_id: str, vote_data: VoteRequest, token_data: TokenDep, session: SessionDep
):
    """Vote on a comment"""
    try:
        comment = session.exec(
            select(RedditComment).where(RedditComment.id == uuid.UUID(comment_id))
        ).first()
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )
        
        user_id = uuid.UUID(token_data.user_id)
        
        # Check if vote exists
        existing_vote = session.exec(
            select(RedditVote).where(
                RedditVote.user_id == user_id,
                RedditVote.comment_id == comment.id,
                RedditVote.post_id.is_(None)
            )
        ).first()
        
        if existing_vote:
            # Update existing vote
            if existing_vote.vote_type == vote_data.vote_type:
                # Same vote - remove it
                comment.score -= existing_vote.vote_type
                session.delete(existing_vote)
            else:
                # Different vote - update it
                comment.score -= existing_vote.vote_type
                comment.score += vote_data.vote_type
                existing_vote.vote_type = vote_data.vote_type
                session.add(existing_vote)
        else:
            # Create new vote
            vote = RedditVote(
                user_id=user_id,
                comment_id=comment.id,
                vote_type=vote_data.vote_type
            )
            comment.score += vote_data.vote_type
            session.add(vote)
        
        session.add(comment)
        session.commit()
        
        return {"message": "Vote updated", "score": comment.score}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/posts/{post_id}/vote")
async def remove_post_vote(post_id: str, token_data: TokenDep, session: SessionDep):
    """Remove vote on a post"""
    try:
        post = session.exec(
            select(RedditPost).where(RedditPost.id == uuid.UUID(post_id))
        ).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        vote = session.exec(
            select(RedditVote).where(
                RedditVote.user_id == uuid.UUID(token_data.user_id),
                RedditVote.post_id == post.id,
                RedditVote.comment_id.is_(None)
            )
        ).first()
        
        if vote:
            post.score -= vote.vote_type
            session.delete(vote)
            session.add(post)
            session.commit()
        
        return {"message": "Vote removed", "score": post.score}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/comments/{comment_id}/vote")
async def remove_comment_vote(
    comment_id: str, token_data: TokenDep, session: SessionDep
):
    """Remove vote on a comment"""
    try:
        comment = session.exec(
            select(RedditComment).where(RedditComment.id == uuid.UUID(comment_id))
        ).first()
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )
        
        vote = session.exec(
            select(RedditVote).where(
                RedditVote.user_id == uuid.UUID(token_data.user_id),
                RedditVote.comment_id == comment.id,
                RedditVote.post_id.is_(None)
            )
        ).first()
        
        if vote:
            comment.score -= vote.vote_type
            session.delete(vote)
            session.add(comment)
            session.commit()
        
        return {"message": "Vote removed", "score": comment.score}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== REPORTS ====================

@router.post("/posts/{post_id}/report")
async def report_post(
    post_id: str, report_data: ReportRequest, token_data: TokenDep, session: SessionDep
):
    """Report a post"""
    try:
        post = session.exec(
            select(RedditPost).where(RedditPost.id == uuid.UUID(post_id))
        ).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        report = RedditReport(
            reporter_id=uuid.UUID(token_data.user_id),
            post_id=post.id,
            reason=report_data.reason,
            description=report_data.description
        )
        session.add(report)
        session.commit()
        
        return {"message": "Report submitted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/comments/{comment_id}/report")
async def report_comment(
    comment_id: str, report_data: ReportRequest, token_data: TokenDep, session: SessionDep
):
    """Report a comment"""
    try:
        comment = session.exec(
            select(RedditComment).where(RedditComment.id == uuid.UUID(comment_id))
        ).first()
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )
        
        report = RedditReport(
            reporter_id=uuid.UUID(token_data.user_id),
            comment_id=comment.id,
            reason=report_data.reason,
            description=report_data.description
        )
        session.add(report)
        session.commit()
        
        return {"message": "Report submitted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== USER ACTIVITY ====================

@router.get("/users/{user_id}/posts", response_model=List[PostResponse])
async def get_user_posts(
    user_id: str,
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    token_data: Optional[TokenData] = Depends(get_current_user_optional)
):
    """Get all posts by a specific user across all countries"""
    try:
        query = select(RedditPost).where(
            RedditPost.user_id == uuid.UUID(user_id),
            RedditPost.is_hidden == False
        ).order_by(RedditPost.created_at.desc())
        
        posts = session.exec(query.offset(skip).limit(limit)).all()
        
        # Get countries for posts
        country_ids = [p.country_id for p in posts]
        countries = session.exec(
            select(Country).where(Country.id.in_(country_ids))
        ).all()
        country_map = {str(c.id): c.name for c in countries}
        
        # Get user votes if authenticated
        current_user_id = uuid.UUID(token_data.user_id) if token_data and hasattr(token_data, 'user_id') else None
        user_votes = {}
        if current_user_id:
            votes = session.exec(
                select(RedditVote).where(
                    RedditVote.user_id == current_user_id,
                    RedditVote.post_id.in_([p.id for p in posts]),
                    RedditVote.comment_id.is_(None)
                )
            ).all()
            user_votes = {str(v.post_id): v.vote_type for v in votes}
        
        # Get usernames
        post_user_ids = [p.user_id for p in posts]
        users = session.exec(
            select(Users).where(Users.user_id.in_(post_user_ids))
        ).all()
        username_map = {str(u.user_id): u.username for u in users}
        
        return [
            PostResponse(
                id=str(p.id),
                country_id=str(p.country_id),
                country_name=country_map.get(str(p.country_id), "Unknown"),
                user_id=str(p.user_id),
                username=username_map.get(str(p.user_id), "Unknown"),
                title=p.title,
                content=p.content,
                media_urls=p.media_urls,
                score=p.score,
                comment_count=p.comment_count,
                is_pinned=p.is_pinned,
                is_hidden=p.is_hidden,
                user_vote=user_votes.get(str(p.id)),
                created_at=p.created_at,
                updated_at=p.updated_at
            )
            for p in posts
        ]
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
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    token_data: Optional[TokenData] = Depends(get_current_user_optional)
):
    """Get all comments by a specific user"""
    try:
        query = select(RedditComment).where(
            RedditComment.user_id == uuid.UUID(user_id),
            RedditComment.is_hidden == False
        ).order_by(RedditComment.created_at.desc())
        
        comments = session.exec(query.offset(skip).limit(limit)).all()
        
        # Get user votes if authenticated
        current_user_id = uuid.UUID(token_data.user_id) if token_data and hasattr(token_data, 'user_id') else None
        user_votes = {}
        if current_user_id:
            votes = session.exec(
                select(RedditVote).where(
                    RedditVote.user_id == current_user_id,
                    RedditVote.comment_id.in_([c.id for c in comments]),
                    RedditVote.post_id.is_(None)
                )
            ).all()
            user_votes = {str(v.comment_id): v.vote_type for v in votes}
        
        # Get usernames
        comment_user_ids = [c.user_id for c in comments]
        users = session.exec(
            select(Users).where(Users.user_id.in_(comment_user_ids))
        ).all()
        username_map = {str(u.user_id): u.username for u in users}
        
        return [
            CommentResponse(
                id=str(c.id),
                post_id=str(c.post_id),
                parent_id=str(c.parent_id) if c.parent_id else None,
                user_id=str(c.user_id),
                username=username_map.get(str(c.user_id), "Unknown"),
                content=c.content,
                score=c.score,
                is_hidden=c.is_hidden,
                depth=c.depth,
                user_vote=user_votes.get(str(c.id)),
                created_at=c.created_at,
                updated_at=c.updated_at
            )
            for c in comments
        ]
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
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """Get all posts by the current authenticated user"""
    return await get_user_posts(token_data.user_id, session, skip, limit, token_data)


@router.get("/users/me/comments", response_model=List[CommentResponse])
async def get_my_comments(
    token_data: TokenDep,
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """Get all comments by the current authenticated user"""
    return await get_user_comments(token_data.user_id, session, skip, limit, token_data)

