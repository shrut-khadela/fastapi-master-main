import html
import json
import logging
import os
import uuid
from typing import List

import io

import qrcode
from fastapi import APIRouter, Body, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, Response
from src.config import Config
from sqlalchemy.orm import Session

from src.user.crud import user_crud
from src.user.models import (
    User as UserModel,
    Table as TableModel,
    Menu as MenuModel,
    Category as CategoryModel,
    Order as OrderModel,
    OrderStatus as OrderStatusModel,
    Stock as StockModel,
    Invoice as InvoiceModel,
    PaymentStatus as PaymentStatusModel,
    Payment as PaymentModel,
    QRCode as QRCodeModel,
    Restaurant as RestaurantModel,
)
from src.user.schemas import (
    LoginRequest,
    Table,
    Category,
    Token,
    UserBase,
    SignupRequest,
    UserResponse,
    UserUpdate,
    Menu,
    MenuCreate,
    OrderCreate,
    OrderResponse,
    OrderStatus,
    OrderStatusResponse,
    OrderStatusUpdate,
    OrderUpdate,
    StockCreate,
    Stock,
    StockUpdate,
    InvoiceCreate,
    InvoiceCreateForTable,
    Invoice,
    InvoiceUpdate,
    InvoiceResponse,
    PaymentStatus,
    PaymentCreate,
    PaymentMarkPaid,
    PaymentResponse,
    PaymentUpdate,
    QRCode,
    PaymentReviveResponse,
    PaymentWebhook,
    Restaurant,
)
from src.user.utils.deps import authenticated_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.expression import false
from utils.crud.base import CRUDBase
from utils.db.session import get_db

logger = logging.getLogger(__name__)

user_router = APIRouter()
table_router = APIRouter()
menu_router = APIRouter()
category_router = APIRouter()
order_router = APIRouter()
order_status_router = APIRouter()
stock_router = APIRouter()
invoice_router = APIRouter()
payment_status_router = APIRouter()
payment_router = APIRouter()
restaurant_router = APIRouter()

table_crud = CRUDBase[TableModel, Table, Table](TableModel)
menu_crud = CRUDBase[MenuModel, Menu, Menu](MenuModel)
category_crud = CRUDBase[CategoryModel, Category, Category](CategoryModel)
order_crud = CRUDBase[OrderModel, OrderCreate, OrderResponse](OrderModel)
order_status_crud = CRUDBase[OrderStatusModel, OrderStatusUpdate, OrderStatusResponse](
    OrderStatusModel
)
stock_crud = CRUDBase[StockModel, StockCreate, StockUpdate](StockModel)
invoice_crud = CRUDBase[InvoiceModel, InvoiceCreate, InvoiceUpdate](InvoiceModel)
payment_status_crud = CRUDBase[PaymentStatusModel, PaymentStatus, PaymentStatus](
    PaymentStatusModel
)
payment_crud = CRUDBase[PaymentModel, PaymentCreate, PaymentResponse](PaymentModel)
qr_code_crud = CRUDBase[QRCodeModel, QRCode, QRCode](QRCodeModel)


class RestaurantCRUD(CRUDBase[RestaurantModel, Restaurant, Restaurant]):
    def get_by_merchant_name(self, db: Session, name: str) -> RestaurantModel:
        return (
            db.query(RestaurantModel)
            .filter(RestaurantModel.upi_merchant_name == name)
            .first()
        )


restaurant_crud = RestaurantCRUD(RestaurantModel)

########################################################
# Restaurant APIs
########################################################


@restaurant_router.post(
    "/create_restaurant", response_model=Restaurant, status_code=status.HTTP_201_CREATED
)
def create_restaurant(restaurant_data: Restaurant, db: get_db):
    restaurant_crud.create(db, obj_in=restaurant_data)
    return restaurant_data


@restaurant_router.get("/get_restaurants", response_model=List[Restaurant])
def get_restaurants(db: get_db, page: int = 1, per_page: int = 50):
    rows = restaurant_crud.get_multi(db, page=page, per_page=per_page)
    return [
        Restaurant(
            upi_merchant_name=r.upi_merchant_name or "",
            upi_id=r.upi_id or "",
            restaurant_address=getattr(r, "restaurant_address", None),
            restaurant_phone=getattr(r, "restaurant_phone", None),
            restaurant_email=getattr(r, "restaurant_email", None),
            logo_url=getattr(r, "logo_url", None),
        )
        for r in rows
    ]


ALLOWED_LOGO_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
EXT_FROM_CONTENT_TYPE = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


