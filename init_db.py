from sqlmodel import SQLModel
from database import engine
import models  # обязательно импортировать, чтобы SQLModel "видел" их

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

if __name__ == "__main__":
    create_db_and_tables()