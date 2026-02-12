from re import U
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator
from decimal import Decimal
from typing import List
from src.user.models import UserRoles
from utils.schemas.base import BaseSchema
from enum import Enum
from datetime import datetime


########################################################
# Restaurant Schemas
########################################################


class Restaurant(BaseModel):
    upi_merchant_name: str
    upi_id: str
    restaurant_address: Optional[str] = None
    restaurant_phone: Optional[str] = None
    restaurant_email: Optional[str] = None
    logo_url: Optional[str] = None


########################################################
# User Schemas
########################################################


class UserUpdate(BaseModel):
    firstname: Optional[str] = None
    lastname: Optional[str] = None

    email: Optional[str] = None
    phone_number_country_code: Optional[str] = None
    phone_number: Optional[str] = None


class SignupRequest(BaseModel):
    """Signup payload; required fields only (no override of UserUpdate optional fields)."""

    firstname: str
    lastname: str
    email: str
    password: str


class UserResponse(UserUpdate):
    email_verified: Optional[bool] = False
    phone_number_verified: Optional[bool] = False

    role: str = UserRoles.USER.value
    is_active: bool = True
    is_banned: bool = False

    # model config for orm models
    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseSchema, UserResponse):
    id: Optional[str]
    updated_by: Optional[str]
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    user: UserResponse
    token: str


########################################################
# Table Schemas
########################################################


class Table(BaseModel):
    table_id: str = str(uuid.uuid4())
    table_no: int


########################################################
# Category Schemas
########################################################


class Category(BaseModel):
    category_id: str = str(uuid.uuid4())
    category_name: str


# class category(BaseModel):
#     category_id: str = uuid.uuid4()
#     category_name: str


########################################################
# Menu Item Schemas
########################################################


class MenuItemBase(BaseModel):
    item_id: str = str(uuid.uuid4())
    item_name: str
    price: Decimal
    category: Category
    # category_name: List[Category]


# Request/API shape: frontend sends item_list with category_id/category_name, and category_name list
class MenuItemIn(BaseModel):
    item_name: str = ""
    price: Optional[float] = 0
    category_id: Optional[str] = ""
    category_name: Optional[str] = ""


class MenuCreate(BaseModel):
    """Payload for creating a menu. Matches frontend and DB (item_list/category_name as lists)."""
    item_list: List[MenuItemIn] = []
    price: Optional[float] = 0
    quantity: str = ""
    category_name: List[dict] = []  # list of { category_id, category_name } from frontend


class Menu(BaseModel):
    """Response and update shape. item_list and category_name stored as JSON in DB."""
    menu_id: str = str(uuid.uuid4())
    item_list: List[dict] = []  # list of item dicts from DB
    price: Optional[float] = 0
    quantity: str = ""
    category_name: List[dict] = []  # list of category dicts from DB


########################################################
# Order Schemas
########################################################


class OrderStatus(str, Enum):
    PENDING = "pending"  # Order received
    PREPARING = "preparing"  # Order sent to kitchen, being prepared
    READY = "ready"  # Order ready
    CANCELLED = "cancelled"  # Order cancelled


class Order(BaseModel):
    """Line-item order (table_id, order_items, order_quantity, order_notes)."""

    table_id: Table
    order_id: str = uuid.uuid4()
    item_list: list[MenuItemBase]
    order_quantity: int
    order_notes: Optional[str] = None


class OrderCreate(BaseModel):
    """Payload for creating an order. Maps to DB: item_list (JSON), quantity, table_no."""

    item_list: str  # JSON string of order items
    quantity: int
    table_no: str


class OrderUpdate(BaseModel):
    """Payload for updating an order. Maps to DB: item_list (JSON), quantity, table_no."""

    item_list: str  # JSON string of order items
    quantity: int
    table_no: str


class OrderResponse(BaseModel):
    """Response for GET /get_orders and GET /get_order_by_id. Matches model fields."""

    order_id: str
    item_list: str  # JSON string from DB
    order_status: OrderStatus
    table_id: str  # table_no as string


# class kitchen_view(BaseModel):
#     order_id: Order
#     item_list: list[Order]
#     order_status: OrderStatus
#     table_id: Table


class OrderStatusResponse(BaseModel):
    """Response for order status APIs. order_id + status from order_status table."""

    order_id: str
    status: str


class OrderStatusUpdate(BaseModel):
    order_id: Optional[str] = None  # optional when provided in path
    status: OrderStatus


########################################################
# Stock Schemas
########################################################


class StockCreate(BaseModel):
    name: str
    quantity: float = 0
    unit_of_measure: str = "unit"
    cost_per_unit: Optional[float] = 0


class StockBase(BaseModel):
    name: str
    quantity: float = 0
    unit_of_measure: str = "unit"
    cost_per_unit: Optional[float] = 0


# class StockCreate(StockBase):
#     pass


class StockUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[float] = None
    unit_of_measure: Optional[str] = None
    cost_per_unit: Optional[float] = None


class Stock(StockBase):
    id: str = uuid.uuid4()
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


########################################################
# Invoice Schemas
########################################################


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"


