# app/models.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from flask_login import UserMixin
from sqlalchemy.sql import func
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db

# =========================================================
# Helpers
# =========================================================

UTCNOW_SQL = sa.text("timezone('utc', now())")


def utcnow() -> datetime:
    """Python-side UTC timestamp."""
    return datetime.utcnow()


# =========================================================
# Admin Users (System Users + Roles)
# =========================================================

class AdminUser(UserMixin, db.Model):
    """
    System users who can access /admin/* routes.

    - role: finance | ops | support | admin
    - is_superadmin: bypass role checks
    - name: optional display name
    """
    __tablename__ = "admin_users"

    id: int = db.Column(db.Integer, primary_key=True)

    email: str = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash: str = db.Column(db.String(255), nullable=False)

    is_active: bool = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=sa.text("true"),
        index=True,
    )

    name: Optional[str] = db.Column(db.String(80), nullable=True)

    role: str = db.Column(
        db.String(20),
        nullable=False,
        default="admin",
        server_default=sa.text("'admin'"),
        index=True,
    )

    is_superadmin: bool = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("false"),
        index=True,
    )

    created_at: datetime = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow,
        server_default=func.now(),  # keep legacy compatibility
        index=True,
    )

    # Tickets
    tickets_created = db.relationship(
        "Ticket",
        foreign_keys="Ticket.created_by_admin_id",
        back_populates="created_by",
        lazy="select",
    )

    tickets_assigned = db.relationship(
        "Ticket",
        foreign_keys="Ticket.assigned_to_admin_id",
        back_populates="assigned_to",
        lazy="select",
    )

    ticket_updates = db.relationship(
        "TicketUpdate",
        foreign_keys="TicketUpdate.actor_admin_id",
        back_populates="actor",
        lazy="select",
    )

    # --- Password helpers ---
    @staticmethod
    def hash_password(password: str) -> str:
        # scrypt is strong and supported by werkzeug
        return generate_password_hash(password, method="scrypt")

    def set_password(self, password: str) -> None:
        self.password_hash = self.hash_password(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    # --- Role helpers ---
    def has_role(self, *roles: str) -> bool:
        if not self.is_active:
            return False
        if self.is_superadmin:
            return True
        my_role = (self.role or "").strip().lower()
        allowed = {r.strip().lower() for r in roles if r and r.strip()}
        return my_role in allowed

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

    id: int = db.Column(db.Integer, primary_key=True)

    admin_user_id: int = db.Column(
        db.Integer,
        db.ForeignKey("admin_users.id"),
        nullable=False,
        index=True,
    )

    action: str = db.Column(db.String(60), nullable=False, index=True)
    ip_address: Optional[str] = db.Column(db.String(64), nullable=True)
    user_agent: Optional[str] = db.Column(db.String(255), nullable=True)
    meta_json: Optional[str] = db.Column(db.Text, nullable=True)

    created_at: datetime = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow,
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
    """Represents any plan you sell (Hotspot or PPPoE)."""
    __tablename__ = "packages"

    id: int = db.Column(db.Integer, primary_key=True)

    code: str = db.Column(db.String(30), unique=True, nullable=False, index=True)
    name: str = db.Column(db.String(80), nullable=False)

    duration_minutes: int = db.Column(db.Integer, nullable=False)
    price_kes: int = db.Column(db.Integer, nullable=False)

    max_devices: int = db.Column(
        db.Integer,
        nullable=False,
        default=1,
        server_default=sa.text("1"),
    )

    mikrotik_profile: str = db.Column(db.String(60), nullable=False)

    created_at: datetime = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow,
        server_default=func.now(),
        index=True,
    )

    # IMPORTANT: subscriptions has TWO FKs referencing packages.id
    # - Subscription.package_id
    # - Subscription.pending_package_id
    #
    # We must disambiguate with foreign_keys to avoid AmbiguousForeignKeysError.
    subscriptions = db.relationship(
        "Subscription",
        foreign_keys="Subscription.package_id",
        back_populates="package",
        lazy="select",
    )

    pending_subscriptions = db.relationship(
        "Subscription",
        foreign_keys="Subscription.pending_package_id",
        back_populates="pending_package",
        lazy="select",
    )

    transactions = db.relationship("Transaction", back_populates="package", lazy="select")

    def __repr__(self) -> str:
        return f"<Package id={self.id} code={self.code} price_kes={self.price_kes}>"


