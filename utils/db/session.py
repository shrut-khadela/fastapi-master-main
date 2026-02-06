from typing import Annotated, Generator

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from src.config import Config

# Build database URL from config
SQLALCHEMY_DB_URL = Config.assemble_db_connection()

engine = create_engine(SQLALCHEMY_DB_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def _get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db

    except ProgrammingError as pe:
        print("###############################################")
        print("EITHER DATABASE NOT FOUND OR NO TABLES PRESENT")
        print("###############################################")
        return pe
    finally:
        db.close()


get_db = Annotated[Session, Depends(_get_db)]