@restaurant_router.post("/upload_restaurant_logo")
def upload_restaurant_logo(file: UploadFile = File(...)):
    """Upload a logo image; returns logo_url to use in create_restaurant."""
    if file.content_type not in ALLOWED_LOGO_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Allowed types: PNG, JPEG, WebP, GIF",
        )
    ext = EXT_FROM_CONTENT_TYPE.get(file.content_type) or ".png"
    uploads_dir = os.path.join(Config.BASE_DIR, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    filename = f"restaurant_logo_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(uploads_dir, filename)
    try:
        contents = file.file.read()
        with open(filepath, "wb") as f:
            f.write(contents)
    finally:
        file.file.close()
    logo_url = f"/api/uploads/{filename}"
    return {"logo_url": logo_url}


########################################################
# User APIs
########################################################


@user_router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
def signup(user_req: SignupRequest, db: get_db):
    email = (user_req.email or "").strip().lower()
    if user_crud.get_by_email(db, email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )
    user_id = str(uuid.uuid4())
    data = user_req.model_dump()
    data["email"] = email
    data["password"] = (data.get("password") or "").strip()
    # Signup has no authenticated user; use new user's firstname for audit fields
    firstname_str = (data.get("firstname") or "signup").strip() or "signup"
    user = user_crud.create(
        db,
        obj_in=UserBase(
            id=user_id,
            created_by=firstname_str,
            updated_by=firstname_str,
            **data,
        ),
    )
    return Token(user=user, token=user.create_token())


@user_router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
def login(login_creds: LoginRequest, db: get_db):
    email = (login_creds.email or "").strip().lower()
    password = (login_creds.password or "").strip()
    user = user_crud.get_by_email(db, email)
    if not user:
        logger.debug("Login 401: no user found for email=%s", email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    if not user.verify_password(password):
        logger.debug(
            "Login 401: password mismatch for email=%s (DB may use Argon2 - pip install 'passlib[argon2]')",
            email,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    return Token(user=user, token=user.create_token())


@user_router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
def me(user_db: authenticated_user):
    user, _ = user_db
    return user


@user_router.get(
    "/users", response_model=List[UserResponse], status_code=status.HTTP_200_OK
)
def get_users(db: get_db, page: int = 1, per_page: int = 10):
    users = user_crud.get_multi(db, page=page, per_page=per_page)
    return [
        UserResponse(
            id=str(u.id),
            email=u.email,
            firstname=u.firstname,
            lastname=u.lastname,
            role=u.role,
        )
        for u in users
    ]


@user_router.put(
    "/user", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def update_user(user_req: UserUpdate, user_db: authenticated_user):
    _, db = user_db
    return user_crud.update(db, db_obj=user_db, obj_in=user_req)


@user_router.delete("/user", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_db: authenticated_user):
    _, db = user_db
    user_crud.soft_del(db, db_obj=user_db)
    return None


########################################################
# Table APIs
########################################################
@table_router.post(
    "/create_table", response_model=Table, status_code=status.HTTP_201_CREATED
)
def create_table(table_data: Table, user_db: authenticated_user):
    user, db = user_db
    # Table model has table_no (+ ModelBase); no table_id column (id is the PK)
    obj_in = {"table_no": table_data.table_no}
    obj_in["created_by"] = str(getattr(user, "firstname", None) or "system")
    obj_in["updated_by"] = str(getattr(user, "firstname", None) or "system")
    created = table_crud.create(db, obj_in=obj_in)
    return Table(table_id=str(created.id), table_no=created.table_no)


@table_router.get("/get_tables", response_model=List[Table])
def get_tables(db: get_db, page: int = 1, per_page: int = 10):
    tables = table_crud.get_multi(db, page=page, per_page=per_page)
    return [Table(table_id=str(t.id), table_no=t.table_no) for t in tables]


@table_router.get("/tables_by_id/{table_id}", response_model=Table)
def get_table(table_id: str, db: get_db):

    db_table = table_crud.get(db, id=table_id)
    if not db_table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Table not found"
        )
    return Table(table_id=str(db_table.id), table_no=db_table.table_no)


@table_router.put("/update_table/{table_id}", response_model=Table)
def update_table(
    table_id: str,
    table_data: Table,
    user_db: authenticated_user,
):
    _, db = user_db
    db_table = table_crud.get(db, id=table_id)
    if not db_table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Table not found"
        )
    updated_data = table_crud.update(db, db_obj=db_table, obj_in=table_data)
    return updated_data


@table_router.delete(
    "/delete_table_by_id/{table_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_table(table_id: str, db: get_db):
    db_table = table_crud.get(db, id=table_id)
    if not db_table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Table not found"
        )
    table_crud.soft_del(db, db_table)
    return {"message": "Table deleted successfully"}


########################################################
# Category APIs
########################################################


@category_router.post(
    "/create_category", response_model=Category, status_code=status.HTTP_201_CREATED
)
def create_category(category_data: Category, user_db: authenticated_user):
    _, db = user_db
    obj_in = category_data.model_dump()
    obj_in["created_by"] = str(UserModel.firstname)
    obj_in["updated_by"] = str(UserModel.firstname)
    category_crud.create(db, obj_in=obj_in)
    return Category(
        category_id=str(category_data.category_id),
        category_name=category_data.category_name,
    )


########################################################
# Menu APIs
########################################################


def _ensure_list_of_dicts(value):
    """Normalize JSON/list so Pydantic gets a list of dicts (handles str, list of dicts, list of strings, Row-like)."""
    if value is None:
        return []
    if isinstance(value, str):
        if not value or not value.strip():
            return []
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    if not isinstance(value, list):
        return []
    out = []
    for el in value:
        if isinstance(el, dict):
            out.append(el)
        elif hasattr(el, "_mapping"):
            out.append(dict(el._mapping))
        elif hasattr(el, "__iter__") and not isinstance(el, str):
            try:
                out.append(dict(el))
            except (TypeError, ValueError):
                pass
        elif isinstance(el, str):
            try:
                parsed = json.loads(el)
                if isinstance(parsed, dict):
                    out.append(parsed)
            except (json.JSONDecodeError, TypeError):
                pass
    return out


def _menu_row_to_schema(m):
    """Build Menu schema from DB row (item_list/category_name stored as JSON strings)."""
    item_list = _ensure_list_of_dicts(m.item_list)
    category_name = _ensure_list_of_dicts(m.category_name)
    quantity = m.quantity
    if quantity is not None and not isinstance(quantity, str):
        quantity = str(quantity)
    return Menu(
        menu_id=str(m.menu_id or m.id),
        item_list=item_list,
        price=m.price,
        quantity=quantity or "",
        category_name=category_name,
    )


@menu_router.post(
    "/create_menu", response_model=Menu, status_code=status.HTTP_201_CREATED
)
def create_menu(menu_data: MenuCreate, user_db: authenticated_user):
    _, db = user_db
    # Serialize lists to JSON strings for DB columns
    item_list_json = json.dumps(
        [p.model_dump() if hasattr(p, "model_dump") else p for p in menu_data.item_list],
        default=str,
    )
    category_name_json = json.dumps(menu_data.category_name, default=str)
    db_obj = MenuModel(
        menu_id=str(uuid.uuid4()),
        item_list=item_list_json,
        price=int(menu_data.price or 0),
        quantity=str(menu_data.quantity or ""),
        category_name=category_name_json,
        created_by=str(UserModel.firstname),
        updated_by=str(UserModel.firstname),
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return _menu_row_to_schema(db_obj)


@menu_router.get("/get_menus", response_model=List[Menu])
def get_menus(db: get_db, page: int = 1, per_page: int = 10):
    menus = menu_crud.get_multi(db, page=page, per_page=per_page)
    return [_menu_row_to_schema(m) for m in menus]


def _normalize_menu_id(menu_id: str) -> str:
    """Strip surrounding quotes so IDs like \"uuid\" still resolve."""
    if not menu_id:
        return menu_id
    return menu_id.strip().strip('"').strip("'").strip()


@menu_router.get("/get_menu_by_id/{menu_id}", response_model=Menu)
def get_menu(menu_id: str, db: get_db):
    menu_id = _normalize_menu_id(menu_id)
    menu = (
        db.query(MenuModel)
        .filter(MenuModel.menu_id == menu_id, MenuModel.is_deleted == false())
        .first()
    )
    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Menu not found for menu_id: {menu_id}. Use a menu_id from GET /get_menus or from POST /create_menu.",
        )
    return _menu_row_to_schema(menu)


@menu_router.put("/update_menu/{menu_id}", response_model=Menu)
def update_menu(
    menu_id: str,
    menu_data: Menu,
    user_db: authenticated_user,
):
    _, db = user_db
    menu_id = _normalize_menu_id(menu_id)
    menu = (
        db.query(MenuModel)
        .filter(MenuModel.menu_id == menu_id, MenuModel.is_deleted == false())
        .first()
    )
    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Menu not found for menu_id: {menu_id}. Use a menu_id from GET /get_menus or from POST /create_menu.",
        )
    menu.item_list = json.dumps(menu_data.item_list, default=str)
    menu.price = int(menu_data.price)
    menu.quantity = menu_data.quantity
    menu.category_name = json.dumps(menu_data.category_name, default=str)
    menu.updated_by = str(UserModel.firstname)
    db.add(menu)
    db.commit()
    db.refresh(menu)
    return _menu_row_to_schema(menu)


@menu_router.delete(
    "/delete_menu_by_id/{menu_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_menu(menu_id: str, db: get_db):
    menu_id = _normalize_menu_id(menu_id)
    menu = (
        db.query(MenuModel)
        .filter(MenuModel.menu_id == menu_id, MenuModel.is_deleted == false())
        .first()
    )
    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Menu not found for menu_id: {menu_id}. Use a menu_id from GET /get_menus or from POST /create_menu.",
        )
    menu_crud.soft_del(db, menu)
    return {"message": "Menu deleted successfully"}


def _order_status_from_model(o: OrderModel) -> OrderStatus:
    """Derive OrderStatus from order_pending, order_done, order_cancel."""
    done = (o.order_done or "").lower() == "true"
    cancel = (o.order_cancel or "").lower() == "true"
    pending = (o.order_pending or "").lower() == "true"
    if cancel:
        return OrderStatus.CANCELLED
    if done:
        return OrderStatus.READY
    if pending:
        return OrderStatus.PENDING
    return OrderStatus.PREPARING


def _order_status_for_response(o: OrderModel, db) -> OrderStatus:
    """Use status from order_status table if present; else derive from order flags."""
    row = (
        db.query(OrderStatusModel)
        .filter(
            OrderStatusModel.order_id == str(o.id),
            OrderStatusModel.is_deleted == false(),
        )
        .first()
    )
    if row and (row.status or "").strip():
        try:
            return OrderStatus(row.status.strip().lower())
        except ValueError:
            pass
    return _order_status_from_model(o)


def _order_row_to_response(o: OrderModel, db) -> OrderResponse:
    """Build OrderResponse from DB row; status from order_status table when present."""
    return OrderResponse(
        order_id=str(o.id),
        item_list=o.item_list or "[]",
        order_status=_order_status_for_response(o, db),
        table_id=str(o.table_no or ""),
    )


########################################################
# Order APIs
########################################################


@order_router.post(
    "/create_order", response_model=OrderResponse, status_code=status.HTTP_201_CREATED
)
def create_order(order_data: OrderCreate, db: get_db):
    try:
        table_no = int(order_data.table_no)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="table_no must be a valid integer",
        )
    obj_in = {
        "item_list": order_data.item_list,
        "quantity": order_data.quantity,
        "table_no": table_no,
        "order_pending": "true",
        "order_done": "false",
        "order_cancel": "false",
    }
    created = order_crud.create(db, obj_in=obj_in)
    return _order_row_to_response(created, db)


