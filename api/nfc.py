# from fastapi import APIRouter, Depends, HTTPException
# from sqlmodel import Session, select
# from models import UserAccess, User
# from database import engine
# from api.auth import get_current_user
#
# router = APIRouter(prefix="/nfc", tags=["NFC"])
#
# @router.post("/unlock/{terminal_id}")
# def unlock_terminal(terminal_id: int, current_user: User = Depends(get_current_user)):
#     with Session(engine) as session:
#         # Получаем терминал
#         terminal = session.get(Terminal, terminal_id)
#         if not terminal:
#             raise HTTPException(status_code=404, detail="Терминал не найден")
#
#         # Проверка доступа терминала к комнате
#         terminal_accesses = session.exec(select(TerminalAccess).where(TerminalAccess.terminal == terminal_id)).all()
#         room_ids = [access.room for access in terminal_accesses]
#
#         # Проверка доступа пользователя к этим комнатам
#         access = session.exec(select(UserAccess).where(
#             UserAccess.user == current_user.id,
#             UserAccess.room.in_(room_ids)
#         )).first()
#
#         if not access:
#             raise HTTPException(status_code=403, detail="У вас нет доступа к этому терминалу")
#
#         return {
#             "message": "Доступ разрешён. Ячейка разблокирована.",
#             "terminal": terminal.name
#         }