class Invoice(BaseModel):
    invoice_id: str = str(uuid.uuid4())
    order_id: str
    invoice_number: str
    invoice_date: datetime
    total_amount: float
    gst_percent: float = 0.0
    discount_percent: float = 0.0
    payment_status: PaymentStatus
    notes: Optional[str] = None
    customer_name: str = ""


class InvoiceCreate(BaseModel):
    model_config = ConfigDict(
        extra="ignore"
    )  # ignore extra fields so client typos don't cause 422

    order_id: str
    invoice_number: str
    invoice_date: datetime
    total_amount: Optional[float] = None  # auto-computed from order items + GST - discount if not provided
    gst_percent: float = 0.0
    discount_percent: float = 0.0
    payment_status: PaymentStatus = PaymentStatus.PENDING
    notes: Optional[str] = None
    customer_name: str = ""

    @field_validator("invoice_date", mode="before")
    @classmethod
    def coerce_invoice_date(cls, v):
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return datetime.now()
            # Accept date-only "YYYY-MM-DD" from frontend
            if len(s) == 10 and s[4] == "-" and s[7] == "-":
                return datetime.strptime(s, "%Y-%m-%d")
            try:
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            except ValueError:
                pass
        return v

    @field_validator("payment_status", mode="before")
    @classmethod
    def coerce_payment_status(cls, v):
        if isinstance(v, PaymentStatus):
            return v
        if isinstance(v, str):
            s = v.strip().lower()
            if s in ("pending", "paid", "cancelled"):
                return PaymentStatus(s)
        return v


class InvoiceCreateForTable(BaseModel):
    """Create a single merged invoice for all orders of a table."""
    table_no: int
    invoice_number: Optional[str] = None  # auto-generated if not provided
    invoice_date: Optional[datetime] = None
    gst_percent: float = 0.0
    discount_percent: float = 0.0
    payment_status: PaymentStatus = PaymentStatus.PENDING
    notes: Optional[str] = None
    customer_name: str = ""

    @field_validator("invoice_date", mode="before")
    @classmethod
    def coerce_invoice_date(cls, v):
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return None
            if len(s) == 10 and s[4] == "-" and s[7] == "-":
                return datetime.strptime(s, "%Y-%m-%d")
            try:
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            except ValueError:
                pass
        return v


class InvoiceUpdate(BaseModel):
    order_id: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[datetime] = None
    total_amount: Optional[float] = None
    gst_percent: Optional[float] = None
    discount_percent: Optional[float] = None
    payment_status: Optional[PaymentStatus] = None
    notes: Optional[str] = None
    customer_name: str = ""


class InvoiceResponse(BaseModel):
    invoice_id: str
    order_id: str
    invoice_number: str
    invoice_date: datetime
    total_amount: float
    gst_percent: float = 0.0
    discount_percent: float = 0.0
    payment_status: PaymentStatus
    notes: Optional[str] = None
    customer_name: str = ""


class PaymentStatusUpdate(BaseModel):
    payment_status: Optional[PaymentStatus] = None


class PaymentStatusResponse(BaseModel):
    payment_status_id: str
    payment_status: PaymentStatus


########################################################
# Payment Schemas
########################################################
class PaymentCreate(BaseModel):
    restaurant_name: str
    invoice_id: Optional[str] = None  # if set, order_id and amount are taken from this invoice
    order_id: Optional[str] = None
    amount: Optional[float] = None
    payment_status: PaymentStatus = PaymentStatus.PENDING
    upi_ref_id: Optional[str] = None
    retry_count: int = 0


class PaymentResponse(BaseModel):
    payment_id: str
    order_id: str
    amount: float
    payment_status: PaymentStatus
    upi_ref_id: Optional[str] = None
    retry_count: int = 0
    qr_image_url: Optional[str] = (
        None  # Direct URL to GET QR image (e.g. for <img src="">)
    )


class QRCode(BaseModel):
    qr_code_id: str
    payment_id: str
    qr_data: str = Field(
        ...,
        description="Full UPI payment URI (e.g. upi://pay?pa=...&am=...). Use this string as-is when generating the QR image; do not prepend your server URL (127.0.0.1:8000).",
    )
    is_active: bool
    qr_image_url: Optional[str] = (
        None  # Direct URL to GET QR image (e.g. for <img src="">)
    )

    class Config:
        from_attributes = True


class PaymentReviveResponse(BaseModel):
    payment_id: str
    new_qr: QRCode
    retry_count: int


class PaymentWebhook(BaseModel):
    """Payload for payment success webhook. Send payment_id or order_id; when status=paid we update DB."""

    payment_id: Optional[str] = None
    order_id: Optional[str] = None
    status: PaymentStatus
    upi_ref_id: Optional[str] = None


class PaymentMarkPaid(BaseModel):
    """Optional body when marking a payment as successful (e.g. UPI transaction ref)."""

    upi_ref_id: Optional[str] = None


class PaymentUpdate(BaseModel):
    payment_status: PaymentStatus
    upi_ref_id: Optional[str] = None
    retry_count: int = 0