@order_router.get("/get_orders", response_model=List[OrderResponse])
def get_orders(db: get_db, page: int = 1, per_page: int = 10):
    orders = order_crud.get_multi(db, page=page, per_page=per_page)
    return [_order_row_to_response(o, db) for o in orders]


@order_router.get("/get_order_by_id/{order_id}", response_model=OrderResponse)
def get_order(order_id: str, db: get_db):
    order = order_crud.get(db, id=order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )
    return _order_row_to_response(order, db)


@order_router.put("/update_order/{order_id}", response_model=OrderResponse)
def update_order(
    order_id: str,
    order_data: OrderUpdate,
    user_db: authenticated_user,
):
    _, db = user_db
    order_id = order_id.strip("'\"")
    order = order_crud.get(db, id=order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )
    order.item_list = order_data.item_list
    order.quantity = order_data.quantity
    order.updated_by = str(UserModel.firstname)
    order_crud.update(db, db_obj=order, obj_in=order_data)
    return _order_row_to_response(order, db)


@order_router.delete(
    "/delete_order_by_id/{order_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_order(order_id: str, db: get_db):
    order = order_crud.get(db, id=order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )
    order_crud.soft_del(db, order)
    return {"message": "Order deleted successfully"}


########################################################
# Order Status APIs
########################################################


def _normalize_order_id(order_id: str) -> str:
    """Strip surrounding quotes so IDs like \"uuid\" still resolve."""
    if not order_id:
        return order_id
    return order_id.strip().strip('"').strip("'").strip()


@order_status_router.put(
    "/update_order_status/{order_id}", response_model=OrderStatusResponse
)
def update_order_status(
    order_id: str,
    order_status_data: OrderStatusUpdate,
    user_db: authenticated_user,
):
    _, db = user_db
    order_id = _normalize_order_id(order_id)
    # Ensure order exists
    order = order_crud.get(db, id=order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )
    order_status = (
        db.query(OrderStatusModel)
        .filter(
            OrderStatusModel.order_id == order_id,
            OrderStatusModel.is_deleted == false(),
        )
        .first()
    )
    if not order_status:
        # Create order_status row on first update (orders don't get one at creation)
        order_status = OrderStatusModel(
            order_id=order_id,
            status=order_status_data.status.value,
            created_by=str(UserModel.firstname),
            updated_by=str(UserModel.firstname),
        )
        db.add(order_status)
        db.commit()
        db.refresh(order_status)
    else:
        order_status.status = order_status_data.status.value
        order_status.updated_by = str(UserModel.firstname)
        order_status_crud.update(db, db_obj=order_status, obj_in=order_status_data)
        db.refresh(order_status)
    return OrderStatusResponse(
        order_id=str(order_status.order_id), status=order_status.status or ""
    )


########################################################
# Stock APIs
########################################################


@stock_router.post(
    "/create_stock", response_model=Stock, status_code=status.HTTP_201_CREATED
)
def create_stock(stock_data: StockCreate, user_db: authenticated_user):
    _, db = user_db
    obj_in = stock_data.model_dump()
    obj_in["created_by"] = str(UserModel.firstname)
    obj_in["updated_by"] = str(UserModel.firstname)
    # Let the DB generate id and timestamps (avoid duplicate key on retry or client-sent id)
    obj_in.pop("id", None)
    obj_in.pop("created_at", None)
    obj_in.pop("updated_at", None)
    created = stock_crud.create(db, obj_in=obj_in)
    return Stock(
        id=str(created.id),
        name=created.name,
        quantity=created.quantity,
        unit_of_measure=created.unit_of_measure,
        cost_per_unit=created.cost_per_unit,
    )


@stock_router.get("/get_stocks", response_model=List[Stock])
def get_stocks(db: get_db, page: int = 1, per_page: int = 10):
    stocks = stock_crud.get_multi(db, page=page, per_page=per_page)
    return [
        Stock(
            id=str(s.id),
            name=s.name,
            quantity=s.quantity,
            unit_of_measure=s.unit_of_measure,
            cost_per_unit=s.cost_per_unit,
        )
        for s in stocks
    ]


@stock_router.get("/get_stock_by_id/{stock_id}", response_model=Stock)
def get_stock(stock_id: str, db: get_db):
    stock = stock_crud.get(db, id=stock_id)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found"
        )
    return Stock(
        id=str(stock.id),
        name=stock.name,
        quantity=stock.quantity,
        unit_of_measure=stock.unit_of_measure,
        cost_per_unit=stock.cost_per_unit,
    )


@stock_router.put(
    "/update_stock/{stock_id}", status_code=status.HTTP_200_OK, response_model=Stock
)
def update_stock(stock_id: str, stock_data: StockUpdate, user_db: authenticated_user):
    _, db = user_db
    stock = stock_crud.get(db, id=stock_id)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found"
        )
    updated_data = stock_crud.update(db, db_obj=stock, obj_in=stock_data)
    return updated_data


