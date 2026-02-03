# app/models.py
from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from flask_login import UserMixin
from sqlalchemy.sql import func
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db

# =========================================================
# Admin Users (System Users + Roles)
# =========================================================
class AdminUser(UserMixin, db.Model):
    """
    System users who can access /admin/* routes.

    Phase E additions:
    - role: finance | ops | support | admin
    - is_superadmin: bypass role checks (optional)
    - name: optional display name

    Notes:
    - Table remains "admin_users" (matches DB).
    - Login identifier is email (store lowercase).
    - Uses strong password hashing (scrypt) for new/updated passwords.
    """
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(db.String(120), unique=True, nullable=False, index=True)

    password_hash = db.Column(db.String(255), nullable=False)

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=sa.text("true"),
    )

    # -------------------------
    # Phase E: roles & metadata
    # -------------------------
    name = db.Column(db.String(80), nullable=True)

    # roles: admin | finance | ops | support
    role = db.Column(
        db.String(20),
        nullable=False,
        default="admin",
        server_default=sa.text("'admin'"),
        index=True,
    )

    # optional: superadmin can access everything regardless of role
    is_superadmin = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("false"),
        index=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,   # SQLAlchemy inserts
        server_default=func.now(), # raw SQL inserts (DB local timezone; OK for legacy tables)
        index=True,
    )

    # --- Password helpers ---
    @staticmethod
    def hash_password(password: str) -> str:
        return generate_password_hash(password, method="scrypt")

    def set_password(self, password: str) -> None:
        self.password_hash = self.hash_password(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    # --- Role helpers ---
    def has_role(self, *roles: str) -> bool:
        """
        True if:
        - user is superadmin, OR
        - user's role is in roles
        """
        if not self.is_active:
            return False
        if self.is_superadmin:
            return True

        my_role = (self.role or "").strip().lower()
        allowed = {r.strip().lower() for r in roles if r and r.strip()}
        return my_role in allowed

    # Convenience helpers (optional, but useful in templates)
    def can_finance(self) -> bool:
        return self.has_role("finance", "admin")

    def can_ops(self) -> bool:
        return self.has_role("ops", "admin")

    def can_support(self) -> bool:
        return self.has_role("support", "admin")

    def __repr__(self) -> str:
        return f"<AdminUser id={self.id} email={self.email} role={self.role} super={self.is_superadmin}>"


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

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        index=True,
    )

    admin_user = db.relationship("AdminUser", lazy="joined")

    def __repr__(self) -> str:
        return f"<AdminAuditLog id={self.id} action={self.action} admin_user_id={self.admin_user_id}>"


# =========================================================
# Packages (Hotspot & PPPoE Plans)
# =========================================================
class Package(db.Model):
    """
    Represents any plan you sell.
    """
    __tablename__ = "packages"

    id = db.Column(db.Integer, primary_key=True)

    code = db.Column(db.String(30), unique=True, nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)

    duration_minutes = db.Column(db.Integer, nullable=False)
    price_kes = db.Column(db.Integer, nullable=False)

    # MikroTik profile name
    mikrotik_profile = db.Column(db.String(60), nullable=False)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        index=True,
    )

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

    # PPPoE creds (optional)
    pppoe_username = db.Column(db.String(64), unique=True, nullable=True, index=True)
    pppoe_password = db.Column(db.String(128), nullable=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        index=True,
    )

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

    assets = db.relationship(
        "Asset",
        back_populates="customer",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Customer id={self.id} phone={self.phone} pppoe_username={self.pppoe_username}>"


# =========================================================
# Subscriptions (Customer Entitlement)
# =========================================================
class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)

    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False, index=True)
    package_id = db.Column(db.Integer, db.ForeignKey("packages.id"), nullable=False, index=True)

    service_type = db.Column(
        db.String(20),
        nullable=False,
        default="hotspot",
        server_default="hotspot",
        index=True,
    )

    pppoe_username = db.Column(db.String(64), nullable=True, index=True)
    hotspot_username = db.Column(db.String(64), nullable=True, index=True)

    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )

    starts_at = db.Column(db.DateTime, nullable=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=True, index=True)

    router_username = db.Column(db.String(50), nullable=True, index=True)

    mac_address = db.Column(db.String(30), nullable=True, index=True)

    last_tx_id = db.Column(db.Integer, db.ForeignKey("transactions.id"), nullable=True, index=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        index=True,
    )

    customer = db.relationship("Customer", back_populates="subscriptions", lazy="joined")
    package = db.relationship("Package", back_populates="subscriptions", lazy="joined")
    last_transaction = db.relationship("Transaction", foreign_keys=[last_tx_id], lazy="joined")

    @property
    def transaction_id(self) -> int | None:
        return self.last_tx_id

    @transaction_id.setter
    def transaction_id(self, value: int | None) -> None:
        self.last_tx_id = value

    def identity(self) -> str:
        if (self.service_type or "").lower().strip() == "pppoe":
            return (self.pppoe_username or "").strip()
        return (self.hotspot_username or "").strip()

    def is_active_now(self, now: datetime | None = None) -> bool:
        now = now or datetime.utcnow()
        return (
            self.status == "active"
            and self.starts_at is not None
            and self.expires_at is not None
            and self.starts_at <= now < self.expires_at
        )

    def __repr__(self) -> str:
        return f"<Subscription id={self.id} service_type={self.service_type} identity={self.identity()} status={self.status}>"


