import calendar
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.employee import Employee as EmployeeModel
from app.models.finance import (
    ExpenseCategory,
    ExpenseDirection,
    OperatingExpense,
    OrderExpense,
    OrderPayment,
)
from app.models.order import Order as OrderModel
from app.schemas.finance import (
    CategoryBreakdownItem,
    EmployeeWageExpense,
    EmployeeWageItem,
    EmployeeWagesOut,
    MonthlyReportOut,
    OrderDetailItem,
    OrdersDetailOut,
)

# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------


def add_payment(
    db: Session,
    *,
    order_id: int,
    amount: Decimal,
    received_on: date,
    created_by: int,
    note: str | None = None,
) -> OrderPayment:
    payment = OrderPayment(
        order_id=order_id,
        amount=amount,
        received_on=received_on,
        note=note,
        created_by=created_by,
    )
    db.add(payment)
    db.flush()
    return payment


def list_payments(db: Session, order_id: int) -> list[OrderPayment]:
    return list(
        db.execute(
            select(OrderPayment)
            .where(OrderPayment.order_id == order_id)
            .order_by(OrderPayment.received_on, OrderPayment.id)
        )
        .scalars()
        .all()
    )


def delete_payment(db: Session, payment_id: int, *, order_id: int | None = None) -> OrderPayment:
    payment = db.get(OrderPayment, payment_id)
    if payment is None or (order_id is not None and payment.order_id != order_id):
        raise ValueError(f"Payment {payment_id} not found")
    db.delete(payment)
    db.flush()
    return payment


def patch_payment(
    db: Session,
    payment_id: int,
    *,
    order_id: int | None = None,
    **kwargs: object,
) -> OrderPayment:
    payment = db.get(OrderPayment, payment_id)
    if payment is None or (order_id is not None and payment.order_id != order_id):
        raise ValueError(f"Payment {payment_id} not found")
    for key, value in kwargs.items():
        setattr(payment, key, value)
    db.flush()
    return payment


def total_paid(db: Session, order_id: int) -> Decimal:
    result = db.execute(
        select(func.sum(OrderPayment.amount)).where(OrderPayment.order_id == order_id)
    ).scalar_one_or_none()
    return result if result is not None else Decimal("0.00")


def bulk_total_paid(db: Session, order_ids: list[int]) -> dict[int, Decimal]:
    """Return {order_id: total_paid} for a batch of orders in one query."""
    if not order_ids:
        return {}
    rows = db.execute(
        select(OrderPayment.order_id, func.sum(OrderPayment.amount))
        .where(OrderPayment.order_id.in_(order_ids))
        .group_by(OrderPayment.order_id)
    ).all()
    result = {oid: Decimal("0.00") for oid in order_ids}
    for oid, total in rows:
        result[oid] = total
    return result


# ---------------------------------------------------------------------------
# Expenses
# ---------------------------------------------------------------------------


def add_expense(
    db: Session,
    *,
    order_id: int,
    direction: ExpenseDirection,
    category_id: int,
    amount: Decimal,
    spent_on: date,
    created_by: int,
    employee_id: int | None = None,
    note: str | None = None,
) -> OrderExpense:
    # Validate direction/employee_id consistency before hitting the DB CHECK
    if direction == ExpenseDirection.to_employee and employee_id is None:
        raise ValueError("employee_id is required for direction 'to_employee'")
    if direction == ExpenseDirection.general and employee_id is not None:
        raise ValueError("employee_id must be None for direction 'general'")
    expense = OrderExpense(
        order_id=order_id,
        direction=direction,
        category_id=category_id,
        employee_id=employee_id,
        amount=amount,
        spent_on=spent_on,
        note=note,
        created_by=created_by,
    )
    db.add(expense)
    db.flush()
    return expense


def list_expenses(db: Session, order_id: int) -> list[OrderExpense]:
    return list(
        db.execute(
            select(OrderExpense)
            .where(OrderExpense.order_id == order_id)
            .order_by(OrderExpense.spent_on, OrderExpense.id)
        )
        .scalars()
        .all()
    )


def delete_expense(db: Session, expense_id: int, *, order_id: int | None = None) -> OrderExpense:
    expense = db.get(OrderExpense, expense_id)
    if expense is None or (order_id is not None and expense.order_id != order_id):
        raise ValueError(f"Expense {expense_id} not found")
    db.delete(expense)
    db.flush()
    return expense