@stock_router.delete(
    "/delete_stock_by_id/{stock_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_stock(stock_id: str, user_db: authenticated_user):
    _, db = user_db
    stock = stock_crud.get(db, id=stock_id)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found"
        )
    stock_crud.soft_del(db, stock)
    return {"message": "Stock deleted successfully"}


########################################################
# Invoice APIs
########################################################


def _invoice_total_from_subtotal(subtotal: float, gst_percent: float, discount_percent: float) -> float:
    """Compute total from subtotal + GST% - discount% (discount applied on subtotal)."""
    gst_amount = round(subtotal * (gst_percent / 100), 2)
    discount_amount = round(subtotal * (discount_percent / 100), 2)
    return round(subtotal + gst_amount - discount_amount, 2)


@invoice_router.post(
    "/create_invoice", response_model=Invoice, status_code=status.HTTP_201_CREATED
)
def create_invoice(invoice_data: InvoiceCreate, user_db: authenticated_user):
    _, db = user_db
    order = order_crud.get(db, id=invoice_data.order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order not found. Use a valid order_id from GET /get_orders.",
        )
    items = _parse_order_items(order.item_list or "[]")
    subtotal = round(sum((item["quantity"] * item["price"]) for item in items), 2)
    gst_percent = float(getattr(invoice_data, "gst_percent", 0) or 0)
    discount_percent = float(getattr(invoice_data, "discount_percent", 0) or 0)
    total_amount = _invoice_total_from_subtotal(subtotal, gst_percent, discount_percent)
    obj_in = invoice_data.model_dump(exclude_unset=True)
    obj_in["total_amount"] = total_amount
    obj_in["gst_percent"] = gst_percent
    obj_in["discount_percent"] = discount_percent
    obj_in["created_by"] = str(UserModel.firstname)
    obj_in["updated_by"] = str(UserModel.firstname)
    try:
        created = invoice_crud.create(db, obj_in=obj_in)
    except IntegrityError as e:
        err_msg = str(e.orig) if getattr(e, "orig", None) else str(e)
        if "invoice_number" in err_msg or "ix_invoice_invoice_number" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An invoice with this invoice_number already exists. Use a different invoice_number.",
            ) from e
        raise
    return Invoice(
        invoice_id=str(created.id),
        order_id=created.order_id,
        invoice_number=created.invoice_number,
        invoice_date=created.invoice_date,
        total_amount=created.total_amount,
        gst_percent=getattr(created, "gst_percent", 0) or 0,
        discount_percent=getattr(created, "discount_percent", 0) or 0,
        payment_status=created.payment_status,
        notes=created.notes,
        customer_name=getattr(created, "customer_name", ""),
    )


@invoice_router.get("/get_invoices", response_model=List[Invoice])
def get_invoices(db: get_db, page: int = 1, per_page: int = 10):
    invoices = invoice_crud.get_multi(db, page=page, per_page=per_page)
    return [
        Invoice(
            invoice_id=str(i.id),
            order_id=i.order_id,
            invoice_number=i.invoice_number,
            invoice_date=i.invoice_date,
            total_amount=i.total_amount,
            gst_percent=getattr(i, "gst_percent", 0) or 0,
            discount_percent=getattr(i, "discount_percent", 0) or 0,
            payment_status=i.payment_status,
            notes=i.notes,
            customer_name=getattr(i, "customer_name", ""),
        )
        for i in invoices
    ]


@invoice_router.get("/get_invoice_by_id/{invoice_id}", response_model=Invoice)
def get_invoice(invoice_id: str, db: get_db):
    invoice = invoice_crud.get(db, id=invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )
    return Invoice(
        invoice_id=str(invoice.id),
        order_id=invoice.order_id,
        invoice_number=invoice.invoice_number,
        invoice_date=invoice.invoice_date,
        total_amount=invoice.total_amount,
        gst_percent=getattr(invoice, "gst_percent", 0) or 0,
        discount_percent=getattr(invoice, "discount_percent", 0) or 0,
        payment_status=invoice.payment_status,
        notes=invoice.notes,
        customer_name=getattr(invoice, "customer_name", ""),
    )


@invoice_router.put("/update_invoice/{invoice_id}", response_model=Invoice)
def update_invoice(
    invoice_id: str,
    invoice_data: InvoiceUpdate,
    user_db: authenticated_user,
):
    _, db = user_db
    invoice = invoice_crud.get(db, id=invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )
    if invoice_data.order_id is not None:
        order = order_crud.get(db, id=invoice_data.order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order not found. Use a valid order_id from GET /get_orders.",
            )
        invoice.order_id = invoice_data.order_id
    if invoice_data.invoice_number is not None:
        invoice.invoice_number = invoice_data.invoice_number
    if invoice_data.invoice_date is not None:
        invoice.invoice_date = invoice_data.invoice_date
    if invoice_data.total_amount is not None:
        invoice.total_amount = invoice_data.total_amount
    if invoice_data.gst_percent is not None:
        invoice.gst_percent = invoice_data.gst_percent
    if invoice_data.discount_percent is not None:
        invoice.discount_percent = invoice_data.discount_percent
    if invoice_data.payment_status is not None:
        invoice.payment_status = invoice_data.payment_status
    if invoice_data.notes is not None:
        invoice.notes = invoice_data.notes
    if invoice_data.customer_name is not None:
        invoice.customer_name = invoice_data.customer_name
    invoice.updated_by = str(user_db.firstname)
    invoice_crud.update(db, db_obj=invoice, obj_in=invoice_data)
    db.refresh(invoice)
    return Invoice(
        invoice_id=str(invoice.id),
        order_id=invoice.order_id,
        invoice_number=invoice.invoice_number,
        invoice_date=invoice.invoice_date,
        total_amount=invoice.total_amount,
        gst_percent=getattr(invoice, "gst_percent", 0) or 0,
        discount_percent=getattr(invoice, "discount_percent", 0) or 0,
        payment_status=invoice.payment_status,
        notes=invoice.notes,
        customer_name=getattr(invoice, "customer_name", ""),
    )


@invoice_router.get(
    "/tables_with_uninvoiced_orders", response_model=List[int]
)
def get_tables_with_uninvoiced_orders(db: get_db):
    """Return list of table numbers that have at least one uninvoiced order (for dropdown when creating invoice by table)."""
    all_invoices = (
        db.query(InvoiceModel)
        .filter(InvoiceModel.is_deleted == false())
        .all()
    )
    invoiced_order_ids = set()
    for inv in all_invoices:
        invoiced_order_ids.add(inv.order_id)
        if inv.order_ids:
            try:
                ids = json.loads(inv.order_ids)
                if isinstance(ids, list):
                    invoiced_order_ids.update(str(x) for x in ids)
            except (json.JSONDecodeError, TypeError):
                pass
    filters = [OrderModel.is_deleted == false()]
    if invoiced_order_ids:
        filters.append(~OrderModel.id.in_(invoiced_order_ids))
    rows = (
        db.query(OrderModel.table_no)
        .filter(*filters)
        .distinct()
        .order_by(OrderModel.table_no)
        .all()
    )
    return [r[0] for r in rows if r[0] is not None]