# =========================================================
# Transactions (M-Pesa payments / STK push lifecycle)
# =========================================================
class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)

    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False, index=True)
    package_id = db.Column(db.Integer, db.ForeignKey("packages.id"), nullable=False, index=True)

    amount = db.Column(db.Integer, nullable=False)

    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )

    checkout_request_id = db.Column(db.String(80), unique=True, nullable=True, index=True)
    merchant_request_id = db.Column(db.String(80), nullable=True, index=True)
    mpesa_receipt = db.Column(db.String(40), unique=True, nullable=True, index=True)

    result_code = db.Column(db.String(10), nullable=True)
    result_desc = db.Column(db.String(255), nullable=True)

    raw_callback_json = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        index=True,
    )

    customer = db.relationship("Customer", back_populates="transactions", lazy="joined")
    package = db.relationship("Package", back_populates="transactions", lazy="joined")

    def __repr__(self) -> str:
        return f"<Transaction id={self.id} status={self.status} amount={self.amount}>"


# =========================================================
# Phase D — Assets & Expenses (Ops + Finance)
# =========================================================
class Asset(db.Model):
    __tablename__ = "assets"

    id = db.Column(db.Integer, primary_key=True)

    asset_type = db.Column(db.String(30), nullable=False, index=True)
    brand = db.Column(db.String(60), nullable=True)
    model = db.Column(db.String(60), nullable=True)
    serial_number = db.Column(db.String(80), unique=True, nullable=True)

    purchase_date = db.Column(db.Date, nullable=True)
    purchase_cost = db.Column(db.Integer, nullable=True)  # KES

    # in_store, deployed, faulty, retired, lost
    status = db.Column(
        db.String(20),
        nullable=False,
        default="in_store",
        server_default="in_store",
        index=True,
    )

    assigned_customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_location_id = db.Column(db.Integer, nullable=True)  # future FK to customer_locations

    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        # Match DB migration for Phase D tables (UTC)
        server_default=sa.text("timezone('utc', now())"),
        index=True,
    )

    customer = db.relationship("Customer", back_populates="assets", lazy="joined")

    events = db.relationship(
        "AssetEvent",
        back_populates="asset",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="select",
    )

    expenses = db.relationship(
        "Expense",
        back_populates="asset",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Asset id={self.id} type={self.asset_type} status={self.status} serial={self.serial_number}>"


class AssetEvent(db.Model):
    __tablename__ = "asset_events"

    id = db.Column(db.Integer, primary_key=True)

    asset_id = db.Column(
        db.Integer,
        db.ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event_type = db.Column(db.String(30), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)

    performed_by_admin = db.Column(
        db.Integer,
        db.ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=sa.text("timezone('utc', now())"),
        index=True,
    )

    asset = db.relationship("Asset", back_populates="events", lazy="joined")
    admin_user = db.relationship("AdminUser", lazy="joined")

    def __repr__(self) -> str:
        return f"<AssetEvent id={self.id} asset_id={self.asset_id} type={self.event_type}>"


# =========================================================
# Phase D.3 — Expense Categories & Templates
# =========================================================
class ExpenseCategory(db.Model):
    __tablename__ = "expense_categories"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(60), nullable=False, index=True)

    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("expense_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=sa.text("true"))

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=sa.text("timezone('utc', now())"),
        index=True,
    )

    parent = db.relationship(
        "ExpenseCategory",
        remote_side=[id],
        back_populates="children",
        lazy="joined",
    )

    children = db.relationship(
        "ExpenseCategory",
        back_populates="parent",
        cascade="all",
        lazy="select",
    )


    templates = db.relationship("ExpenseTemplate", back_populates="category", lazy="select")

    def __repr__(self) -> str:
        return f"<ExpenseCategory id={self.id} name={self.name} parent_id={self.parent_id}>"


class ExpenseTemplate(db.Model):
    __tablename__ = "expense_templates"

    id = db.Column(db.Integer, primary_key=True)

    category_id = db.Column(
        db.Integer,
        db.ForeignKey("expense_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    name = db.Column(db.String(80), nullable=False, index=True)
    default_amount = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=sa.text("true"))

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=sa.text("timezone('utc', now())"),
        index=True,
    )

    category = db.relationship("ExpenseCategory", back_populates="templates", lazy="joined")
    expenses = db.relationship("Expense", back_populates="template", lazy="select")

    def __repr__(self) -> str:
        return f"<ExpenseTemplate id={self.id} name={self.name} category_id={self.category_id}>"


class Expense(db.Model):
    """
    OPEX / CAPEX entries.

    Keep legacy `category` text for compatibility (NOT NULL in DB).
    New structured fields: category_id + template_id.
    """
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)

    category = db.Column(db.String(30), nullable=False, index=True)

    category_id = db.Column(
        db.Integer,
        db.ForeignKey("expense_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    template_id = db.Column(
        db.Integer,
        db.ForeignKey("expense_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    amount = db.Column(db.Integer, nullable=False)  # KES
    description = db.Column(db.Text, nullable=True)

    asset_id = db.Column(
        db.Integer,
        db.ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    ticket_id = db.Column(db.Integer, nullable=True)  # future FK to tickets

    incurred_at = db.Column(db.DateTime, nullable=False, index=True)

    recorded_by_admin = db.Column(
        db.Integer,
        db.ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        # Keep DB default as-is for now (legacy), we can normalize later in a tiny migration
        server_default=func.now(),
        index=True,
    )

    asset = db.relationship("Asset", back_populates="expenses", lazy="joined")
    admin_user = db.relationship("AdminUser", lazy="joined")

    # Avoid name clash with legacy `category` text column
    category_ref = db.relationship("ExpenseCategory", lazy="joined")
    template = db.relationship("ExpenseTemplate", back_populates="expenses", lazy="joined")

    def __repr__(self) -> str:
        return f"<Expense id={self.id} category={self.category} amount={self.amount} incurred_at={self.incurred_at}>"

