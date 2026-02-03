from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import func

from ..extensions import db
from ..models import Expense, ExpenseCategory, Transaction


# =========================================================
# Month bounds (NAIVE UTC) because DB stores naive UTC
# =========================================================
def month_bounds_utc_naive(year: int, month: int) -> Tuple[datetime, datetime]:
    """
    Returns [start, end) bounds in naive UTC for a given month.
    DB stores naive UTC (datetime.utcnow), so we keep naive here.
    """
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return start, end


def sum_income_utc_naive(start: datetime, end: datetime) -> int:
    """
    Sum successful income from transactions in [start, end).
    Uses Transaction.amount (per your admin.py revenue_totals()).
    """
    val = (
        db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(Transaction.created_at >= start)
        .filter(Transaction.created_at < end)
        .filter(Transaction.status == "success")
        .scalar()
    )
    return int(val or 0)


def sum_expenses_utc_naive(start: datetime, end: datetime) -> int:
    """
    Sum expenses in [start, end).
    Uses incurred_at if present; falls back to created_at.
    """
    ts = func.coalesce(Expense.incurred_at, Expense.created_at)

    val = (
        db.session.query(func.coalesce(func.sum(Expense.amount), 0))
        .filter(ts >= start)
        .filter(ts < end)
        .scalar()
    )
    return int(val or 0)


def profit_snapshot_month(year: int, month: int) -> dict:
    start, end = month_bounds_utc_naive(year, month)
    income = sum_income_utc_naive(start, end)
    expenses = sum_expenses_utc_naive(start, end)
    return {
        "year": year,
        "month": month,
        "income_kes": income,
        "expenses_kes": expenses,
        "profit_kes": income - expenses,
        "start_utc": start,  # naive UTC
        "end_utc": end,      # naive UTC
    }


def expense_breakdown_by_category_month(year: int, month: int) -> List[dict]:
    """
    Breakdown by category_id (preferred) with fallback to legacy text.
    """
    start, end = month_bounds_utc_naive(year, month)
    ts = func.coalesce(Expense.incurred_at, Expense.created_at)

    rows = (
        db.session.query(
            Expense.category_id,
            Expense.category,  # legacy string fallback
            func.coalesce(func.sum(Expense.amount), 0).label("total_kes"),
        )
        .filter(ts >= start)
        .filter(ts < end)
        .group_by(Expense.category_id, Expense.category)
        .order_by(func.coalesce(func.sum(Expense.amount), 0).desc())
        .all()
    )

    cat_ids = [r.category_id for r in rows if r.category_id is not None]
    cats = {}
    if cat_ids:
        for c in db.session.query(ExpenseCategory).filter(ExpenseCategory.id.in_(cat_ids)).all():
            cats[c.id] = c.name

    out: List[dict] = []
    for r in rows:
        name = cats.get(r.category_id) if r.category_id else (r.category or "Uncategorized")
        out.append(
            {
                "category_id": r.category_id,
                "category_name": name,
                "total_kes": int(r.total_kes or 0),
            }
        )
    return out


def last_n_months_summary(n: int = 6, anchor_utc_naive: Optional[datetime] = None) -> List[dict]:
    """
    Last N months including anchor month. Anchor is naive UTC.
    """
    if anchor_utc_naive is None:
        anchor_utc_naive = datetime.utcnow()

    y, m = anchor_utc_naive.year, anchor_utc_naive.month

    items: List[dict] = []
    for _ in range(n):
        items.append(profit_snapshot_month(y, m))
        # step back one month
        if m == 1:
            y -= 1
            m = 12
        else:
            m -= 1

    return items

def profit_snapshot_range(start: datetime, end: datetime) -> dict:
    """
    Range snapshot using naive UTC [start, end).
    """
    income = sum_income_utc_naive(start, end)
    expenses = sum_expenses_utc_naive(start, end)
    return {
        "start_utc": start,
        "end_utc": end,
        "income_kes": income,
        "expenses_kes": expenses,
        "profit_kes": income - expenses,
    }


def expense_breakdown_by_category_range(start: datetime, end: datetime) -> List[dict]:
    """
    Range breakdown by category_id (preferred) + legacy text fallback.
    """
    ts = func.coalesce(Expense.incurred_at, Expense.created_at)

    rows = (
        db.session.query(
            Expense.category_id,
            Expense.category,
            func.coalesce(func.sum(Expense.amount), 0).label("total_kes"),
        )
        .filter(ts >= start)
        .filter(ts < end)
        .group_by(Expense.category_id, Expense.category)
        .order_by(func.coalesce(func.sum(Expense.amount), 0).desc())
        .all()
    )

    cat_ids = [r.category_id for r in rows if r.category_id is not None]
    cats = {}
    if cat_ids:
        for c in db.session.query(ExpenseCategory).filter(ExpenseCategory.id.in_(cat_ids)).all():
            cats[c.id] = c.name

    out: List[dict] = []
    for r in rows:
        name = cats.get(r.category_id) if r.category_id else (r.category or "Uncategorized")
        out.append(
            {
                "category_id": r.category_id,
                "category_name": name,
                "total_kes": int(r.total_kes or 0),
            }
        )
    return out
