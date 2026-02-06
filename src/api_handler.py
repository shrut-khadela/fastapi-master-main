from fastapi import APIRouter

from src.user.api import user_router, table_router, menu_router, category_router, order_router, order_status_router, stock_router, invoice_router, payment_status_router, payment_router
# Router
api_router = APIRouter()
api_router.include_router(user_router, include_in_schema=True, tags=["User APIs"])
api_router.include_router(table_router, include_in_schema=True, tags=["Table APIs"])
api_router.include_router(menu_router, include_in_schema=True, tags=["Menu APIs"])
api_router.include_router(category_router, include_in_schema=True, tags=["Category APIs"])
api_router.include_router(order_router, include_in_schema=True, tags=["Order APIs"])
api_router.include_router(order_status_router, include_in_schema=True, tags=["Order Status APIs"])
api_router.include_router(stock_router, include_in_schema=True, tags=["Stock APIs"])
api_router.include_router(invoice_router, include_in_schema=True, tags=["Invoice APIs"])
api_router.include_router(payment_status_router, include_in_schema=True, tags=["Payment Status APIs"])
api_router.include_router(payment_router, include_in_schema=True, tags=["Payment APIs"])