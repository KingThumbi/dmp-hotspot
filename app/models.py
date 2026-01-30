from __future__ import annotations

from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


# =========================================================
# Admin Users (Dashboard Login)
# =========================================================
class AdminUser(UserMixin, db.Model):
    """
    Admin users who can access /admin/* routes.

    - Table name remains "admin_users" (matches DB).
    - Login identifier is email (store lowercase).
    - Uses strong password hashing (scrypt) for new/updated passwords.
    """
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(db.String(120), unique=True, nullable=False, index=True)

    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # --- Password helpers ---
    @staticmethod
    def hash_password(password: str) -> str:
        return generate_password_hash(password, method="scrypt")

    def set_password(self, password: str) -> None:
        self.password_hash = self.hash_password(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<AdminUser id={self.id} email={self.email}>"


# =========================================================
# Admin Audit Logs
# =========================================================
class AdminAuditLog(db.Model):
    __tablename__ = "admin_audit_logs"

    id = db.Column(db.Integer, primary_key=True)

    admin_user_id = db.Column(
        db.Integer,
        db.ForeignKey("admin_users.id"),
        nullable=False,
        index=True,
    )

    # e.g. login_success, login_failed, password_changed, logout
    action = db.Column(db.String(60), nullable=False, index=True)

    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)

    # optional metadata (JSON stored as text)
    meta_json = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    admin_user = db.relationship("AdminUser", lazy="joined")

    def __repr__(self) -> str:
        return f"<AdminAuditLog id={self.id} action={self.action} admin_user_id={self.admin_user_id}>"


# =========================================================
# Packages (Hotspot Plans)
# =========================================================
class Package(db.Model):
    __tablename__ = "packages"

    id = db.Column(db.Integer, primary_key=True)

    # e.g. daily_1, weekly_1, monthly_2, etc.
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)

    name = db.Column(db.String(60), nullable=False)

    duration_minutes = db.Column(db.Integer, nullable=False)
    price_kes = db.Column(db.Integer, nullable=False)

    mikrotik_profile = db.Column(db.String(60), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    subscriptions = db.relationship("Subscription", back_populates="package", lazy="select")
    transactions = db.relationship("Transaction", back_populates="package", lazy="select")

    def __repr__(self) -> str:
        return f"<Package id={self.id} code={self.code} price_kes={self.price_kes}>"


# =========================================================
# Customers
# =========================================================
class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)

    # Store phone in normalized format (e.g. 2547XXXXXXXX)
    phone = db.Column(db.String(20), unique=True, nullable=False, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    subscriptions = db.relationship(
        "Subscription",
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="select",
    )
    transactions = db.relationship(
        "Transaction",
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Customer id={self.id} phone={self.phone}>"


# =========================================================
# Subscriptions (Customer Entitlement)
# =========================================================
class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)

    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False, index=True)
    package_id = db.Column(db.Integer, db.ForeignKey("packages.id"), nullable=False, index=True)

    # pending / active / expired
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)

    starts_at = db.Column(db.DateTime, nullable=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=True, index=True)

    # phone as username (or PPPoE username later)
    router_username = db.Column(db.String(50), nullable=False, index=True)

    # bind after first login
    mac_address = db.Column(db.String(30), nullable=True, index=True)

    # last tx that affected this subscription
    last_tx_id = db.Column(db.Integer, db.ForeignKey("transactions.id"), nullable=True, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    customer = db.relationship("Customer", back_populates="subscriptions", lazy="joined")
    package = db.relationship("Package", back_populates="subscriptions", lazy="joined")

    last_transaction = db.relationship("Transaction", foreign_keys=[last_tx_id], lazy="joined")

    # Compatibility alias (do NOT use in query filters; use last_tx_id)
    @property
    def transaction_id(self) -> int | None:
        return self.last_tx_id

    @transaction_id.setter
    def transaction_id(self, value: int | None) -> None:
        self.last_tx_id = value

    def is_active_now(self, now: datetime | None = None) -> bool:
        now = now or datetime.utcnow()
        return (
            self.status == "active"
            and self.starts_at is not None
            and self.expires_at is not None
            and self.starts_at <= now < self.expires_at
        )

    def __repr__(self) -> str:
        return f"<Subscription id={self.id} customer_id={self.customer_id} status={self.status}>"


# =========================================================
# Transactions (M-Pesa payments / STK push lifecycle)
# =========================================================
class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)

    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False, index=True)
    package_id = db.Column(db.Integer, db.ForeignKey("packages.id"), nullable=False, index=True)

    amount = db.Column(db.Integer, nullable=False)

    # pending / success / failed
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)

    checkout_request_id = db.Column(db.String(80), unique=True, nullable=True, index=True)
    merchant_request_id = db.Column(db.String(80), nullable=True, index=True)
    mpesa_receipt = db.Column(db.String(40), unique=True, nullable=True, index=True)

    result_code = db.Column(db.String(10), nullable=True)
    result_desc = db.Column(db.String(255), nullable=True)

    raw_callback_json = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    customer = db.relationship("Customer", back_populates="transactions", lazy="joined")
    package = db.relationship("Package", back_populates="transactions", lazy="joined")

    def __repr__(self) -> str:
        return f"<Transaction id={self.id} status={self.status} amount={self.amount}>"
