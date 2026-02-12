from datetime import datetime, timedelta
from enum import Enum

import logging

import jwt
from passlib.context import CryptContext
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Float,
    Text,
    DateTime,
    Enum as SQLEnum,
)
from sqlalchemy.sql.sqltypes import Boolean

# Prefer Argon2 (matches existing DB $argon2id$ hashes); fallback to pbkdf2 if argon2 not installed
try:
    pwd_context = CryptContext(schemes=["argon2", "pbkdf2_sha256"], deprecated="auto")
except Exception:
    logging.warning("Argon2 not available; install with: pip install 'passlib[argon2]'")
    pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

from src.config import Config
from utils.db.base import ModelBase


class UserRoles(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


class AuthProvider(str, Enum):
    GOOGLE = "GOOGLE"
    FACEBOOK = "FACEBOOK"
    LINKEDIN = "LINKEDIN"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"


class User(ModelBase):
    firstname = Column(String, index=True)
    lastname = Column(String, index=True)
    image_url = Column(String, nullable=True)

    email = Column(String, unique=True)
    phone_number_country_code = Column(String)
    phone_number = Column(String, unique=True, nullable=True)

    email_verified = Column(Boolean, default=False)
    phone_number_verified = Column(Boolean, default=False)

    password = Column(String, nullable=False)

    role = Column(String, default=UserRoles.USER.value)
    is_active = Column(Boolean, default=True)
    is_banned = Column(Boolean, default=False)

    def __repr__(self):
        return f"""
            User INFO:
                ID: {self.id}
                Email: {self.email}
                role: {self.role}
                First Name: {self.firstname}
                Last Name: {self.lastname}
        """

    def set_password(self, password):
        """Hash a password for storing (Argon2id, matches existing DB hashes)."""
        self.password = pwd_context.hash(password)

    def verify_password(self, provided_password):
        """Verify a stored password against one provided by user."""
        if not self.password or not provided_password:
            return False
        return pwd_context.verify(provided_password, self.password)

    def create_token(self):
        return jwt.encode(
            {
                "id": self.id,
                "email": self.email,
                "role": self.role,
                "is_active": self.is_active,
                "is_banned": self.is_banned,
                "exp": (
                    datetime.utcnow()
                    + timedelta(seconds=int(Config.JWT_EXPIRATION_TIME))
                ).timestamp(),
            },
            key=Config.JWT_SECRET_KEY,
            algorithm=Config.JWT_ALGORITHM,
        )


class Restaurant(ModelBase):
    upi_merchant_name = Column(String, unique=True, index=True)
    upi_id = Column(String, unique=True, index=True)
    restaurant_address = Column(String, index=True)
    restaurant_phone = Column(String, index=True)
    restaurant_email = Column(String, index=True)
    logo_url = Column(String, nullable=True)

class Table(ModelBase):
    table_no = Column(Integer, index=True)


class Menu(ModelBase):
    menu_id = Column(String, index=True)
    item_list = Column(String, index=True)
    price = Column(Integer, index=True)
    quantity = Column(String, index=True)
    category_name = Column(String, index=True)
    category_id = Column(String, index=True)


class Category(ModelBase):
    category_id = Column(String, index=True)
    category_name = Column(String, index=True)


class MenuItem(ModelBase):
    item_name = Column(String, index=True)
    item_price = Column(Integer, index=True)
    # Link each menu item to a specific category
    category_id = Column(String, ForeignKey("category.id"))


class Order(ModelBase):
    item_list = Column(String, index=True)
    quantity = Column(Integer, index=True)
    order_pending = Column(String, default="false")
    order_done = Column(String, default="false")
    order_cancel = Column(String, default="false")
    table_no = Column(
        Integer, index=True
    )  # references table.table_no; no FK (table_no not unique)


class OrderStatus(ModelBase):
    order_id = Column(String, ForeignKey("order.id"))
    status = Column(String, index=True)


class Invoice(ModelBase):
    order_id = Column(
        String, ForeignKey("order.id", ondelete="RESTRICT"), nullable=False
    )
    order_ids = Column(Text, nullable=True)  # JSON array of order IDs when merging multiple orders for same table
    invoice_number = Column(String(50), unique=True, index=True, nullable=False)
    invoice_date = Column(DateTime, default=datetime.now, nullable=False)
    total_amount = Column(Float, nullable=False)
    gst_percent = Column(Float, default=0.0, nullable=False)
    discount_percent = Column(Float, default=0.0, nullable=False)
    payment_status = Column(
        SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False
    )
    notes = Column(Text, nullable=True)
    customer_name = Column(String(255), nullable=False)  # optional; shown in "INVOICE TO:" instead of table when set


class Stock(ModelBase):
    name = Column(String, index=True)
    quantity = Column(Float, index=True)
    unit_of_measure = Column(String, index=True)
    cost_per_unit = Column(Float, index=True)


class Payment(ModelBase):
    order_id = Column(
        String, ForeignKey("order.id", ondelete="RESTRICT"), nullable=False
    )
    amount = Column(Float, nullable=False)

    status = Column(
        SQLEnum(PaymentStatus),
        default=PaymentStatus.PENDING,
        nullable=False,
    )

    upi_ref_id = Column(String, nullable=True)
    retry_count = Column(Integer, default=0)


class QRCode(ModelBase):
    payment_id = Column(
        String,
        ForeignKey("payment.id", ondelete="CASCADE"),
        nullable=False,
    )
    qr_data = Column(String, nullable=False)  # UPI URI
    is_active = Column(Boolean, default=True)