def patch_expense(
    db: Session,
    expense_id: int,
    *,
    order_id: int | None = None,
    **kwargs: object,
) -> OrderExpense:
    expense = db.get(OrderExpense, expense_id)
    if expense is None or (order_id is not None and expense.order_id != order_id):
        raise ValueError(f"Expense {expense_id} not found")
    # Re-validate direction/employee_id consistency if either is being changed
    new_direction = kwargs.get("direction", expense.direction)
    new_employee_id = kwargs.get("employee_id", expense.employee_id)
    if new_direction == ExpenseDirection.to_employee and new_employee_id is None:
        raise ValueError("employee_id is required for direction 'to_employee'")
    if new_direction == ExpenseDirection.general:
        kwargs["employee_id"] = None
    for key, value in kwargs.items():
        setattr(expense, key, value)
    db.flush()
    return expense


def total_expenses(db: Session, order_id: int) -> Decimal:
    result = db.execute(
        select(func.sum(OrderExpense.amount)).where(OrderExpense.order_id == order_id)
    ).scalar_one_or_none()
    return result if result is not None else Decimal("0.00")


# ---------------------------------------------------------------------------
# Operating expenses (not tied to a specific order)
# ---------------------------------------------------------------------------


def add_operating_expense(
    db: Session,
    *,
    category_id: int,
    amount: Decimal,
    spent_on: date,
    created_by: int,
    note: str | None = None,
) -> OperatingExpense:
    expense = OperatingExpense(
        category_id=category_id,
        amount=amount,
        spent_on=spent_on,
        note=note,
        created_by=created_by,
    )
    db.add(expense)
    db.flush()
    return expense


def list_operating_expenses(db: Session) -> list[OperatingExpense]:
    return list(
        db.execute(
            select(OperatingExpense).order_by(OperatingExpense.spent_on.desc(), OperatingExpense.id)
        )
        .scalars()
        .all()
    )


def delete_operating_expense(db: Session, expense_id: int) -> OperatingExpense:
    expense = db.get(OperatingExpense, expense_id)
    if expense is None:
        raise ValueError(f"Operating expense {expense_id} not found")
    db.delete(expense)
    db.flush()
    return expense


def patch_operating_expense(db: Session, expense_id: int, **kwargs: object) -> OperatingExpense:
    expense = db.get(OperatingExpense, expense_id)
    if expense is None:
        raise ValueError(f"Operating expense {expense_id} not found")
    for key, value in kwargs.items():
        setattr(expense, key, value)
    db.flush()
    return expense


# ---------------------------------------------------------------------------
# Monthly report — computed on-the-fly from three sources
# ---------------------------------------------------------------------------


def _zero() -> Decimal:
    return Decimal("0.00")


def monthly_report(db: Session, year: int, month: int) -> MonthlyReportOut:
    """Compute monthly financial report without storing results.

    Combines order_expense AND operating_expense into a single category breakdown
    so no category present in only one source is lost (union, not inner join).
    Invariant: total_expenses == sum(breakdown.amount).
    """
    last_day = calendar.monthrange(year, month)[1]
    start = date(year, month, 1)
    end = date(year, month, last_day)

    # Revenue: payments received in this month
    revenue_raw = db.execute(
        select(func.sum(OrderPayment.amount)).where(OrderPayment.received_on.between(start, end))
    ).scalar_one_or_none()
    revenue = revenue_raw if revenue_raw is not None else _zero()

    # Order expenses by category
    oe_rows = db.execute(
        select(OrderExpense.category_id, func.sum(OrderExpense.amount))
        .where(OrderExpense.spent_on.between(start, end))
        .group_by(OrderExpense.category_id)
    ).all()

    # Operating expenses by category
    op_rows = db.execute(
        select(OperatingExpense.category_id, func.sum(OperatingExpense.amount))
        .where(OperatingExpense.spent_on.between(start, end))
        .group_by(OperatingExpense.category_id)
    ).all()

    # Subtotals for the report
    order_exp_total = sum((r[1] for r in oe_rows), _zero())
    op_exp_total = sum((r[1] for r in op_rows), _zero())

    # Merge both sources by category (union of keys — neither source loses categories)
    by_category: dict[int, Decimal] = defaultdict(_zero)
    for cat_id, total in oe_rows:
        by_category[cat_id] += total
    for cat_id, total in op_rows:
        by_category[cat_id] += total

    total_exp = order_exp_total + op_exp_total

    # Resolve category names in one query — include deactivated (historical data intact)
    cat_ids = list(by_category.keys())
    cats: dict[int, ExpenseCategory] = {}
    if cat_ids:
        cats = {
            c.id: c
            for c in db.execute(select(ExpenseCategory).where(ExpenseCategory.id.in_(cat_ids)))
            .scalars()
            .all()
        }
    breakdown: list[CategoryBreakdownItem] = []
    for cat_id, amount in by_category.items():
        cat = cats.get(cat_id)
        breakdown.append(
            CategoryBreakdownItem(
                category_id=cat_id,
                category_name=cat.name if cat else f"#{cat_id}",
                amount=amount,
            )
        )
    breakdown.sort(key=lambda x: x.category_name)

    return MonthlyReportOut(
        year=year,
        month=month,
        revenue=revenue,
        order_expenses=order_exp_total,
        operating_expenses=op_exp_total,
        total_expenses=total_exp,
        profit=revenue - total_exp,
        breakdown=breakdown,
    )