@invoice_router.post(
    "/create_invoice_for_table", response_model=Invoice, status_code=status.HTTP_201_CREATED
)
def create_invoice_for_table(
    payload: InvoiceCreateForTable, user_db: authenticated_user
):
    """Create a single merged invoice for all (uninvoiced) orders from the given table."""
    _, db = user_db
    table_no = payload.table_no

    # Collect all order IDs that are already on any invoice
    all_invoices = (
        db.query(InvoiceModel)
        .filter(InvoiceModel.is_deleted == false())
        .all()
    )
    invoiced_order_ids = set()
    for inv in all_invoices:
        invoiced_order_ids.add(inv.order_id)
        if inv.order_ids:
            try:
                ids = json.loads(inv.order_ids)
                if isinstance(ids, list):
                    invoiced_order_ids.update(str(x) for x in ids)
            except (json.JSONDecodeError, TypeError):
                pass

    # All orders for this table that are not yet invoiced
    filters = [
        OrderModel.table_no == table_no,
        OrderModel.is_deleted == false(),
    ]
    if invoiced_order_ids:
        filters.append(~OrderModel.id.in_(invoiced_order_ids))
    table_orders = (
        db.query(OrderModel).filter(*filters).order_by(OrderModel.id).all()
    )
    if not table_orders:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No uninvoiced orders found for table {table_no}. All orders for this table may already be invoiced.",
        )

    order_ids_list = [str(o.id) for o in table_orders]
    first_order_id = order_ids_list[0]

    # Compute subtotal from all orders' item_list, then apply GST and discount
    subtotal = 0.0
    for o in table_orders:
        items = _parse_order_items(o.item_list or "[]")
        subtotal += sum((item["quantity"] * item["price"]) for item in items)
    subtotal = round(subtotal, 2)
    gst_percent = float(getattr(payload, "gst_percent", 0) or 0)
    discount_percent = float(getattr(payload, "discount_percent", 0) or 0)
    total_amount = _invoice_total_from_subtotal(subtotal, gst_percent, discount_percent)

    invoice_number = payload.invoice_number or f"INV-{int(__import__('time').time() * 1000)}"
    invoice_date = payload.invoice_date
    if invoice_date is None:
        from datetime import datetime
        invoice_date = datetime.now()

    obj_in = {
        "order_id": first_order_id,
        "order_ids": json.dumps(order_ids_list),
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "total_amount": total_amount,
        "gst_percent": gst_percent,
        "discount_percent": discount_percent,
        "payment_status": payload.payment_status.value
        if hasattr(payload.payment_status, "value")
        else payload.payment_status,
        "notes": payload.notes,
        "customer_name": (payload.customer_name or "").strip(),
        "created_by": str(UserModel.firstname),
        "updated_by": str(UserModel.firstname),
    }
    try:
        created = invoice_crud.create(db, obj_in=obj_in)
    except IntegrityError as e:
        err_msg = str(e.orig) if getattr(e, "orig", None) else str(e)
        if "invoice_number" in err_msg or "ix_invoice_invoice_number" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An invoice with this invoice_number already exists. Use a different invoice_number.",
            ) from e
        raise
    return Invoice(
        invoice_id=str(created.id),
        order_id=created.order_id,
        invoice_number=created.invoice_number,
        invoice_date=created.invoice_date,
        total_amount=created.total_amount,
        gst_percent=getattr(created, "gst_percent", 0) or 0,
        discount_percent=getattr(created, "discount_percent", 0) or 0,
        payment_status=created.payment_status,
        notes=created.notes,
        customer_name=getattr(created, "customer_name", ""),
    )


@invoice_router.delete(
    "/delete_invoice_by_id/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_invoice(invoice_id: str, db: get_db):
    invoice = invoice_crud.get(db, id=invoice_id)
    if invoice:
        invoice_crud.soft_del(db, invoice)
        return None
    # Already soft-deleted? Treat as success (idempotent delete)
    invoice_any = invoice_crud.get_deleted_also(db, id=invoice_id)
    if invoice_any:
        return None
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
    )


def _parse_order_items(item_list_str: str) -> List[dict]:
    """Parse order item_list JSON into list of {description, quantity, price} for invoice."""
    if not item_list_str or not (item_list_str or "").strip():
        return []
    try:
        raw = json.loads(item_list_str) if isinstance(item_list_str, str) else item_list_str
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(raw, list):
        return []
    rows = []
    for i, el in enumerate(raw):
        if not isinstance(el, dict):
            continue
        name = el.get("name") or el.get("item_name") or el.get("description") or f"Item {i + 1}"
        qty = int(el.get("qty") or el.get("quantity") or 1)
        price = float(el.get("price") or 0)
        rows.append({"description": str(name), "quantity": qty, "price": price})
    return rows


