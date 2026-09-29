"""Advanced search & filtering: turns query-string params into SQLAlchemy
predicates.

Supported syntax (``<field>__<op>=<value>``):

===============  =========================================================
``field=v``       equality
``field__ne=v``   inequality
``field__gte=v``  >=        ``field__lte=v``  <=
``field__gt=v``   >         ``field__lt=v``   <
``field__like=v`` case-insensitive containment (ILIKE %v%)
``field__in=a,b,c`` membership
``q=free text``  OR-ed ILIKE across the model's searchable columns
===============  =========================================================

Only columns explicitly whitelisted in ``allowed`` can be filtered —
this prevents leaking or injecting predicates the API never intended
to expose.
"""

import operator
import uuid as uuid_module
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import Request
from sqlalchemy import ColumnElement, and_, or_
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql import Select

from app.core.exceptions import ValidationAppError

_COMPARATORS = {
    "eq": operator.eq,
    "ne": operator.ne,
    "gte": operator.ge,
    "lte": operator.le,
    "gt": operator.gt,
    "lt": operator.lt,
}

#: query-string keys with list-endpoint meaning that are never column filters
RESERVED_PARAMS = frozenset({"q", "page", "page_size", "sort"})


def _coerce(column: InstrumentedAttribute, raw: Any) -> Any:
    """Cast a raw string to the column's Python type."""
    python_type = getattr(column.type, "python_type", None)
    try:
        if python_type and isinstance(raw, python_type):
            return raw
        if python_type is int:
            return int(raw)
        if python_type is float:
            return float(raw)
        if python_type is bool:
            value = str(raw).lower()
            if value not in ("1", "true", "yes", "0", "false", "no"):
                raise ValueError("expected a boolean")
            return value in ("1", "true", "yes")
        if python_type is Decimal:
            value = Decimal(str(raw))
            if not value.is_finite():
                raise ValueError("expected a finite number")
            return value
        if python_type is datetime:
            return datetime.fromisoformat(raw)
        if python_type is date:
            return date.fromisoformat(raw)
        if python_type is uuid_module.UUID:
            return uuid_module.UUID(raw)
    except (TypeError, ValueError, InvalidOperation) as exc:
        raise ValueError(f"invalid value {raw!r} for column {column.key}") from exc
    return raw


def apply_filters(
    stmt: Select,
    model: type,
    allowed: dict[str, InstrumentedAttribute],
    params: dict[str, Any],
    searchable: list[InstrumentedAttribute] | None = None,
) -> Select:
    """Append predicates parsed from ``params`` to ``stmt``."""
    conditions: list[ColumnElement[bool]] = []

    for raw_key, value in params.items():
        if raw_key in (None, "q", "sort", "page", "page_size") or value in (None, ""):
            continue

        field_name, _, op = raw_key.partition("__")
        op = op or "eq"

        column = allowed.get(field_name)
        if column is None:
            raise ValidationAppError(f"filtering by '{field_name}' is not allowed")
        if op not in _COMPARATORS and op not in ("like", "in"):
            raise ValidationAppError(f"unknown filter operator '{op}'")

        try:
            if op == "like":
                conditions.append(column.ilike(f"%{value}%"))
            elif op == "in":
                values = [_coerce(column, v.strip()) for v in value.split(",") if v.strip()]
                conditions.append(column.in_(values))
            else:
                conditions.append(_COMPARATORS[op](column, _coerce(column, value)))
        except ValueError as exc:
            raise ValidationAppError(str(exc)) from exc

    # free-text search: OR across whitelisted searchable columns
    q = params.get("q")
    if q and searchable:
        like_clauses = [col.ilike(f"%{q}%") for col in searchable]
        if like_clauses:
            conditions.append(or_(*like_clauses))

    if conditions:
        stmt = stmt.where(and_(*conditions))
    return stmt


def validate_query_params(request: Request, allowed: dict[str, InstrumentedAttribute]) -> None:
    """Reject query parameters that are not whitelisted filters.

    FastAPI silently ignores undeclared query parameters, so a typo like
    ``?statu=available`` would otherwise be swallowed and return unfiltered
    data. Every list endpoint calls this with its whitelist so clients get an
    actionable 422 instead.
    """
    from app.core.exceptions import ValidationAppError

    for key in request.query_params:
        if key in RESERVED_PARAMS:
            continue
        field_name, _, op = key.partition("__")
        op = op or "eq"
        if field_name not in allowed or (op not in _COMPARATORS and op not in ("like", "in")):
            raise ValidationAppError(
                f"filtering by '{key}' is not allowed",
                details={
                    "allowed_fields": sorted(allowed),
                    "operators": ["eq", "ne", "gt", "gte", "lt", "lte", "like", "in"],
                },
            )


def apply_sort(
    stmt: Select,
    allowed: dict[str, InstrumentedAttribute],
    sort: str | None,
    default: str = "created_at",
) -> Select:
    """Sort spec: comma-separated columns, ``-`` prefix means descending."""
    if not sort:
        sort = default
    clauses = []
    for part in sort.split(","):
        part = part.strip()
        if not part:
            continue
        descending = part.startswith("-")
        column_name = part.lstrip("-")
        column = allowed.get(column_name)
        if column is None:
            from app.core.exceptions import ValidationAppError

            raise ValidationAppError(f"sorting by '{column_name}' is not allowed")
        clauses.append(column.desc() if descending else column.asc())
    if clauses:
        stmt = stmt.order_by(*clauses)
    return stmt