# ---------------------------------------------------------------------------
# Employee wages report — order expenses directed to employees
# ---------------------------------------------------------------------------


def employee_wages_report(db: Session, year: int, month: int) -> EmployeeWagesOut:
    last_day = calendar.monthrange(year, month)[1]
    start = date(year, month, 1)
    end = date(year, month, last_day)

    rows = db.execute(
        select(
            OrderExpense.employee_id,
            OrderExpense.order_id,
            OrderExpense.amount,
            OrderExpense.spent_on,
            OrderExpense.note,
            ExpenseCategory.name.label("category_name"),
            OrderModel.title.label("order_title"),
            OrderModel.internal_number.label("order_internal_number"),
            EmployeeModel.full_name.label("employee_name"),
        )
        .join(OrderModel, OrderExpense.order_id == OrderModel.id)
        .join(ExpenseCategory, OrderExpense.category_id == ExpenseCategory.id)
        .join(EmployeeModel, OrderExpense.employee_id == EmployeeModel.id)
        .where(OrderExpense.direction == ExpenseDirection.to_employee)
        .where(OrderExpense.spent_on.between(start, end))
        .order_by(EmployeeModel.full_name, OrderExpense.spent_on)
    ).all()

    by_employee: dict[int, dict[str, Any]] = {}
    for row in rows:
        eid = row.employee_id
        if eid not in by_employee:
            by_employee[eid] = {
                "employee_id": eid,
                "full_name": row.employee_name,
                "total": _zero(),
                "expenses": [],
            }
        by_employee[eid]["total"] += row.amount
        by_employee[eid]["expenses"].append(
            EmployeeWageExpense(
                order_id=row.order_id,
                order_title=row.order_title,
                order_internal_number=row.order_internal_number,
                category_name=row.category_name,
                amount=row.amount,
                spent_on=row.spent_on,
                note=row.note,
            )
        )

    employees = [
        EmployeeWageItem(**d) for d in sorted(by_employee.values(), key=lambda x: x["full_name"])
    ]
    grand_total = sum((e.total for e in employees), _zero())
    return EmployeeWagesOut(year=year, month=month, total=grand_total, employees=employees)


# ---------------------------------------------------------------------------
# Orders detail report — per-order payments and expenses for the month
# ---------------------------------------------------------------------------


def orders_detail_report(db: Session, year: int, month: int) -> OrdersDetailOut:
    last_day = calendar.monthrange(year, month)[1]
    start = date(year, month, 1)
    end = date(year, month, last_day)

    paid_rows = db.execute(
        select(OrderPayment.order_id, func.sum(OrderPayment.amount).label("paid"))
        .where(OrderPayment.received_on.between(start, end))
        .group_by(OrderPayment.order_id)
    ).all()

    exp_rows = db.execute(
        select(OrderExpense.order_id, func.sum(OrderExpense.amount).label("expenses"))
        .where(OrderExpense.spent_on.between(start, end))
        .group_by(OrderExpense.order_id)
    ).all()

    paid_by_order: dict[int, Decimal] = {r.order_id: r.paid for r in paid_rows}
    exp_by_order: dict[int, Decimal] = {r.order_id: r.expenses for r in exp_rows}
    all_ids = list(set(paid_by_order) | set(exp_by_order))

    if not all_ids:
        return OrdersDetailOut(year=year, month=month, orders=[])

    orders = {
        o.id: o
        for o in db.execute(select(OrderModel).where(OrderModel.id.in_(all_ids))).scalars().all()
    }

    # All-time totals for receivable calculation (total_amount - total_paid_all_time)
    all_time_paid = bulk_total_paid(db, all_ids)

    items: list[OrderDetailItem] = []
    for oid in all_ids:
        o = orders.get(oid)
        if o is None:
            continue
        paid = paid_by_order.get(oid, _zero())
        exp = exp_by_order.get(oid, _zero())
        items.append(
            OrderDetailItem(
                order_id=o.id,
                title=o.title,
                customer_name=o.customer_name,
                internal_number=o.internal_number,
                total_amount=o.total_amount,
                paid_in_month=paid,
                expenses_in_month=exp,
                net_in_month=paid - exp,
                total_paid_all_time=all_time_paid.get(oid, _zero()),
            )
        )

    items.sort(key=lambda x: float(str(x.paid_in_month)), reverse=True)
    return OrdersDetailOut(year=year, month=month, orders=items)


# ---------------------------------------------------------------------------
