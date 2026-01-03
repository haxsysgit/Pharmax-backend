import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import select

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.db.session import SessionLocal
from app.models.user_table import User, UserRole
from app.schemas.user_schema import RegisterUser
from app.services.user_service import UserService


def _ensure_user(
    db,
    *,
    username: str,
    email: str,
    full_name: str,
    role: UserRole,
    password: str,
) -> tuple[User, bool]:
    existing = db.execute(
        select(User).where((User.username == username) | (User.email == email))
    ).scalar_one_or_none()

    if existing:
        return existing, False

    payload = RegisterUser(
        username=username,
        email=email,
        full_name=full_name,
        role=role,
        password=password,
    )
    created = UserService.register_user(db, payload)
    return created, True


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed default Vigilis Pharmacy users (ADMIN/CASHIER/SALES).")

    parser.add_argument("--admin-username", default="admin")
    parser.add_argument("--admin-email", default="admin@vigilis.local")
    parser.add_argument("--admin-password", default=os.getenv("VIGILIS_ADMIN_PASSWORD"))

    parser.add_argument("--cashier-username", default="cashier")
    parser.add_argument("--cashier-email", default="cashier@vigilis.local")
    parser.add_argument("--cashier-password", default=os.getenv("VIGILIS_CASHIER_PASSWORD"))

    parser.add_argument("--sales-username", default="sales")
    parser.add_argument("--sales-email", default="sales@vigilis.local")
    parser.add_argument("--sales-password", default=os.getenv("VIGILIS_SALES_PASSWORD"))

    args = parser.parse_args()

    missing = []
    if not args.admin_password:
        missing.append("--admin-password or VIGILIS_ADMIN_PASSWORD")
    if not args.cashier_password:
        missing.append("--cashier-password or VIGILIS_CASHIER_PASSWORD")
    if not args.sales_password:
        missing.append("--sales-password or VIGILIS_SALES_PASSWORD")

    if missing:
        raise SystemExit(
            "Missing required passwords:\n- " + "\n- ".join(missing) + "\n\n"
            "Passwords must be at least 8 characters."
        )

    db = SessionLocal()
    try:
        created_any = False

        _, created = _ensure_user(
            db,
            username=args.admin_username,
            email=args.admin_email,
            full_name="Admin",
            role=UserRole.ADMIN,
            password=args.admin_password,
        )
        created_any |= created
        print(f"{'CREATED' if created else 'EXISTS'} ADMIN: {args.admin_username} ({args.admin_email})")

        _, created = _ensure_user(
            db,
            username=args.cashier_username,
            email=args.cashier_email,
            full_name="Cashier",
            role=UserRole.CASHIER,
            password=args.cashier_password,
        )
        created_any |= created
        print(f"{'CREATED' if created else 'EXISTS'} CASHIER: {args.cashier_username} ({args.cashier_email})")

        _, created = _ensure_user(
            db,
            username=args.sales_username,
            email=args.sales_email,
            full_name="Sales",
            role=UserRole.SALES,
            password=args.sales_password,
        )
        created_any |= created
        print(f"{'CREATED' if created else 'EXISTS'} SALES: {args.sales_username} ({args.sales_email})")

        if created_any:
            print("Seed complete.")
        else:
            print("No changes (all users already exist).")

    finally:
        db.close()


if __name__ == "__main__":
    main()
