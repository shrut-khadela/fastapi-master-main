from typing import Any, Dict, Union

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.user.models import User
from src.user.schemas import UserBase, UserUpdate
from utils.crud.base import CRUDBase


# user crud
class UserCRUD(CRUDBase[User, UserBase, UserUpdate]):
    def get_by_email(self, db: Session, email: str) -> User:
        if not email:
            return None
        return db.query(User).filter(func.lower(User.email) == email.strip().lower()).first()

    def create(self, db: Session, *, obj_in: UserBase) -> User:
        obj_in_data: dict = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, "model_dump") else jsonable_encoder(obj_in, exclude_unset=True)
        password = obj_in_data.pop("password", None)
        db_obj = self.model(**obj_in_data)
        if password is not None:
            db_obj.set_password(str(password).strip())
        db.add(db_obj)
        db.commit()
        return db_obj

    def update(
        self, db: Session, *, db_obj: User, obj_in: Union[UserUpdate, Dict[str, Any]]
    ) -> User:
        obj_data: dict = jsonable_encoder(db_obj, exclude_unset=True)
        password = obj_data.pop("password", None)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        if password:
            db_obj.set_password(password)
        db.add(db_obj)
        db.commit()
        return db_obj


user_crud = UserCRUD(User)