@invoice_router.get(
    "/invoice/{invoice_id}/view",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def invoice_view_page(invoice_id: str, db: get_db):
    """Generate a printable invoice page with restaurant details and line items."""
    invoice = invoice_crud.get(db, id=invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )

    # Merged invoice: multiple orders from same table
    order_ids_json = getattr(invoice, "order_ids", None)
    order_ids_list = []
    if order_ids_json:
        try:
            parsed = json.loads(order_ids_json)
            if isinstance(parsed, list) and len(parsed) > 1:
                order_ids_list = [str(x) for x in parsed]
        except (json.JSONDecodeError, TypeError):
            pass

    if order_ids_list:
        orders = []
        for oid in order_ids_list:
            o = order_crud.get(db, id=oid)
            if o:
                orders.append(o)
        if not orders:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orders not found for this invoice",
            )
        order = orders[0]
        line_items = []
        for o in orders:
            line_items.extend(_parse_order_items(o.item_list or "[]"))
    else:
        order = order_crud.get(db, id=invoice.order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found for this invoice",
            )
        line_items = _parse_order_items(order.item_list or "[]")

    restaurants = restaurant_crud.get_multi(db, page=1, per_page=1)
    restaurant = restaurants[0] if restaurants else None

    logo_url = getattr(restaurant, "logo_url", None) or ""
    address = getattr(restaurant, "restaurant_address", None) or ""
    phone = getattr(restaurant, "restaurant_phone", None) or ""
    email = getattr(restaurant, "restaurant_email", None) or ""

    inv_date = invoice.invoice_date
    if hasattr(inv_date, "strftime"):
        date_str = inv_date.strftime("%d/%m/%Y")
    else:
        date_str = str(inv_date)[:10] if inv_date else ""

    total = float(invoice.total_amount or 0)
    subtotal = round(sum((item["quantity"] * item["price"]) for item in line_items), 2) or total
    gst_percent = float(getattr(invoice, "gst_percent", 0) or 0)
    discount_percent = float(getattr(invoice, "discount_percent", 0) or 0)
    gst_amount = round(subtotal * (gst_percent / 100), 2)
    discount_amount = round(subtotal * (discount_percent / 100), 2)
    total_computed = round(subtotal + gst_amount - discount_amount, 2)
    if abs(total_computed - total) > 0.01:
        total_computed = total

    rows_html = "".join(
        f"""
        <tr>
          <td>{i + 1}</td>
          <td>{html.escape(str(item['description']))}</td>
          <td>{item['quantity']}pcs</td>
          <td>₹{item['price']:.2f}</td>
        </tr>"""
        for i, item in enumerate(line_items)
    )
    if not rows_html:
        rows_html = "<tr><td colspan='4'>No items</td></tr>"

    # Header: logo (if set) or initial, then restaurant name (auto from first restaurant in DB)
    restaurant_display_name = (restaurant.upi_merchant_name or "Restaurant") if restaurant else "Restaurant"
    logo_html = ""
    if logo_url:
        logo_html = f'<img src="{html.escape(logo_url)}" alt="{html.escape(restaurant_display_name)}" class="logo-img" />'
    else:
        initial = (restaurant_display_name or "R")[0].upper()
        logo_html = f'<div class="logo-placeholder" aria-hidden="true">{html.escape(initial)}</div>'

    website = getattr(restaurant, "website", None) or ""
    contact_lines = []
    if phone:
        contact_lines.append(f'<span class="contact-line"><span class="icon">&#9742;</span> {html.escape(phone)}</span>')
    if website:
        contact_lines.append(f'<span class="contact-line"><span class="icon">&#127760;</span> {html.escape(website)}</span>')
    elif address:
        contact_lines.append(f'<span class="contact-line"><span class="icon">&#127760;</span> www.restaurant.com</span>')
    if email:
        contact_lines.append(f'<span class="contact-line"><span class="icon">&#9993;</span> {html.escape(email)}</span>')
    if address:
        contact_lines.append(f'<span class="contact-line"><span class="icon">&#128205;</span> {html.escape(address)}</span>')
    contact_html = "".join(contact_lines) if contact_lines else "<span class=\"contact-line\">—</span>"

    customer_name_val = (getattr(invoice, "customer_name", "") or "").strip()
    customer_display = html.escape(customer_name_val) if customer_name_val else f"Table {html.escape(str(order.table_no or ''))}"
    customer_address = ""

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Invoice {html.escape(invoice.invoice_number or "")}</title>
  <link href="https://fonts.googleapis.com/css2?family=Dancing+Script:wght@500&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: 'Segoe UI', system-ui, sans-serif; margin: 0; padding: 2rem; background: #f5f0e8; color: #3d2f24; }}
    .invoice {{ max-width: 800px; margin: 0 auto; background: #fdfbf7; padding: 2.5rem; border-radius: 8px; box-shadow: 0 2px 16px rgba(61,47,36,0.06); position: relative; }}
    .leaf-top {{ position: absolute; top: 1rem; left: 1rem; color: #6b5344; font-size: 1.8rem; opacity: 0.7; }}
    .leaf-bottom {{ position: absolute; bottom: 1rem; right: 1rem; color: #6b5344; font-size: 1.8rem; opacity: 0.7; }}
    .header-top {{ display: flex; justify-content: center; align-items: center; gap: 0.75rem; margin-bottom: 1.5rem; }}
    .logo-img {{ width: 56px; height: 56px; object-fit: contain; border-radius: 50%; }}
    .logo-placeholder {{ width: 56px; height: 56px; border: 2px solid #6b5344; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; color: #6b5344; }}
    .logo-text {{ font-weight: 700; font-size: 1.25rem; color: #3d2f24; letter-spacing: 0.02em; }}
    .header-row {{ display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 1rem; margin-bottom: 0.5rem; }}
    .bill-to {{ font-size: 0.75rem; color: #6b5344; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.2rem; }}
    .customer-name {{ font-size: 1.1rem; font-weight: 700; color: #3d2f24; }}
    .customer-addr {{ font-size: 0.9rem; color: #5c4a3a; }}
    .inv-meta {{ text-align: right; font-size: 0.9rem; color: #3d2f24; }}
    .inv-meta p {{ margin: 0.2rem 0; }}
    h1.invoice-title {{ text-align: center; font-size: 1.6rem; margin: 1.25rem 0; color: #3d2f24; font-weight: 700; letter-spacing: 0.02em; }}
    table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
    th {{ text-align: left; padding: 0.5rem 0.4rem; border-bottom: 1px solid #d4cdc4; font-size: 0.8rem; color: #3d2f24; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; }}
    td {{ padding: 0.5rem 0.4rem; border-bottom: 1px solid #e8e2d9; font-size: 0.9rem; color: #3d2f24; }}
    .summary-wrap {{ margin-top: 1.5rem; display: flex; justify-content: flex-end; }}
    .summary {{ width: 280px; border-collapse: collapse; font-size: 0.9rem; color: #3d2f24; }}
    .summary tr {{ border-bottom: 1px solid #e8e2d9; }}
    .summary td {{ padding: 0.35rem 0; border: none; }}
    .summary td:first-child {{ padding-right: 1.5rem; }}
    .summary td:last-child {{ text-align: right; }}
    .summary .total-row {{ font-weight: 700; font-size: 1rem; border-bottom: none; padding-top: 0.4rem; }}
    .footer {{ margin-top: 2rem; padding-top: 1.25rem; border-top: 1px solid #e8e2d9; }}
    .thanks {{ font-family: 'Dancing Script', cursive; font-size: 1.15rem; color: #6b5344; margin-bottom: 0.75rem; }}
    .contact {{ font-size: 0.85rem; color: #5c4a3a; }}
    .contact-line {{ display: block; margin: 0.2rem 0; }}
    .icon {{ margin-right: 0.35rem; color: #6b5344; }}
    @media print {{ body {{ background: #fff; }} .invoice {{ box-shadow: none; }} }}
  </style>
</head>
<body>
  <div class="invoice">
    <span class="leaf-top">&#10047;</span>
    <div class="header-top">
      {logo_html}
      <span class="logo-text">{html.escape(restaurant_display_name)}</span>
    </div>
    <div class="header-row">
      <div>
        <div class="bill-to">INVOICE TO:</div>
        <div class="customer-name">{html.escape(customer_display)}</div>
        <div class="customer-addr">{html.escape(customer_address) or "—"}</div>
      </div>
      <div class="inv-meta">
        <p><strong>INVOICE NO:</strong> {html.escape(invoice.invoice_number or "")}</p>
        <p><strong>DATE:</strong> {date_str}</p>
      </div>
    </div>
    <h1 class="invoice-title">INVOICE</h1>
    <table>
      <thead>
        <tr>
          <th>SL NO</th>
          <th>ITEM DESCRIPTION</th>
          <th>QUANTITY</th>
          <th>PRICE</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
    <table class="summary">
      <tr><td>SUB TOTAL</td><td>₹{subtotal:.2f}</td></tr>
      <tr><td>GST ({gst_percent}%)</td><td>₹{gst_amount:.2f}</td></tr>
      <tr><td>DISCOUNT ({discount_percent}%)</td><td>-₹{discount_amount:.2f}</td></tr>
      <tr class="total-row"><td>TOTAL</td><td>₹{total_computed:.2f}</td></tr>
    </table>
    <div class="footer">
      <div class="thanks">Thank you for your recent order!</div>
      <div class="contact">
        {contact_html}
      </div>
    </div>
    <span class="leaf-bottom">&#10047;</span>
  </div>
</body>
</html>"""
    return HTMLResponse(html_content)


########################################################
# # Payment Status APIs
# ########################################################

# @payment_status_router.put("/update_payment_status/{payment_status_id}", response_model=PaymentStatusResponse)
# def update_payment_status(payment_status_id: str, payment_status_data: PaymentStatusUpdate, db: get_db, user_db:authenticated_user):
#     payment_status = (
#         db.query(PaymentStatusModel)
#         .filter(PaymentStatusModel.payment_status_id == payment_status_id, PaymentStatusModel.is_deleted == false())
#         .first()
#     )
#     if not payment_status:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment status not found")


def generate_upi_uri(order_id: str, amount: float, restaurant: RestaurantModel) -> str:
    """Build UPI payment link so when customer scans & pays, money credits to your bank (upi_id from restaurant)."""
    import urllib.parse

    vpa = (restaurant.upi_id or "").strip() if restaurant else "Restaurant UPI ID"
    if not vpa:
        raise ValueError(
            "upi_id from restaurant is not set. Add your upi_id from restaurant to the database (e.g. 9876543210@ybl or yourname@paytm) "
            "so payment QR codes credit to your bank account."
        )

    params = {
        "pa": vpa,  # Payee VPA – your UPI ID (money goes here)
        "pn": (
            restaurant.upi_merchant_name
            if restaurant
            else "Restaurant UPI Merchant Name"
        ),
        "am": str(round(amount, 2)),
        "cu": "INR",
        "tn": f"Order {order_id}",
    }
    qs = urllib.parse.urlencode(params)
    return f"upi://pay?{qs}"


def generate_qr_png(data: str, size: int = 10, border: int = 2) -> bytes:
    """Generate PNG bytes for a QR code encoding the given string (e.g. UPI link)."""
    qr = qrcode.QRCode(version=1, box_size=size, border=border)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _qr_image_url(request: Request, payment_id: str) -> str:
    """Build full URL for the QR image endpoint (must include /api prefix as app mounts api_router at /api)."""
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/{payment_id}/qr/image"


@payment_router.get(
    "/pay/{payment_id}",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def pay_page(request: Request, payment_id: str, db: get_db):
    """
    Integrated payment page: open this URL to show a scannable QR code.
    Share the link with customers (e.g. http://yourserver/pay/{payment_id}) or use in kiosk/tablet.
    """
    payment = db.query(PaymentModel).filter(PaymentModel.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    qr_image_url = _qr_image_url(request, payment_id)
    amount = float(payment.amount)
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Pay &ndash; &#8377;{amount:,.2f}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: system-ui, sans-serif; margin: 0; padding: 2rem; min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; background: #f5f5f5; }}
    .card {{ background: #fff; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); padding: 2rem; text-align: center; max-width: 360px; }}
    h1 {{ margin: 0 0 0.5rem; font-size: 1.5rem; color: #333; }}
    .amount {{ font-size: 2rem; font-weight: 700; color: #0d9488; margin-bottom: 1.5rem; }}
    .qr {{ margin: 0 auto 1rem; display: block; border-radius: 8px; }}
    p {{ color: #666; margin: 0; font-size: 0.95rem; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Scan to pay</h1>
    <div class="amount">&#8377;{amount:,.2f}</div>
    <img class="qr" src="{qr_image_url}" alt="UPI QR code" width="256" height="256" />
    <p>Scan with any UPI app to pay</p>
  </div>
</body> 
</html>
"""
    return HTMLResponse(html)


@payment_router.post(
    "/create_payment",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payment(request: Request, payload: PaymentCreate, db: get_db):
    order_id = payload.order_id
    amount = payload.amount

    if payload.invoice_id:
        invoice = invoice_crud.get(db, id=payload.invoice_id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invoice not found. Use a valid invoice_id from GET /get_invoices.",
            )
        order_id = invoice.order_id
        amount = float(invoice.total_amount or 0)
    else:
        if not order_id or amount is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide either invoice_id or both order_id and amount.",
            )
        amount = float(amount)

    order = order_crud.get(db, id=order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order not found for this invoice/order.",
        )
    # Check duplicate payment for this order
    existing = (
        db.query(PaymentModel).filter(PaymentModel.order_id == order_id).first()
    )
    if existing:
        # Return existing payment with QR so frontend can show it without a second request
        existing_response = PaymentResponse(
            payment_id=str(existing.id),
            order_id=existing.order_id,
            amount=existing.amount,
            payment_status=existing.status,
            retry_count=existing.retry_count or 0,
            upi_ref_id=existing.upi_ref_id,
            qr_image_url=_qr_image_url(request, str(existing.id)),
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "A payment already exists for this order.",
                "payment_id": str(existing.id),
                "payment": existing_response.model_dump(),
            },
        )

    payment = PaymentModel(
        order_id=order_id,
        amount=amount,
        status=PaymentStatus.PENDING,
        retry_count=payload.retry_count or 0,
        upi_ref_id=payload.upi_ref_id,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    # Generate first QR (linked to the restaurant's UPI_ID so payment credits to the restaurant's account)
    try:
        upi_uri = generate_upi_uri(
            order_id=payment.order_id,
            amount=float(payment.amount),
            restaurant=restaurant_crud.get_by_merchant_name(
                db, payload.restaurant_name
            ),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        )
    qr_code_crud.create(
        db,
        obj_in={"payment_id": str(payment.id), "qr_data": upi_uri, "is_active": True},
    )
    return PaymentResponse(
        payment_id=str(payment.id),
        order_id=payment.order_id,
        amount=payment.amount,
        payment_status=payment.status,
        retry_count=payment.retry_count or 0,
        upi_ref_id=payment.upi_ref_id,
        qr_image_url=_qr_image_url(request, str(payment.id)),
    )


def _set_payment_paid_and_persist(
    db,
    payment: PaymentModel,
    upi_ref_id: str | None = None,
) -> None:
    """Mark payment as PAID in DB, set optional upi_ref_id, deactivate its QRs. Caller must have payment loaded."""
    payment.status = PaymentStatus.PAID
    if upi_ref_id is not None:
        payment.upi_ref_id = upi_ref_id
    db.query(QRCodeModel).filter(
        QRCodeModel.payment_id == payment.id,
        QRCodeModel.is_active == True,
    ).update({"is_active": False})
    db.add(payment)
    db.commit()
    db.refresh(payment)


@payment_router.post(
    "/webhook/payment",
    status_code=status.HTTP_200_OK,
)
def payment_webhook(payload: PaymentWebhook, db: get_db):
    """
    Webhook for payment success: when status=paid, payment is automatically updated to PAID and saved to DB.
    Call this from a payment gateway callback or your own job when you detect payment success.
    Send either payment_id or order_id (we look up the payment and update it).
    """
    if not payload.payment_id and not payload.order_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either payment_id or order_id",
        )
    if payload.status != PaymentStatus.PAID:
        return {"ok": True, "message": "Ignored (status is not paid)"}

    if payload.payment_id:
        payment = (
            db.query(PaymentModel).filter(PaymentModel.id == payload.payment_id).first()
        )
    else:
        payment = (
            db.query(PaymentModel)
            .filter(PaymentModel.order_id == payload.order_id)
            .order_by(PaymentModel.created_at.desc())
            .first()
        )

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found for the given payment_id or order_id",
        )
    if payment.status == PaymentStatus.PAID:
        return {
            "ok": True,
            "payment_id": str(payment.id),
            "payment_status": "paid",
            "message": "Already paid",
        }

    _set_payment_paid_and_persist(db, payment, upi_ref_id=payload.upi_ref_id)
    return {"ok": True, "payment_id": str(payment.id), "payment_status": "paid"}


@payment_router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
)
def get_payment(request: Request, payment_id: str, db: get_db):
    payment = db.query(PaymentModel).filter(PaymentModel.id == payment_id).first()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    return PaymentResponse(
        payment_id=str(payment.id),
        order_id=payment.order_id,
        amount=payment.amount,
        payment_status=payment.status,
        retry_count=payment.retry_count or 0,
        upi_ref_id=payment.upi_ref_id,
        qr_image_url=_qr_image_url(request, payment_id),
    )


@payment_router.get(
    "/{payment_id}/qr",
    response_model=QRCode,
)
def get_active_qr(
    request: Request,
    payment_id: str,
    db: get_db,
):
    payment = db.query(PaymentModel).filter(PaymentModel.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    qr = (
        db.query(QRCodeModel)
        .filter(
            QRCodeModel.payment_id == payment_id,
            QRCodeModel.is_active == True,
        )
        .order_by(QRCodeModel.created_at.desc())
        .first()
    )

    if not qr:
        # Payment exists but no active QR: create one on the fly
        db.query(QRCodeModel).filter(
            QRCodeModel.payment_id == payment_id,
            QRCodeModel.is_active == True,
        ).update({"is_active": False})
        try:
            upi_uri = generate_upi_uri(
                order_id=payment.order_id,
                amount=float(payment.amount),
                restaurant=restaurant_crud.get(db, id=payment.order_id),
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e),
            )
        qr = qr_code_crud.create(
            db,
            obj_in={
                "payment_id": str(payment.id),
                "qr_data": upi_uri,
                "is_active": True,
            },
        )

    return QRCode(
        qr_code_id=str(qr.id),
        payment_id=qr.payment_id,
        qr_data=qr.qr_data,
        is_active=qr.is_active,
        qr_image_url=_qr_image_url(request, payment_id),
    )


@payment_router.get(
    "/{payment_id}/qr/image",
    response_class=Response,
    responses={
        200: {"content": {"image/png": {}}, "description": "QR code image (PNG)"}
    },
)
def get_payment_qr_image(
    payment_id: str,
    db: get_db,
    size: int = 10,
    border: int = 2,
):
    """
    Return a scannable QR code image (PNG) for the payment's active UPI link.
    Use in <img src="/.../qr/image"> or download. Size and border are optional query params.
    """
    payment = db.query(PaymentModel).filter(PaymentModel.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    qr = (
        db.query(QRCodeModel)
        .filter(
            QRCodeModel.payment_id == payment_id,
            QRCodeModel.is_active == True,
        )
        .order_by(QRCodeModel.created_at.desc())
        .first()
    )

    if not qr:
        db.query(QRCodeModel).filter(
            QRCodeModel.payment_id == payment_id,
            QRCodeModel.is_active == True,
        ).update({"is_active": False})
        try:
            upi_uri = generate_upi_uri(
                order_id=payment.order_id,
                amount=float(payment.amount),
                restaurant=restaurant_crud.get(db, id=payment.order_id),
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e),
            )
        qr = qr_code_crud.create(
            db,
            obj_in={
                "payment_id": str(payment.id),
                "qr_data": upi_uri,
                "is_active": True,
            },
        )

    png_bytes = generate_qr_png(
        qr.qr_data, size=min(max(size, 1), 20), border=min(max(border, 0), 10)
    )
    return Response(content=png_bytes, media_type="image/png")


@payment_router.post(
    "/{payment_id}/revive",
    response_model=PaymentReviveResponse,
)
def revive_payment(request: Request, payment_id: str, db: get_db):
    payment = db.query(PaymentModel).filter(PaymentModel.id == payment_id).first()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    if payment.status == PaymentStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment already successful",
        )

    # Deactivate old QRs
    db.query(QRCodeModel).filter(
        QRCodeModel.payment_id == payment.id,
        QRCodeModel.is_active == True,
    ).update({"is_active": False})

    # Generate new QR (linked to your UPI_VPA)
    try:
        upi_uri = generate_upi_uri(
            order_id=payment.order_id,
            amount=float(payment.amount),
            restaurant=restaurant_crud.get(db, id=payment.order_id),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )

    new_qr = QRCodeModel(
        payment_id=payment.id,
        qr_data=upi_uri,
        is_active=True,
    )
    new_qr = qr_code_crud.create(db, obj_in=new_qr)
    payment.retry_count += 1
    payment.status = PaymentStatus.PENDING
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return PaymentReviveResponse(
        payment_id=str(payment.id),
        new_qr=QRCode(
            qr_code_id=str(new_qr.id),
            payment_id=new_qr.payment_id,
            qr_data=new_qr.qr_data,
            is_active=new_qr.is_active,
            qr_image_url=_qr_image_url(request, payment_id),
        ),
        retry_count=payment.retry_count or 0,
    )


@payment_router.post(
    "/{payment_id}/mark_paid",
    response_model=PaymentResponse,
    status_code=status.HTTP_200_OK,
)
def mark_payment_paid(
    request: Request,
    payment_id: str,
    db: get_db,
    body: PaymentMarkPaid | None = Body(None),
):
    """
    Record that this payment was successful (customer has paid).
    Call this when you confirm payment (e.g. from your bank/UPI app, or from a payment gateway webhook).
    Optionally pass upi_ref_id (e.g. UPI transaction reference) for your records.
    Updates the payment row in the database and deactivates its QRs.
    """
    payment = db.query(PaymentModel).filter(PaymentModel.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    if payment.status == PaymentStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment is already marked as paid",
        )

    _set_payment_paid_and_persist(
        db, payment, upi_ref_id=body.upi_ref_id if body else None
    )

    return PaymentResponse(
        payment_id=str(payment.id),
        order_id=payment.order_id,
        amount=payment.amount,
        payment_status=payment.status,
        retry_count=payment.retry_count or 0,
        upi_ref_id=payment.upi_ref_id,
        qr_image_url=None,
    )