# =========================================================
# Customers
# =========================================================

class Customer(db.Model):
    __tablename__ = "customers"

    id: int = db.Column(db.Integer, primary_key=True)

    # Store phone in normalized format (e.g. 2547XXXXXXXX)
    phone: str = db.Column(db.String(20), unique=True, nullable=False, index=True)

    # PPPoE creds (optional)
    pppoe_username: Optional[str] = db.Column(db.String(64), unique=True, nullable=True, index=True)
    pppoe_password: Optional[str] = db.Column(db.String(128), nullable=True)

    created_at: datetime = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow,
        server_default=func.now(),
        index=True,
    )

    locations = db.relationship(
        "CustomerLocation",
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="CustomerLocation.created_at.desc()",
    )

    tickets = db.relationship(
        "Ticket",
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="Ticket.created_at.desc()",
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

    @property
    def active_location(self):
        # Best-effort helper (DB should enforce uniqueness via partial index)
        for loc in self.locations:
            if loc.active:
                return loc
        return None

    def __repr__(self) -> str:
        return f"<Customer id={self.id} phone={self.phone} pppoe_username={self.pppoe_username}>"


# =========================================================
# Subscriptions (Customer Entitlement)
# =========================================================

class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id: int = db.Column(db.Integer, primary_key=True)

    customer_id: int = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False, index=True)

    package_id: int = db.Column(db.Integer, db.ForeignKey("packages.id"), nullable=False, index=True)

    # If customer requests a downgrade mid-cycle, apply it at next renewal (no refunds)
    pending_package_id: Optional[int] = db.Column(
        db.Integer,
        db.ForeignKey("packages.id"),
        nullable=True,
        index=True,
    )

    service_type: str = db.Column(
        db.String(20),
        nullable=False,
        default="hotspot",
        server_default=sa.text("'hotspot'"),
        index=True,
    )

    pppoe_username: Optional[str] = db.Column(db.String(64), nullable=True, index=True)
    hotspot_username: Optional[str] = db.Column(db.String(64), nullable=True, index=True)

    status: str = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
        server_default=sa.text("'pending'"),
        index=True,
    )

    starts_at: Optional[datetime] = db.Column(db.DateTime, nullable=True, index=True)
    expires_at: Optional[datetime] = db.Column(db.DateTime, nullable=True, index=True)

    router_username: Optional[str] = db.Column(db.String(50), nullable=True, index=True)
    mac_address: Optional[str] = db.Column(db.String(30), nullable=True, index=True)

    last_tx_id: Optional[int] = db.Column(
        db.Integer,
        db.ForeignKey("transactions.id"),
        nullable=True,
        index=True,
    )

    created_at: datetime = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow,
        server_default=func.now(),
        index=True,
    )

    # Relationships
    customer = db.relationship("Customer", back_populates="subscriptions", lazy="joined")

    package = db.relationship(
        "Package",
        foreign_keys=[package_id],
        back_populates="subscriptions",
        lazy="joined",
    )

    pending_package = db.relationship(
        "Package",
        foreign_keys=[pending_package_id],
        back_populates="pending_subscriptions",
        lazy="joined",
    )

    last_transaction = db.relationship(
        "Transaction",
        foreign_keys=[last_tx_id],
        lazy="joined",
    )

    tickets = db.relationship(
        "Ticket",
        back_populates="subscription",
        lazy="select",
        order_by="Ticket.created_at.desc()",
    )

    @property
    def transaction_id(self) -> Optional[int]:
        return self.last_tx_id

    @transaction_id.setter
    def transaction_id(self, value: Optional[int]) -> None:
        self.last_tx_id = value

    def identity(self) -> str:
        if (self.service_type or "").strip().lower() == "pppoe":
            return (self.pppoe_username or "").strip()
        return (self.hotspot_username or "").strip()

    def is_active_now(self, now: Optional[datetime] = None) -> bool:
        now = now or utcnow()
        return (
            (self.status or "").strip().lower() == "active"
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

    id: int = db.Column(db.Integer, primary_key=True)

    customer_id: int = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False, index=True)
    package_id: int = db.Column(db.Integer, db.ForeignKey("packages.id"), nullable=False, index=True)

    amount: int = db.Column(db.Integer, nullable=False)

    status: str = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
        server_default=sa.text("'pending'"),
        index=True,
    )

    checkout_request_id: Optional[str] = db.Column(db.String(80), unique=True, nullable=True, index=True)
    merchant_request_id: Optional[str] = db.Column(db.String(80), nullable=True, index=True)
    mpesa_receipt: Optional[str] = db.Column(db.String(40), unique=True, nullable=True, index=True)

    result_code: Optional[str] = db.Column(db.String(10), nullable=True)
    result_desc: Optional[str] = db.Column(db.String(255), nullable=True)

    raw_callback_json: Optional[str] = db.Column(db.Text, nullable=True)

    created_at: datetime = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow,
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

    id: int = db.Column(db.Integer, primary_key=True)

    asset_type: str = db.Column(db.String(30), nullable=False, index=True)
    brand: Optional[str] = db.Column(db.String(60), nullable=True)
    model: Optional[str] = db.Column(db.String(60), nullable=True)
    serial_number: Optional[str] = db.Column(db.String(80), unique=True, nullable=True)

    purchase_date = db.Column(db.Date, nullable=True)
    purchase_cost: Optional[int] = db.Column(db.Integer, nullable=True)

    status: str = db.Column(
        db.String(20),
        nullable=False,
        default="in_store",
        server_default=sa.text("'in_store'"),
        index=True,
    )

    assigned_customer_id: Optional[int] = db.Column(
        db.Integer,
        db.ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    assigned_location_id = db.Column(db.Integer, nullable=True)  # future FK

    notes: Optional[str] = db.Column(db.Text, nullable=True)

    created_at: datetime = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow,
        server_default=UTCNOW_SQL,
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

    id: int = db.Column(db.Integer, primary_key=True)

    asset_id: int = db.Column(
        db.Integer,
        db.ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event_type: str = db.Column(db.String(30), nullable=False, index=True)
    description: Optional[str] = db.Column(db.Text, nullable=True)

    performed_by_admin: Optional[int] = db.Column(
        db.Integer,
        db.ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: datetime = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow,
        server_default=UTCNOW_SQL,
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

    id: int = db.Column(db.Integer, primary_key=True)

    name: str = db.Column(db.String(60), nullable=False, index=True)

    parent_id: Optional[int] = db.Column(
        db.Integer,
        db.ForeignKey("expense_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    is_active: bool = db.Column(db.Boolean, nullable=False, default=True, server_default=sa.text("true"))

    created_at: datetime = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow,
        server_default=UTCNOW_SQL,
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

    id: int = db.Column(db.Integer, primary_key=True)

    category_id: int = db.Column(
        db.Integer,
        db.ForeignKey("expense_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    name: str = db.Column(db.String(80), nullable=False, index=True)
    default_amount: Optional[int] = db.Column(db.Integer, nullable=True)
    notes: Optional[str] = db.Column(db.Text, nullable=True)

    is_active: bool = db.Column(db.Boolean, nullable=False, default=True, server_default=sa.text("true"))

    created_at: datetime = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow,
        server_default=UTCNOW_SQL,
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

    id: int = db.Column(db.Integer, primary_key=True)

    category: str = db.Column(db.String(30), nullable=False, index=True)

    category_id: Optional[int] = db.Column(
        db.Integer,
        db.ForeignKey("expense_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    template_id: Optional[int] = db.Column(
        db.Integer,
        db.ForeignKey("expense_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    amount: int = db.Column(db.Integer, nullable=False)
    description: Optional[str] = db.Column(db.Text, nullable=True)

    asset_id: Optional[int] = db.Column(
        db.Integer,
        db.ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    ticket_id = db.Column(db.Integer, nullable=True)  # future FK

    incurred_at: datetime = db.Column(db.DateTime, nullable=False, index=True)

    recorded_by_admin: Optional[int] = db.Column(
        db.Integer,
        db.ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: datetime = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow,
        server_default=func.now(),
        index=True,
    )

    asset = db.relationship("Asset", back_populates="expenses", lazy="joined")
    admin_user = db.relationship("AdminUser", lazy="joined")

    category_ref = db.relationship("ExpenseCategory", lazy="joined")
    template = db.relationship("ExpenseTemplate", back_populates="expenses", lazy="joined")

    def __repr__(self) -> str:
        return f"<Expense id={self.id} category={self.category} amount={self.amount} incurred_at={self.incurred_at}>"


# =========================================================
# Phase A — Customer Locations & Ticketing (Schema First)
# =========================================================

class CustomerLocation(db.Model):
    __tablename__ = "customer_locations"

    id: int = db.Column(db.Integer, primary_key=True)

    customer_id: int = db.Column(
        db.Integer,
        db.ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    label: Optional[str] = db.Column(db.String(80), nullable=True)

    county: Optional[str] = db.Column(db.String(60), nullable=True)
    town: Optional[str] = db.Column(db.String(60), nullable=True)
    estate: Optional[str] = db.Column(db.String(80), nullable=True)
    apartment_name: Optional[str] = db.Column(db.String(120), nullable=True)
    house_no: Optional[str] = db.Column(db.String(40), nullable=True)
    landmark: Optional[str] = db.Column(db.String(200), nullable=True)

    gps_lat = db.Column(db.Numeric(9, 6), nullable=True)
    gps_lng = db.Column(db.Numeric(9, 6), nullable=True)

    notes: Optional[str] = db.Column(db.Text, nullable=True)

    active: bool = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("false"),
        index=True,
    )

    active_from_utc: datetime = db.Column(db.DateTime, nullable=False, index=True)
    active_to_utc: Optional[datetime] = db.Column(db.DateTime, nullable=True, index=True)

    created_by_admin_id: Optional[int] = db.Column(
        db.Integer,
        db.ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: datetime = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow,
        server_default=UTCNOW_SQL,
        index=True,
    )

    updated_at: datetime = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=UTCNOW_SQL,
        index=True,
    )

    customer = db.relationship("Customer", back_populates="locations", lazy="joined")
    created_by = db.relationship("AdminUser", lazy="joined")

    tickets = db.relationship(
        "Ticket",
        back_populates="location",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<CustomerLocation id={self.id} customer_id={self.customer_id} active={self.active} label={self.label}>"


class Ticket(db.Model):
    __tablename__ = "tickets"

    id: int = db.Column(db.Integer, primary_key=True)

    code: str = db.Column(db.String(30), nullable=False, unique=True, index=True)

    customer_id: int = db.Column(
        db.Integer,
        db.ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    subscription_id: Optional[int] = db.Column(
        db.Integer,
        db.ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    location_id: Optional[int] = db.Column(
        db.Integer,
        db.ForeignKey("customer_locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    category: str = db.Column(
        db.String(40),
        nullable=False,
        default="outage",
        server_default=sa.text("'outage'"),
        index=True,
    )

    priority: str = db.Column(
        db.String(10),
        nullable=False,
        default="med",
        server_default=sa.text("'med'"),
        index=True,
    )

    status: str = db.Column(
        db.String(20),
        nullable=False,
        default="open",
        server_default=sa.text("'open'"),
        index=True,
    )

    subject: str = db.Column(db.String(160), nullable=False)
    description: Optional[str] = db.Column(db.Text, nullable=True)

    opened_at_utc: datetime = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow,
        server_default=UTCNOW_SQL,
        index=True,
    )

    resolved_at_utc: Optional[datetime] = db.Column(db.DateTime, nullable=True, index=True)
    closed_at_utc: Optional[datetime] = db.Column(db.DateTime, nullable=True, index=True)

    created_by_admin_id: int = db.Column(
        db.Integer,
        db.ForeignKey("admin_users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    assigned_to_admin_id: Optional[int] = db.Column(
        db.Integer,
        db.ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: datetime = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow,
        server_default=UTCNOW_SQL,
        index=True,
    )

    updated_at: datetime = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=UTCNOW_SQL,
        index=True,
    )

    customer = db.relationship("Customer", back_populates="tickets", lazy="joined")
    subscription = db.relationship("Subscription", back_populates="tickets", lazy="joined")
    location = db.relationship("CustomerLocation", back_populates="tickets", lazy="joined")

    created_by = db.relationship(
        "AdminUser",
        foreign_keys=[created_by_admin_id],
        back_populates="tickets_created",
        lazy="joined",
    )

    assigned_to = db.relationship(
        "AdminUser",
        foreign_keys=[assigned_to_admin_id],
        back_populates="tickets_assigned",
        lazy="joined",
    )

    updates = db.relationship(
        "TicketUpdate",
        back_populates="ticket",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="select",
        order_by="TicketUpdate.created_at.asc()",
    )

    @property
    def is_open(self) -> bool:
        return (self.status or "").strip().lower() in {
            "open", "assigned", "in_progress", "waiting_customer"
        }

    def __repr__(self) -> str:
        return f"<Ticket id={self.id} code={self.code} status={self.status} customer_id={self.customer_id}>"


class TicketUpdate(db.Model):
    __tablename__ = "ticket_updates"

    id: int = db.Column(db.Integer, primary_key=True)

    ticket_id: int = db.Column(
        db.Integer,
        db.ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    actor_admin_id: Optional[int] = db.Column(
        db.Integer,
        db.ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    message: Optional[str] = db.Column(db.Text, nullable=True)

    status_from: Optional[str] = db.Column(db.String(20), nullable=True)
    status_to: Optional[str] = db.Column(db.String(20), nullable=True)

    assigned_from_admin_id: Optional[int] = db.Column(
        db.Integer,
        db.ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    assigned_to_admin_id: Optional[int] = db.Column(
        db.Integer,
        db.ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: datetime = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow,
        server_default=UTCNOW_SQL,
        index=True,
    )

    ticket = db.relationship("Ticket", back_populates="updates", lazy="joined")

    actor = db.relationship(
        "AdminUser",
        foreign_keys=[actor_admin_id],
        back_populates="ticket_updates",
        lazy="joined",
    )

    assigned_from = db.relationship(
        "AdminUser",
        foreign_keys=[assigned_from_admin_id],
        lazy="joined",
    )

    assigned_to = db.relationship(
        "AdminUser",
        foreign_keys=[assigned_to_admin_id],
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<TicketUpdate id={self.id} ticket_id={self.ticket_id} created_at={self.created_at}>"

class MpesaPayment(db.Model):
    __tablename__ = "mpesa_payments"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, nullable=True)
    subscription_id = db.Column(db.Integer, nullable=True)

    phone = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)

    checkout_request_id = db.Column(db.String(64), index=True)
    merchant_request_id = db.Column(db.String(64))
    mpesa_receipt = db.Column(db.String(40), unique=True)

    status = db.Column(db.String(20), nullable=False, default="pending")
    paid_at = db.Column(db.DateTime(timezone=True), nullable=True)

    raw_callback = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), server_default=db.text("now()"), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.text("now()"), nullable=False)


class HotspotEntitlement(db.Model):
    __tablename__ = "hotspot_entitlements"
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), index=True, nullable=False)
    username = db.Column(db.String(64), index=True, nullable=False)
    package_code = db.Column(db.String(32), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active")  # active|expired|revoked
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
