from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from models import User
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
