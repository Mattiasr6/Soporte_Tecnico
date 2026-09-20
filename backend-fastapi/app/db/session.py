from collections.abc import Iterator
from typing import Annotated

from app.db.base import SessionLocal
from fastapi import Depends
from sqlalchemy.orm import Session


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db)]
