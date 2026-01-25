from __future__ import annotations

from datetime import datetime
from .extensions import db


# =========================================================
# Packages (hotspot plans)
# =========================================================
class Package(db.Model):
    __tablename__ = "packages"

    id = db.Column(db.Integer, primary_key=True)

    # e.g. daily_1, weekly_1, monthly_2, etc.
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)

    name = db.Column(db.String(60), nullable=False)

    # Duration of access in minutes
    duration_minutes = db.Column(db.Integer, nullable=False)

    # Price in Kenyan Shillings
    price_kes = db.Column(db.Integer, nullable=False)

    # MikroTik profile name (e.g. HS-DAILY, HS-WEEKLY)
    mikrotik_profile = db.Column(db.String(60), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<Package id={self.id} code={self.code} price_kes={self.price_kes}>"


# =========================================================
# Customers
# =========================================================
class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)

    # Store phone in a normalized way in your app logic if possible (e.g. 2547...)
    phone = db.Column(db.String(20), unique=True, nullable=False, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Helpful reverse relationships (optional but clean)
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
# Subscriptions (customer entitlement)
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

    # IMPORTANT:
    # This is the DB column you already have.
    # It represents the *last* (most recent) transaction affecting this subscription.
    last_tx_id = db.Column(db.Integer, db.ForeignKey("transactions.id"), nullable=True, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    customer = db.relationship("Customer", back_populates="subscriptions")
    package = db.relationship("Package", lazy="joined")

    last_transaction = db.relationship(
        "Transaction",
        foreign_keys=[last_tx_id],
        lazy="joined",
    )

    # ✅ Compatibility alias:
    # Your routes currently pass `transaction_id=tx.id`.
    # Instead of crashing, this property maps that to `last_tx_id`.
    @property
    def transaction_id(self) -> int | None:
        return self.last_tx_id

    @transaction_id.setter
    def transaction_id(self, value: int | None) -> None:
        self.last_tx_id = value

    def is_active(self, now: datetime | None = None) -> bool:
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

    # Relationships
    customer = db.relationship("Customer", back_populates="transactions")
    package = db.relationship("Package", lazy="joined")

    def __repr__(self) -> str:
        return f"<Transaction id={self.id} status={self.status} amount={self.amount}>"
