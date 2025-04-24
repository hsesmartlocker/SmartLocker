from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from models import User, Request
from database import engine
from api.auth import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/")
def get_users(current_user: User = Depends(get_current_user)):
    with Session(engine) as session:
        users = session.exec(select(User)).all()
        return users


@router.get("/{user_id}")
def get_user_by_id(user_id: int, current_user: User = Depends(get_current_user)):
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user


@router.delete("/delete")
def delete_user(current_user: User = Depends(get_current_user)):
    with Session(engine) as session:
        active_requests = session.exec(
            select(Request).where(Request.user == current_user.id)
        ).all()
        if active_requests:
            raise HTTPException(
                status_code=400,
                detail="Невозможно удалить аккаунт — у вас есть активные заявки.",
            )

        user = session.get(User, current_user.id)
        if user:
            session.delete(user)
            session.commit()
        return {"message": "Аккаунт удален"}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "type": current_user.type,
        "active": current_user.active,
        "created": current_user.created.isoformat() if current_user.created else None
    }
