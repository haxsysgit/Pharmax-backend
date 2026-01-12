from __future__ import annotations

from starlette.requests import Request

from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend

from app.db.session import SessionLocal, engine
from app.models.invoice_item_table import InvoiceItem
from app.models.invoice_table import Invoice
from app.models.product_table import Product
from app.models.product_unit_table import ProductUnit
from app.models.stock_adjustment_table import StockAdjustment
from app.models.user_table import User, UserRole
from app.models.audit_log_table import AuditLog
from app.services.audit_service import AuditService
from app.services.user_service import UserService


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        identifier = str(form.get("username") or "").strip()
        password = str(form.get("password") or "")
        if not identifier or not password:
            return False

        db = SessionLocal()
        try:
            user = UserService.authenticate(db, identifier, password)
            if not user:
                return False
            if not user.is_active:
                return False
            if user.role != UserRole.ADMIN:
                return False

            request.session["admin_user_id"] = user.id
            db.commit()  # Commit the audit log from authenticate
            return True
        except Exception:
            db.rollback()
            return False
        finally:
            db.close()

    async def logout(self, request: Request) -> bool:
        user_id = request.session.get("admin_user_id")
        request.session.pop("admin_user_id", None)
        
        if user_id:
            db = SessionLocal()
            try:
                AuditService.log_action(
                    db=db,
                    user_id=user_id,
                    action="LOGOUT",
                    resource_type="USER",
                    resource_id=user_id,
                    details={"via": "admin_panel"}
                )
                db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()
        return True

    async def authenticate(self, request: Request) -> bool:
        user_id = request.session.get("admin_user_id")
        if not user_id:
            return False

        db = SessionLocal()
        try:
            user = db.get(User, user_id)
            if not user:
                return False
            if not user.is_active:
                return False
            return user.role == UserRole.ADMIN
        finally:
            db.close()


class UserAdmin(ModelView, model=User):
    column_list = [
        User.id,
        User.username,
        User.email,
        User.full_name,
        User.role,
        User.is_active,
        User.created_at,
        User.updated_at,
    ]
    form_excluded_columns = [User.hashed_password]


class ProductAdmin(ModelView, model=Product):
    column_list = [
        Product.id,
        Product.sku,
        Product.name,
        Product.brand_name,
        Product.quantity_on_hand,
        Product.reorder_level,
        Product.status,
        Product.created_at,
        Product.updated_at,
    ]


class ProductUnitAdmin(ModelView, model=ProductUnit):
    column_list = [
        ProductUnit.id,
        ProductUnit.product_id,
        ProductUnit.name,
        ProductUnit.multiplier_to_base,
        ProductUnit.price_per_unit,
        ProductUnit.is_default,
    ]


class StockAdjustmentAdmin(ModelView, model=StockAdjustment):
    column_list = [
        StockAdjustment.id,
        StockAdjustment.product_id,
        StockAdjustment.change_qty,
        StockAdjustment.reason,
        StockAdjustment.created_at,
    ]


class InvoiceAdmin(ModelView, model=Invoice):
    column_list = [
        Invoice.id,
        Invoice.sold_by_id,
        Invoice.status,
        Invoice.created_at,
        Invoice.updated_at,
    ]


class InvoiceItemAdmin(ModelView, model=InvoiceItem):
    column_list = [
        InvoiceItem.id,
        InvoiceItem.invoice_id,
        InvoiceItem.product_id,
        InvoiceItem.product_unit_id,
        InvoiceItem.quantity,
        InvoiceItem.unit_price,
        InvoiceItem.line_total,
    ]


class AuditLogAdmin(ModelView, model=AuditLog):
    column_list = [
        AuditLog.id,
        AuditLog.user_id,
        AuditLog.action,
        AuditLog.resource_type,
        AuditLog.resource_id,
        AuditLog.details,
        AuditLog.created_at
    ]


def setup_admin(app, *, secret_key: str) -> Admin:
    authentication_backend = AdminAuth(secret_key=secret_key)
    admin = Admin(app, engine, authentication_backend=authentication_backend)

    admin.add_view(UserAdmin)
    admin.add_view(ProductAdmin)
    admin.add_view(ProductUnitAdmin)
    admin.add_view(StockAdjustmentAdmin)
    admin.add_view(InvoiceAdmin)
    admin.add_view(InvoiceItemAdmin)
    admin.add_view(AuditLogAdmin)
    return admin
