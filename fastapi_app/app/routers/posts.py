from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastapi_app.app.db.session import get_db
from fastapi_app.app.models import Like, Post, User
from fastapi_app.app.routers.deps import get_current_user
from fastapi_app.app.schemas import PostCreate, PostPublic


router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("", response_model=list[PostPublic])
def list_posts(db: Session = Depends(get_db)):
    rows = db.execute(select(Post).order_by(Post.created_at.desc())).scalars().all()
    return [
        PostPublic(
            id=p.id,
            user_id=p.user_id,
            title=p.title,
            body=p.body,
            filename=p.filename,
            created_at=p.created_at,
        )
        for p in rows
    ]


@router.post("", response_model=PostPublic, status_code=status.HTTP_201_CREATED)
def create_post(
    payload: PostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = Post(
        user_id=current_user.id,
        title=payload.title,
        body=payload.body,
        filename=payload.filename,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return PostPublic(
        id=post.id,
        user_id=post.user_id,
        title=post.title,
        body=post.body,
        filename=post.filename,
        created_at=post.created_at,
    )


@router.get("/{post_id}", response_model=PostPublic)
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.execute(select(Post).where(Post.id == post_id)).scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return PostPublic(
        id=post.id,
        user_id=post.user_id,
        title=post.title,
        body=post.body,
        filename=post.filename,
        created_at=post.created_at,
    )


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.execute(select(Post).where(Post.id == post_id)).scalar_one_or_none()
    if post is None:
        return
    if post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    db.delete(post)
    db.commit()
    return


@router.post("/{post_id}/likes/toggle")
def toggle_like(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.execute(select(Post).where(Post.id == post_id)).scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    existing = db.execute(
        select(Like).where(Like.user_id == current_user.id, Like.post_id == post_id),
    ).scalar_one_or_none()

    if existing:
        db.delete(existing)
        liked = False
    else:
        db.add(Like(user_id=current_user.id, post_id=post_id))
        liked = True

    db.commit()

    like_count = db.execute(
        select(func.count()).select_from(Like).where(Like.post_id == post_id),
    ).scalar_one()
    return {"post_id": post_id, "liked": liked, "like_count": like_count}

